"""Keep browser model instructions and schemas in sync with the Mac engine."""
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from engine import SYSTEM, REVIEW, TEXT_SCHEMA, REVIEW_SCHEMA
(ROOT/'docs/browser/rules.json').write_text(json.dumps({'system':SYSTEM,'review':REVIEW,'textSchema':TEXT_SCHEMA,'reviewSchema':REVIEW_SCHEMA},indent=2)+'\n')
