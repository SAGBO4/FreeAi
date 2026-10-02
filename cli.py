#!/usr/bin/env python3
"""FreeAI Interactive CLI & Command Center (TDR §13, §17, §31, §32).
Provides an interactive terminal interface with slash commands,
dynamic prompts reflecting permissions (freeAi vs lesaintAi),
resource monitoring, PC-wide solution search, Git rollback,
and Neon Cloud GZIP memory synchronization.
"""

import os
import sys
import shlex
import asyncio
import logging
import readline
from pathlib import Path
from typing import Optional, List, Dict, Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings
from app.resource_manager.watchdog import ResourceManager
from app.tools.gateway import ToolGateway
from app.orchestrator.orchestrator import TechLeadOrchestrator

# Configure logging: quiet console in CLI mode to avoid polluting the prompt
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("freeai_cli")

console = Console()

SLASH_COMMANDS = [
    "/mode",
    "/mode freeAi",
    "/mode lesaintAi",
    "/search",
    "/code",
    "/status",
    "/rollback",
    "/sync",
    "/help",
    "/clear",
    "/exit",
    "/quit"
]


def setup_readline():
    """Sets up auto-completion and tab navigation for slash commands."""
    def completer(text: str, state: int):
        options = [cmd for cmd in SLASH_COMMANDS if cmd.startswith(text)]
        if state < len(options):
            return options[state]
        return None

    readline.set_completer(completer)
    readline.set_completer_delims(" \t\n`~!@#$%^&*()=+[{]}\\|;:'\",<>?")
    readline.parse_and_bind("tab: complete")


def display_welcome_banner(mode: str):
    """Displays the welcome banner with sovereign FreeAI status."""
    banner_text = Text()
    banner_text.append("╔══════════════════════════════════════════════════════════════════════╗\n", style="bold cyan")
    banner_text.append("║                   ⚡ FreeAI Sovereign Assistant ⚡                   ║\n", style="bold yellow")
    banner_text.append("║       Intelligence Locale & Hybride - Mode NÉANT (0 résidu disque)   ║\n", style="bold green")
    banner_text.append("╚══════════════════════════════════════════════════════════════════════╝", style="bold cyan")

    console.print(Panel(
        banner_text,
        subtitle="Tapez [bold green]/help[/] pour afficher les commandes disponibles ou posez une question",
        border_style="cyan"
    ))


def get_prompt(mode: str) -> str:
    """Returns the dynamic prompt string based on the active mode."""
    if mode == "lesaintAi":
        return "[FreeAI:lesaintAi ⚡] > "
    return "[FreeAI:freeAi] > "


def print_help():
    """Displays the help table with all slash commands and usage examples."""
    table = Table(title="📖 Commandes Explicites FreeAI (Slash Commands)", border_style="cyan")
    table.add_column("Commande", style="bold yellow", width=26)
    table.add_column("Description", style="white")
    table.add_column("Exemple d'utilisation", style="green")

    table.add_row(
        "/mode freeAi",
        "Mode Standard sécurisé : écriture confinée au workspace, lecture globale autorisée, sudo désactivé.",
        "/mode freeAi"
    )
    table.add_row(
        "/mode lesaintAi",
        "Mode Super-Utilisateur : déverrouillage total (ALLOW_SUDO=True), écriture et exécution sur tout le PC.",
        "/mode lesaintAi"
    )
    table.add_row(
        "/search <motif> [dossier]",
        "Recherche de fichiers sur le PC pour trouver un fichier, script ou solution.",
        "/search *.py /home/lesaint"
    )
    table.add_row(
        "/code <texte> [motif]",
        "Recherche de code dans les fichiers de l'ordinateur pour trouver une implémentation.",
        "/code def handle_objective *.py"
    )
    table.add_row(
        "/status",
        "Affiche l'état en direct de la RAM, du CPU, du mode actif et de la base Neon Cloud.",
        "/status"
    )
    table.add_row(
        "/rollback",
        "Annulation Git instantanée des modifications non validées (reset --hard).",
        "/rollback"
    )
    table.add_row(
        "/sync",
        "Synchronise et compresse en GZIP la mémoire essentielle sur Neon PostgreSQL.",
        "/sync"
    )
    table.add_row(
        "/clear",
        "Nettoie l'affichage du terminal.",
        "/clear"
    )
    table.add_row(
        "/help",
        "Affiche ce panneau d'aide détaillé.",
        "/help"
    )
    table.add_row(
        "/exit ou /quit",
        "Ferme proprement la session FreeAI.",
        "/exit"
    )
    table.add_row(
        "<texte libre>",
        "Transmet directement l'objectif au Tech Lead Orchestrator pour exécution autonome.",
        "Analyse les failles de sécurité de mon script"
    )

    console.print(table)


