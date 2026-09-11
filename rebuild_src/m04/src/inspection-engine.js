/* Starfall 0.1 — original, zero-dependency WebGL2 renderer and GLB subset loader.
   No Three.js is bundled or impersonated. GPU resources are owned and reused.
   Character skinning supports up to 25 joints. Rendering is separate from combat. */
'use strict';
window.SF = window.SF || {};
(() => {
const S=window.SF;
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
const lerp=(a,b,t)=>a+(b-a)*t;
const v3=(x=0,y=0,z=0)=>[x,y,z];
const add=(a,b)=>a.map((x,i)=>x+b[i]);
const sub=(a,b)=>a.map((x,i)=>x-b[i]);
const scale=(a,s)=>a.map(x=>x*s);
const dot=(a,b)=>a.reduce((s,x,i)=>s+x*b[i],0);
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const norm=a=>scale(a,1/(Math.hypot(...a)||1));
const identity=()=>new Float32Array([1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]);
function mul(a,b){let o=new Float32Array(16);for(let c=0;c<4;c++)for(let r=0;r<4;r++){let s=0;for(let k=0;k<4;k++)s+=a[k*4+r]*b[c*4+k];o[c*4+r]=s;}return o;}
function transform(m,v,w=1){return [0,1,2,3].map(r=>m[r]*v[0]+m[4+r]*v[1]+m[8+r]*v[2]+m[12+r]*w);}
function inverse(a){let rows=Array.from({length:4},(_,r)=>[...Array.from({length:4},(_,c)=>a[c*4+r]),...Array.from({length:4},(_,c)=>+(c===r))]);for(let c=0;c<4;c++){let best=c;for(let r=c+1;r<4;r++)if(Math.abs(rows[r][c])>Math.abs(rows[best][c]))best=r;[rows[c],rows[best]]=[rows[best],rows[c]];let d=rows[c][c];if(Math.abs(d)<1e-12)throw Error('Singular camera matrix');rows[c]=rows[c].map(x=>x/d);for(let r=0;r<4;r++)if(r!==c){let f=rows[r][c];rows[r]=rows[r].map((x,k)=>x-f*rows[c][k]);}}let out=identity();for(let r=0;r<4;r++)for(let c=0;c<4;c++)out[c*4+r]=rows[r][c+4];return out;}
function compose(t=[0,0,0],q=[0,0,0,1],s=[1,1,1]){let[x,y,z,w]=q,x2=x+x,y2=y+y,z2=z+z,xx=x*x2,xy=x*y2,xz=x*z2,yy=y*y2,yz=y*z2,zz=z*z2,wx=w*x2,wy=w*y2,wz=w*z2;return new Float32Array([(1-yy-zz)*s[0],(xy+wz)*s[0],(xz-wy)*s[0],0,(xy-wz)*s[1],(1-xx-zz)*s[1],(yz+wx)*s[1],0,(xz+wy)*s[2],(yz-wx)*s[2],(1-xx-yy)*s[2],0,t[0],t[1],t[2],1]);}
const yaw=(a)=>[0,Math.sin(a/2),0,Math.cos(a/2)];
function quatEuler(x,y,z){let a=Math.cos(x/2),b=Math.cos(y/2),c=Math.cos(z/2),d=Math.sin(x/2),e=Math.sin(y/2),f=Math.sin(z/2);return[d*b*c+a*e*f,a*e*c-d*b*f,a*b*f+d*e*c,a*b*c-d*e*f];}
function slerp(a,b,t){let d=dot(a,b),bb=b;if(d<0){bb=b.map(x=>-x);d=-d;}if(d>.9995)return norm(a.map((x,i)=>lerp(x,bb[i],t)));let th=Math.acos(clamp(d,-1,1)),sn=Math.sin(th);return a.map((x,i)=>(x*Math.sin((1-t)*th)+bb[i]*Math.sin(t*th))/sn);}
function perspective(fovy,aspect,n,f){let k=1/Math.tan(fovy/2);return new Float32Array([k/aspect,0,0,0,0,k,0,0,0,0,(f+n)/(n-f),-1,0,0,2*f*n/(n-f),0]);}
function ortho(l,r,b,t,n,f){return new Float32Array([2/(r-l),0,0,0,0,2/(t-b),0,0,0,0,-2/(f-n),0,-(r+l)/(r-l),-(t+b)/(t-b),-(f+n)/(f-n),1]);}
function lookAt(eye,target,up=[0,1,0]){let z=norm(sub(eye,target)),x=norm(cross(up,z)),y=cross(z,x);return new Float32Array([x[0],y[0],z[0],0,x[1],y[1],z[1],0,x[2],y[2],z[2],0,-dot(x,eye),-dot(y,eye),-dot(z,eye),1]);}
S.M={clamp,lerp,v3,add,sub,scale,dot,cross,norm,identity,mul,inverse,transform,compose,yaw,quatEuler,slerp,perspective,ortho,lookAt};

class Geometry {
 constructor(){this.data=[];this.indices=[];}
 vertex(p,n,c=[.5,.5,.5],surface=[.8,0,0],uv=[0,0],js=[0,0,0,0],ws=[1,0,0,0]){let i=this.data.length/22;this.data.push(...p,...n,...c,...surface,...js,...ws,...uv);return i;}
 tri(a,b,c,color,surface,uvs){let n=norm(cross(sub(b,a),sub(c,a)));this.indices.push(this.vertex(a,n,color,surface,uvs?.[0]),this.vertex(b,n,color,surface,uvs?.[1]),this.vertex(c,n,color,surface,uvs?.[2]));}
 quad(a,b,c,d,color,surface,uvs){this.tri(a,b,c,color,surface,uvs&&[uvs[0],uvs[1],uvs[2]]);this.tri(a,c,d,color,surface,uvs&&[uvs[0],uvs[2],uvs[3]]);}
 merge(other,m=identity()){let offset=this.data.length/22;for(let i=0;i<other.data.length;i+=22){let v=other.data.slice(i,i+22),p=transform(m,v.slice(0,3)),n=norm(transform(m,v.slice(3,6),0).slice(0,3));v.splice(0,6,...p.slice(0,3),...n);this.data.push(...v);}this.indices.push(...other.indices.map(i=>i+offset));return this;}
 loft(rings,segments,color,surface=[.85,0,0],phase=0){let vv=rings.map(([y,rx,rz,cx=0,cz=0])=>Array.from({length:segments},(_,i)=>{let a=phase+i*Math.PI*2/segments;return[cx+Math.sin(a)*rx,y,cz+Math.cos(a)*rz];}));for(let k=0;k<vv.length-1;k++)for(let i=0;i<segments;i++){let j=(i+1)%segments;this.quad(vv[k][i],vv[k][j],vv[k+1][j],vv[k+1][i],color,surface);}for(let i=1;i<segments-1;i++){this.tri(vv[0][0],vv[0][i+1],vv[0][i],color,surface);this.tri(vv.at(-1)[0],vv.at(-1)[i],vv.at(-1)[i+1],color,surface);}return this;}
 ring(inner,outer,y,color=[1,1,1],surface=[.6,.4,0],segments=96,start=0,length=Math.PI*2){for(let i=0;i<segments;i++){let a=start+i/segments*length,b=start+(i+1)/segments*length;this.quad([Math.sin(a)*inner,y,Math.cos(a)*inner],[Math.sin(a)*outer,y,Math.cos(a)*outer],[Math.sin(b)*outer,y,Math.cos(b)*outer],[Math.sin(b)*inner,y,Math.cos(b)*inner],color,surface);}return this;}
 prism(points,depth,color,surface=[.8,0,0]){let front=points.map(([x,y])=>[x,y,depth/2]),back=points.map(([x,y])=>[x,y,-depth/2]);let fc=scale(front.reduce(add,[0,0,0]),1/front.length),bc=scale(back.reduce(add,[0,0,0]),1/back.length);for(let i=0;i<front.length;i++){let j=(i+1)%front.length;this.tri(front[i],front[j],fc,color,surface);this.tri(back[j],back[i],bc,color,surface);this.quad(front[i],back[i],back[j],front[j],color,surface);}return this;}
}
S.Geometry=Geometry;

// v0.1.2 local adapter extension. Still a documented subset, not a general importer.
function parseGLB(encoded){
 const bytes=Uint8Array.from(atob(encoded),c=>c.charCodeAt(0)),dv=new DataView(bytes.buffer);
 if(dv.getUint32(0,true)!==0x46546c67||dv.getUint32(4,true)!==2)throw Error('角色文件不是有效的 glTF 2.0 GLB');
 let json,bin;for(let o=12;o<bytes.length;){let len=dv.getUint32(o,true),type=dv.getUint32(o+4,true);o+=8;if(type===0x4e4f534a)json=JSON.parse(new TextDecoder().decode(bytes.subarray(o,o+len)));else if(type===0x004e4942)bin=bytes.slice(o,o+len).buffer;o+=len;}
 if(!json||!bin)throw Error('GLB 缺少几何数据');
 if(json.extensionsRequired?.length)throw Error('当前角色适配器尚不支持所需 GLB 扩展：'+json.extensionsRequired.join(', '));
 const types={5126:Float32Array,5123:Uint16Array,5125:Uint32Array,5121:Uint8Array},dims={SCALAR:1,VEC2:2,VEC3:3,VEC4:4,MAT4:16};
 function accessor(idx){let a=json.accessors[idx];if(!a)throw Error('GLB 属性访问器缺失');let v=json.bufferViews[a.bufferView];if(a.sparse||v.byteStride)throw Error('当前适配器不支持 sparse/interleaved GLB，请先转换');let C=types[a.componentType];if(!C)throw Error('不支持的 GLB 数值类型');let raw=new C(bin,(v.byteOffset||0)+(a.byteOffset||0),a.count*dims[a.type]);if(a.normalized&&a.componentType!==5126){const max={5121:255,5123:65535,5125:4294967295}[a.componentType];return Float32Array.from(raw,x=>x/max);}return raw;}
 let skin=json.skins?.[0];if(!skin)throw Error('GLB 缺少角色蒙皮');
 if(skin.joints.length>25)throw Error('角色骨骼超过当前适配器的 25 根上限');
 let jointIndex=new Map(skin.joints.map((n,i)=>[n,i]));let parents=Array(skin.joints.length).fill(-1);
 json.nodes.forEach((n,i)=>n.children?.forEach(c=>{if(jointIndex.has(c)){if(!jointIndex.has(i))throw Error('骨骼的非关节父节点需要先烘焙');parents[jointIndex.get(c)]=jointIndex.get(i);}}));
 let geo=new Geometry(),textureIndex=null,meshCount=0,primitiveCount=0;
 for(let node of json.nodes){if(node.mesh===undefined)continue;
  if(node.skin!==0)throw Error('当前多网格适配器要求角色各网格共享第一个蒙皮');
  if(node.matrix||node.translation?.some(x=>x!==0)||node.rotation?.some((x,i)=>x!==[0,0,0,1][i])||node.scale?.some(x=>x!==1))throw Error('角色网格节点变换需先烘焙到绑定空间');
  meshCount++;
  for(let p of json.meshes[node.mesh].primitives){if(p.mode!==undefined&&p.mode!==4)throw Error('角色网格必须是三角形');primitiveCount++;
   let a=p.attributes,po=accessor(a.POSITION),no=accessor(a.NORMAL),co=a.COLOR_0!==undefined?accessor(a.COLOR_0):null,cd=co?dims[json.accessors[a.COLOR_0].type]:0;
   let jo=accessor(a.JOINTS_0),we=accessor(a.WEIGHTS_0),uv=a.TEXCOORD_0!==undefined?accessor(a.TEXCOORD_0):null,ix=accessor(p.indices),mt=json.materials?.[p.material]||{},pbr=mt.pbrMetallicRoughness||{},f=pbr.baseColorFactor||[1,1,1,1],surf=[pbr.roughnessFactor??1,pbr.metallicFactor??1,mt.extras?.emissionStrength||0];
   if(pbr.baseColorTexture){if(!uv)throw Error('角色材质有贴图但缺少 TEXCOORD_0');let ti=pbr.baseColorTexture.index;if(textureIndex!==null&&ti!==textureIndex)throw Error('当前合批角色需要共用一张 UV 图集');textureIndex=ti;}
   let offset=geo.data.length/22;
   for(let i=0;i<po.length/3;i++)geo.vertex(Array.from(po.slice(i*3,i*3+3)),Array.from(no.slice(i*3,i*3+3)),[0,1,2].map(k=>f[k]*(co?co[i*cd+k]:1)),surf,uv?Array.from(uv.slice(i*2,i*2+2)):[0,0],Array.from(jo.slice(i*4,i*4+4)),Array.from(we.slice(i*4,i*4+4)));
   geo.indices.push(...Array.from(ix,i=>i+offset));
  }
 }
 let textureData=null;
 if(textureIndex!==null){let im=json.images[json.textures[textureIndex].source];if(im.uri?.startsWith('data:'))textureData=im.uri;else if(im.bufferView!==undefined){let v=json.bufferViews[im.bufferView],data=new Uint8Array(bin,v.byteOffset||0,v.byteLength),str='';for(let i=0;i<data.length;i+=8192)str+=String.fromCharCode(...data.subarray(i,i+8192));textureData='data:'+im.mimeType+';base64,'+btoa(str);}else throw Error('角色贴图必须嵌入 GLB，未提供的外部路径不会被忽略');}
 let clips={};for(let an of json.animations||[]){let channels=an.channels.map(ch=>{let sa=an.samplers[ch.sampler],interpolation=sa.interpolation||'LINEAR';if(!['LINEAR','STEP'].includes(interpolation))throw Error('当前动画适配器支持 LINEAR / STEP，不支持 '+interpolation);if(!['rotation','translation','scale'].includes(ch.target.path))throw Error('当前动画适配器不支持 '+ch.target.path);if(!jointIndex.has(ch.target.node))throw Error('动画目标不是已知骨骼');return{node:jointIndex.get(ch.target.node),path:ch.target.path,interpolation,times:accessor(sa.input),values:accessor(sa.output)};});clips[an.name]={channels,duration:Math.max(...channels.map(c=>c.times[c.times.length-1]))};}
 return {geometry:geo,nodes:skin.joints.map(i=>json.nodes[i]),parents,inverseBind:accessor(skin.inverseBindMatrices),clips,textureData,metadata:{...json.extras,loadedMeshes:meshCount,loadedPrimitives:primitiveCount,uvLoaded:textureIndex!==null}};
}
class Animator{
 constructor(asset){this.asset=asset;this.name='Idle';this.time=0;this.prev=null;this.fade=0;this.bones=new Float32Array(25*16);this.speed=1;this.update(0);}
 set(name,speed=1,restart=false){if(!this.asset.clips[name])name='Idle';if(name===this.name&&!restart){this.speed=speed;return;}this.prev={name:this.name,time:this.time,speed:this.speed};this.name=name;this.time=0;this.speed=speed;this.fade=.12;}
 sample(name,time){let a=this.asset,clip=a.clips[name]||a.clips.Idle;let loop=['Idle','Run'].includes(name),t=loop?time%clip.duration:Math.min(time,clip.duration);let pose=a.nodes.map(n=>({rotation:n.rotation||[0,0,0,1],translation:n.translation||[0,0,0],scale:n.scale||[1,1,1]}));
  for(let ch of clip.channels){let i=0;while(i<ch.times.length-2&&t>ch.times[i+1])i++;let j=Math.min(i+1,ch.times.length-1),u=ch.interpolation==='STEP'?(t>=ch.times[j]?1:0):clamp((t-ch.times[i])/(ch.times[j]-ch.times[i]||1),0,1),dim=ch.path==='rotation'?4:3;let av=Array.from(ch.values.slice(i*dim,(i+1)*dim)),bv=Array.from(ch.values.slice(j*dim,(j+1)*dim));pose[ch.node][ch.path]=ch.path==='rotation'?slerp(av,bv,u):av.map((v,k)=>lerp(v,bv[k],u));}return pose;
 }
 update(dt){this.time+=dt*this.speed;let pose=this.sample(this.name,this.time);if(this.fade>0&&this.prev){this.fade=Math.max(0,this.fade-dt);this.prev.time+=dt*this.prev.speed;let old=this.sample(this.prev.name,this.prev.time),u=1-this.fade/.12;pose=pose.map((v,i)=>({rotation:slerp(old[i].rotation,v.rotation,u),translation:v.translation.map((x,k)=>lerp(old[i].translation[k],x,u)),scale:v.scale.map((x,k)=>lerp(old[i].scale[k],x,u))}));}
  let worlds=[],a=this.asset,visiting=new Set();const world=i=>{if(worlds[i])return worlds[i];if(visiting.has(i))throw Error('角色骨骼有循环父子关系');visiting.add(i);let p=pose[i],local=compose(p.translation,p.rotation,p.scale);worlds[i]=a.parents[i]>=0?mul(world(a.parents[i]),local):local;visiting.delete(i);return worlds[i];};
  for(let i=0;i<a.nodes.length;i++)this.bones.set(mul(world(i),a.inverseBind.subarray(i*16,i*16+16)),i*16);return this.bones;
 }
}
S.parseGLB=parseGLB;S.Animator=Animator;

const vertexShader=`#version 300 es
precision highp float;
layout(location=0) in vec3 aPosition;layout(location=1) in vec3 aNormal;
layout(location=2) in vec3 aColor;layout(location=3) in vec3 aSurface;
layout(location=4) in vec4 aJoints;layout(location=5) in vec4 aWeights;layout(location=6) in vec2 aUV;
uniform mat4 uVP,uModel,uLightVP;uniform mat4 uBones[25];uniform bool uSkin;
out vec3 vWorld,vNormal,vColor,vSurface;out vec2 vUV;out vec4 vShadow;
void main(){mat4 skin=mat4(1.0);if(uSkin){ivec4 j=ivec4(aJoints);skin=uBones[j.x]*aWeights.x+uBones[j.y]*aWeights.y+uBones[j.z]*aWeights.z+uBones[j.w]*aWeights.w;}vec4 w=uModel*skin*vec4(aPosition,1.0);vWorld=w.xyz;vNormal=normalize(mat3(uModel*skin)*aNormal);vColor=aColor;vSurface=aSurface;vUV=aUV;vShadow=uLightVP*w;gl_Position=uVP*w;}`;
const fragmentShader=`#version 300 es
precision highp float;
in vec3 vWorld,vNormal,vColor,vSurface;in vec2 vUV;in vec4 vShadow;
uniform vec3 uEye,uTint,uHero,uEnemy;uniform float uAlpha,uFlash,uTime;uniform bool uTextured,uUnlit;
uniform int uInspectionMode;uniform bool uClay;
uniform int uMaterialMode;uniform sampler2D uTexture,uShadow;uniform bool uShadows;
out vec4 frag;
const float PI=3.14159265359;
float shadow(vec3 n){if(!uShadows)return 1.;vec3 p=vShadow.xyz/vShadow.w*.5+.5;if(p.x<0.||p.x>1.||p.y<0.||p.y>1.||p.z>1.)return 1.;float bias=max(.00058*(1.-dot(n,normalize(vec3(-.6,1.,.52)))),.00029);vec2 texel=1./vec2(textureSize(uShadow,0));float sh=0.;for(int x=-1;x<=1;x++)for(int y=-1;y<=1;y++){float d=texture(uShadow,p.xy+vec2(float(x),float(y))*texel).r;sh+=p.z-bias<=d?1.:0.;}return uInspectionMode>0?.63+.37*sh/9.:.23+.77*sh/9.;}
vec3 tone(vec3 x){return clamp((x*(2.51*x+.03))/(x*(2.43*x+.59)+.14),0.,1.);}
vec3 fresnel(float v,vec3 f0){return f0+(1.-f0)*pow(1.-v,5.);}
vec3 specular(vec3 n,vec3 V,vec3 L,float rough,vec3 f0){vec3 h=normalize(V+L);float nv=max(dot(n,V),.001),nl=max(dot(n,L),.001),nh=max(dot(n,h),0.),vh=max(dot(V,h),0.);float a=rough*rough,aa=a*a,d=nh*nh*(aa-1.)+1.;float D=aa/(PI*d*d);float k=(rough+1.)*(rough+1.)/8.;float G=nv/(nv*(1.-k)+k)*nl/(nl*(1.-k)+k);return min(vec3(8.),D*G*fresnel(vh,f0)/(4.*nv*nl+.001));}
void main(){vec3 n=normalize(vNormal);if(!gl_FrontFacing)n=-n;vec4 tex=vec4(1.);vec3 base=vColor*uTint;if(uTextured){tex=texture(uTexture,vUV);base*=tex.rgb;}
 float rough=clamp(vSurface.x,.17,1.),metal=vSurface.y;
 if(uMaterialMode==2&&uTextured)rough=clamp(rough*(.86+.28*tex.a),.17,1.);
 if(uMaterialMode==1&&uTextured){vec2 d=1./vec2(textureSize(uTexture,0));float dx=texture(uTexture,vUV-vec2(d.x,0)).a-texture(uTexture,vUV+vec2(d.x,0)).a;float dz=texture(uTexture,vUV-vec2(0,d.y)).a-texture(uTexture,vUV+vec2(0,d.y)).a;n=normalize(n+vec3(dx*.18,0,dz*.18));rough=.91;metal=.01;}
 if(uClay){base=vec3(.55);rough=.83;metal=0.;}
 vec3 bc=pow(max(base,vec3(.001)),vec3(2.2)),V=normalize(uEye-vWorld),L=normalize(vec3(-.6,1.,.52));float nd=max(dot(n,L),0.),nv=max(dot(n,V),.001),sh=shadow(n);
 vec3 hemi=mix(vec3(.085,.13,.155),vec3(.32,.43,.48),clamp(n.y*.5+.5,0.,1.));
 if(uInspectionMode>0)hemi=mix(vec3(.24),vec3(.53),clamp(n.y*.5+.5,0.,1.));
 vec3 key=uInspectionMode>0?vec3(2.05):vec3(2.5,2.15,1.68),f0=mix(vec3(.035),bc,metal);
 vec3 lit=bc*(1.-metal*.94)*(hemi+key*nd*sh*.78);
 lit+=specular(n,V,L,rough,f0)*key*nd*sh;
 // Broad analytic reflected sky and architectural light cards. No bloom pass.
 vec3 r=reflect(-V,n);float sky=smoothstep(-.28,.8,r.y);
 vec3 env=mix(vec3(.025,.055,.075),vec3(.40,.60,.68),sky);
 float warm=pow(max(dot(r,normalize(vec3(-.85,.60,.40))),0.),mix(22.,3.,rough));
 float cool=pow(max(dot(r,normalize(vec3(.78,.50,-.62))),0.),mix(36.,4.,rough));
 env+=vec3(1.8,1.53,1.04)*warm+vec3(.22,.58,.73)*cool;
 if(uInspectionMode>0)env=mix(vec3(.22),vec3(.73),sky)+vec3(1.12)*warm+vec3(.58)*cool;
 lit+=env*fresnel(nv,f0)*(1.-rough*.42)*(.38+metal*.86);
 vec3 fillL=normalize(vec3(.72,.32,-.70));float fill=max(dot(n,fillL),0.);
 lit+=bc*(1.-metal)*(uInspectionMode>0?vec3(.29):vec3(.10,.23,.28))*fill;
 lit+=specular(n,V,fillL,max(rough,.3),f0)*(uInspectionMode>0?vec3(.60):vec3(.24,.47,.56))*fill*.48;
 if(uMaterialMode==1){vec2 ph=vWorld.xz-uHero.xz,pe=vWorld.xz-uEnemy.xz;float ao=1.-.40*exp(-dot(ph,ph)*8.)-.39*exp(-dot(pe,pe)*4.2);lit*=clamp(ao,.28,1.);}
 if(!uClay)lit+=bc*vSurface.z*1.2;lit=mix(lit,vec3(2.7,2.4,1.8),uFlash);if(uUnlit)lit=bc*(1.+vSurface.z);
 vec3 color=pow(tone(lit),vec3(1./2.2)); if(uInspectionMode>0&&uMaterialMode==1){vec2 d=vWorld.xz-uHero.xz;float contact=1.-.12*exp(-dot(d,d)*4.);color=vec3(.86,.875,.873)*(.78+.22*sh)*contact;}
 // Fog follows world depth, not camera distance: it no longer washes the foreground floor.
 float fogStart=uMaterialMode==2?24.:18.;float fog=1.-exp(-max(-vWorld.z-fogStart,0.)*.025-max(-vWorld.y-2.,0.)*.033);
 if(uInspectionMode==0)color=mix(color,vec3(.19,.28,.31),min(fog,.89));frag=vec4(color,uAlpha);}`;
const shadowVS=`#version 300 es
precision highp float;layout(location=0) in vec3 aPosition;layout(location=4) in vec4 aJoints;layout(location=5) in vec4 aWeights;
uniform mat4 uLightVP,uModel,uBones[25];uniform bool uSkin;
void main(){mat4 s=mat4(1);if(uSkin){ivec4 j=ivec4(aJoints);s=uBones[j.x]*aWeights.x+uBones[j.y]*aWeights.y+uBones[j.z]*aWeights.z+uBones[j.w]*aWeights.w;}gl_Position=uLightVP*uModel*s*vec4(aPosition,1);}`;
const shadowFS=`#version 300 es
precision highp float;void main(){}`;
const skyVS=`#version 300 es
out vec2 uv;void main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);uv=p;gl_Position=vec4(p*2.-1.,.999,1);}`;
const skyFS=`#version 300 es
precision highp float;in vec2 uv;out vec4 frag;uniform float uTime;uniform vec2 uResolution;uniform bool uStudio;
void main(){if(uStudio){frag=vec4(vec3(.86,.875,.873),1.);return;}float y=uv.y;vec3 c=mix(vec3(.245,.324,.339),vec3(.071,.128,.166),smoothstep(0.,1.,y));
 vec2 p=uv-vec2(.18,.91);p.x*=uResolution.x/uResolution.y;float d=dot(p,p);
 c+=vec3(.155,.119,.066)*exp(-d*3.5)*.30;
 float mist=exp(-pow((y-.50+sin(uv.x*4.1)*.035)*5.,2.));c+=vec3(.026,.040,.042)*mist;
 frag=vec4(c,1.);}`;
const particleVS=`#version 300 es
precision highp float;layout(location=0) in vec3 aPosition;layout(location=1) in vec4 aColorSize;uniform mat4 uVP;uniform float uHeight;
out vec3 vColor;void main(){gl_Position=uVP*vec4(aPosition,1);gl_PointSize=clamp(aColorSize.a*uHeight/max(gl_Position.w,1.),1.,100.);vColor=aColorSize.rgb;}`;
const particleFS=`#version 300 es
precision highp float;in vec3 vColor;out vec4 frag;void main(){vec2 p=gl_PointCoord-.5;float d=length(p)*2.;if(d>1.)discard;float a=pow(1.-d,2.5);frag=vec4(vColor,a);}`;
class Renderer{
 constructor(canvas){this.canvas=canvas;
 let gl=null;const contextErrors=[];canvas.addEventListener('webglcontextcreationerror',e=>contextErrors.push(e.statusMessage||'WebGL context creation failed'));
 const options=[{alpha:false,antialias:true,powerPreference:'default',preserveDrawingBuffer:false},{alpha:false,antialias:false},{alpha:false}];
 for(let i=0;i<options.length&&!gl;i++){try{gl=canvas.getContext('webgl2',options[i]);}catch(e){contextErrors.push(e.message);}if(window.SF_BOOT)window.SF_BOOT.contextAttempts=i+1;}
 if(window.SF_BOOT)window.SF_BOOT.contextErrors=contextErrors;
 if(!gl)throw Error('[G01] 浏览器没有提供 WebGL 2。请把文件下载到电脑，再用桌面版 Edge / Chrome 打开；若仍失败，请将本页截图发给我。');
 this.gl=gl;this.program=this.programFrom(vertexShader,fragmentShader);this.shadowProgram=this.programFrom(shadowVS,shadowFS);this.skyProgram=this.programFrom(skyVS,skyFS);this.particleProgram=this.programFrom(particleVS,particleFS);this.uniforms=new Map();this.highQuality=false;this.meshes=[];this.emptyVAO=gl.createVertexArray();this.particleVAO=gl.createVertexArray();this.particleBuffer=gl.createBuffer();gl.bindVertexArray(this.particleVAO);gl.bindBuffer(gl.ARRAY_BUFFER,this.particleBuffer);gl.enableVertexAttribArray(0);gl.vertexAttribPointer(0,3,gl.FLOAT,false,28,0);gl.enableVertexAttribArray(1);gl.vertexAttribPointer(1,4,gl.FLOAT,false,28,12);gl.bindVertexArray(null);this.white=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,this.white);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,1,1,0,gl.RGBA,gl.UNSIGNED_BYTE,new Uint8Array([255,255,255,255]));gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);this.setupShadow();this.lightVP=mul(ortho(-16,16,-16,16,.1,65),lookAt([-15,25,13],[0,0,0]));this.resize();gl.enable(gl.DEPTH_TEST);gl.disable(gl.CULL_FACE);this.drawCalls=0;}
 programFrom(vs,fs){let gl=this.gl;let compile=(type,src)=>{let sh=gl.createShader(type);gl.shaderSource(sh,src);gl.compileShader(sh);if(!gl.getShaderParameter(sh,gl.COMPILE_STATUS)){let msg=gl.getShaderInfoLog(sh);gl.deleteShader(sh);throw Error('着色器编译失败：'+msg);}return sh;};let v=compile(gl.VERTEX_SHADER,vs),f=compile(gl.FRAGMENT_SHADER,fs),p=gl.createProgram();gl.attachShader(p,v);gl.attachShader(p,f);gl.linkProgram(p);gl.deleteShader(v);gl.deleteShader(f);if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw Error('WebGL 程序链接失败：'+gl.getProgramInfoLog(p));return p;}
 loc(p,n){let key=this.uniforms.get(p);if(!key){key={};this.uniforms.set(p,key);}return key[n]??(key[n]=this.gl.getUniformLocation(p,n));}
 setupShadow(){
 const gl=this.gl;if(this.shadowTexture&&this.shadowTexture!==this.white)gl.deleteTexture(this.shadowTexture);if(this.shadowFBO)gl.deleteFramebuffer(this.shadowFBO);
 this.shadowEnabled=false;this.shadowFBO=null;this.shadowTexture=this.white;this.shadowSize=this.highQuality?2048:1024;
 for(const [internal,type] of [[gl.DEPTH_COMPONENT24,gl.UNSIGNED_INT],[gl.DEPTH_COMPONENT16,gl.UNSIGNED_SHORT]]){
  const tex=gl.createTexture(),fbo=gl.createFramebuffer();gl.bindTexture(gl.TEXTURE_2D,tex);
  gl.texImage2D(gl.TEXTURE_2D,0,internal,this.shadowSize,this.shadowSize,0,gl.DEPTH_COMPONENT,type,null);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
  gl.bindFramebuffer(gl.FRAMEBUFFER,fbo);gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.DEPTH_ATTACHMENT,gl.TEXTURE_2D,tex,0);gl.drawBuffers([gl.NONE]);gl.readBuffer(gl.NONE);
  const complete=gl.checkFramebufferStatus(gl.FRAMEBUFFER)===gl.FRAMEBUFFER_COMPLETE;const err=gl.getError();gl.bindFramebuffer(gl.FRAMEBUFFER,null);
  if(complete&&err===gl.NO_ERROR){this.shadowFBO=fbo;this.shadowTexture=tex;this.shadowEnabled=true;return;}
  gl.deleteFramebuffer(fbo);gl.deleteTexture(tex);for(let i=0;i<8&&gl.getError()!==gl.NO_ERROR;i++){}
 }
 if(window.SF_BOOT)window.SF_BOOT.warnings.push('阴影缓冲区不可用，已关闭动态阴影，玩法保持不变。');
 }
 resize(){let dpr=this.highQuality?Math.min(window.devicePixelRatio||1,1.5):1;let w=Math.round(innerWidth*dpr),h=Math.round(innerHeight*dpr);if(this.canvas.width!==w||this.canvas.height!==h){this.canvas.width=w;this.canvas.height=h;}this.width=w;this.height=h;}
 mesh(geo,dynamic=false){let gl=this.gl;let m={vao:gl.createVertexArray(),vbo:gl.createBuffer(),ibo:gl.createBuffer(),count:geo.indices.length,dynamic};gl.bindVertexArray(m.vao);gl.bindBuffer(gl.ARRAY_BUFFER,m.vbo);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(geo.data),dynamic?gl.DYNAMIC_DRAW:gl.STATIC_DRAW);gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,m.ibo);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint32Array(geo.indices),dynamic?gl.DYNAMIC_DRAW:gl.STATIC_DRAW);let lengths=[3,3,3,3,4,4,2],off=0;lengths.forEach((n,i)=>{gl.enableVertexAttribArray(i);gl.vertexAttribPointer(i,n,gl.FLOAT,false,88,off*4);off+=n;});gl.bindVertexArray(null);this.meshes.push(m);return m;}
 async texture(data,label="地面",required=false){let im=new Image(),timer;im.src=data;
 try{await Promise.race([im.decode(),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error(label+'纹理解码超时')),10000);})]);}
 catch(e){if(required)throw Error('[A02] '+label+'解码失败，请重新下载完整游戏文件。');if(window.SF_BOOT)window.SF_BOOT.warnings.push(label+'纹理不可用，已使用基础材质继续游戏。');return this.white;}finally{clearTimeout(timer);}let gl=this.gl,t=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,t);gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,false);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,im);gl.generateMipmap(gl.TEXTURE_2D);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR_MIPMAP_LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);let ext=gl.getExtension('EXT_texture_filter_anisotropic');if(ext)gl.texParameterf(gl.TEXTURE_2D,ext.TEXTURE_MAX_ANISOTROPY_EXT,Math.min(4,gl.getParameter(ext.MAX_TEXTURE_MAX_ANISOTROPY_EXT)));return t;}
 draw(item,shadow=false){let gl=this.gl,p=shadow?this.shadowProgram:this.program;gl.useProgram(p);gl.uniformMatrix4fv(this.loc(p,'uModel'),false,item.model||identity());gl.uniform1i(this.loc(p,'uSkin'),item.bones?1:0);if(item.bones)gl.uniformMatrix4fv(this.loc(p,'uBones[0]'),false,item.bones);if(!shadow){gl.uniform3fv(this.loc(p,'uTint'),item.tint||[1,1,1]);gl.uniform1f(this.loc(p,'uAlpha'),item.alpha??1);gl.uniform1f(this.loc(p,'uFlash'),item.flash||0);gl.uniform1i(this.loc(p,'uTextured'),item.texture?1:0);gl.uniform1i(this.loc(p,'uMaterialMode'),item.materialMode||0);gl.uniform1i(this.loc(p,'uUnlit'),item.unlit?1:0);gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,item.texture||this.white);}gl.bindVertexArray(item.mesh.vao);gl.drawElements(gl.TRIANGLES,item.mesh.count,gl.UNSIGNED_INT,0);this.drawCalls++;}
 render({eye,vp,opaque,transparent=[],particles=[],time=0,hero=[0,0,0],enemy=[0,0,0]}){let gl=this.gl;this.drawCalls=0;gl.enable(gl.DEPTH_TEST);gl.depthMask(true);gl.disable(gl.BLEND);if(this.shadowEnabled){gl.bindFramebuffer(gl.FRAMEBUFFER,this.shadowFBO);gl.viewport(0,0,this.shadowSize,this.shadowSize);gl.clear(gl.DEPTH_BUFFER_BIT);gl.enable(gl.POLYGON_OFFSET_FILL);gl.polygonOffset(1.4,2.0);gl.useProgram(this.shadowProgram);gl.uniformMatrix4fv(this.loc(this.shadowProgram,'uLightVP'),false,this.lightVP);for(let o of opaque)if(o.castShadow!==false)this.draw(o,true);gl.disable(gl.POLYGON_OFFSET_FILL);}
 gl.bindFramebuffer(gl.FRAMEBUFFER,null);gl.viewport(0,0,this.width,this.height);gl.clearColor(.08,.12,.16,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.disable(gl.DEPTH_TEST);gl.useProgram(this.skyProgram);gl.uniform1i(this.loc(this.skyProgram,"uStudio"),this.inspection>0?1:0);gl.uniform1f(this.loc(this.skyProgram,'uTime'),time);gl.uniform2f(this.loc(this.skyProgram,'uResolution'),this.width,this.height);gl.bindVertexArray(this.emptyVAO);gl.drawArrays(gl.TRIANGLES,0,3);gl.enable(gl.DEPTH_TEST);gl.useProgram(this.program);gl.uniform1i(this.loc(this.program,'uInspectionMode'),this.inspection||0);gl.uniform1i(this.loc(this.program,'uClay'),this.clay?1:0);gl.uniformMatrix4fv(this.loc(this.program,'uVP'),false,vp);gl.uniformMatrix4fv(this.loc(this.program,'uLightVP'),false,this.lightVP);gl.uniform3fv(this.loc(this.program,'uEye'),eye);gl.uniform3fv(this.loc(this.program,'uHero'),hero);gl.uniform3fv(this.loc(this.program,'uEnemy'),enemy);gl.uniform1f(this.loc(this.program,'uTime'),time);gl.uniform1i(this.loc(this.program,'uTexture'),0);gl.uniform1i(this.loc(this.program,'uShadow'),1);gl.uniform1i(this.loc(this.program,'uShadows'),this.shadowEnabled?1:0);gl.activeTexture(gl.TEXTURE1);gl.bindTexture(gl.TEXTURE_2D,this.shadowTexture);for(let o of opaque)this.draw(o);
 gl.enable(gl.BLEND);gl.depthMask(false);for(let o of transparent){gl.blendFunc(gl.SRC_ALPHA,o.additive?gl.ONE:gl.ONE_MINUS_SRC_ALPHA);this.draw(o);}if(particles.length){gl.blendFunc(gl.SRC_ALPHA,gl.ONE);gl.useProgram(this.particleProgram);gl.uniformMatrix4fv(this.loc(this.particleProgram,'uVP'),false,vp);gl.uniform1f(this.loc(this.particleProgram,'uHeight'),this.height);gl.bindVertexArray(this.particleVAO);gl.bindBuffer(gl.ARRAY_BUFFER,this.particleBuffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(particles),gl.DYNAMIC_DRAW);gl.drawArrays(gl.POINTS,0,particles.length/7);}gl.depthMask(true);gl.disable(gl.BLEND);gl.bindVertexArray(null);}
 project(pos,vp){let v=transform(vp,pos);return{x:(v[0]/v[3]*.5+.5)*innerWidth,y:(.5-v[1]/v[3]*.5)*innerHeight,visible:v[3]>0};}
}
S.Renderer=Renderer;
})();
