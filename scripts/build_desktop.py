"""Native-platform Windows/Linux preview builds with the same pinned model."""
import hashlib,importlib.metadata,json,os,platform,shutil,subprocess,sys,tarfile,urllib.request,zipfile
from pathlib import Path
from split_archive import package
from split_deb import package_deb
ROOT=Path(__file__).resolve().parents[1];os.chdir(ROOT)
VERSION=(ROOT/'VERSION').read_text().strip();WINDOWS=os.name=='nt';TARGET='Windows-x64' if WINDOWS else 'Linux-x64'
if platform.machine().lower() not in ('x86_64','amd64'):raise SystemExit('Preview builds currently support x64 only.')
CPU=('llama-b11531-bin-win-cpu-x64.zip','a713d17e2bde26862e3c27bf2a226d35dffc80c3220a135b8cc278ad035ab170') if WINDOWS else ('llama-b11531-bin-ubuntu-x64.tar.gz','0ad476a96a05870977f8f1fed4a75f3598e33b566a41271a820f555ba3c700c5')
GPU=('llama-b11531-bin-win-vulkan-x64.zip','e6b751b1678cb2a2503a98d974e14f5a18ab534f56f16660882ab310efe75ff6') if WINDOWS else ('llama-b11531-bin-ubuntu-vulkan-x64.tar.gz','6dfdb394b086f164abeef95b4acd5495b08a54c7312f2d60a1aca541cd58f4d8')
def run(args,**kwargs):subprocess.run([str(x) for x in args],check=True,**kwargs)
def download(url,path,sha):
    if not path.exists():
        path.parent.mkdir(parents=True,exist_ok=True)
        with urllib.request.urlopen(url,timeout=120) as response,path.open('wb') as output:shutil.copyfileobj(response,output,8*1024*1024)
    if hashlib.file_digest(path.open('rb'),'sha256').hexdigest()!=sha:raise RuntimeError('Checksum mismatch: '+path.name)
processor=ROOT/'build/desktop-processor';processor.mkdir(parents=True,exist_ok=True)
model=ROOT/'vendor/model.gguf'
download('https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-gguf/resolve/29d097773436b69ff9feafd636ab4cf873786537/gemma-4-12b-it-qat-q4_0.gguf',model,'93567e57a8fe10b23569b9d9ec38cd005deedf71e29477c421a4b83f418a538b')
for kind,(name,sha) in [('cpu',CPU),('vulkan',GPU)]:
    artifact=ROOT/'vendor'/name;download('https://github.com/ggml-org/llama.cpp/releases/download/b11531/'+name,artifact,sha)
    extracted=ROOT/'build'/('runtime-'+kind);extracted.mkdir(exist_ok=True)
    if name.endswith('.zip'):
        with zipfile.ZipFile(artifact) as archive:archive.extractall(extracted)
    else:
        with tarfile.open(artifact) as archive:archive.extractall(extracted,filter='data')
    binary=next(extracted.rglob('llama-server.exe' if WINDOWS else 'llama-server'))
    destination=processor/'llama'/kind;destination.mkdir(parents=True,exist_ok=True)
    for path in binary.parent.iterdir():
        if path.is_file() and (path.name.startswith('llama-server') or '.so' in path.name or path.suffix.lower() in ('.dll','.metallib')):shutil.copy2(path,destination/path.name)
run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--name','shortener-helper','--distpath','build/desktop-helper','--workpath','build/desktop-helper-work','--specpath','build','src/engine.py'])
shutil.copytree(ROOT/'build/desktop-helper/shortener-helper',processor/'helper',dirs_exist_ok=True)
shutil.copytree(ROOT/'licenses',processor/'licenses',dirs_exist_ok=True)
shutil.copy2(ROOT/'THIRD_PARTY_NOTICES.md',processor/'licenses/THIRD_PARTY_NOTICES.md')
shutil.copy2(ROOT/'LICENSE',processor/'licenses/Description-Shortener-LICENSE')
for name in ['lxml','pyinstaller','altgraph','macholib','packaging','setuptools','pyinstaller-hooks-contrib']:
    try: distribution=importlib.metadata.distribution(name)
    except importlib.metadata.PackageNotFoundError: continue
    target=processor/'licenses'/name;target.mkdir(exist_ok=True)
    for entry in distribution.files or []:
        if any(word in entry.name.lower() for word in ['license','copying','notice']) and distribution.locate_file(entry).is_file():shutil.copy2(distribution.locate_file(entry),target/entry.name)
for kind in ['cpu','vulkan']:
    for path in (ROOT/'build'/('runtime-'+kind)).rglob('*'):
        if path.is_file() and any(word in path.name.upper() for word in ['LICENSE','LICENCE','NOTICE']):shutil.copy2(path,processor/'licenses'/(kind+'-'+path.name))
if WINDOWS:
    from windows_support import bundle
    bundle(processor)
# Hard links avoid duplicating the pinned 7 GB weights on CI disks.
linked=processor/'model.gguf'
if not linked.exists():os.link(model,linked)
linked.unlink() # Model is represented by the immutable download segment below.
run(['node','desktop/node_modules/@electron/packager/bin/electron-packager.mjs','desktop','DescriptionShortener','--platform='+('win32' if WINDOWS else 'linux'),'--arch=x64','--out=build/electron','--overwrite','--asar','--icon='+str(ROOT/'assets'/('app-icon.ico' if WINDOWS else 'app-icon.png')),'--extra-resource='+str(processor),'--app-version='+(VERSION+'.0' if VERSION.count('.')==1 else VERSION)])
folder=ROOT/'build/electron'/('DescriptionShortener-'+('win32' if WINDOWS else 'linux')+'-x64')
# Electron resources use the stable name expected by the launcher.
(folder/'resources/desktop-processor').rename(folder/'resources/processor')
os.link(model,folder/'resources/processor/model.gguf')
run([sys.executable,'scripts/desktop_smoke.py',str(folder/'resources/processor')],env={**os.environ,'DESCRIPTION_SHORTENER_BACKEND':'cpu','PYTHONUTF8':'1'})
(folder/'resources/processor/model.gguf').unlink()
command=[str(folder/('DescriptionShortener.exe' if WINDOWS else 'DescriptionShortener')),'--ui-smoke-test']
run(command if WINDOWS else ['xvfb-run','-a',*command])
result=package(folder,model,ROOT/'downloads',TARGET,VERSION) if WINDOWS else package_deb(folder,model,ROOT/'downloads',VERSION)
print(json.dumps(result),flush=True)
