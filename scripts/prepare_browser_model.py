"""Map llama-gguf-split shards onto byte slices of the immutable upstream GGUF.

Publish only shard metadata. Weights stay at the pinned official Google URL.
"""
import hashlib, json, struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def read_gguf(path):
    with path.open('rb') as f:
        def u(fmt): return struct.unpack('<'+fmt, f.read(struct.calcsize('<'+fmt)))[0]
        def string(): return f.read(u('Q')).decode('utf-8')
        def value(t):
            if t==8: return string()
            if t==9:
                subtype=u('I'); return [value(subtype) for _ in range(u('Q'))]
            return u({0:'B',1:'b',2:'H',3:'h',4:'I',5:'i',6:'f',7:'?',10:'Q',11:'q',12:'d'}[t])
        assert f.read(4)==b'GGUF'
        assert u('I')==3
        tensors=u('Q'); metadata=u('Q'); alignment=32
        for _ in range(metadata):
            key=string(); item=value(u('I'))
            if key=='general.alignment': alignment=item
        offsets={}
        for _ in range(tensors):
            name=string(); dims=u('I')
            for _ in range(dims): u('Q')
            u('I'); offsets[name]=u('Q')
        start=(f.tell()+alignment-1)//alignment*alignment
        f.seek(0); prefix=f.read(start)
        return start,offsets,prefix

def main():
    model=ROOT/'vendor/model.gguf'; start,offsets,_=read_gguf(model)
    output=ROOT/'docs/browser/model'; output.mkdir(parents=True,exist_ok=True)
    shards=[]
    for path in sorted((ROOT/'build/browser-model').glob('*.gguf')):
        shard_start,shard_offsets,prefix=read_gguf(path)
        first=min(shard_offsets,key=shard_offsets.get)
        source_offset=start+offsets[first]
        assert all(offsets[name]-offsets[first]==offset for name,offset in shard_offsets.items())
        length=path.stat().st_size-shard_start
        with model.open('rb') as a,path.open('rb') as b:
            a.seek(source_offset); b.seek(shard_start)
            remaining=length
            while remaining:
                n=min(8*1024*1024,remaining)
                assert a.read(n)==b.read(n), path.name
                remaining-=n
        header=path.name+'.header'; (output/header).write_bytes(prefix)
        shards.append({'name':path.name,'header':header,'offset':source_offset,'bytes':length,'sha256':hashlib.file_digest(path.open('rb'),'sha256').hexdigest()})
    manifest={'url':'https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-gguf/resolve/29d097773436b69ff9feafd636ab4cf873786537/gemma-4-12b-it-qat-q4_0.gguf','bytes':6975879296,'sha256':'93567e57a8fe10b23569b9d9ec38cd005deedf71e29477c421a4b83f418a538b','shards':shards}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Verified {len(shards)} shards byte-for-byte; only {sum((output/s["header"]).stat().st_size for s in shards):,} metadata bytes published.')
if __name__=='__main__': main()
