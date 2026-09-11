"""M03 BASE COVERAGE ONLY.
Read H01's real pauldron faces, deform to DesignPose/0, build a plain sheet
outside the full shoulder envelope, then invert its own blend skin matrix to
write bind-space coordinates. No border, decorative folds or new textures.
Run from any directory: python authoring/build_mantle.py
"""
from pathlib import Path
import json, math, hashlib
import numpy as np
from scipy.spatial import ConvexHull
from scipy.interpolate import CubicSpline
from glb_io import read_glb,acc,mesh_arrays,bone_matrices,skin_positions,unskin_positions,replace_mesh
R=Path(__file__).resolve().parents[1]
TAU=math.tau

def unit(v):
 a=np.asarray(v,float);return a/np.maximum(np.linalg.norm(a,axis=-1,keepdims=True),1e-12)
def smooth(t):t=np.clip(t,0,1);return t*t*(3-2*t)

def sources():
 j,b=read_glb(R/'authoring/H01_BASE.glb');B=bone_matrices(j,b,'DesignPose',0)
 ar=mesh_arrays(j,b,3);f=ar['f']
 sel=(ar['j'][f,0]==11).all(1)&(ar['w'][f,0]>.999).all(1)&(ar['mat']==0)
 # All silver pauldron outer skin and its rim; exclude forearm, hand and opposite shoulder.
 f=f[sel];pp=skin_positions(ar['p'],ar['j'],ar['w'],B);points=pp[np.unique(f)]
 cu=mesh_arrays(j,b,0,materials=[1]);p=cu['p'];mask=(p[:,0]<-.18)&(p[:,0]>-.32)&(p[:,1]>1.92)&(p[:,2]>.15)
 lo=p[mask].min(0);hi=p[mask].max(0);clasp=(lo+hi)/2;clasp[2]=lo[2]+.016
 # Coin is rigidly attached to Chest in H01; this is its real rear mounting surface.
 clasp=(B[3]@np.r_[clasp,1])[:3]
 hull=ConvexHull(points);hull2=ConvexHull(points[:,[0,2]])
 return j,b,B,points,hull,hull2,clasp,dict(selectedPauldronTriangles=int(len(f)),claspBindBounds=[lo.tolist(),hi.tolist()],claspDesign=clasp.tolist(),pauldronDesignBounds=[points.min(0).tolist(),points.max(0).tolist()])

