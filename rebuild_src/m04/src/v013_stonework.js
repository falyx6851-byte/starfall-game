/* Visual-only masonry. Tile bevels have no collision or gameplay role. */
'use strict';
(()=>{const S=window.SF,G=S.Geometry,M=S.M;
const pi=Math.PI,TAU=pi*2;
function clip(poly,normal,d){let out=[];for(let i=0;i<poly.length;i++){let a=poly[i],b=poly[(i+1)%poly.length],da=a[0]*normal[0]+a[1]*normal[1]-d,db=b[0]*normal[0]+b[1]*normal[1]-d;if(da<=0)out.push(a);if((da<=0)!==(db<=0)){let t=da/(da-db);out.push([a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t]);}}return out;}
function circleClip(poly,r=9.73){for(let i=0;i<96&&poly.length>2;i++){let a=(i+.5)*TAU/96;poly=clip(poly,[Math.sin(a),Math.cos(a)],r);}return poly;}
function tile(g,poly,co,top=.063,bevel=.027,depth=.075){
 if(poly.length<3)return;let cx=poly.reduce((t,p)=>t+p[0],0)/poly.length,cz=poly.reduce((t,p)=>t+p[1],0)/poly.length;
 let o=poly.map(([x,z])=>{let d=Math.hypot(x-cx,z-cz)||1;return[x+(cx-x)*.012/d,top-bevel,z+(cz-z)*.012/d];});
 let inner=o.map(([x,y,z])=>{let d=Math.hypot(x-cx,z-cz)||1;return[x+(cx-x)*bevel/d,top,z+(cz-z)*bevel/d];});
 const uv=p=>[.5+p[0]/20.68,.5+p[2]/20.68];
 for(let i=0;i<poly.length;i++){let j=(i+1)%poly.length,a=inner[i],b=inner[j],c=[cx,top,cz],aa=o[i],bb=o[j];
  // Facing is deliberately +Y. Broad faces are flat, bevels form the turning planes.
  g.tri(a,c,b,co,[.9,.01,0],[uv(a),uv(c),uv(b)]);
  g.quad(a,b,bb,aa,co.map(x=>x*1.08),[.88,.01,0],[uv(a),uv(b),uv(bb),uv(aa)]);
  g.quad(aa,bb,[bb[0],top-depth,bb[2]],[aa[0],top-depth,aa[2]],co.map(x=>x*.63),[.97,0,0]);
 }
}
function stoneFloor(){let g=new G();let seed=713;const rnd=()=>{seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;};
 // Offset ashlar courses, intentionally varied slab widths and tonality.
 let zs=[-10,-8.2,-6.35,-4.37,-2.30,-.15,1.9,3.95,5.85,7.85,10];
 for(let row=0;row<zs.length-1;row++){
  let x=-11-(row%3)*.76,z=zs[row],zz=zs[row+1];
  while(x<10){let w=1.76+rnd()*1.32,xx=x+w;let cut=.06+rnd()*.065;let poly=circleClip([[x+cut,z+.012],[xx-cut*.7,z+.012],[xx-.012,z+cut],[xx-.012,zz-cut*.7],[xx-cut,zz-.012],[x+cut*.7,zz-.012],[x+.012,zz-cut],[x+.012,z+cut*.7]]);
   let k=(rnd()-.5)*.055,warm=rnd()>.73;let co=[.303+k+(warm?.017:0),.352+k,.368+k-(warm?.021:0)];tile(g,poly,co,.062+(rnd()-.5)*.006,.025,.07);x=xx;}
 }
 // Eight massive central voussoirs, not 48 radial tick marks.
 for(let i=0;i<8;i++){
  let a=i*TAU/8+.003,b=(i+1)*TAU/8-.003,poly=[[Math.sin(a)*.77,Math.cos(a)*.77]];
  for(let k=0;k<=12;k++){let q=a+(b-a)*k/12;poly.push([Math.sin(q)*2.78,Math.cos(q)*2.78]);}
  poly.push([Math.sin(b)*.77,Math.cos(b)*.77]);let k=(i%3-1)*.014;tile(g,poly,[.312+k,.348+k,.359+k],.073,.012,.05);
 }
 let poly=[];for(let i=0;i<32;i++){let a=i*TAU/32;poly.push([Math.sin(a)*.76,Math.cos(a)*.76]);}tile(g,poly,[.294,.337,.35],.075,.014,.05);
 return g;
}
function sanctuaryInlay(){let g=new G(),gold=[.38,.332,.233],stone=[.294,.341,.35];
 g.ring(2.755,2.775,.080,gold,[.62,.48,0],128);
 g.ring(8.44,8.458,.078,[.32,.317,.252],[.67,.36,0],192);
 // The center oath star is retained as one quiet inlaid contour.
 let pts=[];for(let i=0;i<16;i++){let a=i*TAU/16,r=i%2?.92:(i%4?1.88:2.32);pts.push([Math.sin(a)*r,.081,Math.cos(a)*r]);}
 for(let i=0;i<pts.length;i++){let a=pts[i],b=pts[(i+1)%pts.length],v=M.norm(M.cross(M.sub(b,a),[0,1,0])),d=M.scale(v,.012);g.quad(M.add(a,d),M.sub(a,d),M.sub(b,d),M.add(b,d),gold,[.56,.56,0]);}
 g.ring(.32,.334,.082,gold,[.54,.52,0],48);
 return g;
}
S.Stonework={clip,circleClip,tile,stoneFloor,sanctuaryInlay};})();
