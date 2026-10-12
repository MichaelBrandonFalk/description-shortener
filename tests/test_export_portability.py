import errno,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from engine import process_file
class Model:
    limit=110
    def shorten(self,text):return text
class PortableExportTests(unittest.TestCase):
    def test_unsupported_hard_link_uses_exclusive_copy(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'input.txt';target=Path(temp)/'output.txt';source.write_text('This bottle holds 500 ml.')
            with patch('engine.os.link',side_effect=OSError(errno.EOPNOTSUPP,'Not supported')):
                result=process_file(source,target,Model())
            self.assertTrue(result['ok']);self.assertEqual(source.read_bytes(),target.read_bytes())
    def test_fallback_does_not_replace_a_racing_file(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'input.txt';target=Path(temp)/'output.txt';source.write_text('This bottle holds 500 ml.')
            def racing(*args):target.write_text('Keep me.');raise OSError(errno.EOPNOTSUPP,'Not supported')
            with patch('engine.os.link',side_effect=racing):
                with self.assertRaises(FileExistsError):process_file(source,target,Model())
            self.assertEqual(target.read_text(),'Keep me.')
