"""Test the delivered DEB in verified Linux Mint 22.3 userspace on disposable CI.
This is a chroot integration test, not a booted Cinnamon/GPU hardware test.
"""
import hashlib,json,os,shutil,subprocess,sys,urllib.request
from pathlib import Path
if os.environ.get('GITHUB_ACTIONS')!='true':raise SystemExit('Mint verification is restricted to disposable CI.')
ROOT=Path(__file__).resolve().parents[1];version=(ROOT/'VERSION').read_text().strip()
qa=ROOT/'build/mint';qa.mkdir(parents=True,exist_ok=True)
def run(*args):subprocess.run([str(a) for a in args],check=True)
def download(url,path):
    with urllib.request.urlopen(url,timeout=180) as response,path.open('xb') as output:shutil.copyfileobj(response,output,8*1024*1024)
iso=qa/'mint.iso'
download('https://pub.linuxmint.io/stable/22.3/linuxmint-22.3-cinnamon-64bit.iso',iso)
with iso.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()=='a081ab202cfda17f6924128dbd2de8b63518ac0531bcfe3f1a1b88097c459bd4'
# The pinned digest is from Mint's official linked SHA256 file, not an arbitrary container image.
run('sudo','apt-get','update');run('sudo','apt-get','install','-y','squashfs-tools','p7zip-full')
run('7z','e',iso,'casper/filesystem.squashfs','-o'+str(qa))
iso.unlink();root=qa/'root'
run('sudo','unsquashfs','-d',root,qa/'filesystem.squashfs');(qa/'filesystem.squashfs').unlink()
run('sudo','chroot',root,'cat','/etc/os-release')
manifest=json.loads((ROOT/'downloads'/f'Description-Shortener-V{version}-Linux-x64-release.json').read_text())
model=qa/'model.gguf'
download('https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-gguf/resolve/29d097773436b69ff9feafd636ab4cf873786537/gemma-4-12b-it-qat-q4_0.gguf',model)
with model.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()=='93567e57a8fe10b23569b9d9ec38cd005deedf71e29477c421a4b83f418a538b'
archive=qa/'package.deb';sha=hashlib.sha256()
with archive.open('xb') as output:
    for part in manifest['parts']:
        path=model if part.get('model') else ROOT/'downloads'/part['filename']
        assert path.stat().st_size==part['bytes']
        with path.open('rb') as source:
            while chunk:=source.read(8*1024*1024):output.write(chunk);sha.update(chunk)
assert sha.hexdigest()==manifest['sha256'] and archive.stat().st_size==manifest['bytes'];model.unlink()
run('sudo','mv',archive,root/'package.deb')
run('sudo','rm','-f',root/'etc/resolv.conf')
run('sudo','cp','-L','/etc/resolv.conf',root/'etc/resolv.conf')
mounted=[]
try:
    for source in ['/dev','/proc','/sys']:
        destination=str(root)+source;run('sudo','mount','--rbind',source,destination);run('sudo','mount','--make-rslave',destination);mounted.append(destination)
    run('sudo','chroot',root,'apt-get','update')
    run('sudo','chroot',root,'env','DEBIAN_FRONTEND=noninteractive','apt-get','install','-y','/package.deb','xvfb','python3-lxml','dbus-x11')
    run('sudo','rm',root/'package.deb')
    run('sudo','mkdir','-p',root/'qa')
    for directory in ['scripts','src','tests','benchmarks']:run('sudo','cp','-r',ROOT/directory,root/'qa'/directory)
    run('sudo','cp',ROOT/'VERSION',root/'qa/VERSION')
    run('sudo','chroot',root,'useradd','-m','-s','/bin/bash','appcheck')
    sandbox=root/'opt/description-shortener/chrome-sandbox'
    assert sandbox.stat().st_uid==0 and sandbox.stat().st_mode&0o7777==0o4755
    run('sudo','chroot',root,'runuser','-u','appcheck','--','dbus-run-session','--','xvfb-run','-a','/opt/description-shortener/DescriptionShortener','--ui-smoke-test','--disable-gpu','--enable-logging=stderr')
    run('sudo','chroot',root,'runuser','-u','appcheck','--','python3','/qa/scripts/desktop_smoke.py','/opt/description-shortener/resources/processor')
    print('Linux Mint 22.3 userspace: DEB installation, sandbox, UI, model and file processing passed.',flush=True)
finally:
    for destination in reversed(mounted):subprocess.run(['sudo','umount','-R',destination],check=False)
