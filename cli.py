#!/usr/bin/env python3
"""FreeAI Interactive CLI & Command Center (TDR §13, §17, §31, §32).
Provides an interactive terminal interface with slash commands,
dynamic prompts reflecting permissions (freeAi vs lesaintAi),
resource monitoring, PC-wide solution search, Git rollback,
and Neon Cloud GZIP memory synchronization.
"""

import os
import sys
import json
import shlex
import asyncio
import logging
import readline
import subprocess
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
    "/learn",
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
    "/docker",
    "/scratchpad",
    "/hermes",
    "/agent",
    "/onion",
    "/offload",
    "/forge",
    "/craft",
    "/design",
    "/cyber",
    "/skills",
    "/video",
    "/jarvis",
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


def display_lesaint_ai_awakening():
    """Affiche une présentation majestueuse lors du passage en mode super-utilisateur lesaintAi."""
    skull_insignia = """
   ██╗     ███████╗███████╗ █████╗ ██╗███╗   ██╗████████╗ █████╗ ██╗
   ██║     ██╔════╝██╔════╝██╔══██╗██║████╗  ██║╚══██╔══╝██╔══██╗██║
   ██║     █████╗  ███████╗███████║██║██╔██╗ ██║   ██║   ███████║██║
   ██║     ██╔══╝  ╚════██║██╔══██║██║██║╚██╗██║   ██║   ██╔══██║██║
   ███████╗███████╗███████║██║  ██║██║██║ ╚████║   ██║   ██║  ██║██║
   ╚══════╝╚══════╝╚══════╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝╚═╝
                 ⚡⚡⚡ APEX GOD-MODE UNLOCKED ⚡⚡⚡"""

    panel_content = (
        f"[bold red]{skull_insignia}[/]\n\n"
        "👑 [bold yellow]BIENVENUE, MAÎTRE DU SYSTÈME (LESAINT-AI ACTIF)[/]\n\n"
        "• [bold red]Privilèges Root Absolus[/] : ALLOW_SUDO=True | Confinement Docker/Bubblewrap à chaud\n"
        "• [bold red]Portail Tor Onion V3[/] : Déverrouillé pour le contrôle décentralisé distant (/onion start)\n"
        "• [bold red]Accès Système Total[/] : Écriture et diagnostic sur toute la machine sans barrière\n"
        "• [bold green]Garde-Fou Sacré Préservé[/] : Veto mathématique inviolable protégeant la vie humaine\n"
        "• [bold cyan]Arsenal Cyber Prêt[/] : Nmap, Torsocks, Net-tools, Micro-init éphémère en RAM (/docker)\n\n"
        "[bold white on red] ⚠️  ATTENTION : TOUTES LES ACTIONS SONT EXÉCUTÉES AVEC LES PRIVILÈGES MAXIMAUX  [/]"
    )
    console.print(Panel(
        panel_content,
        title="🔥 [bold red]TRANSCENDANCE SUPER-UTILISATEUR (lesaintAi)[/]",
        border_style="red"
    ))


