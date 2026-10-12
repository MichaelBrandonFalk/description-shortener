"""Verify the delivered archive, then run the extracted/installed native app in CI."""
import hashlib,json,os,shutil,subprocess,sys,tarfile,urllib.request,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if os.environ.get('GITHUB_ACTIONS')!='true':raise SystemExit('Installer verification runs only on disposable CI hosts.')
windows=os.name=='nt';target='Windows-x64' if windows else 'Linux-x64'
version=(ROOT/'VERSION').read_text().strip()
manifest=json.loads((ROOT/'downloads'/f'Description-Shortener-V{version}-{target}-release.json').read_text())
model=ROOT/'vendor/model.gguf';model.parent.mkdir(exist_ok=True)
if not model.exists():
    url='https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-gguf/resolve/29d097773436b69ff9feafd636ab4cf873786537/gemma-4-12b-it-qat-q4_0.gguf'
    with urllib.request.urlopen(url,timeout=120) as source,model.open('xb') as output:shutil.copyfileobj(source,output,8*1024*1024)
with model.open('rb') as source:assert hashlib.file_digest(source,'sha256').hexdigest()=='93567e57a8fe10b23569b9d9ec38cd005deedf71e29477c421a4b83f418a538b'
qa=ROOT/'build/archive-verification';qa.mkdir(parents=True,exist_ok=True)
archive=qa/manifest['archive'];sha=hashlib.sha256()
with archive.open('xb') as output:
    for part in manifest['parts']:
        path=model if part.get('model') else ROOT/'downloads'/part['filename']
        assert path.stat().st_size==part['bytes']
        with path.open('rb') as source:
            while chunk:=source.read(8*1024*1024):output.write(chunk);sha.update(chunk)
assert archive.stat().st_size==manifest['bytes'] and sha.hexdigest()==manifest['sha256']
print('Complete delivered archive SHA-256 and size verified.',flush=True)
if windows:
    model.unlink() # Keep at most two complete copies of the 7 GB weights during extraction.
    with zipfile.ZipFile(archive) as packaged:
        assert packaged.testzip() is None
        packaged.extractall(qa/'extracted')
    folder=next((qa/'extracted').glob('DescriptionShortener-*'))
    # Finalize the unpublished Windows candidate with app-local CRT dependencies.
    from windows_support import bundle
    from split_archive import package
    processor=folder/'resources/processor';bundle(processor)
    shutil.copy2(ROOT/'licenses/llama.cpp-LICENSE',processor/'licenses/llama.cpp-LICENSE')
    shutil.copy2(ROOT/'THIRD_PARTY_NOTICES.md',processor/'licenses/THIRD_PARTY_NOTICES.md')
    archive.unlink()
    model=processor/'model.gguf'
    final=ROOT/'build/final-downloads'
    manifest=package(folder,model,final,target,version)
    archive=qa/manifest['archive'];sha=hashlib.sha256()
    with archive.open('xb') as output:
        for part in manifest['parts']:
            path=model if part.get('model') else final/part['filename']
            with path.open('rb') as source:
                while chunk:=source.read(8*1024*1024):output.write(chunk);sha.update(chunk)
    assert sha.hexdigest()==manifest['sha256'] and archive.stat().st_size==manifest['bytes']
    with zipfile.ZipFile(archive) as packaged:
        assert packaged.testzip() is None
        for entry in packaged.infolist():
            if not entry.filename.endswith('/model.gguf'):packaged.extract(entry,qa/'extracted')
    print('Final Windows ZIP, app-local CRT files and complete notices verified.',flush=True)
else:
    # Preserve the unpublished native binaries, and rebuild only the installer wrapper.
    from split_deb import package_deb
    with archive.open('rb') as source:
        assert source.read(8)==b'!<arch>\n'
        while header:=source.read(60):
            size=int(header[48:58]);name=header[:16].decode().strip().rstrip('/')
            if name=='data.tar':
                with tarfile.open(fileobj=source,mode='r|') as data:data.extractall(qa/'deb-extracted',filter='data')
                break
            source.seek(size+(size%2),1)
        else:raise RuntimeError('The candidate installer has no data archive.')
    folder=qa/'deb-extracted/opt/description-shortener';processor=folder/'resources/processor'
    shutil.copy2(ROOT/'licenses/llama.cpp-LICENSE',processor/'licenses/llama.cpp-LICENSE')
    shutil.copy2(ROOT/'THIRD_PARTY_NOTICES.md',processor/'licenses/THIRD_PARTY_NOTICES.md')
    archive.unlink();model.unlink();model=processor/'model.gguf'
    final=ROOT/'build/final-downloads';manifest=package_deb(folder,model,final,version)
    sha=hashlib.sha256()
    with archive.open('xb') as output:
        for part in manifest['parts']:
            path=model if part.get('model') else final/part['filename']
            with path.open('rb') as source:
                while chunk:=source.read(8*1024*1024):output.write(chunk);sha.update(chunk)
    assert sha.hexdigest()==manifest['sha256'] and archive.stat().st_size==manifest['bytes']
    subprocess.run(['dpkg-deb','--info',str(archive)],check=True)
    subprocess.run(['sudo','dpkg','-i',str(archive)],check=True)
    folder=Path('/opt/description-shortener')
    sandbox=folder/'chrome-sandbox'
    assert sandbox.stat().st_uid==0 and sandbox.stat().st_mode&0o7777==0o4755
with (folder/'resources/processor/model.gguf').open('rb') as source:assert hashlib.file_digest(source,'sha256').hexdigest()=='93567e57a8fe10b23569b9d9ec38cd005deedf71e29477c421a4b83f418a538b'
command=[str(folder/('DescriptionShortener.exe' if windows else 'DescriptionShortener')),'--ui-smoke-test']
subprocess.run(command if windows else ['xvfb-run','-a',*command],check=True)
subprocess.run([sys.executable,str(ROOT/'scripts/desktop_smoke.py'),str(folder/'resources/processor')],check=True)
print('Delivered archive extraction/installation, sandbox, UI and actual-model checks passed.',flush=True)
