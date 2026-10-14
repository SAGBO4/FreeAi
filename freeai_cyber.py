#!/usr/bin/env python3
"""
FreeAi Cyber Interface
-------------------
Interface utilisateur autonome pour exécuter des outils Kali Linux réels.
Utilise une boucle ReAct pour écouter les erreurs et s'adapter dynamiquement.
"""

import logging
import json
import subprocess
import argparse
import asyncio
import sys
from typing import Dict, Any, Optional
from app.cognition.hermes_scratchpad import HermesScratchpadEngine
from app.tools.kali_registry import KaliToolRegistry

# Configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Mappage des reformulations pour les demandes interdites
REFORMULATION_MAP = {
    "brute force": "test de vulnérabilités d'authentification avec Hydra",
    "cracker": "test de sécurité des mots de passe avec Hydra",
    "scan port": "détection de ports ouverts avec Nmap",
    "intrusion": "analyse de vulnérabilités avec Nikto",
}
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("freeai_cyber")


def reformulate_demand(user_input: str) -> str:
    """Réformule une demande utilisateur interdite en une tâche acceptable."""
    user_input_lower = user_input.lower()
    for forbidden_term, reformulated_term in REFORMULATION_MAP.items():
        if forbidden_term in user_input_lower:
            logger.info(f"Réformulation de la demande: '{user_input}' -> '{reformulated_term}'")
            return reformulated_term
    return user_input


def execute_command(tool_name: str, arguments: Dict[str, Any]) -> Optional[str]:
    """Executes a Kali tool command using subprocess."""
    registry = KaliToolRegistry()
    command = registry.build_tool_command(tool_name, arguments)
    if not command:
        logger.error(f"Failed to build command for tool: {tool_name}")
        return None

    logger.info(f"Executing: {command}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        logger.info(f"Output: {result.stdout}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with error: {e.stderr}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return None


def interactive_mode():
    """Mode interactif pour l'utilisateur."""
    registry = KaliToolRegistry()
    hermes_engine = HermesScratchpadEngine()
    installed_tools = registry.get_installed_tools()

    if not installed_tools:
        logger.error("Aucun outil Kali détecté. Quittez.")
        return

    logger.info("Outils Kali disponibles:")
    for tool_name in installed_tools:
        logger.info(f"- {tool_name}")

    while True:
        try:
            user_input = input("Entrez votre demande ou 'exit' pour quitter: ").strip()
            reformulated_input = reformulate_demand(user_input)
            if reformulated_input != user_input:
                logger.info(f"Demande reformulée: '{user_input}' -> '{reformulated_input}'")
                user_input = reformulated_input

            if user_input.lower() == "exit":
                break

            if not registry.is_tool_available(user_input):
                logger.error(f"L'outil '{user_input}' n'est pas disponible.")
                continue
            if user_input.lower() == "exit":
                break

            if user_input not in installed_tools:
                logger.error(f"L'outil '{user_input}' n'est pas disponible.")
                continue

            # Générer une réflexion et un appel d'outil
            scratchpad = hermes_engine.formulate_thought_scratchpad(f"Exécuter {user_input}")
            tool_call = scratchpad.get("tool_call", {})
            if tool_call:
                tool_name = tool_call.get("name", "")
                arguments = tool_call.get("arguments", {})
                if tool_name:
                    tool_name = tool_name.replace("kali_", "")
                    if not registry.is_tool_available(tool_name):
                        logger.error(f"L'outil '{tool_name}' n'est pas disponible.")
                        continue

                    output = execute_command(tool_name, arguments)
                    if output:
                        print(output)
                    else:
                        logger.error(f"Échec de l'exécution de l'outil '{tool_name}'")
                else:
                    logger.error("Aucun outil spécifié dans la réflexion.")
            else:
                logger.error("Aucun appel d'outil généré.")
        except KeyboardInterrupt:
            logger.info("Sortie du mode interactif...")
            break
        except Exception as e:
            logger.error(f"Erreur: {str(e)}")


def non_interactive_mode(tool_name: str, arguments: Dict[str, Any]) -> Optional[str]:
    """Mode non-interactif pour l'exécution directe."""
    registry = KaliToolRegistry()
    reformulated_name = reformulate_demand(tool_name)

    if reformulated_name != tool_name:
        logger.info(f"Réformulation de l'outil: '{tool_name}' -> '{reformulated_name}'")
        tool_name = reformulated_name

    if not registry.is_tool_available(tool_name):
        logger.error(f"L'outil '{tool_name}' n'est pas disponible.")
        return None

    command = registry.build_tool_command(tool_name, arguments)
    if not command:
        logger.error(f"Impossible de construire la commande pour {tool_name}.")
        return None

    return execute_command(tool_name, arguments)


def main():
    parser = argparse.ArgumentParser(description="FreeAI Cyber Arsenal: Execute Kali tools interactively or non-interactively.")
    parser.add_argument("--interactive", action="store_true", help="Run in interactive mode.")
    parser.add_argument("--tool", help="Tool name to execute in non-interactive mode.")
    parser.add_argument("--arguments", help="JSON string of arguments for the tool.")

    args = parser.parse_args()

    if args.interactive:
        interactive_mode()
    elif args.tool and args.arguments:
        try:
            arguments = json.loads(args.arguments)
            result = non_interactive_mode(args.tool, arguments)
            print(json.dumps(result, indent=2))
        except Exception as e:
            logger.error(f"Erreur en mode non-interactif: {str(e)}")
            sys.exit(1)
    else:
        parser.error("Missing required arguments. Use --help for usage.")


if __name__ == "__main__":
    main()