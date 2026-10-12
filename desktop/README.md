# Windows and Linux desktop previews

These builds reuse the native Python engine and pinned Gemma model. The Electron interface calls the frozen helper through a restricted IPC bridge; input text and files are not sent to an external service.

The initial targets are Windows x64 and Ubuntu Linux x64. Build jobs must pass the same 11 actual-model benchmark cases, selected-limit/cache/file checks, and packaged interface checks before downloads are published. CPU tests on hosted runners do not qualify GPU acceleration or all desktop environments.

- Windows: self-contained ZIP. Extract the whole folder and open DescriptionShortener.exe. Python and the model are bundled. This preview is unsigned and may receive a Windows trust warning.
- Ubuntu: self-contained DEB installer with the Chromium sandbox helper owned by root and its expected permissions. No sandbox-disabling launcher is used. Other distributions are not yet supported.
- Inputs: pasted text, XLSX, CSV, DOCX and TXT. Legacy document conversion and PDF import remain Mac-only in this preview.
- Settings: default/minimum 110 characters, including spaces and punctuation.
- CPU operation is the mandatory test target. The bundled Vulkan runtime is attempted automatically; startup failure falls back to CPU. GPU memory and drivers need separate hardware testing. The initial hosted CPU tests took 17–189 seconds per description, excluding startup.

Run `python scripts/build_desktop.py` on the matching OS after installing `requirements.txt` and running `npm ci` here. The build downloads checksum-pinned native runtimes and official model weights, builds the frozen helper, tests it, and prepares immutable split download segments. It does not duplicate the 7 GB model in the CI artifact; the public download service delivers each complete archive using the pinned official model segment.

The build workflow is `.github/workflows/desktop-preview.yml`. Each version needs successful native-platform tests and its matching GitHub release assets before the page gains working download buttons.

The final archive verification stage adds app-local Microsoft C++ runtime dependencies to the unpublished Windows candidate and rebuilds Ubuntu’s installer wrapper using dpkg-compatible GNU tar headers. It then verifies the exact archive and tests its extracted/installed app. These candidate segments must pass before becoming release assets. Runtime DLL source versions and hashes are bundled in the Windows notices folder.
