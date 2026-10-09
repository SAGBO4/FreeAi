#!/usr/bin/env bash
# ==============================================================================
#  FreeAi Sovereign Mesh v3.0 (Jarvis Edition)
#  Triple-Tier Auto-Failover: Mistral ➔ Groq ➔ OpenRouter | Disk Cache Sémantique
# ==============================================================================

set -e

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
DIR="$(dirname "$SCRIPT_PATH")"
PROJECT_ROOT="$(cd "$DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"
CONFIG_FILE="$PROJECT_ROOT/config/litellm_sovereign.yaml"
CACHE_DIR="$PROJECT_ROOT/cache/litellm_cache"

export PATH="$HOME/.local/bin:$HOME/.nvm/versions/node/v22.22.2/bin:$PATH"

# Couleurs & Styles
C_RESET="\033[0m"
C_CYAN="\033[1;36m"
C_GREEN="\033[1;32m"
C_YELLOW="\033[1;33m"
C_MAGENTA="\033[1;35m"
C_RED="\033[1;31m"
C_BOLD="\033[1m"

clear 2>/dev/null || true

cat << "EOF"
  ███████╗██████╗ ███████╗███████╗ █████╗ ██╗
  ██╔════╝██╔══██╗██╔════╝██╔════╝██╔══██╗██║
  █████╗  ██████╔╝█████╗  █████╗  ███████║██║
  ██╔══╝  ██╔══██╗██╔══╝  ██╔══╝  ██╔══██║██║
  ██║     ██║  ██║███████╗███████╗██║  ██║██║
  SOVEREIGN MESH  —  KALI EDITION  —  TRIPLE-TIER 0€
EOF

echo -e "${C_CYAN}══════════════════════════════════════════════════════════════════════${C_RESET}"
echo -e "${C_BOLD} [FreeAi Sovereign Mesh] Initialisation de l'infrastructure IA...${C_RESET}"

# 1. Chargement des clés d'environnement
if [ -f "$ENV_FILE" ]; then
    export $(grep -E "^(MISTRAL_API_KEY|GROQ_API_KEY|OPENROUTER_API_KEY)=" "$ENV_FILE" | xargs)
    echo -e "${C_GREEN}  ✔ Fournisseurs connectés${C_RESET} : Mistral AI, Groq Cloud, OpenRouter"
else
    echo -e "${C_RED}  ✖ Fichier .env introuvable dans $PROJECT_ROOT${C_RESET}"
    exit 1
fi

mkdir -p "$CACHE_DIR"

# 2. Vérification et Démarrage du Proxy LiteLLM
if ! curl -s http://127.0.0.1:4000/v1/models >/dev/null 2>&1; then
    echo -e "${C_YELLOW}  ⚙ Démarrage du Proxy LiteLLM Sovereign Mesh (port 4000)...${C_RESET}"
    nohup litellm --config "$CONFIG_FILE" --port 4000 > /tmp/litellm_sovereign.log 2>&1 &
    disown
    
    # Attente active du proxy
    for i in {1..20}; do
        if curl -s http://127.0.0.1:4000/v1/models >/dev/null 2>&1; then
            break
        fi
        sleep 1
    done
fi

if curl -s http://127.0.0.1:4000/v1/models >/dev/null 2>&1; then
    echo -e "${C_GREEN}  ✔ Proxy LiteLLM en ligne sur http://127.0.0.1:4000${C_RESET}"
else
    echo -e "${C_RED}  ✖ Impossible d'initialiser LiteLLM. Consultez /tmp/litellm_sovereign.log${C_RESET}"
    exit 1
fi

echo -e "${C_CYAN}──────────────────────────────────────────────────────────────────────${C_RESET}"
echo -e "${C_BOLD} Architecture de Résilience (Triple-Tier Cascade) :${C_RESET}"
echo -e "  • ${C_GREEN}Tier 1 (Priorité)${C_RESET} : Mistral Nemo (Outils/Code 128k) & Groq 120B (Vitesse)"
echo -e "  • ${C_YELLOW}Tier 2 (Failover)${C_RESET} : Groq GPT-OSS 120B / 20B (Inférence ultra-rapide)"
echo -e "  • ${C_MAGENTA}Tier 3 (Secours)${C_RESET}  : OpenRouter Nemotron 120B Free & Gemma 31B Free"
echo -e "  • ${C_CYAN}Accélérateur${C_RESET}      : Cache Sémantique SQLite Local ($CACHE_DIR)"
echo -e "${C_CYAN}══════════════════════════════════════════════════════════════════════${C_RESET}"
echo -e "${C_GREEN}>> Lancement de Claude Code (Modèle actif : logic)...${C_RESET}\n"

# 3. Export des variables Anthropic pour Claude Code
export ANTHROPIC_BASE_URL="http://127.0.0.1:4000"
export ANTHROPIC_API_KEY="sk-local"
export ANTHROPIC_DEFAULT_OPUS_MODEL="logic"
export ANTHROPIC_DEFAULT_SONNET_MODEL="logic"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="fast"
export CLAUDE_CODE_DISABLE_AUTO_UPDATE=1
export DISABLE_AUTO_UPDATE=true
export CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT=1
export CLAUDE_CODE_MAX_CONTEXT_TOKENS=128000

# Si aucun modèle explicite n'est passé en argument, on applique --model logic par défaut
HAS_MODEL=false
for arg in "$@"; do
    if [[ "$arg" == "--model" ]] || [[ "$arg" == --model=* ]]; then
        HAS_MODEL=true
        break
    fi
done

if [ "$HAS_MODEL" = false ]; then
    exec claude --model logic "$@"
else
    exec claude "$@"
fi
