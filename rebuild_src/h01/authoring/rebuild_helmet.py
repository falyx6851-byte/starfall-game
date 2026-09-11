"""H01: replace ONLY A01's helmet mesh. Body/materials/rig/animation bytes are preserved.

Authoring: explicit continuous parametric shell with real inner walls; face panels
share sampled boundary curves, with separate normals only at authored panel creases.
No Blender, generative image, external API, or flat reference image is used.
"""
from pathlib import Path
import numpy as np
from scipy.interpolate import PchipInterpolator
import struct, json, copy, hashlib, math
R=Path(__file__).resolve().parents[1]
RECT=[(0,0,512,512),(512,0,1024,512),(0,512,512,1024),(512,512,768,768),(768,512,1024,768),(512,768,768,1024),(768,768,1024,1024)]
TAU=math.tau
HELMET_SCALE=np.array([.91,.86,.90])
HELMET_ANCHOR=np.array([0,-.116,0])

def unit(x):
 a=np.asarray(x,float);n=np.linalg.norm(a);return a/max(n,1e-12)
def read_glb(path):
 raw=path.read_bytes();j=None;b=None;o=12
 while o<len(raw):
  n,t=struct.unpack_from('<II',raw,o);o+=8
  if t==0x4e4f534a:j=json.loads(raw[o:o+n])
  if t==0x004e4942:b=raw[o:o+n]
  o+=n
 return j,b
