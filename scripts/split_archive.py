"""Write an exact ZIP as header + pinned model + footer without duplicating 7 GB."""
import hashlib, json, os, shutil, zipfile
from pathlib import Path
class SplitSink:
    def __init__(self,head,tail):
        self.head=head.open('wb');self.tail=tail.open('wb');self.phase='head';self.position=0;self.sha=hashlib.sha256();self.sizes={'head':0,'model':0,'tail':0}
    def tell(self):return self.position
    def write(self,data):
        self.sha.update(data);self.position+=len(data);self.sizes[self.phase]+=len(data)
        if self.phase!='model':getattr(self,self.phase).write(data)
        return len(data)
    def flush(self):self.head.flush();self.tail.flush()
    def seek(self,*_):raise OSError('Non-seekable split ZIP')
    def close(self):self.head.close();self.tail.close()

def package(folder,model,output,platform,version):
    stem=f'Description-Shortener-V{version}-{platform}'
    head=output/(stem+'-zip-head.bin');tail=output/(stem+'-zip-tail.bin')
    if head.exists() or tail.exists():raise RuntimeError('This version is already packaged. Do not overwrite it.')
    output.mkdir(parents=True,exist_ok=True);sink=SplitSink(head,tail)
    try:
        with zipfile.ZipFile(sink,'w',compression=zipfile.ZIP_DEFLATED,allowZip64=True) as archive:
            for path in sorted(folder.rglob('*')):
                if path.is_file() and path.name!='model.gguf':archive.write(path,str(Path(folder.name)/path.relative_to(folder)))
            info=zipfile.ZipInfo(str(Path(folder.name)/'resources/processor/model.gguf'))
            info.compress_type=zipfile.ZIP_STORED;info.file_size=model.stat().st_size;info.external_attr=0o100644<<16
            with archive.open(info,'w',force_zip64=True) as target:
                sink.phase='model'
                with model.open('rb') as source:shutil.copyfileobj(source,target,8*1024*1024)
                sink.phase='tail'
        result={'version':version,'platform':platform,'archive':stem+'.zip','sha256':sink.sha.hexdigest(),'bytes':sink.position,
          'parts':[{'filename':head.name,'bytes':sink.sizes['head']},{'model':True,'bytes':sink.sizes['model']},{'filename':tail.name,'bytes':sink.sizes['tail']}]}
        (output/(stem+'-release.json')).write_text(json.dumps(result,indent=2)+'\n')
        (output/(stem+'-SHA256.txt')).write_text(result['sha256']+'  '+result['archive']+'\n')
        return result
    finally:sink.close()
