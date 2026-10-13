# Description Shortener release rules

This directory is its own app repository. Never publish unrelated parent-workspace files.

- Every user-visible delivered edit increments VERSION (1.0, 1.1, 1.2, ...).
- Update CHANGELOG.md, build a new versioned Mac app and ZIP, and create a matching GitHub release. Retain older downloads; never overwrite an existing release artifact.
- Run unit tests and actual-model smoke tests before packaging. Verify the packaged helper and native UI.
- Keep the download page and its version history current, with links to bundled open-source components.
- Never commit user inputs, credentials, model weights, virtual environments, or build output.
- Do not claim guaranteed semantic preservation or Apple notarization without evidence.

- Preserve the browser origin and model cache path across app updates. Model cache identity must not depend on the application version. Do not clear cached weights when updating app code.
- Shortening captures the gist and may drop supporting details. Return a useful draft or source excerpt with a review flag instead of blocking solely because some details were omitted. Keep flags outside copied text and exported description fields.
- Linux Mint support needs installer and actual-model checks in Mint userspace. Distinguish userspace-container tests from a booted desktop or GPU hardware test.
