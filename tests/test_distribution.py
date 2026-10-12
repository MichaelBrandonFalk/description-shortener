import importlib.util,sys,tempfile,unittest,zipfile,io,hashlib,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from split_archive import package
from split_deb import package_deb
class DistributionTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.folder=self.root/'app';(self.folder/'resources/processor').mkdir(parents=True);(self.folder/'launcher').write_bytes(b'launcher');self.model=self.root/'model.gguf';self.model.write_bytes(b'GGUF'+b'weights'*71)
    def tearDown(self):self.temp.cleanup()
    def reassemble(self,result):
        parts=[]
        for part in result['parts']:parts.append(self.model.read_bytes() if part.get('model') else (self.root/'downloads'/part['filename']).read_bytes())
        data=b''.join(parts);self.assertEqual(hashlib.sha256(data).hexdigest(),result['sha256']);self.assertEqual(len(data),result['bytes']);return data
    def test_split_zip_is_valid_with_exact_model_and_checksum(self):
        result=package(self.folder,self.model,self.root/'downloads','Windows-x64','1.3');data=self.reassemble(result)
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            self.assertIsNone(archive.testzip());self.assertEqual(archive.read('app/resources/processor/model.gguf'),self.model.read_bytes());self.assertEqual(archive.read('app/launcher'),b'launcher')
    def test_linux_deb_members_and_model_padding(self):
        result=package_deb(self.folder,self.model,self.root/'downloads','1.3');data=self.reassemble(result);self.assertTrue(data.startswith(b'!<arch>\n'));offset=8;members={}
        while offset<len(data):
            h=data[offset:offset+60];size=int(h[48:58]);name=h[:16].decode().strip().rstrip('/');members[name]=data[offset+60:offset+60+size];offset+=60+size+(size%2)
        self.assertEqual(members['debian-binary'],b'2.0\n')
        with tarfile.open(fileobj=io.BytesIO(members['data.tar'])) as archive:
            self.assertTrue(all(not entry.pax_headers for entry in archive.getmembers()))
            directories={'.'}
            for entry in archive.getmembers():
                self.assertIn(str(Path(entry.name).parent),directories,entry.name)
                if entry.isdir():directories.add(entry.name)
            self.assertEqual(archive.extractfile('opt/description-shortener/resources/processor/model.gguf').read(),self.model.read_bytes())
            self.assertEqual(archive.getmember('opt/description-shortener/launcher').uid,0)
    def test_linux_rewrap_includes_the_model_only_once(self):
        inside=self.folder/'resources/processor/model.gguf';inside.write_bytes(self.model.read_bytes())
        result=package_deb(self.folder,inside,self.root/'downloads','1.3');data=self.reassemble(result)
        offset=8
        while offset<len(data):
            header=data[offset:offset+60];size=int(header[48:58]);name=header[:16].decode().strip().rstrip('/')
            if name=='data.tar':
                with tarfile.open(fileobj=io.BytesIO(data[offset+60:offset+60+size])) as archive:
                    self.assertEqual([p.name for p in archive.getmembers()].count('opt/description-shortener/resources/processor/model.gguf'),1)
                return
            offset+=60+size+(size%2)
        self.fail('Missing data.tar')
    def test_immutable_parts_cannot_be_overwritten(self):
        package(self.folder,self.model,self.root/'downloads','Windows-x64','1.3')
        with self.assertRaises(RuntimeError):package(self.folder,self.model,self.root/'downloads','Windows-x64','1.3')
