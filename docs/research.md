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

V1.0 bundled Qwen3 4B. V1.1 selects Gemma 4 12B after comparing Qwen3.5 2B/4B/9B, Mistral Small 3.2 24B, and Granite 4.2 8B locally, with additional hosted screening. The V1.1–V1.3 rules preserved material facts while allowing incidental enjoyment to be omitted. See [evaluation evidence](model_evaluation.md). The model is about 7 GB, and no model setup is required after installation.

## Alternatives considered

- [openpyxl](https://pypi.org/project/openpyxl/) (MIT): useful workbook API, but a full workbook round trip may discard unsupported features. Targeted XML edits preserve more of the original workbook.
- [python-docx](https://github.com/python-openxml/python-docx) (MIT): useful document API; direct package edits give more explicit control of untouched parts and runs.
- [Qwen2.5 3B](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct/blob/main/LICENSE): rejected because its research license restricts commercial use.

## Limits

No language model can guarantee semantic equivalence for arbitrary descriptions. A 110-character budget can be incompatible with retaining all material facts. V1.1–V1.3 combined word-budget guidance, bounded drafting/revision, conservative whole-phrase and unit formatting, hard format checks, protected numeric tokens, and a separate model review. Incidental narrative enjoyment may be omitted; product attributes and factual claims remain material. In those versions unresolved items blocked file export and show their locations. Human review is still recommended for changed wording. The original is never overwritten.

## Browser processing, V1.2

[WebLLM](https://github.com/mlc-ai/web-llm) was inspected, but its current prebuilt Gemma 4 model list provides E2B rather than the qualified 12B model. [wllama 3.8.1](https://github.com/ngxson/wllama) supports the existing GGUF with WebGPU and asynchronous file reads. Actual browser loading and shortening were tested with the same pinned 12B Q4_0 model. CPU-only fallback is not offered for this large model.

`llama-gguf-split` produces browser-compatible shards. `scripts/prepare_browser_model.py` verifies their data byte-for-byte against slices of the original model and publishes only shard headers and offsets. The browser downloads and hashes the official model into its own OPFS storage, then constructs shards from file slices. This avoids another public copy of 7 GB weights. Input text and documents stay in browser memory and are never posted to an inference server.

## V1.3 desktop portability checks

Windows x64 and Ubuntu 22.04 x64 reuse the pinned model and native processor through Electron. Native CI runs checked all 11 model cases and the extracted/installed application. The Windows candidate needed app-local Microsoft C++ runtime DLLs; actual process-module checks confirmed those files loaded from the app folder. Ubuntu installation caught and resolved PAX-header and missing-directory issues before publication.

The pinned Linux CPU runtime requires at most GLIBC 2.34, GLIBCXX 3.4.30 and CXXABI 1.3.13. Ubuntu 22.04 provides [GCC 12 libstdc++](https://packages.ubuntu.com/jammy/amd64/libstdc%2B%2B6). Use current Ubuntu updates. This qualifies the tested x64 Ubuntu target, not every distribution or GPU. [Microsoft local deployment guidance](https://learn.microsoft.com/en-us/cpp/windows/choosing-a-deployment-method) describes the Windows runtime packaging method.

## V1.4 gist and Linux Mint checks

The user-approved goal is a useful gist within the character limit, with supporting details allowed to drop. The prompt now states that directly. Valid drafts are returned with a review flag instead of being withheld by a separate semantic reviewer. Model failures use a clearly flagged source excerpt where possible. Native checks cover 11 synthetic cases, character limits, cache isolation and Office/CSV/TXT preservation.

The browser keeps its stable model file across application releases, requests persistent storage, uses a smaller 2048-token context and smaller batches, and releases failed runtimes. It also offers flagged excerpts without loading weights. Browser eviction or cleared data can still remove weights.

[Linux Mint 22.x uses the Ubuntu 24.04 base](https://linuxmint.com/rel_wilma.php). The installer test uses [the official Linux Mint 22.3 Cinnamon ISO](https://linuxmint.com/edition.php?id=326), pinned to its [published SHA-256](https://mirrors.kernel.org/linuxmint/stable/22.3/sha256sum.txt). The CI chroot checks actual Mint userspace, package installation, sandbox permissions, interface launch as a regular user, local model inference and file preservation. A full booted desktop and GPU hardware are not covered; LMDE and older Mint editions are not qualified.
