# Open-source research

Research completed before implementation, October 9, 2026.

| Component | License | Decision and source |
| --- | --- | --- |
| llama.cpp b11531 | MIT | Bundle the official Apple Silicon inference runtime. Apple Metal acceleration; no separate installation. [Source](https://github.com/ggml-org/llama.cpp) · [Release](https://github.com/ggml-org/llama.cpp/releases/tag/b11531) |
| Qwen3 4B Instruct 2507 Q3_K_M | Apache-2.0 | Bundle the Unsloth quantized model at revision `a06e946bb6b655725eafa393f4a9745d460374c9`. Fits in a single GitHub release asset with the app. [Model and license](https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF) |
| lxml 6.0.2 | BSD-3-Clause plus bundled libxml2/libxslt licenses | Edit targeted Office XML parts while retaining untouched archive entries, formulas, styles, and relationships. [Source and license](https://github.com/lxml/lxml) |
| Python 3.13 | PSF license | Bundle the interpreter and standard-library CSV/ZIP tools. [License](https://docs.python.org/3/license.html) |
| PyInstaller 6.16.0 | GPL with distribution exception | Bundle the Python helper into the native Mac app. [License and exception](https://pyinstaller.org/en/stable/license.html) |

The interface uses Apple's system SwiftUI/AppKit frameworks. No separately installed UI runtime is required.

The initial 1.7B model was evaluated and rejected after failing realistic shortening cases. The final selection is the stronger non-thinking 4B Instruct model, using Q3_K_M quantization to keep the self-contained archive within GitHub release limits.

## Alternatives considered

- [openpyxl](https://pypi.org/project/openpyxl/) (MIT): useful workbook API, but a full workbook round trip may discard unsupported features. Targeted XML edits preserve more of the original workbook.
- [python-docx](https://github.com/python-openxml/python-docx) (MIT): useful document API; direct package edits give more explicit control of untouched parts and runs.
- [Qwen2.5 3B](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct/blob/main/LICENSE): rejected because its research license restricts commercial use.

## Limits

No language model can guarantee semantic equivalence for arbitrary descriptions. A 110-character budget can be incompatible with retaining all facts. The app combines hard format checks, protected numeric tokens, and a separate model review. Unresolved items block file export and show their locations. Human review is still recommended for changed wording. The original is never overwritten.
