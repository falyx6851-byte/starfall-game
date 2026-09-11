from pathlib import Path
import base64,json,hashlib,difflib
R=Path(__file__).resolve().parents[1]
src=(R/'src/v013_engine.js').read_text()
s=src.replace('uniform int uMaterialMode;','uniform int uInspectionMode;uniform bool uClay;\nuniform int uMaterialMode;')
s=s.replace('vec3 bc=pow(max(base,vec3(.001)),vec3(2.2))','if(uClay){base=vec3(.55);rough=.83;metal=0.;}\n vec3 bc=pow(max(base,vec3(.001)),vec3(2.2))')
s=s.replace('vec3 key=vec3(2.5,2.15,1.68),f0=mix(vec3(.035),bc,metal);','if(uInspectionMode>0)hemi=mix(vec3(.24),vec3(.53),clamp(n.y*.5+.5,0.,1.));\n vec3 key=uInspectionMode>0?vec3(2.05):vec3(2.5,2.15,1.68),f0=mix(vec3(.035),bc,metal);')
s=s.replace('return .23+.77*sh/9.;','return uInspectionMode>0?.63+.37*sh/9.:.23+.77*sh/9.;')
s=s.replace('env+=vec3(1.8,1.53,1.04)*warm+vec3(.22,.58,.73)*cool;','env+=vec3(1.8,1.53,1.04)*warm+vec3(.22,.58,.73)*cool;\n if(uInspectionMode>0)env=mix(vec3(.22),vec3(.73),sky)+vec3(1.12)*warm+vec3(.58)*cool;')
s=s.replace('vec3(.10,.23,.28)*fill','(uInspectionMode>0?vec3(.29):vec3(.10,.23,.28))*fill')
s=s.replace('vec3(.24,.47,.56)*fill*.48','(uInspectionMode>0?vec3(.60):vec3(.24,.47,.56))*fill*.48')
s=s.replace('lit+=bc*vSurface.z*1.2;','if(!uClay)lit+=bc*vSurface.z*1.2;')
s=s.replace('vec3 color=pow(tone(lit),vec3(1./2.2));','vec3 color=pow(tone(lit),vec3(1./2.2)); if(uInspectionMode>0&&uMaterialMode==1){vec2 d=vWorld.xz-uHero.xz;float contact=1.-.12*exp(-dot(d,d)*4.);color=vec3(.86,.875,.873)*(.78+.22*sh)*contact;}')
s=s.replace('color=mix(color,vec3(.19,.28,.31),min(fog,.89));','if(uInspectionMode==0)color=mix(color,vec3(.19,.28,.31),min(fog,.89));')
s=s.replace('uniform float uTime;uniform vec2 uResolution;','uniform float uTime;uniform vec2 uResolution;uniform bool uStudio;')
s=s.replace('void main(){float y=uv.y;vec3 c=','void main(){if(uStudio){frag=vec4(vec3(.86,.875,.873),1.);return;}float y=uv.y;vec3 c=')
s=s.replace('gl.useProgram(this.skyProgram);gl.uniform1f','gl.useProgram(this.skyProgram);gl.uniform1i(this.loc(this.skyProgram,"uStudio"),this.inspection>0?1:0);gl.uniform1f')
s=s.replace("gl.useProgram(this.program);gl.uniformMatrix4fv(this.loc(this.program,'uVP')","gl.useProgram(this.program);gl.uniform1i(this.loc(this.program,'uInspectionMode'),this.inspection||0);gl.uniform1i(this.loc(this.program,'uClay'),this.clay?1:0);gl.uniformMatrix4fv(this.loc(this.program,'uVP')")
(R/'src/inspection-engine.js').write_text(s)
(R/'reports/renderer-inspection-only.patch').write_text(''.join(difflib.unified_diff(src.splitlines(True),s.splitlines(True),fromfile='v0.1.3/src/engine.js',tofile='sample/inspection-engine.js')))
payload={'glb':base64.b64encode((R/'assets/Stargazer_M04.glb').read_bytes()).decode(),'floor':'data:image/png;base64,'+base64.b64encode((R/'assets/arena.png').read_bytes()).decode(),'hash':hashlib.sha256((R/'assets/Stargazer_M04.glb').read_bytes()).hexdigest()}
parts=[s,(R/'src/v013_stonework.js').read_text(),(R/'src/v013_world.js').read_text(),'window.HERO_DATA='+json.dumps(payload,separators=(',',':'))+';',(R/'src/viewer.js').read_text()]
html=(R/'src/page.html').read_text().replace('/*STYLE*/',(R/'src/viewer.css').read_text()).replace('/*SCRIPTS*/','\n'.join(parts))
(R/'Stargazer_M04_PREVIEW.html').write_text(html)
print('Preview built:',len(html),'GLB',len(payload['glb']))
