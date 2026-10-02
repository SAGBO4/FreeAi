#!/usr/bin/env bash
# FreeAI Jarvis Daemon Installer
# Configures FreeAI as a persistent 24/7 background systemd service on Linux.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVICE_NAME="freeai-jarvis.service"
USER_SYSTEMD_DIR="$HOME/.config/systemd/user"

echo "⚡ [FreeAI Jarvis] Configuration du daemon d'écoute permanente..."

mkdir -p "$USER_SYSTEMD_DIR"

cat > "$USER_SYSTEMD_DIR/$SERVICE_NAME" <<EOF
[Unit]
Description=FreeAI Jarvis Sentinel - Continuous Telegram Neural Voice & Text Telepathy
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$PROJECT_ROOT
ExecStart=/usr/bin/python3 cli.py "/telegram loop"
Restart=always
RestartSec=3
Environment=PYTHONUNBUFFERED=1
Environment=PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

# Enable lingering so service runs even without open GUI session
loginctl enable-linger "$USER" 2>/dev/null || true

systemctl --user daemon-reload
systemctl --user enable "$SERVICE_NAME"
systemctl --user restart "$SERVICE_NAME"

echo "✔ [FreeAI Jarvis] Service activé et démarré avec succès !"
echo "• Statut : systemctl --user status $SERVICE_NAME"
echo "• Logs en direct : journalctl --user -u $SERVICE_NAME -f"
