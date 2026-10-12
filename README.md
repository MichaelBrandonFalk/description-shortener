# Description Shortener

A self-contained, fully local Mac app that shortens descriptions to a chosen maximum character count, including spaces and punctuation. The default and minimum are 110. No account, API key, Python installation, or model download is needed after installing the app.

[Download page](https://michaelbrandonfalk.github.io/description-shortener/) · [Versioned releases](https://github.com/MichaelBrandonFalk/description-shortener/releases) · [Open-source research](docs/research.md)

## Use

1. Unzip the download and drag **Description Shortener V1.2.app** to Applications.
2. Open the app. Paste one description per line, or choose/drop a file.
3. Click **Shorten description** or **Shorten & save copy**.
4. Copy the text or use the saved file. Review details lists changed descriptions and any blocked locations.

V1.2 is ad-hoc signed, not Apple notarized. On first launch, macOS may require approving the app in System Settings → Privacy & Security → Open Anyway. This does not require disabling Gatekeeper. Developer ID signing is required for a future notarized release.

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

Every returned description is checked against the chosen character limit, em dashes, terminal punctuation, and numeric changes. The rules and a soft word budget are supplied to the local model before drafting. A conservative whole-phrase/unit pass may compact an overlong draft without slicing text. Invalid drafts receive specific revision feedback; a separate local-model pass checks complete sentences, equivalent meaning and close wording. The model stays loaded while the app is open, and checked descriptions are cached in memory for faster repeat runs. It does not intentionally add claims or marketing language. These semantic checks are probabilistic, so review changed wording before use.

Incidental narrative enjoyment may be omitted while the main meaning and material facts remain. Product attributes, names, specifications and quantities are protected.

Some inputs cannot retain all material facts within the selected character limit. If any selected description fails after retries, file export is blocked and the app lists its location. Resolve those source descriptions and run again. The app does not truncate, silently discard facts, or put error messages into description cells.

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

[Open the browser app](https://michaelbrandonfalk.github.io/description-shortener/browser/). It uses the same pinned Gemma 4 12B model on your own GPU through wllama. The first use downloads about 7 GB from the official model URL; SHA-256 is checked before loading. The model is stored in this browser’s private file storage. Clearing browser data removes it. Use a WebGPU-capable browser and 16 GB RAM or more. Loading and processing depend on the browser and device; the native Mac app is faster on the tested Mac.

Paste text or select XLSX, CSV, DOCX or UTF-8 TXT files. No text or document is uploaded for inference. The browser saves a new file and retains sheet names, formulas, non-description values and untouched Office package content. Complex Word fields or tracked changes need review; legacy document formats and PDF use the Mac app. Browser CSV quoting may normalize, while delimiter, BOM, line endings, order and other field values are retained.

Run `node --test tests/browser.test.mjs` for browser counting, limit, cache and CSV checks. `scripts/export_browser_rules.py` keeps the model instructions and JSON schemas synchronized with the Python engine. `scripts/prepare_browser_model.py` verifies GGUF shard metadata against the pinned original weights.
