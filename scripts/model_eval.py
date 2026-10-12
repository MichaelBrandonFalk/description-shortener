"""Screen hosted responses and local finalists with the same measured checks.

The checks catch specified omissions; passing still requires human semantic review.
Keep actual customer inputs and hosted responses in ignored build/qa, never Git.
"""
import argparse
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from engine import LocalModel, ReviewNeeded, hard_errors

def check(case, text):
    if not isinstance(text, str): return ['Missing response.']
    errors = hard_errors(case['description'], text)
    for pattern in case['required']:
        if not re.search(pattern, text, re.I): errors.append(f'Missing required detail: {pattern}')
    for pattern in case['forbidden']:
        if re.search(pattern, text, re.I): errors.append(f'Changed meaning: {pattern}')
    return errors

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--responses', type=Path, help='JSON object of case ID to hosted response text.')
    source.add_argument('--model', type=Path, help='Local GGUF finalist, tested before packaging.')
    parser.add_argument('--resources', type=Path, default=ROOT/'vendor')
    parser.add_argument('--cases', type=Path, default=ROOT/'benchmarks/cases.json')
    args = parser.parse_args()
    cases = json.loads(args.cases.read_text())
    responses = json.loads(args.responses.read_text()) if args.responses else {}
    model = LocalModel(args.resources, args.model) if args.model else None
    failures = 0
    try:
        for case in cases:
            started = time.monotonic()
            try:
                text = model.shorten(case['description']) if model else responses.get(case['id'])
                errors = check(case, text)
                if model and model.review_for(case['description']):
                    errors = [e for e in errors if not e.startswith('Missing required detail:')]
                warning = model.review_for(case['description']) if model else ''
            except ReviewNeeded as error:
                text = None; errors = [str(error)]
            failures += bool(errors)
            print(json.dumps({'case':case['id'], 'text':text, 'characters':len(text) if text else 0,
                'errors':errors, 'warning':warning, 'seconds':round(time.monotonic()-started,2) if model else None}), flush=True)
    finally:
        if model: model.close()
    return 1 if failures else 0

if __name__ == '__main__': sys.exit(main())