def print_status(tech_lead: TechLeadOrchestrator):
    """Displays the system, mode, and Neon status."""
    status = tech_lead.get_status()
    res = status.get("resources", {})
    neon = status.get("neon", {})
    mode = status.get("mode", "freeAi")

    is_super = mode == "lesaintAi"
    mode_display = "[bold red]lesaintAi ⚡ (SUPER-UTILISATEUR)[/]" if is_super else "[bold green]freeAi (Standard Sécurisé)[/]"
    sudo_display = "[bold red]Activé (ALLOW_SUDO=True)[/]" if status.get("allow_sudo") else "[dim]Désactivé (Sudo Bloqué)[/]"
    fs_display = "[bold red]Accès Total (Tout le PC)[/]" if status.get("allow_full_fs_access") else "[green]Confiné au Workspace[/]"

    table = Table(title="📊 État Global du Système FreeAI", border_style="cyan", show_header=True)
    table.add_column("Composant", style="bold yellow")
    table.add_column("Valeur / État", style="white")

    table.add_row("Mode Actif", mode_display)
    table.add_row("Privilèges Sudo", sudo_display)
    table.add_row("Périmètre Écriture", fs_display)
    table.add_row("Lecture Globale PC", "[bold green]Autorisée[/]" if status.get("allow_global_read") else "[yellow]Restreinte[/]")
    table.add_row("Workspace", status.get("workspace", ""))
    table.add_row("RAM Processus IA", f"{res.get('ai_process_rss_mb', 0)} MB / Budget: {res.get('target_limit_mb')} MB (Max: {res.get('hard_limit_mb')} MB)")
    table.add_row("RAM Système", f"Utilisée: {res.get('system_ram_used_mb')} MB | Dispo: {res.get('system_ram_available_mb')} MB | Total: {res.get('system_ram_total_mb')} MB")
    table.add_row("CPU Système", f"{res.get('cpu_percent', 0)} %")
    table.add_row("Mode Mémoire Local", "[bold cyan]NÉANT (0 octet écrit sur disque)[/]")
    
    # Neon DB
    if neon.get("enabled"):
        if neon.get("connected"):
            neon_txt = f"[bold green]Connecté[/] - {neon.get('database')} | Connaissances: {neon.get('knowledge_records', 0)} | Audits: {neon.get('audit_records', 0)}"
        else:
            neon_txt = f"[bold red]Erreur de connexion[/] ({neon.get('error')})"
    else:
        neon_txt = "[yellow]Désactivé (Mémoire RAM éphémère)[/]"
    table.add_row("Neon PostgreSQL Cloud", neon_txt)
    table.add_row("Compression Mémoire", neon.get("compression", "GZIP"))

    console.print(table)


