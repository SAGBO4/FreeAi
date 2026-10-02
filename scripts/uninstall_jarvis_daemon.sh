#!/usr/bin/env bash
# FreeAI Jarvis Daemon Uninstaller

set -euo pipefail

SERVICE_NAME="freeai-jarvis.service"
USER_SYSTEMD_DIR="$HOME/.config/systemd/user"

echo "🛑 [FreeAI Jarvis] Arrêt et désinstallation du service d'arrière-plan..."

systemctl --user stop "$SERVICE_NAME" 2>/dev/null || true
systemctl --user disable "$SERVICE_NAME" 2>/dev/null || true
rm -f "$USER_SYSTEMD_DIR/$SERVICE_NAME"
systemctl --user daemon-reload

echo "✔ [FreeAI Jarvis] Service désinstallé."
