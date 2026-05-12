# Server Config ZIP

`tmp/release/varda-server-config-<version>.zip` is the server-side pack payload published by `varda-modpack`.

It preserves paths relative to `pack-configs/` and includes the server-relevant pack files:

- `config/`
- `kubejs/`
- `defaultconfigs/` when present
- `datapacks/` when present
- `README-SERVER.txt` when present

It does not include:

- `mods/`
- `profileImage/`
- client-only shader or UI assets
- any Go installer payloads or `.varda/*` runtime files

The separate `varda-server-installer` repo reads `docs/manifest.json` from GitHub Pages, downloads this ZIP from GitHub Releases, and handles server convergence from that remote manifest.
