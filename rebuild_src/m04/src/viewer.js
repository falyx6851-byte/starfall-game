/* M04 asset-review host. Uses v0.1.3 GLB adapter, Animator and rendering passes.
   No combat controller is loaded and no source game files are modified. */
'use strict';
(async()=>{
 const $=id=>document.getElementById(id),S=window.SF,M=S.M;
 const fail=err=>{$('loading').hidden=true;$('fatal').hidden=false;$('error-message').textContent=String(err.message||err);console.error(err);};
 window.addEventListener('error',e=>fail(e.error||e.message));window.addEventListener('unhandledrejection',e=>fail(e.reason));
 try{
 window.SF_BOOT={warnings:[]};const canvas=$('viewport'),r=new S.Renderer(canvas);r.highQuality=true;r.setupShadow();r.resize();
 const asset=S.parseGLB(HERO_DATA.glb),mesh=r.mesh(asset.geometry),texture=await r.texture(asset.textureData,'逐星者内嵌图集',true),anim=new S.Animator(asset);
 const floorTexture=await r.texture(HERO_DATA.floor,'v0.1.3 地面'),world=new S.World(r,floorTexture);
 const g=new S.Geometry();g.quad([-100,-.005,-100],[-100,-.005,100],[100,-.005,100],[100,-.005,-100],[.74,.75,.75],[.95,0,0]);const studioFloor=r.mesh(g);
 const lightGame=r.lightVP,lightStudio=M.mul(M.ortho(-2.6,2.6,-2.6,2.6,.1,28),M.lookAt([-6,10,5.2],[0,1.35,0]));
 let state={view:'reference',theta:-.46,phi:1.435,distance:6.8,target:[0,1.40,0],clip:'DesignPose',time:0,playing:false,rotate:false,gray:true,gameLight:false,clean:false,manual:false};
 let vp,eye,last=0,frame=0,drag=null,raf=0;
 const names={reference:'参考角度',front:'正面',side:'披肩侧面',back:'背面',head:'披肩近景',combat:'v0.1.3 战斗机位复现'};
 const clips={DesignPose:'造型静置',Idle:'待机',Run:'跑步',Attack1:'普通攻击 1'};
 function pose(){anim.set(state.clip,1,false);anim.prev=null;anim.fade=0;anim.time=state.time;anim.update(0);}
 function sync(){document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===state.view));$('material').classList.toggle('active',!state.gray);$('clay').classList.toggle('active',state.gray);$('game-light').checked=state.gameLight;$('animation').value=state.clip;$('play').textContent=state.playing?'暂停动作':'播放动作';$('play').classList.toggle('active',state.playing);$('rotate').classList.toggle('active',state.rotate);let dur=asset.clips[state.clip].duration;$('scrub').max=dur;$('scrub').value=state.time;$('clock').textContent=state.time.toFixed(2)+' / '+dur.toFixed(2)+' s';$('clip-label').textContent=clips[state.clip]||state.clip;$('view-label').textContent=names[state.view]+(state.gray?' · 中性灰模':'')+(state.view==='combat'?' · 原机位 / 原缩放 / 非游戏接入':state.gameLight?' · 原游戏光照':' · 中性棚光');document.body.classList.toggle('game',state.view==='combat');document.body.classList.toggle('clean',state.clean);$('show-ui').hidden=!state.clean;}
 function preset(v){
  state.view=v;state.target=[0,1.4,0];state.distance=6.8;state.phi=1.435;state.theta={reference:-.46,front:0,side:-Math.PI/2,back:Math.PI,head:-.38}[v]??0;
  if(v==='head'){state.target=[-.29,1.84,-.02];state.distance=2.35;state.phi=1.47;state.theta=-.42;}
  state.rotate=false;sync();draw();
 }
 function draw(){
  r.resize();const battle=state.view==='combat';r.inspection=battle||state.gameLight?0:1;r.clay=state.gray;r.lightVP=battle?lightGame:lightStudio;
  pose();let model;
  if(battle){
   const p={x:-1.4,z:1.1},e={x:1.4,z:-1.6};
   const focus=[p.x*.62+e.x*.22,p.z*.57+e.z*.16];let pull=Math.max(0,1.45-r.width/r.height)*9;
   eye=[focus[0],15+pull*.72,17.8+pull+focus[1]];vp=M.mul(M.perspective(42*Math.PI/180,r.width/r.height,.1,180),M.lookAt(eye,[focus[0],.62,focus[1]]));
   model=M.compose([p.x,.051,p.z],M.yaw(3.02),[1.05,1.05,1.05]);
   const scene=world.collect(12);scene.particles=[];scene.opaque.push({mesh,texture,bones:anim.bones,model,materialMode:2});
   r.render({...scene,eye,vp,time:12,hero:[p.x,0,p.z],enemy:[e.x,0,e.z]});
  }else{
   eye=M.add(state.target,[Math.sin(state.theta)*Math.sin(state.phi)*state.distance,Math.cos(state.phi)*state.distance,Math.cos(state.theta)*Math.sin(state.phi)*state.distance]);
   vp=M.mul(M.perspective(31*Math.PI/180,r.width/r.height,.05,170),M.lookAt(eye,state.target));model=M.identity();
   r.render({eye,vp,time:12,hero:[0,0,0],enemy:[99,0,99],opaque:[{mesh:studioFloor,materialMode:1,castShadow:false},{mesh,texture,bones:anim.bones,model,materialMode:2}]});
  }
  frame++;
 }
 function tick(now){let dt=last?Math.min((now-last)/1000,.045):0;last=now;
  if(!state.manual){if(state.playing){let duration=asset.clips[state.clip].duration;state.time=(state.time+dt)%duration;}if(state.rotate&&state.view!=='combat')state.theta+=dt*.32;draw();sync();}
  raf=requestAnimationFrame(tick);
 }
 canvas.addEventListener('pointerdown',e=>{if(state.view==='combat')return;drag={x:e.clientX,y:e.clientY,button:e.button};canvas.setPointerCapture(e.pointerId);canvas.classList.add('dragging');state.rotate=false;});
 canvas.addEventListener('pointermove',e=>{if(!drag)return;let dx=e.clientX-drag.x,dy=e.clientY-drag.y;drag.x=e.clientX;drag.y=e.clientY;if(drag.button===2||e.shiftKey){let q=state.distance*.00085;state.target[0]-=dx*q*Math.cos(state.theta);state.target[2]+=dx*q*Math.sin(state.theta);state.target[1]+=dy*q;}else{state.theta-=dx*.007;state.phi=M.clamp(state.phi-dy*.006,.15,Math.PI-.10);}draw();});
 const stopDrag=()=>{drag=null;canvas.classList.remove('dragging');};canvas.addEventListener('pointerup',stopDrag);canvas.addEventListener('pointercancel',stopDrag);canvas.addEventListener('contextmenu',e=>e.preventDefault());
 canvas.addEventListener('wheel',e=>{e.preventDefault();if(state.view!=='combat'){state.distance=M.clamp(state.distance*Math.exp(e.deltaY*.001),1.05,13);draw();}},{passive:false});
 document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>preset(b.dataset.view));
 $('material').onclick=()=>{state.gray=false;sync();draw();};$('clay').onclick=()=>{state.gray=true;sync();draw();};
 $('game-light').onchange=e=>{state.gameLight=e.target.checked;sync();draw();};
 $('animation').onchange=e=>{state.clip=e.target.value;state.time=0;state.playing=state.clip!=='DesignPose';sync();draw();};
 $('play').onclick=()=>{state.playing=!state.playing;sync();};$('rotate').onclick=()=>{if(state.view==='combat')preset('reference');state.rotate=!state.rotate;sync();};
 $('scrub').oninput=e=>{state.playing=false;state.time=+e.target.value;sync();draw();};
 $('export').onclick=()=>{let bytes=Uint8Array.from(atob(HERO_DATA.glb),x=>x.charCodeAt(0));let url=URL.createObjectURL(new Blob([bytes],{type:'model/gltf-binary'}));let a=document.createElement('a');a.href=url;a.download='Stargazer_M04.glb';a.click();setTimeout(()=>URL.revokeObjectURL(url),5000);};
 const hide=()=>{state.clean=!state.clean;sync();};$('show-ui').onclick=hide;window.addEventListener('keydown',e=>{if(e.key.toLowerCase()==='h')hide();if(e.key===' '&&!['INPUT','SELECT'].includes(document.activeElement.tagName)){e.preventDefault();state.playing=!state.playing;sync();}});
 canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();cancelAnimationFrame(raf);fail(Error('WebGL 上下文已丢失。请重新载入此页面。'));});window.addEventListener('resize',draw);
 window.__HERO_SAMPLE__={
  ready:true,state,asset,anim,renderer:r,mesh,hash:HERO_DATA.hash,
  set(o={}){if(o.view)preset(o.view);Object.assign(state,o);sync();draw();return this.report();},
  draw,report(){return{version:'M04',modelSHA256:HERO_DATA.hash,clip:state.clip,time:state.time,view:state.view,gray:state.gray,eye,vp:Array.from(vp),frame,metadata:asset.metadata,renderer:r.gl.getParameter(r.gl.RENDERER),width:r.width,height:r.height,glError:r.gl.getError(),shadowSize:r.shadowSize,bonesFinite:Array.from(anim.bones).every(Number.isFinite)};},
  vertices(){let g=asset.geometry.data,out=[];for(let i=0;i<g.length;i+=22){let p=[0,0,0];for(let k=0;k<4;k++){let w=g[i+16+k];if(w){let j=g[i+12+k],v=M.transform(anim.bones.subarray(j*16,j*16+16),g.slice(i,i+3));p=p.map((n,q)=>n+v[q]*w);}}out.push(p);}return out;}
 };
 sync();draw();$('loading').hidden=true;$('health').textContent='WebGL 2 · 本地资源已载入';raf=requestAnimationFrame(tick);
 }catch(err){fail(err);}
})();
