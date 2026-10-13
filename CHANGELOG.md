# Changelog

## Download website update

- Remove the browser option and browser-specific guidance from the download page. Direct browser links redirect to desktop downloads. V1.4 installers are unchanged.

## V1.4

- Shorten to the gist, allowing supporting details to be dropped. Valid drafts are returned with a “May need review” flag instead of being withheld by a second model review.
- At most two generation attempts. Model failures return a flagged source excerpt when usable prose is available.
- Added a browser model-unload control that releases memory without deleting cached weights.
- Browser model context and batch sizes reduced; failed engines are released. Quick source excerpts are available without loading the model.
- Reuse the existing browser model cache across app releases and request persistent storage. Clearing data or browser eviction can still remove it.
- Linux Mint 22.3 userspace installer verification added, including sandboxed UI, actual-model inference and file preservation.

## V1.3

- Add Windows x64 and Ubuntu Linux x64 desktop preview builds with the same pinned local model and Python shortening engine.
- Bundle an Electron interface, CPU runtime and optional Vulkan runtime; fall back to CPU when GPU startup fails.
- Add Windows process cleanup, UTF-8 helper communication and app-local C++ runtime dependencies.
- Export safely to filesystems without hard-link support.
- Build and test packaged helpers on Windows and Ubuntu CI runners, then reconstruct and verify the final ZIP/DEB and exercise extracted/installed apps.
- Use dpkg-compatible GNU tar headers and root-owned Chromium sandbox permissions in the Ubuntu installer. GPU support remains unverified.

## V1.2

- Add fully local browser shortening on GitHub Pages while retaining the downloadable Mac app.
- Add saved Settings for a maximum character count, default and minimum 110, including spaces and punctuation.
- Apply the selected limit to drafting, revision feedback, validation and file export; isolate cached results by limit.
- Load the same Gemma 4 12B model in the browser with WebGPU and a verified local model cache.
- Process pasted text, XLSX, CSV, DOCX and TXT locally in the browser.

## Website hosting correction

- Publish the public download page on GitHub Pages, matching the other app download pages.
- Update the repository homepage and download-page links. V1.1 app and ZIP remain unchanged.

## V1.1

- Bundle the official Gemma 4 12B QAT model; no account or separate model setup.
- Use word-guided drafting, exact character feedback, conservative compaction and material-fact review.
- Allow incidental narrative enjoyment to be omitted while retaining material facts and the original action or intention.

- Remove the tagline and extra rule badges; make text/file controls readable in all system appearances.
- Simplify the download page and retain open-source credits and version history.
- Apply length, grammar, fact and planned-action rules during model generation.
- Remove the generation cutoff that could truncate sentences; revise invalid drafts internally with specific feedback.
- Keep the local model loaded while the app is open and reuse checked descriptions within the session.
- Show an explanatory review message instead of exposing draft punctuation errors.

## V1.0

- Initial native Apple Silicon Mac app with a bundled offline model.
- Paste text or process XLSX, CSV and documents.
- Enforce 110 characters, no em dashes, complete-sentence checks and fact-retention review.
- Preserve originals and block export when a description cannot pass validation.
- Bundle open-source credits and publish versioned downloads.
