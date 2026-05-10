Varda Server

Extract this zip into a fresh folder.

Then run `install-mods.sh` on Linux/macOS or `install-mods.cmd` on Windows. The installer downloads the required server mod jars into `mods/` and can update previously installed Varda mods using `mods/.varda-mods-installed.txt`.

User-added untracked files in `mods/` are left alone. No CurseForge API token is required on the server itself, but the installer needs internet access.

If a download fails, rerun the installer.

After the mods are installed, start the server with `run.sh` or `run.bat`.

The first launch will create `eula.txt` and stop if you have not accepted the Minecraft EULA yet.
If needed, open `user_jvm_args.txt` to adjust memory settings.
