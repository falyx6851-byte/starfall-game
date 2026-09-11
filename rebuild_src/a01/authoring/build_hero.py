"""Starfall / Stargazer A01. Reference-led, actual 3D surface authoring.
Run: python authoring/build_hero.py
No Blender, image-to-3D API, external assets, or image planes are used.
Geometry helper routines and the 25-joint animation donor belong to v0.1.3.
"""
from pathlib import Path
import copy, json, math, struct, io, hashlib
import numpy as np
from PIL import Image, ImageDraw
from scipy.interpolate import PchipInterpolator, CubicSpline
from scipy.spatial.transform import Rotation
from geometry import GeometryAuthor, unit, RECT
R=Path(__file__).resolve().parents[1]; TAU=math.tau

def load_glb(path):
 data=path.read_bytes(); n=struct.unpack_from('<I',data,12)[0]
 return json.loads(data[20:20+n]),data[28+n:]
def acc_read(j,b,idx):
 a=j['accessors'][idx]; bv=j['bufferViews'][a['bufferView']]; dim={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]
 return np.frombuffer(b,{5126:'<f4',5123:'<u2',5125:'<u4'}[a['componentType']],count=a['count']*dim,offset=bv.get('byteOffset',0)+a.get('byteOffset',0)).reshape(-1,dim).copy()
def make_atlas():
 # Albedo only. No permanent lighting/highlight is painted into the silver.
 cols=[(168,178,189),(155,122,70),(18,62,67),(24,28,33),(40,191,204),(192,201,208),(74,86,100)]
 out=np.empty((1024,1024,4),np.uint8)
 for k,(x0,y0,x1,y1) in enumerate(RECT):
  h,w=y1-y0,x1-x0; yy,xx=np.mgrid[:h,:w]; u=xx/(w-1);v=yy/(h-1)
  if k==2: variation=.36*np.sin(xx*math.pi/2)*np.sin(yy*math.pi/2)+.5*np.sin(u*5+v*4)
  elif k==3: variation=.35*np.sin(xx*.65)*np.sin(yy*.65)
  elif k in [0,1,5,6]: variation=.28*np.sin(yy*2.3+np.sin(xx*.035))
  else: variation=0
  out[y0:y1,x0:x1,:3]=np.clip(np.array(cols[k])+np.asarray(variation)[...,None],0,255).astype(np.uint8)
  out[y0:y1,x0:x1,3]=128
 buf=io.BytesIO();Image.fromarray(out).save(buf,'PNG',optimize=True);return buf.getvalue()