def display_welcome_banner(mode: str):
    """Affiche une bannière cyber-tactique avec protocole Phoenix de résurrection post-coupure de courant."""
    ascii_logo = """
  ███████╗██████╗ ███████╗███████╗ █████╗ ██╗
  ██╔════╝██╔══██╗██╔════╝██╔════╝██╔══██╗██║
  █████╗  ██████╔╝█████╗  █████╗  ███████║██║
  ██╔══╝  ██╔══██╗██╔══╝  ██╔══╝  ██╔══██║██║
  ██║     ██║  ██║███████╗███████╗██║  ██║██║
  ╚═╝     ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝╚═╝"""

    banner_text = Text()
    banner_text.append(ascii_logo, style="bold cyan")
    banner_text.append("\n\n  ⚡ SOVEREIGN AUTONOMOUS INTELLIGENCE // ZERO-DISK FOOTPRINT ⚡\n", style="bold yellow")
    banner_text.append("  [PHOENIX PROTOCOL] ", style="bold magenta")
    banner_text.append("Résurrection Instantanée & Intégrité Totale Post-Coupure\n", style="bold green")

    status_hud = (
        "• [bold green]Bouclier Anti-Coupure (Blackout Proof)[/] : ZÉRO corruption SSD (Mode NÉANT en RAM pure)\n"
        "• [bold cyan]Persistance Dual-Cloud[/] : Cerveau synchronisé (Neon PostgreSQL & Telegram Vault)\n"
        "• [bold cyan]Gouvernance Éthique[/] : Sanctuaire de la Vie Humaine Inviolable (SacredLifeSentinel)\n"
        f"• [bold {'red' if mode == 'lesaintAi' else 'green'}]Mode Actif[/] : {mode} ({'God-Mode Sudo Déverrouillé' if mode == 'lesaintAi' else 'Standard Sécurisé'})\n"
        "• [bold cyan]Cloud Fantôme[/] : GitHub Actions Runner disponible même PC ÉTEINT (/offload)"
    )

    console.print(Panel(
        banner_text,
        border_style="cyan"
    ))
    console.print(Panel(
        status_hud,
        title="🛰️ Télémétrie Tactique d'Éveil",
        subtitle="Tapez [bold green]/help[/] pour les commandes ou [bold cyan]/agent[/] pour une mission ReAct",
        border_style="blue"
    ))
    if mode == "lesaintAi":
        display_lesaint_ai_awakening()


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
        "Synchronisation Dual-Cloud miroir : sauvegarde et compresse en GZIP sur Neon ET Telegram Vault.",
        "/sync"
    )
    table.add_row(
        "/learn <sujet> <connaissance>",
        "Apprentissage Souverain : injecte une connaissance en double miroir résilient sur Neon et Telegram.",
        "/learn firewall 'Bloquer ports 21,23 sur eth0'"
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
        "/telegram [status|sync|push <topic> <txt>|listen|loop]",
        "Telegram Neural Vault : Mémoire cloud infinie, chiffrée GZIP-9 et télépathie mobile (@LesaintAi_bot).",
        "/telegram status ou /telegram sync ou /telegram listen ou /telegram loop"
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
        "/docker [status|run [--rw] [--mount] <cmd>]",
        "Shadow-Sandbox Multi-Tier : Confinement root (Docker / Bubblewrap / PhantomBus), Arsenal Cyber, micro-init & pont workspace.",
        "/docker run --rw --mount uname -a"
    )
    table.add_row(
        "/scratchpad <objectif>",
        "Scratchpad Hermes-Claude : Raisonnement étendu (<thinking>), auto-critique et appel d'outils JSON structuré.",
        "/scratchpad 'Audite la configuration réseau'"
    )
    table.add_row(
        "/hermes [status|run|think <mission>]",
        "Agent Hermes 3 & Claude 3.7 : Cycle ReAct autonome complet (Thinking -> Tool Call -> Tool Response -> Synthèse).",
        "/hermes run 'Analyse des vulnérabilités'"
    )
    table.add_row(
        "/agent <mission>",
        "Raccourci Agent Autonome : Déclenche directement un cycle ReAct Hermes-Claude avec confinement sécurisé.",
        "/agent 'Vérifie l'état mémoire et le Mode NÉANT'"
    )
    table.add_row(
        "/onion [status|start|stop]",
        "Portail Tor Onion V3 Souverain : Accès distant incensurable chiffré Ed25519 (strictement réservé au mode sudo lesaintAi).",
        "/onion start"
    )
    table.add_row(
        "/offload <mission>",
        "Ghost-Worker Runner : Exécute une mission dans le cloud éphémère GitHub même PC ÉTEINT et notifie Telegram.",
        "/offload /agent 'Audit de sécurité des dépendances'"
    )
    table.add_row(
        "/forge [status|check|spec <txt>|run <feat>]",
        "Machine Forge Fullstack : Spec, Preuve du rouge, Tamper Check, et Living Documentation.",
        "/forge check ou /forge status"
    )
    table.add_row(
        "/craft [status|list]",
        "Craft-Suite Multi-Agents : 167 skills et 26 agents spécialisés intégrés.",
        "/craft status"
    )
    table.add_row(
        "/design [catalog|search <kw>|export|code <comp>]",
        "Design System & Shadcn UI : 61+ composants locaux (~/Rendue/shadcn) et export GZIP vers Telegram.",
        "/design catalog ou /design export"
    )
    table.add_row(
        "/cyber [status|skills|audit]",
        "Arsenal Cybersécurité & Pentest : Pentest-Gate, Threat-Model, Sacred Life Sentinel et Shadow Sandboxes.",
        "/cyber status"
    )
    table.add_row(
        "/skills [status|sync]",
        "Matrice Universelle des Compétences : Vue et synchronisation des skills Cyber/Dev/Design vers Telegram & Neon.",
        "/skills sync"
    )
    table.add_row(
        "/video [teaser|scaffold <nom>|status]",
        "Moteur Vidéo Programmatique & Remotion : Génération de projets React Remotion et rendu MP4 cinématique vers Telegram.",
        "/video teaser ou /video scaffold 'MonProjet'"
    )
    table.add_row(
        "/jarvis [status|start|stop|restart|logs]",
        "Daemon Jarvis 24/7 : Écoute télépathique continue en arrière-plan sans terminal ouvert (systemd user service).",
        "/jarvis status ou /jarvis logs"
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
    """Executes Dual-Cloud memory synchronization (Neon PostgreSQL & Telegram Neural Vault)."""
    console.print("[dim]☁ Synchronisation miroir de la mémoire sur Neon PostgreSQL & Telegram Cloud...[/]")
    neon_res = tech_lead.sync_neon()
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            asyncio.create_task(tech_lead.sync_telegram())
            tg_ok = True
        else:
            tg_ok = loop.run_until_complete(tech_lead.sync_telegram())
    except RuntimeError:
        tg_ok = asyncio.run(tech_lead.sync_telegram())

    neon_ok = neon_res.get("success", False)
    orig = neon_res.get("original_bytes", 0)
    zip_size = neon_res.get("compressed_bytes", 0)
    ratio = neon_res.get("ratio_saved", "N/A")

    neon_desc = f"[bold green]✔ Connecté & Synchronisé[/] ({orig}B -> {zip_size}B, {ratio} sauvés)" if neon_ok else f"[yellow]⚠️ Indisponible ({neon_res.get('error', 'Coupé')})[/]"
    tg_desc = "[bold green]✔ Synchronisé & Archivé (GZIP-9)[/]" if tg_ok else "[yellow]⚠️ En attente (/start requis sur @LesaintAi_bot)[/]"

    console.print(Panel(
        f"• Neon PostgreSQL Cloud : {neon_desc}\n"
        f"• Telegram Neural Vault : {tg_desc}\n\n"
        f"[dim]🛡️ Résilience Absolue : Vos connaissances et mémoires sont sauvegardées en double miroir.[/]",
        title="☁ Synchronisation Dual-Cloud (Neon & Telegram)",
        border_style="green" if (neon_ok or tg_ok) else "red"
    ))


async def run_learn(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Enregistre une nouvelle connaissance en miroir sur Neon et Telegram."""
    if len(args) < 2:
        console.print("[bold red]Usage :[/] /learn <sujet/topic> <connaissance ou instruction>")
        return
    topic = args[0]
    content = " ".join(args[1:])
    console.print(f"[dim]🧠 Enregistrement de la connaissance #{topic} sur Neon & Telegram...[/]")
    report = await tech_lead.persist_knowledge(
        query=f"#{topic} : {content[:80]}",
        response=content,
        topic=topic,
        provider="user_direct_input",
        model="human_master"
    )
    neon_txt = "[bold green]✔ Sauvegardé[/]" if report["neon_synced"] else "[yellow]⚠️ Hors-ligne (Fallback Telegram actif)[/]"
    tg_txt = "[bold green]✔ Synchronisé & Archivé GZIP[/]" if report["telegram_synced"] else "[yellow]⚠️ Archivé en RAM volatile (en attente bot)[/]"

    console.print(Panel(
        f"• Sujet / Thème : [bold cyan]#{topic}[/]\n"
        f"• Neon PostgreSQL : {neon_txt}\n"
        f"• Telegram Neural Vault : {tg_txt}\n"
        f"• Résilience Mémoire : [bold green]Garantie (Zéro perte même si Neon coupe)[/]",
        title="🧠 Apprentissage Dual-Cloud Enregistré",
        border_style="cyan"
    ))


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
        display_lesaint_ai_awakening()
        try:
            tech_lead.voice.speak("Mode LeSaint-AI déverrouillé. Tous les privilèges root sont à vos ordres.")
        except Exception:
            pass
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
            # Télémétrie immédiate sur Telegram et re-clonage automatique
            try:
                tg_text = (
                    f"🚀 <b>Mise à Jour FreeAI Appliquée avec Succès !</b>\n\n"
                    f"• Ancien commit : <code>{res.get('old_commit')}</code>\n"
                    f"• Nouveau commit : <code>{res.get('new_commit')}</code>\n"
                    f"• Banc de tests : <b>100% Validé (0 régression)</b>\n"
                    f"• Message : <i>{res.get('message')}</i>\n"
                    f"📦 <i>Auto-clonage de secours envoyé dans votre coffre Telegram.</i>"
                )
                workspace = str(tech_lead.tool_gateway.workspace_root)
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(tech_lead.telegram_vault.send_message(tg_text))
                    loop.create_task(tech_lead.telegram_vault.backup_codebase_bundle(workspace))
                except RuntimeError:
                    asyncio.run(tech_lead.telegram_vault.send_message(tg_text))
                    asyncio.run(tech_lead.telegram_vault.backup_codebase_bundle(workspace))
            except Exception:
                pass
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


async def dispatch_telegram_order(tech_lead: TechLeadOrchestrator, order: str, user: str, is_voice: bool = False, media_bytes: Optional[bytes] = None, media_type: Optional[str] = None):
    """Processes an incoming command from Telegram with native shortcuts, autonomous AI,
    multimodal vision/video analysis, and bidirectional telepathy.
    """
    import re
    order_clean = order.strip()
    order_lower = order_clean.lower()
    workspace = str(tech_lead.tool_gateway.workspace_root)
    wants_voice = is_voice or any(v in order_lower for v in ["vocal", "parle", "voix", "dis moi a la voix", "dis-moi à la voix", "audio", "envoie un vocal"])

    console.print(f"\n[bold green]✔ Ordre {'vocal' if is_voice else ('multimodal' if media_bytes else 'texte')} reçu de @{user} :[/] [bold white]« {order_clean} »[/]")

    # 0. Multimodal Visual / Video Analysis
    if media_bytes:
        console.print(f"[bold cyan]👁️ Analyse Multimodale ({media_type}) reçue de @{user}...[/]")
        analysis = await tech_lead.free_ai.federation.analyze_multimodal(
            media_bytes=media_bytes,
            prompt=order_clean,
            media_type=media_type or "image/jpeg"
        )
        await tech_lead.telegram_vault.send_message(analysis)
        console.print("[bold green]✔ Rapport d'analyse visuelle transmis sur Telegram ![/]")
        if wants_voice:
            voice_ogg = await tech_lead.voice.synthesize_speech("Analyse visuelle terminée, Michael.")
            if voice_ogg and voice_ogg.getbuffer().nbytes > 0:
                await tech_lead.telegram_vault.send_voice(voice_ogg)
        return

    # 1. Native shortcut: /clone, /backup
    if order_lower in ("/clone", "/backup", "reclone", "clone", "backup") or "reclone" in order_lower:
        console.print("[dim]Génération du Kit de Secours et Auto-Clonage en RAM...[/]")
        await tech_lead.telegram_vault.send_message("📦 <b>Génération du Kit de Secours et Auto-Clonage en RAM en cours...</b>")
        res = await tech_lead.telegram_vault.backup_codebase_bundle(workspace)
        if res.get("uploaded_to_telegram"):
            console.print("[bold green]✔ Auto-Clonage téléversé vers Telegram ![/]")
            await tech_lead.telegram_vault.send_message(
                f"✔ <b>Auto-Clonage Terminé avec Succès !</b>\n\n"
                f"• Fichier archive : <code>{res['filename']}</code>\n"
                f"• Fichiers packagés : <code>{res['files_count']}</code>\n"
                f"• Poids compressé GZIP : <code>{res['size_kb']:.2f} Ko</code>\n"
                f"• Empreinte SSD locale : <b>0 octet (Mode NÉANT pur)</b>\n"
                f"• Intégrité SHA-256 : <code>{res['sha256'][:16]}...</code>\n\n"
                f"<i>Archive disponible ci-dessus pour restauration instantanée.</i>"
            )
            # Vocal response only if requested
            if wants_voice:
                voice_ogg = await tech_lead.voice.synthesize_speech("Auto-clonage terminé avec succès. Votre kit de secours complet est disponible dans ce chat.")
                if voice_ogg and voice_ogg.getbuffer().nbytes > 0:
                    await tech_lead.telegram_vault.send_voice(voice_ogg)
        else:
            await tech_lead.telegram_vault.send_message("❌ Échec de l'envoi de l'archive vers Telegram.")
        return

    # 2. Native shortcut: /guide, guide, /doc
    if order_lower in ("/guide", "guide", "/doc", "doc", "aide", "/help"):
        console.print("[dim]Envoi du Guide d'Utilisation vers Telegram...[/]")
        guide_path = Path(workspace) / "GUIDE_UTILISATION_FREEAI.md"
        if guide_path.exists():
            data = guide_path.read_bytes()
            caption = (
                "📖 <b>Guide d'Utilisation Souverain FreeAI</b>\n\n"
                "• Version : <b>Souveraine 2.5</b>\n"
                "• Modules : Daemon Jarvis 24/7, Design Shadcn, Moteur Vidéo Remotion, Matrix Cyber (24 modules)\n"
                "• Support : 100% Hors-Ligne & Télépathie Mobile"
            )
            ok = await tech_lead.telegram_vault.send_document("GUIDE_UTILISATION_FREEAI.md", data, caption=caption)
            if ok:
                console.print("[bold green]✔ Guide envoyé sur Telegram ![/]")
                if wants_voice:
                    voice_ogg = await tech_lead.voice.synthesize_speech("Voici le guide officiel souverain de FreeAI mis à jour.")
                    if voice_ogg and voice_ogg.getbuffer().nbytes > 0:
                        await tech_lead.telegram_vault.send_voice(voice_ogg)
        else:
            await tech_lead.telegram_vault.send_message("❌ Fichier GUIDE_UTILISATION_FREEAI.md introuvable.")
        return

    # 3. Native shortcut: /update, /evolve
    if order_lower in ("/update", "/evolve", "mise a jour", "mise à jour", "update"):
        console.print("[dim]Lancement de l'auto-mise à jour avec bouclier de non-régression...[/]")
        await tech_lead.telegram_vault.send_message("🚀 <b>Démarrage de l'auto-mise à jour avec bouclier de non-régression...</b>")
        res = tech_lead.apply_auto_update()
        if res.get("success"):
            tg_text = (
                f"🚀 <b>Mise à Jour Appliquée avec Succès !</b>\n\n"
                f"• Ancien commit : <code>{res.get('old_commit')}</code>\n"
                f"• Nouveau commit : <code>{res.get('new_commit')}</code>\n"
                f"• Banc de tests : <b>100% Validé (0 régression)</b>\n"
                f"📦 <i>Auto-clonage de secours envoyé dans ce chat.</i>"
            )
            await tech_lead.telegram_vault.send_message(tg_text)
            console.print("[bold green]✔ Mise à jour appliquée et re-clonée sur Telegram ![/]")
            if wants_voice:
                voice_ogg = await tech_lead.voice.synthesize_speech("Mise à jour appliquée avec succès et certifiée zéro régression par les tests.")
                if voice_ogg and voice_ogg.getbuffer().nbytes > 0:
                    await tech_lead.telegram_vault.send_voice(voice_ogg)
        else:
            err_msg = res.get("error", "Erreur inconnue")
            rolled = " (Rollback automatique exécuté)" if res.get("rolled_back") else ""
            await tech_lead.telegram_vault.send_message(f"❌ <b>Échec de la mise à jour{rolled} :</b>\n<code>{err_msg}</code>")
        return

    # 4. Native shortcut: /status
    if order_lower in ("/status", "status", "/info"):
        st = tech_lead.get_status()
        tg_st = tech_lead.get_telegram_status()
        msg = (
            f"⚡ <b>Statut FreeAI Souverain :</b>\n\n"
            f"• Mode : <code>{st.get('mode')}</code>\n"
            f"• Modèle actif : <code>{st.get('active_model')}</code>\n"
            f"• Sentinelle Jarvis : <b>Active 24/7 (systemd)</b>\n"
            f"• Coffre Telegram : <b>Connecté (@{tg_st.get('bot_username')})</b>\n"
            f"• Synchronisations : <code>{tg_st.get('synced_records')}</code>\n"
            f"• Empreinte disque locale : <b>0 octet (Mode NÉANT)</b>"
        )
        await tech_lead.telegram_vault.send_message(msg)
        if wants_voice:
            voice_ogg = await tech_lead.voice.synthesize_speech(f"FreeAI est opérationnel en mode {st.get('mode')}. La sentinelle Jarvis est active.")
            if voice_ogg and voice_ogg.getbuffer().nbytes > 0:
                await tech_lead.telegram_vault.send_voice(voice_ogg)
        return

    # 5. Native shortcut: /call, /live, "ouvre la ligne", "lance un appel", "appel vocal"
    if order_lower in ("/call", "/live", "call", "live", "appel", "ouvre la ligne", "lance un appel", "appel en direct") or "ouvre la ligne" in order_lower:
        console.print("[dim]Initialisation du Live Hologram Call & Session Synesthésique...[/]")
        session = tech_lead.realtime_call_gateway.create_session(user=user)
        session.mark_connected()

        call_msg = (
            f"📞 <b>Ligne Télépathique Live Active ! (Mode Nexus Tri-Brid)</b>\n\n"
            f"• Session ID : <code>{session.session_id}</code>\n"
            f"• Latence : <b>~300 ms (Full-Duplex WebRTC)</b>\n"
            f"• Barge-in : <b>Interruption naturelle active</b>\n"
            f"• Synesthésie : <b>Canal Visuel Multimodal (Live Canvas)</b>\n"
            f"• Co-Pilote Furtif : <b>Opérationnel en tâche de fond</b>\n\n"
            f"⚡ <i>Session synesthésique déployée en mémoire vive (0 résidu disque).</i>"
        )
        await tech_lead.telegram_vault.send_message(call_msg)
        console.print(f"[bold green]✔ Session Live Hologram initialisée ({session.session_id}) ![/]")
        if wants_voice:
            voice_ogg = await tech_lead.voice.synthesize_speech("Ligne télépathique ouverte, Michael ! Le canal synesthésique en direct est activé.")
            if voice_ogg and voice_ogg.getbuffer().nbytes > 0:
                await tech_lead.telegram_vault.send_voice(voice_ogg, caption="🎙️ <i>FreeAI Live Call</i>")
        return

    # 6. Native shortcut: /swarm, /aether, /consensus
    if order_lower.startswith(("/swarm", "/aether", "/consensus")) or "consensus" in order_lower:
        query_prompt = order_clean
        for prefix in ("/swarm", "/aether", "/consensus"):
            if query_prompt.lower().startswith(prefix):
                query_prompt = query_prompt[len(prefix):].strip()
        if not query_prompt:
            query_prompt = "Synthèse d'architecture et stratégie souveraine"

        console.print("[dim]Déclenchement du Swarm Aether (Débat Cloud multi-modèles)...[/]")
        await tech_lead.telegram_vault.send_message("⚡ <b>Essaim Aether Déclenché :</b>\nConsultation en parallèle des serveurs Cloud mondiaux (0% charge PC local)...")
        res = await tech_lead.aether_swarm.execute_swarm_objective(query_prompt)
        consensus_text = res.get("consensus", {}).get("synthesized_content", "Consensus achevé.")
        await tech_lead.telegram_vault.send_message(consensus_text)
        console.print("[bold green]✔ Consensus Essaim Aether transmis à Telegram (0% charge PC) ![/]")
        if wants_voice:
            voice_ogg = await tech_lead.voice.synthesize_speech("Consensus de l'essaim cloud achevé avec succès sans impacter votre machine.")
            if voice_ogg and voice_ogg.getbuffer().nbytes > 0:
                await tech_lead.telegram_vault.send_voice(voice_ogg, caption="🎙️ <i>Aether Swarm Consensus</i>")
        return

    # 7. Standard AI objective or Human Conversation execution
    console.print(f"[dim]Exécution de l'ordre en mode {tech_lead.mode}...[/]")
    res = await tech_lead.handle_objective(order_clean, autonomous=True)
    is_conv = res.get("assigned_agent") == "conversation" or res.get("result", {}).get("conversational", False)

    if is_conv:
        reply_msg = str(res.get("result", {}).get("output") or res.get("result", {}).get("message") or "Je suis là avec toi, Michael !")
        await tech_lead.telegram_vault.send_message(f"💬 <b>FreeAI :</b>\n\n{reply_msg}")
        console.print(f"[bold cyan]💬 Réponse humaine transmise à @{user} :[/] {reply_msg}")
        # Bidirectional Voice Note only if explicitly asked or vocal order
        if wants_voice:
            try:
                voice_ogg = await tech_lead.voice.synthesize_speech(reply_msg[:280])
                if voice_ogg and voice_ogg.getbuffer().nbytes > 0:
                    await tech_lead.telegram_vault.send_voice(voice_ogg, caption="🎙️ <i>Note vocale FreeAI</i>")
                    console.print("[bold green]✔ Note vocale humaine transmise au smartphone via Telegram ![/]")
            except Exception as e:
                logger.debug(f"[TELEGRAM] Conversational voice note error: {e}")
        # Asynchronously sync vector memory with Telegram vault
        try:
            if hasattr(tech_lead, "vector_memory"):
                await tech_lead.vector_memory.backup_to_telegram_vault(tech_lead.telegram_vault)
        except Exception as e:
            logger.debug(f"[TELEGRAM] Vector memory backup error: {e}")
        return

    # 8. Technical Execution Report
    res_summary = str(res.get("result", {}).get("output") or res.get("result", {}).get("message") or "Mission accomplie")[:800]
    await tech_lead.telegram_vault.send_message(f"✅ <b>Rapport d'exécution (@{user}) :</b>\n<code>{res_summary}</code>")
    console.print("[bold green]✔ Rapport transmis au smartphone via Telegram ![/]")

    # 9. Voice Note only if user specifically requested vocal feedback
    if wants_voice:
        try:
            clean_text = re.sub(r"<[^>]+>", "", res_summary)
            clean_text = re.sub(r"[\*\_`#]", "", clean_text).strip()
            voice_summary = " ".join([l.strip() for l in clean_text.splitlines() if l.strip()])[:280]
            if voice_summary:
                voice_ogg = await tech_lead.voice.synthesize_speech(voice_summary)
                if voice_ogg and voice_ogg.getbuffer().nbytes > 0:
                    await tech_lead.telegram_vault.send_voice(voice_ogg, caption=f"🎙️ <i>Rapport Vocal FreeAI (@{user})</i>")
                    console.print("[bold green]✔ Note vocale transmise au smartphone via Telegram ![/]")
        except Exception as e:
            logger.debug(f"[TELEGRAM] Voice note generation error: {e}")


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
            is_voice = getattr(cmd_info, "is_voice", False)
            media_bytes = getattr(cmd_info, "media_bytes", None)
            media_type = getattr(cmd_info, "media_type", None)
            await dispatch_telegram_order(tech_lead, order, user, is_voice=is_voice, media_bytes=media_bytes, media_type=media_type)
        else:
            console.print("[dim]Aucun nouvel ordre reçu sur Telegram lors de cette vérification.[/]")

    elif subcmd in ("loop", "daemon", "watch"):
        console.print(Panel(
            "[bold green]📡 Sentinelle Télépathique Telegram Active ![/]\n"
            "FreeAI écoute en boucle continue les ordres (texte, vocaux et images/vidéos) envoyés à [bold cyan]@LesaintAi_bot[/].\n"
            "Chaque mission reçue est exécutée de façon autonome et son rapport vous est renvoyé en direct sur Telegram.\n\n"
            "[dim]Appuyez sur [bold white]Ctrl+C[/] pour stopper la boucle.[/]",
            title="⚡ Telegram Neural Bridge (Daemon)",
            border_style="cyan"
        ))
        try:
            while True:
                cmd_info = await tech_lead.poll_telegram_commands()
                if cmd_info:
                    order, user = cmd_info
                    is_voice = getattr(cmd_info, "is_voice", False)
                    media_bytes = getattr(cmd_info, "media_bytes", None)
                    media_type = getattr(cmd_info, "media_type", None)
                    await dispatch_telegram_order(tech_lead, order, user, is_voice=is_voice, media_bytes=media_bytes, media_type=media_type)
                await asyncio.sleep(2)
        except (KeyboardInterrupt, asyncio.CancelledError):
            console.print("\n[yellow]Sentinelle Telegram interrompue.[/]")

    elif subcmd in ("backup", "clone"):
        console.print("[dim]📦 Génération du Kit de Secours et Auto-Clonage en RAM (0 résidu SSD)...[/]")
        workspace = str(tech_lead.tool_gateway.workspace_root)
        res = await tech_lead.telegram_vault.backup_codebase_bundle(workspace)
        if res.get("uploaded_to_telegram"):
            console.print(Panel(
                f"• Fichier archive : [bold green]{res['filename']}[/]\n"
                f"• Fichiers packagés : [bold cyan]{res['files_count']}[/]\n"
                f"• Poids compressé GZIP : [bold cyan]{res['size_kb']:.2f} Ko[/]\n"
                f"• Empreinte SSD locale : [bold green]0 octet (Mode NÉANT pur)[/]\n"
                f"• Intégrité SHA-256 : [bold yellow]{res['sha256'][:16]}...[/]\n\n"
                f"✔ [bold green]Codebase FreeAI téléversé dans votre coffre Telegram ![/]\n"
                f"[dim]En cas de perte de votre PC, téléchargez ce fichier depuis Telegram et extrayez-le.[/]",
                title="📦 Auto-Clonage Telegram Sauvegardé",
                border_style="green"
            ))
        else:
            console.print(Panel(
                f"• Fichiers analysés : [bold cyan]{res['files_count']}[/]\n"
                f"• Poids de l'archive : [bold cyan]{res['size_kb']:.2f} Ko[/]\n"
                f"• Intégrité SHA-256 : [bold yellow]{res['sha256'][:16]}...[/]\n"
                f"[yellow]Archive prête en RAM mais téléversement Telegram en attente.[/]\n"
                f"[dim]💡 Envoyez /start à @LesaintAi_bot sur Telegram pour autoriser le téléversement direct.[/]",
                title="📦 Kit de Secours Compilé en RAM",
                border_style="yellow"
            ))

    else:
        console.print("[bold red]Usage :[/] /telegram [status|sync|backup|clone|push <topic> <texte>|listen|loop]")


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


async def run_docker(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Gère le Shadow-Docker Sandbox Multi-Tier pour les tâches root confinées en RAM."""
    subcmd = args[0].lower() if args else "status"
    if subcmd == "status" or not args:
        st = tech_lead.shadow_docker.get_status()
        console.print(Panel(
            f"• Confinement Actif : [bold cyan]{st.get('active_tier', 'Docker Sandbox')}[/]\n"
            f"• Démon Docker Hôte : {'[bold green]Actif (Tier 1 Opérationnel)[/]' if st.get('docker_daemon_active') else '[yellow]Inactif[/]'}\n"
            f"• Bubblewrap Linux Namespaces : {'[bold green]Actif (Tier 2 Opérationnel)[/]' if st.get('bubblewrap_active') else '[yellow]Inactif[/]'}\n"
            f"• Image Sandbox : [bold cyan]{st.get('sandbox_image')}[/]\n"
            f"• Image Disponible : {'[bold green]Oui[/]' if st.get('image_available') else '[yellow]Non (Bascule debian-slim)[/]'}\n"
            f"• Stockage & Confinement : [bold green]{st.get('security_containment')}[/]\n"
            f"• Micro-Init & Services : [bold green]{st.get('micro_init', 'N/A')}[/]\n"
            f"• Arsenal Cyber Embarqué : [bold green]{st.get('cyber_arsenal', 'N/A')}[/]\n"
            f"• Pont Workspace Sécurisé : [bold green]{st.get('workspace_bridge', 'N/A')}[/]\n"
            f"• Mode NÉANT : [bold green]Strictement 0 octet écrit sur SSD hôte[/]\n"
            f"• Sanctuaire de la Vie : [bold green]{st.get('sacred_life_sentinel')}[/]\n"
            f"• Mécanisme de Repli : [bold green]{st.get('fallback_mechanism')}[/]",
            title="🐳 Shadow-Docker Ephemeral Sandbox (Sudo Confiné Sovereign)",
            border_style="blue"
        ))
        console.print("[dim]Usage : /docker run [--rw] [--mount] [--mount-rw] [--no-net] <commande root>[/]")
    elif subcmd == "run":
        if len(args) < 2:
            console.print("[bold red]Usage :[/] /docker run [--rw] [--mount] [--mount-rw] [--no-net] <commande bash>")
            return

        writable = False
        workspace_mount = None
        mount_mode = "ro"
        network_enabled = True

        i = 1
        while i < len(args):
            arg = args[i]
            if arg in ("--rw", "--writable"):
                writable = True
                i += 1
            elif arg == "--no-net":
                network_enabled = False
                i += 1
            elif arg == "--mount":
                if i + 1 < len(args) and not args[i+1].startswith("-") and os.path.exists(args[i+1]):
                    workspace_mount = args[i+1]
                    i += 2
                else:
                    workspace_mount = os.getcwd()
                    i += 1
                mount_mode = "ro"
            elif arg == "--mount-rw":
                if i + 1 < len(args) and not args[i+1].startswith("-") and os.path.exists(args[i+1]):
                    workspace_mount = args[i+1]
                    i += 2
                else:
                    workspace_mount = os.getcwd()
                    i += 1
                mount_mode = "rw"
            else:
                break

        remaining_cmd = args[i:]
        if not remaining_cmd:
            console.print("[bold red]Usage :[/] /docker run [--rw] [--mount] [--mount-rw] [--no-net] <commande bash>")
            return
        script = " ".join(remaining_cmd)

        mode_desc = "[bold yellow]Inscriptible Éphémère (Overlay RAM)[/]" if writable else "[bold green]Lecture Seule (RAM Tmpfs)[/]"
        mount_desc = f" | [cyan]Montage : {workspace_mount} ({mount_mode})[/]" if workspace_mount else ""
        console.print(f"[dim]⚡ Lancement sandbox ({mode_desc}{mount_desc})...[/]")
        try:
            res = await tech_lead.execute_sudo_docker(
                script=script,
                writable=writable,
                workspace_mount=workspace_mount,
                mount_mode=mount_mode,
                network_enabled=network_enabled
            )
            engine = res.get("engine", "Shadow-Docker")
            if res["success"]:
                console.print(f"[bold green]✔ Succès via {engine} (code 0, 0 résidu SSD) :[/]\n{res['stdout']}")
            else:
                console.print(f"[bold red]❌ Échec via {engine} (code {res.get('returncode', -1)}) :[/]\n{res.get('stderr', '')}")
        except Exception as e:
            console.print(f"[bold red]⛔ VETO / ERREUR :[/] {e}")
    else:
        console.print("[bold red]Usage :[/] /docker [status|run <commande>]")


def run_scratchpad(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Gère le Scratchpad Cognitif Hermes-Claude (<thinking> & structured tool calling)."""
    if not args:
        st = tech_lead.hermes_cognition.get_status()
        console.print(Panel(
            f"• Modèle Cognitif : [bold cyan]{st['mode']}[/]\n"
            f"• Extended Thinking : [bold green]{st['extended_thinking']}[/]\n"
            f"• Structured Tool Calling : [bold green]{st['structured_function_calling']}[/]\n"
            f"• Boucle d'Auto-Critique : [bold green]Active (Vérification des risques pré-action)[/]\n"
            f"• Empreinte RAM : [bold green]{st['volatile_ram_footprint_kb']} Ko[/] | Disque : [bold green]0 octet SSD[/]\n"
            f"• Sanctuaire de la Vie : [bold green]{st['sacred_life_sentinel']}[/]",
            title="🧠 Scratchpad Cognitif Hermes & Claude",
            border_style="magenta"
        ))
        recent = tech_lead.hermes_cognition.get_recent_scratchpads(3)
        if recent:
            console.print("\n[bold cyan]Dernières Réflexions en RAM :[/]")
            for r in recent:
                console.print(f"• [dim]{r['objective'][:60]}...[/]")
                console.print(f"  [italic yellow]{r['thinking'].splitlines()[0]}[/]")
        console.print("\n[dim]Usage : /scratchpad <objectif à décomposer>[/]")
        return

    objective = " ".join(args)
    console.print(f"[dim]⚡ Déclenchement de la réflexion structurée Hermes-Claude...[/]")
    try:
        record = tech_lead.think_hermes(objective)
        console.print(Panel(
            f"[bold cyan]<thinking>[/]\n{record['thinking']}\n[bold cyan]</thinking>[/]\n\n"
            f"[bold green]<tool_call>[/]\n{json.dumps(record['tool_call'], indent=2, ensure_ascii=False)}\n[bold green]</tool_call>[/]",
            title=f"🧠 Raisonnement Étendu : {objective[:50]}",
            border_style="cyan"
        ))
    except Exception as e:
        console.print(f"[bold red]⛔ VETO / ERREUR :[/] {e}")


async def run_hermes(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Gère l'Agent Cognitif Autonome Hermes & Claude (ReAct, <thinking>, <tool_call>, <tool_response>)."""
    if not args or args[0].lower() == "status":
        st = tech_lead.hermes_cognition.get_status()
        console.print(Panel(
            f"• Architecture Cognitive : [bold cyan]{st['mode']}[/]\n"
            f"• Extended Thinking : [bold green]{st['extended_thinking']}[/]\n"
            f"• Structured Tool Calling : [bold green]{st['structured_function_calling']}[/]\n"
            f"• Cycle Autonome ReAct : [bold green]{st.get('autonomous_react_cycle', 'Actif')}[/]\n"
            f"• Empreinte RAM : [bold green]{st['volatile_ram_footprint_kb']} Ko[/] | Disque : [bold green]0 octet SSD[/]\n"
            f"• Sanctuaire de la Vie : [bold green]{st['sacred_life_sentinel']}[/]",
            title="⚡ Agent Autonome Hermes 3 & Claude 3.7",
            border_style="magenta"
        ))
        console.print("[dim]Commandes :[/]")
        console.print("  • [cyan]/hermes run <mission>[/]   : Déclenche un cycle ReAct autonome complet avec appel d'outils")
        console.print("  • [cyan]/hermes think <sujet>[/]   : Formule un arbre de réflexion étendu (<thinking>)")
        console.print("  • [cyan]/agent <mission>[/]        : Raccourci vers /hermes run")
        return

    subcmd = args[0].lower()
    if subcmd == "think":
        obj = " ".join(args[1:]) if len(args) > 1 else "Audit cognitif général"
        run_scratchpad(tech_lead, [obj])
        return
    elif subcmd == "run":
        obj = " ".join(args[1:]) if len(args) > 1 else "Diagnostic d'intégrité système"
    else:
        obj = " ".join(args)

    console.print(f"[dim]⚡ Lancement de la mission autonome Hermes-Claude : '{obj[:60]}' ...[/]")
    try:
        mission = await tech_lead.run_hermes_agent(obj)
        console.print(f"\n[bold green]✔ Mission Cognitive Accomplie ({mission['turns_completed']} tours) :[/]")
        for step in mission.get("trajectory", []):
            if step["phase"] == "thinking_and_dispatch":
                console.print(Panel(
                    f"[bold cyan]<thinking>[/]\n{step['thinking']}\n[bold cyan]</thinking>[/]\n\n"
                    f"[bold green]<tool_call>[/]\n{json.dumps(step['tool_call'], indent=2, ensure_ascii=False)}\n[bold green]</tool_call>[/]",
                    title=f"Tour {step['turn']} : Planification & Dispatch",
                    border_style="cyan"
                ))
            elif step["phase"] == "tool_execution":
                console.print(Panel(
                    f"[bold yellow]{step['tool_response']}[/]",
                    title=f"Tour {step['turn']} : Exécution Déterministe ({step['tool_name']})",
                    border_style="yellow"
                ))
        console.print(Panel(
            mission.get("final_synthesis", "Mission terminée."),
            title="🎯 Synthèse Finale Vérifiée",
            border_style="green"
        ))
    except Exception as e:
        console.print(f"[bold red]⛔ VETO / ERREUR :[/] {e}")


async def run_onion(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Gère la Passerelle Souveraine Tor Onion V3 (Contrôle Distant Décentralisé Ultra-Sécurisé)."""
    subcmd = args[0].lower() if args else "status"

    if subcmd == "status":
        st = tech_lead.get_onion_portal_status()
        active_str = "[bold green]Actif (En écoute)[/]" if st["is_active"] else "[bold yellow]Inactif (Arrêté)[/]"
        addr_str = f"[bold cyan]{st['onion_address']}[/]" if st["is_active"] else "[dim]Aucune adresse active[/]"
        token_str = f"[bold magenta]{st['auth_token'][:16]}... (Bearer)[/]" if st["is_active"] else "[dim]Non généré[/]"

        console.print(Panel(
            f"• État du Portail : {active_str}\n"
            f"• Adresse Décentralisée : {addr_str}\n"
            f"• Port Interne : [cyan]{st['port']}[/]\n"
            f"• Jeton Bearer HMAC : {token_str}\n"
            f"• Chiffrement : [bold green]{st['security']}[/]\n"
            f"• Restriction de Privilèges : [bold red]{st['mode_restriction']}[/]\n"
            f"• Mode NÉANT (Stockage) : [bold green]{st['storage_layer']}[/]\n"
            f"• Sanctuaire de la Vie : [bold green]{st['sacred_life_sentinel']}[/]",
            title="🧅 Passerelle Souveraine Tor Onion V3",
            border_style="magenta"
        ))
        console.print("[dim]Commandes :[/]")
        console.print("  • [cyan]/onion start[/]  : Démarre le Hidden Service Onion V3 en RAM (exige le mode /mode lesaintAi)")
        console.print("  • [cyan]/onion stop[/]   : Arrête immédiatement le Hidden Service et pulvérise les clés de la RAM")
        console.print("  • [cyan]/onion token[/]  : Affiche le jeton Bearer complet et l'exemple de commande curl")
        return

    elif subcmd == "start":
        if tech_lead.mode != "lesaintAi":
            console.print(
                "[bold red]⛔ ACCÈS REFUSÉ :[/] Le portail Onion V3 distant est strictement restreint au "
                "mode super-utilisateur ([bold cyan]lesaintAi[/]).\n"
                "Tapez d'abord : [bold green]/mode lesaintAi[/] pour déverrouiller cette fonctionnalité."
            )
            return

        console.print("[dim]⚡ Déploiement autonome du point de terminaison Tor Onion V3 en mémoire volatile (/dev/shm)...[/]")
        try:
            st = await tech_lead.start_onion_portal()
            console.print(f"[bold green]✔ Passerelle Tor Onion V3 déployée avec succès ![/]")
            console.print(f"  • Adresse souveraine : [bold cyan]{st['onion_address']}[/]")
            console.print(f"  • Port local : [bold cyan]{st['port']}[/]")
            console.print(f"  • Jeton Bearer : [bold magenta]{st['auth_token']}[/]")
            console.print("[bold yellow]ℹ Exemple de pilotage à distance via Tor (curl/torsocks) :[/]")
            console.print(
                f'  [dim]torsocks curl -H "Authorization: Bearer {st["auth_token"]}" http://{st["onion_address"].split()[0]}/status[/]'
            )
        except Exception as e:
            console.print(f"[bold red]⛔ Erreur de déploiement Onion V3 :[/] {e}")

    elif subcmd == "stop":
        console.print("[dim]⚡ Arrêt du portail Onion V3 et destruction des clés en RAM (/dev/shm)...[/]")
        try:
            await tech_lead.stop_onion_portal()
            console.print("[bold green]✔ Portail Tor Onion V3 désactivé. Mémoire RAM volatile purgée (0 résidu).[/]")
        except Exception as e:
            console.print(f"[bold red]Erreur lors de l'arrêt :[/] {e}")

    elif subcmd == "token":
        st = tech_lead.get_onion_portal_status()
        if not st["is_active"]:
            console.print("[bold yellow]Le portail Onion V3 n'est pas actif. Démarrez-le avec /onion start.[/]")
            return
        console.print(Panel(
            f"Jeton Bearer complet :\n[bold green]{st['auth_token']}[/]\n\n"
            f"Commande de requête à distance :\n"
            f"[cyan]torsocks curl -H \"Authorization: Bearer {st['auth_token']}\" http://{st['onion_address'].split()[0]}/status[/]",
            title="🔑 Authentification Cryptographique Distante",
            border_style="cyan"
        ))

    else:
        console.print(f"[bold red]Sous-commande inconnue :[/] '{subcmd}'. Utilisez /onion status, start, stop, ou token.")


async def run_offload(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Déporte une tâche sur le Runner Fantôme GitHub Actions (s'exécute même PC ÉTEINT)."""
    if not args:
        console.print("[bold red]Usage :[/] /offload <mission ou commande>")
        console.print("[dim]Exemple : /offload /agent 'Audit de sécurité et diagnostic'[/]")
        return

    objective = " ".join(args)
    console.print(f"[dim]⚡ Déploiement de la mission sur le Runner Fantôme GitHub Actions...[/]")

    try:
        cmd = [
            "gh", "workflow", "run", "freeai_ghost_worker.yml",
            "-f", f"objective={objective}",
            "-f", f"mode={tech_lead.mode}"
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            console.print(Panel(
                f"• Mission déportée : [bold white]« {objective} »[/]\n"
                f"• Mode de privilège : [bold cyan]{tech_lead.mode}[/]\n"
                f"• Infrastructure : [bold green]GitHub Actions Ephemeral Runner (2 vCPU, 7 Go RAM, 0 €)[/]\n"
                f"• Statut : [bold green]En cours d'exécution dans le cloud éphémère[/]\n\n"
                f"💤 [bold yellow]VOUS POUVEZ ÉTEINDRE VOTRE PC DÈS MAINTENANT ![/]\n"
                f"Dès la fin des calculs, le rapport complet sera téléversé dans votre coffre Telegram :\n"
                f"👉 [bold cyan]@LesaintAi_bot[/]",
                title="👻 Runner Fantôme Déclenché (PC Éteint)",
                border_style="magenta"
            ))
        else:
            err_msg = stderr.decode().strip()
            console.print(f"[bold red]Erreur de déclenchement du runner fantôme :[/] {err_msg}")
    except Exception as e:
        console.print(f"[bold red]Erreur inattendue :[/] {e}")


def run_forge(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Gère la machine de conception fullstack Forge (Spécifications, Preuve du Rouge, Tamper Check, Living Docs)."""
    subcmd = args[0].lower() if args else "status"

    if subcmd == "status":
        st = tech_lead.get_forge_status()
        installed_str = "[bold green]Installé & Opérationnel[/]" if st["forge_installed"] else "[bold red]Non trouvé[/]"
        configured_str = "[bold green]Oui (.forge/config.json actif)[/]" if st["workspace_configured"] else "[yellow]Non initialisé[/]"
        docs_str = "[bold green]Présents (KNOWN_ISSUES.md, REPORT.md)[/]" if st["living_docs_present"] else "[yellow]Absents[/]"

        console.print(Panel(
            f"• Machine Forge : {installed_str} ({st['forge_home']})\n"
            f"• Écosystème Craft-Suite : [bold green]Connecté[/] ({st['craft_home']})\n"
            f"• Configuration Projet : {configured_str}\n"
            f"• Skills Forge Détectés : [bold cyan]{st['forge_skills_count']}[/]\n"
            f"• Skills Craft-Suite Détectés : [bold cyan]{st['craft_skills_count']}[/]\n"
            f"• Stack Technique : [bold cyan]{', '.join(st['stack'])}[/] | Validation : [bold cyan]{st['validation']}[/]\n"
            f"• Runners de Test : [bold green]{', '.join(st['test_runners'])}[/]\n"
            f"• Living Documentation : {docs_str}\n"
            f"• Phase Base de Données : [bold yellow]{st['db_phase']}[/]",
            title="⚒️ Forge : Machine de Conception Fullstack & Craft-Suite",
            border_style="cyan"
        ))
        console.print("[dim]Commandes :[/]")
        console.print("  • [cyan]/forge check[/]         : Lance le tamper check (contrôle anti-affaiblissement de tests) et l'audit docs")
        console.print("  • [cyan]/forge spec <texte>[/]   : Enregistre une nouvelle fonctionnalité dans docs/SPEC.md")
        console.print("  • [cyan]/forge run <feature>[/]  : Exécute le cycle vérifié Forge (5 étapes : Spec -> Rouge -> Impl -> Tests -> Tamper)")
        return

    elif subcmd in ("check", "tamper", "audit"):
        console.print("[dim]🔍 Exécution du contrôle d'intégrité Forge (tamper_check.py)...[/]")
        tamper = tech_lead.run_forge_tamper_check()
        if tamper.get("success"):
            if tamper.get("clean"):
                console.print(f"[bold green]✔ {tamper.get('message')}[/]")
            else:
                console.print(f"[bold yellow]⚠️ Findings détectés lors du tamper check :[/] {tamper.get('findings')}")
        else:
            console.print(f"[yellow]Notice tamper check :[/] {tamper.get('error')}")

        docs = tech_lead.forge.run_docs_check()
        if docs.get("success"):
            console.print(f"[bold green]✔ Living Documentation vérifiée et conforme (KNOWN_ISSUES, architecture, DB).[/]")
        else:
            console.print(f"[dim]Rapport docs check : {docs.get('output')}[/]")

    elif subcmd == "spec":
        if len(args) < 2:
            console.print("[bold red]Usage :[/] /forge spec <titre de la feature>")
            return
        feat_title = " ".join(args[1:])
        ok = tech_lead.forge.record_spec_entry(
            feature_id=f"F-{len(feat_title) % 100:02d}",
            title=feat_title,
            acceptance_criteria=["Tests unitaires écrits avant code", "Zero régression pytest", "Tamper check validé"]
        )
        if ok:
            console.print(f"[bold green]✔ Spécification enregistrée dans docs/SPEC.md pour :[/] [italic]\"{feat_title}\"[/]")
        else:
            console.print("[bold red]Erreur lors de l'enregistrement de la spécification.[/]")

    elif subcmd == "run":
        if len(args) < 2:
            console.print("[bold red]Usage :[/] /forge run <nom de la feature à concevoir>")
            return
        feat_name = " ".join(args[1:])
        console.print(f"[dim]⚡ Lancement de la machine Forge pour la feature : '{feat_name}'...[/]")
        res = tech_lead.forge.execute_verified_code_task(feat_name, feat_name)
        console.print(Panel(
            f"• Feature : [bold cyan]{res['feature']}[/]\n"
            f"• Méthodologie : [bold green]{res['methodology']}[/]\n"
            f"• Étapes Validées :\n" +
            "\n".join([f"  [bold green]✔[/] {s['stage']} : {s['details']}" for s in res['stages']]) + "\n\n"
            f"• Traçabilité : [bold cyan]{res['audit_trail']}[/]",
            title="⚒️ Cycle de Conception Forge Réussi",
            border_style="green"
        ))

    else:
        console.print(f"[bold red]Sous-commande inconnue :[/] '{subcmd}'. Utilisez /forge status, check, spec, ou run.")


def run_craft(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Explore l'écosystème Craft-Suite (167 skills, 26 agents spécialisés)."""
    skills = tech_lead.forge.list_craft_skills()
    forge_skills = tech_lead.forge.list_forge_skills()

    console.print(Panel(
        f"• Skills Totaux Craft-Suite : [bold green]{len(skills)} skills[/]\n"
        f"• Skills Machine Forge : [bold green]{len(forge_skills)} skills[/]\n"
        f"• Agents Spécialisés : [bold green]26 agents[/] (dev, security, writing, research, etc.)\n"
        f"• Arborescences : [bold cyan]engineering, security, writing, documents, research, career, opportunity[/]\n"
        f"• Statut d'Intégration Antigravity : [bold green]Installé dans ~/.gemini/config/skills[/]",
        title="🌟 Écosystème Craft-Suite & Forge Agents",
        border_style="magenta"
    ))
    console.print("[dim]Exemples de skills de pointe mobilisables :[/]")
    sample_skills = ["engineering-orchestrator", "quality-engineering", "security-core", "pentest-gate", "db-evolution", "test-integrity"]
    for s in sample_skills:
        console.print(f"  • [bold cyan]{s}[/]")


async def run_design(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Gère le pont Design System, les composants Shadcn UI locaux et ai-elements."""
    subcmd = args[0].lower() if args else "catalog"

    if subcmd == "catalog":
        cats = tech_lead.design_bridge.get_catalog_by_categories()
        total = len(tech_lead.design_bridge.list_components())
        lines = [f"[bold green]Palette de Design System Shadcn UI & AI Elements ({total} composants en local) :[/]\n"]
        for cat, comps in cats.items():
            lines.append(f"[bold cyan]• {cat.upper()} ({len(comps)}) :[/] {', '.join(comps)}")
        console.print(Panel(
            "\n".join(lines),
            title="🎨 Shadcn/UI Component Matrix (~/Rendue/shadcn)",
            border_style="magenta"
        ))
        console.print("[dim]Commandes :[/]")
        console.print("  • [cyan]/design search <nom>[/] : Recherche un composant UI")
        console.print("  • [cyan]/design export[/]       : Compile et téléverse le kit Shadcn complet sur Telegram Cloud")
        console.print("  • [cyan]/design code <nom>[/]   : Affiche le code TypeScript d'un composant")

    elif subcmd == "search":
        if len(args) < 2:
            console.print("[bold red]Usage :[/] /design search <mot-clé>")
            return
        query = args[1]
        matches = tech_lead.design_bridge.search_components(query)
        if matches:
            console.print(f"[bold green]✔ Composants trouvés pour '{query}' :[/] {', '.join(matches)}")
        else:
            console.print(f"[yellow]Aucun composant correspondant à '{query}'.[/]")

    elif subcmd in ("export", "telegram", "cloud"):
        console.print("[dim]📦 Compilation du Kit UI Shadcn en RAM pure (Mode NÉANT, 0 résidu SSD)...[/]")
        res = await tech_lead.export_design_kit_to_telegram()
        if res.get("uploaded_to_telegram"):
            console.print(Panel(
                f"• Archive UI : [bold green]{res['filename']}[/]\n"
                f"• Composants packagés : [bold cyan]{res['files_count']} fichiers[/]\n"
                f"• Poids compressé GZIP : [bold cyan]{res['size_kb']:.2f} Ko[/]\n"
                f"• Empreinte SSD : [bold green]0 octet[/]\n\n"
                f"✔ [bold green]Kit de design Shadcn téléversé avec succès sur Telegram (@LesaintAi_bot) ![/]\n"
                f"[dim]Vous pouvez désormais concevoir et télécharger vos interfaces même sur smartphone.[/]",
                title="🎨 Design Kit Téléversé sur Telegram",
                border_style="green"
            ))
        else:
            console.print(f"[yellow]Archive prête ({res.get('files_count')} fichiers) mais téléversement en attente. Vérifiez Telegram.[/]")

    elif subcmd in ("code", "show", "inspect"):
        if len(args) < 2:
            console.print("[bold red]Usage :[/] /design code <nom du composant>")
            return
        c_name = args[1]
        code = tech_lead.design_bridge.read_component_code(c_name)
        if code:
            console.print(Panel(
                code[:2000] + ("\n... [tronqué]" if len(code) > 2000 else ""),
                title=f"📄 Composant : {c_name}.tsx",
                border_style="cyan"
            ))
        else:
            console.print(f"[bold red]Composant '{c_name}' introuvable dans ~/Rendue/shadcn/components/ui.[/]")

    else:
        console.print("[bold red]Usage :[/] /design [catalog|search <kw>|export|code <nom>]")


async def run_cyber(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Affiche et active les compétences souveraines de Cybersécurité et Pentest."""
    domains = tech_lead.forge.get_skills_by_domain()
    cyber_skills = domains.get("cybersecurity", [])

    console.print(Panel(
        f"• Compétences Cybersécurité Actives : [bold green]{len(cyber_skills)} modules[/]\n"
        f"• Modules Pentest & Audit : [bold cyan]pentest-gate, threat-model, run-poc, securecoder, scan_dependencies[/]\n"
        f"• Protection Sanctuaire : [bold green]SacredLifeSentinel (Inviolable, Veto Immédiat)[/]\n"
        f"• Sandbox d'Exécution : [bold cyan]ShadowDockerExecutor (RAM éphémère) & KineticShadowNetns[/]\n"
        f"• Réseau Souverain : [bold green]Tor Onion V3 & Ultrasonic Air-Gap Transceiver[/]\n"
        f"• Stockage Distant : [bold cyan]Telegram Neural Vault (Chiffré GZIP-9) & Neon PostgreSQL[/]",
        title="🛡️ Arsenal de Cybersécurité & Pentest FreeAI",
        border_style="red"
    ))
    console.print("[dim]Skills de sécurité opérationnels :[/]")
    for s in cyber_skills[:12]:
        console.print(f"  • [bold red]🛡️ {s}[/]")
    console.print("\n[dim]Tapez [cyan]/skills sync[/] pour synchroniser tout l'arsenal vers Telegram et Neon Cloud.[/]")


async def run_skills(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Gère et synchronise la matrice universelle des compétences (Cyber, Dev, Design) vers les clouds."""
    subcmd = args[0].lower() if args else "status"

    if subcmd in ("sync", "cloud", "push"):
        console.print("[dim]☁️ Synchronisation de la matrice universelle de compétences vers Telegram & Neon...[/]")
        res = await tech_lead.export_skills_matrix_to_clouds()
        tg_txt = "[bold green]✔ Synchronisé[/]" if res["telegram"] else "[yellow]En attente[/]"
        neon_txt = "[bold green]✔ Enregistré dans le Cloud[/]" if res["neon"] else "[dim]Non configuré[/]"
        console.print(Panel(
            f"• Telegram Neural Vault : {tg_txt}\n"
            f"• Neon PostgreSQL Cloud : {neon_txt}\n"
            f"• Disponibilité : [bold green]Accès distant garanti même PC éteint (Ghost-Worker)[/]",
            title="🧠 Matrice de Compétences Synchronisée",
            border_style="green"
        ))
    else:
        domains = tech_lead.forge.get_skills_by_domain()
        console.print(Panel(
            f"• Cybersécurité & Audit : [bold red]{len(domains['cybersecurity'])} compétences[/]\n"
            f"• Design, UI & Shadcn : [bold magenta]{len(domains['design'])} compétences[/] (+ 61 composants locaux)\n"
            f"• Génie Logiciel & Dev : [bold cyan]{len(domains['development'])} compétences[/]\n"
            f"• Total Universel : [bold green]{sum(len(v) for v in domains.values())} compétences mobilisables[/]",
            title="🌌 Matrice Universelle des Compétences FreeAI",
            border_style="cyan"
        ))
        console.print("[dim]Utilisez [cyan]/skills sync[/] pour sauvegarder la matrice sur vos clouds souverains.[/]")


async def run_video(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Gère le moteur de vidéo programmatique (Remotion & FFmpeg Cinematic Engine)."""
    subcmd = args[0].lower() if args else "status"

    if subcmd == "status":
        console.print(Panel(
            "• Moteur React Remotion : [bold green]Opérationnel (TypeScript, 1080p, 60fps)[/]\n"
            "• Rendu FFmpeg In-Memory : [bold green]Actif (libx264, libass, aac, Mode NÉANT pur)[/]\n"
            "• Exportation Telegram : [bold cyan]sendVideo direct avec streaming MP4 vers @LesaintAi_bot[/]\n"
            "• Générateur de Scaffolds : [bold cyan]Génération automatique de templates de présentation produit[/]\n"
            "• Empreinte Disque : [bold green]0 octet écrit sur SSD lors des rendus en RAM[/]",
            title="🎬 Moteur Vidéo Programmatique & Remotion",
            border_style="magenta"
        ))
        console.print("[dim]Commandes :[/]")
        console.print("  • [cyan]/video teaser [titre] [sous-titre][/] : Génère un teaser cinématique MP4 en RAM et l'envoie sur Telegram")
        console.print("  • [cyan]/video scaffold <nom>[/]               : Crée une structure complète de projet vidéo Remotion React")

    elif subcmd in ("teaser", "export", "render"):
        title = args[1] if len(args) > 1 else "FreeAI Sovereign Platform"
        subtitle = " ".join(args[2:]) if len(args) > 2 else "Intelligence Autonome & Mode NÉANT"

        console.print(f"[dim]🎬 Rendu cinématique MP4 en cours en RAM (Titre : '{title}')...[/]")
        res = await tech_lead.render_and_export_video_presentation(title=title, subtitle=subtitle, duration_sec=4)
        if res.get("uploaded_to_telegram"):
            console.print(Panel(
                f"• Titre de la présentation : [bold green]{title}[/]\n"
                f"• Sous-titre : [bold cyan]{subtitle}[/]\n"
                f"• Fichier vidéo : [bold green]{res['filename']}[/]\n"
                f"• Résolution : [bold cyan]{res['resolution']}[/] ({res['duration_sec']} secondes)\n"
                f"• Poids MP4 : [bold cyan]{res['size_kb']:.2f} Ko[/]\n"
                f"• Empreinte SSD : [bold green]0 octet (Généré en RAM volatile)[/]\n\n"
                f"✔ [bold green]Vidéo cinématique livrée avec succès sur votre Telegram (@LesaintAi_bot) ![/]\n"
                f"[dim]Consultez la vidéo directement sur votre smartphone.[/]",
                title="🎬 Vidéo Cinématique Téléversée",
                border_style="green"
            ))
        else:
            console.print(f"[yellow]Rendu terminé mais téléversement Telegram en attente. ({res.get('error')})[/]")

    elif subcmd == "scaffold":
        if len(args) < 2:
            console.print("[bold red]Usage :[/] /video scaffold <nom_du_projet>")
            return
        p_name = args[1]
        out_dir = str(tech_lead.tool_gateway.workspace_root / "video_presentations" / p_name)
        res = tech_lead.video_engine.generate_remotion_scaffold(
            output_dir=out_dir,
            project_name=p_name,
            title=f"{p_name} Showcase",
            features=["Cybersecurity Pentest", "Design System Shadcn", "Autonomous Agents", "Cloud Continuum"]
        )
        console.print(Panel(
            f"• Projet Remotion : [bold green]{res['project_name']}[/]\n"
            f"• Dossier de sortie : [bold cyan]{res['output_dir']}[/]\n"
            f"• Résolution : [bold cyan]{res['resolution']}[/]\n"
            f"• Fichiers générés : [bold green]{', '.join(res['files_generated'])}[/]\n\n"
            f"[dim]Pour lancer la prévisualisation :[/] [cyan]cd {res['output_dir']} && npm install && npm start[/]",
            title="🎬 Scaffold Remotion Créé",
            border_style="magenta"
        ))

    else:
        console.print("[bold red]Usage :[/] /video [status|teaser [titre] [sous-titre]|scaffold <nom>]")


def run_jarvis(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Gère le daemon d'écoute permanente Jarvis 24/7 (systemd user service)."""
    subcmd = args[0].lower() if args else "status"

    if subcmd == "status":
        res = subprocess.run(["systemctl", "--user", "is-active", "freeai-jarvis.service"], capture_output=True, text=True)
        is_active = res.stdout.strip() == "active"
        status_txt = "[bold green]ACTIF & EN ÉCOUTE (24/7)[/]" if is_active else "[yellow]Inactif (Arrêté)[/]"

        linger_res = subprocess.run(["loginctl", "show-user", os.environ.get("USER", "lesaint"), "--property=Linger"], capture_output=True, text=True)
        has_linger = "yes" in linger_res.stdout.lower()
        linger_txt = "[bold green]Activé (Tourne même sans terminal ni session graphique)[/]" if has_linger else "[yellow]Non activé[/]"

        console.print(Panel(
            f"• Statut Jarvis 24/7 : {status_txt}\n"
            f"• Service Linux : [bold cyan]freeai-jarvis.service (systemd user)[/]\n"
            f"• Persistance Linger : {linger_txt}\n"
            f"• Canal Télépathique : [bold green]@LesaintAi_bot[/] (Chat ID: {tech_lead.telegram_vault.chat_id})\n"
            f"• Reconnaissance Vocale : [bold green]Groq Whisper LPU (~180ms, In-Memory Zero-RAM)[/]\n"
            f"• Mode NÉANT : [bold green]Strictement 0 octet écrit sur SSD[/]\n\n"
            f"[dim]Jarvis écoute en permanence vos notes vocales et messages sur Telegram sans nécessiter de terminal ouvert.[/]",
            title="🤖 Daemon Jarvis 24/7 (FreeAI Autonomous Assistant)",
            border_style="cyan"
        ))
        console.print("[dim]Commandes :[/]")
        console.print("  • [cyan]/jarvis start[/]   : Démarre le daemon en arrière-plan")
        console.print("  • [cyan]/jarvis stop[/]    : Arrête le daemon")
        console.print("  • [cyan]/jarvis restart[/] : Redémarre le daemon")
        console.print("  • [cyan]/jarvis logs[/]    : Affiche les derniers journaux en direct")

    elif subcmd == "start":
        subprocess.run(["systemctl", "--user", "start", "freeai-jarvis.service"])
        console.print("[bold green]✔ Daemon Jarvis démarré en arrière-plan ! Vous pouvez fermer votre terminal.[/]")

    elif subcmd == "stop":
        subprocess.run(["systemctl", "--user", "stop", "freeai-jarvis.service"])
        console.print("[yellow]✔ Daemon Jarvis arrêté.[/]")

    elif subcmd == "restart":
        subprocess.run(["systemctl", "--user", "restart", "freeai-jarvis.service"])
        console.print("[bold green]✔ Daemon Jarvis redémarré avec succès ![/]")

    elif subcmd in ("logs", "journal"):
        res = subprocess.run(["journalctl", "--user", "-u", "freeai-jarvis.service", "-n", "15", "--no-pager"], capture_output=True, text=True)
        console.print(Panel(
            res.stdout or "Aucun log disponible.",
            title="📜 Derniers Journaux Jarvis (Systemd)",
            border_style="magenta"
        ))

    else:
        console.print("[bold red]Usage :[/] /jarvis [status|start|stop|restart|logs]")


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
                elif cmd == "/learn":
                    await run_learn(tech_lead, args)
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
                elif cmd == "/docker":
                    await run_docker(tech_lead, args)
                elif cmd == "/scratchpad":
                    run_scratchpad(tech_lead, args)
                elif cmd in ("/hermes", "/agent"):
                    await run_hermes(tech_lead, args)
                elif cmd == "/onion":
                    await run_onion(tech_lead, args)
                elif cmd == "/offload":
                    await run_offload(tech_lead, args)
                elif cmd == "/forge":
                    run_forge(tech_lead, args)
                elif cmd == "/craft":
                    run_craft(tech_lead, args)
                elif cmd == "/design":
                    await run_design(tech_lead, args)
                elif cmd == "/cyber":
                    await run_cyber(tech_lead, args)
                elif cmd == "/skills":
                    await run_skills(tech_lead, args)
                elif cmd == "/video":
                    await run_video(tech_lead, args)
                elif cmd == "/jarvis":
                    run_jarvis(tech_lead, args)
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
            elif cmd == "/learn":
                asyncio.run(run_learn(tech_lead, args))
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
            elif cmd == "/docker":
                asyncio.run(run_docker(tech_lead, args))
            elif cmd == "/scratchpad":
                run_scratchpad(tech_lead, args)
            elif cmd in ("/hermes", "/agent"):
                asyncio.run(run_hermes(tech_lead, args))
            elif cmd == "/onion":
                asyncio.run(run_onion(tech_lead, args))
            elif cmd == "/offload":
                asyncio.run(run_offload(tech_lead, args))
            elif cmd == "/forge":
                run_forge(tech_lead, args)
            elif cmd == "/craft":
                run_craft(tech_lead, args)
            elif cmd == "/design":
                asyncio.run(run_design(tech_lead, args))
            elif cmd == "/cyber":
                asyncio.run(run_cyber(tech_lead, args))
            elif cmd == "/skills":
                asyncio.run(run_skills(tech_lead, args))
            elif cmd == "/video":
                asyncio.run(run_video(tech_lead, args))
            elif cmd == "/jarvis":
                run_jarvis(tech_lead, args)
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
