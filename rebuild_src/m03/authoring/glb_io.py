"""Small glTF 2 reader / byte-preserving mesh replacement. Project-specific, offline."""
from pathlib import Path
import struct, json, copy, hashlib
import numpy as np
from scipy.spatial.transform import Rotation
DT={5126:'<f4',5123:'<u2',5125:'<u4',5121:'u1'}
DIMS={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
def read_glb(path):
 raw=Path(path).read_bytes();j=b=None;o=12
 if struct.unpack_from('<III',raw)!=(0x46546c67,2,len(raw)):raise ValueError('Invalid GLB header')
 while o<len(raw):
  n,t=struct.unpack_from('<II',raw,o);o+=8
  if t==0x4e4f534a:j=json.loads(raw[o:o+n])
  elif t==0x004e4942:b=raw[o:o+n]
  o+=n
 return j,b

def acc(j,b,i):
 a=j['accessors'][i];v=j['bufferViews'][a['bufferView']]
 if 'byteStride' in v:raise ValueError('Interleaved accessor not supported by this authoring utility')
 return np.frombuffer(b,DT[a['componentType']],count=a['count']*DIMS[a['type']],offset=v.get('byteOffset',0)+a.get('byteOffset',0)).reshape(a['count'],-1).copy()

def mesh_arrays(j,b,mi,materials=None):
 ps=[];ns=[];js=[];ws=[];uv=[];ix=[];ms=[];off=0
 for p in j['meshes'][mi]['primitives']:
  if materials is not None and p['material'] not in materials:continue
  a=p['attributes'];pos=acc(j,b,a['POSITION']);ps.append(pos);ns.append(acc(j,b,a['NORMAL']))
  js.append(acc(j,b,a['JOINTS_0']));ws.append(acc(j,b,a['WEIGHTS_0']));uv.append(acc(j,b,a['TEXCOORD_0']))
  tri=acc(j,b,p['indices']).reshape(-1,3)+off;ix.append(tri);ms.extend([p['material']]*len(tri));off+=len(pos)
 return dict(p=np.concatenate(ps),n=np.concatenate(ns),j=np.concatenate(js),w=np.concatenate(ws),uv=np.concatenate(uv),f=np.concatenate(ix),mat=np.array(ms))

def qinterp(a,b,u):
 a=a.astype(float);b=b.astype(float);d=np.dot(a,b)
 if d<0:b=-b;d=-d
 if d>.9995:q=a*(1-u)+b*u;return q/np.linalg.norm(q)
 th=np.arccos(np.clip(d,-1,1));return (a*np.sin((1-u)*th)+b*np.sin(u*th))/np.sin(th)

def bone_matrices(j,b,name='DesignPose',time=0):
 """Matches the original Animator.sample() LINEAR/STEP rules, no crossfade."""
 joints=j['skins'][0]['joints'];count=len(joints);tr=[];qu=[];sc=[]
 for k in joints:
  n=j['nodes'][k];tr.append(np.array(n.get('translation',[0,0,0]),float));qu.append(np.array(n.get('rotation',[0,0,0,1]),float));sc.append(np.array(n.get('scale',[1,1,1]),float))
 nodeIndex={n:i for i,n in enumerate(joints)};an=next(a for a in j['animations'] if a['name']==name)
 dur=max(float(acc(j,b,s['input'])[-1,0]) for s in an['samplers']);t=time%dur if name in ['Idle','Run'] else min(time,dur)
 for ch in an['channels']:
  s=an['samplers'][ch['sampler']];ts=acc(j,b,s['input']).ravel();vs=acc(j,b,s['output']);i=0
  while i<len(ts)-2 and t>ts[i+1]:i+=1
  k=min(i+1,len(ts)-1);u=(1 if t>=ts[k] else 0) if s.get('interpolation')=='STEP' else np.clip((t-ts[i])/(ts[k]-ts[i] or 1),0,1)
  n=nodeIndex[ch['target']['node']];path=ch['target']['path'];val=qinterp(vs[i],vs[k],u) if path=='rotation' else (1-u)*vs[i]+u*vs[k]
  if path=='rotation':qu[n]=val
  elif path=='translation':tr[n]=val
  elif path=='scale':sc[n]=val
  else:raise ValueError('Unsupported channel')
 parents={nodeIndex[c]:nodeIndex[n] for n in joints for c in j['nodes'][n].get('children',[]) if c in nodeIndex};world={}
 def w(i):
  if i not in world:
   m=np.eye(4);m[:3,:3]=Rotation.from_quat(qu[i]).as_matrix()@np.diag(sc[i]);m[:3,3]=tr[i]
   world[i]=w(parents[i])@m if i in parents else m
  return world[i]
 inverse=acc(j,b,j['skins'][0]['inverseBindMatrices']).reshape(count,4,4).transpose(0,2,1)
 return np.array([w(i)@inverse[i] for i in range(count)])

def skin_positions(p,joints,weights,bones):
 pp=np.c_[p,np.ones(len(p))];mt=np.sum(bones[joints]*weights[...,None,None],axis=1)
 return np.einsum('nij,nj->ni',mt,pp)[:,:3]

def unskin_positions(p,joints,weights,bones):
 mt=np.sum(bones[joints]*weights[...,None,None],axis=1)
 return np.linalg.solve(mt,np.c_[p,np.ones(len(p))][...,None])[:,:3,0]

def section_segments(p,f,y):
 """Actual triangle/horizontal plane intersection, not a bbox/vertex-nearness test."""
 tri=p[f];sel=(tri[:,:,1].min(1)<=y)&(tri[:,:,1].max(1)>=y);tri=tri[sel];segments=[]
 for t in tri:
  points=[]
  for k in range(3):
   a=t[k];b=t[(k+1)%3]
   if abs(a[1]-b[1])<1e-10:continue
   u=(y-a[1])/(b[1]-a[1])
   if -1e-9<=u<=1+1e-9:points.append(a+u*(b-a))
  if len(points)>=2:segments.append(points[:2])
 return np.array(segments)

def replace_mesh(base_path,out_path,positions,normals,joints,weights,uv,faces,metadata):
 j,b=read_glb(base_path);new=copy.deepcopy(j);blob=bytearray(b)
 def av(raw,target):
  blob.extend(b'\0'*(-len(blob)%4));v=dict(buffer=0,byteOffset=len(blob),byteLength=len(raw),target=target)
  new['bufferViews'].append(v);blob.extend(raw);return len(new['bufferViews'])-1
 def aa(a,ty,ct=5126,target=34962):
  a=np.asarray(a,DT[ct]);v=dict(bufferView=av(a.tobytes(),target),componentType=ct,count=len(a),type=ty)
  if ty=='VEC3':v.update(min=a.min(0).astype(float).tolist(),max=a.max(0).astype(float).tolist())
  new['accessors'].append(v);return len(new['accessors'])-1
 attrs={k:aa(a,ty,ct) for k,a,ty,ct in [('POSITION',positions,'VEC3',5126),('NORMAL',normals,'VEC3',5126),('JOINTS_0',joints,'VEC4',5123),('WEIGHTS_0',weights,'VEC4',5126),('TEXCOORD_0',uv,'VEC2',5126),('COLOR_0',np.ones((len(positions),4)),'VEC4',5126)]}
 new['meshes'][7]=dict(name=j['meshes'][7]['name'],primitives=[dict(attributes=attrs,indices=aa(np.array(faces).ravel(),'SCALAR',5125,34963),material=2)],extras=metadata)
 new['asset']['generator']='Stargazer M03 / H01 base / design-space shoulder envelope'
 new['extras']={**j.get('extras',{}),'sampleVersion':'M03','status':'plain coverage candidate, not visually approved or installed in game','scope':'only mesh 08 Asymmetric shoulder mantle','sourceH01SHA256':hashlib.sha256(Path(base_path).read_bytes()).hexdigest(),'checkedClips':[], 'animationReview':'refer to M03 reports; inherited H01 claims do not apply', 'mantle':metadata}
 # Compact while retaining every live non-mantle byte.
 live=set()
 for mesh in new['meshes']:
  for p in mesh['primitives']:live.update(p['attributes'].values());live.add(p['indices'])
 for sk in new['skins']:live.add(sk['inverseBindMatrices'])
 for a in new['animations']:
  for s in a['samplers']:live.update([s['input'],s['output']])
 buf=bytearray();views=[];acs=[];vm={};am={}
 def cp(i):
  if i in vm:return vm[i]
  v=copy.deepcopy(new['bufferViews'][i]);raw=blob[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']];buf.extend(b'\0'*(-len(buf)%4));v['byteOffset']=len(buf);buf.extend(raw);vm[i]=len(views);views.append(v);return vm[i]
 for i in sorted(live):
  a=copy.deepcopy(new['accessors'][i]);a['bufferView']=cp(a['bufferView']);am[i]=len(acs);acs.append(a)
 for mesh in new['meshes']:
  for p in mesh['primitives']:p['attributes']={k:am[i] for k,i in p['attributes'].items()};p['indices']=am[p['indices']]
 for sk in new['skins']:sk['inverseBindMatrices']=am[sk['inverseBindMatrices']]
 for an in new['animations']:
  for s in an['samplers']:s['input']=am[s['input']];s['output']=am[s['output']]
 for im in new['images']:im['bufferView']=cp(im['bufferView'])
 new['accessors']=acs;new['bufferViews']=views;new['buffers']=[dict(byteLength=len(buf))]
 new['extras']['triangleCount']=sum(acs[p['indices']]['count']//3 for m in new['meshes'] for p in m['primitives'])
 new['extras']['vertexCount']=sum(acs[p['attributes']['POSITION']]['count'] for m in new['meshes'] for p in m['primitives'])
 js=json.dumps(new,separators=(',',':'),ensure_ascii=False).encode();js+=b' '*(-len(js)%4);buf.extend(b'\0'*(-len(buf)%4))
 raw=struct.pack('<III',0x46546c67,2,28+len(js)+len(buf))+struct.pack('<II',len(js),0x4e4f534a)+js+struct.pack('<II',len(buf),0x004e4942)+buf
 Path(out_path).write_bytes(raw);return new
