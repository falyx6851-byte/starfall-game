from pathlib import Path
import subprocess,time,sys
from playwright.sync_api import sync_playwright
ROOT=Path.cwd(); evidence=ROOT/'evidence'; evidence.mkdir(exist_ok=True)
server=subprocess.Popen([sys.executable,'-m','http.server','8765','--bind','127.0.0.1'],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
time.sleep(1)
shots=[
 ('baselines/M03/Stargazer_M03_PREVIEW.html','M03','reference-gray',dict(view='reference',clip='DesignPose',time=0,gray=True,manual=True,clean=True,playing=False)),
 ('baselines/M03/Stargazer_M03_PREVIEW.html','M03','combat-gray',dict(view='combat',clip='Idle',time=.45,gray=True,manual=True,clean=True,playing=False)),
 ('candidates/M04/Stargazer_M04_PREVIEW.html','M04','reference-material',dict(view='reference',clip='DesignPose',time=0,gray=False,manual=True,clean=True,playing=False)),
 ('candidates/M04/Stargazer_M04_PREVIEW.html','M04','combat-material',dict(view='combat',clip='Idle',time=.45,gray=False,manual=True,clean=True,playing=False)),
 ('candidates/M04/Stargazer_M04_PREVIEW.html','M04','attack1-013',dict(view='reference',clip='Attack1',time=.13,gray=False,manual=True,clean=True,playing=False)),
 ('candidates/M04/Stargazer_M04_PREVIEW.html','M04','attack1-016',dict(view='reference',clip='Attack1',time=.16,gray=False,manual=True,clean=True,playing=False)),
 ('candidates/M04/Stargazer_M04_PREVIEW.html','M04','attack1-032',dict(view='reference',clip='Attack1',time=.32,gray=False,manual=True,clean=True,playing=False)),
]
with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    page=browser.new_page(viewport={'width':1500,'height':1120},device_scale_factor=1)
    current=None
    for rel,ver,name,cfg in shots:
        if current!=rel:
            page.goto('http://127.0.0.1:8765/'+rel,wait_until='load',timeout=60000)
            page.wait_for_function('window.__HERO_SAMPLE__?.ready',timeout=60000); current=rel
        page.evaluate('o=>__HERO_SAMPLE__.set(o)',cfg)
        page.locator('#show-ui').evaluate('e=>e.style.display="none"')
        out=evidence/ver; out.mkdir(parents=True,exist_ok=True)
        page.screenshot(path=str(out/(name+'.png')))
    browser.close()
server.terminate(); server.wait(timeout=10)
