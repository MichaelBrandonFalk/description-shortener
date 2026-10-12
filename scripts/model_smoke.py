"""Fail the release check if the selected local model misses a benchmark rule."""
from pathlib import Path
import sys
from model_eval import main

if __name__ == '__main__':
    sys.argv = [sys.argv[0], '--model', str(Path(__file__).resolve().parents[1] / 'vendor/model.gguf')]
    sys.exit(main())
