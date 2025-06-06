#!/bin/bash
set -euo pipefail

VARDA_USR=minecraft
VARDA_DIR=/srv/minecraft/varda
VARDA_SRV=/etc/systemd/system/varda.service
VARDA_CRON="0 3 * * * /usr/bin/systemctl restart varda.service"


if sudo systemctl is-active --quiet varda; then
    echo "Varda service running. Stop it to continue..."
    exit 1
fi
if sudo systemctl is-enabled --quiet varda; then
    echo "Varda service enabled. Disable it to continue..."
    exit 1
fi

sudo apt update; sudo apt upgrade -y
if ! [ -x "$(command -v tmux)" ]; then
    sudo apt install tmux
fi
if ! [ -x "$(command -v java)" ]; then
    sudo apt install openjdk-17-jre-headless  
fi
JAVA_VER="$(java -version 2>&1 >/dev/null | awk -F '"' '/version/ {print $2}' | awk -F '.' '{sub("^$", "0", $2); print $1$2}')"
if ! [ "$JAVA_VER" -ge 170 ]; then
    echo "Install Java version 17 to continue..."
    exit 1
fi

if [ ! -d "$VARDA_DIR" ]; then
    sudo mkdir -p /srv/minecraft/varda
fi
if [ ! id "$VARDA_USR" >/dev/null 2>&1 ]; then
    sudo useradd -r -m -U -d /srv/minecraft -s /bin/bash minecraft
fi
sudo chown -R minecraft:minecraft /srv/minecraft
if [ ! -f "$VARDA_SRV" ]; then
    sudo rm "$VARDA_SRV"
fi
sudo touch /etc/systemd/system/varda.service
sudo tee /etc/systemd/system/varda.service &>/dev/null <<EOF
[Unit]
Description=Varda Service
After=local-fs.target network.target

[Service]
Type=forking
Restart=on-failure
Nice=1
KillMode=none
SuccessExitStatus=0 1
ProtectHome=true
ProtectSystem=full
PrivateDevices=true
NoNewPrivileges=true
User=minecraft
Group=minecraft
WorkingDirectory=/srv/minecraft/varda
ExecStart=/usr/bin/tmux -L minecraft new-session -s varda -d '/usr/bin/bash /srv/minecraft/varda/start.sh'
ExecStop=/usr/bin/tmux -L minecraft send-keys -t varda 'say SERVER SHUTTING DOWN IN 10 SECONDS!' ENTER
ExecStop=/usr/bin/sleep 10
ExecStop=/usr/bin/tmux -L minecraft send-keys -t varda 'stop' ENTER

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload

# Add a restart cron
sudo crontab -l > rootcrons
echo "$VARDA_CRON" >> rootcrons
sudo crontab rootcrons
sudo rm rootcrons