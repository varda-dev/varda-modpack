# Server Files

This repo includes `server-files/` for text that gets bundled into the generated
server zip.

`README-SERVER.txt` is the user-facing file that ends up in the archive root.
Keep it brief and practical, since it is meant to be read after extraction.

`server.properties` is optional. If present, `scripts/prep-files.py --server`
will copy it into the package root alongside the generated NeoForge files.

The server build process itself:
- copies the selected pack files into a temp package directory
- installs the NeoForge server into that directory
- patches the generated launch scripts to start in `nogui`
- replaces `user_jvm_args.txt` with the Varda defaults
- removes installer artifacts before zipping the result

The generated archive should still include the standard pack content:
`libraries/`, `mods/`, `config/`, `kubejs/`, `minecraftinstance.json`,
`run.sh`, `run.bat`, `user_jvm_args.txt`, and `README-SERVER.txt`.