def run_search_files(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Executes a file search across the computer or specified directory."""
    if not args:
        console.print("[bold red]Usage :[/] /search <motif> [dossier_de_recherche]")
        console.print("[dim]Exemple : /search *.py ou /search requirements.txt /home/lesaint[/]")
        return

    pattern = args[0]
    search_dir = args[1] if len(args) > 1 else None

    console.print(f"[dim]🔍 Recherche des fichiers correspondant à '[bold cyan]{pattern}[/]' dans {search_dir or 'le workspace/PC'}...[/]")
    res = tech_lead.search_files(pattern=pattern, search_dir=search_dir)

    if not res.get("success"):
        console.print(f"[bold red]Erreur :[/] {res.get('error')}")
        return

    matches = res.get("matches", [])
    count = res.get("count", 0)

    if count == 0:
        console.print(f"[yellow]Aucun fichier trouvé correspondant à '{pattern}'.[/]")
        return

    table = Table(title=f"📁 Résultats de recherche ({count} trouvés)", border_style="cyan")
    table.add_column("#", style="dim", width=4)
    table.add_column("Chemin du fichier", style="white")

    for i, path in enumerate(matches, 1):
        table.add_row(str(i), path)

    console.print(table)


def run_search_code(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Executes a code search across files on the computer."""
    if not args:
        console.print("[bold red]Usage :[/] /code <texte_ou_fonction> [motif_fichier] [dossier]")
        console.print("[dim]Exemple : /code def handle_objective ou /code import psycopg2 *.py /home/lesaint/Rendue[/]")
        return

    query = args[0]
    file_pattern = args[1] if len(args) > 1 else "*"
    search_dir = args[2] if len(args) > 2 else None

    console.print(f"[dim]🔎 Recherche de code contenant '[bold cyan]{query}[/]' (fichiers: {file_pattern})...[/]")
    res = tech_lead.search_code(query=query, search_dir=search_dir, file_pattern=file_pattern)

    if not res.get("success"):
        console.print(f"[bold red]Erreur :[/] {res.get('error')}")
        return

    matches = res.get("matches", [])
    count = res.get("count", 0)

    if count == 0:
        console.print(f"[yellow]Aucune occurrence de code trouvée pour '{query}'.[/]")
        return

    table = Table(title=f"💻 Occurrences de code trouvées ({count})", border_style="cyan")
    table.add_column("Fichier", style="bold yellow")
    table.add_column("Ligne", style="dim", width=6)
    table.add_column("Extrait", style="white")

    for m in matches:
        table.add_row(m.get("file", ""), str(m.get("line", "")), m.get("content", ""))

    console.print(table)


def run_rollback(tech_lead: TechLeadOrchestrator):
    """Executes instant Git rollback."""
    console.print("[bold yellow]⏪ Exécution de l'annulation Git instantanée (git reset --hard HEAD)...[/]")
    res = tech_lead.rollback()
    if res.get("success"):
        console.print("[bold green]✔ Annulation Git effectuée avec succès ! Les modifications non validées ont été nettoyées.[/]")
        if res.get("stdout"):
            console.print(f"[dim]{res['stdout'].strip()}[/]")
    else:
        console.print(f"[bold red]❌ Échec du rollback :[/] {res.get('error') or res.get('stderr')}")


def run_sync(tech_lead: TechLeadOrchestrator):
    """Executes Neon memory synchronization with GZIP compression."""
    console.print("[dim]☁ Synchronisation et compression GZIP de la mémoire essentielle sur Neon PostgreSQL...[/]")
    res = tech_lead.sync_neon()
    if res.get("success"):
        orig = res.get("original_bytes", 0)
        zip_size = res.get("compressed_bytes", 0)
        ratio = res.get("ratio_saved", "N/A")
        console.print(Panel(
            f"[bold green]✔ Synchronisation réussie ![/]\n\n"
            f"• [white]Données brutes :[/] {orig} octets\n"
            f"• [white]Taille compressée (GZIP) :[/] [bold cyan]{zip_size} octets[/]\n"
            f"• [white]Gain d'espace :[/] [bold green]{ratio}[/]\n"
            f"• [dim]{res.get('message')}[/]",
            title="☁ Synchronisation Neon Cloud",
            border_style="green"
        ))
    else:
        console.print(f"[bold red]❌ Échec de la synchronisation :[/] {res.get('error') or res.get('message')}")


async def execute_tech_lead_task(tech_lead: TechLeadOrchestrator, objective: str):
    """Submits a free-form objective to the Tech Lead Orchestrator for autonomous execution."""
    with console.status(f"[bold cyan]FreeAI ({tech_lead.mode}) en cours d'analyse et d'exécution...[/]", spinner="dots"):
        result = await tech_lead.handle_objective(objective, autonomous=True)

    if not result.get("success"):
        console.print(f"[bold red]❌ Erreur d'exécution :[/] {result.get('error')}")
        return

    agent = result.get("assigned_agent", "Tech Lead")
    plan = result.get("plan", [])
    agent_res = result.get("result", {})
    external = result.get("external_resourcing_used", False)
    neon_sync = result.get("neon_cloud_sync", False)

    content = Text()
    content.append(f"🎯 Objectif : {objective}\n", style="bold white")
    content.append(f"🤖 Agent Assigné : {agent.upper()}\n", style="bold yellow")
    content.append(f"🌐 Resourcing Externe : {'Oui (Modèle libre)' if external else 'Non (100% Local)'}\n", style="cyan")
    content.append(f"☁ Synchro Neon Cloud : {'Actif (GZIP)' if neon_sync else 'Mémoire Éphémère'}\n\n", style="cyan")

    if plan:
        content.append("📋 Stratégie adoptée :\n", style="bold green")
        for step in plan:
            content.append(f"  • {step}\n", style="dim green")
        content.append("\n")

    content.append("📝 Résultat :\n", style="bold white")
    msg = agent_res.get("message", "")
    content.append(f"{msg}\n", style="white")

    if "findings" in agent_res and agent_res["findings"]:
        content.append(f"\n🔍 Constats ({len(agent_res['findings'])}) :\n", style="bold yellow")
        for f in agent_res["findings"][:10]:
            content.append(f"  - {f}\n", style="yellow")

    if "files" in agent_res and agent_res["files"]:
        content.append(f"\n📂 Fichiers traités : {', '.join(agent_res['files'])}\n", style="dim")

    console.print(Panel(
        content,
        title=f"🚀 Exécution Tech Lead ({tech_lead.mode})",
        border_style="green" if result.get("success") else "red"
    ))


def handle_mode_command(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Handles the /mode slash command."""
    if not args:
        current = tech_lead.mode
        is_super = current == "lesaintAi"
        console.print(f"Mode actuel : [bold {'red' if is_super else 'green'}]{current}[/]")
        console.print("[dim]Pour changer : /mode freeAi (Standard sécurisé) ou /mode lesaintAi (Super-Utilisateur)[/]")
        return

    target = args[0]
    res = tech_lead.set_mode(target)
    new_mode = res.get("mode")

    if new_mode == "lesaintAi":
        console.print(Panel(
            "[bold red]⚡ MODE SUPER-UTILISATEUR ACTIVÉ (lesaintAi) ⚡[/]\n\n"
            "• Privilèges sudo déverrouillés ([bold red]ALLOW_SUDO=True[/])\n"
            "• Écriture et exécution totale sur tout le système sans restriction\n"
            "• Attention : les actions s'exécutent avec les privilèges maximaux.",
            title="Avertissement Privilèges",
            border_style="red"
        ))
    else:
        console.print(Panel(
            "[bold green]🛡 MODE STANDARD SÉCURISÉ ACTIVÉ (freeAi)[/]\n\n"
            "• Privilèges sudo désactivés ([bold green]Sudo bloqué[/])\n"
            "• Écriture confinée au workspace du projet\n"
            "• Lecture globale du PC autorisée pour trouver des solutions\n"
            "• Compression et sauvegarde déportée vers Neon Cloud.",
            title="Mode Sécurisé",
            border_style="green"
        ))


def get_active_workspace() -> str:
    """Returns the effective workspace root, prioritizing active git repo or WORKSPACE_ROOT."""
    cwd = Path.cwd().resolve()
    if (cwd / ".git").exists():
        return str(cwd)
    if (PROJECT_ROOT / ".git").exists():
        return str(PROJECT_ROOT)
    env_ws = os.getenv("WORKSPACE_ROOT")
    if env_ws and Path(env_ws).exists():
        return env_ws
    return settings.WORKSPACE_ROOT


async def interactive_cli(initial_mode: str = "freeAi"):
    """Main interactive REPL loop."""
    workspace = get_active_workspace()

    # Initialize core services
    resource_manager = ResourceManager(
        target_mb=settings.RAM_TARGET_MB,
        hard_limit_mb=settings.RAM_HARD_LIMIT_MB
    )

    tool_gateway = ToolGateway(
        workspace_root=workspace,
        allow_network=settings.ALLOW_NETWORK,
        allow_sudo=(initial_mode == "lesaintAi"),
        allow_global_read=settings.ALLOW_GLOBAL_READ,
        allow_full_fs_access=(initial_mode == "lesaintAi"),
        mode=initial_mode
    )

    tech_lead = TechLeadOrchestrator(
        tool_gateway=tool_gateway,
        resource_manager=resource_manager
    )

    if initial_mode != "freeAi":
        tech_lead.set_mode(initial_mode)

    setup_readline()
    display_welcome_banner(tech_lead.mode)

    while True:
        try:
            prompt_str = get_prompt(tech_lead.mode)
            user_input = input(prompt_str).strip()

            if not user_input:
                continue

            # Parse input
            parts = shlex.split(user_input)
            cmd = parts[0].lower()
            args = parts[1:]

            if cmd in ("/exit", "/quit"):
                console.print("[bold cyan]Au revoir ! FreeAI s'est arrêté proprement.[/]")
                break
            elif cmd == "/clear":
                console.clear()
            elif cmd == "/help":
                print_help()
            elif cmd == "/status":
                print_status(tech_lead)
            elif cmd == "/mode":
                handle_mode_command(tech_lead, args)
            elif cmd == "/search":
                run_search_files(tech_lead, args)
            elif cmd == "/code":
                run_search_code(tech_lead, args)
            elif cmd == "/rollback":
                run_rollback(tech_lead)
            elif cmd == "/sync":
                run_sync(tech_lead)
            elif user_input.startswith("/"):
                console.print(f"[bold red]Commande slash inconnue :[/] '{cmd}'. Tapez [bold green]/help[/] pour la liste des commandes.")
            else:
                # Regular natural language query transmitted to Tech Lead
                await execute_tech_lead_task(tech_lead, user_input)

        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Interruption détectée. Tapez /exit pour quitter.[/]")
        except Exception as e:
            console.print(f"[bold red]Erreur inattendue :[/] {e}")


def main():
    """CLI entry point handling flags or starting interactive session."""
    import argparse
    parser = argparse.ArgumentParser(description="FreeAI Sovereign Assistant CLI")
    parser.add_argument("--mode", choices=["freeAi", "lesaintAi"], default="freeAi", help="Mode de privilèges initial")
    parser.add_argument("objective", nargs="*", help="Objectif direct à exécuter sans session interactive")

    parsed = parser.parse_args()

    if parsed.objective:
        # Non-interactive batch execution
        objective_text = " ".join(parsed.objective)
        workspace = get_active_workspace()
        rm = ResourceManager()
        gw = ToolGateway(
            workspace_root=workspace,
            allow_sudo=(parsed.mode == "lesaintAi"),
            allow_full_fs_access=(parsed.mode == "lesaintAi"),
            allow_global_read=True,
            mode=parsed.mode
        )
        tech_lead = TechLeadOrchestrator(tool_gateway=gw, resource_manager=rm)
        tech_lead.set_mode(parsed.mode)

        if objective_text.startswith("/"):
            # Handle slash command in batch mode
            parts = shlex.split(objective_text)
            cmd = parts[0].lower()
            args = parts[1:]
            if cmd == "/status":
                print_status(tech_lead)
            elif cmd == "/rollback":
                run_rollback(tech_lead)
            elif cmd == "/sync":
                run_sync(tech_lead)
            elif cmd == "/search":
                run_search_files(tech_lead, args)
            elif cmd == "/code":
                run_search_code(tech_lead, args)
            elif cmd == "/help":
                print_help()
            else:
                print(f"Commande non supportée en mode batch: {cmd}")
        else:
            asyncio.run(execute_tech_lead_task(tech_lead, objective_text))
    else:
        asyncio.run(interactive_cli(initial_mode=parsed.mode))


if __name__ == "__main__":
    main()
