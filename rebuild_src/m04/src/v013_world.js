/* v0.1.3 art remaster. World meshes are decorative only; Combat owns collision. */
'use strict';
(()=>{const S=window.SF,G=S.Geometry,M=S.M,{compose,yaw,quatEuler}=M,TAU=Math.PI*2;
const STONE=[.32,.355,.364],LIMESTONE=[.37,.397,.389],BRASS=[.43,.342,.209];
function block(w,h,d,co=STONE,b=.07){let g=new G();b=Math.min(b,w*.2,h*.24,d*.2);
 const outline=(ww,dd,cut)=>[[-ww/2+cut,-dd/2],[ww/2-cut,-dd/2],[ww/2,-dd/2+cut],[ww/2,dd/2-cut],[ww/2-cut,dd/2],[-ww/2+cut,dd/2],[-ww/2,dd/2-cut],[-ww/2,-dd/2+cut]];
 let levels=[[0,w-b*1.4,d-b*1.4],[b,w,d],[h-b,w,d],[h,w-b*1.1,d-b*1.1]],rings=levels.map(([y,ww,dd])=>outline(ww,dd,b).map(([x,z])=>[x,y,z]));
 for(let k=0;k<3;k++)for(let i=0;i<8;i++){let j=(i+1)%8;g.quad(rings[k][i],rings[k+1][i],rings[k+1][j],rings[k][j],co,[.89,.015,0]);}
 for(let i=0;i<8;i++)g.tri([0,h,0],rings[3][i],rings[3][(i+1)%8],co,[.9,.015,0]);return g;}
function arch(radius,thick,depth,start=0,end=Math.PI,parts=12,co=LIMESTONE,missing=[]){let g=new G();for(let i=0;i<parts;i++){if(missing.includes(i))continue;let a=start+(end-start)*(i+.025)/parts,b=start+(end-start)*(i+.975)/parts;let pts=[[Math.cos(a)*radius,Math.sin(a)*radius],[Math.cos(a)*(radius+thick),Math.sin(a)*(radius+thick)],[Math.cos(b)*(radius+thick),Math.sin(b)*(radius+thick)],[Math.cos(b)*radius,Math.sin(b)*radius]];g.merge(new G().prism(pts,depth,co.map(x=>x*(.98+(i%3)*.014)),[.88,.02,0]));}return g;}
class World{
 constructor(r,texture){this.r=r;this.texture=texture;this.seed=13713;this.braziers=[];this.motes=[];
 this.static=this.build();this.floorMesh=r.mesh(S.Stonework.stoneFloor());this.inlayMesh=r.mesh(S.Stonework.sanctuaryInlay());
 this.flameMesh=r.mesh(new G().loft([[0,.02,.025],[.10,.11,.09],[.32,.062,.05,.04],[.55,0,0,-.02]],9,[.82,.38,.115],[.7,0,1.5]));
 for(let i=0;i<18;i++)this.motes.push({x:(this.rand()-.5)*23,z:(this.rand()-.5)*23,y:1+this.rand()*3,p:this.rand()*TAU});
 }
 rand(){this.seed=(1664525*this.seed+1013904223)>>>0;return this.seed/4294967296;}
 build(){let g=new G();const p=(r,y,a)=>[Math.sin(a)*r,y,Math.cos(a)*r];
 // The foundation is stacked radial masonry above a shallow stratified escarpment.
 let count=40;
 for(let i=0;i<count;i++){let a=i*TAU/count+.002,b=(i+1)*TAU/count-.002;let damaged=[5,6,18,27,28].includes(i);let outer=damaged?9.92:10.24;let co=STONE.map(x=>x+((i%4)-1.5)*.009),y=.06-(damaged?.04:0);
  g.quad(p(9.735,y,a),p(outer-.03,y,a),p(outer-.03,y,b),p(9.735,y,b),co,[.9,0,0]);
  g.quad(p(outer-.03,y,a),p(outer,y-.045,a),p(outer,y-.045,b),p(outer-.03,y,b),co.map(x=>x*1.06),[.9,0,0]);
  g.quad(p(outer,y-.045,a),p(outer,-.28,a),p(outer,-.28,b),p(outer,y-.045,b),co.map(x=>x*.85),[.94,0,0]);
  g.quad(p(outer,-.28,a),p(10.35,-.34,a),p(10.35,-.34,b),p(outer,-.28,b),[.26,.30,.31],[.9,0,0]);
  g.quad(p(10.35,-.34,a),p(10.16,-.79,a),p(10.16,-.79,b),p(10.35,-.34,b),[.236,.275,.294],[.94,0,0]);
  let ro=10.03+(i%3)*.05;g.quad(p(ro,-.82,a),p(ro,-1.28,a),p(ro,-1.28,b),p(ro,-.82,b),[.255,.288,.30],[.95,0,0]);
  let rm=9.6+this.rand()*.38;g.quad(p(10.13,-1.30,a),p(rm,-2.8,a+.025),p(rm,-2.76,b),p(10.13,-1.30,b),[.177,.229,.252],[.99,0,0]);
 }
 // Deliberate missing stones and a few low fragments. No obstacle enters r=9.35.
 for(let [a,c] of [[.87,3],[2.90,4],[4.36,3]])for(let i=0;i<c;i++){
  let r=9.90+(i%2)*.28,angle=a+(i-c/2)*.047;g.merge(block(.32+i*.045,.12+(i%2)*.06,.29,[.32,.358,.355],.042),compose(p(r,-.08-i*.045,angle),quatEuler(.06,angle+i*.41,-.08*i)));
 }
 // Three pieces of old parapet frame the rim without forming a new enclosing wall.
 for(let [a,h,l] of [[-1.11,.43,1.20],[1.57,.26,1.48],[2.77,.30,1.05]]){
  let pp=p(10.08,0,a);g.merge(block(l,h,.45,STONE,.065),compose(pp,yaw(a)));g.merge(block(l+.10,.10,.52,LIMESTONE,.025),compose([pp[0],h-.015,pp[2]],yaw(a)));
 }
 // A low, fully framed broken sanctuary arch: its crown stays below the default HUD.
 let gate=new G();for(let sg of [-1,1]){
  gate.merge(block(.82,.17,.87,STONE),compose([sg*1.37,0,0]));
  gate.merge(block(.64,1.58,.61,LIMESTONE,.075),compose([sg*1.37,.16,0]));
  gate.merge(block(.77,.18,.72,STONE,.035),compose([sg*1.37,1.72,0]));
  gate.merge(block(.12,1.15,.035,[.17,.255,.284],.006),compose([sg*1.37,.46,.309]));
  gate.merge(block(.25,.052,.048,BRASS,.01),compose([sg*1.37,1.53,.317]));
 }
 gate.merge(arch(1.08,.40,.64,0,Math.PI,14,LIMESTONE,[3,4]),compose([0,1.86,0]));
 // A fallen keystone sits on its own ledge rather than hovering in a gap.
 gate.merge(block(.37,.24,.44,BRASS,.035),compose([1.72,.21,.30],quatEuler(.1,0,-.26)));
 g.merge(gate,compose([-3.80,-.34,-11.35],yaw(.025)));
 // Rear sanctuary landing. Separate steps read as a structure, not a circular dial.
 for(let i=0;i<4;i++)g.merge(block(3.95,.22,.79,STONE,.045),compose([-3.8,-.13-i*.105,-9.22-i*.70]));
 g.merge(block(4.08,.41,2.30,STONE,.08),compose([-3.8,-.69,-11.25]));
 g.merge(block(3.72,2.20,1.82,[.19,.25,.28],.12),compose([-3.8,-2.89,-11.42]));
 // Two short inset-energy pylons, not a forest of oversized hovering crystals.
 for(let sg of [-1,1]){
  let x=sg*9.60,z=-4.1;g.merge(block(.82,.22,.82,STONE),compose([x,-.08,z],yaw(sg*.24)));
  let post=new G();post.merge(block(.52,1.35,.56,LIMESTONE,.075));post.merge(block(.63,.12,.64,STONE,.03),compose([0,1.24,0]));
  post.merge(new G().prism([[-.105,.55],[0,.32],[.105,.55],[.06,1.0],[0,1.18],[-.06,1.0]],.035,[.10,.37,.40],[.45,.22,.35]),compose([0,0,.28]));
  post.merge(block(.22,.056,.049,BRASS,.012),compose([0,.43,.287]));g.merge(post,compose([x,.13,z],yaw(sg*.24)));
 }
 // Bronze fire bowls are restrained, outside the fight disc.
 for(let sg of [-1,1]){
  let x=sg*10.12,z=2.2;let bowl=new G();bowl.merge(block(.58,.13,.58,STONE,.045));
  bowl.merge(new G().loft([[.1,.24,.24],[.24,.17,.17],[.59,.13,.13],[.65,.24,.24],[.84,.41,.41],[.91,.42,.42]],16,BRASS,[.47,.73,0]));
  bowl.merge(new G().loft([[.883,.36,.36],[.901,.33,.33]],16,[.07,.08,.082],[1,0,0]));g.merge(bowl,compose([x,-.01,z]));this.braziers.push([x,.89,z]);
 }
 // Moss collects in three sheltered fracture pockets, never across the combat center.
 for(let [a,r] of [[.84,9.82],[2.91,10.0],[4.35,9.92]])for(let k=0;k<7;k++){
  let q=a+(k-3)*.018,rr=r+(k%2)*.09,x=Math.sin(q)*rr,z=Math.cos(q)*rr;g.merge(block(.15+(k%3)*.05,.011,.14,[.126,.226,.196],.004),compose([x,.069,z],yaw(q+k)));
 }
 // A broken aqueduct recedes into the valley. Real arch openings, depth and supports.
 let bridge=new G();const farStone=[.211,.266,.288];
 for(let i=0;i<4;i++){
  let x=i*3.65;bridge.merge(block(.86,4.6,.98,farStone,.08),compose([x,-4.6,0]));bridge.merge(block(1.13,.22,1.14,farStone,.035),compose([x,-.1,0]));
  if(i<3){bridge.merge(arch(1.34,.33,1.00,0,Math.PI,11,farStone,i===2?[2,3,4,5,6,7]:[]),compose([x+1.825,-1.41,0]));if(i!==2)bridge.merge(block(3.55,.20,1.26,farStone,.035),compose([x+1.825,.15,0]));}
 }
 g.merge(bridge,compose([-21,-4.25,-21],yaw(-.31)));
 // Distant bell-tower ruin is attached to a single island and terrace, not floating posts.
 let farCo=[.185,.246,.271],island=new G();
 island.merge(block(5.4,.38,3.6,farCo,.13),compose([0,0,0]));
 island.merge(block(1.30,3.4,1.40,farCo,.09),compose([-1.10,.26,0]));
 island.merge(block(1.30,3.4,1.40,farCo,.09),compose([1.10,.26,0]));
 island.merge(arch(.63,.49,1.40,0,Math.PI,10,farCo,[1,2]),compose([0,3.66,0]));
 island.merge(block(3.15,.25,1.65,farCo,.04),compose([0,4.59,0]));
 // Partial parapet gives the ruined tower an asymmetric crown.
 island.merge(block(.45,.62,1.45,farCo,.07),compose([-1.18,4.80,.02]));
 island.merge(block(.60,.26,1.45,farCo,.05),compose([1.06,4.80,.02]));
 g.merge(island,compose([18,-9.8,-27.5],yaw(-.18)));
 // Sculpted strata support the far architecture. The near flanks remain open valley.
 for(let [x,y,z,wx,wz] of [[18,-10.0,-27.5,3.7,2.4],[-21,-8.8,-21.0,2.5,1.8],[-10.5,-8.8,-24.6,2.2,1.5]]){
  let rock=new G(),N=32,rows=[[-18,.40],[-9,.68],[-3,.88],[-.55,1.0],[0,.93]],rr=[];
  for(let [yy,sc] of rows)rr.push(Array.from({length:N},(_,i)=>{let a=i*TAU/N;let deform=1+.10*Math.sin(a*3+.7)+.052*Math.cos(a*7);return[Math.sin(a)*wx*sc*deform,yy+Math.sin(a*4)*.12,Math.cos(a)*wz*sc*deform];}));
  for(let k=0;k<rr.length-1;k++)for(let i=0;i<N;i++){let j=(i+1)%N;rock.quad(rr[k][i],rr[k][j],rr[k+1][j],rr[k+1][i],[.127+(i%5)*.004,.196+(i%5)*.003,.224+(i%5)*.003],[1,0,0]);}
  for(let i=0;i<N;i++)rock.tri([0,0,0],rr.at(-1)[i],rr.at(-1)[(i+1)%N],[.17,.23,.251],[1,0,0]);
  g.merge(rock,compose([x,y,z]));
 }
 this.backgroundDesign={gate:{center:[-3.8,-.34,-11.35],height:3.34},aqueduct:true,sideBillboards:false};return this.r.mesh(g);
 }
 collect(time){let opaque=[{mesh:this.static},{mesh:this.floorMesh,texture:this.texture,materialMode:1,castShadow:false},{mesh:this.inlayMesh,castShadow:false}],particles=[];
 for(let b of this.braziers){for(let i=0;i<2;i++){let q=time*2+i*2;opaque.push({mesh:this.flameMesh,model:compose([b[0]+Math.sin(q)*.038,b[1],b[2]+Math.cos(q)*.03],yaw(q),[.86,.83+.09*Math.cos(q),.86]),castShadow:false});}particles.push(b[0],b[1]+.14,b[2],.53,.20,.045,.33);}
 for(let m of this.motes){particles.push(m.x+Math.sin(time*.2+m.p)*.13,(m.y+time*.04)%4,m.z,.13,.29,.32,.018);}
 return{opaque,transparent:[],particles};}
}
S.World=World;})();
