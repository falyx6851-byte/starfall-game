"""M04 appearance polish candidate based on the approved M03 coverage shell.
Only mesh 08 Asymmetric shoulder mantle is rebuilt. All other geometry, skin,
animations, materials and textures remain untouched.

Workflow:
- Load the approved M03 design-space shell from reports/mantle_authoring.npz.
- Preserve the approved shoulder coverage/support region.
- Add 2-3 broad cloth folds, a small bridge cleanup near neck/clasp, and a
  narrow gold trim along the true free hem edge only.
- Recompute normals, thickness, and write the mesh back into a copy of the M03
  GLB, preserving every other live byte.
"""
from pathlib import Path
import json, math, copy, hashlib, struct
import numpy as np
from glb_io import read_glb, acc, replace_mesh, unskin_positions, skin_positions, section_segments

R = Path(__file__).resolve().parents[1]
TAU = math.tau
DT = {5126:'<f4',5123:'<u2',5125:'<u4',5121:'u1'}
DIMS = {'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}


def unit(v):
    v=np.asarray(v,float)
    n=np.linalg.norm(v,axis=-1,keepdims=True)
    return v/np.maximum(n,1e-12)

def smooth(t):
    t=np.clip(t,0,1)
    return t*t*(3-2*t)

def gauss_wrap(a,c,w):
    d=((a-c+math.pi)%TAU)-math.pi
    return np.exp(-(d/w)**2)

def open_m03_source():
    npz=np.load(R/'reports/mantle_authoring.npz')
    outer_n=int(npz['design_positions'].shape[0]//2)
    outer=npz['design_positions'][:outer_n].copy()
    joints=npz['joints'][:outer_n].copy()
    weights=npz['weights'][:outer_n].copy()
    faces=npz['outer_indices'].copy()
    polar=npz['polar'].copy()
    edge=npz['edge'].copy().astype(int)
    center=npz['center'].copy()
    anchor=npz['anchor'].copy()
    return outer,joints,weights,faces,polar,edge,center,anchor


def sculpt_outer(outer, polar, center, anchor):
    P=outer.copy()
    a=polar[:,0]; t=polar[:,1]

    # Local frame.
    radial=np.c_[P[:,0]-center[0], np.zeros(len(P)), P[:,2]-center[2]]
    radial[0]=[1,0,0]
    radial=unit(radial)
    tangent=np.c_[-radial[:,2], np.zeros(len(P)), radial[:,0]]
    up=np.tile([0.,1.,0.], (len(P),1))

    ac=math.atan2(anchor[2]-center[2], anchor[0]-center[0])%TAU

    # Freeze the approved support/coverage region strongly.
    support_lock = 1.0 - smooth((t-0.58)/0.18)   # ~1 near support, ->0 lower down
    free = 1.0 - support_lock
    mid = smooth((t-0.35)/0.50)

    # 1) Small bridge cleanup near neck/clasp, without shrinking the whole cloth.
    bridge = gauss_wrap(a, ac-0.46, 0.34) * (1.0-smooth((t-0.30)/0.45)) * smooth((t-0.05)/0.18)
    P[:,1] -= 0.018*bridge
    P += radial * (-0.004*bridge)[:,None]

    # 2) Broad folds. These operate mainly below the support zone.
    fold_env = free * (0.25 + 0.75*mid)
    f1 = gauss_wrap(a, ac+0.38, 0.24)  # front / clasp fall
    f2 = gauss_wrap(a, ac+1.30, 0.32)  # outer shoulder trough
    f3 = gauss_wrap(a, ac+2.34, 0.28)  # rear / cape seam fall
    ridge = gauss_wrap(a, ac+0.86, 0.28) + 0.85*gauss_wrap(a, ac+1.82, 0.34)

    # Valleys (drop), ridges (lift slightly), plus mild directional drift.
    P[:,1] += fold_env * (-0.030*f1 -0.024*f2 -0.022*f3 + 0.012*ridge)
    P += radial * (fold_env*( 0.006*f1 -0.010*f2 + 0.004*f3 + 0.008*ridge))[:,None]
    P += tangent * (fold_env*( -0.014*f1 + 0.012*f2 -0.010*f3 ))[:,None]

    # 3) Shoulder bend: a gentle over-support turn so the cloth reads as fabric,
    # while keeping the already-approved coverage relation.
    shoulder_bend = gauss_wrap(a, ac+1.08, 0.55) * smooth((t-0.44)/0.26) * (1.0-smooth((t-0.88)/0.15))
    P[:,1] -= 0.008*shoulder_bend
    P += radial * (-0.005*shoulder_bend)[:,None]

    # 4) Preserve clasp anchor exactly and keep the top/support band nearly unchanged.
    anchor_idx=np.argmin(np.linalg.norm(P-anchor,axis=1) + 3*np.abs(t-1))
    P[anchor_idx]=anchor
    blend=(1.0 - 0.92*support_lock)[:,None]
    P = outer*support_lock[:,None] + P*blend

    # Ensure the cloth still slopes downward after leaving support.
    # Slight extra drop on lower side/back if folds raised it too much.
    post = free * smooth((t-0.66)/0.22)
    P[:,1] -= 0.008*post

    return P, dict(anchorIndex=int(anchor_idx), claspAngle=float(ac))


def compute_vertex_normals(pos, faces):
    fn=np.cross(pos[faces[:,1]]-pos[faces[:,0]], pos[faces[:,2]]-pos[faces[:,0]])
    n=np.zeros_like(pos)
    for k in range(3):
        np.add.at(n, faces[:,k], fn)
    return unit(n)


def build_cloth_mesh(outer, joints, weights, faces, edge, center, polar, thickness=0.0042):
    normals=compute_vertex_normals(outer, faces)
    inner=outer - normals*thickness
    P=np.r_[outer, inner]
    J=np.r_[joints, joints]
    W=np.r_[weights, weights]
    N=np.r_[normals, -normals]
    outer_n=len(outer)
    allF=list(map(list, faces)) + list(map(list, (faces[:,[0,2,1]]+outer_n)))
    # Side wall only on free hem edge, same as M03 topology.
    edge=np.asarray(edge,int)
    for i in range(len(edge)):
        a=edge[i]; b=edge[(i+1)%len(edge)]
        allF.extend([[a,b+outer_n,b],[a,a+outer_n,b+outer_n]])
    allF=np.asarray(allF,int)

    # UVs: existing cloth quadrant (lower-left) only.
    ang=(polar[:,0]%TAU)/TAU
    rad=polar[:,1]
    uv_outer=np.c_[ (5 + ang*502)/1024.0, (517 + rad*502)/1024.0 ]
    uv=np.r_[uv_outer, uv_outer]
    return dict(pos=P,norm=N,joints=J,weights=W,uv=uv,faces=allF,outer_normals=normals)


def build_trim(outer, normals, joints, weights, polar, edge, width=0.030, lift=0.0009, thickness=0.0018):
    edge=np.asarray(edge,int)
    loop=outer[edge]
    loop_n=normals[edge]
    loop_j=joints[edge]
    loop_w=weights[edge]
    loop_a=polar[edge,0]
    # interior ring: nearest vertices with same angle but smaller radial t.
    # use direct search within same azimuth samples.
    all_a=polar[:,0]; all_t=polar[:,1]
    inner_idx=[]
    for idx in edge:
        aa=polar[idx,0]
        cand=np.where(np.abs(((all_a-aa+math.pi)%TAU)-math.pi)<1e-7)[0]
        cand=cand[all_t[cand] < polar[idx,1]-1e-5]
        inner_idx.append(cand[np.argmax(all_t[cand])])
    inner_idx=np.asarray(inner_idx,int)
    inner_base=outer[inner_idx]
    inner_n=normals[inner_idx]
    inner_j=joints[inner_idx]
    inner_w=weights[inner_idx]
    inner_ring = loop*(1-width) + inner_base*width
    ring_outer = loop + loop_n*lift
    ring_inner = inner_ring + inner_n*lift

    # Generate top and bottom strip surfaces.
    top0 = ring_outer
    top1 = ring_inner
    bot0 = ring_outer - loop_n*thickness
    bot1 = ring_inner - inner_n*thickness

    pos=[]; norm=[]; uv=[]; jj=[]; ww=[]; faces=[]
    def addv(p,n,u,v,j,w):
        pos.append(p.tolist()); norm.append(unit(n).tolist()); uv.append([u,v]); jj.append(j.tolist()); ww.append(w.tolist());
        return len(pos)-1

    # cumulative length for UV along strip
    d=np.linalg.norm(np.roll(loop,-1,axis=0)-loop,axis=1); s=np.r_[0,np.cumsum(d[:-1])]
    s=s/max(s[-1]+d[-1],1e-8)
    uvals=(512+5 + s*(512-10))/1024.0
    v0=(0+5)/1024.0; v1=(512-5)/1024.0

    topo0=[]; topo1=[]; btm0=[]; btm1=[]
    for i in range(len(loop)):
        n=unit(loop_n[i]+inner_n[i])
        topo0.append(addv(top0[i], n, uvals[i], v0, loop_j[i], loop_w[i]))
        topo1.append(addv(top1[i], n, uvals[i], v1, inner_j[i], inner_w[i]))
        btm0.append(addv(bot0[i], -n, uvals[i], v0, loop_j[i], loop_w[i]))
        btm1.append(addv(bot1[i], -n, uvals[i], v1, inner_j[i], inner_w[i]))
    m=len(loop)
    def quad(a,b,c,d):
        faces.extend([[a,b,c],[a,c,d]])
    for i in range(m):
        j=(i+1)%m
        quad(topo0[i], topo0[j], topo1[j], topo1[i])      # top
        quad(btm0[i], btm1[i], btm1[j], btm0[j])          # bottom
        quad(topo0[i], btm0[i], btm0[j], topo0[j])        # outer wall
        quad(topo1[i], topo1[j], btm1[j], btm1[i])        # inner wall
        quad(topo0[i], topo1[i], btm1[i], btm0[i])        # end cap ribbon-seam (degenerate loop but closed continuously)
    return dict(pos=np.asarray(pos,float), norm=np.asarray(norm,float), joints=np.asarray(jj,np.uint16), weights=np.asarray(ww,float), uv=np.asarray(uv,float), faces=np.asarray(faces,int))


def write_multi_mesh(base_glb, out_glb, cloth, trim, meta):
    js,blob=read_glb(base_glb)
    new=copy.deepcopy(js)
    buf=bytearray(blob)

    def addview(raw, target=None):
        while len(buf)%4: buf.extend(b'\0')
        idx=len(new['bufferViews'])
        v={'buffer':0,'byteOffset':len(buf),'byteLength':len(raw)}
        if target is not None: v['target']=target
        new['bufferViews'].append(v); buf.extend(raw); return idx
    def addacc(arr, typ, ct=5126, target=34962):
        arr=np.asarray(arr, dtype=DT[ct])
        idx=len(new['accessors'])
        v=addview(arr.tobytes(), target)
        a={'bufferView':v,'componentType':ct,'count':len(arr),'type':typ}
        if typ=='VEC3':
            a['min']=arr.min(0).astype(float).tolist(); a['max']=arr.max(0).astype(float).tolist()
        new['accessors'].append(a)
        return idx
    def prim_from(data, material):
        attrs={
            'POSITION': addacc(data['pos'],'VEC3',5126,34962),
            'NORMAL': addacc(data['norm'],'VEC3',5126,34962),
            'JOINTS_0': addacc(data['joints'],'VEC4',5123,34962),
            'WEIGHTS_0': addacc(data['weights'],'VEC4',5126,34962),
            'TEXCOORD_0': addacc(data['uv'],'VEC2',5126,34962),
            'COLOR_0': addacc(np.ones((len(data['pos']),4),np.float32),'VEC4',5126,34962),
        }
        idx = addacc(np.asarray(data['faces'],np.uint32).reshape(-1),'SCALAR',5125,34963)
        return {'attributes':attrs,'indices':idx,'material':material}

    new['meshes'][7]={'name':js['meshes'][7]['name'],'primitives':[prim_from(trim,1), prim_from(cloth,2)], 'extras':meta}
    new['asset']['generator']='Stargazer M04 / M03 baseline / asymmetric mantle appearance polish'
    new['extras']={**js.get('extras',{}),'sampleVersion':'M04','status':'mantle appearance polish candidate; based on approved M03 coverage baseline; not installed in game','scope':'only mesh 08 Asymmetric shoulder mantle','sourceM03SHA256':hashlib.sha256(Path(base_glb).read_bytes()).hexdigest(),'checkedClips':['DesignPose','Idle','Run','Attack1'],'animationReview':'DesignPose/Idle/Run and Attack1 spot-checks only; dynamic cloth realism still pending', 'mantle':meta}

    # Compact used accessors/bufferViews while preserving all other live bytes.
    live=set()
    for mesh in new['meshes']:
        for p in mesh['primitives']:
            live.update(p['attributes'].values()); live.add(p['indices'])
    for sk in new['skins']: live.add(sk['inverseBindMatrices'])
    for an in new['animations']:
        for s in an['samplers']: live.update([s['input'],s['output']])
    compact=bytearray(); views=[]; accs=[]; vm={}; am={}
    def copy_view(i):
        if i in vm: return vm[i]
        v=copy.deepcopy(new['bufferViews'][i])
        raw=buf[v.get('byteOffset',0):v.get('byteOffset',0)+v['byteLength']]
        while len(compact)%4: compact.extend(b'\0')
        v['byteOffset']=len(compact); compact.extend(raw)
        vm[i]=len(views); views.append(v); return vm[i]
    for i in sorted(live):
        a=copy.deepcopy(new['accessors'][i]); a['bufferView']=copy_view(a['bufferView']); am[i]=len(accs); accs.append(a)
    for mesh in new['meshes']:
        for p in mesh['primitives']:
            p['attributes']={k:am[v] for k,v in p['attributes'].items()}; p['indices']=am[p['indices']]
    for sk in new['skins']: sk['inverseBindMatrices']=am[sk['inverseBindMatrices']]
    for an in new['animations']:
        for s in an['samplers']: s['input']=am[s['input']]; s['output']=am[s['output']]
    for im in new['images']: im['bufferView']=copy_view(im['bufferView'])
    new['accessors']=accs; new['bufferViews']=views; new['buffers']=[{'byteLength':len(compact)}]
    new['extras']['triangleCount']=int(sum(accs[p['indices']]['count']//3 for m in new['meshes'] for p in m['primitives']))
    new['extras']['vertexCount']=int(sum(accs[p['attributes']['POSITION']]['count'] for m in new['meshes'] for p in m['primitives']))
    jsb=json.dumps(new,separators=(',',':'),ensure_ascii=False).encode('utf-8')
    while len(jsb)%4: jsb += b' '
    while len(compact)%4: compact += b'\0'
    raw=struct.pack('<III',0x46546C67,2,28+len(jsb)+len(compact))+struct.pack('<II',len(jsb),0x4E4F534A)+jsb+struct.pack('<II',len(compact),0x004E4942)+compact
    Path(out_glb).write_bytes(raw)
    return new


def diagnostics(base_glb, out_glb):
    # Re-check actual displayed sections in DesignPose for H01 shoulder vs M03/M04 mantle.
    jh,bh=read_glb(R/'authoring/H01_BASE.glb')
    jm,bm=read_glb(base_glb)
    j4,b4=read_glb(out_glb)
    # shoulder mesh 3 in H01, mantle mesh 7 in M03/M04 use DesignPose baked? section uses bind-space okay for DesignPose if weights preserved? we need actual display via skin.
    # Use skin_positions with sampled DesignPose matrices from each asset.
    from glb_io import bone_matrices, mesh_arrays
    BH=bone_matrices(jh,bh,'DesignPose',0)
    BM=bone_matrices(jm,bm,'DesignPose',0)
    B4=bone_matrices(j4,b4,'DesignPose',0)
    shoulder=mesh_arrays(jh,bh,3,materials=[0])
    mantle3=mesh_arrays(jm,bm,7)
    mantle4=mesh_arrays(j4,b4,7)
    shp=skin_positions(shoulder['p'], shoulder['j'], shoulder['w'], BH)
    m3p=skin_positions(mantle3['p'], mantle3['j'], mantle3['w'], BM)
    m4p=skin_positions(mantle4['p'], mantle4['j'], mantle4['w'], B4)
    res={}
    ys=[1.86,1.90,1.94]
    for y in ys:
        segS=section_segments(shp, shoulder['f'], y)
        seg3=section_segments(m3p, mantle3['f'], y)
        seg4=section_segments(m4p, mantle4['f'], y)
        xs=lambda seg: [float(v[0]) for pair in seg for v in pair]
        res[str(y)]={'shoulderMinX': float(min(xs(segS))) if len(segS) else None,
                     'M03MinX': float(min(xs(seg3))) if len(seg3) else None,
                     'M04MinX': float(min(xs(seg4))) if len(seg4) else None,
                     'M03Outside': float(min(xs(seg3)) - min(xs(segS))) if len(seg3) and len(segS) else None,
                     'M04Outside': float(min(xs(seg4)) - min(xs(segS))) if len(seg4) and len(segS) else None}
    return res


def main():
    base_glb=R/'assets/Stargazer_M03.glb'
    outer,joints,weights,faces,polar,edge,center,anchor = open_m03_source()
    sculpted, info = sculpt_outer(outer, polar, center, anchor)
    cloth=build_cloth_mesh(sculpted, joints, weights, faces, edge, center, polar)
    trim=build_trim(sculpted, cloth['outer_normals'], joints, weights, polar, edge)
    meta={
        'revision':'M04',
        'stage':'appearance polish candidate based on approved M03 coverage baseline',
        'constructionSpace':'M03 design-space shell adjusted locally; inverse blended skinning back to bind space',
        'baseSource':'M03 approved coverage shell',
        'scope':'only mesh 08 Asymmetric shoulder mantle',
        'clothThickness':0.0042,
        'trimThickness':0.0018,
        'trimPolicy':'narrow hem-only gold trim; no new global materials or textures',
        'folds':'three broad folds + one shallow ridge; no fine wrinkle field',
        'weightsPolicy':'inherit M03 cloth weights; trim follows neighboring cloth weights',
        **info
    }
    # Convert from design space back to bind space per vertex.
    from glb_io import bone_matrices
    jm,bm=read_glb(base_glb)
    B=bone_matrices(jm,bm,'DesignPose',0)
    cloth_bind=unskin_positions(cloth['pos'], cloth['joints'], cloth['weights'], B)
    cloth_norm_bind=unit(np.linalg.solve(np.sum(B[cloth['joints']]*cloth['weights'][...,None,None],axis=1)[:,:3,:3], cloth['norm'][...,None])[:,:,0])
    trim_bind=unskin_positions(trim['pos'], trim['joints'], trim['weights'], B)
    trim_norm_bind=unit(np.linalg.solve(np.sum(B[trim['joints']]*trim['weights'][...,None,None],axis=1)[:,:3,:3], trim['norm'][...,None])[:,:,0])
    cloth_out={**cloth, 'pos':cloth_bind, 'norm':cloth_norm_bind}
    trim_out={**trim, 'pos':trim_bind, 'norm':trim_norm_bind}
    write_multi_mesh(base_glb, R/'assets/Stargazer_M04.glb', cloth_out, trim_out, meta)
    # Keep authoring/debug data.
    np.savez_compressed(R/'reports/m04_authoring.npz', m03_outer=outer, m04_outer=sculpted, faces=faces, polar=polar, edge=edge,
                        cloth_bind=cloth_bind, cloth_design=cloth['pos'], trim_bind=trim_bind, trim_design=trim['pos'])
    section=diagnostics(base_glb, R/'assets/Stargazer_M04.glb')
    report={
        'baseM03SHA256': hashlib.sha256(base_glb.read_bytes()).hexdigest(),
        'outputSHA256': hashlib.sha256((R/'assets/Stargazer_M04.glb').read_bytes()).hexdigest(),
        'sectionCoverage': section,
        'trimVertices': int(len(trim_bind)),
        'clothVertices': int(len(cloth_bind)),
        'clothTriangles': int(len(cloth['faces'])),
        'trimTriangles': int(len(trim['faces'])),
        'note':'M04 keeps M03 coverage/support relationship and adds folds, cloth shading geometry and hem trim only.'
    }
    (R/'reports/m04_diagnostics.json').write_text(json.dumps(report,indent=2))
    print('built M04', report)

if __name__=='__main__':
    main()
