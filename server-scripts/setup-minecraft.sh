#!/bin/bash
set -euo pipefail

VARDA_RAM=10
VARDA_USR=minecraft
VARDA_ZIP=~/varda-server.zip
VARDA_DIR=/srv/minecraft/varda
FORGE_VER="1.20.1-47.3.10"

# Checks
if [ ! -f "$VARDA_ZIP" ]; then
    echo "varda-server.zip not found..."
    exit 1
fi
if [ ! id "$VARDA_USR" >/dev/null 2>&1 ]; then
    echo "minecraft user not found. Have you run setup-server.sh?"
    exit 1
fi

# Main setup
if [ ! -d "$VARDA_DIR" ]; then
    sudo mkdir -p /srv/minecraft/varda
    sudo unzip "$VARDA_ZIP" -d "$VARDA_DIR"
    # Need to do this dynamically after forge has been installed so i can set the right version without having to specify it up above
    echo "#!/usr/bin/env sh" | sudo tee "$VARDA_DIR"/start.sh
    echo "/usr/bin/java -server -XX:+UseG1GC -XX:+UnlockExperimentalVMOptions @user_jvm_args.txt @libraries/net/minecraftforge/forge/${FORGE_VER}/unix_args.txt nogui" | sudo tee -a "$VARDA_DIR"/start.sh
    echo "eula=true" | sudo tee -a "$VARDA_DIR"/eula.txt
    sudo chown -R minecraft:minecraft /srv/minecraft/varda
    sudo -u minecraft -H sh -c "chmod u+x $VARDA_DIR/start.sh"
    (cd "$VARDA_DIR" && sudo -u minecraft -H sh -c "java -jar forge-*-installer.jar --installServer")
fi

# Forge check
if [ ! -f "$VARDA_DIR"/forge-*-installer.jar.log ]; then
    echo "Forge not installed..."
    exit 1
fi

# Cleanup
if [ -f "$VARDA_DIR"/run.bat ]; then
    sudo rm "$VARDA_DIR"/run.bat
fi
if [ -f "$VARDA_DIR"/run.sh ]; then
    sudo rm "$VARDA_DIR"/run.sh
fi
if [ -f "$VARDA_DIR"/forge-*-installer.jar ]; then
    sudo rm "$VARDA_DIR"/forge-*-installer.jar
fi