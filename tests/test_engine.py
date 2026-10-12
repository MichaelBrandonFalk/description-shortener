import csv
import io
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from engine import *

ORIGINAL = 'This durable stainless steel bottle is designed to hold 500 ml of water and is safe to clean in the dishwasher.'
SHORT = 'This durable stainless steel bottle holds 500 ml of water and is safe to clean in the dishwasher.'

class Stub:
    def shorten(self, text):
        if text == ORIGINAL: return SHORT
        if text == 'The bottle holds 500 ml.': return text
        raise ReviewNeeded('Cannot retain all facts.')

class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.dir = Path(self.temp.name)
    def tearDown(self): self.temp.cleanup()
    def test_hard_rules(self):
        self.assertFalse(hard_errors(ORIGINAL, SHORT))
        for text in ['a' * 110 + '.', 'It works\u2014well.', 'It works,', 'It works;', 'It works...', 'It works\u2026', 'It holds 600 ml.']:
            self.assertTrue(hard_errors(ORIGINAL, text))
        self.assertFalse(hard_errors('x' * 109 + '.', 'x' * 109 + '.'))
        self.assertTrue(hard_errors('There are 2 red and 2 blue parts.', 'There are 2 parts.'))
    def test_csv_structure(self):
        path = self.dir/'in.csv'; out = self.dir/'out.csv'
        path.write_bytes(('SKU;Description;Overview;Price\r\n001;"'+ORIGINAL+'";"'+ORIGINAL+'";12.90\r\n').encode('utf-8-sig'))
        result = process_file(path, out, Stub())
        self.assertTrue(result['ok']); self.assertEqual(result['changed'], 2)
        raw = out.read_bytes(); self.assertTrue(raw.startswith(b'\xef\xbb\xbf')); self.assertIn(b'\r\n', raw)
        rows = list(csv.reader(io.StringIO(raw.decode('utf-8-sig')), delimiter=';'))
        self.assertEqual(rows[1], ['001', SHORT, SHORT, '12.90'])
    def test_block_all_export(self):
        path = self.dir/'in.txt'; out = self.dir/'out.txt'
        path.write_text(ORIGINAL+'\nA different description.\n')
        result = process_file(path, out, Stub())
        self.assertFalse(result['ok']); self.assertFalse(out.exists()); self.assertIn(ORIGINAL, path.read_text())
    def test_original_and_existing_protected(self):
        path = self.dir/'in.txt'; path.write_text(ORIGINAL)
        with self.assertRaises(ValueError): process_file(path, path, Stub())
        other = self.dir/'existing.txt'; other.write_text('keep')
        with self.assertRaises(ValueError): process_file(path, other, Stub())
        self.assertEqual(other.read_text(), 'keep')
    def test_headerless_csv(self):
        path = self.dir/'in.csv'; out = self.dir/'out.csv'
        with path.open('w') as f: csv.writer(f).writerow([ORIGINAL])
        self.assertTrue(process_file(path, out, Stub())['ok'])
        with out.open() as f: self.assertEqual(list(csv.reader(f))[0][0], SHORT)
    def test_workbook_preserves_untouched_parts(self):
        path = self.dir/'in.xlsx'; out = self.dir/'out.xlsx'
        shared = f'<sst xmlns="{S}"><si><t>Description</t></si><si><t>{ORIGINAL}</t></si><si><t>Name</t></si></sst>'
        sheet = f'<worksheet xmlns="{S}"><sheetData><row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>2</v></c></row><row r="2"><c r="A2" t="s" s="4"><v>1</v></c><c r="B2" t="s"><v>1</v></c><c r="C2"><f>1+1</f><v>2</v></c><c r="D2"><v>500</v></c></row></sheetData></worksheet>'
        with ZipFile(path, 'w') as z:
            z.writestr('xl/sharedStrings.xml', shared)
            z.writestr('xl/worksheets/sheet1.xml', sheet)
            z.writestr('xl/styles.xml', '<styles>unchanged</styles>')
            z.writestr('customXml/item1.xml', '<custom>unchanged</custom>')
        result = process_file(path, out, Stub()); self.assertTrue(result['ok']); self.assertEqual(result['changed'], 1)
        with ZipFile(path) as src, ZipFile(out) as dst:
            for name in ['xl/sharedStrings.xml', 'xl/styles.xml', 'customXml/item1.xml']:
                self.assertEqual(src.read(name), dst.read(name))
            root = xml(dst.read('xl/worksheets/sheet1.xml'))
            self.assertEqual(root.xpath('//s:c[@r="A2"]/@s', namespaces=NS), ['4'])
            self.assertEqual(root.xpath('//s:c[@r="A2"]//s:t/text()', namespaces=NS), [SHORT])
            self.assertEqual(root.xpath('//s:c[@r="B2"]/s:v/text()', namespaces=NS), ['1'])
            self.assertEqual(root.xpath('//s:f/text()', namespaces=NS), ['1+1'])
    def test_docx_table_and_style(self):
        path = self.dir/'in.docx'; out = self.dir/'out.docx'
        with ZipFile(path,'w') as z:
            z.writestr('word/document.xml', f'<w:document xmlns:w="{W}"><w:body><w:tbl><w:tr><w:tc><w:p><w:pPr><w:pStyle w:val="Normal"/></w:pPr><w:r><w:rPr><w:b/></w:rPr><w:t>{ORIGINAL}</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>')
            z.writestr('word/header1.xml', '<header>keep me</header>')
        result = process_file(path,out,Stub()); self.assertTrue(result['ok'])
        with ZipFile(out) as z:
            root = xml(z.read('word/document.xml'))
            self.assertEqual(root.xpath('//w:t/text()',namespaces=NS),[SHORT])
            self.assertTrue(root.xpath('//w:b',namespaces=NS))
            self.assertEqual(z.read('word/header1.xml'),b'<header>keep me</header>')
    def test_edited_cells_rechecked(self):
        class Bad:
            def shorten(self, text): return 'It holds 600 ml.'
        path=self.dir/'in.txt'; path.write_text(ORIGINAL); out=self.dir/'out.txt'
        self.assertFalse(process_file(path,out,Bad())['ok']); self.assertFalse(out.exists())
    def test_formula_and_name_selection(self):
        self.assertFalse(relevant(ORIGINAL,'Product Name'))
        self.assertFalse(relevant('https://example.com/'+'a'*120,'Description'))
        self.assertFalse(relevant('=SUM(A1:A100)','Description'))
        self.assertTrue(relevant(ORIGINAL,'Overview'))
    def test_empty_and_unicode(self):
        path=self.dir/'in.txt'; path.write_text('\n'+ORIGINAL+'\n\n',encoding='utf-8'); out=self.dir/'out.txt'
        process_file(path,out,Stub())
        self.assertEqual(out.read_text(),'\n'+SHORT+'\n\n')
        self.assertFalse(hard_errors('Café opens at 9.', 'Café opens at 9.'))

