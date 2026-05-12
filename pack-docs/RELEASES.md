# Release Publishing

Varda now splits release publishing into two paths:

- CurseForge receives the client zip only.
- GitHub Releases receives `varda-server-config-<version>.zip`.
- GitHub Pages serves `docs/manifest.json` at `https://varda-dev.github.io/varda-modpack/manifest.json`.

## Local Flow

Build the release artifacts first:

```bash
python scripts/prep-files.py -v 0.1.0 -f
```

Upload the CurseForge client zip:

```bash
python scripts/cf-upload.py -v 0.1.0 -r beta -c "Changelog text"
```

Upload the GitHub release asset:

```bash
python scripts/gh-upload.py -v 0.1.0 -c "Changelog text" --replace-assets
```

## Environment

Create a `.env` file in the repo root with:

```env
CURSEFORGE_INSTANCE_DIR="..."
CURSEFORGE_API_TOKEN="..."
GITHUB_RELEASES_PAT="..."
```

`scripts/gh-upload.py` hardcodes the repository to `varda-dev/varda-modpack`.
`docs/manifest.json` is published from GitHub Pages branch `main` / folder `/docs`.

## Token Access

For GitHub Releases, use a token with access limited to `varda-dev/varda-modpack`.

- Repository access: only `varda-dev/varda-modpack`
- Repository permissions:
  - Contents: read/write
  - Metadata: read-only

The local Python release uploader does not need Actions or Attestations permissions.

If you run the GitHub Actions release workflow with `GITHUB_TOKEN`, set the workflow or job `permissions` to `contents: write`.

## Artifact Split

- CurseForge:
  - `varda-client-{version}-{release}.zip`
- GitHub Releases:
  - `varda-server-config-{version}.zip`
- GitHub Pages:
  - `docs/manifest.json`
