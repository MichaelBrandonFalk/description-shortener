"""Debian package with root-owned Chromium sandbox and a raw, reusable model segment."""
import hashlib,io,json,tarfile,time
from pathlib import Path
from split_archive import SplitSink

def header(name,size):
    return (f'{name}/'.ljust(16)+'0'.ljust(12)+'0'.ljust(6)+'0'.ljust(6)+'100644'.ljust(8)+str(size).ljust(10)+'`\n').encode()
def member(name,data):return header(name,len(data))+data+(b'\n' if len(data)%2 else b'')
def package_deb(folder,model,output,version):
    stem=f'Description-Shortener-V{version}-Linux-x64';output.mkdir(parents=True,exist_ok=True)
    inner_head=output/(stem+'-data-head.tmp');inner_tail=output/(stem+'-data-tail.tmp');sink=SplitSink(inner_head,inner_tail)
    class Reader:
        def __init__(self):self.file=model.open('rb')
        def read(self,n):sink.phase='model';return self.file.read(n)
    try:
        with tarfile.open(fileobj=sink,mode='w',format=tarfile.PAX_FORMAT) as archive:
            def add(path,name):
                info=archive.gettarinfo(str(path),name);info.uid=info.gid=0;info.uname=info.gname='root'
                if path.name=='chrome-sandbox':info.mode=0o4755
                if info.isfile():
                    with path.open('rb') as source:archive.addfile(info,source)
                else:archive.addfile(info)
            for path in sorted(folder.rglob('*')):add(path,'opt/description-shortener/'+str(path.relative_to(folder)))
            launcher=b'[Desktop Entry]\nType=Application\nName=Description Shortener\nExec=/opt/description-shortener/DescriptionShortener\nTerminal=false\nCategories=Utility;\n'
            info=tarfile.TarInfo('usr/share/applications/description-shortener.desktop');info.size=len(launcher);info.mode=0o644;archive.addfile(info,io.BytesIO(launcher))
            info=tarfile.TarInfo('opt/description-shortener/resources/processor/model.gguf');info.size=model.stat().st_size;info.mode=0o644
            reader=Reader();archive.addfile(info,reader);reader.file.close();sink.phase='tail'
    finally:sink.close()
    # tar padding after the model must be part of the footer, not its source segment.
    padding=sink.sizes['model']-model.stat().st_size
    if padding:
        old=inner_tail.read_bytes();inner_tail.write_bytes(b'\0'*padding+old);sink.sizes['model']-=padding;sink.sizes['tail']+=padding
    control=f'Package: description-shortener\nVersion: {version}\nArchitecture: amd64\nMaintainer: Michael Brandon Falk\nDescription: Fully local description shortening desktop preview\nDepends: libc6 (>= 2.35), libgtk-3-0, libnss3, libasound2 | libasound2t64, libgbm1, libxss1, libatk-bridge2.0-0, libdrm2, libxkbcommon0\n'.encode()
    bio=io.BytesIO()
    with tarfile.open(fileobj=bio,mode='w:gz') as archive:
        info=tarfile.TarInfo('./control');info.size=len(control);info.mode=0o644;archive.addfile(info,io.BytesIO(control))
    head=output/(stem+'-deb-head.bin');tail=output/(stem+'-deb-tail.bin')
    if head.exists() or tail.exists():raise RuntimeError('This immutable version is already packaged.')
    head.write_bytes(b'!<arch>\n'+member('debian-binary',b'2.0\n')+member('control.tar.gz',bio.getvalue())+header('data.tar',sink.position)+inner_head.read_bytes())
    tail.write_bytes(inner_tail.read_bytes()+(b'\n' if sink.position%2 else b''))
    sha=hashlib.sha256();sha.update(head.read_bytes())
    with model.open('rb') as source:
        while chunk:=source.read(8*1024*1024):sha.update(chunk)
    sha.update(tail.read_bytes());inner_head.unlink();inner_tail.unlink()
    result={'version':version,'platform':'Linux-x64','archive':stem+'.deb','sha256':sha.hexdigest(),'bytes':head.stat().st_size+model.stat().st_size+tail.stat().st_size,
      'parts':[{'filename':head.name,'bytes':head.stat().st_size},{'model':True,'bytes':model.stat().st_size},{'filename':tail.name,'bytes':tail.stat().st_size}]}
    (output/(stem+'-release.json')).write_text(json.dumps(result,indent=2)+'\n');(output/(stem+'-SHA256.txt')).write_text(result['sha256']+'  '+result['archive']+'\n')
    return result
