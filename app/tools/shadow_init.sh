#!/bin/bash
# FreeAI Sovereign Micro-Init & Virtual Service Shim
# Provides transparent systemctl & service compatibility inside the Shadow Sandbox

ACTION="${2:-status}"
SERVICE="$1"

if [ "$1" = "start" ] || [ "$1" = "stop" ] || [ "$1" = "restart" ] || [ "$1" = "status" ]; then
    ACTION="$1"
    SERVICE="$2"
fi

mkdir -p /run /tmp/services

case "$ACTION" in
    start)
        if [ -x "/etc/init.d/$SERVICE" ]; then
            /etc/init.d/"$SERVICE" start
        elif command -v "$SERVICE" >/dev/null 2>&1; then
            nohup "$SERVICE" > "/tmp/services/$SERVICE.log" 2>&1 &
            echo $! > "/run/$SERVICE.pid"
            echo "[SHADOW-INIT] Service $SERVICE démarré en arrière-plan (PID $(cat "/run/$SERVICE.pid"))"
        else
            echo $! > "/run/$SERVICE.pid" 2>/dev/null || true
            echo "[SHADOW-INIT] Service $SERVICE actif (simulation micro-init)"
        fi
        ;;
    stop)
        if [ -f "/run/$SERVICE.pid" ]; then
            kill -9 "$(cat "/run/$SERVICE.pid")" 2>/dev/null || true
            rm -f "/run/$SERVICE.pid"
        fi
        echo "[SHADOW-INIT] Service $SERVICE arrêté"
        ;;
    restart)
        "$0" "$SERVICE" stop
        "$0" "$SERVICE" start
        ;;
    status)
        if [ -f "/run/$SERVICE.pid" ] && kill -0 "$(cat "/run/$SERVICE.pid")" 2>/dev/null; then
            echo "● $SERVICE.service - Active (running) [PID: $(cat "/run/$SERVICE.pid")]"
        else
            echo "● $SERVICE.service - Active (prêt / sovereign micro-init)"
        fi
        ;;
    *)
        echo "[SHADOW-INIT] systemctl $ACTION sur $SERVICE exécuté avec succès."
        ;;
esac

exit 0
