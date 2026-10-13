# Description Shortener

A self-contained, fully local desktop app that shortens descriptions to a chosen maximum character count, including spaces and punctuation. The default and minimum are 110. No account, API key, Python installation, or model download is needed after installing the app.

[Download page](https://michaelbrandonfalk.github.io/description-shortener/) · [Versioned releases](https://github.com/MichaelBrandonFalk/description-shortener/releases) · [Open-source research](docs/research.md)

## Use

1. On Mac, unzip the download and drag **Description Shortener V1.5.app** to Applications.
2. Open the app. Paste one description per line, or choose/drop a file.
3. Click **Shorten description** or **Shorten & save copy**.
4. Copy the text or use the saved file. Review details lists changed descriptions and any review flags.

The Mac app is ad-hoc signed, not Apple notarized. On first launch, macOS may require approving the app in System Settings → Privacy & Security → Open Anyway. This does not require disabling Gatekeeper. Developer ID signing is required for a future notarized release.

Use **Settings** to choose a whole-number maximum of at least 110. Spaces, punctuation and Unicode code points count toward the total. Changing the setting clears previous results and separates the model cache by limit.

## Supported input

| Input | Output and preservation |
| --- | --- |
| Pasted text | Only shortened descriptions in the output/copy area, one per line. |
| XLSX | XLSX; targeted description-like columns and long prose fields. Keeps sheet names, row order, formulas, non-description values, styles and untouched package parts. Changed rich-text cells become plain text while keeping cell formatting. |
| CSV | CSV; preserves column names, field values outside selected descriptions, delimiter, common encoding and newline style. Quoting may be normalized. |
| DOCX | DOCX; body paragraphs, including table cells. Retains paragraph structure and styles. Changed text inherits the first run's formatting. Headings, headers and footers remain unchanged. Complex fields and tracked changes may require review. |
| TXT | TXT; one description per nonempty line. |
| RTF, DOC, ODT | Same format through macOS conversion. Complex layout may change. |
| PDF | Selectable text is extracted and returned as TXT. No OCR or PDF layout preservation. |

The app inspects selected files without a written prompt. It never overwrites originals or existing destination files.

## Rules and verification

Every returned description is checked against the chosen character limit, em dashes, terminal punctuation, and invented numeric values. The local model receives a short gist-focused prompt and word budget before drafting. Supporting details may be omitted. Retained facts should remain accurate, but model output still needs human review.

There is at most one corrective generation pass and no second model reviewer. Shortened results carry “May need review” outside the copied text and outside description cells. If inference fails or drafts cannot pass the format checks, the app returns a flagged source excerpt when usable prose is available. An excerpt may be incomplete in meaning or grammar; the flag is deliberate. Original files are preserved.

Long identifier/name/title/link columns are excluded when identifiable. Generic long prose columns are selected by best judgment. Hidden sheets are included; formulas, blank cells and numeric values are left alone.

## Requirements and privacy

Apple Silicon (M1 or newer), macOS 14 or newer, 16 GB RAM minimum. The bundled Gemma model is about 7 GB. Allow roughly 25 GB free space during installation. Tested on an Apple Silicon Mac running macOS 26.4; older supported macOS versions are not independently tested.

Processing is offline. The bundled engine listens only on a random localhost port with a per-run random key. There are no analytics, remote model calls, or persistent input logs. Temporary conversion files are removed after processing. Inputs and outputs are not uploaded. Project/license links open externally when clicked.

## Build and version a change

Requires Xcode Command Line Tools and Python 3.13 on an Apple Silicon Mac.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
bash scripts/fetch_vendor.sh
.venv/bin/python scripts/build.py
```

`VERSION` is the single version source. Every delivered edit must increment it (1.0, 1.1, 1.2, ...), update CHANGELOG.md, and create a new immutable GitHub tag/release and ZIP. Old releases remain available. The build refuses to overwrite an existing versioned ZIP. Do not commit model weights, virtual environments, builds or private input files.

Use `scripts/release.sh` to publish the current verified version after committing source. GitHub authentication must be configured. Signing/notarization can be added when an Apple Developer ID certificate is available.

## Open source

See [third-party notices](THIRD_PARTY_NOTICES.md) and [research](docs/research.md). Credits are linked on the download page and at the bottom of the app. Full bundled license texts are available through the app's Licenses button.

## Download page hosting

The public download page is hosted on GitHub Pages from `main:/docs`. Edit `docs/index.html` and push to main to publish page updates. Website hosting corrections do not change the Mac binary or its immutable versioned release.

The complete V1.1 ZIP is about 7 GB, so its Download button uses the existing streaming endpoint to deliver one self-contained ZIP. The public page, source code and release history are on GitHub. Keep that endpoint available for existing downloads.

## Use in the browser

[Open the browser app](https://michaelbrandonfalk.github.io/description-shortener/browser/). It uses the same pinned Gemma 4 12B model on your own GPU through wllama. The first use downloads about 7 GB from the official model URL; SHA-256 is checked before loading. The model is stored in this browser’s private file storage. Application updates retain the same model file and origin. Persistent storage is requested, but browser eviction, changing browsers or clearing browser data can require another download. For the AI model, use a WebGPU-capable browser and preferably 24 GB RAM or more. A quick, flagged source excerpt is available without loading the model. Loading and processing depend on the browser and device; the native Mac app is faster on the tested Mac.

Paste text or select XLSX, CSV, DOCX or UTF-8 TXT files. No text or document is uploaded for inference. The browser saves a new file and retains sheet names, formulas, non-description values and untouched Office package content. Complex Word fields or tracked changes need review; legacy document formats and PDF use the Mac app. Browser CSV quoting may normalize, while delimiter, BOM, line endings, order and other field values are retained.

Run `node --test tests/browser.test.mjs` for browser counting, limit, cache and CSV checks. `scripts/export_browser_rules.py` keeps the model instructions and JSON schemas synchronized with the Python engine. `scripts/prepare_browser_model.py` verifies GGUF shard metadata against the pinned original weights.

## Windows, Ubuntu and Linux Mint previews (V1.5)

The same download page offers a self-contained Windows x64 ZIP and Ubuntu 22.04 / Linux Mint 22.x x64 DEB. Extract the entire Windows folder and open DescriptionShortener.exe, or install the Ubuntu DEB with your package installer. Python and the pinned model are included. The Windows preview is unsigned.

These previews support pasted text, XLSX, CSV, DOCX and TXT. Mac document conversion and PDF import remain Mac-only. CPU processing is checked on Windows Server 2022 and Ubuntu 22.04 hosted runners using 11 actual-model gist benchmarks, selected-limit/cache checks and packaged file processing. The exact downloadable archives are also reconstructed and verified, extracted/installed, and used to launch the native app. GPU acceleration and consumer hardware remain unqualified. See [desktop details](desktop/README.md).

Linux Mint 22.3 Cinnamon is checked using checksum-pinned official ISO userspace in a CI userspace container: install the exact DEB, launch the sandboxed interface as a regular user, and exercise the packaged model and files. This is not a booted Cinnamon session or GPU hardware test. Other Mint 22.x editions share the Ubuntu 24.04 base but are not individually tested. LMDE is not qualified. See [Mint release notes](https://linuxmint.com/rel_wilma.php).

The browser’s **Unload model to free memory** control releases RAM/GPU resources while keeping the downloaded weights cached. **Load cached model** restores AI processing without downloading the weights again.
