Varda Server

Run platform installer binary in fresh folder for new server, or run it in existing Varda server folder to update it.

Java 21 or newer required.

Windows AMD64:

  .\varda-server-installer-<version>-<release>-windows-amd64.exe

Linux AMD64:

  chmod +x ./varda-server-installer-<version>-<release>-linux-amd64
  ./varda-server-installer-<version>-<release>-linux-amd64

Linux ARM64:

  chmod +x ./varda-server-installer-<version>-<release>-linux-arm64
  ./varda-server-installer-<version>-<release>-linux-arm64

macOS:

  chmod +x ./varda-server-installer-<version>-<release>-macos-amd64
  ./varda-server-installer-<version>-<release>-macos-amd64

  chmod +x ./varda-server-installer-<version>-<release>-macos-arm64
  ./varda-server-installer-<version>-<release>-macos-arm64

Installer embeds pack metadata. At runtime it writes support files only to `.varda/`, installs or updates NeoForge, downloads server mod jars from `.varda/mods-list.txt`, and writes pack configs into place. No CurseForge API token required on server itself, but internet access required.

By default, old mod jar versions and extra files not listed in `.varda/mods-list.txt` are removed. `mods/` is managed by the installer and should contain only server mod `.jar` files. Files or directories manually placed in `mods/` will be removed during updates.

Flags:

  --force
  --skip-mods
  --skip-neoforge
  --download-workers 6
  --dir <path>

Recommended memory defaults are written to `user_jvm_args.txt`:

  -Xms4G
  -Xmx6G

Adjust those values for server before launch if needed.

First launch creates `eula.txt` and stops if Minecraft EULA not accepted yet.

macOS Gatekeeper may block unsigned binaries. If that happens, clear quarantine attribute or approve binary once before running it again.
