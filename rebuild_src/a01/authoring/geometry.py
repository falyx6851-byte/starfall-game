"""Small geometry-authoring utilities adapted from the project's v0.1.3 builder.
Only the utility routines are reused. New hero surfaces are authored in build_hero.py.
"""
from pathlib import Path
import math, copy, json, struct, io
import numpy as np
from scipy.interpolate import PchipInterpolator, CubicSpline
TAU=math.tau
RECT=[(0,0,512,512),(512,0,1024,512),(0,512,512,1024),(512,512,768,768),(768,512,1024,768),(512,768,768,1024),(768,768,1024,1024)]
def unit(v):
 v=np.asarray(v,float);return v/max(np.linalg.norm(v),1e-10)
class GeometryAuthor:
 def mesh(self):
  if self.active not in self.meshes:self.meshes[self.active]={'p':[],'n':[],'uv':[],'j':[],'w':[],'c':[],'ix':[[] for _ in RECT]}
  return self.meshes[self.active]
 def vertex(self,p,n,b,m,uv=(.5,.5),weights=None,shade=1):
  t=self.mesh();idx=len(t['p']);x0,y0,x1,y1=RECT[m];u,v=np.clip(uv,0,1);pad=5
  t['p'].append(list(p));t['n'].append(list(unit(n)));t['uv'].append([(x0+pad+u*(x1-x0-2*pad))/1024,(y0+pad+v*(y1-y0-2*pad))/1024])
  ww=weights or [(b,1)];ww=[(j,w) for j,w in ww if w>1e-7];ss=sum(w for j,w in ww)
  t['j'].append([j for j,w in ww]+[0]*(4-len(ww)));t['w'].append([w/ss for j,w in ww]+[0]*(4-len(ww)));t['c'].append([shade,shade,shade,1]);return idx
 def face(self,ids,m):
  t=self.mesh();a,b,c=[np.array(t['p'][i]) for i in ids];n=np.sum([t['n'][i] for i in ids],axis=0)
  if np.linalg.norm(np.cross(b-a,c-a))<1e-10:return
  if np.dot(np.cross(b-a,c-a),n)<0:ids=[ids[0],ids[2],ids[1]]
  t['ix'][m].extend(ids)
 def tri(self,pts,b,m,uvs=None,ns=None):
  a,bb,c=[np.array(p) for p in pts];n=unit(np.cross(bb-a,c-a));ids=[]
  for k,p in enumerate(pts):ids.append(self.vertex(p,ns[k] if ns is not None else n,b,m,uvs[k] if uvs else (.25+(k%2)*.5,.25+(k//2)*.5)))
  self.face(ids,m)
 def surface(self,fn,b,m,nu=28,nv=12,weights=None,hint=None,shade=None):
  ids=[];off=self.W[b];eps=.00005
  for j in range(nv+1):
   row=[];v=j/nv
   for i in range(nu+1):
    u=i/nu;p=np.array(fn(u,v),float);du=np.array(fn(u+eps,v))-fn(u-eps,v);dv=np.array(fn(u,v+eps))-fn(u,v-eps);nn=unit(np.cross(du,dv))
    if hint is not None and np.dot(nn,hint(u,v))<0:nn=-nn
    if np.linalg.norm(nn)<.1:nn=unit(hint(u,v) if hint else [0,1,0])
    row.append(self.vertex(p+off,nn,b,m,(u,v),weights(v) if weights else None,shade(u,v) if shade else 1))
   ids.append(row)
  for j in range(nv):
   for i in range(nu):self.face([ids[j][i],ids[j][i+1],ids[j+1][i+1]],m);self.face([ids[j][i],ids[j+1][i+1],ids[j+1][i]],m)
 def shell(self,b,rings,m=0,N=32,rows=16,power=1,ridge=0,center=(0,0,0),cap=True,weights=None):
  # Cross-sections are art-directed profiles. PCHIP creates continuous curvature,
  # not flat rows with smoothing used to conceal a cylindrical silhouette.
  rr=np.array(rings,float);ys=rr[:,0];f=PchipInterpolator(ys,rr[:,1:],axis=0);y0,y1=ys[0],ys[-1];cen=np.array(center)
  def fn(u,v):
   y=y0+(y1-y0)*v;rx,rz,zc=f(y);a=TAU*u;s,c=math.sin(a),math.cos(a)
   return cen+[rx*math.copysign(abs(s)**power,s),y,zc+rz*math.copysign(abs(c)**power,c)+ridge*max(c,0)**8]
  self.surface(fn,b,m,N,rows,weights,hint=lambda u,v:[math.sin(u*TAU),0,math.cos(u*TAU)])
  if cap:
   for v,n in [(0,[0,-1,0]),(1,[0,1,0])]:
    ring=[np.array(fn(i/N,v))+self.W[b] for i in range(N)];c=np.mean(ring,axis=0)
    for i in range(N):self.tri([c,ring[i],ring[(i+1)%N]],b,m,ns=[n]*3)
 def plate(self,b,outline,m=0,depth=.04,crown=.045,edge=5,rounds=1):
  # Convex rounded armor plate. Crown and bevel are separate continuous surfaces.
  out=np.array(outline,float)
  if len(out)>=4:
   plane=np.linalg.lstsq(np.c_[out[:,:2],np.ones(len(out))],out[:,2],rcond=None)[0];out[:,2]=np.c_[out[:,:2],np.ones(len(out))]@plane
  for _ in range(rounds):out=np.array([q for a,bb in zip(out,np.roll(out,-1,axis=0)) for q in [.82*a+.18*bb,.18*a+.82*bb]])
  c=out.mean(axis=0);N=len(out);curve=CubicSpline(np.arange(N+1),np.vstack([out,out[0]]),bc_type='periodic')
  def fn(u,v):
   pp=curve((u%1)*N);return c+(pp-c)*v+[0,0,crown*(1-v*v)]
  # Analytic interpolation across outline; normal smoothing around large curved faces.
  self.surface(fn,b,m,N,12,hint=lambda u,v:[0,0,1])
  # Solid perimeter and honed bevel ring, darker backs.
  for i in range(N):
   a=out[i]+self.W[b];bb=out[(i+1)%N]+self.W[b];ai=c+(out[i]-c)*.948+self.W[b]+[0,0,.018];bi=c+(out[(i+1)%N]-c)*.948+self.W[b]+[0,0,.018]
   self.tri([a,bb,bi],b,edge);self.tri([a,bi,ai],b,edge)
   backa=a-[0,0,depth];backb=bb-[0,0,depth];self.tri([a,backa,backb],b,m);self.tri([a,backb,bb],b,m)
   self.tri([backb,backa,c+self.W[b]-[0,0,depth]],b,6)
 def band(self,b,points,width,m=1):
  for a,bb in zip(points,points[1:]):
   a,bb=np.array(a)+self.W[b],np.array(bb)+self.W[b];d=unit(np.cross(bb-a,[0,0,1]))*width/2
   self.tri([a-d,bb-d,bb+d],b,m);self.tri([a-d,bb+d,a+d],b,m)
 def tube(self,b,points,radii,m=1,sides=12):
  pts=np.array(points);rings=[]
  for i,(p,r) in enumerate(zip(pts,radii)):
   tangent=unit(pts[min(i+1,len(pts)-1)]-pts[max(i-1,0)]);ax=unit(np.cross(tangent,[0,0,1]));by=unit(np.cross(tangent,ax));rings.append([p+r*(math.cos(a)*ax+math.sin(a)*by) for a in np.arange(sides)*TAU/sides])
  for i in range(len(rings)-1):
   for k in range(sides):
    kk=(k+1)%sides;a,bb,c,d=[p+self.W[b] for p in [rings[i][k],rings[i][kk],rings[i+1][kk],rings[i+1][k]]];self.tri([a,bb,c],b,m);self.tri([a,c,d],b,m)