DT={5126:'<f4',5123:'<u2',5125:'<u4',5121:'u1'}
DIMS={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
def accessor(j,b,i):
 a=j['accessors'][i];v=j['bufferViews'][a['bufferView']]
 return np.frombuffer(b,dtype=DT[a['componentType']],count=a['count']*DIMS[a['type']],offset=v.get('byteOffset',0)+a.get('byteOffset',0)).reshape(a['count'],-1)

class Model:
 def __init__(self):
  self.p=[];self.n=[];self.uv=[];self.indices=[[] for _ in RECT];self.parts=[]
 def vert(self,p,n,m,u=0.5,v=0.5):
  i=len(self.p);self.p.append(list(p));self.n.append(list(unit(n)))
  x0,y0,x1,y1=RECT[m];self.uv.append([(x0+5+np.clip(u,0,1)*(x1-x0-10))/1024,(y0+5+np.clip(v,0,1)*(y1-y0-10))/1024]);return i
 def face(self,a,b,c,m):
  p=np.array([self.p[i] for i in [a,b,c]]);f=np.cross(p[1]-p[0],p[2]-p[0])
  if np.linalg.norm(f)<1e-12:return
  if np.dot(f,np.sum([self.n[i] for i in [a,b,c]],axis=0))<0:b,c=c,b
  self.indices[m].extend([a,b,c])
 def tri(self,ps,m,norm=None):
  n=unit(np.cross(np.array(ps[1])-ps[0],np.array(ps[2])-ps[0])) if norm is None else norm
  ids=[self.vert(p,n,m) for p in ps];self.face(*ids,m)
 def grid(self,fn,m,nu,nv,hint,periodic=False):
  pts=[];ns=[];eps=1e-5
  for v in np.linspace(0,1,nv+1):
   pr=[];nr=[]
   for u in np.linspace(0,1,nu+1):
    p=np.array(fn(u,v));u0=u-eps if periodic else max(0,u-eps);u1=u+eps if periodic else min(1,u+eps)
    v0=max(0,v-eps);v1=min(1,v+eps)
    du=np.array(fn(u1,v))-fn(u0,v);dv=np.array(fn(u,v1))-fn(u,v0);n=unit(np.cross(du,dv));h=hint(u,v)
    if np.linalg.norm(n)<.5:n=unit(h)
    if np.dot(n,h)<0:n=-n
    pr.append(p);nr.append(n)
   pts.append(pr);ns.append(nr)
  pts=np.array(pts);ns=np.array(ns)
  # Collapsed pole rings share a single stable normal; no spiky pole shading.
  for j in [0,nv]:
   if np.max(np.ptp(pts[j],axis=0))<1e-9:
    ns[j,:]=unit(np.sum(ns[j],axis=0))
  ids=np.empty((nv+1,nu+1),int)
  for j in range(nv+1):
   for i in range(nu+1):ids[j,i]=self.vert(pts[j,i],ns[j,i],m,i/nu,j/nv)
  for j in range(nv):
   for i in range(nu):
    self.face(ids[j,i],ids[j,i+1],ids[j+1,i+1],m);self.face(ids[j,i],ids[j+1,i+1],ids[j+1,i],m)
  return pts,ns
 def shell(self,name,fn,m,nu,nv,hint,thick=.008,periodic=False,offset=None,walls=(True,True,True,True)):
  start=len(self.p);ii=[len(a) for a in self.indices]
  pts,ns=self.grid(fn,m,nu,nv,hint,periodic)
  # Interior offset field is a *continuous* function shared across panel boundaries.
  if offset is None:inners=pts-ns*thick
  else:inners=np.array([[p-np.asarray(offset(i/nu,j/nv))*thick for i,p in enumerate(row)] for j,row in enumerate(pts)])
  inmat=6 if m==0 else m
  ids=np.empty((nv+1,nu+1),int)
  for j in range(nv+1):
   for i in range(nu+1):ids[j,i]=self.vert(inners[j,i],-ns[j,i],inmat,i/nu,j/nv)
  for j in range(nv):
   for i in range(nu):self.face(ids[j,i],ids[j+1,i+1],ids[j,i+1],inmat);self.face(ids[j,i],ids[j+1,i],ids[j+1,i+1],inmat)
  # Real thickness at every exposed perimeter; no duplicated internal panel walls.
  for ed in range(4):
   if not walls[ed] or periodic and ed in [2,3]:continue
   aa=(pts[0,:],pts[-1,:],pts[:,0],pts[:,-1])[ed];bb=(inners[0,:],inners[-1,:],inners[:,0],inners[:,-1])[ed]
   for k in range(len(aa)-1):
    self.tri([aa[k],bb[k],bb[k+1]],m);self.tri([aa[k],bb[k+1],aa[k+1]],m)
  self.parts.append({'name':name,'vertexStart':start,'vertexEnd':len(self.p),'indicesStart':ii,'indicesEnd':[len(a) for a in self.indices]})
 def poly(self,name,outline,front,back,m=1):
  start=len(self.p);ii=[len(a) for a in self.indices];p=np.array(outline)
  for a,b in zip(p,np.roll(p,-1,axis=0)):
   self.tri([front,a,b],m);self.tri([back,b-[0,0,.009],a-[0,0,.009]],m)
   self.tri([a,a-[0,0,.009],b-[0,0,.009]],m);self.tri([a,b-[0,0,.009],b],m)
  self.parts.append({'name':name,'vertexStart':start,'vertexEnd':len(self.p),'indicesStart':ii,'indicesEnd':[len(a) for a in self.indices]})

def profile_radius(y):
 if y>.10:
  f=math.sqrt(max(0,1-((y-.10)/.156)**2));return .170*f,.197*f,.168*f
 f=np.clip((y+.12)/.22,0,1);return .110+.060*math.sin(f*math.pi/2),.130+.067*math.sin(f*math.pi/2),.120+.048*math.sin(f*math.pi/2)
def bottom(a):
 a=abs((a+math.pi)%TAU-math.pi)
 if a<=1.04:return .082+.029*math.sin(a)
 if a>=1.66:return -.106+.01*max(0,(a-1.66)/(math.pi-1.66))
 t=(a-1.04)/(.62);t=t*t*(3-2*t)
 return (.082+.029*math.sin(1.04))*(1-t)+(-.106)*t

def crown(u,v):
 a=TAU*u;y=bottom(a)+(.256-bottom(a))*math.sin(v*math.pi/2)
 rx,rf,rb=profile_radius(y);c,s=math.cos(a),math.sin(a)
 zc=-.016-.016*max(0,(y-.12)/.136)
 return np.array([rx*s,y,zc+(rf if c>=0 else rb)*c+.005*max(c,0)**14*(1-v)**3])
def brow_at(a):return crown(a/TAU,0)

def make_helmet():
 m=Model()
 m.shell('continuous full cranial shell',crown,0,80,30,lambda u,v:[math.sin(TAU*u),.08+v*3,math.cos(TAU*u)],.009,True)
 # Low integrated sagittal crest. The base follows (and enters) the closed cranium.
 def crest_base(v):
  a=.29+2.48*v;y=.10+.156*math.sin(a)
  rx,rf,rb=profile_radius(y);zc=-.016-.016*max(0,(y-.12)/.136)
  z=zc+(rf if math.cos(a)>=0 else -rb)
  return np.array([0,y,z]),unit([0,math.sin(a),math.cos(a)])
 def crest(u,v):
  q,n=crest_base(v);w=.006+.016*math.sin(math.pi*v)**.8
  q=q+np.array([(2*u-1)*w,0,0]);q+=n*(-.006+.043*(1-abs(2*u-1))*math.sin(math.pi*v)**.75)
  return q
 for k in range(2):
  fn=lambda u,v,k=k:crest((k+u)/2,v)
  m.shell('integrated central crest '+str(k),fn,0,6,32,lambda u,v:[(k*2-1)*.5,.8,0],.012,offset=lambda u,v:crest_base(v)[1],walls=(True,True,k==0,k==1))
 # Lower mask: three connected longitudinal panels per side. All seam coordinates coincide.
 a0=math.asin(.010/.170);a1=1.04
 top=[brow_at(a0),brow_at(a1),np.array([.160,.073,.055]),np.array([.164,.049,.009])]
 for p in top[:2]:p[1]-=.019;p[2]-=.002
 rows=np.array([
  top,
  [[.012,-.002,.188],[.088,-.004,.172],[.124,-.018,.099],[.156,-.009,.008]],
  [[.010,-.077,.177],[.060,-.075,.162],[.108,-.068,.106],[.133,-.057,-.005]],
  [[.008,-.116,.167],[.032,-.112,.150],[.095,-.084,.093],[.121,-.073,-.009]]
 ],float)
 fs=[PchipInterpolator([0,.36,.76,1],rows[:,i,:],axis=0) for i in range(4)]
 for sg in [-1,1]:
  for k in range(3):
   def panel(u,v,k=k,sg=sg):
    p=fs[k](v)*(1-u)+fs[k+1](v)*u
    p=p.copy();p[2]+=(.0005 if k==0 else .0018)*math.sin(math.pi*u)*math.sin(math.pi*v)
    if k==0:
     contour=brow_at(a0+(a1-a0)*u).copy();contour[1]-=.019;contour[2]-=.002
     p+=(contour-(top[0]*(1-u)+top[1]*u))*(1-v)**4
    p[0]*=sg;return p
   def off(u,v,k=k,sg=sg):
    p=fs[k](v)*(1-u)+fs[k+1](v)*u
    return unit([sg*p[0]*.6,0,max(.015,p[2])])
   m.shell(f'face {sg} panel {k}',panel,0,12,24,lambda u,v,sg=sg:[sg*.5,0,1],.009,offset=off,walls=(True,True,k==0,k==2))
  # Recessed continuous eye band. The brim and the face top delimit its actual opening.
  def eyes(u,v,sg=sg):
   a=.07+(.982-.07)*u;p=brow_at(a).copy();p[1]-=.010+(v-.5)*.0058
   p[0]*=sg;p[2]-=.005;return p
  def backing(u,v,sg=sg):
   a=.045+1.015*u;p=brow_at(a).copy();p[1]-=.001+.019*v;p[0]*=sg;p[2]-=.010;return p
  m.shell(f'eye dark cavity {sg}',backing,3,36,2,lambda u,v:[0,0,1],.004)
  m.shell(f'cyan eye lens {sg}',eyes,4,36,2,lambda u,v:[0,0,1],.003)
  # A restrained antique-gold upper eyelid following the EXACT brim, not intersecting it.
  def brow_trim(u,v,sg=sg):
   a=.062+(.978-.062)*u;p=brow_at(a).copy();p[1]+=.0006+.0044*v;p[2]+=.0015;p[0]*=sg;return p
  m.shell(f'gold brow lip {sg}',brow_trim,1,36,2,lambda u,v:[0,0,1],.002)
 # Narrow black center joint behind mask and short gold nose bridge.
 def center(u,v):return [(u-.5)*.024,.09-.210*v,.178-.018*v]
 m.shell('recessed center mask seam',center,3,2,18,lambda u,v:[0,0,1],.008)
 # Crest badge: clear, short gold fold; the lower silver face remains two broad planes.
 m.poly('forehead seal and short nasal bridge',[[0,.154,.183],[.028,.103,.195],[.017,.071,.200],[0,.029,.203],[-.017,.071,.200],[-.028,.103,.195]],np.array([0,.095,.215]),np.array([0,.092,.179]),1)
 # Reference-scale crescent side fittings, embedded in oval temporal pivots.
 outer=PchipInterpolator([0,.18,.42,.67,.85,1],[.167,.211,.248,.250,.224,.174])
 inner=PchipInterpolator([0,.18,.42,.67,.85,1],[.140,.140,.167,.197,.210,.174])
 for sg in [-1,1]:
  # Ear pivot geometry occupies the actual shell surface, and the ornament root overlaps its upper lip.
  def socket(u,v,sg=sg):
   a=TAU*u;rim=.009*math.exp(-((v-.78)/.15)**2);return [sg*(.162+rim),.025+.040*v*math.sin(a),.006+.031*v*math.cos(a)]
  m.shell(f'temple pivot {sg}',socket,6,32,6,lambda u,v,sg=sg:[sg,0,0],.012)
  def crescent(u,v,sg=sg):
   x=float(outer(v))*(1-u)+float(inner(v))*u
   return [sg*x,.054+.326*v,.015-.056*v-.80*(x-.16)+.005*math.sin(math.pi*u)]
  m.shell(f'crescent fitting {sg}',crescent,0,10,38,lambda u,v:[0,0,1],.014,offset=lambda u,v:[0,0,1])
  for side in [0,1]:
   def edge(u,v,sg=sg,side=side):
    t=.08*u if side==0 else .92+.08*u;p=np.array(crescent(t,v));p[2]+=.0015;return p
   m.shell(f'crescent border {sg} {side}',edge,1,2,38,lambda u,v:[0,0,1],.001,offset=lambda u,v:[0,0,1])
 # Helmet-local reference-proportion pass; no body, rig, pose, or camera rescaling.
 m.p=(HELMET_ANCHOR+(np.asarray(m.p)-HELMET_ANCHOR)*HELMET_SCALE).tolist()
 m.n=[unit(np.array(n)/HELMET_SCALE).tolist() for n in m.n]
 return m

def write_asset(model):
 j,b=read_glb(R/'authoring/A01_BASE.glb');buf=bytearray(b);new=copy.deepcopy(j)
 # Actual head origin from the base hierarchy; no global body or actor scale change.
 parents={c:i for i,n in enumerate(j['nodes'][:25]) for c in n.get('children',[])};ws=[]
 for i,n in enumerate(j['nodes'][:25]):ws.append(np.array(n['translation'])+(ws[parents[i]] if i in parents else 0))
 po=np.array(model.p)+ws[5];no=np.array(model.n)
 def addview(raw,target=None):
  buf.extend(b'\0'*(-len(buf)%4));v={'buffer':0,'byteOffset':len(buf),'byteLength':len(raw)}
  if target:v['target']=target
  new['bufferViews'].append(v);buf.extend(raw);return len(new['bufferViews'])-1
 def acc(a,typ,ct=5126,target=None):
  arr=np.asarray(a,DT[ct]);q={'bufferView':addview(arr.tobytes(),target),'componentType':ct,'count':len(arr),'type':typ}
  if typ=='VEC3' or (typ=='SCALAR' and ct==5126):q.update(min=np.atleast_1d(arr.min(0)).tolist(),max=np.atleast_1d(arr.max(0)).tolist())
  new['accessors'].append(q);return len(new['accessors'])-1
 prim=[]
 for mt,ix in enumerate(model.indices):
  if not ix:continue
  used,ix2=np.unique(ix,return_inverse=True);n=len(used)
  attrs={'POSITION':acc(po[used],'VEC3',target=34962),'NORMAL':acc(no[used],'VEC3',target=34962),'TEXCOORD_0':acc(np.array(model.uv)[used],'VEC2',target=34962),'JOINTS_0':acc(np.tile([5,0,0,0],(n,1)),'VEC4',5123,34962),'WEIGHTS_0':acc(np.tile([1,0,0,0],(n,1)),'VEC4',target=34962),'COLOR_0':acc(np.ones((n,4)),'VEC4',target=34962)}
  prim.append({'attributes':attrs,'indices':acc(ix2,'SCALAR',5125,34963),'material':mt})
 new['meshes'][2]={'name':j['meshes'][2]['name'],'primitives':prim,'extras':{'revision':'H01','scope':'helmet only','construction':'closed continuous cranial shell with intentional eye and neck openings'}}
 new['extras']={**j.get('extras',{}),'sampleVersion':'H01','status':'A01 body with rebuilt helmet; not installed in game; awaiting visual acceptance','sourceA01SHA256':hashlib.sha256((R/'authoring/A01_BASE.glb').read_bytes()).hexdigest(),'scope':'only mesh 03 Crescent helm changed; original materials, texture, other meshes, skeleton and animations retained','checkedClips':['DesignPose'],'animationReview':'A01 keyframes retained; Idle/Run/Attack1 playback smoke checks only. Head-turn QA is documented separately, not a full animation art signoff.','helmetVertexCount':len(po),'helmetTriangles':sum(map(len,model.indices))//3}
 new['asset']['generator']='Stargazer H01: A01 baseline + continuous helmet rebuild'
 # Compact out superseded helmet buffer data; every live base accessor/image is copied byte-for-byte.
 live=set()
 for mesh in new['meshes']:
  for p in mesh['primitives']:live.update(p['attributes'].values());live.add(p['indices'])
 for skin in new['skins']:live.add(skin['inverseBindMatrices'])
 for anim in new['animations']:
  for sam in anim['samplers']:live.update([sam['input'],sam['output']])
 views=[];acs=[];compact=bytearray();vmap={};amap={}
 def copyview(i):
  if i in vmap:return vmap[i]
  v=copy.deepcopy(new['bufferViews'][i]);raw=buf[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']]
  compact.extend(b'\0'*(-len(compact)%4));v['byteOffset']=len(compact);compact.extend(raw);vmap[i]=len(views);views.append(v);return vmap[i]
 for i in sorted(live):
  a=copy.deepcopy(new['accessors'][i]);a['bufferView']=copyview(a['bufferView']);amap[i]=len(acs);acs.append(a)
 for mesh in new['meshes']:
  for p in mesh['primitives']:p['attributes']={k:amap[v] for k,v in p['attributes'].items()};p['indices']=amap[p['indices']]
 for skin in new['skins']:skin['inverseBindMatrices']=amap[skin['inverseBindMatrices']]
 for anim in new['animations']:
  for sam in anim['samplers']:sam['input']=amap[sam['input']];sam['output']=amap[sam['output']]
 for im in new['images']:im['bufferView']=copyview(im['bufferView'])
 new['accessors']=acs;new['bufferViews']=views;new['buffers']=[{'byteLength':len(compact)}]
 new['extras']['triangleCount']=sum(new['accessors'][p['indices']]['count']//3 for mesh in new['meshes'] for p in mesh['primitives'])
 new['extras']['vertexCount']=sum(new['accessors'][p['attributes']['POSITION']]['count'] for mesh in new['meshes'] for p in mesh['primitives'])
 js=json.dumps(new,separators=(',',':'),ensure_ascii=False).encode();js+=b' '*(-len(js)%4);compact.extend(b'\0'*(-len(compact)%4))
 raw=struct.pack('<III',0x46546c67,2,28+len(js)+len(compact))+struct.pack('<II',len(js),0x4e4f534a)+js+struct.pack('<II',len(compact),0x004e4942)+compact
 (R/'assets/Stargazer_H01.glb').write_bytes(raw)
 (R/'reports/helmet_parts.json').write_text(json.dumps(model.parts,indent=2))
 np.savez_compressed(R/'reports/helmet_geometry.npz',positions=po,normals=no,indices=np.asarray(np.concatenate(model.indices),dtype=np.int64),uv=model.uv)
 print('H01 GLB exported:',len(raw),'bytes; helmet',len(po),'vertices',sum(map(len,model.indices))//3,'triangles')
 return new
if __name__=='__main__':
 write_asset(make_helmet())
