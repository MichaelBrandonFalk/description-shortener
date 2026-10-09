# Bundled open-source credits

Description Shortener includes unmodified third-party components. Their original license terms apply; complete available license texts are in the app's Resources/licenses folder, accessible through the Licenses button.

- **llama.cpp b11531**, Georgi Gerganov and contributors, MIT. [Source](https://github.com/ggml-org/llama.cpp/tree/b11531) · [License](https://github.com/ggml-org/llama.cpp/blob/b11531/LICENSE). Includes ggml and the upstream server's third-party components.
- **Qwen3 4B Instruct 2507 Q3_K_M**, Qwen Team / Alibaba Cloud; quantization by Unsloth, Apache-2.0. The unmodified Unsloth GGUF quantization is bundled. [Model and attribution](https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF) · [License](https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF/blob/main/LICENSE). Model revision: `a06e946bb6b655725eafa393f4a9745d460374c9`.
- **lxml 6.0.2**, Infrae and contributors, BSD-3-Clause. [Source](https://github.com/lxml/lxml) · [Licensing](https://lxml.de/FAQ.html#what-is-the-license). Its binary wheel also includes libxml2 and libxslt, under their included licenses.
- **Python 3.13.1**, Python Software Foundation and contributors, PSF license. [Source](https://github.com/python/cpython/tree/v3.13.1) · [License](https://docs.python.org/3.13/license.html). Standard-library components retain their own notices.
- **PyInstaller 6.16.0**, PyInstaller development team, GPL with bootloader distribution exception. [Source](https://github.com/pyinstaller/pyinstaller/tree/v6.16.0) · [License](https://pyinstaller.org/en/stable/license.html).

Build tooling includes altgraph (MIT), macholib (MIT), packaging (Apache-2.0/BSD-2-Clause), setuptools (MIT), and PyInstaller hooks (Apache-2.0/GPL with exception). Their installed notices are included in the bundled license folder.

The native interface uses Apple's macOS system frameworks, which are provided by the operating system.