class Hero(GeometryAuthor):
 def __init__(self):
  self.old,self.oldbin=load_glb(R/'authoring/base_v013.glb');self.nodes=copy.deepcopy(self.old['nodes'][:25])
  self.parents=[-1]*25
  for i,n in enumerate(self.nodes):
   for c in n.get('children',[]):self.parents[c]=i
  self.W=[]
  for i,n in enumerate(self.nodes):self.W.append(np.array(n.get('translation',[0,0,0]),float)+(self.W[self.parents[i]] if self.parents[i]>=0 else 0))
  self.meshes={};self.active='01 Cuirass and articulated armor';self.texture=make_atlas()
 def rib(self,b,fn,m,nu=24,nv=12,thick=.018,weights=None,hint=lambda u,v:[0,0,1]):
  # Complete thickened curved shell, including back skin and closed boundary walls.
  self.surface(fn,b,m,nu,nv,weights,hint)
  def rear(u,v):return np.asarray(fn(u,v))-unit(hint(u,v))*thick
  self.surface(rear,b,6 if m==0 else m,nu,nv,weights,lambda u,v:-unit(hint(u,v)))
  for edge in range(4):
   def wall(u,v):
    a,c=([u,0],[u,1],[0,u],[1,u])[edge];return np.asarray(fn(a,c))*(1-v)+rear(a,c)*v
   # boundary weights follow original coordinate, not thickness coordinate
   if weights:
    old=self.active; mm=self.mesh();start=len(mm['p'])
   self.surface(wall,b,m,nu if edge<2 else nv,1,hint=None)
   if weights:
    end=len(mm['p']);N=nu if edge<2 else nv
    for row in range(2):
     for i in range(N+1):
      v0=0 if edge==0 else 1 if edge==1 else i/N
      ww=weights(v0);idx=start+row*(N+1)+i
      mm['j'][idx]=[j for j,w in ww]+[0]*(4-len(ww));mm['w'][idx]=[w for j,w in ww]+[0]*(4-len(ww))
 def patch(self,b,fn,m,ua,ub,va,vb,nu=16,nv=4,weights=None,hint=lambda u,v:[0,0,1],offset=.003):
  def f(u,v):
   a=ua+(ub-ua)*u;c=va+(vb-va)*v
   return np.asarray(fn(a,c))+unit(hint(a,c))*offset
  self.surface(f,b,m,nu,nv,(lambda v:weights(va+(vb-va)*v)) if weights else None,lambda u,v:hint(ua+(ub-ua)*u,va+(vb-va)*v))
 def coin(self,b,center,r,depth=.012,m=1):
  # Domed disk in XY plane, with a bevel and actual back.
  x,y,z=center
  def fn(u,v):
   a=u*TAU;return [x+math.sin(a)*r*v,y+math.cos(a)*r*v,z+.012*(1-v*v)]
  self.rib(b,fn,m,32,6,depth)
  self.surface(lambda u,v:[x+math.sin(u*TAU)*r*(.83+.10*v),y+math.cos(u*TAU)*r*(.83+.10*v),z+.004],b,1,32,2,hint=lambda u,v:[0,0,1])
 def hardplate(self,b,outline,center,m=0,thick=.02):
  # Designed planar turns. Each broad fan is a real face, not an albedo highlight.
  p=np.array(outline);c=np.array(center);W=self.W[b]
  for a,bb in zip(p,np.roll(p,-1,axis=0)):
   self.tri([c+W,a+W,bb+W],b,m)
   self.tri([a+W,bb+W,bb+W-[0,0,thick]],b,6 if m==0 else m)
   self.tri([a+W,bb+W-[0,0,thick],a+W-[0,0,thick]],b,6 if m==0 else m)
   self.tri([c+W-[0,0,thick],bb+W-[0,0,thick],a+W-[0,0,thick]],b,6 if m==0 else m)
 def save(self):
  blob=bytearray();views=[];acs=[]
  def view(data,target=None):
   blob.extend(b'\0'*(-len(blob)%4));i=len(views);q={'buffer':0,'byteOffset':len(blob),'byteLength':len(data)}
   if target:q['target']=target
   views.append(q);blob.extend(data);return i
  def acc(a,typ,ct=5126,target=None):
   a=np.asarray(a,{5126:'<f4',5123:'<u2',5125:'<u4'}[ct]);q={'bufferView':view(a.tobytes(),target),'componentType':ct,'count':len(a),'type':typ}
   if typ in ['SCALAR','VEC3'] and ct==5126:q.update(min=np.atleast_1d(a.min(axis=0)).tolist(),max=np.atleast_1d(a.max(axis=0)).tolist())
   acs.append(q);return len(acs)-1
  meshes=[]
  for name,me in self.meshes.items():
   primitives=[]
   for material,ix in enumerate(me['ix']):
    if not ix:continue
    used=sorted(set(ix));remap={v:i for i,v in enumerate(used)}
    attrs={k:acc([me[key][v] for v in used],typ,ct,34962) for k,key,typ,ct in [('POSITION','p','VEC3',5126),('NORMAL','n','VEC3',5126),('TEXCOORD_0','uv','VEC2',5126),('JOINTS_0','j','VEC4',5123),('WEIGHTS_0','w','VEC4',5126),('COLOR_0','c','VEC4',5126)]}
    primitives.append({'attributes':attrs,'indices':acc([remap[v] for v in ix],'SCALAR',5125,34963),'material':material})
   meshes.append({'name':name,'primitives':primitives})
  nodes=copy.deepcopy(self.nodes)
  for i,mesh in enumerate(meshes):nodes.append({'name':mesh['name'],'mesh':i,'skin':0})
  inv=[]
  for w in self.W:mt=np.eye(4);mt[:3,3]=-w;inv.append(mt.T.reshape(-1))
  inverse=acc(inv,'MAT4');animations=[]
  # Keep legacy timing; only the first three clips will be signed off this round.
  for an in self.old['animations']:
   out=copy.deepcopy(an)
   for sam in out['samplers']:
    ii,oo=sam['input'],sam['output'];values=acc_read(self.old,self.oldbin,oo)
    si=out['samplers'].index(sam)
    target=next((ch['target'] for ch in out['channels'] if ch['sampler']==si),{})
    if an['name'] in ['Idle','Run','Attack1'] and target.get('path')=='rotation' and target.get('node') in [22,23,24]:
     e=Rotation.from_quat(values).as_euler('XYZ');e[:,0]=abs(e[:,0])*.70
     values=Rotation.from_euler('XYZ',e).as_quat()
    sam['input']=acc(acc_read(self.old,self.oldbin,ii).flatten(),'SCALAR');sam['output']=acc(values,self.old['accessors'][oo]['type'])
   animations.append(out)
  # Explicit neutral design pose is additional to, not a replacement for gameplay clips.
  pose={7:[.025,0,.085],8:[-.07,0,0],11:[-.04,0,-.18],12:[-.10,0,0],13:[-.60,0,.48],15:[.012,0,.12],17:[0,0,-.12],19:[-.014,0,-.145],21:[0,0,.145],22:[0,0,0],23:[0,0,0],24:[0,0,0]}
  design={'name':'DesignPose','samplers':[],'channels':[]};ti=acc([0.,1.],'SCALAR')
  for idx in range(25):
   q=Rotation.from_euler('XYZ',pose.get(idx,[0,0,0])).as_quat();o=acc([q,q],'VEC4');design['samplers'].append({'input':ti,'output':o,'interpolation':'LINEAR'});design['channels'].append({'sampler':len(design['samplers'])-1,'target':{'node':idx,'path':'rotation'}})
  animations.append(design)
  params=[(.33,.88,0),(.37,.83,0),(.94,0,0),(.86,0,0),(.28,.25,.40),(.24,.92,0),(.42,.74,0)]
  names=['Moonsteel - satin silver','Antique gold - restrained trim','Deep teal - woven cloth','Black - leather and textile liner','Cyan - recessed eyes and guard gem','Honed steel - blade edge','Blued steel - recesses']
  mats=[]
  for i,(rough,metal,em) in enumerate(params):
   mat={'name':names[i],'pbrMetallicRoughness':{'baseColorFactor':[1,1,1,1],'baseColorTexture':{'index':0},'roughnessFactor':rough,'metallicFactor':metal},'doubleSided':True,'alphaMode':'OPAQUE','extras':{'emissionStrength':em}}
   if em:mat['emissiveFactor']=[.012,.17,.19]
   mats.append(mat)
  tris=sum(sum(len(ix) for ix in m['ix'])//3 for m in self.meshes.values());verts=sum(len(m['p']) for m in self.meshes.values())
  meta={'sampleVersion':'A01','status':'independent hero asset sample; not installed in playable game','reference':'approved 月影圣骑士角色立绘.png','forward':'+Z','baseVersion':'0.1.3','jointCount':25,'meshCount':len(meshes),'triangleCount':tris,'vertexCount':verts,'supplementaryDesign':['rear helmet plates and nape','back cuirass closure','hidden shoulder suspension','cape rear fold distribution and hem','leather sole and back of greaves'],'checkedClips':['DesignPose','Idle','Run','Attack1'],'otherClips':'retained from v0.1.3; no new full visual signoff','textureRole':'subtle material albedo, no baked highlights; border strips are geometry'}
  j={'asset':{'version':'2.0','generator':'Starfall reference-led hero authoring A01'},'scene':0,'scenes':[{'nodes':[0]+list(range(25,len(nodes)))}],'nodes':nodes,'meshes':meshes,'skins':[{'joints':list(range(25)),'skeleton':0,'inverseBindMatrices':inverse}],'animations':animations,'materials':mats,'images':[{'bufferView':view(self.texture),'mimeType':'image/png','name':'Hero material atlas'}],'textures':[{'sampler':0,'source':0}],'samplers':[{'magFilter':9729,'minFilter':9987,'wrapS':33071,'wrapT':33071}],'bufferViews':views,'accessors':acs,'buffers':[{'byteLength':len(blob)}],'extras':meta}
  js=json.dumps(j,separators=(',',':'),ensure_ascii=False).encode();js+=b' '*(-len(js)%4);blob+=b'\0'*(-len(blob)%4)
  raw=struct.pack('<III',0x46546c67,2,28+len(js)+len(blob))+struct.pack('<II',len(js),0x4e4f534a)+js+struct.pack('<II',len(blob),0x004e4942)+blob
  (R/'assets/Stargazer_A01.glb').write_bytes(raw);(R/'assets/stargazer_atlas.png').write_bytes(self.texture)
  meta['glbSHA256']=hashlib.sha256(raw).hexdigest();(R/'reports/asset-build.json').write_text(json.dumps(meta,indent=2,ensure_ascii=False));print(json.dumps(meta,ensure_ascii=False),flush=True)


def torso(s):
 s.active='01 Cuirass and articulated armor'
 s.shell(1,[(-.16,.22,.147,0),(.08,.238,.167,0),(.22,.207,.15,0)],3,N=32,rows=14)
 s.shell(2,[(-.2,.215,.15,0),(.00,.218,.165,0),(.21,.287,.185,-.008)],3,N=36,rows=16)
 # Breastplate: full 3D sweep, V-shaped lower termination, a raised center ridge.
 radius=PchipInterpolator([0,.20,.57,.82,1],[.216,.266,.345,.342,.287])
 depth=PchipInterpolator([0,.22,.56,.82,1],[.187,.215,.245,.224,.175])
 def cuirass(u,v):
  a=TAU*u;sa,ca=math.sin(a),math.cos(a)
  bottom=-.367+.116*abs(sa)+.065*max(-ca,0)
  top=.166-.072*abs(sa)+.019*max(-ca,0)
  y=bottom+(top-bottom)*v
  x=float(radius(v))*math.copysign(abs(sa)**.85,sa)
  z=float(depth(v))*ca*(1 if ca>0 else .82)+.032*max(ca,0)**12*math.sin(math.pi*(.12+v*.78))
  return [x,y,z]
 s.rib(3,cuirass,0,64,32,.024,hint=lambda u,v:[math.sin(TAU*u),.1,math.cos(TAU*u)])
 # Raised center chest diamond and inset shoulder-side hardware are focal accents.
 s.hardplate(3,[(0,.076,.274),(.049,-.005,.280),(0,-.132,.284),(-.049,-.005,.280)],[0,-.022,.294],1,.008)
 # A quiet embossed breast ridge continues below the gold insignia.
 s.band(3,[(0,-.134,.28),(0,-.274,.223),(0,-.344,.205)],.005,6)
 s.shell(4,[(-.07,.105,.096,0),(.066,.108,.097,-.018),(.122,.115,.103,-.015)],3,N=32,rows=10)
 # Thick hollow gorget rather than capped cone around the neck.
 def collar(u,v):
  a=u*TAU;r=.171-.024*v;return [r*math.sin(a),.143+v*(.079-.026*max(math.cos(a),0)),(.135-.013*v)*math.cos(a)-.006]
 s.rib(3,collar,0,48,8,.020,hint=lambda u,v:[math.sin(TAU*u),.12,math.cos(TAU*u)])
 s.patch(3,collar,5,0,1,.91,1,48,2,hint=lambda u,v:[math.sin(TAU*u),.12,math.cos(TAU*u)],offset=.002)
 # Two articulated abdomen lames with continuous curved fronts, not horizontal boxes.
 for k in range(2):
  def fauld(u,v):
   a=(u-.5)*math.pi*1.23;yy=.020-k*.098-.074*v-.055*(1-abs(math.sin(a)))
   return [( .221+.012*v)*math.sin(a),yy,.158*math.cos(a)+.014]
  s.rib(2,fauld,6,32,5,.018,hint=lambda u,v:[math.sin((u-.5)*math.pi*1.23),0,math.cos((u-.5)*math.pi*1.23)])
  s.patch(2,fauld,0,0,1,0,.12,32,2,offset=.002)
 s.shell(1,[(.015,.249,.185,0),(.087,.242,.182,0)],3,N=48,rows=4)
 s.plate(1,[(-.101,.098,.192),(.096,.098,.192),(.087,.007,.201),(0,-.020,.219),(-.092,.007,.201)],1,.031,.022,edge=1,rounds=0)
 for sg in [-1,1]:
  s.plate(1,[(sg*.114,.086,.193),(sg*.218,.078,.163),(sg*.224,.020,.173),(sg*.117,.019,.2)],0,.014,.008,edge=6,rounds=0)
 # Supplement: subdued back fastening; normally concealed by the cape.
 s.active='02 Backplate and hidden closures'
 for sg in [-1,1]:
  for y in [-.15,.08]:
   s.tube(3,[(sg*.22,y,-.14),(sg*.155,y+.012,-.192),(sg*.095,y+.023,-.208)],[.013,.014,.012],3,10)


def helmet(s):
 s.active='03 Crescent helm';b=5
 # A longitudinally swept crown, split at the intentional central ridge.
 # Unlike the earlier lathed skull, the brow, peak and rear have separate profiles.
 cz=np.array([-.177,-.125,-.025,.075,.145,.185])
 widths=PchipInterpolator(cz,[.070,.150,.174,.169,.142,.121])
 heights=PchipInterpolator(cz,[.15,.31,.378,.344,.238,.121])
 for half in [-1,1]:
  def crown(u,v,half=half):
   z=-.177+.362*v;w=float(widths(z));h=float(heights(z));base=.055+.035*v
   return [half*u*w,base+(h-base)*(1-max(u,0)**1.68)+.012*(1-u),z]
  s.rib(b,crown,0,26,40,.017,hint=lambda u,v:[half*u,.85,v-.5])
 s.shell(b,[(-.145,.099,.103,.005),(-.025,.142,.141,.008),(.08,.159,.157,-.004)],3,N=40,rows=14)
 # Nape and side closure supplement the unseen rear of the approved image.
 def nape(u,v):
  a=math.pi*(.40+1.2*u);return [(.109+.063*v)*math.sin(a),-.172+.295*v,-.014+(.12+.04*v)*math.cos(a)-.024*(1-v)**3]
 s.rib(b,nape,0,40,14,.017,hint=lambda u,v:[math.sin(math.pi*(.40+1.2*u)),0,math.cos(math.pi*(.40+1.2*u))])
 for sg in [-1,1]:
  # Continuous face halves with a designed cheek turn, not pyramid triangle fans.
  width=PchipInterpolator([0,.25,.63,1],[.148,.153,.116,.009])
  for lo,hi in [(0,.60),(.60,1)]:
   def visor(u,v,lo=lo,hi=hi):
    a=lo+(hi-lo)*u;vv=max(0,min(v,1));w=float(width(v))
    z=.230-.029*v-.022*min(a,.60)-.135*max(a-.60,0)+.003*math.sin(a*math.pi)*math.sin(vv*math.pi)
    return [sg*a*w,.073-.265*v+.029*a*(1-v),z]
   s.rib(b,visor,0,16,24,.018,hint=lambda u,v:[sg*.40,0,1])
  # Curved cheek return joins the faceplate to the nape, not an empty black side.
  # Its unseen attachment is a necessary complementary design.
  def cheekwrap(u,v):
   w=float(width(v));x=sg*(w*(1-u)+(.162-.030*v)*u+.020*math.sin(math.pi*u))
   y=(.102-.294*v)*(1-u)+(.094-.25*v)*u
   z=(.1628-.029*v)*(1-u)+(-.075-.005*v)*u-.020*math.sin(math.pi*u)
   return [x,y,z]
  s.rib(b,cheekwrap,0,24,24,.017,hint=lambda u,v:[sg*.8,0,.4])
  # Narrow slit in a dark recess with a substantial brow over it.
  s.band(b,[(sg*.012,.089,.221),(sg*.083,.103,.199),(sg*.158,.12,.149)],.026,3)
  s.band(b,[(sg*.017,.088,.224),(sg*.085,.104,.202),(sg*.157,.119,.153)],.010,4)
  s.band(b,[(sg*.006,.115,.224),(sg*.082,.129,.2),(sg*.171,.14,.141)],.018,0)
  s.band(b,[(sg*.008,.114,.227),(sg*.088,.13,.201),(sg*.16,.139,.155)],.006,1)
 # Slim nasal ridge ties the forehead into the mask.
 s.hardplate(b,[(-.014,.115,.227),(.014,.115,.227),(.018,-.117,.222),(0,-.20,.193),(-.018,-.117,.222)],[0,-.055,.240],0,.012)
 s.hardplate(b,[(0,.21,.17),(.028,.155,.202),(0,.115,.224),(-.028,.155,.202)],[0,.157,.207],1,.008)
 # Narrow cold-steel reinforcement follows the same crown surface.
 for half in [-1,1]:
  def spine(u,v,half=half):
   z=-.166+.331*v;h=float(heights(z));return [half*.014*u,h+.012*(1-u)+.005,z]
  s.rib(b,spine,0,3,36,.009,hint=lambda u,v:[0,1,.2])
 # Reference-defining crescent side blades. A curved, bevelled metal band in 3D.
 for sg in [-1,1]:
  def crescent(u,v):
   y=.032+.602*v
   xc=.168+.124*math.sin(math.pi*(v*.96+.04))
   wid=.095*max(math.sin(math.pi*(.10+.90*min(1,max(0,v)))),.001)**.72
   x=sg*(xc+(u-.52)*wid)
   z=-.014+.025*math.sin(v*math.pi)-.066*v+.013*math.sin(math.pi*u)
   return [x,y,z]
  s.rib(b,crescent,0,10,40,.022,hint=lambda u,v:[0,0,1])
  for ua,ub in [(0,.085),(.91,1)]:s.patch(b,crescent,1,ua,ub,0,1,2,40,offset=.003)

 # Reference proportion pass: the previous gray review made the helm too dominant.
 # Local-only edit preserves the existing Head joint and all model-space bone positions.
 me=s.mesh();scale=np.array([.83,.60,.91])
 for i,p in enumerate(me['p']):
  me['p'][i]=list(s.W[5]+(np.array(p)-s.W[5])*scale)
  me['n'][i]=list(unit(np.array(me['n'][i])/scale))


def arms(s):
 s.active='04 Arms and fitted shoulder castings'
 for sg,b in [(1,7),(-1,11)]:
  s.shell(b,[(-.35,.077,.086,0),(-.24,.105,.115,0),(-.105,.12,.122,0),(.055,.119,.118,-.012)],3,N=32,rows=18)
  # One coherent teardrop pauldron with downward outer point, closed rim.
  def cap(u,v):
   a=u*TAU;xx=(.211 if sg==1 else .195)*math.sin(a)*v
   outward=max(sg*math.sin(a)*v,0)
   zz=.183*math.cos(a)*v*(1-(.27 if sg==1 else 0)*outward**3)
   y=.149*(1-v**4)-.045*v*v-(.253 if sg==1 else .133)*outward**2.6
   return [sg*.02+xx,y,zz-.025]
  s.rib(b,cap,0,48,22,.023,hint=lambda u,v:[math.sin(u*TAU),.75,math.cos(u*TAU)])
  # Exposed side has the gold lozenge seen on the reference; mantle side is quiet.
  if sg==1:
   def inlay(u,v):
    a=.115+(u-.5)*.060*math.sin(math.pi*v);rr=.36+.54*v
    pp=np.array(cap(a,rr));pp+=unit([math.sin(TAU*a),.6,math.cos(TAU*a)])*.004
    return pp
   s.surface(inlay,b,1,8,20,hint=lambda u,v:[.5,.6,.8])
  # A single under-lame, never a fan of floating fragments.
  def lower(u,v):
   a=(u-.5)*2.30
   return [sg*(.117+.057*math.cos(a)),-.12-.11*v+.022*math.cos(a),.139*math.sin(a)-.012]
  s.rib(b,lower,6,22,5,.016,hint=lambda u,v:[sg,.1,0])
  fore,hand=b+1,b+2
  s.shell(fore,[(-.337,.068,.074,0),(-.27,.079,.094,.001),(-.12,.102,.104,-.008),(.035,.092,.09,0)],3,N=32,rows=16)
  # Vambrace extends around the arm; front ridge has thickness and broad curved planes.
  s.shell(fore,[(-.30,.079,.086,-.01),(-.225,.094,.098,-.018),(-.10,.107,.115,-.027),(.026,.084,.096,-.012)],6,N=40,rows=18,power=.86)
  for half in [-1,1]:
   def front_plate(u,v,half=half):
    w=float(PchipInterpolator([0,.3,.78,1],[.068,.096,.070,.050])(v))
    return [half*w*u,.04-.368*v+.045*(1-u)*(1-v)**4-.010*(1-u)*v**8,.094+.038*(1-u)+.006*math.sin(v*math.pi)]
   s.rib(fore,front_plate,0,12,22,.023,hint=lambda u,v:[half*.45,0,.9])
  # Elbow couter shields the hinge, neither spherical nor spiky.
  s.plate(fore,[(-.08,.057,.052),(0,.097,.072),(.075,.039,.068),(.095,-.016,.075),(0,-.061,.11),(-.093,-.012,.079)],0,.021,.019,edge=6,rounds=1)
  s.shell(fore,[(-.323,.076,.081,0),(-.298,.080,.085,0)],0,N=32,rows=3)
  # Sculpted palm with actual fingers wrapping the weapon-side grip.
  s.shell(hand,[(-.122,.052,.046,-.021),(-.08,.070,.06,-.009),(-.021,.075,.061,-.009),(.025,.064,.058,-.002)],3,N=28,rows=12)
  s.plate(hand,[(-.062,.001,.045),(.062,.001,.045),(.069,-.054,.053),(.052,-.106,.051),(-.05,-.11,.047),(-.069,-.049,.052)],0,.012,.009,edge=6,rounds=1)
  for k in range(4):
   yy=-.021-k*.028
   if b==11:
    pts=[(-.054,yy,.015),(-.053,yy,.059),(-.025,yy,.087),(.02,yy,.080),(.038,yy,.048)]
   else:
    xx=-.052+k*.031;pts=[(xx,-.078,.005),(xx,-.119,.027),(xx,-.159,.041),(xx,-.173,.018)]
   s.tube(hand,pts,[.015]*len(pts),3,10)
   if b==11:s.plate(hand,[(-.043,yy+.009,.079),(-.016,yy+.009,.090),(-.014,yy-.011,.090),(-.04,yy-.011,.079)],6,.005,.003,edge=6,rounds=0)
  s.tube(hand,[(.065,-.004,.019),(.084,-.038,.037),(.052,-.081,.057),(.014,-.087,.066)],[.022,.021,.018,.015],3,12)


def legs(s):
 s.active='05 Long greaves, knee plates and sabatons'
 for th,sh,ft,sg in [(15,16,17,1),(19,20,21,-1)]:
  L=-s.nodes[sh]['translation'][1];S=-s.nodes[ft]['translation'][1]
  s.shell(th,[(-L+.015,.075,.077,0),(-.36,.095,.112,-.008),(-.18,.116,.124,-.005),(.05,.127,.127,0)],3,N=36,rows=22)
  # Curved cuisse with a narrow medial ridge and volumetric side return.
  s.shell(th,[(-L+.105,.085,.098,0),(-.30,.124,.133,-.004),(-.14,.137,.147,-.006),(.032,.125,.129,0)],0,N=36,rows=20)
  s.plate(th,[(-.104,.018,.13),(.107,.018,.13),(.121,-.191,.141),(.073,-L+.091,.113),(0,-L+.055,.148),(-.078,-L+.09,.108),(-.124,-.18,.142)],0,.027,.038,edge=0,rounds=1)
  s.shell(sh,[(-S+.015,.064,.074,-.004),(-S+.1,.073,.086,-.009),(-.245,.103,.123,-.035),(-.105,.107,.113,-.026),(.045,.092,.098,0)],0,N=40,rows=24,power=.87)
  # Tall wraparound front greave, purposefully angular at the shin.
  def greave(u,v):
   a=(u-.5)*math.pi*1.36
   y=-.495+.457*v+.025*(1-abs(math.sin(a)))*(1-v)
   rx=.064+.033*math.sin(v*math.pi*.84);rz=.084+.039*math.sin(v*math.pi*.83)
   return [rx*math.sin(a),y,rz*math.cos(a)-.012+.027*max(math.cos(a),0)**10]
  s.rib(sh,greave,0,36,24,.022,hint=lambda u,v:[math.sin((u-.5)*math.pi*1.36),0,math.cos((u-.5)*math.pi*1.36)])
  s.hardplate(sh,[(-.100,.035,.102),(0,.129,.105),(.1,.035,.102),(.096,-.035,.113),(0,-.143,.151),(-.094,-.036,.115)],[0,-.018,.178],0,.028)
  s.hardplate(sh,[(-.053,-.079,.123),(0,-.152,.15),(.058,-.083,.122),(0,-.188,.120)],[0,-.131,.164],6,.012)
  # Foot shell swept along the length. Pointed sabaton, not a rounded boot primitive.
  boot_w=PchipInterpolator([0,.20,.41,.65,.86,1],[.061,.083,.091,.077,.047,.005])
  boot_h=PchipInterpolator([0,.22,.42,.65,.86,1],[.108,.161,.148,.074,.041,.012])
  def boot(u,v):
   z=-.112+.456*v;a=(u-.5)*math.pi
   width=float(boot_w(v));top=float(boot_h(v))
   return [width*math.copysign(abs(math.sin(a))**.86,math.sin(a)),.007+top*max(0,1-abs(math.sin(a))**1.33),z]
  s.rib(ft,boot,0,32,26,.017,hint=lambda u,v:[math.sin((u-.5)*math.pi),.7,.1])
  # Discrete sole perimeter follows the same last.
  def sole(u,v):
   # Match the upper's pointed last; an oval sole would visually erase the toe.
   t=u*2 if u<.5 else 2-u*2;sg0=1 if u<.5 else -1
   return [sg0*(float(boot_w(t))+.003),-.032+.040*v,-.112+.456*t]

  s.rib(ft,sole,3,40,3,.008,hint=lambda u,v:[math.sin(u*TAU),0,math.cos(u*TAU)])
  for vv in [.40,.61]:s.patch(ft,boot,6,0,1,vv,vv+.016,32,1,hint=lambda u,v:[0,1,0],offset=.004)
  # Broad side tasset, following the thigh so it does not shear through the pelvis.
  s.active='06 Hip tassets'
  s.plate(th,[(-.128,.11,.153),(.107,.107,.155),(.162,-.016,.161),(.100,-.275,.156),(-.017,-.326,.161),(-.126,-.155,.164)],0,.033,.028,edge=0,rounds=0)
  s.band(th,[(sg*.07,-.262,.184),(sg*.014,-.302,.182)],.01,1)
  s.active='05 Long greaves, knee plates and sabatons'


def cloth(s):
 s.active='07 Deep teal cape - weighted rear';b=22
 def cape(u,v):
  vv=max(v,0);w=.278+.352*vv**.77
  x=(2*u-1)*w-.036+.065*math.sin(math.pi*v)
  hem=.045*math.cos(u*math.pi*2+.3)+.037*u
  y=.013-1.785*v+hem*v**10
  z=.007-.294*v-.13*v*v+(.012+.055*v)*math.cos(u*math.pi*7-.3)+.022*v*math.sin(u*math.pi*2)
  return [x,y,z]
 def weights(v):
  t=min(max(v,0)*2,1.999999);i=int(t);f=t-i;f=f*f*(3-2*f);return [(22+i,1-f),(23+i,f)]
 s.rib(b,cape,2,56,38,.009,weights,lambda u,v:[0,0,-1])
 for ua,ub in [(0,.018),(.982,1)]:s.patch(b,cape,1,ua,ub,0,1,2,38,weights,lambda u,v:[0,0,-1],.005)
 s.patch(b,cape,1,0,1,.966,.98,56,2,weights,lambda u,v:[0,0,-1],.005)
 # Two large, sparse hem glyphs. Supplementary embroidery, not an inferred back illustration.
 for uc in [.14,.86]:
  def glyph(u,v,uc=uc):return cape(uc+(u-.5)*.065,.88+v*.048-abs(u-.5)*.035)
  s.surface(lambda u,v:np.array(glyph(u,v))+[0,0,-.01],b,1,8,2,lambda v:weights(.89),hint=lambda u,v:[0,0,-1])
 # The sword-side mantle is an actual draped shoulder wrap, not painted green armor.
 s.active='08 Asymmetric shoulder mantle';b=11
 def mantle(u,v):
  # Tailored cloth from the inner collar over the shoulder to a free outside hem.
  # Four corners define a garment, instead of revolving a bell around the arm.
  x=.186-.490*u
  z=(2*v-1)*(.154+.103*math.sin(math.pi*(.10+.8*u)))-.026
  y=.265-.070*u-.215*u**3-(.130+.070*u)*abs(2*v-1)**1.7
  y+=(.020+.015*u)*math.sin(u*math.pi*3+.25*(2*v-1))*math.sin(math.pi*v)
  z+=.008*math.sin(u*math.pi*4)*math.sin(v*math.pi)
  return [x,y,z]
 s.rib(b,mantle,2,46,34,.009,hint=lambda u,v:[-.30,.82,(2*v-1)*.5])
 s.patch(b,mantle,1,0,1,0,.020,46,2,hint=lambda u,v:[-.25,.6,-.8],offset=.004)
 s.patch(b,mantle,1,.974,.998,0,1,2,34,hint=lambda u,v:[-.7,.5,.1],offset=.004)
 s.patch(b,mantle,1,0,1,.98,1,46,2,hint=lambda u,v:[-.25,.6,.8],offset=.004)
 # Neckline follows the chest; the free shoulder hem follows the upper arm.
 # Sharing weights prevents the whole mantle from behaving as a rigid shoulder pad.
 mm=s.mesh()
 for i,pp in enumerate(mm['p']):
  uu=max(0,min(1,(.186-(pp[0]-s.W[11][0]))/.490))
  f=.035+.82*(uu*uu*(3-2*uu))
  mm['j'][i]=[3,11,0,0];mm['w'][i]=[1-f,f,0,0]
 # Silver/gold brooch at chest-side attachment, clean enough to read from above.
 s.active='01 Cuirass and articulated armor'
 s.coin(3,[-.246,.135,.194],.052,.016,1)
 s.hardplate(3,[(-.246,.168,.213),(-.22,.134,.221),(-.246,.102,.213),(-.271,.134,.219)],[-.246,.134,.227],1,.006)
 s.coin(3,[.248,.104,.180],.029,.011,1)
 # Paired front falls with large folds, independently weighted toward each thigh.
 s.active='09 Split tabard'
 for sg,th in [(-1,19),(1,15)]:
  def tab(u,v):
   x=sg*(.012+.113*u)*(1+.14*v)
   y=.016-.71*v+.025*u*v**9
   z=.208+.105*v+.020*math.cos(u*math.pi*2+.2)*v
   return [x,y,z]
  def wt(v):f=.65*max(0,min(v,1))**1.6;return [(1,1-f),(th,f)]
  s.rib(1,tab,2,18,24,.008,wt,lambda u,v:[0,0,1])
  for ua,ub in [(0,.044),(.94,1)]:s.patch(1,tab,1,ua,ub,0,1,2,24,wt,lambda u,v:[0,0,1],.003)
  s.patch(1,tab,1,0,1,.948,.965,18,2,wt,lambda u,v:[0,0,1],.003)


def sword(s):
 s.active='10 Straight moon-guard sword';b=13
 # Grip and glove share exactly the same hand joint and reference center.
 zc=.036
 s.shell(b,[(-.131,.031,.031,zc),(.136,.031,.031,zc)],3,N=20,rows=12)
 for k in range(7):s.shell(b,[(-.107+k*.034,.0325,.0325,zc),(-.102+k*.034,.0325,.0325,zc)],6,N=20,rows=1)
 s.shell(b,[(.135,.035,.032,zc),(.16,.052,.043,zc),(.22,.046,.039,zc),(.242,.018,.020,zc)],1,N=16,rows=10)
 # Crescent guard is forged 3D volume with front/back planes and edge taper.
 for sg in [-1,1]:
  def guard(u,v):
   xx=sg*(.036+.299*v)
   yc=-.182+.178*max(v,0)**2.2
   wid=.061*max(1-v,0)**.57+.002
   y=yc+(u-.5)*wid*1.5
   z=zc+.029*(1-v*.82)+.006*math.sin(u*math.pi)
   return [xx,y,z]
  s.rib(b,guard,1,8,30,.045,hint=lambda u,v:[0,0,1])
  s.patch(b,guard,1,0,.09,0,1,2,30,offset=.006)
 s.hardplate(b,[(-.070,-.145,zc+.047),(.065,-.145,zc+.047),(.074,-.252,zc+.049),(0,-.273,zc+.052),(-.072,-.247,zc+.049)],[0,-.20,zc+.062],1,.087)
 s.hardplate(b,[(0,-.158,zc+.068),(.034,-.202,zc+.071),(0,-.247,zc+.068),(-.034,-.202,zc+.071)],[0,-.202,zc+.080],4,.008)
 # Straight, long, tapering blade. Real central ridge, broad blade planes, honed bevel.
 rings=[(-.253,.069),(-.327,.074),(-.91,.061),(-1.223,.045),(-1.405,.001)]
 for (y,w),(yy,ww) in zip(rings,rings[1:]):
  for front in [-1,1]:
   for sg in [-1,1]:
    cols=[(0,.027),(.14,.026),(.75,.016),(1,.001)]
    for k,((u,z),(uu,zz)) in enumerate(zip(cols,cols[1:])):
     pts=[s.W[b]+[sg*w*u,y,zc+front*z],s.W[b]+[sg*w*uu,y,zc+front*zz],s.W[b]+[sg*ww*uu,yy,zc+front*zz],s.W[b]+[sg*ww*u,yy,zc+front*z]]
     mat=6 if k==0 else 0 if k==1 else 5
     s.tri(pts[:3],b,mat);s.tri([pts[0],pts[2],pts[3]],b,mat)

if __name__=='__main__':
 s=Hero()
 for fn in [torso,helmet,arms,legs,cloth,sword]:
  print('Authoring',fn.__name__,flush=True);fn(s)
 s.save()