class GenerationTests(unittest.TestCase):
    def fake(self, drafts, verdicts):
        model = LocalModel(Path('/unused'))
        model.responses = iter(drafts)
        model.verdicts = iter(verdicts)
        model.calls = []
        def ask(system, payload, schema=None):
            model.calls.append((system, payload, schema))
            return next(model.verdicts) if system == REVIEW else {'text': next(model.responses)}
        model.ask = ask
        return model
    def test_invalid_draft_rewritten_internally(self):
        good = {'equivalent': True, 'complete_sentences': True, 'close_wording': True, 'issue': ''}
        model = self.fake([SHORT[:-1], SHORT], [good])
        self.assertEqual(model.shorten(ORIGINAL), SHORT)
        self.assertIn('complete sentence', model.calls[1][1]['previous_issue'])
        self.assertNotIn('maxLength', str(model.calls[0][2]))
        self.assertIn('word_budget_guidance', model.calls[0][1])
    def test_unresolved_draft_has_explanatory_message(self):
        model = self.fake([SHORT[:-1]] * 3, [])
        with self.assertRaises(ReviewNeeded) as error: model.shorten(ORIGINAL)
        self.assertIn('local model', str(error.exception))
        self.assertIn('material facts', str(error.exception))
        self.assertNotIn('Must end', str(error.exception))
    def test_semantic_feedback_is_sent_to_generator(self):
        bad = {'equivalent': False, 'complete_sentences': True, 'close_wording': True, 'issue': 'The draft turns a planned action into a completed action.'}
        good = {'equivalent': True, 'complete_sentences': True, 'close_wording': True, 'issue': ''}
        model = self.fake([SHORT, SHORT], [bad, good])
        self.assertEqual(model.shorten(ORIGINAL), SHORT)
        self.assertIn('planned action', model.calls[2][1]['previous_issue'])
    def test_compaction_preserves_units_and_quoted_names(self):
        raw = 'They bought a holiday home ~2 yrs ago and wanted an outdoor living space.'
        compact = compact_draft(raw)
        self.assertIn('~2yr ago', compact)
        self.assertIn('wanted outdoor living space.', compact)
        self.assertEqual(numeric_tokens(raw), numeric_tokens(compact))
        self.assertEqual(compact_draft('The name is "an outdoor living space".'), 'The name is "an outdoor living space".')
        self.assertEqual(compact_draft('A' * 120 + '.'), 'A' * 120 + '.')

    def test_same_description_uses_session_cache(self):
        good = {'equivalent': True, 'complete_sentences': True, 'close_wording': True, 'issue': ''}
        model = self.fake([SHORT], [good])
        model.shorten(ORIGINAL)
        before=len(model.calls)
        self.assertEqual(model.shorten(ORIGINAL), SHORT)
        self.assertEqual(len(model.calls),before)
    def test_overlength_result_is_never_returned(self):
        long = 'This durable stainless steel bottle is designed to hold 500 ml of water and is safe to clean in the dishwasher today.'
        model = self.fake([long] * 3, [])
        with self.assertRaises(ReviewNeeded): model.shorten(ORIGINAL)
        self.assertLess(model.calls[1][1]['word_budget_guidance'], model.calls[0][1]['word_budget_guidance'])
        self.assertIn('exceeds 110', model.calls[1][1]['previous_issue'])

    def test_equivalent_quantities(self):
        self.assertEqual(numeric_tokens('About two years ago.'),numeric_tokens('~2 yrs ago.'))
        self.assertNotEqual(numeric_tokens('two years'),numeric_tokens('3 years'))
        self.assertNotEqual(numeric_tokens('twenty-five parts'),numeric_tokens('twenty parts'))

if __name__ == '__main__': unittest.main()
