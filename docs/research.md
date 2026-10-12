# Open-source research

Initial research preceded implementation on October 9, 2026. Model selection for V1.1 was updated on October 12 after local comparison and the clarified allowance to omit incidental enjoyment.

| Component | License | Decision and source |
| --- | --- | --- |
| llama.cpp b11531 | MIT | Bundle the official Apple Silicon inference runtime. Apple Metal acceleration; no separate installation. [Source](https://github.com/ggml-org/llama.cpp) · [Release](https://github.com/ggml-org/llama.cpp/releases/tag/b11531) |
| Gemma 4 12B QAT Q4_0 | Apache-2.0 | Bundle the official Google quantization at revision `29d097773436b69ff9feafd636ab4cf873786537`. Passed the eleven-case local material-fact benchmark and the actual reported regression. [Model card](https://huggingface.co/google/gemma-4-12B-it) · [Official GGUF](https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-gguf) |
| lxml 6.0.2 | BSD-3-Clause plus bundled libxml2/libxslt licenses | Edit targeted Office XML parts while retaining untouched archive entries, formulas, styles, and relationships. [Source and license](https://github.com/lxml/lxml) |
| Python 3.13 | PSF license | Bundle the interpreter and standard-library CSV/ZIP tools. [License](https://docs.python.org/3/license.html) |
| PyInstaller 6.16.0 | GPL with distribution exception | Bundle the Python helper into the native Mac app. [License and exception](https://pyinstaller.org/en/stable/license.html) |

The interface uses Apple's system SwiftUI/AppKit frameworks. No separately installed UI runtime is required.

V1.0 bundled Qwen3 4B. V1.1 selects Gemma 4 12B after comparing Qwen3.5 2B/4B/9B, Mistral Small 3.2 24B, and Granite 4.2 8B locally, with additional hosted screening. The final rules preserve material facts while allowing incidental enjoyment to be omitted. See [evaluation evidence](model_evaluation.md). The model is about 7 GB, and no model setup is required after installation.

## Alternatives considered

- [openpyxl](https://pypi.org/project/openpyxl/) (MIT): useful workbook API, but a full workbook round trip may discard unsupported features. Targeted XML edits preserve more of the original workbook.
- [python-docx](https://github.com/python-openxml/python-docx) (MIT): useful document API; direct package edits give more explicit control of untouched parts and runs.
- [Qwen2.5 3B](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct/blob/main/LICENSE): rejected because its research license restricts commercial use.

## Limits

No language model can guarantee semantic equivalence for arbitrary descriptions. A 110-character budget can be incompatible with retaining all material facts. The app combines word-budget guidance, bounded drafting/revision, conservative whole-phrase and unit formatting, hard format checks, protected numeric tokens, and a separate model review. Incidental narrative enjoyment may be omitted; product attributes and factual claims remain material. Unresolved items block file export and show their locations. Human review is still recommended for changed wording. The original is never overwritten.
