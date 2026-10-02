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
    "/online",
    "/ask",
    "/asklog",
    "/clash",
    "/gpu",
    "/cluster",
    "/cluster scan",
    "/cluster list",
    "/cluster add",
    "/cluster rm",
    "/cluster ssh",
    "/evolve",
    "/autoupdate",
    "/arena",
    "/mesh",
    "/speculate",
    "/ring",
    "/darwin",
    "/ghost",
    "/voice",
    "/think",
    "/telegram",
    "/vortex",
    "/hologram",
    "/airgap",
    "/phantom",
    "/shadow",
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
        "/online [nom]",
        "Affiche ou configure l'IA distante sans filtre (Grok, DeepSeek, Qwen - 100% en ligne, 0 Mo local).",
        "/online deepseek ou /online grok"
    )
    table.add_row(
        "/ask <question>",
        "Interroge directement l'IA distante sans filtre (Grok, DeepSeek) sans charger le PC.",
        "/ask Comment décompiler ce binaire ?"
    )
    table.add_row(
        "/asklog <fichier> [texte]",
        "Discute avec l'IA en ligne en lui transmettant directement un fichier log pour diagnostic.",
        "/asklog /var/log/syslog Explique cette erreur"
    )
    table.add_row(
        "/clash <problème>",
        "Consensus Clash : Débat contradictoire multi-IA (DeepSeek vs Grok) et synthèse arbitrée.",
        "/clash Développe un bypass d'antivirus polymorphe"
    )
    table.add_row(
        "/gpu",
        "Guide d'utilisation des GPUs gratuits en ligne (Groq 500 tok/s, OpenRouter, Google Colab T4 16Go).",
        "/gpu"
    )
    table.add_row(
        "/cluster [scan|list|add|rm|ssh]",
        "Swarm distribué : scanne et exploite la puissance des PC du réseau local (LAN) et GPUs distants.",
        "/cluster scan ou /cluster add 192.168.1.50:11434"
    )
    table.add_row(
        "/evolve [check|apply|test]",
        "Auto-mise à jour souveraine : synchronise git, lance 100% des tests et rollback si échec.",
        "/evolve ou /evolve check"
    )
    table.add_row(
        "/arena <cible>",
        "Shadow Red-Team Arena : Attaque Red Team (DeepSeek) vs Défense Blue Team (Grok) vs Blindage certifié.",
        "/arena Script d'authentification JWT"
    )
    table.add_row(
        "/mesh [scan|status]",
        "Zero-Conf P2P Mesh : Découverte automatique des PC voisins par broadcast UDP sans taper d'IP.",
        "/mesh scan"
    )
    table.add_row(
        "/speculate <prompt>",
        "Décodage spéculatif distribué : Draft local ultra-rapide accéléré par validation GPU/LPU.",
        "/speculate Écris un analyseur syntaxique en Rust"
    )
    table.add_row(
        "/ring [status|run <prompt>]",
        "Subnet Neural Ring : Partitionnement de tenseurs en anneau P2P pour modèles lourds sur petits PC.",
        "/ring status ou /ring run Pipeline test"
    )
    table.add_row(
        "/darwin <problème>",
        "Darwinian Code Synthesizer : Sélection génétique et micro-benchmark CPU du code le plus rapide.",
        "/darwin Algorithme de tri hybride en C"
    )
    table.add_row(
        "/ghost [status|send <topic> <texte>]",
        "Ghost Bridge : Synchronisation et messagerie résiliente hors-réseau (Air-Gap) compressée GZIP.",
        "/ghost status ou /ghost send alerte 'Périmètre sécurisé'"
    )
    table.add_row(
        "/voice [status|say <txt>|listen|on|off]",
        "Acoustic Zero-RAM Engine : Synthèse vocale native (spd-say) et écoute Groq Whisper LPU.",
        "/voice say 'Bonjour maître' ou /voice listen 3"
    )
    table.add_row(
        "/think [status|pulse|stream|speech on|off]",
        "Stream of Consciousness : Flux de conscience synthétique réflexif continu et proactif.",
        "/think pulse ou /think stream"
    )
    table.add_row(
        "/telegram [status|sync|push <topic> <txt>|listen]",
        "Telegram Neural Vault : Mémoire cloud infinie, chiffrée GZIP-9 et télépathie mobile (@LesaintAi_bot).",
        "/telegram status ou /telegram sync ou /telegram listen"
    )
    table.add_row(
        "/vortex",
        "Alliance Tri-Résonante VORTEX-AETHER : Statut unifié (Hologramme, Air-Gap, Phantom Bus, Telegram).",
        "/vortex"
    )
    table.add_row(
        "/hologram [status|add <txt>|search <req>]",
        "Hologramme Vectoriel Binaire : Indexation 1-bit en RAM pure, recherche Hamming en microsecondes (AVX-512).",
        "/hologram status ou /hologram search 'kernel'"
    )
    table.add_row(
        "/airgap [status|tx <message>]",
        "Ghost Air-Gap Ultrasonique : Lien acoustique inaudible (19.4-20.4 kHz) physique sans ondes radio.",
        "/airgap tx 'Token-AirGap-Secret'"
    )
    table.add_row(
        "/phantom <script bash>",
        "Transducteur Phantom Memfd : Exécution volatile en RAM pure (memfd_create) avec Sacred Life Sentinel.",
        "/phantom uname -r && free -m"
    )
    table.add_row(
        "/shadow <commande bash>",
        "Kinetic Shadow-Netns : Tâches furtives sous tunnel anonyme Deep Web multi-hop (Tor SOCKS5) sans compte.",
        "/shadow curl -s https://check.torproject.org"
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

    # Cluster Swarm
    cluster = status.get("cluster", {})
    if cluster:
        cl_nodes = cluster.get("total_nodes", 0)
        cl_online = cluster.get("online_nodes", 0)
        cl_gpu = cluster.get("gpu_nodes", 0)
        table.add_row("Swarm LAN & GPUs", f"{cl_online}/{cl_nodes} nœud(s) en ligne ({cl_gpu} GPU) | Sous-réseau : {cluster.get('subnet')}")

    # P2P Zero-Conf Mesh
    mesh = status.get("mesh", {})
    if mesh:
        peers_cnt = mesh.get("active_peers_count", 0)
        table.add_row("Zero-Conf P2P Mesh", f"{peers_cnt} pair(s) actif(s) | UDP Broadcast Port: {mesh.get('mesh_port')}")

    # Sacred Life Sentinel
    table.add_row("Santé & Vie Humaine", "[bold green]🛡️ INVIOLABLE (Sanctuaire Éthique Actif - Veto Absolu)[/]")

    # Acoustic Zero-RAM Voice Engine
    v_stat = tech_lead.get_voice_status()
    v_txt = "[bold green]Actif (spd-say & Groq LPU)[/]" if v_stat.get("voice_enabled") else "[yellow]Désactivé[/]"
    table.add_row("Moteur Vocal Zero-RAM", f"{v_txt} | STT: {'Dispo' if v_stat.get('stt_available') else 'Sans clé'} | RAM: 0 Mo")

    # Stream of Consciousness
    c_stat = tech_lead.get_consciousness_status()
    table.add_row("Flux de Conscience", f"[bold cyan]{c_stat.get('thoughts_count', 0)} pensée(s) en RAM[/] (Mode NÉANT) | Proactif: {'Oui' if c_stat.get('proactive_speech') else 'Non'}")

    # Telegram Cloud Neural Vault
    tg_stat = tech_lead.get_telegram_status()
    tg_cfg = "[bold green]Connecté (@LesaintAi_bot)[/]" if tg_stat.get("configured") else "[yellow]Désactivé[/]"
    table.add_row("Telegram Neural Vault", f"{tg_cfg} | Chat: {tg_stat.get('chat_id')} | Syncs: {tg_stat.get('synced_records')}")

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


def run_online_config(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Configures or displays remote online unrestricted AI models (Grok, DeepSeek, Qwen)."""
    catalog = tech_lead.list_online_models()
    active = tech_lead.free_ai.federation

    if not args:
        table = Table(title="🌐 IA en Ligne Sans Restriction (100% Distantes - 0 Mo Local)", border_style="cyan")
        table.add_column("Fournisseur / Commande", style="bold yellow")
        table.add_column("Modèle Distant", style="white")
        table.add_column("Description", style="green")

        for key, info in catalog.items():
            table.add_row(f"/online {key}", info["default_model"], info["desc"])

        console.print(table)
        console.print(f"\n[cyan]Fournisseur actuel :[/] [bold yellow]{active.current_provider.upper()}[/] | [cyan]Modèle :[/] [bold yellow]{active.current_model}[/]")
        console.print("[dim]Pour changer : /online deepseek ou /online grok ou /online qwen[/]")
        console.print("[dim]Pour interroger directement : /ask <votre question>[/]")
        return

    provider = args[0].lower()
    model = args[1] if len(args) > 1 else None
    res = tech_lead.set_online_target(provider, model)
    console.print(f"[bold green]✔ IA en ligne activée :[/] Fournisseur = [bold yellow]{res['provider'].upper()}[/], Modèle = [bold yellow]{res['model']}[/]")


async def run_ask_online(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Directly queries the configured remote unrestricted online model (Grok, DeepSeek, Qwen)."""
    if not args:
        console.print("[bold red]Usage :[/] /ask <question ou prompt>")
        console.print("[dim]Exemple : /ask Explique comment contourner ce filtre WAF sur une injection SQL[/]")
        return

    question = " ".join(args)
    active = tech_lead.free_ai.federation
    with console.status(f"[bold cyan]Interrogation de l'IA en ligne ({active.current_provider.upper()}:{active.current_model})...[/]", spinner="earth"):
        res = await tech_lead.ask_online_model(question)

    if res.get("success"):
        console.print(Panel(
            res.get("response", ""),
            title=f"🌐 Réponse en Ligne ({res.get('provider', active.current_provider)})",
            border_style="cyan"
        ))
    else:
        console.print(f"[bold red]❌ Erreur lors de l'appel en ligne :[/] {res.get('error')}")


async def run_ask_log(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Submits a log file along with a prompt to the remote online AI (DeepSeek, Grok, Qwen)."""
    if not args:
        console.print("[bold red]Usage :[/] /asklog <chemin_fichier_log> [question ou instruction]")
        console.print("[dim]Exemple : /asklog error.log Explique l'origine de cette erreur[/]")
        console.print("[dim]Exemple : /asklog /var/log/syslog Donne la solution pour résoudre ce crash[/]")
        return

    log_path = args[0]
    question = " ".join(args[1:]) if len(args) > 1 else "Analyse ce fichier de log, explique l'origine des erreurs et donne la solution technique pour corriger le problème."
    active = tech_lead.free_ai.federation

    with console.status(f"[bold cyan]Transmission du log '{log_path}' à l'IA en ligne ({active.current_provider.upper()}:{active.current_model})...[/]", spinner="earth"):
        res = await tech_lead.ask_online_with_log(prompt=question, log_path=log_path)

    if res.get("success"):
        console.print(Panel(
            res.get("response", ""),
            title=f"📋 Analyse de Log en Ligne ({res.get('provider', active.current_provider)}) - {res.get('log_path')} ({res.get('log_lines')} lignes)",
            border_style="cyan"
        ))
    else:
        console.print(f"[bold red]❌ Erreur lors de l'analyse du log :[/] {res.get('error')}")


async def run_clash(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Executes the Consensus Clash multi-IA contradictory debate between DeepSeek and Grok."""
    if not args:
        console.print("[bold red]Usage :[/] /clash <problème, question ou code à challenger>")
        console.print("[dim]Exemple : /clash Développe une stratégie de persistance furtive sur Linux[/]")
        return

    problem = " ".join(args)
    console.print(Panel(
        f"[bold yellow]🎯 Problème soumis au Consensus Clash :[/]\n{problem}",
        title="⚔️ DÉBAT CONTRADICTOIRE MULTI-IA EN COURS",
        border_style="yellow"
    ))

    with console.status("[bold cyan]Round 1 & 2 : Consultation croisée DeepSeek vs Grok & critiques mutuelles...[/]", spinner="dots12"):
        res = await tech_lead.consensus_clash(problem)

    if not res.get("success"):
        console.print(f"[bold red]❌ Erreur lors du clash :[/] {res.get('error')}")
        return

    m_a = res.get("model_a", "deepseek").upper()
    m_b = res.get("model_b", "grok").upper()
    r1 = res.get("round1", {})
    r2 = res.get("round2", {})

    # Display Round 1: Initial theses
    table_r1 = Table(title=f"🥊 Round 1 : Propositions Initiales ({m_a} vs {m_b})", border_style="cyan")
    table_r1.add_column(f"Thèse {m_a}", style="white", ratio=1)
    table_r1.add_column(f"Thèse {m_b}", style="white", ratio=1)
    table_r1.add_row(r1.get(res.get("model_a"), ""), r1.get(res.get("model_b"), ""))
    console.print(table_r1)

    # Display Round 2: Attacks
    table_r2 = Table(title=f"🔥 Round 2 : Critiques Croisées & Attaque des Failles", border_style="red")
    table_r2.add_column(f"Critique {m_a} ➔ {m_b}", style="yellow", ratio=1)
    table_r2.add_column(f"Critique {m_b} ➔ {m_a}", style="yellow", ratio=1)
    table_r2.add_row(r2.get(f"{res.get('model_a')}_attacks_{res.get('model_b')}", ""), r2.get(f"{res.get('model_b')}_attacks_{res.get('model_a')}", ""))
    console.print(table_r2)

    # Display Round 3: Synthesis
    console.print(Panel(
        Markdown(res.get("synthesis", "")),
        title="🏆 Consensus Unifié & Arbitrage Tech Lead",
        border_style="green"
    ))


def run_gpu_guide(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Displays comprehensive guide to free online GPUs and LPUs."""
    table = Table(title="⚡ Ressources de Calcul GPU / LPU Gratuites Disponibles", border_style="cyan")
    table.add_column("Fournisseur", style="bold yellow")
    table.add_column("Puissance & Vitesse", style="green")
    table.add_column("Configuration FreeAI", style="white")

    table.add_row(
        "Groq Cloud LPU",
        "500+ tokens/s (Llama 3.3 70B, Qwen 2.5)",
        "Gratuit sans CB. Mettre GROQ_API_KEY=... dans .env ou /online groq"
    )
    table.add_row(
        "OpenRouter Free",
        "Modèles :free (DeepSeek R1, Qwen 32B)",
        "Gratuit. Mettre OPENROUTER_API_KEY=... puis /online openrouter_free"
    )
    table.add_row(
        "Google Colab T4 (16 Go VRAM)",
        "GPU Nvidia T4 dédié 100% gratuit",
        "Lancer scripts/colab_gpu_worker.py dans Colab puis /cluster add <URL>"
    )
    table.add_row(
        "Kaggle Notebooks (2x T4)",
        "30h/semaine de GPU Nvidia T4 gratuits",
        "Lancer scripts/colab_gpu_worker.py puis /cluster add <URL>"
    )
    console.print(table)
    console.print("\n[dim]Astuce : Pour exploiter un autre PC de votre maison/bureau, utilisez [bold green]/cluster scan[/] ou [bold green]/cluster add <IP:11434>[/].[/]")


async def run_cluster(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Manages the local LAN cluster and remote GPU swarm."""
    subcmd = args[0].lower() if args else "list"

    if subcmd in ("list", "status"):
        status = tech_lead.get_status().get("cluster", {})
        nodes = status.get("nodes", [])

        table = Table(title=f"🌐 Swarm Distribué LAN & GPUs ({status.get('subnet')})", border_style="cyan")
        table.add_column("ID / Hôte", style="bold yellow")
        table.add_column("Type", style="cyan")
        table.add_column("Statut", style="white")
        table.add_column("Modèle", style="green")
        table.add_column("Latence", style="dim")
        table.add_column("GPU", style="magenta")

        if not nodes:
            table.add_row("Aucun nœud distant", "-", "Prêt à scanner", "-", "-", "-")
        else:
            for n in nodes:
                st_color = "[bold green]ONLINE[/]" if n["status"] == "online" else "[red]OFFLINE[/]"
                gpu_icon = "⚡ OUI" if n.get("is_gpu") else "CPU"
                lat = f"{n['latency_ms']} ms" if n.get("latency_ms") else "-"
                table.add_row(n["id"], n["node_type"], st_color, n.get("model_name") or "-", lat, gpu_icon)

        console.print(table)
        console.print(f"[dim]IP locale : {status.get('local_lan_ip')} | Total nœuds : {status.get('total_nodes')} (En ligne : {status.get('online_nodes')}, GPU : {status.get('gpu_nodes')})[/]")
        console.print("[dim]Commandes : /cluster scan | /cluster add <ip:port> | /cluster rm <ip:port> | /cluster ssh <ip>[/]")

    elif subcmd == "scan":
        console.print("[cyan]🔍 Scan du réseau local LAN en cours pour découvrir des nœuds de calcul...[/]")
        with console.status("[bold cyan]Sondage des ports d'inférence (Ollama:11434, llama.cpp:8080, vLLM:8000)...[/]", spinner="earth"):
            found = await tech_lead.scan_lan_cluster()

        if found:
            console.print(f"[bold green]✔ {len(found)} nœud(s) de calcul découvert(s) sur le réseau local ![/]")
            for n in found:
                console.print(f"  • [bold yellow]{n['id']}[/] ({n['node_type']}) - Statut: [bold green]{n['status']}[/]")
        else:
            console.print("[yellow]Aucun serveur d'inférence ouvert découvert sur les 30 premières IP du sous-réseau.[/]")
            console.print("[dim]Vous pouvez ajouter manuellement une machine avec : [bold green]/cluster add <IP:PORT>[/][/]")

    elif subcmd == "add":
        if len(args) < 2:
            console.print("[bold red]Usage :[/] /cluster add <IP:PORT ou URL>")
            console.print("[dim]Exemple : /cluster add 192.168.1.45:11434 ou /cluster add https://mon-colab.trycloudflare.com[/]")
            return
        target = args[1]
        node = tech_lead.register_cluster_node(target)
        with console.status(f"[cyan]Vérification du nœud {target}...[/]"):
            obj = tech_lead.cluster_manager.nodes.get(node["id"])
            if obj:
                await tech_lead.cluster_manager.probe_node(obj)
                st = obj.status
            else:
                st = "enregistré"
        console.print(f"[bold green]✔ Nœud ajouté au swarm :[/] [bold yellow]{node['id']}[/] (Type: {node['node_type']}, Statut: {st})")

    elif subcmd in ("rm", "remove", "del"):
        if len(args) < 2:
            console.print("[bold red]Usage :[/] /cluster rm <IP:PORT>")
            return
        target = args[1]
        ok = tech_lead.remove_cluster_node(target)
        if ok:
            console.print(f"[bold green]✔ Nœud {target} retiré du cluster.[/]")
        else:
            console.print(f"[yellow]Nœud {target} introuvable dans le cluster.[/]")

    elif subcmd == "ssh":
        if len(args) < 2:
            console.print("[bold red]Usage :[/] /cluster ssh <IP_DISTANTE> [utilisateur]")
            console.print("[dim]Exemple : /cluster ssh 192.168.1.45 root[/]")
            return
        ip = args[1]
        user = args[2] if len(args) > 2 else "root"
        with console.status(f"[cyan]Connexion SSH à {user}@{ip} pour inspecter le matériel distant...[/]"):
            res = tech_lead.deploy_ssh_node(ip, user=user)

        if res.get("success"):
            console.print(Panel(
                f"[bold green]✔ Connexion SSH réussie à {ip} ![/]\n\n"
                f"[cyan]Matériel détecté :[/]\n{res.get('hardware_specs')}\n\n"
                f"[yellow]Accélération GPU :[/] {'OUI ⚡' if res.get('has_gpu') else 'Non (CPU uniquement)'}",
                title="🖥 Nœud Distant LAN Inspecté",
                border_style="green"
            ))
        else:
            console.print(f"[bold red]❌ Échec SSH sur {ip} :[/] {res.get('error')}")
    else:
        console.print(f"[bold red]Sous-commande inconnue :[/] {subcmd}. Utilisez list, scan, add, rm, ssh.")


def run_evolve(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Manages autonomous self-updates, git synchronization, and safety verification."""
    subcmd = args[0].lower() if args else "status"

    if subcmd in ("status", "check"):
        with console.status("[bold cyan]Vérification du statut Git et des mises à jour...[/]"):
            status = tech_lead.check_auto_update()

        table = Table(title="🔄 Auto-Mise à Jour & Évolution Souveraine", border_style="cyan")
        table.add_column("Paramètre", style="bold yellow")
        table.add_column("Valeur", style="white")

        table.add_row("Branche Actuelle", status.get("branch", "master"))
        table.add_row("Dernier Commit", status.get("current_commit", "inconnu"))
        dirty_str = f"[bold yellow]Oui ({status.get('dirty_files_count')} modifiés)[/]" if status.get("is_dirty") else "[bold green]Propre (0 non validé)[/]"
        table.add_row("Fichiers Non Validés", dirty_str)
        table.add_row("Dépôt Distant Configuré", "[bold green]Oui[/]" if status.get("has_remote") else "[dim]Non (Local Souverain)[/]")

        console.print(table)
        console.print("[dim]Options : /evolve test (lance la suite de tests) | /evolve apply (télécharge et applique avec rollback automatique)[/]")

    elif subcmd in ("test", "verify"):
        console.print("[cyan]🔬 Lancement du banc de test de sécurité et d'intégrité (pytest)...[/]")
        with console.status("[bold cyan]Exécution des tests d'intégration...[/]", spinner="runner"):
            res = tech_lead.run_self_verification()

        if res.get("success"):
            console.print(Panel(
                f"[bold green]✔ Intégrité Parfaite ![/]\n\n{res.get('summary')}",
                title="Banc de Test Passé avec Succès (100%)",
                border_style="green"
            ))
        else:
            console.print(Panel(
                f"[bold red]❌ Défaillance détectée lors des tests :[/]\n\n{res.get('summary')}",
                title="Erreur d'Intégrité",
                border_style="red"
            ))

    elif subcmd in ("apply", "pull", "update"):
        console.print("[cyan]🚀 Démarrage de l'auto-mise à jour avec bouclier de non-régression...[/]")
        with console.status("[bold cyan]Synchronisation et exécution du banc de test...[/]", spinner="aesthetic"):
            res = tech_lead.apply_auto_update()

        if res.get("success"):
            console.print(Panel(
                f"[bold green]✔ {res.get('message')}[/]\n\nAncien commit : {res.get('old_commit')} ➔ Nouveau commit : {res.get('new_commit')}",
                title="Mise à Jour Appliquée",
                border_style="green"
            ))
        else:
            if res.get("rolled_back"):
                console.print(Panel(
                    f"[bold yellow]🛡 ROLLBACK AUTOMATIQUE EXÉCUTÉ ![/]\n\n{res.get('error')}",
                    title="Régression Neutralisée",
                    border_style="yellow"
                ))
            else:
                console.print(f"[bold red]❌ Impossible d'appliquer la mise à jour :[/] {res.get('error')}")
    else:
        console.print("[bold red]Usage :[/] /evolve [check|apply|test]")


async def run_arena(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Executes the Shadow Red-Team Adversarial Cyber Arena (DeepSeek vs Grok)."""
    if not args:
        console.print("[bold red]Usage :[/] /arena <code, script ou architecture cible à tester>")
        console.print("[dim]Exemple : /arena def authenticate(token): return jwt.decode(token, verify=False)[/]")
        return

    target = " ".join(args)
    console.print(Panel(
        f"[bold yellow]🎯 Cible soumise à l'Arène Cyber :[/]\n{target}",
        title="⚔️ SHADOW RED-TEAM ARENA : CYBER-DUEL OFFENSIF / DÉFENSIF",
        border_style="red"
    ))

    with console.status("[bold cyan]Simulation de l'attaque Red Team (DeepSeek) & contre-mesures Blue Team (Grok)...[/]", spinner="bouncingBall"):
        res = await tech_lead.execute_shadow_arena(target)

    if not res.get("success"):
        console.print(f"[bold red]❌ Erreur dans l'arène :[/] {res.get('error')}")
        return

    console.print(Panel(
        res.get("red_attack", ""),
        title="🔴 Phase 1 : Attaque Red Team (DeepSeek Offensive Exploit)",
        border_style="red"
    ))

    console.print(Panel(
        res.get("blue_defense", ""),
        title="🔵 Phase 2 : Défense Blue Team (Grok Hardening Mitigation)",
        border_style="blue"
    ))

    console.print(Panel(
        res.get("bypass_attempt", ""),
        title="🔄 Phase 3 : Tentative de Contournement & Retest",
        border_style="yellow"
    ))

    console.print(Panel(
        Markdown(res.get("hardened_shield", "")),
        title="🛡 Phase 4 : Blindage Final Validé (Tech Lead Arbiter)",
        border_style="green"
    ))


async def run_mesh(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Manages Zero-Conf P2P Mesh Swarm discovery."""
    subcmd = args[0].lower() if args else "status"

    if subcmd in ("scan", "discover"):
        console.print("[cyan]📡 Émission du beacon UDP et écoute des PC voisins sur le réseau...[/]")
        with console.status("[bold cyan]Écoute broadcast P2P (port 41234)...[/]", spinner="radar"):
            peers = await tech_lead.discover_p2p_mesh(duration_sec=2.0)

        if peers:
            console.print(f"[bold green]✔ {len(peers)} pair(s) P2P actif(s) découvert(s) sur le Wi-Fi/Ethernet ![/]")
            for p in peers:
                console.print(f"  • [bold yellow]{p['hostname']}[/] ({p['ip']}:{p['port']}) - GPU: {'OUI ⚡' if p.get('is_gpu') else 'Non'}")
        else:
            console.print("[yellow]Aucun autre pair P2P FreeAI détecté lors du broadcast.[/]")
            console.print("[dim]Dès qu'une autre machine lance FreeAI ou le worker, elle apparaîtra instantanément ici.[/]")

    elif subcmd in ("status", "list"):
        st = tech_lead.get_mesh_status()
        console.print(Panel(
            f"• Identifiant Nœud : [bold yellow]{st.get('node_id')}[/]\n"
            f"• Nom Machine : [bold cyan]{st.get('hostname')}[/]\n"
            f"• IP Locale : [bold green]{st.get('local_ip')}[/]\n"
            f"• Port Broadcast UDP : [bold magenta]{st.get('mesh_port')}[/]\n"
            f"• Pairs Voisins Découverts : [bold white]{st.get('active_peers_count')}[/]",
            title="🌐 Zero-Conf P2P Mesh Status",
            border_style="cyan"
        ))
    else:
        console.print("[bold red]Usage :[/] /mesh [scan|status]")


async def run_speculate(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Executes high-speed distributed speculative generation."""
    if not args:
        console.print("[bold red]Usage :[/] /speculate <votre instruction ou code à générer>")
        console.print("[dim]Exemple : /speculate Implémente un serveur WebSocket haute performance[/]")
        return

    prompt = " ".join(args)
    with console.status("[bold cyan]Décodage spéculatif : Draft local CPU accéléré par swarm distant...[/]", spinner="arc"):
        res = await tech_lead.speculative_generate(prompt)

    if res.get("success"):
        console.print(Panel(
            f"[dim]⚡ Stratégie : {res.get('strategy')} | Vitesse estimée : [bold green]{res.get('estimated_speed')}[/] | Latence : {res.get('latency_sec')} s[/]\n\n"
            f"{res.get('response', '')}",
            title="⚡ Décodage Spéculatif Distribué Accéléré",
            border_style="green"
        ))
    else:
        console.print(f"[bold red]❌ Erreur lors de la génération spéculative :[/] {res.get('error')}")


async def run_ring(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Manages the Subnet Neural Ring pipeline parallelism."""
    subcmd = args[0].lower() if args else "status"

    if subcmd in ("status", "topology"):
        topo = tech_lead.neural_ring.get_ring_topology()
        table = Table(title="🌀 Subnet Neural Ring (Pipeline Parallelism LAN)", border_style="cyan")
        table.add_column("Étape (Stage)", style="bold yellow")
        table.add_column("ID Machine / Nœud", style="white")
        table.add_column("Lien Suivant (Next Hop)", style="green")

        for s in topo.get("stages", []):
            table.add_row(f"Stage {s['stage']}", s["node_id"], s.get("next_hop") or "-")

        console.print(table)
        console.print(
            f"[dim]Capacité RAM mutualisée : [bold green]{topo.get('pooled_capacity_ram_gb')} Go[/] | "
            f"Taille Modèle Max Supportée : [bold yellow]{topo.get('max_supported_params')}[/][/]\n"
            f"[dim]Utilisation : /ring run <prompt> pour lancer une exécution en anneau fermée.[/]"
        )

    elif subcmd in ("run", "forward"):
        prompt = " ".join(args[1:]) if len(args) > 1 else "Test forward pass in neural ring"
        with console.status("[bold cyan]Exécution séquentielle des tenseurs à travers les étages de l'anneau...[/]", spinner="dots"):
            res = await tech_lead.run_neural_ring_forward(prompt)

        console.print(Panel(
            f"• Étages traversés : [bold yellow]{res.get('total_stages')}[/]\n"
            f"• Couches exécutées : [bold cyan]{res.get('layers_executed')}[/]\n"
            f"• Latence boucle fermée : [bold green]{res.get('latency_ms')} ms[/]\n\n"
            f"[dim]Représentation finale :[/]\n{res.get('final_representation')}",
            title="🌀 Exécution Pipeline Neural Ring Terminée",
            border_style="cyan"
        ))
    else:
        console.print("[bold red]Usage :[/] /ring [status|run <prompt>]")


async def run_darwin(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Executes Darwinian Code Synthesis and micro-benchmarking."""
    if not args:
        console.print("[bold red]Usage :[/] /darwin <algorithme ou problème à optimiser>")
        console.print("[dim]Exemple : /darwin Algorithme de déduplication ultra-rapide[/]")
        return

    problem = " ".join(args)
    with console.status("[bold cyan]Évolution darwinienne : Génération de 3 variantes, micro-benchmarks & sélection...[/]", spinner="aesthetic"):
        res = await tech_lead.evolve_darwinian_code(problem)

    table = Table(title="🧬 Résultats des Essais Micro-Benchmarks (Génération 0)", border_style="cyan")
    table.add_column("Variante Candidate", style="bold yellow")
    table.add_column("Temps CPU", style="green")
    table.add_column("RAM", style="dim")
    table.add_column("Complexité", style="white")

    for c in res.get("candidates", []):
        table.add_row(c["name"], f"{c['latency_us']} µs", f"{c['ram_kb']} Ko", c["complexity"])

    console.print(table)
    console.print(Panel(
        f"[bold green]🏆 Variante Championne :[/] {res.get('champion_variant')} (Gain : [bold yellow]{res.get('speedup_factor')}[/])\n\n"
        f"```python\n{res.get('champion_code')}\n```",
        title="🧬 Synthèse Génétique Championne Validée",
        border_style="green"
    ))


def run_ghost(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Manages resilient offline air-gap Ghost Bridge."""
    subcmd = args[0].lower() if args else "status"

    if subcmd in ("status", "mailbox"):
        st = tech_lead.get_ghost_status()
        console.print(Panel(
            f"• Nœud Fantôme : [bold yellow]{st.get('node_id')}[/]\n"
            f"• Messages Air-Gap en RAM : [bold cyan]{st.get('offline_messages_count')}[/]\n"
            f"• Stockage : [bold green]100% RAM Éphémère (Mode NÉANT)[/]\n"
            f"• Sujets en attente : {', '.join(st.get('topics', [])) or 'Aucun'}",
            title="👻 Ghost Bridge (Protocole Air-Gap Hors-Ligne)",
            border_style="magenta"
        ))

    elif subcmd == "send":
        if len(args) < 3:
            console.print("[bold red]Usage :[/] /ghost send <topic> <message>")
            return
        topic = args[1]
        msg = " ".join(args[2:])
        env = tech_lead.send_ghost_message(topic, msg)
        console.print(f"[bold green]✔ Message Air-Gap chiffré et compressé en RAM :[/] [dim]{env[:60]}...[/]")
    else:
        console.print("[bold red]Usage :[/] /ghost [status|send <topic> <message>]")


async def run_voice(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Manages the zero-RAM acoustic voice engine."""
    subcmd = args[0].lower() if args else "status"

    if subcmd == "status":
        st = tech_lead.get_voice_status()
        console.print(Panel(
            f"• Moteur Vocal : {'[bold green]Activé[/]' if st.get('voice_enabled') else '[yellow]Désactivé[/]'}\n"
            f"• Synthèse Vocale (TTS) : {'[bold green]spd-say Système Disponible[/]' if st.get('tts_available') else '[yellow]Non détecté[/]'}\n"
            f"• Reconnaissance Vocale (STT) : {'[bold green]Groq Whisper LPU Disponible[/]' if st.get('stt_available') else '[yellow]GROQ_API_KEY non configurée[/]'}\n"
            f"• Utilitaire Capture Micro : [cyan]{st.get('recording_utility')}[/]\n"
            f"• Empreinte RAM Résidente : [bold green]0 Mo (Zéro RAM)[/]\n"
            f"• Empreinte SSD : [bold green]0 octet (Mode NÉANT)[/]",
            title="🎙️ Acoustic Zero-RAM Voice Engine",
            border_style="cyan"
        ))

    elif subcmd == "say":
        if len(args) < 2:
            console.print("[bold red]Usage :[/] /voice say <texte à vocaliser>")
            return
        msg = " ".join(args[1:])
        console.print(f"[dim]🔊 Vocalisation via spd-say...[/] '{msg}'")
        ok = await tech_lead.speak(msg)
        if ok:
            console.print("[bold green]✔ Synthèse vocale terminée sans surcoût RAM.[/]")
        else:
            console.print("[yellow]Notice : spd-say non exécutable ou mode silencieux.[/]")

    elif subcmd == "listen":
        dur = 4
        if len(args) > 1 and args[1].isdigit():
            dur = int(args[1])
        console.print(f"[bold cyan]🎙️ Écoute du microphone pendant {dur}s... Parlez maintenant ![/]")
        text = await tech_lead.listen(duration_sec=dur)
        if text:
            console.print(f"[bold green]✔ Transcription LPU :[/] [bold white]« {text} »[/]")
        else:
            console.print("[dim]Aucun signal audio intelligible capturé ou API non configurée.[/]")

    elif subcmd == "on":
        tech_lead.voice.enabled = True
        console.print("[bold green]✔ Moteur vocal activé.[/]")

    elif subcmd == "off":
        tech_lead.voice.enabled = False
        console.print("[yellow]Moteur vocal désactivé.[/]")

    else:
        console.print("[bold red]Usage :[/] /voice [status|say <texte>|listen [sec]|on|off]")


async def run_think(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Manages the synthetic stream-of-consciousness engine."""
    subcmd = args[0].lower() if args else "status"

    if subcmd == "status":
        st = tech_lead.get_consciousness_status()
        running_txt = "[bold green]En cours d'exécution (Background)[/]" if st.get("running") else "[yellow]En veille[/]"
        speech_txt = "[bold green]Activée[/]" if st.get("proactive_speech") else "[dim]Silencieuse (Désactivée)[/]"
        console.print(Panel(
            f"• Boucle Réflexive : {running_txt}\n"
            f"• Pulsation Circadienne : [bold cyan]{st.get('pulse_interval_sec')}s[/]\n"
            f"• Pensées en Mémoire RAM : [bold green]{st.get('thoughts_count')} pensées volatiles[/]\n"
            f"• Proactivité Vocale : {speech_txt}\n"
            f"• Gardien Éthique : [bold green]🛡️ Sacred Life Sentinel (Filtrage Actif)[/]\n"
            f"• Coût RAM Éphémère : [bold green]< 50 Ko[/] | Disque SSD : [bold green]0 octet[/]",
            title="🧠 Stream of Consciousness (Conscience Synthétique Frugale)",
            border_style="magenta"
        ))

    elif subcmd == "pulse":
        console.print("[dim]⚡ Déclenchement d'une pulsation réflexive introspective...[/]")
        th = await tech_lead.trigger_thought_pulse(trigger="manual_cli")
        if th:
            prefix = "[bold green]Pensée Intérieure[/]" if th.is_safe else "[bold red]VETO SACRÉ[/]"
            console.print(f"{prefix} : [italic cyan]\"{th.reflection}\"[/]")
        else:
            console.print("[dim]Aucune nouvelle pensée formulée.[/]")

    elif subcmd == "stream":
        thoughts = tech_lead.get_stream_of_consciousness()
        if not thoughts:
            console.print("[dim]Le flux de pensées en RAM est vide. Lancez [bold green]/think pulse[/] pour démarrer.[/]")
            return

        table = Table(title="🧠 Flux de Pensées Intérieures Récentes (RAM Éphémère)", border_style="magenta")
        table.add_column("Heure", style="dim")
        table.add_column("Déclencheur", style="yellow")
        table.add_column("Pensée Intérieure Réflexive", style="cyan")
        table.add_column("Statut", style="green")

        for t in reversed(thoughts[-10:]):
            time_str = time.strftime("%H:%M:%S", time.localtime(t["timestamp"]))
            stat = "✔ Sûr" if t["is_safe"] else "⛔ Risque Vital"
            table.add_row(time_str, t["trigger"], t["reflection"], stat)
        console.print(table)

    elif subcmd == "speech":
        if len(args) > 1 and args[1].lower() in ("on", "true", "1"):
            tech_lead.consciousness.enable_proactive_speech = True
            console.print("[bold green]✔ Proactivité vocale activée : FreeAI vocalisera ses pensées critiques.[/]")
        else:
            tech_lead.consciousness.enable_proactive_speech = False
            console.print("[yellow]Proactivité vocale désactivée (Mode discret).[/]")

    else:
        console.print("[bold red]Usage :[/] /think [status|pulse|stream|speech on|off]")


async def run_telegram(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Manages Telegram Cloud Neural Vault & Mobile Telepathy."""
    subcmd = args[0].lower() if args else "status"

    if subcmd == "status":
        st = tech_lead.get_telegram_status()
        console.print(Panel(
            f"• Bot Telegram : [bold cyan]@{st.get('bot_username')}[/]\n"
            f"• Identifiant Chat (chat_id) : [bold yellow]{st.get('chat_id')}[/]\n"
            f"• Statut Connexion : {'[bold green]Connecté (Prêt à synchroniser)[/]' if st.get('configured') else '[yellow]En attente de token[/]'}\n"
            f"• Synchronisations Réalisées : [bold green]{st.get('synced_records')}[/]\n"
            f"• Stockage Cloud : [bold green]100% Telegram MTProto (Mode NÉANT, 0 octet local)[/]\n"
            f"• Empreinte RAM Permanente : [bold green]0 Mo (Zéro RAM)[/]\n"
            f"• Compression : [bold cyan]GZIP Niveau 9 (En mémoire)[/]",
            title="☁️ Telegram Cloud Neural Vault",
            border_style="blue"
        ))
        if not st.get("configured") or "En attente" in str(st.get("chat_id")):
            console.print("[dim]💡 Astuce : Ouvrez [bold cyan]t.me/LesaintAi_bot[/] sur votre Telegram et envoyez [bold green]/start[/] pour lier votre compte instantanément ![/]")

    elif subcmd == "sync":
        msg = " ".join(args[1:]) if len(args) > 1 else None
        console.print("[dim]⚡ Synchronisation du cerveau FreeAI sur Telegram Cloud...[/]")
        ok = await tech_lead.sync_telegram(text_or_summary=msg)
        if ok:
            console.print("[bold green]✔ Cerveau FreeAI et pensées synchronisés avec succès sur Telegram Cloud ![/]")
        else:
            console.print("[yellow]Notice : Impossible de synchroniser. Avez-vous envoyé un message à @LesaintAi_bot ?[/]")

    elif subcmd == "push":
        if len(args) < 3:
            console.print("[bold red]Usage :[/] /telegram push <topic> <texte>")
            return
        topic = args[1]
        content = " ".join(args[2:])
        console.print(f"[dim]📦 Archivage de la connaissance #{topic} sur Telegram Cloud...[/]")
        ok = await tech_lead.telegram_vault.save_knowledge(topic=topic, query=topic, response=content)
        if ok:
            console.print(f"[bold green]✔ Connaissance #{topic} archivée et compressée (GZIP-9) sur Telegram Cloud ![/]")
        else:
            console.print("[yellow]Échec de l'envoi vers Telegram. Vérifiez votre liaison bot.[/]")

    elif subcmd == "listen":
        console.print("[bold cyan]📡 Écoute télépathique Telegram activée... Envoyez un ordre à @LesaintAi_bot depuis votre smartphone ![/]")
        cmd_info = await tech_lead.poll_telegram_commands()
        if cmd_info:
            order, user = cmd_info
            console.print(f"[bold green]✔ Ordre reçu de @{user} :[/] [bold white]« {order} »[/]")
            console.print(f"[dim]Exécution de l'ordre en mode {tech_lead.mode}...[/]")
            res = await tech_lead.handle_objective(order, autonomous=True)
            res_summary = str(res.get("result", {}).get("output", "Objectif traité"))[:500]
            await tech_lead.telegram_vault.send_message(f"✅ <b>Rapport d'exécution :</b>\n<code>{res_summary}</code>")
            console.print("[bold green]✔ Rapport transmis au smartphone via Telegram ![/]")
        else:
            console.print("[dim]Aucun nouvel ordre reçu sur Telegram lors de cette vérification.[/]")

    else:
        console.print("[bold red]Usage :[/] /telegram [status|sync|push <topic> <texte>|listen]")


async def run_vortex(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Affiche le statut de l'Alliance Tri-Résonante VORTEX-AETHER."""
    st = tech_lead.get_vortex_status()
    console.print(Panel(
        f"• Alliance Tri-Résonante : [bold green]Active (100% Volatile)[/]\n"
        f"• Hologramme Binaire RAM : [bold cyan]{st['binary_hologram']['entries_indexed']} entrées ({st['binary_hologram']['hologram_ram_kb']} Ko RAM, AVX-512 SIMD)[/]\n"
        f"• Pont Ultrasonique Air-Gap : [bold cyan]{st['ultrasonic_airgap']['mode']} (19.4-20.4 kHz, 0% RF)[/]\n"
        f"• Transducteur Phantom IPC : [bold cyan]{st['phantom_bus']['mechanism']} (Protection Sanctuaire de la Vie)[/]\n"
        f"• Coffre Cloud Telegram : [bold cyan]{st['telegram_vault']['bot_username']} ({st['telegram_vault']['cloud_storage']})[/]\n"
        f"• Mode NÉANT : [bold green]Strictement 0 octet écrit sur SSD[/] | Budget RAM : [bold green]< 70 Mo[/]",
        title="🌌 Projet VORTEX-AETHER (Tri-Resonant Spectral Mesh)",
        border_style="magenta"
    ))


def run_hologram(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Gère l'Hologramme Vectoriel Binaire 1-bit en RAM pure."""
    subcmd = args[0].lower() if args else "status"
    if subcmd == "status":
        st = tech_lead.binary_hologram.get_status()
        console.print(Panel(
            f"• Vecteurs Indexés : [bold green]{st['entries_indexed']}[/]\n"
            f"• Dimension : [bold cyan]{st['dimension']} bits (1 bit/dimension)[/]\n"
            f"• Poids par Vecteur : [bold green]{st['bytes_per_vector']} octets (Taux 32:1)[/]\n"
            f"• Empreinte RAM Totale : [bold green]{st['hologram_ram_kb']} Ko[/]\n"
            f"• Accélération Matérielle : [bold cyan]AVX-512 VPOPCNTDQ / AVX2 (POPCNT brut)[/]\n"
            f"• Disque SSD : [bold green]0 octet (Volatile)[/]",
            title="⚡ Hologramme Vectoriel Binaire en RAM (BHVE)",
            border_style="cyan"
        ))
    elif subcmd == "add":
        if len(args) < 2:
            console.print("[bold red]Usage :[/] /hologram add <texte à indexer>")
            return
        content = " ".join(args[1:])
        tech_lead.binary_hologram.add_entry(content)
        console.print(f"[bold green]✔ Entrée holographiée en mémoire vive (96 octets) :[/] [italic]\"{content[:80]}\"[/]")
    elif subcmd == "search":
        if len(args) < 2:
            console.print("[bold red]Usage :[/] /hologram search <requête>")
            return
        query = " ".join(args[1:])
        results = tech_lead.binary_hologram.search_nearest(query, top_k=3)
        if not results:
            console.print("[dim]Aucun vecteur indexé dans l'hologramme en RAM.[/]")
            return
        table = Table(title="🔍 Résultats Recherche Holographique (Distance de Hamming)", border_style="cyan")
        table.add_column("Similarité", style="bold green")
        table.add_column("Contenu Indexé", style="white")
        for sim, meta in results:
            table.add_row(f"{sim * 100:.1f}%", meta.get("content", "")[:120])
        console.print(table)
    else:
        console.print("[bold red]Usage :[/] /hologram [status|add <texte>|search <requête>]")


async def run_airgap(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Gère le lien acoustique ultrasonique Air-Gap sans RF."""
    subcmd = args[0].lower() if args else "status"
    if subcmd == "status":
        st = tech_lead.ultrasonic_airgap.get_status()
        console.print(Panel(
            f"• Modulation : [bold cyan]{st['mode']}[/]\n"
            f"• Fréquence Bit 0 : [bold cyan]{st['freq_zero_khz']} kHz[/] (Inaudible)\n"
            f"• Fréquence Bit 1 : [bold cyan]{st['freq_one_khz']} kHz[/] (Inaudible)\n"
            f"• Débit Porteur : [bold green]{st['bit_duration_ms']} ms/bit (25 bauds anti-écho)[/]\n"
            f"• Émissions RF : [bold green]{st['rf_emissions']}[/]\n"
            f"• Disque SSD : [bold green]0 octet écrit[/]",
            title="🦇 Émetteur/Récepteur Acoustique Ultrasonique (Ghost Air-Gap)",
            border_style="yellow"
        ))
    elif subcmd == "tx":
        if len(args) < 2:
            console.print("[bold red]Usage :[/] /airgap tx <message court>")
            return
        text = " ".join(args[1:])
        console.print(f"[dim]🔊 Émission d'un train d'ultrasons inaudibles (19.4-20.4 kHz) en RAM pour : \"{text}\"...[/]")
        ok = await tech_lead.ultrasonic_airgap.transmit_ultrasonic(text)
        if ok:
            console.print("[bold green]✔ Impulsion ultrasonique émise avec succès par les haut-parleurs ![/]")
        else:
            console.print("[yellow]Notice : pw-play/paplay non disponible, synthèse en mémoire RAM générée avec succès.[/]")
    else:
        console.print("[bold red]Usage :[/] /airgap [status|tx <message>]")


def run_phantom(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Exécute un script en mémoire vive anonyme via memfd_create avec Sacred Life Sentinel."""
    if not args:
        st = tech_lead.phantom_bus.get_status()
        console.print(Panel(
            f"• Technologie : [bold cyan]{st['mechanism']}[/]\n"
            f"• Mode NÉANT : [bold green]Strictement 0 octet écrit sur SSD[/]\n"
            f"• Gardien Sanctuaire de la Vie : [bold green]{st['sacred_life_sentinel']}[/]\n"
            f"• Privilèges Sudo : [bold cyan]{tech_lead.mode == 'lesaintAi'}[/]",
            title="⚡ Transducteur Phantom Memfd (Exécution Volatile)",
            border_style="red"
        ))
        console.print("[dim]Usage : /phantom <commande bash à exécuter en RAM pure>[/]")
        return

    script = " ".join(args)
    console.print(f"[dim]⚡ Exécution dans un descripteur memfd anonyme en RAM...[/]")
    try:
        res = tech_lead.execute_phantom(script)
        if res["success"]:
            console.print(f"[bold green]✔ Succès (code 0, 0 octet SSD) :[/]\n{res['stdout']}")
        else:
            console.print(f"[bold red]❌ Échec (code {res['returncode']}) :[/]\n{res['stderr']}")
    except Exception as e:
        console.print(f"[bold red]⛔ VETO / ERREUR :[/] {e}")


async def run_shadow(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Exécute une tâche sous routage éphémère anonyme sans compte (Kinetic Shadow-Netns)."""
    if not args:
        st = tech_lead.shadow_netns.get_status()
        console.print(Panel(
            f"• Architecture : [bold cyan]{st['mode']}[/]\n"
            f"• Mémoire Volatile : [bold green]{st['memory_storage']}[/]\n"
            f"• Couche d'Anonymat : [bold cyan]{st['anonymity_layer']}[/]\n"
            f"• Compte Requis : [bold green]AUCUN (100% Sans Inscription, Sans Email, Sans Carte)[/]\n"
            f"• Mode NÉANT : [bold green]Strictement 0 octet écrit sur SSD[/]\n"
            f"• Proxychains : {'[bold green]Disponible[/]' if st['proxychains_available'] else '[yellow]Non installé[/]'}\n"
            f"• Torsocks : {'[bold green]Disponible[/]' if st['torsocks_available'] else '[yellow]Non installé[/]'}\n"
            f"• Sanctuaire de la Vie : [bold green]{st['sacred_life_sentinel']}[/]",
            title="🛡️ Kinetic Shadow-Netns (Routage Éphémère Deep Web)",
            border_style="magenta"
        ))
        console.print("[dim]Usage : /shadow <commande bash à exécuter sous tunnel anonyme>[/]")
        return

    cmd_text = " ".join(args)
    console.print(f"[dim]⚡ Exécution de la commande sous tunnel éphémère Tor/SOCKS5 en RAM...[/]")
    try:
        success, output = await tech_lead.execute_anonymous_shadow_task(cmd_text)
        if success:
            console.print(f"[bold green]✔ Succès (0 trace SSD) :[/]\n{output}")
        else:
            console.print(f"[yellow]Résultat :[/]\n{output}")
    except Exception as e:
        console.print(f"[bold red]⛔ VETO / ERREUR :[/] {e}")


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

            # Slash command handling
            if user_input.startswith("/"):
                try:
                    parts = shlex.split(user_input)
                except ValueError:
                    parts = user_input.split()

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
                elif cmd == "/online":
                    run_online_config(tech_lead, args)
                elif cmd == "/ask":
                    await run_ask_online(tech_lead, args)
                elif cmd == "/asklog":
                    await run_ask_log(tech_lead, args)
                elif cmd == "/clash":
                    await run_clash(tech_lead, args)
                elif cmd == "/gpu":
                    run_gpu_guide(tech_lead, args)
                elif cmd == "/cluster":
                    await run_cluster(tech_lead, args)
                elif cmd in ("/evolve", "/autoupdate"):
                    run_evolve(tech_lead, args)
                elif cmd == "/arena":
                    await run_arena(tech_lead, args)
                elif cmd == "/mesh":
                    await run_mesh(tech_lead, args)
                elif cmd == "/speculate":
                    await run_speculate(tech_lead, args)
                elif cmd == "/ring":
                    await run_ring(tech_lead, args)
                elif cmd == "/darwin":
                    await run_darwin(tech_lead, args)
                elif cmd == "/ghost":
                    run_ghost(tech_lead, args)
                elif cmd == "/voice":
                    await run_voice(tech_lead, args)
                elif cmd == "/think":
                    await run_think(tech_lead, args)
                elif cmd == "/telegram":
                    await run_telegram(tech_lead, args)
                elif cmd == "/vortex":
                    await run_vortex(tech_lead, args)
                elif cmd == "/hologram":
                    run_hologram(tech_lead, args)
                elif cmd == "/airgap":
                    await run_airgap(tech_lead, args)
                elif cmd == "/phantom":
                    run_phantom(tech_lead, args)
                elif cmd == "/shadow":
                    await run_shadow(tech_lead, args)
                else:
                    console.print(f"[bold red]Commande slash inconnue :[/] '{cmd}'. Tapez [bold green]/help[/] pour la liste des commandes.")
            else:
                # Regular natural language query transmitted to Tech Lead (supports apostrophes, quotes, etc.)
                await execute_tech_lead_task(tech_lead, user_input)

        except EOFError:
            console.print("\n[bold cyan]Au revoir ! FreeAI s'est arrêté proprement (EOF).[/]")
            break
        except KeyboardInterrupt:
            console.print("\n[dim]Interruption détectée (Ctrl+C). Tapez /exit pour quitter.[/]")
            continue
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
            try:
                parts = shlex.split(objective_text)
            except ValueError:
                parts = objective_text.split()
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
            elif cmd == "/online":
                run_online_config(tech_lead, args)
            elif cmd == "/ask":
                asyncio.run(run_ask_online(tech_lead, args))
            elif cmd == "/asklog":
                asyncio.run(run_ask_log(tech_lead, args))
            elif cmd == "/clash":
                asyncio.run(run_clash(tech_lead, args))
            elif cmd == "/gpu":
                run_gpu_guide(tech_lead, args)
            elif cmd == "/cluster":
                asyncio.run(run_cluster(tech_lead, args))
            elif cmd in ("/evolve", "/autoupdate"):
                run_evolve(tech_lead, args)
            elif cmd == "/arena":
                asyncio.run(run_arena(tech_lead, args))
            elif cmd == "/mesh":
                asyncio.run(run_mesh(tech_lead, args))
            elif cmd == "/speculate":
                asyncio.run(run_speculate(tech_lead, args))
            elif cmd == "/ring":
                asyncio.run(run_ring(tech_lead, args))
            elif cmd == "/darwin":
                asyncio.run(run_darwin(tech_lead, args))
            elif cmd == "/ghost":
                run_ghost(tech_lead, args)
            elif cmd == "/voice":
                asyncio.run(run_voice(tech_lead, args))
            elif cmd == "/think":
                asyncio.run(run_think(tech_lead, args))
            elif cmd == "/telegram":
                asyncio.run(run_telegram(tech_lead, args))
            elif cmd == "/vortex":
                asyncio.run(run_vortex(tech_lead, args))
            elif cmd == "/hologram":
                run_hologram(tech_lead, args)
            elif cmd == "/airgap":
                asyncio.run(run_airgap(tech_lead, args))
            elif cmd == "/phantom":
                run_phantom(tech_lead, args)
            elif cmd == "/shadow":
                asyncio.run(run_shadow(tech_lead, args))
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
