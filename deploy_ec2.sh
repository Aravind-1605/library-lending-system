#!/usr/bin/env bash
set -e

if [ -f /etc/debian_version ]; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -y
    apt-get install -y python3 python3-pip python3-venv git
elif [ -f /etc/redhat-release ] || [ -f /etc/system-release ]; then
    if command -v dnf >/dev/null 2>&1; then
        dnf update -y
        dnf install -y python3 python3-pip git
    else
        yum update -y
        yum install -y python3 python3-pip git
    fi
fi

APP_DIR="/opt/library-system"
mkdir -p "$APP_DIR"
cp -r . "$APP_DIR"

python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

cat <<'EOF' > /etc/systemd/system/library.service
[Unit]
Description=Library Book Lending System Flask Application
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/library-system
EnvironmentFile=-/opt/library-system/.env
ExecStart=/opt/library-system/venv/bin/gunicorn -b 0.0.0.0:80 app:app --workers 3 --timeout 120
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable library.service
systemctl restart library.service
systemctl status library.service --no-pager
