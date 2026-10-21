#!/bin/bash

# FreeAi Cyber Shell Interface
# --------------------------
# Script shell pour faciliter l'appel de freeai_cyber.py en mode interactif ou non-interactif.

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_SCRIPT="$SCRIPT_DIR/freeai_cyber.py"

# Fonction pour afficher l'aide
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --interactive    Exécuter en mode interactif."
    echo "  --tool <nom>     Nom de l'outil Kali à exécuter."
    echo "  --arguments <json> Arguments JSON pour l'outil."
    echo "  --help           Afficher cette aide."
    exit 1
}

# Vérification de la disponibilité de Python3
if ! command -v python3 &> /dev/null; then
    echo "Erreur : Python3 n'est pas installé ou n'est pas accessible." >&2
    exit 1
fi

# Vérification de la disponibilité du script principal
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Erreur : Le script $PYTHON_SCRIPT n'existe pas." >&2
    exit 1
fi

# Traitement des arguments
INTERACTIVE=false
TOOL_NAME=""
ARGUMENTS=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --interactive)
            INTERACTIVE=true
            shift
            ;;
        --tool)
            TOOL_NAME="$2"
            shift 2
            ;;
        --arguments)
            ARGUMENTS="$2"
            shift 2
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            echo "Erreur : Argument inconnu $1"
            usage
            exit 1
            ;;
    esac
done

# Lancer en mode interactif par défaut si aucun argument n'est fourni
if [ "$INTERACTIVE" = false ] && [ -z "$TOOL_NAME" ] && [ -z "$ARGUMENTS" ]; then
    INTERACTIVE=true
fi

# Exécuter freeai_cyber.py
if $INTERACTIVE; then
    python3 "$PYTHON_SCRIPT" --interactive
else
    if [ -z "$TOOL_NAME" ] || [ -z "$ARGUMENTS" ]; then
        echo "Erreur : Les arguments --tool et --arguments sont requis pour le mode non-interactif."
        usage
        exit 1
    fi
    python3 "$PYTHON_SCRIPT" --tool "$TOOL_NAME" --arguments "$ARGUMENTS"
fi