def build():
 j,b,B,pts,hull,hull2,clasp,info=sources()
 # Centre derives from the actual top surface, not the shoulder joint origin.
 top=pts[pts[:,1]>pts[:,1].max()-.018]
 C=top.mean(0);C[1]=pts[:,1].max()
 E=hull.equations;E2=hull2.equations
 clearance=.014
 def roof(x,z):
  n=E[:,:3];d=E[:,3];sel=n[:,1]>.015
  return np.min((clearance-d[sel]-n[sel,0]*x-n[sel,2]*z)/n[sel,1])
 def rad(a):
  d=np.array([math.cos(a),math.sin(a)]);D=E2[:,:2]@d;ok=D>1e-7
  return np.min((-E2[ok,2]-E2[ok,:2]@C[[0,2]])/D[ok])
 # Mostly vertical free hem: one smooth, undecorated curve round the garment.
 # Near the fixed front brooch the hem lifts to the attachment; back seam joins the old cape.
 ac=math.atan2(clasp[2]-C[2],clasp[0]-C[0])%TAU
 rc=np.linalg.norm(clasp[[0,2]]-C[[0,2]])
 # medial (+X), actual brooch, front (+Z), outer (-X), rear (-Z)
 angles=np.array([0,ac,1.55,2.15,math.pi,3.95,4.72,5.52,TAU])
 ys=np.array([1.98,clasp[1],1.775,1.71,1.70,1.715,1.755,1.972,1.98])
 hem_y=CubicSpline(angles,ys,bc_type='periodic')
 # Target radii on medial/cape seam; outward side uses complete footprint (not a centreline).
 medial=lambda a:max(math.cos(a),0)**3
 def boundary(a):
  base=rad(a)+.013
  r=base
  dc=abs((a-ac+math.pi)%TAU-math.pi)
  aweight=math.exp(-(dc/.28)**2)
  r=r*(1-aweight)+rc*aweight
  # mild medial clipping protects the unchanged neck/gorget.
  r=r*(1-.30*medial(a)) + .17*.30*medial(a)
  if dc<1e-6:r=rc
  y=float(hem_y(a))
  return r,y
 def profile(a,t):
  dx,dz=math.cos(a),math.sin(a);rfull=rad(a);rhem,yhem=boundary(a)
  # contact region follows the offset FULL 3D envelope; the drape only starts outside it.
  rstart=rfull*.76
  ystart=roof(C[0]+dx*rstart,C[2]+dz*rstart)
  r_end=max(rhem,rstart+.01)
  # Two constraints blended continuously in azimuth: supported roof vs lifted neckline.
  # A hard switch here would create a crease/triangular tongue beside the brooch.
  ri=rhem*t
  yi=max((C[1]+clearance)*(1-t*t)+yhem*t*t,roof(C[0]+dx*ri,C[2]+dz*ri))
  if t<=.67:
   rr=rstart*t/.67;y=roof(C[0]+dx*rr,C[2]+dz*rr)
  else:
   u=(t-.67)/.33
   deriv=(roof(C[0]+dx*(rstart+.001),C[2]+dz*(rstart+.001))-ystart)/.001
   d1=min(.035,(r_end-rstart)*.55)
   p0=np.array([rstart,ystart]);p1=p0+[d1,deriv*d1]
   p3=np.array([r_end,yhem]);p2=p3+[0,min(.065,max(.003,(ystart-yhem)*.40))]
   q=(1-u)**3*p0+3*(1-u)**2*u*p1+3*(1-u)*u*u*p2+u**3*p3
   rr,y=q
  lift=smooth((yhem-ystart+.075)/.13)
  rr=(1-lift)*rr+lift*ri;y=(1-lift)*y+lift*yi
  if rr<rfull+.010:y=max(y,roof(C[0]+dx*rr,C[2]+dz*rr))
  return np.array([C[0]+dx*rr,y,C[2]+dz*rr])
 # Angular sampling includes the exact brooch direction to make the fixed point reproducible.
 A=np.sort(np.r_[np.arange(88)*TAU/88,ac]);V=np.linspace(0,1,37)
 # Pole shared, avoiding collapsed degenerate triangles.
 P=[np.array([C[0],C[1]+clearance,C[2]])];UV=[[.5,0]];polar=[[0,0]]
 for v in V[1:]:
  for a in A:P.append(profile(a,float(v)));UV.append([a/TAU,float(v)]);polar.append([a,float(v)])
 P=np.array(P);polar=np.array(polar);N=len(A);F=[]
 for i in range(N):F.append([0,1+i,1+(i+1)%N])
 for r in range(len(V)-2):
  for i in range(N):
   a=1+r*N+i;c=1+(r+1)*N+i;bb=1+r*N+(i+1)%N;d=1+(r+1)*N+(i+1)%N
   F.extend([[a,c,bb],[bb,c,d]])
 F=np.array(F,int)
 # Consistent outward winding from the chosen parameterization.
 if np.cross(P[F[0,1]]-P[F[0,0]],P[F[0,2]]-P[F[0,0]])[1]<0:F=F[:,[0,2,1]]
 norm=np.zeros_like(P);fn=np.cross(P[F[:,1]]-P[F[:,0]],P[F[:,2]]-P[F[:,0]])
 for k in range(3):np.add.at(norm,F[:,k],fn)
 norm=unit(norm)
 # The contact area follows the SAME Arm.R matrix as the unchanged armor.
 # Only the small medial attachment patch blends to the stationary chest coin.
 dist=np.linalg.norm(P-clasp,axis=1)
 chestw=1-smooth((dist-.028)/.095)
 # small back shoulder seam can remain arm-driven for now, rather than inventing a new fixed pin.
 J=np.tile([11,3,0,0],(len(P),1));W=np.c_[1-chestw,chestw,np.zeros((len(P),2))]
 anchor_idx=1+(len(V)-2)*N+np.argmin(abs(A-ac));P[anchor_idx]=clasp;W[anchor_idx]=[0,1,0,0]
 # Actual inner cloth thickness, plain edge, no gold geometry.
 thickness=.004
 inner=P-norm*thickness;allP=np.r_[P,inner];allJ=np.r_[J,J];allW=np.r_[W,W];allN=np.r_[norm,-norm]
 NF=len(P);allF=list(F)+list(F[:,[0,2,1]]+NF)
 edge=1+(len(V)-2)*N+np.arange(N)
 for i in range(N):
  a=edge[i];bb=edge[(i+1)%N];allF.extend([[a,bb+NF,bb],[a,a+NF,bb+NF]])
 allF=np.array(allF)
 bind=unskin_positions(allP,allJ,allW,B)
 blend=np.sum(B[allJ]*allW[...,None,None],axis=1)
 # Original shader multiplies normals by mat3(skin); use its inverse for this asset's bind normals.
 bindN=unit(np.linalg.solve(blend[:,:3,:3],allN[...,None])[:,:,0])
 uv=np.asarray(UV);uv=np.c_[(5+uv[:,0]*502)/1024,(517+uv[:,1]*502)/1024];uv=np.r_[uv,uv]
 # Constant dye from the original cloth atlas. No added texture/color/material or renderer changes.
 meta={'revision':'M03','stage':'plain base coverage only; no trim and no decorative folds','constructionSpace':'H01 DesignPose at 0 seconds; inverse blended skinning to bind space','shoulderSource':'all mantle-side silver pauldron triangles of mesh 04, rigid Arm.R','clearance':clearance,'thickness':thickness,'anchorVertex':int(anchor_idx),'outerVertexCount':len(P),'materialPolicy':'existing material 2; viewer defaults to original clay mode','contactWeights':'Arm.R rigid on contact surface, local Chest blend at clasp only'}
 new=replace_mesh(R/'authoring/H01_BASE.glb',R/'assets/Stargazer_M03.glb',bind,bindN,allJ,allW,uv,allF,meta)
 np.savez_compressed(R/'reports/mantle_authoring.npz',design_positions=allP,bind_positions=bind,normals_design=allN,indices=allF,weights=allW,joints=allJ,outer_indices=F,polar=polar,edge=edge,anchor=clasp,center=C)
 info.update(constructionSpace='DesignPose0',profileAngles=A.tolist(),contactClearance=clearance,thickness=thickness,rigTransforms={'Chest':B[3].tolist(),'Arm.R':B[11].tolist()},scope='mesh 7 only',anchorVertex=int(anchor_idx),sourceSHA256=hashlib.sha256((R/'authoring/H01_BASE.glb').read_bytes()).hexdigest())
 (R/'reports/construction.json').write_text(json.dumps(info,indent=2))
 print('M03 plain shell',len(bind),'vertices',len(allF),'triangles; anchor',clasp,flush=True)
 return new
if __name__=='__main__':build()
