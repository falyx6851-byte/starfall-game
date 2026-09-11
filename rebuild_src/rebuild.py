from pathlib import Path
import shutil, subprocess, sys, hashlib, json
ROOT=Path.cwd(); SRC=ROOT/'rebuild_src'; BUILD=ROOT/'_rebuild_work'
if BUILD.exists(): shutil.rmtree(BUILD)
BUILD.mkdir()

def cpdir(src,dst):
    shutil.copytree(src,dst,dirs_exist_ok=True)
def run(cmd,cwd):
    print('+', ' '.join(map(str,cmd)), 'cwd=',cwd, flush=True)
    subprocess.run(cmd,cwd=cwd,check=True)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

# A01 exact rebuild from compact animation donor.
a01=BUILD/'a01'; cpdir(SRC/'a01',a01); (a01/'assets').mkdir(exist_ok=True); (a01/'reports').mkdir(exist_ok=True)
run([sys.executable,'authoring/build_hero.py'],a01)
assert sha(a01/'assets/Stargazer_A01.glb')=='6fa0bc5bb56a53e5369b83fb28674c1717c472ba1c56827938316296521c4815'
# H01 exact rebuild.
h01=BUILD/'h01'; cpdir(SRC/'h01',h01); (h01/'assets').mkdir(exist_ok=True); (h01/'reports').mkdir(exist_ok=True)
shutil.copy2(a01/'assets/Stargazer_A01.glb', h01/'authoring/A01_BASE.glb')
run([sys.executable,'authoring/rebuild_helmet.py'],h01)
assert sha(h01/'assets/Stargazer_H01.glb')=='21a38ba0a12994084b85ef52a34eecc39dc3b99028c8d31d6b83b6a8b088bbc1'
# Arena exact rebuild.
arena=BUILD/'arena'; cpdir(SRC/'arena',arena); (arena/'assets/textures').mkdir(parents=True,exist_ok=True)
run([sys.executable,'tools/remaster_textures.py'],arena)
assert sha(arena/'assets/textures/arena.png')=='693785ba87b7dafda76558e3afbde95e64960f7778528638cf2a9a0afeeecaa4'
# M03 exact rebuild.
m03=BUILD/'m03'; cpdir(SRC/'m03',m03); (m03/'assets').mkdir(exist_ok=True); (m03/'reports').mkdir(exist_ok=True)
shutil.copy2(h01/'assets/Stargazer_H01.glb',m03/'authoring/H01_BASE.glb')
shutil.copy2(arena/'assets/textures/arena.png',m03/'assets/arena.png')
run([sys.executable,'authoring/build_mantle.py'],m03)
run([sys.executable,'authoring/build_preview.py'],m03)
assert sha(m03/'assets/Stargazer_M03.glb')=='f98d23b9ea1d908bef1025ef884fdd276c3d56f0e3329da3a7b249b02f2f6f72'
assert sha(m03/'Stargazer_M03_PREVIEW.html')=='2a8e34c8cedb9a638792d708a31c7145ded19db11a5fd60f05dea094ab799ff3'
# M04 exact rebuild.
m04=BUILD/'m04'; cpdir(SRC/'m04',m04); (m04/'assets').mkdir(exist_ok=True); (m04/'reports').mkdir(exist_ok=True)
shutil.copy2(h01/'assets/Stargazer_H01.glb',m04/'authoring/H01_BASE.glb')
shutil.copy2(m03/'assets/Stargazer_M03.glb',m04/'assets/Stargazer_M03.glb')
shutil.copy2(m03/'reports/mantle_authoring.npz',m04/'reports/mantle_authoring.npz')
shutil.copy2(arena/'assets/textures/arena.png',m04/'assets/arena.png')
run([sys.executable,'authoring/build_mantle.py'],m04)
run([sys.executable,'authoring/build_preview.py'],m04)
assert sha(m04/'assets/Stargazer_M04.glb')=='1fc1da387de71cb674660e71549d6bb0d575bb697710277e403891f5fdac1b9e'
assert sha(m04/'Stargazer_M04_PREVIEW.html')=='d5ee27cce5c9485ea9189a012f60fc023304e31eed90b591c22afe5b2c4e3a66'
# Materialize repository handoff paths.
base=ROOT/'baselines/M03'; cand=ROOT/'candidates/M04'
for d in [base/'authoring',base/'reports',cand/'authoring',cand/'reports',ROOT/'evidence/M03',ROOT/'evidence/M04']:
    d.mkdir(parents=True,exist_ok=True)
shutil.copy2(m03/'assets/Stargazer_M03.glb',base/'Stargazer_M03.glb')
shutil.copy2(m03/'Stargazer_M03_PREVIEW.html',base/'Stargazer_M03_PREVIEW.html')
shutil.copy2(SRC/'m03/authoring/build_mantle.py',base/'authoring/build_mantle.py')
shutil.copy2(SRC/'m03/authoring/glb_io.py',base/'authoring/glb_io.py')
shutil.copy2(SRC/'reports/Stargazer_M03_REPORT.md',base/'reports/Stargazer_M03_REPORT.md')
shutil.copy2(m04/'assets/Stargazer_M04.glb',cand/'Stargazer_M04.glb')
shutil.copy2(m04/'Stargazer_M04_PREVIEW.html',cand/'Stargazer_M04_PREVIEW.html')
shutil.copy2(SRC/'m04/authoring/build_mantle.py',cand/'authoring/build_mantle.py')
shutil.copy2(SRC/'m04/authoring/glb_io.py',cand/'authoring/glb_io.py')
shutil.copy2(SRC/'reports/Stargazer_M04_REPORT.md',cand/'reports/Stargazer_M04_REPORT.md')
shutil.copy2(SRC/'reports/Stargazer_M04_VALIDATION.json',cand/'reports/Stargazer_M04_VALIDATION.json')
manifest={
 'M03_GLBSHA256':sha(base/'Stargazer_M03.glb'),'M03_HTMLSHA256':sha(base/'Stargazer_M03_PREVIEW.html'),
 'M04_GLBSHA256':sha(cand/'Stargazer_M04.glb'),'M04_HTMLSHA256':sha(cand/'Stargazer_M04_PREVIEW.html')}
(ROOT/'ASSET_HASHES.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(manifest,indent=2),flush=True)
