"""Offline shortening and loss-minimizing Office/CSV file editing."""
from __future__ import annotations
import atexit
import errno
import shutil
import csv
import io
import json
import os
from pathlib import Path
import re
import secrets
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from dataclasses import dataclass
from collections import Counter
from lxml import etree as ET

LIMIT = 110
S = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS = {'s': S, 'w': W}
DESCRIPTION = re.compile(r'description|synopsis|overview|summary|blurb|long.?text|short.?text|plot|^details$|^copy$', re.I)
IDENTIFIER = re.compile(r'(^|[ _-])(id|sku|url|uri|code|name|title|isbn|upc|ean|email|link|path)([ _-]|$)', re.I)
SYSTEM = '''Shorten the description DATA to a complete sentence of at most 110 characters INCLUDING spaces and punctuation.
Capture the main gist. Some supporting details may be dropped to fit. Prefer the central action and outcome.
Stay close to the original wording. Keep retained names, numbers, facts, negations and tense accurate.
Do not invent facts, reinterpret, add marketing language, use em dashes, or end with a comma, semicolon or ellipsis.
Use the word budget as guidance. A revision must resolve the reported length or punctuation problem.
Always return your best useful sentence in JSON {"text":"shortened description"}. Never return an empty result merely because all details cannot fit.'''
REVIEW = '''You are a strict copy editor reviewing JSON DATA. Compare original and candidate.
Check the main meaning and every material fact: names, quantities, specifications, claims, locations, negations, chronology, and actions or intentions.
Incidental narrative enjoyment and similar sentiment, including its background causal explanation, may be omitted. Redundant idioms may be removed.
Product attributes and factual claims are material, not optional sentiment. Do not permit invented features or changed facts.
Preserve source tense and whether an action occurred: wanted to add is a past intention, not added or intends now.
Equivalent numeric notation, familiar unit abbreviations and ~ for about are allowed. Purchased/bought and vacation home/holiday home are equivalent.
Reordered clauses and compact grammar count as close wording; reject creative or unnecessary rewrites.
Check required articles as well as finite predicates; bare count nouns in headline style are not ordinary complete prose. Check complete_sentences by grammar only: a subject plus a finite predicate, with attached participial clauses or compound predicates allowed.
Do not reject grammatical compression merely because optional sentiment is absent.
Return JSON {"equivalent":true or false,"complete_sentences":true or false,"close_wording":true or false,
"issue":"one short actionable explanation for any failed check, otherwise empty"}.'''
TEXT_SCHEMA = {'type': 'object', 'properties': {'text': {'type': 'string'}}, 'required': ['text'], 'additionalProperties': False}
REVIEW_SCHEMA = {'type': 'object', 'properties': {'equivalent': {'type': 'boolean'},
    'complete_sentences': {'type': 'boolean'}, 'close_wording': {'type': 'boolean'}, 'issue': {'type': 'string'}},
    'required': ['equivalent', 'complete_sentences', 'close_wording', 'issue'], 'additionalProperties': False}
FAILURE_MESSAGE = "The local model couldn't fit the material facts into a complete sentence within 110 characters. This description needs review."


def numeric_tokens(text):
    # Equivalent number words and digits represent the same quantity.
    words = ['zero','one','two','three','four','five','six','seven','eight','nine','ten',
             'eleven','twelve','thirteen','fourteen','fifteen','sixteen','seventeen','eighteen','nineteen','twenty']
    # Avoid converting parts of compound numbers such as twenty-five or one hundred.
    compounds = re.compile(r'\b(?:' + '|'.join(words) + r')(?:[ -]+(?:hundred|thousand|million|billion|(?:' + '|'.join(words[1:]) + r')))\b', re.I)
    protected = []
    def protect(match):
        protected.append(match.group().lower()); return 'QUANTITYPLACEHOLDER'
    text = compounds.sub(protect, text)
    for number, word in enumerate(words):
        text = re.sub(r'\b' + word + r'\b', str(number), text, flags=re.I)
    return Counter(re.findall(r'(?<!\w)\d+(?:[.,:/-]\d+)*(?:\s?[%°])?', text) + protected)

