#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p vendor licenses
curl -fL --retry 3 -o vendor/llama.tar.gz https://github.com/ggml-org/llama.cpp/releases/download/b11531/llama-b11531-bin-macos-arm64.tar.gz
tar -xzf vendor/llama.tar.gz -C vendor
ln -sfn llama-b11531 vendor/llama
curl -fL --retry 3 -o vendor/model.gguf https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF/resolve/a06e946bb6b655725eafa393f4a9745d460374c9/Qwen3-4B-Instruct-2507-Q3_K_M.gguf
curl -fsSL -o licenses/Qwen3-LICENSE https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF/raw/a06e946bb6b655725eafa393f4a9745d460374c9/LICENSE
curl -fsSL -o licenses/Python-LICENSE.txt https://raw.githubusercontent.com/python/cpython/v3.13.1/LICENSE
curl -fsSL -o licenses/llama-third-party-httplib-LICENSE https://raw.githubusercontent.com/ggml-org/llama.cpp/b11531/vendor/cpp-httplib/LICENSE
curl -fsSL -o licenses/llama-third-party-json-LICENSE https://raw.githubusercontent.com/ggml-org/llama.cpp/b11531/licenses/LICENSE-jsonhpp
