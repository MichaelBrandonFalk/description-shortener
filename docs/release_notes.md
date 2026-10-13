Description Shortener V1.4 returns useful gist outputs with review flags, reduces model passes, and adds a Linux Mint installer preview.

- Supporting details may be dropped to fit. Valid model drafts are returned with “May need review” outside the copied text and exported description fields.
- At most two generation attempts, with no separate model reviewer. If the model fails, a clearly flagged source excerpt is returned when usable prose is available.
- Browser model context/batch sizes reduced; failed engines are released. Quick flagged excerpts can be produced without loading the AI model.
- The model stays in the same browser cache across application updates. Persistent storage is requested. Clearing browser data or browser eviction can still require a download.
- Default/minimum 110 characters, including spaces and punctuation; Settings can increase the limit.

[Public GitHub download page](https://michaelbrandonfalk.github.io/description-shortener/) · [Use in browser](https://michaelbrandonfalk.github.io/description-shortener/browser/).

Complete downloads: [Mac ZIP](https://description-shortener.great-americ-8514.chatgpt.site/download/Description-Shortener-V1.4-Apple-Silicon.zip), [Windows ZIP](https://description-shortener.great-americ-8514.chatgpt.site/download/Description-Shortener-V1.4-Windows-x64.zip), [Linux Mint / Ubuntu DEB](https://description-shortener.great-americ-8514.chatgpt.site/download/Description-Shortener-V1.4-Linux-x64.deb).

Apple Silicon/macOS 14+, Windows x64, Ubuntu 22.04 x64 and Linux Mint 22.x x64. Each native download includes the model and Python; no account, API key or separate model setup. Allow 16 GB RAM and about 25 GB installation space. Browser AI processing benefits from 24 GB RAM or more and WebGPU; source excerpts need no AI weights.

Mac is ad-hoc signed, not notarized. Windows is unsigned. Windows and Linux remain previews; GPU acceleration and consumer hardware are not qualified. Linux Mint qualification covers official Mint 22.3 Cinnamon userspace in a CI userspace container, including package installation and sandboxed app launch, not a booted Cinnamon session. Other Mint 22.x editions are not individually tested; LMDE is not qualified.

Outputs are best effort and should be reviewed. Excerpts can omit context or need grammatical editing. Original files and unrelated spreadsheet data are preserved. Complex tracked Word content and legacy conversion can need manual review.

The .bin assets are immutable distribution segments, not standalone installers. Use the complete download links above. Full SHA-256 values are supplied in each checksum/manifest asset. Older versions remain available.

The browser’s **Unload model to free memory** control releases RAM/GPU resources while keeping the downloaded weights cached. **Load cached model** restores AI processing without downloading the weights again.
