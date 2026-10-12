# Bundled open-source credits

Description Shortener includes unmodified third-party components. Their original license terms apply; complete available license texts are in the app's Resources/licenses folder, accessible through the Licenses button.

- **llama.cpp b11531**, Georgi Gerganov and contributors, MIT. [Source](https://github.com/ggml-org/llama.cpp/tree/b11531) · [License](https://github.com/ggml-org/llama.cpp/blob/b11531/LICENSE). Includes ggml and the upstream server's third-party components.
- **Gemma 4 12B QAT Q4_0**, Google DeepMind, Apache-2.0. The official, unmodified Google GGUF is bundled. [Model and attribution](https://huggingface.co/google/gemma-4-12B-it) · [Official quantization](https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-gguf) · [Apache 2.0 license](https://www.apache.org/licenses/LICENSE-2.0). Model revision: `29d097773436b69ff9feafd636ab4cf873786537`; file `gemma-4-12b-it-qat-q4_0.gguf`, SHA256 `93567e57a8fe10b23569b9d9ec38cd005deedf71e29477c421a4b83f418a538b`.

- **lxml 6.0.2**, Infrae and contributors, BSD-3-Clause. [Source](https://github.com/lxml/lxml) · [Licensing](https://lxml.de/FAQ.html#what-is-the-license). Its binary wheel also includes libxml2 and libxslt, under their included licenses.
- **Python 3.13**, Python Software Foundation and contributors, PSF license. [Source](https://github.com/python/cpython/tree/3.13) · [License](https://docs.python.org/3.13/license.html). Standard-library components retain their own notices.
- **PyInstaller 6.16.0**, PyInstaller development team, GPL with bootloader distribution exception. [Source](https://github.com/pyinstaller/pyinstaller/tree/v6.16.0) · [License](https://pyinstaller.org/en/stable/license.html).

Build tooling includes altgraph (MIT), macholib (MIT), packaging (Apache-2.0/BSD-2-Clause), setuptools (MIT), and PyInstaller hooks (Apache-2.0/GPL with exception). Their installed notices are included in the bundled license folder.

The native interface uses Apple's macOS system frameworks, which are provided by the operating system.

## Browser runtime

The GitHub Pages browser app additionally vendors wllama 3.8.1 (MIT), hash-wasm 4.12.0 (MIT), and fflate 0.8.3 (MIT). License texts are in `docs/browser/vendor/`. Browser GGUF shard metadata is derived from the same pinned Google Gemma model under Apache-2.0; model weights download directly from its official pinned URL.

- [wllama](https://github.com/ngxson/wllama), WebAssembly/WebGPU bindings for llama.cpp.
- [hash-wasm](https://github.com/Daninet/hash-wasm), incremental SHA-256 verification.
- [fflate](https://github.com/101arrowz/fflate), local XLSX and DOCX ZIP handling.

## Windows and Linux desktop previews

The desktop previews use [Electron 44.7.0](https://github.com/electron/electron) (MIT) and its bundled Chromium/Node.js notices. Their included `LICENSE` and `LICENSES.chromium.html` files ship with the desktop runtime. Packaging uses [@electron/packager 20.3.0](https://github.com/electron/packager) (BSD-2-Clause). These previews bundle the same Google model and Python processing dependencies as the Mac build, plus official llama.cpp b11531 CPU and Vulkan binaries.

The Windows preview additionally includes unmodified Microsoft Visual C++ x64 runtime DLLs from the CI host's Visual Studio redistributable directory, using [Microsoft's local deployment method](https://learn.microsoft.com/en-us/cpp/windows/choosing-a-deployment-method). These Microsoft components are proprietary and retain Microsoft's terms. Bundled notices record their source version and SHA-256 values. They are included beside the model runtime so a separate C++ runtime installation is unnecessary.
