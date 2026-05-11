# Server Payload

`cmd/varda-server-installer/payload/` holds text bundled into generated server installer binaries.

`README-SERVER.txt` is the user-facing file that lands in server root. Keep it short and practical.

The server build process:
- copies selected pack files into `cmd/varda-server-installer/payload/`
- embeds that payload into Go installer binary
- installs NeoForge into target server directory
- patches or creates `run.sh` and `run.bat`
- replaces `user_jvm_args.txt` with Varda defaults
- writes runtime metadata to `.varda/`
- removes installer artifacts after successful NeoForge install
- downloads server mod jars from `.varda/mods-list.txt`
- removes unmanaged files and directories from `mods/`
- supports `--download-workers 6` to speed mod downloads

Generated payload should still include standard pack content:
`config/`, `kubejs/`, `README-SERVER.txt`, plus embedded metadata that lands in `.varda/mods-list.txt`, `.varda/neoforge-url.txt`, and `.varda/installer-version.txt`.
