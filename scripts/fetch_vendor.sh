#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p vendor licenses
curl -fL --retry 3 -o vendor/llama.tar.gz https://github.com/ggml-org/llama.cpp/releases/download/b11531/llama-b11531-bin-macos-arm64.tar.gz
tar -xzf vendor/llama.tar.gz -C vendor
ln -sfn llama-b11531 vendor/llama
curl -fL --retry 3 -o vendor/model.gguf https://huggingface.co/google/gemma-4-12B-it-qat-q4_0-gguf/resolve/29d097773436b69ff9feafd636ab4cf873786537/gemma-4-12b-it-qat-q4_0.gguf
curl -fsSL -o licenses/Gemma4-LICENSE https://www.apache.org/licenses/LICENSE-2.0.txt
curl -fsSL -o licenses/Python-LICENSE.txt https://raw.githubusercontent.com/python/cpython/v3.13.1/LICENSE
curl -fsSL -o licenses/llama-third-party-httplib-LICENSE https://raw.githubusercontent.com/ggml-org/llama.cpp/b11531/vendor/cpp-httplib/LICENSE
curl -fsSL -o licenses/llama-third-party-json-LICENSE https://raw.githubusercontent.com/ggml-org/llama.cpp/b11531/licenses/LICENSE-jsonhpp
