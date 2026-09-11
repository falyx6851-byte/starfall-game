from pathlib import Path
import numpy as np, math
from PIL import Image, ImageDraw, ImageFilter
R=Path(__file__).resolve().parents[1];w=1536;y,x=np.mgrid[:w,:w];u=x/w;v=y/w
# Mineral fields follow broad swathes; stronger age is confined to the perimeter.
cloud=np.sin(u*16+np.sin(v*7)*1.3)*.7+np.sin(v*19-u*9)*.6+np.sin(u*33+v*13)*.25
r=np.sqrt((u-.5)**2+(v-.5)**2)*2
age=np.clip((r-.58)*2.5,0,1)
vein=np.exp(-np.square(np.sin(u*18-v*11+np.sin(v*9)))*170)*1.6
rgb=np.zeros((w,w,3));rgb[:]=[205,208,207];rgb+=(cloud*(16+age*6)-vein)[...,None]
rgb[:,:,0]+=age*np.sin(v*5+u*9)*3;rgb[:,:,2]-=age*4
height=np.full((w,w),160.)+cloud*32
im=Image.fromarray(np.dstack([np.clip(rgb,0,255),np.clip(height,0,255)]).astype('uint8'),'RGBA');d=ImageDraw.Draw(im)
# Six authored branching fissures stop outside the calm central medallion.
for pts in [[(-7.9,4.9),(-7.35,4.48),(-7.02,4.34),(-6.8,3.91)],[(6.4,5.9),(5.99,5.44),(5.93,5.03)],[(7.4,-5.3),(7.1,-5.61),(6.79,-5.85)], [(-6.15,-6.63),(-5.96,-6.1),(-5.55,-5.96)],[(2.3,8.4),(2.50,7.83),(2.25,7.5)], [(-3.7,7.1),(-3.25,7.35),(-2.84,7.38)]]:
 p=[(w*(.5+xx/20.68),w*(.5+zz/20.68)) for xx,zz in pts];d.line(p,fill=(122,138,144,96),width=2);d.line([(a+2,b+1) for a,b in p],fill=(214,215,209,185),width=1)
im.save(R/'assets/textures/arena.png',optimize=True);print('stone surface baked',flush=True)