def compact_draft(text: str) -> str:
    """Conservative whole-phrase/unit edits; never slice a sentence or edit quoted names."""
    parts = re.split(r'("[^"]*"|“[^”]*”)', text)
    for i in range(0, len(parts), 2):
        part = parts[i]
        part = re.sub(r'\ban outdoor living space\b', 'outdoor living space', part)
        part = re.sub(r'~(\d+(?:\.\d+)?)\s+yrs?\b', r'~\1yr', part)
        parts[i] = part
    return ''.join(parts)


def fallback_description(original, limit=LIMIT):
    """A visibly flagged source excerpt when inference fails; no invented words or numbers."""
    clean = re.sub(r'\s+', ' ', original.replace('—', ',').replace('…', '.')).strip()
    # Prefer a whole source sentence or independent narrative clause.
    for part in re.split(r'(?<=[.!?])\s+|,?\s+(?:but|and then|so)\s+', clean, flags=re.I):
        part = part.strip(' ,;:.!?') + '.'
        if part != '.' and len(part) <= limit and not hard_errors(original, part, limit):
            return part
    words = clean.split()
    excerpt = ''
    for word in words:
        trial = (excerpt + ' ' + word).strip().rstrip(' ,;:.!?') + '.'
        if len(trial) > limit: break
        excerpt = trial[:-1]
    if not excerpt:
        # A single unbroken token is not a prose description and cannot be shortened safely.
        raise ReviewNeeded('No usable prose was found. Please review this input.')
    return excerpt.rstrip(' ,;:.!?') + '.'


class ReviewNeeded(Exception):
    pass


def validate_limit(value):
    if type(value) is not int or value < 110:
        raise ValueError("Character limit must be a whole number of at least 110, including spaces and punctuation.")
    return value


def failure_message(limit):
    return FAILURE_MESSAGE.replace("110 characters", f"{limit} characters")


def hard_errors(original: str, candidate: str, limit: int = LIMIT) -> list[str]:
    errors = []
    if not candidate.strip(): errors.append('No meaning-preserving result was found.')
    if len(candidate) > limit: errors.append(f'{len(candidate)} characters exceeds {limit}.')
    if '\u2014' in candidate: errors.append('Contains an em dash.')
    if not re.search(r'[.!?][\"\u201d\u2019\']?$', candidate) or re.search(r'(\.{2,}|\u2026)[\"\u201d\u2019\']?$', candidate):
        errors.append('Must end with a complete sentence, without an ellipsis.')
    if numeric_tokens(candidate) - numeric_tokens(original): errors.append('A number, quantity or numeric specification changed.')
    return errors


class LocalModel:
    def __init__(self, resources: Path, model_path: Path | None = None, limit: int = LIMIT):
        self.limit = validate_limit(limit)
        self.resources = resources
        self.model_path = model_path or resources / 'model.gguf'
        self.process = None
        self.close_job = None
        self.backend = 'metal' if sys.platform == 'darwin' else 'cpu'
        self.key = secrets.token_hex(24)
        self.cache = {}
        self.reviews = {}
        atexit.register(self.close)

    def start(self):
        if self.process and self.process.poll() is None: return
        if self.process: self.close()
        executable = 'llama-server.exe' if os.name == 'nt' else 'llama-server'
        if sys.platform == 'darwin':
            choices = [('metal', self.resources / 'llama' / executable)]
        else:
            choices = [('vulkan', self.resources / 'llama' / 'vulkan' / executable),
                       ('cpu', self.resources / 'llama' / 'cpu' / executable)]
            if os.environ.get('DESCRIPTION_SHORTENER_BACKEND') == 'cpu': choices = choices[-1:]
        last_error = 'The bundled model or engine is missing. Reinstall the complete app.'
        for backend, server in choices:
            if not server.is_file() or not self.model_path.is_file(): continue
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
            self.url = f'http://127.0.0.1:{port}'
            args = [str(server), '-m', str(self.model_path), '--host', '127.0.0.1',
                '--port', str(port), '--api-key', self.key, '-c', '8192' if backend == 'metal' else '4096',
                '-ngl', '0' if backend == 'cpu' else '99', '--parallel', '1', '--jinja',
                '--reasoning', 'off', '--reasoning-format', 'deepseek', '--no-webui']
            if backend != 'metal': args += ['-b', '128', '-ub', '64']
            try:
                self.process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            except OSError:
                last_error = 'The bundled engine could not launch. Check this computer’s supported architecture.'
                continue
            if os.name == 'nt':
                from windows_job import attach_job
                try: self.close_job = attach_job(self.process.pid)
                except OSError:
                    exited = self.process.poll() is not None
                    self.close()
                    if exited:
                        last_error = 'The local engine could not start. Check available memory.'
                        continue
                    raise RuntimeError('The engine could not establish reliable process cleanup on this computer.')
            self.backend = backend
            for _ in range(180):
                if self.process.poll() is not None:
                    last_error = 'The local engine could not start. Check available memory.'; break
                try:
                    req = urllib.request.Request(self.url + '/health', headers={'Authorization': 'Bearer ' + self.key})
                    with urllib.request.urlopen(req, timeout=1) as response:
                        if response.status == 200: return
                except (OSError, ValueError): pass
                time.sleep(0.5)
            self.close()
        raise RuntimeError(last_error)

    def close(self):
        if self.process is not None:
            self.process.terminate()
            try: self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            self.process = None
        if self.close_job:
            self.close_job(); self.close_job = None

    def ask(self, system, payload, schema=None):
        self.start()
        if system == SYSTEM:
            system = system.replace("110 characters", f"{self.limit} characters")
            system += f"\nFor this draft, aim for at most {payload.get('word_budget_guidance', 21)} words. The hard character limit is {self.limit}. Keep the gist; supporting details may be omitted."
        messages = [{'role': 'system', 'content': system},
                    {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False)}]
        if payload.get('previous_candidate'):
            messages = [{'role': 'system', 'content': system},
                        {'role': 'user', 'content': json.dumps({'description': payload['description'], 'limit_including_spaces': self.limit, 'word_budget_guidance': payload.get('word_budget_guidance')})},
                        {'role': 'assistant', 'content': json.dumps({'text': payload['previous_candidate']})},
                        {'role': 'user', 'content': f"Revise that draft. It has {len(payload['previous_candidate'])} characters. Maximum: {self.limit}. "
                            + payload.get('previous_issue', '') + ' '
                            + f" Aim for about {payload.get('word_budget_guidance', 21)} words while keeping the gist. "
                            + payload.get('revision_instruction', '')
                            + ' Remove redundant infinitive wording where equivalent (wanted to have more room -> wanted more room). Return a complete sentence in JSON.'}]
        body = {'messages': messages,
                'temperature': 0.2 if payload.get('previous_candidate') else 0.1,
                'seed': 42 + 17 * payload.get('attempt', 0) + len(payload.get('previous_candidate', '')), 'max_tokens': min(768, max(96, self.limit)), 'cache_prompt': True,
                'response_format': {'type': 'json_object'} if schema is None else {'type': 'json_schema', 'json_schema': {'name': 'result', 'strict': True, 'schema': schema}},
                'chat_template_kwargs': {'enable_thinking': False}}
        req = urllib.request.Request(self.url + '/v1/chat/completions',
            data=json.dumps(body).encode(), headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.key})
        with urllib.request.urlopen(req, timeout=180) as response:
            content = json.load(response)['choices'][0]['message']['content']
        try:
            return json.loads(content)
        except (json.JSONDecodeError, TypeError):
            raise ReviewNeeded('The local model returned an incomplete response. This description needs review.') from None

    def shorten(self, original):
        cache_key = (self.limit, original)
        if cache_key in self.cache: return self.cache[cache_key]
        source = original.strip()
        if not hard_errors(original, source, self.limit):
            self.cache[cache_key] = source
            return source
        previous, reason = '', ''
        budget = max(10, self.limit // 6)
        for attempt in range(2):
            try:
                data = self.ask(SYSTEM, {'description': source[:12000], 'limit_including_spaces': self.limit,
                    'previous_candidate': previous, 'previous_issue': reason,
                    'word_budget_guidance': budget, 'attempt': attempt}, TEXT_SCHEMA)
                candidate = data.get('text', '')
                candidate = candidate.strip() if isinstance(candidate, str) else ''
                errors = hard_errors(original, candidate, self.limit)
                if not errors:
                    self.cache[cache_key] = candidate
                    self.reviews[cache_key] = 'May need review: supporting details may have been omitted.'
                    return candidate
                previous, reason = candidate, ' '.join(errors)
                if candidate: budget = max(8, min(budget - 1, int(len(candidate.split()) * (self.limit - 1) / max(len(candidate), 1))))
            except (OSError, ValueError, ReviewNeeded, RuntimeError):
                reason = 'The model was unavailable or returned an incomplete response.'
                break
        candidate = fallback_description(original, self.limit)
        self.cache[cache_key] = candidate
        self.reviews[cache_key] = 'May need review: a best-effort source excerpt was used because the model could not produce a valid result.'
        return candidate

    def review_for(self, original):
        return self.reviews.get((self.limit, original), '')


@dataclass
class Item:
    location: str
    original: str
    apply: object


def xml(data):
    return ET.fromstring(data, ET.XMLParser(resolve_entities=False, no_network=True, remove_blank_text=False))


def xml_bytes(root):
    return ET.tostring(root, encoding='UTF-8', xml_declaration=True)


def column(ref):
    return re.sub(r'\d', '', ref)


def relevant(value, header=''):
    if not isinstance(value, str) or not value.strip(): return False
    if IDENTIFIER.search(header) and not DESCRIPTION.search(header): return False
    if re.match(r'^\s*(?:https?://|www\.|=|\S+@\S+\.)', value): return False
    return bool(DESCRIPTION.search(header)) or (len(value.strip()) > LIMIT and len(value.split()) >= 5)


class Package:
    def __init__(self, path):
        self.path = path
        self.entries = {}
        self.roots = {}
        self.items = []
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if sum(x.file_size for x in infos) > 512 * 1024 * 1024:
                raise ValueError('Expanded file exceeds the 512 MB processing limit.')
            if len({x.filename for x in infos}) != len(infos): raise ValueError('The file contains duplicate ZIP entries.')
            self.entries = {x.filename: (x, archive.read(x)) for x in infos}

    def root(self, name):
        if name not in self.roots: self.roots[name] = xml(self.entries[name][1])
        return self.roots[name]

    def write(self, output):
        # Only parts explicitly marked as changed are serialized.
        with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, (info, data) in self.entries.items():
                archive.writestr(info, xml_bytes(self.roots[name]) if name in self.changed else data)


class Workbook(Package):
    def __init__(self, path):
        super().__init__(path)
        self.changed = set()
        shared = []
        if 'xl/sharedStrings.xml' in self.entries:
            # Only <t> content is text: phonetic annotations are not descriptions.
            shared = [''.join(si.xpath('.//s:t/text()', namespaces=NS)) for si in self.root('xl/sharedStrings.xml').findall(f'{{{S}}}si')]
        sheet_names = {}
        relpath = 'xl/_rels/workbook.xml.rels'
        if relpath in self.entries:
            import posixpath
            relationships = {r.get('Id'): posixpath.normpath('xl/' + r.get('Target', '')) if not r.get('Target', '').startswith('/') else r.get('Target').lstrip('/') for r in self.root(relpath)}
            for s in self.root('xl/workbook.xml').xpath('//*[local-name()="sheet"]'):
                sheet_names[relationships.get(s.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'))] = s.get('name')
        for name in self.entries:
            if not re.fullmatch(r'xl/worksheets/sheet\d+\.xml', name): continue
            root = self.root(name)
            rows = root.findall(f'{{{S}}}sheetData/{{{S}}}row')
            headers = {}
            header_row = None
            for row in rows[:20]:
                strings = [(c, self.cell_text(c, shared)) for c in row.findall(f'{{{S}}}c')]
                if any(DESCRIPTION.search(t or '') for c, t in strings if len(t or '') < 80 and len((t or '').split()) < 7 and not re.search(r'[.!?]$', t or '')):
                    headers = {column(c.get('r', '')): t or '' for c, t in strings}
                    header_row = row.get('r')
                    break
            if not headers and rows:
                first = [(c, self.cell_text(c, shared)) for c in rows[0].findall(f'{{{S}}}c')]
                # Short label-like first rows are headers. A long first description is data.
                if first and all(t is None or (len(t) < 80 and not re.search(r'[.!?]$', t)) for c, t in first):
                    headers = {column(c.get('r', '')): t or '' for c, t in first}
                    header_row = rows[0].get('r')
            for row in rows:
                if header_row is not None and int(row.get('r', '0')) <= int(header_row): continue
                for cell in row.findall(f'{{{S}}}c'):
                    text = self.cell_text(cell, shared)
                    if not relevant(text, headers.get(column(cell.get('r', '')), '')): continue
                    def update(value, cell=cell, name=name):
                        # Per-cell inline strings avoid changing other cells sharing the same string.
                        for child in list(cell):
                            if child.tag in (f'{{{S}}}v', f'{{{S}}}is'): cell.remove(child)
                        cell.set('t', 'inlineStr')
                        inline = ET.SubElement(cell, f'{{{S}}}is')
                        t = ET.SubElement(inline, f'{{{S}}}t')
                        t.text = value
                        t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
                        self.changed.add(name)
                    self.items.append(Item(f'{sheet_names.get(name, name)}!{cell.get("r")}', text, update))

    @staticmethod
    def cell_text(cell, shared):
        if cell.find(f'{{{S}}}f') is not None: return None
        if cell.get('t') == 's':
            v = cell.findtext(f'{{{S}}}v')
            return shared[int(v)] if v is not None else None
        if cell.get('t') == 'inlineStr': return ''.join(cell.xpath('./s:is//s:t/text()', namespaces=NS))
        return None


class Document(Package):
    def __init__(self, path):
        super().__init__(path)
        self.changed = set()
        for name in self.entries:
            if name != 'word/document.xml': continue  # Headers, footers, comments and metadata remain intact.
            root = self.root(name)
            for index, paragraph in enumerate(root.findall(f'.//{{{W}}}p'), 1):
                texts = paragraph.findall(f'.//{{{W}}}t')
                original = ''.join(t.text or '' for t in texts)
                style = paragraph.find(f'{{{W}}}pPr/{{{W}}}pStyle')
                if style is not None and re.search('heading|title|subtitle|caption', style.get(f'{{{W}}}val', ''), re.I): continue
                if not original.strip(): continue
                # Short labels are left alone; long prose and sentence-like descriptions are processed.
                if len(original) <= LIMIT and not re.search(r'[.!?\u2014]', original): continue
                complex_content = paragraph.xpath('.//w:fldChar | .//w:instrText | .//w:del | .//w:ins | .//w:drawing | .//w:tab | .//w:br', namespaces=NS)
                def update(value, texts=texts, name=name, complex_content=complex_content):
                    if complex_content: raise ReviewNeeded('This paragraph contains fields, tracked changes, or embedded content. Resolve these first.')
                    texts[0].text = value
                    texts[0].set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
                    for t in texts[1:]: t.text = ''
                    self.changed.add(name)
                self.items.append(Item(f'Paragraph {index}', original, update))


class TextFile:
    def __init__(self, path):
        raw = Path(path).read_bytes()
        self.encoding = detect_encoding(raw)
        text = raw.decode(self.encoding)
        self.lines = text.splitlines(keepends=True)
        self.items = []
        for index, line in enumerate(self.lines):
            original = line.rstrip('\r\n')
            ending = line[len(original):]
            if not original.strip(): continue
            def update(value, index=index, ending=ending): self.lines[index] = value + ending
            self.items.append(Item(f'Line {index + 1}', original, update))

    def write(self, output): Path(output).write_bytes(''.join(self.lines).encode(self.encoding))


def detect_encoding(raw):
    if raw.startswith(b'\xef\xbb\xbf'): return 'utf-8-sig'
    if raw.startswith((b'\xff\xfe', b'\xfe\xff')): return 'utf-16'
    try: raw.decode('utf-8'); return 'utf-8'
    except UnicodeDecodeError: return 'cp1252'


class CSVFile:
    def __init__(self, path):
        raw = Path(path).read_bytes()
        self.encoding = detect_encoding(raw)
        text = raw.decode(self.encoding)
        self.newline = '\r\n' if '\r\n' in text else '\n'
        try: self.dialect = csv.Sniffer().sniff(text[:65536], delimiters=',;\t|')
        except csv.Error: self.dialect = csv.excel
        self.rows = list(csv.reader(io.StringIO(text, newline=''), self.dialect))
        self.items = []
        if not self.rows: return
        first = self.rows[0]
        has_header = any(DESCRIPTION.search(t) for t in first if len(t) < 80 and len(t.split()) < 7 and not re.search(r'[.!?]$', t)) or all(len(t) < 80 and not re.search(r'[.!?]$', t) for t in first)
        headers = first if has_header else []
        for r in range(1 if has_header else 0, len(self.rows)):
            for c, value in enumerate(self.rows[r]):
                if not relevant(value, headers[c] if c < len(headers) else ''): continue
                def update(result, r=r, c=c): self.rows[r][c] = result
                self.items.append(Item(f'Row {r + 1}, column {c + 1}', value, update))

    def write(self, output):
        with open(output, 'w', encoding=self.encoding, newline='') as handle:
            writer = csv.writer(handle, self.dialect, lineterminator=self.newline)
            writer.writerows(self.rows)


def process_file(source, destination, model, progress=lambda *args: None):
    source, destination = Path(source), Path(destination)
    if source.stat().st_size > 128 * 1024 * 1024: raise ValueError('The file exceeds the 128 MB input limit.')
    if source.resolve() == destination.resolve(): raise ValueError('Choose a new output filename. Originals are never overwritten.')
    if destination.exists(): raise ValueError('That output file already exists. Choose a new filename.')
    if source.suffix.lower() != destination.suffix.lower(): raise ValueError('The output must use the same file extension.')
    factories = {'.xlsx': Workbook, '.csv': CSVFile, '.docx': Document, '.txt': TextFile}
    if source.suffix.lower() not in factories: raise ValueError('Use XLSX, CSV, DOCX or TXT. Convert other documents using the app first.')
    document = factories[source.suffix.lower()](source)
    issues, edits, warnings = [], [], []
    for index, item in enumerate(document.items, 1):
        progress(index, len(document.items), item.location)
        try:
            result = model.shorten(item.original)
            errors = hard_errors(item.original, result, getattr(model, 'limit', LIMIT))
            if errors: raise ReviewNeeded(' '.join(errors))
            warning = getattr(model, 'review_for', lambda _: '')(item.original)
            if warning: warnings.append({'location': item.location, 'reason': warning})
            if result != item.original:
                item.apply(result)
                edits.append({'location': item.location, 'original': item.original, 'text': result, 'characters': len(result)})
        except ReviewNeeded as exc:
            issues.append({'location': item.location, 'reason': str(exc), 'original': item.original})
    if issues:
        return {'ok': False, 'issues': issues, 'checked': len(document.items), 'changed': len(edits)}
    fd, temporary = tempfile.mkstemp(prefix='.description-shortener-', suffix=destination.suffix, dir=destination.parent)
    os.close(fd)
    try:
        document.write(temporary)
        # Exclusive destination creation avoids accidentally replacing a file made while processing.
        try:
            os.link(temporary, destination)
        except OSError as error:
            if isinstance(error, FileExistsError): raise
            # FAT/exFAT and some network drives do not support hard links.
            if error.errno not in (errno.EPERM, errno.EACCES, errno.EXDEV, errno.ENOSYS, errno.EOPNOTSUPP, errno.EINVAL): raise
            created = False
            try:
                with open(destination, 'xb') as output:
                    created = True
                    with open(temporary, 'rb') as input_file: shutil.copyfileobj(input_file, output)
                    output.flush(); os.fsync(output.fileno())
            except BaseException:
                if created: destination.unlink(missing_ok=True)
                raise
    finally:
        Path(temporary).unlink(missing_ok=True)
    return {'ok': True, 'path': str(destination), 'checked': len(document.items), 'changed': len(edits), 'edits': edits, 'warnings': warnings}


def handle_request(request, model, emit):
    if request.get('mode') == 'warm':
        model.start()
        emit({'event': 'ready', 'ok': True, 'backend': model.backend})
        return
    model.limit = validate_limit(request.get('character_limit', LIMIT))
    if request.get('mode') == 'text':
        originals = [line for line in request.get('text', '').splitlines() if line.strip()]
        if not originals: raise ValueError('Paste a description first.')
        results, issues, warnings = [], [], []
        for index, original in enumerate(originals, 1):
            emit({'event': 'progress', 'current': index, 'total': len(originals), 'location': f'Description {index}'})
            try:
                result = model.shorten(original)
                errors = hard_errors(original, result, model.limit)
                if errors: raise ReviewNeeded(' '.join(errors))
                results.append(result)
                warning = getattr(model, 'review_for', lambda _: '')(original)
                if warning: warnings.append({'location': f'Description {index}', 'reason': warning})
            except ReviewNeeded as exc:
                issues.append({'location': f'Description {index}', 'reason': str(exc), 'original': original})
        if issues:
            emit({'event': 'result', 'ok': False, 'error': failure_message(model.limit), 'issues': issues})
        else:
            emit({'event': 'result', 'ok': True, 'text': '\n'.join(results), 'counts': [len(x) for x in results], 'warnings': warnings})
    else:
        result = process_file(request['source'], request['destination'], model,
            lambda current, total, location: emit({'event': 'progress', 'current': current, 'total': total, 'location': location}))
        emit({'event': 'result', **result})


def main():
    if os.name == 'nt':
        sys.stdin.reconfigure(encoding='utf-8'); sys.stdout.reconfigure(encoding='utf-8')
    model = LocalModel(Path(sys.argv[1]))
    def stop(*_):
        model.close()
        raise SystemExit(130)
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    def process(request):
        def emit(obj):
            print(json.dumps({'request_id': request.get('request_id'), **obj}, ensure_ascii=False), flush=True)
        try: handle_request(request, model, emit)
        except Exception as exc:
            emit({'event': 'ready' if request.get('mode') == 'warm' else 'result', 'ok': False, 'error': str(exc)})
    try:
        if '--serve' in sys.argv:
            for line in sys.stdin:
                if line.strip(): process(json.loads(line))
        else: process(json.load(sys.stdin))
    finally: model.close()

if __name__ == '__main__': main()
