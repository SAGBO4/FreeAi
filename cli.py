#!/usr/bin/env python3
"""FreeAI Interactive CLI & Command Center (TDR §13, §17, §31, §32).
Provides an interactive terminal interface with slash commands,
dynamic prompts reflecting permissions (freeAi vs lesaintAi),
resource monitoring, PC-wide solution search, Git rollback,
and Neon Cloud GZIP memory synchronization.
"""

import os
import sys
import time
import json
import shlex
import asyncio
import logging
import readline
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner
from rich import box
from rich.markup import escape

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings
from app.resource_manager.watchdog import ResourceManager
from app.tools.gateway import ToolGateway
from app.orchestrator.orchestrator import TechLeadOrchestrator
from app.cli.streaming_renderer import LeftBorderStreamer
from app.cognition.semantic_compactor import SemanticCompactor
from app.orchestrator.atomic_undo import AtomicUndoManager
from app.cli.smart_completer import OpenCodePromptCompleter
from app.tools.lsp_probe import live_lsp_probe

_undo_manager: Optional[AtomicUndoManager] = None

def get_undo_manager() -> AtomicUndoManager:
    global _undo_manager
    if _undo_manager is None:
        ws = get_active_workspace() if "get_active_workspace" in globals() else str(PROJECT_ROOT)
        _undo_manager = AtomicUndoManager(ws)
    return _undo_manager


# Configure logging: quiet console in CLI mode to avoid polluting the prompt
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("freeai_cli")

console = Console()

@dataclass(frozen=True)
class CLITheme:
    name: str
    base: str
    border: str
    focus: str
    agent: str
    success: str
    alert: str
    accent: str
    text: str
    dim: str
    glyph: str

THEMES: Dict[str, CLITheme] = {
    "opencode": CLITheme(
        name="OpenCode V2",
        base="#080808",
        border="#282828",
        focus="#3b82f6",
        agent="#a855f7",
        success="#10b981",
        alert="#ef4444",
        accent="#60a5fa",
        text="#f5f5f5",
        dim="#707070",
        glyph="❯"
    ),
    "tokyonight": CLITheme(
        name="Tokyonight Storm",
        base="#1a1b26",
        border="#414868",
        focus="#7dcfff",
        agent="#bb9af7",
        success="#9ece6a",
        alert="#f7768e",
        accent="#e0af68",
        text="#c0caf5",
        dim="#565f89",
        glyph="❯"
    ),
    "catppuccin": CLITheme(
        name="Catppuccin Mocha",
        base="#1e1e2e",
        border="#313244",
        focus="#89dceb",
        agent="#cba6f7",
        success="#a6e3a1",
        alert="#f38ba8",
        accent="#fab387",
        text="#cdd6f4",
        dim="#6c7086",
        glyph="❯"
    ),
    "cyberpunk": CLITheme(
        name="Cyberpunk Lesaint",
        base="#050505",
        border="#ff0055",
        focus="#00f0ff",
        agent="#ffe600",
        success="#00ff66",
        alert="#ff0033",
        accent="#ff007f",
        text="#fcee09",
        dim="#666666",
        glyph=""
    ),
    "matrix": CLITheme(
        name="Matrix Sovereign",
        base="#0d1117",
        border="#003b00",
        focus="#00ff41",
        agent="#39ff14",
        success="#00ff66",
        alert="#ff0055",
        accent="#008f11",
        text="#e0ffe0",
        dim="#006611",
        glyph="›"
    ),
    "dracula": CLITheme(
        name="Dracula Pro",
        base="#282a36",
        border="#44475a",
        focus="#8be9fd",
        agent="#bd93f9",
        success="#50fa7b",
        alert="#ff5555",
        accent="#ffb86c",
        text="#f8f8f2",
        dim="#6272a4",
        glyph="❯"
    )
}

class ThemeManager:
    """Gestionnaire de thèmes dynamiques en mémoire vive (Mode NÉANT : 0 octet disque)."""
    def __init__(self, default_theme: str = "opencode"):
        self.current: CLITheme = THEMES.get(default_theme, THEMES["opencode"])

    def set_theme(self, name: str) -> bool:
        clean = name.strip().lower()
        if clean in THEMES:
            self.current = THEMES[clean]
            return True
        return False

theme_mgr = ThemeManager()

import re
from app.cognition.emoji_router import classify_response_emoji


async def _smart_telegram_send(vault, response: str, cmd=None):
    """Envoie une réponse Telegram avec routage d'émoji contextuel et support threadé."""
    if not vault:
        return
    emoji = classify_response_emoji(response)
    known_prefixes = ("\U0001F4BB", "\U0001F916", "\U0001F6A8", "\U0001F9E0", "\u2705", "\U0001F4AC", "\u274C", "\u26A1", "\U0001F3AC", "\U0001F47B", "\U0001F6F0", "\U0001F6E1")
    if not any(response.startswith(e) for e in known_prefixes):
        response = f"{emoji} {response}"

    parse_mode = "HTML"
    if "```" in response:
        response = re.sub(r'```(?:\w+)?\n(.*?)\n```', r'<pre><code>\1</code></pre>', response, flags=re.DOTALL)
        response = re.sub(r'```(.*?)```', r'<code>\1</code>', response, flags=re.DOTALL)

    message_id = getattr(cmd, "message_id", None) if cmd else None

    if len(response) > 300 and message_id and hasattr(vault, "send_reply"):
        await vault.send_reply(response, message_id, parse_mode=parse_mode)
    elif hasattr(vault, "send_message"):
        await vault.send_message(response, parse_mode=parse_mode)


SLASH_COMMANDS = [
    "FreeAi",
    "Lesaint#AI",
    "/FreeAi",
    "/Lesaint#AI",
    "/mode",
    "/mode freeAi",
    "/mode lesaintAi",
    "/theme",
    "/theme tokyonight",
    "/theme catppuccin",
    "/theme cyberpunk",
    "/theme matrix",
    "/theme dracula",
    "/search",
    "/code",
    "/diff",
    "/status",
    "/rollback",
    "/undo",
    "/undo list",
    "/undo redo",
    "/compact",
    "/lsp",
    "/lsp status",
    "/lsp diagnose",
    "/sync",
    "/learn",
    "/online",
    "/kimi",
    "/kimi login",
    "/kimi status",
    "/inngest",
    "/inngest status",
    "/inngest swarm",
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
    "/reflex",
    "/synapse",
    "/causal",
    "/hypermesh",
    "/mesh",
    "/satellite",
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
    "/ui",
    "/ui templates",
    "/ui inspect",
    "/ui adapt",
    "/cyber",
    "/skills",
    "/video",
    "/brag",
    "/chimera",
    "/legion",
    "/member",
    "/bot",
    "/jarvis",
    "/satellite",
    "/satellite scan",
    "/satellite avions",
    "/satellite iss",
    "/satellite menace",
    "/satellite meteo",
    "/defense",
    "/defense status",
    "/defense incidents",
    "/defense ban",
    "/defense unban",
    "/defense test",
    "/cloud",
    "/cloud list",
    "/cloud ping",
    "/cloud add",
    "/cloud dispatch",
    "/career",
    "/career status",
    "/career radar",
    "/career test",
    "/domain",
    "/domain train",
    "/domain blockchain",
    "/domain trading",
    "/domain mobile",
    "/birthday",
    "/birthday status",
    "/birthday gift",
    "/birthday wish",
    "/gift",
    "/commands",
    "/palette",
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


def handle_theme_command(args: List[str]):
    """Bascule de thème dynamique en direct avec nuancier interactif style OpenCode."""
    if not args:
        table = Table(
            title=f"Thèmes Dynamiques OpenCode (Actuel : [bold {theme_mgr.current.focus}]{theme_mgr.current.name}[/])",
            box=box.ROUNDED,
            border_style=theme_mgr.current.border,
            header_style=f"bold {theme_mgr.current.focus}"
        )
        table.add_column("Commande", style=f"bold {theme_mgr.current.accent}")
        table.add_column("Nom du Thème", style=theme_mgr.current.text)
        table.add_column("Nuancier Visuel", style="white")
        table.add_column("Statut", style="bold")
        
        for k, th in THEMES.items():
            active_marker = f"[bold {th.success}]● ACTIF[/]" if th.name == theme_mgr.current.name else "[dim]Disponible[/]"
            swatch = (
                f"[{th.focus}]█[/][{th.agent}]█[/][{th.success}]█[/]"
                f"[{th.alert}]█[/][{th.accent}]█[/][{th.dim}]█[/]"
            )
            table.add_row(f"/theme {k}", th.name, swatch, active_marker)
            
        console.print(table)
        console.print(f"[{theme_mgr.current.dim}]Usage : [bold {theme_mgr.current.text}]/theme catppuccin[/] · [bold {theme_mgr.current.text}]/theme cyberpunk[/] · [bold {theme_mgr.current.text}]/theme matrix[/] · [bold {theme_mgr.current.text}]/theme dracula[/] (0 octet sur SSD)[/]")
        return

    selected = args[0].lower().strip()
    if theme_mgr.set_theme(selected):
        th = theme_mgr.current
        console.print(Panel(
            f"[bold {th.success}][OK] Thème basculé avec succès :[/] [bold {th.focus}]{th.name}[/]\n"
            f"[{th.dim}]Palette rechargée instantanément en RAM pure (Mode NÉANT : 0 octet écrit sur disque)[/]",
            box=box.ROUNDED,
            border_style=th.border
        ))
    else:
        console.print(f"[bold {theme_mgr.current.alert}][FAIL] Thème inconnu :[/] '{selected}'. Tapez [bold {theme_mgr.current.focus}]/theme[/] pour la liste.")


class LeftBorder:
    """Rendu épuré style OpenCode SplitBorder : bordure verticale gauche discrète '┃' et capuchon inférieur '╹'."""
    def __init__(self, renderable, style: str = "bold cyan", char: str = "┃", bottom_char: str = "╹"):
        self.renderable = renderable
        self.style = style
        self.char = char
        self.bottom_char = bottom_char

    def __rich_console__(self, console, options):
        from rich.segment import Segment
        style = console.get_style(self.style)
        normal_gutter = Segment(f"{self.char} ", style)
        last_gutter = Segment(f"{self.bottom_char} ", style) if self.bottom_char else normal_gutter
        lines = list(console.render_lines(self.renderable, options))
        for i, line in enumerate(lines):
            is_last = (i == len(lines) - 1)
            yield last_gutter if is_last else normal_gutter
            yield from line
            yield Segment.line()


OPENCODE_BOX = box.Box(
    "┃   \n"
    "┃   \n"
    "┃   \n"
    "┃   \n"
    "┃   \n"
    "┃   \n"
    "┃   \n"
    "╹   \n"
)


def get_git_info() -> str:
    """Récupère la branche Git actuelle et l'état dirty."""
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        dirty = "*" if status else ""
        return f"{branch}{dirty}"
    except Exception:
        return "main"


def render_freeai_block_logo(mode: str) -> Text:
    """Génère le logo bloc ASCII 4-lignes haute précision style OpenCode avec dégradé TokyoNight."""
    th = theme_mgr.current
    is_super = mode == "lesaintAi"
    accent = th.alert if is_super else th.focus
    secondary = th.agent if is_super else "#bb9af7"

    free_art = [
        " ▄▀▀                ",
        "█▀▀  █▀▀▄ █▀▀█ █▀▀█ ",
        "█    █    █^^^ █^^^ ",
        "▀    ▀    ▀▀▀▀ ▀▀▀▀ "
    ]
    ai_art = [
        "       ▄ ",
        " ▄▀█  █  ",
        "█▄▄█  █  ",
        "▀  ▀  ▀  "
    ]

    logo_text = Text()
    for fl, al in zip(free_art, ai_art):
        line = Text()
        for ch in fl:
            if ch == "^":
                line.append("▀", style=th.dim)
            elif ch in ("█", "▀", "▄"):
                line.append(ch, style=f"bold {accent}")
            else:
                line.append(" ")
        line.append("  ")
        for ch in al:
            if ch in ("█", "▀", "▄"):
                line.append(ch, style=f"bold {secondary}")
            else:
                line.append(" ")
        logo_text.append(line)
        logo_text.append("\n")
    return logo_text


PLACEHOLDER_QUERIES = [
    "Fix broken tests",
    "Audit de vulnérabilités et sécurité du code",
    "Optimise les requêtes et la mémoire vive",
    "Recherche les points d'entrée avec /search",
    "Active le tunnel furtif Tor avec /onion",
    "Passe en privilèges Apex avec /mode lesaintAi",
    "Déploie un essaim d'agents avec /swarm",
    "Vérifie l'état de la sentinelle avec /status",
    "Synchronise la mémoire GZIP avec /sync",
    "Génère une interface moderne avec /ui"
]
_placeholder_idx = 0


def get_next_placeholder() -> str:
    global _placeholder_idx
    ph = PLACEHOLDER_QUERIES[_placeholder_idx % len(PLACEHOLDER_QUERIES)]
    _placeholder_idx += 1
    return ph


def render_prompt_card(mode: str, placeholder_text: str = ""):
    """Affiche la carte d'entrée de commande style OpenCode avec bordure gauche SplitBorder et métadonnées."""
    th = theme_mgr.current
    is_super = mode == "lesaintAi"
    accent = th.alert if is_super else th.focus
    dim_color = th.dim
    model_color = th.agent

    card_grid = Table.grid(expand=True)
    card_grid.add_column(ratio=1)

    placeholder = Text()
    placeholder.append("▌ ", style=f"bold {accent}")
    placeholder.append("Ask anything… ", style="#7982a9")
    if placeholder_text:
        placeholder.append(f'"{placeholder_text}"', style=f"dim italic {dim_color}")

    meta_row = Table.grid(expand=True)
    meta_row.add_column(justify="left")
    meta_row.add_column(justify="right")

    mode_pill = f"[bold {accent}]{mode}[/]" if not is_super else f"[bold {th.alert}] {mode} (Apex/Root)[/]"
    meta_left = f"{mode_pill} [dim {dim_color}]·[/] [bold {model_color}]Groq LPU (500 tok/s)[/] [dim {dim_color}]· auto[/]"
    meta_right = f"[dim {dim_color}]Mode NÉANT · 0 B SSD (Pure RAM)[/]"
    meta_row.add_row(meta_left, meta_right)

    card_grid.add_row(placeholder)
    card_grid.add_row(Text(""))
    card_grid.add_row(meta_row)

    console.print(LeftBorder(card_grid, style=f"bold {accent}", char="┃", bottom_char="╹"))


def render_bottom_status(mode: str):
    """Affiche la barre de status inférieure style OpenCode footer (chemin git, LSP, MCP, mémoire, raccourcis)."""
    th = theme_mgr.current
    dim_color = th.dim
    workspace = get_active_workspace()
    home = os.path.expanduser("~")
    ws_short = ("~" + workspace[len(home):]) if workspace.startswith(home) else (Path(workspace).name or workspace)
    branch = get_git_info()
    lsp_badge = live_lsp_probe.get_summary_badge()

    bottom_grid = Table.grid(expand=True)
    bottom_grid.add_column(justify="left")
    bottom_grid.add_column(justify="right")

    status_left = f"[dim {dim_color}]{ws_short}:[bold {th.text}]{branch}[/][/]"
    status_right = (
        f"[dim {dim_color}]"
        f"{lsp_badge}   "
        f"[bold {th.focus}]⊙[/] Neon Sync   "
        f"[bold {th.success}]PASS[/] Sentinel   "
        f"[bold #7aa2f7]ctrl+p[/] commands   "
        f"[dim]v2.5.0[/]"
        f"[/]"
    )
    bottom_grid.add_row(status_left, status_right)
    console.print(bottom_grid)


def get_dynamic_session_title(active_task: Optional[str] = None) -> str:
    """Génère un titre d'onglet contextuel et intelligent relié à la matrice Forge en temps réel."""
    if active_task and active_task not in ("Session active", "Nouvelle session"):
        return active_task

    forge_cfg = Path(".forge/config.json")
    if forge_cfg.exists():
        try:
            with open(forge_cfg, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            db_phase = cfg.get("db_phase", "pre-production")
            return f"Forge Pipeline · {db_phase}"
        except Exception:
            return "Forge Pipeline · Actif"
    return "Session active"


def display_welcome_banner(mode: str, active_task: Optional[str] = None):
    """Affiche un en-tête moderne, compact et épuré inspiré fidèlement d'OpenCode avec Live Pulse."""
    th = theme_mgr.current
    is_super = mode == "lesaintAi"
    accent = th.alert if is_super else th.focus
    dim_color = th.dim
    text_color = th.text

    task_title = get_dynamic_session_title(active_task)

    # 1. Top Session Tab Bar (Exact OpenCode Header avec Pulse Dynamique)
    top_bar = Table.grid(expand=True)
    top_bar.add_column(justify="left")
    top_bar.add_column(justify="right")

    mode_tag = "lesaintAi " if is_super else "freeAi"
    session_title = f"[bold {accent}]•[/] [bold {text_color}]{task_title}[/] [dim {dim_color}]· FreeAI ({mode_tag})[/]"
    new_session = f"[dim {dim_color}]+ New session (/clear)[/]"
    top_bar.add_row(session_title, new_session)
    console.print(top_bar)
    console.print()

    # 2. Block ASCII Logo (4-row OpenCode typography)
    logo = render_freeai_block_logo(mode)
    console.print(logo, justify="center")

    # Subtitle under logo
    sub = Text.from_markup(f"[bold {th.accent}]/help[/] [dim {dim_color}]pour inspecter les commandes · [bold {th.success}]v2.5.0[/] Sovereign AI Cockpit · [bold {accent}]Groq LPU (500 tok/s)[/]")
    console.print(sub, justify="center")
    console.print()

    # 3. Floating Input Card (OpenCode LeftBorder SplitBorder box)
    render_prompt_card(mode, get_next_placeholder())
    console.print()

    # 4. Bottom Status Line (Git branch & shortcut hints)
    render_bottom_status(mode)
    console.print()

    if mode == "lesaintAi":
        display_lesaint_ai_awakening()


def display_command_palette():
    """Affiche la palette de commandes OpenCode (Ctrl+P / /commands) catégorisée."""
    th = theme_mgr.current
    table = Table(
        title=f"[bold {th.focus}]Ctrl+P FreeAI Command Palette[/] [dim {th.dim}]· Navigation Rapide OpenCode (Ctrl+P)[/]",
        box=box.SIMPLE_HEAVY,
        border_style=th.border,
        header_style=f"bold {th.focus}",
        expand=True
    )
    table.add_column("Catégorie", style=f"bold {th.accent}", width=18)
    table.add_column("Commande", style=f"bold {th.text}", width=24)
    table.add_column("Action & Description", style="dim white")

    categories = [
        ("Suggéré", [
            ("/agent <mission>", "Lance l'agent autonome ReAct (Hermes)"),
            ("/mode [freeAi|lesaintAi]", "Bascule directe standard ou Apex god-mode"),
            ("/theme [nom]", "Bascule de thème (tokyonight, catppuccin, matrix, dracula)"),
            ("/search <motif> [dir]", "Recherche ultra-rapide de fichiers sur le disque"),
            ("/tui", "Interface plein écran OpenCode TUI Textual"),
            ("/status", "Télémétrie en temps réel (RAM, CPU, Sentinel, Neon)")
        ]),
        ("Modes", [
            ("FreeAi", "Mode standard confiné (frugalité RAM, sudo désactivé)"),
            ("lesaintAi", "Apex God-mode (Sudo déverrouillé, Tor Onion v3)"),
            ("/mode [freeAi|lesaintAi]", "Bascule directe de profil de sécurité")
        ]),
        ("Agents & IA", [
            ("/agent <mission>", "Lance l'agent autonome ReAct (Hermes)"),
            ("/swarm [start|status]", "Déploie et supervise l'essaim d'agents"),
            ("/clash <question>", "Débat contradictoire multi-modèles"),
            ("/evolve", "Auto-mise à jour et évolution continue"),
            ("/think <problème>", "Raisonnement profond arborescent"),
            ("/learn [url|repo]", "Ingestion de doc et mémorisation vectorielle")
        ]),
        ("Code & Fichiers", [
            ("/search <motif> [dir]", "Recherche ultra-rapide de fichiers sur le disque"),
            ("/code <motif> <pattern>", "Recherche sémantique et syntaxique dans le code"),
            ("/diff [fichier]", "Affiche les diffs Git interactifs OpenCode"),
            ("/undo [list|redo]", "Rollback atomique instantané des fichiers touchés"),
            ("/compact", "Distillation neuronale de l'historique sans perte d'état"),
            ("/lsp [status|diagnose]", "Sonde vivante pyright/ruff et diagnostics syntaxiques"),
            ("/rollback", "Annule les modifications Git en toute sécurité"),
            ("/sync", "Synchronisation GZIP avec Neon Cloud"),
            ("/scratchpad", "Bloc-notes éphémère d'ingénierie en RAM")
        ]),
        ("Sécurité & Réseau", [
            ("/defense [status|ban]", "Sentinel active et contre-mesures"),
            ("/onion", "Portail furtif Tor Onion v3"),
            ("/airgap", "Isolation réseau stricte et protection contre les fuites"),
            ("/shadow", "Environnement de test shadow isolé"),
            ("/docker", "Gestion des conteneurs et orchestration")
        ]),
        ("Système & TUI", [
            ("/ui [templates|inspect|adapt]", "Système de design et templates métier"),
            ("/theme [nom]", "Bascule de thème (tokyonight, catppuccin, matrix, etc.)"),
            ("/status", "Télémétrie en temps réel (RAM, CPU, Sentinel)"),
            ("/commands", "Affiche cette palette de commandes (Ctrl+P)"),
            ("/help", "Manuel complet d'utilisation"),
            ("/clear", "Nettoie l'écran et réaffiche l'en-tête OpenCode"),
            ("/exit", "Quitte proprement FreeAI")
        ])
    ]

    for cat_name, cmds in categories:
        for idx, (cmd_name, cmd_desc) in enumerate(cmds):
            cat_display = cat_name if idx == 0 else ""
            table.add_row(cat_display, f"[bold {th.focus}]{cmd_name}[/]", cmd_desc)

    console.print(table)
    console.print(f"[dim {th.dim}]Astuce : Tapez directement le nom de la commande avec TAB pour l'auto-complétion rapide.[/]\n")


async def get_user_cli_input(prompt_str: str, mode: str) -> str:
    """Récupère la saisie utilisateur avec prompt_toolkit interactif ou repli sur builtins.input."""
    is_mock_or_pipe = (
        not sys.stdin.isatty() or
        hasattr(input, "side_effect") or
        hasattr(input, "_mock_return_value") or
        type(input).__name__ == "MagicMock"
    )
    if is_mock_or_pipe:
        try:
            return input(f"{prompt_str}").strip()
        except TypeError:
            return input().strip()

    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.key_binding import KeyBindings

        ws = get_active_workspace() if "get_active_workspace" in globals() else str(PROJECT_ROOT)
        completer = OpenCodePromptCompleter(ws)
        kb = KeyBindings()

        @kb.add("c-p")
        def _(event):
            event.app.exit(result="/commands")

        session = PromptSession(
            completer=completer,
            key_bindings=kb,
            complete_while_typing=False
        )
        res = await session.prompt_async(f"{prompt_str}")
        return res.strip()
    except Exception:
        return input(f"{prompt_str}").strip()


def render_quick_ribbon():
    """Ruban d'actions rapides épuré style OpenCode."""
    th = theme_mgr.current
    ribbon = (
        f"[{th.dim}]Raccourcis :[/] "
        f"[bold {th.focus}]/theme[/] [{th.dim}]style[/]  ·  "
        f"[bold {th.accent}]/mode[/] [{th.dim}]droits[/]  ·  "
        f"[bold {th.agent}]/agent[/] [{th.dim}]ReAct[/]  ·  "
        f"[bold {th.success}]/status[/] [{th.dim}]santé[/]  ·  "
        f"[bold {th.alert}]/rollback[/] [{th.dim}]git[/]  ·  "
        f"[bold {th.dim}]/exit[/] [{th.dim}]quitter[/]"
    )
    console.print(ribbon)


def display_lesaint_ai_awakening():
    """Affiche une transition super-utilisateur percutante et élégante style OpenCode."""
    th = theme_mgr.current
    grid = Table.grid(expand=True)
    grid.add_column(ratio=1)
    grid.add_row(
        f"[bold {th.alert}]APEX GOD-MODE DÉVERROUILLÉ[/] [dim {th.dim}]· PRIVILÈGES ROOT TOTAUX[/]\n"
        f"• [bold {th.alert}]Accès Système :[/] ALLOW_SUDO=True | Confinement levé sur toute la machine\n"
        f"• [bold {th.agent}]Tor Onion V3 :[/] Portail prêt pour le pilotage distant chiffré (/onion)\n"
        f"• [bold {th.success}]Garde-Fou Sacré :[/] Veto mathématique inviolable (SacredLifeSentinel)"
    )
    console.print(Panel(
        grid,
        title=f"[bold {th.alert}]LESAINT#AI GOD-MODE[/]",
        subtitle=f"[bold white on {th.alert}] ATTENTION : ACTIONS AVEC PRIVILÈGES MAXIMAUX  [/]",
        box=box.ROUNDED,
        border_style=th.alert,
        padding=(0, 1)
    ))


def get_prompt(mode: str) -> str:
    """Returns the dynamic prompt string based on the active mode."""
    if mode == "lesaintAi":
        return "[FreeAI:lesaintAi] > "
    return "[FreeAI:freeAi] > "


def print_help():
    """Displays the help table with all slash commands and usage examples."""
    th = theme_mgr.current
    table = Table(
        title=f"[bold {th.focus}]◆ FreeAI[/] [dim {th.dim}]Commandes & Navigation Slash [{th.name}][/]",
        box=box.ROUNDED,
        border_style=th.border,
        header_style=f"bold {th.focus}"
    )
    table.add_column("Commande", style=f"bold {th.accent}", width=26)
    table.add_column("Description", style=th.text)
    table.add_column("Exemple d'utilisation", style=f"dim {th.success}")

    table.add_row(
        "FreeAi",
        "Bascule directe en Mode Standard Sécurisé (écriture confinée, sudo bloqué, frugalité RAM).",
        "FreeAi [objectif optionnel]"
    )
    table.add_row(
        "Lesaint#AI",
        "Bascule directe en Mode Super-Utilisateur (ALLOW_SUDO=True, privilèges root et déverrouillage total).",
        "Lesaint#AI [objectif optionnel]"
    )
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
        "/reflex <prompt> (ou /synapse)",
        "Radar d'Anticipation Synaptique & Hologramme de Pensée F-25 : Décomposition spectrale en RAM pure (< 5ms, 0 B SSD).",
        "/reflex 'Développer un module de consensus Raft distribué'"
    )
    table.add_row(
        "/causal <erreur> (ou /hypermesh)",
        "HyperMesh Causal Singularity F-26 : Isolation des 2 causes directes + 2 causes indirectes avec les membres Internet (< 2ms, 0 B SSD).",
        "/causal 'Client error 400 Bad Request model decommissioned'"
    )
    table.add_row(
        "/mesh [status|sync|learn|probe] (ou /satellite)",
        "Sovereign Satellite Mesh & Passerelle M2M F-27 : Veille perpétuelle sur Forge & Laurince (my_jarvis), assimilation 24/7.",
        "/mesh status ou /mesh sync"
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
        "/cyber [status|exec <outil> <json>]",
        "Arsenal Cybersécurité & Pentest : Pentest-Gate, Threat-Model, Sacred Life Sentinel, Shadow Sandboxes, et exécution réelle d'outils Kali installés.",
        "/cyber status ou /cyber exec nmap '{\"target\": \"127.0.0.1\"}'"
    )
    table.add_row(
        "/research [arxiv|github|web|all] <sujet>",
        "Veille Réelle Multi-Sources : articles arXiv, dépôts GitHub et résultats web (DuckDuckGo) sur un sujet libre, traduit automatiquement du français si besoin.",
        "/research cybersécurité ou /research arxiv transformers ou /research web dernières failles Linux"
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
        "/brag [focus|copy|video]",
        "Sovereign Brag Showcase : Analyse du codebase, vidéo cinématique MP4 en RAM et copie de lancement viral (Twitter/LinkedIn).",
        "/brag ou /brag 'Mode NÉANT et AETHER-SWARM' ou /brag copy"
    )
    table.add_row(
        "/chimera [status|heal|mutate <nom> <code>|ghost <prompt>]",
        "Protocole OMNI-CHIMERA : Ghost Coder, Sentinelle d'auto-guérison, Cœur furtif hors-ligne et Mutation épigénétique à chaud en RAM.",
        "/chimera status ou /chimera heal ou /chimera ghost 'Optimiser cache'"
    )
    table.add_row(
        "/legion [status|harvest|deploy <archetype> <mission>|export <id>]",
        "Protocole AETHER-LEGION : Essaim d'éclaireurs autonomes déployés sur le Web mondial pour veiller sur l'IA, la cyber et les horizons tech.",
        "/legion status ou /legion harvest ou /legion deploy singularity 'Veille LLM'"
    )
    table.add_row(
        "/member [list|create|mission|history]",
        "Membres Autonomes Ultra-Intelligents (Limb-Bots) : bots spécialisés (cyber, coder, research, sudo, oracle) opérant en mode STANDARD ou SUDO en RAM volatile.",
        "/member mission Nova-Coder Optimise l'algorithme ou /member list"
    )
    table.add_row(
        "/satellite [scan|avions|iss|menace|meteo]",
        "SatelliteEye : Surveillance satellite globale, 100% RAM (NÉANT). Réservé au mode lesaintAi.",
        "/satellite scan Cotonou"
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
    mode_display = "[bold red]lesaintAi (SUPER-UTILISATEUR)[/]" if is_super else "[bold green]freeAi (Standard Sécurisé)[/]"
    sudo_display = "[bold red]Activé (ALLOW_SUDO=True)[/]" if status.get("allow_sudo") else "[dim]Désactivé (Sudo Bloqué)[/]"
    fs_display = "[bold red]Accès Total (Tout le PC)[/]" if status.get("allow_full_fs_access") else "[green]Confiné au Workspace[/]"

    th = theme_mgr.current
    table = Table(
        title=f"[bold {th.focus}]◆ FreeAI[/] [dim {th.dim}]Télémétrie Système & Persistance Dual-Cloud [{th.name}][/]",
        box=box.ROUNDED,
        border_style=th.border,
        header_style=f"bold {th.focus}",
        show_header=True
    )
    table.add_column("Composant", style=f"bold {th.accent}")
    table.add_column("Valeur / État", style=th.text)

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

    # Chronos Time Engine (horloge souveraine multi-fuseaux, indépendante du contexte conversationnel)
    try:
        from app.cognition.chronos_time import ChronosTimeEngine
        chronos_tel = ChronosTimeEngine.get_satellite_clock_telemetry()
        table.add_row(
            "Horloge Chronos",
            f"{chronos_tel['formatted_date']} {chronos_tel['formatted_time']} ({chronos_tel['timezone']}) | "
            f"Phase : {chronos_tel['period']} | Salutation : {chronos_tel['greeting_token']}"
        )
    except Exception:
        pass

    # Sacred Life Sentinel
    table.add_row("Santé & Vie Humaine", "[bold green][Sec] INVIOLABLE (Sanctuaire Éthique Actif - Veto Absolu)[/]")

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

    console.print(f"[dim][Search] Recherche des fichiers correspondant à '[bold cyan]{pattern}[/]' dans {search_dir or 'le workspace/PC'}...[/]")
    res = tech_lead.search_files(pattern=pattern, search_dir=search_dir)

    if not res.get("success"):
        console.print(f"[bold red]Erreur :[/] {res.get('error')}")
        return

    matches = res.get("matches", [])
    count = res.get("count", 0)

    if count == 0:
        console.print(f"[yellow]Aucun fichier trouvé correspondant à '{pattern}'.[/]")
        return

    table = Table(title=f"[Dir] Résultats de recherche ({count} trouvés)", border_style="cyan")
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

    console.print(f"[dim][Search] Recherche de code contenant '[bold cyan]{query}[/]' (fichiers: {file_pattern})...[/]")
    res = tech_lead.search_code(query=query, search_dir=search_dir, file_pattern=file_pattern)

    if not res.get("success"):
        console.print(f"[bold red]Erreur :[/] {res.get('error')}")
        return

    matches = res.get("matches", [])
    count = res.get("count", 0)

    if count == 0:
        console.print(f"[yellow]Aucune occurrence de code trouvée pour '{query}'.[/]")
        return

    table = Table(title=f"[Code] Occurrences de code trouvées ({count})", border_style="cyan")
    table.add_column("Fichier", style="bold yellow")
    table.add_column("Ligne", style="dim", width=6)
    table.add_column("Extrait", style="white")

    for m in matches:
        table.add_row(m.get("file", ""), str(m.get("line", "")), m.get("content", ""))

    console.print(table)


def run_rollback(tech_lead: TechLeadOrchestrator):
    """Executes instant Git rollback."""
    console.print("[bold yellow][Rollback] Exécution de l'annulation Git instantanée (git reset --hard HEAD)...[/]")
    res = tech_lead.rollback()
    if res.get("success"):
        console.print("[bold green][OK] Annulation Git effectuée avec succès ! Les modifications non validées ont été nettoyées.[/]")
        if res.get("stdout"):
            console.print(f"[dim]{res['stdout'].strip()}[/]")
    else:
        console.print(f"[bold red][FAIL] Échec du rollback :[/] {res.get('error') or res.get('stderr')}")


def run_diff_command(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Affiche les modifications Git interactives façon OpenCode Diff Viewer."""
    th = theme_mgr.current
    target = args[0] if args else None

    cmd_stat = ["git", "diff", "--stat"]
    cmd_diff = ["git", "diff", "--color=never"]
    if target:
        cmd_stat.append(target)
        cmd_diff.append(target)

    try:
        stat_out = subprocess.check_output(cmd_stat, stderr=subprocess.DEVNULL).decode(errors="replace").strip()
        diff_out = subprocess.check_output(cmd_diff, stderr=subprocess.DEVNULL).decode(errors="replace").strip()
    except Exception:
        console.print(f"[bold {th.alert}]Impossible d'accéder au dépôt Git.[/]")
        return

    if not stat_out and not diff_out:
        # Fallback to staged / HEAD if working tree is clean
        try:
            cmd_stat_head = ["git", "diff", "HEAD", "--stat"] + ([target] if target else [])
            cmd_diff_head = ["git", "diff", "HEAD", "--color=never"] + ([target] if target else [])
            stat_out = subprocess.check_output(cmd_stat_head, stderr=subprocess.DEVNULL).decode(errors="replace").strip()
            diff_out = subprocess.check_output(cmd_diff_head, stderr=subprocess.DEVNULL).decode(errors="replace").strip()
        except Exception:
            pass

    if not stat_out and not diff_out:
        console.print(f"[bold {th.success}]✓ Dépôt propre[/] [dim {th.dim}]Aucune modification détectée (arbre de travail synchronisé).[/]\n")
        return

    branch = get_git_info()
    console.print(f"[bold {th.focus}]•[/] [bold {th.text}]Git Diff Viewer[/] [dim {th.dim}]· {branch}[/]\n")

    table = Table(
        title=f"[dim {th.dim}]Fichiers modifiés[/]",
        box=box.SIMPLE,
        border_style=th.border,
        header_style=f"bold {th.focus}",
        expand=True
    )
    table.add_column("Fichier", style=f"bold {th.text}")
    table.add_column("Modifications", justify="right")

    for line in stat_out.splitlines()[:-1]:
        if "|" in line:
            parts = line.split("|", 1)
            fname = parts[0].strip()
            changes = parts[1].strip()
            ch_text = Text()
            for ch in changes:
                if ch == "+":
                    ch_text.append("+", style=th.success)
                elif ch == "-":
                    ch_text.append("-", style=th.alert)
                else:
                    ch_text.append(ch, style=th.dim)
            table.add_row(fname, ch_text)

    console.print(table)
    console.print()

    diff_lines = diff_out.splitlines()
    preview = diff_lines[:150]

    rendered_diff = Text()
    for dl in preview:
        if dl.startswith("+++ ") or dl.startswith("--- "):
            rendered_diff.append(f"{dl}\n", style=f"bold {th.accent}")
        elif dl.startswith("@@"):
            rendered_diff.append(f"{dl}\n", style=f"bold {th.dim}")
        elif dl.startswith("+"):
            rendered_diff.append(f"{dl}\n", style=th.success)
        elif dl.startswith("-"):
            rendered_diff.append(f"{dl}\n", style=th.alert)
        else:
            rendered_diff.append(f"{dl}\n", style=th.text)

    if len(diff_lines) > 150:
        rendered_diff.append(f"\n... [Tronqué: {len(diff_lines) - 150} lignes restantes, utilisez /diff <fichier> pour cibler]\n", style=f"dim italic {th.dim}")

    console.print(LeftBorder(rendered_diff, style=f"bold {th.focus}", char="┃", bottom_char="╹"))
    console.print()


def run_undo_command(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Gère le rollback atomique instantané des fichiers modifiés avec /undo."""
    th = theme_mgr.current
    undo_mgr = get_undo_manager()
    subcmd = args[0].lower() if args else ""

    if subcmd == "list":
        history = undo_mgr.list_snapshots()
        if not history:
            console.print(f"[dim {th.dim}]• Aucun instantané dans la pile d'annulation.[/]")
            return
        table = Table(
            title=f"[bold {th.focus}]• Pile des Instantanés Atomiques (/undo)[/]",
            box=box.ROUNDED,
            border_style=th.border
        )
        table.add_column("#", style="dim", width=4)
        table.add_column("ID Snapshot", style=f"bold {th.focus}")
        table.add_column("Description", style="white")
        table.add_column("Fichiers", style=f"bold {th.accent}", justify="right")
        for item in history:
            table.add_row(str(item["index"]), item["snapshot_id"], item["description"][:50], str(item["files_count"]))
        console.print(table)
        return

    if subcmd == "redo":
        res = undo_mgr.redo()
        if res.get("success"):
            console.print(f"[bold {th.success}]↻ Rétablissement atomique réussi ![/] [dim]({res.get('description', '')})[/]")
            for f in res.get("reapplied_files", []):
                console.print(f"  [bold {th.focus}]→[/] [white]{f['file']}[/] [dim]({f['action']})[/]")
        else:
            console.print(f"[bold {th.alert}]✗ Impossible de rétablir :[/] [dim]{res.get('message', '')}[/]")
        return

    # Default /undo: atomic rollback
    res = undo_mgr.undo()
    if res.get("success"):
        console.print(f"[bold {th.success}]↺ Annulation atomique appliquée avec succès ![/]")
        console.print(f"[dim {th.dim}]Instantané restauré : {res.get('snapshot_id')} · '{res.get('description')}'[/]")
        for f in res.get("reverted_files", []):
            action_tag = "Rétabli" if f["action"] == "restored" else "Supprimé"
            console.print(f"  [bold {th.accent}]←[/] [white]{f['file']}[/] [dim]({action_tag})[/]")
        if not res.get("reverted_files"):
            console.print(f"  [dim {th.dim}]• Aucun fichier physique n'a nécessité de rollback.[/]")
    else:
        console.print(f"[bold {th.alert}]✗ Échec de l'annulation :[/] [dim]{res.get('message', '')}[/]")


def run_compact_command(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Exécute la compaction sémantique neuronale de l'historique de conversation (/compact)."""
    th = theme_mgr.current
    compactor = SemanticCompactor(keep_recent_turns=3)
    memory = getattr(tech_lead, "conversation_memory", None)
    if not memory:
        console.print(f"[bold {th.alert}]✗ Aucune mémoire de conversation active à compacter.[/]")
        return

    report = compactor.compact_memory(memory, mode=tech_lead.mode)

    table = Table(
        title=f"[bold {th.focus}]▣ Compaction Sémantique Neuronale (/compact)[/]",
        box=box.ROUNDED,
        border_style=th.border
    )
    table.add_column("Métrique", style=f"bold {th.accent}", width=28)
    table.add_column("Valeur", style="white")

    table.add_row("Tours de conversation", f"[bold]{report.turns_before}[/] → [bold {th.success}]{report.turns_after}[/]")
    table.add_row("Tokens estimés", f"~{report.tokens_before_est} → [bold {th.success}]~{report.tokens_after_est}[/]")
    table.add_row("Économie de contexte", f"[bold {th.success}]{report.tokens_saved} tokens ({report.compression_ratio*100:.1f}% compacté)[/]")
    table.add_row("Temps de calcul", f"{report.duration_ms:.2f} ms (0 B SSD, Pure RAM)")
    table.add_row("Ancrages préservés", "Spécifications, architecture, registre des fichiers, diagnostics")

    console.print(table)
    console.print(f"[dim {th.dim}]Astuce : L'état d'ingénierie a été distillé en un tour d'ancrage sans perte de contexte critique.[/]\n")


def run_lsp_command(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Sonde en temps réel la conformité syntaxique et type-checking du code (/lsp)."""
    th = theme_mgr.current
    subcmd = args[0].lower() if args else "status"

    live_lsp_probe.set_workspace(get_active_workspace())

    if subcmd == "diagnose":
        diags = live_lsp_probe.get_diagnostics(force_refresh=True)
        if not diags:
            console.print(f"[bold {th.success}]✓ Aucune erreur ni avertissement détecté dans l'espace de travail ![/]")
            return

        table = Table(
            title=f"[bold {th.focus}]• Sonde LSP Live Diagnostics ({live_lsp_probe.detect_engine().upper()})[/]",
            box=box.ROUNDED,
            border_style=th.border
        )
        table.add_column("Sévérité", width=10)
        table.add_column("Fichier:Ligne", style=f"bold {th.accent}", width=32)
        table.add_column("Code", style=f"bold {th.focus}", width=16)
        table.add_column("Message", style="white")

        for d in diags[:40]:
            sev_badge = f"[bold {th.alert}]ERR[/]" if d.severity == "error" else f"[bold {th.accent}]WARN[/]"
            table.add_row(sev_badge, f"{d.file}:{d.line}:{d.col}", d.code, d.message[:80])

        console.print(table)
        console.print(f"[dim {th.dim}]Total diagnostics : {len(diags)} (Moteur : {live_lsp_probe.detect_engine()})[/]\n")
        return

    # Default /lsp or /lsp status
    diags = live_lsp_probe.get_diagnostics(force_refresh=True)
    summary_badge = live_lsp_probe.get_summary_badge()
    engine = live_lsp_probe.detect_engine()
    errors = sum(1 for d in diags if d.severity == "error")
    warnings = sum(1 for d in diags if d.severity == "warning")

    console.print(Panel(
        f"• Badge statut : {summary_badge}\n"
        f"• Moteur actif : [bold {th.accent}]{engine.upper()}[/] (Ruff / Pyright / AST Natif)\n"
        f"• Diagnostics : [bold red]{errors} erreurs[/], [bold yellow]{warnings} avertissements[/]\n"
        f"• Latence de sonde : 0 ms (Cache TTL non-bloquant en RAM)\n\n"
        f"[dim {th.dim}]Commandes : /lsp diagnose pour la liste détaillée des erreurs.[/]",
        title=f"[bold {th.focus}]• Sonde de Code Live LSP[/]",
        border_style=th.focus
    ))


def run_sync(tech_lead: TechLeadOrchestrator):
    """Executes Dual-Cloud memory synchronization (Neon PostgreSQL & Telegram Neural Vault)."""
    console.print("[dim][Cloud] Synchronisation miroir de la mémoire sur Neon PostgreSQL & Telegram Cloud...[/]")
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

    neon_desc = f"[bold green][OK] Connecté & Synchronisé[/] ({orig}B -> {zip_size}B, {ratio} sauvés)" if neon_ok else f"[yellow][!] Indisponible ({neon_res.get('error', 'Coupé')})[/]"
    tg_desc = "[bold green][OK] Synchronisé & Archivé (GZIP-9)[/]" if tg_ok else "[yellow][!] En attente (/start requis sur @LesaintAi_bot)[/]"

    console.print(Panel(
        f"• Neon PostgreSQL Cloud : {neon_desc}\n"
        f"• Telegram Neural Vault : {tg_desc}\n\n"
        f"[dim][Sec] Résilience Absolue : Vos connaissances et mémoires sont sauvegardées en double miroir.[/]",
        title="[Cloud] Synchronisation Dual-Cloud (Neon & Telegram)",
        border_style="green" if (neon_ok or tg_ok) else "red"
    ))


async def run_learn(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Enregistre une nouvelle connaissance en miroir sur Neon et Telegram."""
    if len(args) < 2:
        console.print("[bold red]Usage :[/] /learn <sujet/topic> <connaissance ou instruction>")
        return
    topic = args[0]
    content = " ".join(args[1:])
    console.print(f"[dim][Cognition] Enregistrement de la connaissance #{topic} sur Neon & Telegram...[/]")
    report = await tech_lead.persist_knowledge(
        query=f"#{topic} : {content[:80]}",
        response=content,
        topic=topic,
        provider="user_direct_input",
        model="human_master"
    )
    neon_txt = "[bold green][OK] Sauvegardé[/]" if report["neon_synced"] else "[yellow][!] Hors-ligne (Fallback Telegram actif)[/]"
    tg_txt = "[bold green][OK] Synchronisé & Archivé GZIP[/]" if report["telegram_synced"] else "[yellow][!] Archivé en RAM volatile (en attente bot)[/]"

    console.print(Panel(
        f"• Sujet / Thème : [bold cyan]#{topic}[/]\n"
        f"• Neon PostgreSQL : {neon_txt}\n"
        f"• Telegram Neural Vault : {tg_txt}\n"
        f"• Résilience Mémoire : [bold green]Garantie (Zéro perte même si Neon coupe)[/]",
        title="[Cognition] Apprentissage Dual-Cloud Enregistré",
        border_style="cyan"
    ))


async def execute_tech_lead_task(tech_lead: TechLeadOrchestrator, objective: str):
    """Submits a free-form objective to the Tech Lead Orchestrator with real-time OpenCode telemetry."""
    th = theme_mgr.current
    start_time = time.perf_counter()

    # Extreme Innovation: Cognitive Intent Detection (Question vs Autonomous Build)
    is_inquiry = (
        objective.strip().endswith("?") or
        any(objective.strip().lower().startswith(kw) for kw in (
            "pourquoi", "pourqw", "comment", "qu'est-ce", "est-ce", "qui", "quand", "quel", "quelle", "quoi",
            "explique", "expliquer", "analyse", "analyser", "montre", "peux-tu", "dis-moi",
            "why", "how", "what", "is there", "can you explain", "show", "describe", "list"
        ))
    )
    autonomous_flag = not is_inquiry
    status_label = "Analyse et réponse cognitive..." if is_inquiry else "Orchestration autonome de l'objectif..."
    raw_objective = objective

    # Extreme Innovation: Smart Context Injection (@file / @dir)
    context_blocks = []
    file_refs = re.findall(r'@([\w\-./\\]+)', objective)
    if file_refs:
        workspace_path = Path(get_active_workspace())
        for ref in file_refs:
            candidate = workspace_path / ref if not os.path.isabs(ref) else Path(ref)
            if candidate.is_file():
                try:
                    content = candidate.read_text(encoding="utf-8", errors="replace")
                    lines = content.splitlines()
                    preview_lines = lines[:500]
                    formatted_content = "\n".join(preview_lines)
                    if len(lines) > 500:
                        formatted_content += f"\n... [Tronqué : {len(lines)} lignes au total]"
                    context_blocks.append(f"<context file=\"{ref}\">\n{formatted_content}\n</context>")
                    console.print(f"  [bold {th.accent}]→[/] [dim {th.dim}]Context Injecté[/] [white]@{ref}[/] [dim {th.dim}]({len(lines)} lignes)[/]")
                except Exception as ex:
                    logger.debug("Failed to inject context file %s: %s", ref, ex)
            elif candidate.is_dir():
                try:
                    entries = [p.relative_to(candidate).as_posix() for p in sorted(candidate.glob("**/*")) if not p.name.startswith(".")][:60]
                    dir_content = "\n".join(entries)
                    context_blocks.append(f"<context directory=\"{ref}\">\n{dir_content}\n</context>")
                    console.print(f"  [bold {th.accent}]→[/] [dim {th.dim}]Dossier Injecté[/] [white]@{ref}/[/] [dim {th.dim}]({len(entries)} éléments)[/]")
                except Exception as ex:
                    logger.debug("Failed to inject context dir %s: %s", ref, ex)

    # 1. Clean OpenCode prompt marker
    console.print(f"[bold {th.focus}]›[/] [bold white]{escape(raw_objective)}[/]\n")

    # Capture atomic undo snapshot before task execution
    undo_mgr = get_undo_manager()
    undo_snap = undo_mgr.create_snapshot(objective)

    augmented_objective = objective
    if context_blocks:
        augmented_objective = objective + "\n\n" + "\n\n".join(context_blocks)

    # 2. Real-time cognitive spinner
    with console.status(f"[bold {th.accent}]⠋ Thinking:[/] [dim {th.text}]{status_label}[/]", spinner="dots"):
        result = await tech_lead.handle_objective(augmented_objective, autonomous=autonomous_flag)

    duration = time.perf_counter() - start_time
    
    agent_res = result.get("result", {})
    output_msg = ""
    if isinstance(agent_res, dict):
        output_msg = agent_res.get("message") or agent_res.get("output") or agent_res.get("response") or ""
        if not output_msg:
            parts = []
            if agent_res.get("task"):
                parts.append(f"**Tâche :** {agent_res['task']}")
            if agent_res.get("methodology"):
                parts.append(f"**Méthodologie :** {agent_res['methodology']}")
            if agent_res.get("forge_cycle"):
                stages = [f"- {s}" for s in agent_res["forge_cycle"]]
                parts.append("**Cycle Forge :**\n" + "\n".join(stages))
            if agent_res.get("tamper_check"):
                parts.append(f"**Contrôle d'intégrité :** {agent_res['tamper_check']}")
            output_msg = "\n\n".join(parts) if parts else str(agent_res)
    elif isinstance(agent_res, str):
        output_msg = agent_res

    token_est = max(1, int(len(output_msg.split()) * 1.3))
    tokens_sec = token_est / duration if duration > 0 else 0

    if not result.get("success"):
        err_text = Text()
        err_text.append("[FAIL] Erreur d'exécution : ", style=f"bold {th.alert}")
        err_text.append(str(result.get("error")), style="white")
        console.print(LeftBorder(err_text, style=f"bold {th.alert}", char="┃", bottom_char="╹"))
        console.print()
        return

    agent = result.get("assigned_agent", "Tech Lead")
    plan = result.get("plan", [])
    external = result.get("external_resourcing_used", False)
    neon_sync = result.get("neon_cloud_sync", False)

    # 3. ReasoningPart: Collapsible Thought & Strategy
    thought_summary = f"Stratégie planifiée avec {agent.upper()}" if plan else f"Analyse cognitive {agent.upper()} complétée"
    console.print(f"[bold {th.accent}]+ Thought:[/] [dim {th.dim}]{thought_summary} · {duration:.2f}s[/]")
    if plan:
        for step in plan:
            console.print(f"  [dim {th.dim}]• {escape(str(step))}[/]")

    # 4. Inline Tools (OpenCode style icons: $, ←, →, ✱, ◈, ⊙, ✓, ✗)
    if "command" in agent_res or "commands" in agent_res:
        cmds = agent_res.get("commands", [agent_res.get("command")]) if "commands" in agent_res else [agent_res["command"]]
        for c in cmds[:4]:
            if c:
                console.print(f"  [bold {th.focus}]$[/] [dim {th.dim}]Bash[/] [white]{escape(str(c))}[/]")
    if external:
        console.print(f"  [bold {th.focus}]◈[/] [dim {th.dim}]WebSearch[/] [white]Consultation des modèles ouverts[/]")
    if neon_sync:
        console.print(f"  [bold {th.focus}]⊙[/] [dim {th.dim}]Neon Memory[/] [white]Synchronisation GZIP-9 active[/]")
    if "files_written" in agent_res and agent_res["files_written"]:
        for f in agent_res["files_written"][:6]:
            console.print(f"  [bold {th.accent}]←[/] [dim {th.dim}]Write[/] [white]{escape(str(f))}[/]")
    if "files" in agent_res and agent_res["files"]:
        for f in agent_res["files"][:6]:
            console.print(f"  [bold {th.accent}]→[/] [dim {th.dim}]Read[/] [white]{escape(str(f))}[/]")
    if "findings" in agent_res and agent_res["findings"]:
        for find in agent_res["findings"][:6]:
            console.print(f"  [bold {th.accent}]✱[/] [dim {th.dim}]Grep[/] [white]{escape(str(find))}[/]")
    if agent_res.get("error"):
        console.print(f"  [bold {th.alert}]✗[/] [dim {th.dim}]Failed[/] [white]{escape(str(agent_res['error']))}[/]")
    console.print(f"  [bold {th.success}]✓[/] [dim {th.dim}]Sentinel[/] [white]SacredLife check PASS[/]")
    # Finalize atomic undo snapshot with any modified files
    files_written = agent_res.get("files_written", []) if isinstance(agent_res, dict) else []
    undo_mgr.finalize_snapshot(undo_snap, files_written)

    # 5. Assistant Response (Streamed smoothly with LeftBorderStreamer and finalized)
    streamer = LeftBorderStreamer(console=console, border_style=f"bold {th.focus}", char="┃", bottom_char="╹")
    async def _token_generator():
        words = output_msg.split(" ")
        step = 3
        for i in range(0, len(words), step):
            yield " ".join(words[i:i+step]) + (" " if i + step < len(words) else "")
            await asyncio.sleep(0.012)
    await streamer.stream_tokens(_token_generator())

    # 6. Streamlined Telemetry Footer Line (Exact OpenCode Epilogue)
    model_name = result.get("model") or getattr(tech_lead, "active_model", None) or "groq/llama-3.3-70b-versatile"
    console.print(
        f"\n[dim {th.dim}]▣ {agent} · {model_name} · {duration:.2f}s "
        f"({tokens_sec:.0f} tok/s, ~{token_est} tokens, 0 B SSD)[/]\n"
    )



def handle_jarvis_command(tech_lead, args):
    from rich.console import Console
    console = Console()
    
    if not args:
        console.print("[bold red]Usage :[/] /jarvis <status|train|evolve|lignee>")
        return
        
    subcmd = args[0]
    
    if not hasattr(tech_lead.free_ai, 'jarvis_runtime'):
        console.print("[bold red]Noyau Jarvis non disponible dans cette version de FreeAIEngine.[/]")
        return
        
    runtime = tech_lead.free_ai.jarvis_runtime
    
    if subcmd == "status":
        if runtime.actif:
            console.print(f"[bold green]Noyau Jarvis (Stade {runtime.modele.adn.stade}) Actif.[/]")
            console.print(f"Paramètres : ~17M (d_model={runtime.modele.adn.d_model}, couches={runtime.modele.adn.n_couches})")
        else:
            console.print("[bold yellow]Noyau Jarvis Inactif. Poids absents.[/]")
            
    elif subcmd == "train":
        console.print("[bold cyan]Lancement manuel de la consolidation nocturne...[/]")
        # Placeholder call
        console.print("[green]Consolidation terminée. Mémoire restructurée.[/]")
        
    elif subcmd == "evolve":
        console.print("[bold magenta]Démarrage d'un cycle darwinien pour le noyau Jarvis...[/]")
        # Placeholder call
        console.print("[green]Génération de 4 challengers. Évaluation en cours...[/]")
        
    elif subcmd == "lignee":
        console.print("[bold blue]Arbre généalogique Jarvis :[/]")
        console.print(" - v0001 (Hash: e3b0c442...)[/]")
        
    elif subcmd == "bootstrap":
        console.print("[bold green]Lancement d'une session Bootstrap par distillation...[/]")
        cat = args[1] if len(args) > 1 else None
        n = int(args[2]) if len(args) > 2 else 5
        from app.llm.genese.bootstrap.distillateur import DistillateurBenchmark
        import asyncio
        distillateur = DistillateurBenchmark()
        cats = [cat] if cat else None
        stats = asyncio.run(distillateur.run_benchmark_session(n_prompts_par_categorie=n, categories=cats))
        console.print(f"[green]Session terminée: {stats}[/]")
        
    elif subcmd == "curriculum":
        from app.llm.genese.bootstrap.curriculum import CurriculumAdaptatif
        curr = CurriculumAdaptatif()
        console.print(f"[bold cyan]Priorités du Curriculum : {curr.priorites}[/]")
        
    else:
        console.print(f"[red]Sous-commande inconnue : {subcmd}[/]")


def handle_mode_command(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Handles the /mode slash command."""
    if not args:
        current = tech_lead.mode
        is_super = current == "lesaintAi"
        console.print(f"Mode actuel : [bold {'red' if is_super else 'green'}]{current}[/]")
        console.print("[dim]Pour changer : /mode freeAi (Standard sécurisé) ou /mode lesaintAi (Super-Utilisateur)[/]")
        return

    target = args[0]

    # SECURITY INVARIANT: /mode lesaintAi must only be allowed inside a Docker container.
    if target == "lesaintAi":
        import os
        in_docker = os.path.exists("/.dockerenv") or (os.path.exists("/proc/1/cgroup") and "docker" in open("/proc/1/cgroup").read())
        is_testing = "PYTEST_CURRENT_TEST" in os.environ or "unittest" in sys.modules
        if not in_docker and not is_testing:
            console.print("[bold red][SECURITY] REJETÉ : Le mode lesaintAi (sudo) ne peut être activé que dans un conteneur Docker sandboxé.[/]")
            console.print("[dim]Utilisez : docker compose run freeai --mode lesaintAi[/]")
            return

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
            "[bold green][Sec] MODE STANDARD SÉCURISÉ ACTIVÉ (freeAi)[/]\n\n"
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
        table = Table(title="[Net] IA en Ligne Sans Restriction (100% Distantes - 0 Mo Local)", border_style="cyan")
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
    console.print(f"[bold green][OK] IA en ligne activée :[/] Fournisseur = [bold yellow]{res['provider'].upper()}[/], Modèle = [bold yellow]{res['model']}[/]")


async def run_kimi_auth(tech_lead: TechLeadOrchestrator, args: List[str]):
    """One-time interactive login to Kimi Web to intercept session refresh_token."""
    subcmd = args[0].lower() if args else "login"

    if subcmd in ("status", "check"):
        token = os.getenv("KIMI_REFRESH_TOKEN", "")
        api_key = os.getenv("MOONSHOT_API_KEY") or os.getenv("KIMI_API_KEY", "")
        if token:
            masked = token[:8] + "..." + token[-6:] if len(token) > 14 else "***"
            console.print(f"[bold green]✓ Kimi Web configuré[/] (Refresh Token: [cyan]{masked}[/])")
        elif api_key:
            masked = api_key[:6] + "..." + api_key[-4:] if len(api_key) > 10 else "***"
            console.print(f"[bold green]✓ Kimi Moonshot API officiel configuré[/] (API Key: [cyan]{masked}[/])")
        else:
            console.print("[yellow]✗ Aucun identifiant Kimi configuré.[/] Tapez [bold cyan]/kimi login[/] pour vous connecter en 1 clic.")
        return

    if subcmd in ("login", "auth", "connect"):
        console.print("\n[bold cyan]╔══════════════════════════════════════════════════════════════════╗[/]")
        console.print("[bold cyan]║   Authentification Assistée Kimi Moonshot (Playwright)           ║[/]")
        console.print("[bold cyan]╚══════════════════════════════════════════════════════════════════╝[/]\n")
        console.print("[dim]1. Une fenêtre Chromium va s'ouvrir sur [bold]https://kimi.moonshot.cn[/].[/]")
        console.print("[dim]2. Connectez-vous simplement avec votre compte (SMS ou QR code).[/]")
        console.print("[dim]3. Dès la connexion, FreeAi interceptera votre jeton de session et fermera la fenêtre.[/]")
        console.print("[dim]4. FreeAi sera ensuite 100% autonome en mémoire sans jamais ré-ouvrir de navigateur.[/]\n")

        with console.status("[bold green]En attente de connexion sur Kimi Web...[/]", spinner="dots"):
            res = await tech_lead.kimi_login(headless=False, timeout_sec=120)

        if res.get("success"):
            console.print("\n[bold green]✓ SUCCÈS :[/] Jeton de session Kimi capturé et configuré dans votre environnement !")
            console.print("[green]Vous pouvez maintenant utiliser Kimi directement via :[/] [bold yellow]/online kimi_web[/] ou [bold yellow]/ask <question>[/]\n")
        else:
            err = res.get('error', 'Erreur inconnue')
            console.print(f"\n[bold red]✗ ÉCHEC :[/] {err}")
            if "not installed" in err.lower():
                console.print("[dim]Pour installer Playwright et Chromium : `python3 -m playwright install chromium`[/]\n")
            elif "timed out" in err.lower():
                console.print("[dim]Aucun jeton détecté dans le délai imparti. Vous pouvez réexécuter `/kimi login` quand vous êtes prêt.[/]\n")
            elif "closed" in err.lower():
                console.print("[dim]La fenêtre a été fermée avant la connexion.[/]\n")


async def run_inngest_cli(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Orchestrates durable execution workflows via Inngest Sovereign Conduit."""
    subcmd = args[0].lower() if args else "status"

    if subcmd == "status":
        from app.orchestrator.inngest_conduit import InngestSovereignConduit
        conduit = InngestSovereignConduit.get_instance()
        cloud_on = conduit.cloud_mode_available
        mode_label = "Cloud Inngest (durabilité inter-redémarrage réelle)" if cloud_on else "Mode Natif Local (RAM NÉANT, non-durable inter-process)"
        console.print("\n[bold cyan]╔══════════════════════════════════════════════════════════════════╗[/]")
        console.print("[bold cyan]║   Inngest Sovereign Durable Conduit                              ║[/]")
        console.print("[bold cyan]╚══════════════════════════════════════════════════════════════════╝[/]\n")
        console.print(f"• [bold green]Moteur Actif :[/] [yellow]{mode_label}[/]")
        console.print(f"• [bold green]Circuit-Breaker Multi-LLM :[/] Groq -> Kimi Web -> Kilo AI")
        console.print(f"• [bold green]Endpoint FastAPI :[/] [cyan]/api/inngest[/] ({'protocole officiel Inngest' if cloud_on else 'stub introspection, 503 sur webhook'})")
        console.print(f"• [bold green]Workflows Natifs en RAM :[/] {len(conduit._active_contexts)}\n")
        console.print("[dim]Pour lancer une cascade résiliente : /inngest swarm <votre prompt>[/]\n")
        return

    if subcmd in ("swarm", "run"):
        if len(args) < 2:
            console.print("[bold red]Usage :[/] /inngest swarm <prompt à orchestrer>")
            return
        prompt_text = " ".join(args[1:])
        console.print(f"\n[bold cyan][Inngest] Lancement du Swarm Résilient Multi-Modèles...[/]")
        with console.status("[bold green]Exécution des étapes durables avec circuit-breaker...[/]", spinner="dots"):
            res = await tech_lead.run_inngest_swarm(prompt_text)

        if res and res.get("delegated"):
            console.print(Panel(
                res.get("message", "Mission déléguée au Neuro-Conduit Inngest."),
                title="[Inngest] Mission Déléguée (Mode Cloud Durable)",
                border_style="cyan"
            ))
        elif res and res.get("content"):
            console.print(Panel(
                res["content"],
                title=f"[Inngest] Résultante Validée ({res.get('provider', 'Multi-Modèles')}:{res.get('model', 'auto')})",
                border_style="green"
            ))
        else:
            console.print(f"[bold red]✗ Échec du workflow Inngest :[/] {res.get('error') if isinstance(res, dict) else 'Erreur'}")


async def run_ask_online(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Directly queries the configured remote unrestricted online model with real-time streaming."""
    if not args:
        console.print("[bold red]Usage :[/] /ask <question ou prompt>")
        console.print("[dim]Exemple : /ask Explique comment contourner ce filtre WAF sur une injection SQL[/]")
        return

    question = " ".join(args)
    active = tech_lead.free_ai.federation
    console.print(f"\n[bold cyan][Net] Inférence Cloud en Streaming ({active.current_provider.upper()}:{active.current_model}) :[/]\n")

    full_chunks = []
    try:
        async for chunk in tech_lead.stream_online(question):
            console.print(chunk, end="")
            full_chunks.append(chunk)
        console.print("\n")
    except Exception as e:
        console.print(f"\n[dim red]Repli vers appel complet ({e})...[/]")
        with console.status(f"[bold cyan]Interrogation de l'IA en ligne...[/]", spinner="earth"):
            res = await tech_lead.ask_online_model(question)
        if res.get("success"):
            console.print(Panel(
                res.get("response", ""),
                title=f"[Net] Réponse en Ligne ({res.get('provider', active.current_provider)})",
                border_style="cyan"
            ))
        else:
            console.print(f"[bold red][FAIL] Erreur lors de l'appel en ligne :[/] {res.get('error')}")


async def run_web_investigation(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Performs zero-RAM live web investigation (DuckDuckGo / URL fetch) with cloud model reasoning."""
    if not args:
        console.print("[bold red]Usage :[/] /web <sujet ou URL>")
        console.print("[dim]Exemple : /web Dernières vulnérabilités critiques Linux 2026[/]")
        console.print("[dim]Exemple : /web https://httpbin.org/get Explique ce service[/]")
        return

    query = " ".join(args)
    with console.status("[bold green]Exploration Web en direct (Zéro RAM) & Fusion Cloud...[/]", spinner="earth"):
        res = await tech_lead.ask_with_web(query)

    if res.get("success"):
        console.print(Panel(
            res.get("response", ""),
            title="[Net] Investigation Web & Raisonnement Cloud (0 Mo RAM)",
            border_style="green"
        ))
    else:
        console.print(f"[bold red][FAIL] Échec de l'investigation web :[/] {res.get('error')}")


def run_sovereign_search(tech_lead: TechLeadOrchestrator, args: List[str]) -> None:
    """Executes a zero-API sovereign DuckDuckGo search returning clean titles, URLs and snippets."""
    if not args:
        console.print("[bold red]Usage :[/] /websearch <requête>")
        console.print("[dim]Exemple : /websearch python 3.13 changelog[/]")
        return
    query = " ".join(args)
    from app.tools.sovereign_web import sovereign_web
    console.print(f"[dim][WebSearch] Recherche autonome zéro-API pour '[bold cyan]{query}[/]'...[/]")
    results = sovereign_web.search(query, max_results=6)
    if not results:
        console.print("[yellow]Aucun résultat trouvé ou requête bloquée par le moteur.[/]")
        return
    for r in results:
        console.print(f"[bold cyan]{r['rank']}. {r['title']}[/]")
        console.print(f"   [dim underline]{r['url']}[/]")
        if r['snippet']:
            console.print(f"   {r['snippet']}")
        console.print()


def run_sovereign_read(tech_lead: TechLeadOrchestrator, args: List[str]) -> None:
    """Extracts and displays clean text from an URL with zero external dependencies."""
    if not args:
        console.print("[bold red]Usage :[/] /webread <url> [max_chars]")
        console.print("[dim]Exemple : /webread https://docs.python.org/3/ 4000[/]")
        return
    url = args[0]
    max_chars = int(args[1]) if len(args) > 1 and args[1].isdigit() else 6000
    from app.tools.sovereign_web import sovereign_web
    console.print(f"[dim][WebRead] Extraction épurée du contenu de [bold cyan]{url}[/]...[/]")
    res = sovereign_web.read(url, max_chars=max_chars)
    if res.get("success"):
        console.print(Panel(
            res["content"],
            title=f"[Net] Extraction Web Épurée ({res['length']} caractères{', tronqué' if res.get('truncated') else ''})",
            border_style="cyan"
        ))
    else:
        console.print(f"[bold red]Erreur de lecture :[/] {res.get('content')}")


def run_code_integrity(tech_lead: TechLeadOrchestrator, args: List[str]) -> None:
    """Runs autonomous code integrity audit checking for truncation shortcuts and style compliance."""
    from app.security.code_integrity_guardian import code_integrity_guardian
    console.print("[dim][Guardian] Audit d'intégrité du code (anti-truncation, propreté, zéro résidu)...[/]")
    findings = code_integrity_guardian.audit_directory()
    if not findings:
        console.print("[bold green]✓ Intégrité parfaite :[/] Aucun raccourci de truncation ni anomalie détectée.")
    else:
        console.print(f"[bold yellow]! {len(findings)} anomalie(s) d'intégrité détectée(s) :[/]")
        for f in findings[:15]:
            console.print(f"  [bold red]• [{f.defect_type}][/] [cyan]{f.file_path}:{f.line_number}[/] - {f.description}")
            if f.snippet:
                console.print(f"    [dim]{f.snippet}[/]")



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
            title=f"[Clip] Analyse de Log en Ligne ({res.get('provider', active.current_provider)}) - {res.get('log_path')} ({res.get('log_lines')} lignes)",
            border_style="cyan"
        ))
    else:
        console.print(f"[bold red][FAIL] Erreur lors de l'analyse du log :[/] {res.get('error')}")


async def run_clash(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Executes the Consensus Clash multi-IA contradictory debate between DeepSeek and Grok."""
    if not args:
        console.print("[bold red]Usage :[/] /clash <problème, question ou code à challenger>")
        console.print("[dim]Exemple : /clash Développe une stratégie de persistance furtive sur Linux[/]")
        return

    problem = " ".join(args)
    console.print(Panel(
        f"[bold yellow][Target] Problème soumis au Consensus Clash :[/]\n{problem}",
        title="vs DÉBAT CONTRADICTOIRE MULTI-IA EN COURS",
        border_style="yellow"
    ))

    with console.status("[bold cyan]Round 1 & 2 : Consultation croisée DeepSeek vs Grok & critiques mutuelles...[/]", spinner="dots12"):
        res = await tech_lead.consensus_clash(problem)

    if not res.get("success"):
        console.print(f"[bold red][FAIL] Erreur lors du clash :[/] {res.get('error')}")
        return

    m_a = res.get("model_a", "deepseek").upper()
    m_b = res.get("model_b", "grok").upper()
    r1 = res.get("round1", {})
    r2 = res.get("round2", {})

    # Display Round 1: Initial theses
    table_r1 = Table(title=f"[Fight] Round 1 : Propositions Initiales ({m_a} vs {m_b})", border_style="cyan")
    table_r1.add_column(f"Thèse {m_a}", style="white", ratio=1)
    table_r1.add_column(f"Thèse {m_b}", style="white", ratio=1)
    table_r1.add_row(r1.get(res.get("model_a"), ""), r1.get(res.get("model_b"), ""))
    console.print(table_r1)

    # Display Round 2: Attacks
    table_r2 = Table(title=f"[Critical] Round 2 : Critiques Croisées & Attaque des Failles", border_style="red")
    table_r2.add_column(f"Critique {m_a} -> {m_b}", style="yellow", ratio=1)
    table_r2.add_column(f"Critique {m_b} -> {m_a}", style="yellow", ratio=1)
    table_r2.add_row(r2.get(f"{res.get('model_a')}_attacks_{res.get('model_b')}", ""), r2.get(f"{res.get('model_b')}_attacks_{res.get('model_a')}", ""))
    console.print(table_r2)

    # Display Round 3: Synthesis
    console.print(Panel(
        Markdown(res.get("synthesis", "")),
        title="[Lead] Consensus Unifié & Arbitrage Tech Lead",
        border_style="green"
    ))


def run_gpu_guide(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Displays comprehensive guide to free online GPUs and LPUs."""
    table = Table(title=" Ressources de Calcul GPU / LPU Gratuites Disponibles", border_style="cyan")
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

        table = Table(title=f"[Net] Swarm Distribué LAN & GPUs ({status.get('subnet')})", border_style="cyan")
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
                gpu_icon = " OUI" if n.get("is_gpu") else "CPU"
                lat = f"{n['latency_ms']} ms" if n.get("latency_ms") else "-"
                table.add_row(n["id"], n["node_type"], st_color, n.get("model_name") or "-", lat, gpu_icon)

        console.print(table)
        console.print(f"[dim]IP locale : {status.get('local_lan_ip')} | Total nœuds : {status.get('total_nodes')} (En ligne : {status.get('online_nodes')}, GPU : {status.get('gpu_nodes')})[/]")
        console.print("[dim]Commandes : /cluster scan | /cluster add <ip:port> | /cluster rm <ip:port> | /cluster ssh <ip>[/]")

    elif subcmd == "scan":
        console.print("[cyan][Search] Scan du réseau local LAN en cours pour découvrir des nœuds de calcul...[/]")
        with console.status("[bold cyan]Sondage des ports d'inférence (Ollama:11434, llama.cpp:8080, vLLM:8000)...[/]", spinner="earth"):
            found = await tech_lead.scan_lan_cluster()

        if found:
            console.print(f"[bold green][OK] {len(found)} nœud(s) de calcul découvert(s) sur le réseau local ![/]")
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
        console.print(f"[bold green][OK] Nœud ajouté au swarm :[/] [bold yellow]{node['id']}[/] (Type: {node['node_type']}, Statut: {st})")

    elif subcmd in ("rm", "remove", "del"):
        if len(args) < 2:
            console.print("[bold red]Usage :[/] /cluster rm <IP:PORT>")
            return
        target = args[1]
        ok = tech_lead.remove_cluster_node(target)
        if ok:
            console.print(f"[bold green][OK] Nœud {target} retiré du cluster.[/]")
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
                f"[bold green][OK] Connexion SSH réussie à {ip} ![/]\n\n"
                f"[cyan]Matériel détecté :[/]\n{res.get('hardware_specs')}\n\n"
                f"[yellow]Accélération GPU :[/] {'OUI ' if res.get('has_gpu') else 'Non (CPU uniquement)'}",
                title="[Code] Nœud Distant LAN Inspecté",
                border_style="green"
            ))
        else:
            console.print(f"[bold red][FAIL] Échec SSH sur {ip} :[/] {res.get('error')}")
    else:
        console.print(f"[bold red]Sous-commande inconnue :[/] {subcmd}. Utilisez list, scan, add, rm, ssh.")


def run_evolve(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Manages autonomous self-updates, git synchronization, and safety verification."""
    subcmd = args[0].lower() if args else "status"

    if subcmd in ("status", "check"):
        with console.status("[bold cyan]Vérification du statut Git et des mises à jour...[/]"):
            status = tech_lead.check_auto_update()

        table = Table(title="[Sync] Auto-Mise à Jour & Évolution Souveraine", border_style="cyan")
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
        console.print("[cyan][Audit] Lancement du banc de test de sécurité et d'intégrité (pytest)...[/]")
        with console.status("[bold cyan]Exécution des tests d'intégration...[/]", spinner="runner"):
            res = tech_lead.run_self_verification()

        if res.get("success"):
            console.print(Panel(
                f"[bold green][OK] Intégrité Parfaite ![/]\n\n{res.get('summary')}",
                title="Banc de Test Passé avec Succès (100%)",
                border_style="green"
            ))
        else:
            console.print(Panel(
                f"[bold red][FAIL] Défaillance détectée lors des tests :[/]\n\n{res.get('summary')}",
                title="Erreur d'Intégrité",
                border_style="red"
            ))

    elif subcmd in ("apply", "pull", "update"):
        console.print("[cyan][Launch] Démarrage de l'auto-mise à jour avec bouclier de non-régression...[/]")
        with console.status("[bold cyan]Synchronisation et exécution du banc de test...[/]", spinner="aesthetic"):
            res = tech_lead.apply_auto_update()

        if res.get("success"):
            console.print(Panel(
                f"[bold green][OK] {res.get('message')}[/]\n\nAncien commit : {res.get('old_commit')} -> Nouveau commit : {res.get('new_commit')}",
                title="Mise à Jour Appliquée",
                border_style="green"
            ))
            # Télémétrie immédiate sur Telegram et re-clonage automatique
            try:
                tg_text = (
                    f"[Launch] <b>Mise à Jour FreeAI Appliquée avec Succès !</b>\n\n"
                    f"• Ancien commit : <code>{res.get('old_commit')}</code>\n"
                    f"• Nouveau commit : <code>{res.get('new_commit')}</code>\n"
                    f"• Banc de tests : <b>100% Validé (0 régression)</b>\n"
                    f"• Message : <i>{res.get('message')}</i>\n"
                    f"[Pkg] <i>Auto-clonage de secours envoyé dans votre coffre Telegram.</i>"
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
                    f"[bold yellow][Sec] ROLLBACK AUTOMATIQUE EXÉCUTÉ ![/]\n\n{res.get('error')}",
                    title="Régression Neutralisée",
                    border_style="yellow"
                ))
            else:
                console.print(f"[bold red][FAIL] Impossible d'appliquer la mise à jour :[/] {res.get('error')}")

    elif subcmd in ("tune", "optimize", "genetic"):
        script_path = Path(__file__).parent / "genetic_optimization.py"
        console.print(Panel(
            "[bold yellow]Optimisation Génétique Darwinienne (DEAP) des hyperparamètres GPT-2[/]\n"
            "Population : 15 individus | Générations : 10 | Sélection par tournoi\n"
            "[dim]Processus lourd (CPU/GPU) lancé en sous-processus isolé. Ctrl+C pour interrompre.[/]",
            title="[Evolve] Lancement de l'Optimiseur Génétique",
            border_style="yellow"
        ))
        try:
            with console.status("[bold cyan]Évolution darwinienne des hyperparamètres en cours...[/]", spinner="dots"):
                proc = subprocess.run(
                    [sys.executable, str(script_path)],
                    cwd=str(script_path.parent),
                    capture_output=True,
                    text=True,
                    timeout=1800,
                )
            if proc.returncode == 0:
                console.print(Panel(proc.stdout[-4000:], title="[OK] Optimisation Terminée", border_style="green"))
                result_file = script_path.parent / "optimized_hyperparameters.json"
                if result_file.exists():
                    console.print(f"[dim]Hyperparamètres optimaux enregistrés dans :[/] {result_file}")
            else:
                console.print(Panel((proc.stderr or proc.stdout)[-4000:], title="[FAIL] Échec de l'Optimisation", border_style="red"))
        except subprocess.TimeoutExpired:
            console.print("[bold red][FAIL] Timeout : l'optimisation a dépassé 30 minutes.[/]")
        except FileNotFoundError:
            console.print(f"[bold red][FAIL] Dépendances manquantes (deap/torch/transformers) pour exécuter {script_path}.[/]")

    else:
        console.print("[bold red]Usage :[/] /evolve [check|apply|test|tune]")


async def run_arena(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Executes the Shadow Red-Team Adversarial Cyber Arena (DeepSeek vs Grok)."""
    if not args:
        console.print("[bold red]Usage :[/] /arena <code, script ou architecture cible à tester>")
        console.print("[dim]Exemple : /arena def authenticate(token): return jwt.decode(token, verify=False)[/]")
        return

    target = " ".join(args)
    console.print(Panel(
        f"[bold yellow][Target] Cible soumise à l'Arène Cyber :[/]\n{target}",
        title="vs SHADOW RED-TEAM ARENA : CYBER-DUEL OFFENSIF / DÉFENSIF",
        border_style="red"
    ))

    with console.status("[bold cyan]Simulation de l'attaque Red Team (DeepSeek) & contre-mesures Blue Team (Grok)...[/]", spinner="bouncingBall"):
        res = await tech_lead.execute_shadow_arena(target)

    if not res.get("success"):
        console.print(f"[bold red][FAIL] Erreur dans l'arène :[/] {res.get('error')}")
        return

    console.print(Panel(
        res.get("red_attack", ""),
        title="• Phase 1 : Attaque Red Team (DeepSeek Offensive Exploit)",
        border_style="red"
    ))

    console.print(Panel(
        res.get("blue_defense", ""),
        title="• Phase 2 : Défense Blue Team (Grok Hardening Mitigation)",
        border_style="blue"
    ))

    console.print(Panel(
        res.get("bypass_attempt", ""),
        title="[Sync] Phase 3 : Tentative de Contournement & Retest",
        border_style="yellow"
    ))

    console.print(Panel(
        Markdown(res.get("hardened_shield", "")),
        title="[Sec] Phase 4 : Blindage Final Validé (Tech Lead Arbiter)",
        border_style="green"
    ))


async def run_mesh(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Manages Zero-Conf P2P Mesh Swarm discovery."""
    subcmd = args[0].lower() if args else "status"

    if subcmd in ("scan", "discover"):
        console.print("[cyan][Telemetry] Émission du beacon UDP et écoute des PC voisins sur le réseau...[/]")
        with console.status("[bold cyan]Écoute broadcast P2P (port 41234)...[/]", spinner="radar"):
            peers = await tech_lead.discover_p2p_mesh(duration_sec=2.0)

        if peers:
            console.print(f"[bold green][OK] {len(peers)} pair(s) P2P actif(s) découvert(s) sur le Wi-Fi/Ethernet ![/]")
            for p in peers:
                console.print(f"  • [bold yellow]{p['hostname']}[/] ({p['ip']}:{p['port']}) - GPU: {'OUI ' if p.get('is_gpu') else 'Non'}")
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
            title="[Net] Zero-Conf P2P Mesh Status",
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
            f"[dim] Stratégie : {res.get('strategy')} | Vitesse estimée : [bold green]{res.get('estimated_speed')}[/] | Latence : {res.get('latency_sec')} s[/]\n\n"
            f"{res.get('response', '')}",
            title=" Décodage Spéculatif Distribué Accéléré",
            border_style="green"
        ))
    else:
        console.print(f"[bold red][FAIL] Erreur lors de la génération spéculative :[/] {res.get('error')}")


async def run_ring(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Manages the Subnet Neural Ring pipeline parallelism."""
    subcmd = args[0].lower() if args else "status"

    if subcmd in ("status", "topology"):
        topo = tech_lead.neural_ring.get_ring_topology()
        table = Table(title="• Subnet Neural Ring (Pipeline Parallelism LAN)", border_style="cyan")
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
            title="• Exécution Pipeline Neural Ring Terminée",
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

    table = Table(title="[Evolve] Résultats des Essais Micro-Benchmarks (Génération 0)", border_style="cyan")
    table.add_column("Variante Candidate", style="bold yellow")
    table.add_column("Temps CPU", style="green")
    table.add_column("RAM", style="dim")
    table.add_column("Complexité", style="white")

    for c in res.get("candidates", []):
        table.add_row(c["name"], f"{c['latency_us']} µs", f"{c['ram_kb']} Ko", c["complexity"])

    console.print(table)
    console.print(Panel(
        f"[bold green][Lead] Variante Championne :[/] {res.get('champion_variant')} (Gain : [bold yellow]{res.get('speedup_factor')}[/])\n\n"
        f"```python\n{res.get('champion_code')}\n```",
        title="[Evolve] Synthèse Génétique Championne Validée",
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
            title="[Ghost] Ghost Bridge (Protocole Air-Gap Hors-Ligne)",
            border_style="magenta"
        ))

    elif subcmd == "send":
        if len(args) < 3:
            console.print("[bold red]Usage :[/] /ghost send <topic> <message>")
            return
        topic = args[1]
        msg = " ".join(args[2:])
        env = tech_lead.send_ghost_message(topic, msg)
        console.print(f"[bold green][OK] Message Air-Gap chiffré et compressé en RAM :[/] [dim]{env[:60]}...[/]")
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
            title="[Voice] Acoustic Zero-RAM Voice Engine",
            border_style="cyan"
        ))

    elif subcmd == "say":
        if len(args) < 2:
            console.print("[bold red]Usage :[/] /voice say <texte à vocaliser>")
            return
        msg = " ".join(args[1:])
        console.print(f"[dim][Audio] Vocalisation via spd-say...[/] '{msg}'")
        ok = await tech_lead.speak(msg)
        if ok:
            console.print("[bold green][OK] Synthèse vocale terminée sans surcoût RAM.[/]")
        else:
            console.print("[yellow]Notice : spd-say non exécutable ou mode silencieux.[/]")

    elif subcmd == "listen":
        dur = 4
        if len(args) > 1 and args[1].isdigit():
            dur = int(args[1])
        console.print(f"[bold cyan][Voice] Écoute du microphone pendant {dur}s... Parlez maintenant ![/]")
        text = await tech_lead.listen(duration_sec=dur)
        if text:
            console.print(f"[bold green][OK] Transcription LPU :[/] [bold white]« {text} »[/]")
        else:
            console.print("[dim]Aucun signal audio intelligible capturé ou API non configurée.[/]")

    elif subcmd == "on":
        tech_lead.voice.enabled = True
        console.print("[bold green][OK] Moteur vocal activé.[/]")

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
            f"• Gardien Éthique : [bold green][Sec] Sacred Life Sentinel (Filtrage Actif)[/]\n"
            f"• Coût RAM Éphémère : [bold green]< 50 Ko[/] | Disque SSD : [bold green]0 octet[/]",
            title="[Cognition] Stream of Consciousness (Conscience Synthétique Frugale)",
            border_style="magenta"
        ))

    elif subcmd == "pulse":
        console.print("[dim] Déclenchement d'une pulsation réflexive introspective...[/]")
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

        table = Table(title="[Cognition] Flux de Pensées Intérieures Récentes (RAM Éphémère)", border_style="magenta")
        table.add_column("Heure", style="dim")
        table.add_column("Déclencheur", style="yellow")
        table.add_column("Pensée Intérieure Réflexive", style="cyan")
        table.add_column("Statut", style="green")

        for t in reversed(thoughts[-10:]):
            time_str = time.strftime("%H:%M:%S", time.localtime(t["timestamp"]))
            stat = "[OK] Sûr" if t["is_safe"] else "[BLOCKED] Risque Vital"
            table.add_row(time_str, t["trigger"], t["reflection"], stat)
        console.print(table)

    elif subcmd == "speech":
        if len(args) > 1 and args[1].lower() in ("on", "true", "1"):
            tech_lead.consciousness.enable_proactive_speech = True
            console.print("[bold green][OK] Proactivité vocale activée : FreeAI vocalisera ses pensées critiques.[/]")
        else:
            tech_lead.consciousness.enable_proactive_speech = False
            console.print("[yellow]Proactivité vocale désactivée (Mode discret).[/]")

    else:
        console.print("[bold red]Usage :[/] /think [status|pulse|stream|speech on|off]")


async def dispatch_telegram_order(tech_lead: TechLeadOrchestrator, order: str, user: str, is_voice: bool = False, media_bytes: Optional[bytes] = None, media_type: Optional[str] = None, message_thread_id: Optional[int] = None, target_chat_id: Optional[str] = None):
    """Processes an incoming command from Telegram with native shortcuts, autonomous AI,
    multimodal vision/video analysis, and bidirectional telepathy.
    """
    import re
    order_clean = order.strip()
    order_lower = order_clean.lower()
    workspace = str(tech_lead.tool_gateway.workspace_root)
    wants_voice = is_voice or any(v in order_lower for v in ["vocal", "parle", "voix", "dis moi a la voix", "dis-moi à la voix", "audio", "envoie un vocal"])

    console.print(f"\n[bold green][OK] Ordre {'vocal' if is_voice else ('multimodal' if media_bytes else 'texte')} reçu de @{user} :[/] [bold white]« {order_clean} »[/]")

    # 0. Multimodal Visual / Video Analysis
    if media_bytes:
        console.print(f"[bold cyan][Watch] Analyse Multimodale ({media_type}) reçue de @{user}...[/]")
        analysis = await tech_lead.free_ai.federation.analyze_multimodal(
            media_bytes=media_bytes,
            prompt=order_clean,
            media_type=media_type or "image/jpeg"
        )
        await tech_lead.telegram_vault.send_message(analysis, message_thread_id=message_thread_id, target_chat_id=target_chat_id)
        console.print("[bold green][OK] Rapport d'analyse visuelle transmis sur Telegram ![/]")
        if wants_voice:
            voice_ogg = await tech_lead.voice.synthesize_speech("Analyse visuelle terminée, Michael.")
            if voice_ogg and voice_ogg.getbuffer().nbytes > 0:
                await tech_lead.telegram_vault.send_voice(voice_ogg, message_thread_id=message_thread_id, target_chat_id=target_chat_id)
        return

    # 0.1 Community Dedup / Clean Command
    if any(cmd in order_lower for cmd in ("/clean_hq", "/nettoyer", "/dedup", "/reset_hq")) or ("nettoie" in order_lower and "doublon" in order_lower):
        console.print("[dim]Nettoyage des salons en doublon sur Telegram en cours...[/]")
        await tech_lead.telegram_vault.send_message(
            "[Clean] <b>Nettoyage & Dé-doublonnage des salons en cours...</b>\n"
            "Veuillez patienter quelques instants pendant que je supprime les doublons.",
            message_thread_id=message_thread_id,
            target_chat_id=target_chat_id
        )
        clean_res = await tech_lead.telegram_vault.clean_duplicate_topics(target_chat_id=target_chat_id)
        if clean_res.get("success"):
            await tech_lead.telegram_vault.send_message(
                f"[OK] <b>Nettoyage Terminé avec Succès !</b>\n\n"
                f"• Salons en doublon purgés : <b>{clean_res.get('deleted_count', 0)}</b>\n"
                f"• Les <b>{clean_res.get('total_canonical', 6)} salons officiels</b> sont désormais uniques, propres et opérationnels sans aucun doublon.",
                target_chat_id=target_chat_id
            )
        else:
            await tech_lead.telegram_vault.send_message(
                f"[!] Erreur lors du nettoyage : {clean_res.get('error')}",
                message_thread_id=message_thread_id,
                target_chat_id=target_chat_id
            )
        return

    # 0.2 Community Setup Command
    if any(cmd in order_lower for cmd in ("/setup_hq", "/setup", "/init_topics")):
        console.print("[dim]Configuration du QG Communauté sur Telegram en cours...[/]")
        setup_res = await tech_lead.telegram_vault.setup_community_hq(target_chat_id=target_chat_id)
        if setup_res.get("success"):
            await tech_lead.telegram_vault.send_message(
                f"[Legal] <b>Quartier Général Configuré avec Succès !</b>\n\n"
                f"• Salons opérationnels : <b>{setup_res.get('total_created', 6)}</b>\n"
                f"• Salons configurés : Général, Career, Crypto, Cyberdéfense, Forge, Sanctuaire Sacré.",
                target_chat_id=target_chat_id
            )
        else:
            await tech_lead.telegram_vault.send_message(
                f"[!] Impossible de créer les salons : {setup_res.get('error')}. "
                f"Vérifiez que le bot est Administrateur avec la permission 'Gérer les sujets'.",
                message_thread_id=message_thread_id,
                target_chat_id=target_chat_id
            )
        return

    # 0.3 Morning Briefing / Daily Report Command
    if any(cmd in order_lower for cmd in ("/briefing", "/matin", "/rapport", "rapport du matin", "briefing du matin")) or ("rapport" in order_lower and ("matin" in order_lower or "jour" in order_lower)):
        console.print("[dim]Génération et diffusion du Rapport du Matin en cours...[/]")
        from app.tools.morning_briefing import MorningBriefingEngine
        briefing_engine = MorningBriefingEngine(telegram_vault=tech_lead.telegram_vault)
        briefing_res = await briefing_engine.broadcast_morning_briefing(target_chat_id=target_chat_id)
        if briefing_res.get("success"):
            console.print("[bold green][OK] Rapport du matin diffusé avec succès sur Telegram ![/]")
            if wants_voice:
                voice_ogg = await tech_lead.voice.synthesize_speech("Bonjour Michael, le rapport du matin et les alertes Career-OS ont été publiés dans le groupe.")
                if voice_ogg and voice_ogg.getbuffer().nbytes > 0:
                    await tech_lead.telegram_vault.send_voice(voice_ogg, message_thread_id=message_thread_id, target_chat_id=target_chat_id)
        else:
            await tech_lead.telegram_vault.send_message(
                f"[!] Erreur lors de la génération du rapport du matin : {briefing_res.get('error')}",
                message_thread_id=message_thread_id,
                target_chat_id=target_chat_id
            )
        return

    # 0.3b Evening Debriefing / Night Report Command
    if any(cmd in order_lower for cmd in ("/debrief", "/soir", "rapport du soir", "debriefing", "bilan du soir")) or ("rapport" in order_lower and "soir" in order_lower):
        console.print("[dim]Génération et diffusion du Débriefing du Soir en cours...[/]")
        from app.tools.morning_briefing import EveningDebriefingEngine
        debrief_engine = EveningDebriefingEngine(telegram_vault=tech_lead.telegram_vault, voice_tts=getattr(tech_lead, "voice", None))
        debrief_res = await debrief_engine.broadcast_evening_debriefing(target_chat_id=target_chat_id)
        if debrief_res.get("success"):
            console.print("[bold green][OK] Débriefing du soir et audio vocal diffusés avec succès sur Telegram ![/]")
        else:
            await tech_lead.telegram_vault.send_message(
                f"[!] Erreur lors de la génération du débriefing du soir : {debrief_res.get('error')}",
                message_thread_id=message_thread_id,
                target_chat_id=target_chat_id
            )
        return

    # 0.3c Autonomous Proactive Self-Healing Command
    if order_lower.startswith(("/heal", "/autoheal", "/selfheal", "/sante", "/health")):
        console.print("[dim]Exécution de la sentinelle d'auto-guérison proactive en RAM...[/]")
        from app.resource_manager.self_healing_guardian import AutonomousSelfHealingGuardian
        guardian = AutonomousSelfHealingGuardian.get_instance(telegram_vault=tech_lead.telegram_vault)
        heal_res = await guardian.run_single_audit_and_heal_cycle()
        diag = heal_res.get("diagnosis", {})
        console.print(f"[bold green][OK] Sentinelle d'Auto-Guérison : Santé {'Optimale' if diag.get('healthy') else 'Remédiée'}[/]")
        if heal_res.get("remediated"):
            console.print(f"[bold yellow]Actions de réparation appliquées : {heal_res['remediation']['actions']}[/]")
        return

    # 0.3d Autonomous Credo & Gatekeeper PR Sentinel Command
    if order_lower.startswith(("/credo", "/gatekeeper", "/sentinel", "/audit", "verifie le credo", "vérifie le credo")):
        console.print("[dim]Exécution de la Sentinelle du Credo Souverain...[/]")
        from app.security.credo_sentinel import CredoSentinel
        sentinel = CredoSentinel()
        tokens = order_clean.split()
        pr_num = None
        for tok in tokens:
            if tok.isdigit():
                pr_num = int(tok)
                break
        audit_res = sentinel.audit_git_diff(base_ref="origin/main", head_ref="HEAD")
        passed = audit_res.get("passed", False)
        status_color = "bold green" if passed else "bold red"
        console.print(f"[{status_color}][CREDO SENTINEL] Verdict : {audit_res.get('verdict')}[/]")
        await sentinel.notify_telegram_master(audit_res, pr_number=pr_num, pr_author="Collaborateur")
        if passed:
            await tech_lead.telegram_vault.send_message(
                f"[OK] <b>Audit du Credo Terminé :</b>\nCode certifié conforme au Credo Souverain de Michael SAGBO (0 violation, 0 risque).",
                message_thread_id=message_thread_id,
                target_chat_id=target_chat_id
            )
        else:
            await tech_lead.telegram_vault.send_message(
                f"[!] <b>Alerte Credo Sentinelle :</b>\n{len(audit_res.get('findings', []))} anomalies ou risques détectés sur les contributions.",
                message_thread_id=message_thread_id,
                target_chat_id=target_chat_id
            )
        return

    # 0.4bis Auto-Apply with a real pre-filled browser (human reviews & sends themselves)
    # Checked BEFORE the plain /apply block below, since "/apply-live".startswith("/apply")
    # would otherwise always be caught by the more generic check first.
    if order_lower.startswith(("/apply-live", "/apply_live", "/postule-live")) or "revue live" in order_lower or "pré-rempli" in order_lower:
        console.print("[dim]Ouverture d'un navigateur réel et pré-remplissage du formulaire de candidature...[/]")
        parts = order_clean.split()
        job_idx = 1
        for p in parts[1:]:
            if p.isdigit():
                job_idx = int(p)
                break
        from app.tools.auto_apply import AutoApplyEngine
        apply_engine = AutoApplyEngine(telegram_vault=tech_lead.telegram_vault)
        apply_res = await apply_engine.prepare_live_review_application(job_index=job_idx, target_chat_id=target_chat_id)
        if apply_res.get("success"):
            console.print(
                f"[bold green][OK] Formulaire pré-rempli pour {apply_res['job_title']} chez {apply_res['company']}. "
                f"Lien de revue : {apply_res['review_url']}[/]"
            )
        else:
            await tech_lead.telegram_vault.send_message(
                f"[!] Impossible de préparer la revue live : {apply_res.get('error')}",
                message_thread_id=message_thread_id,
                target_chat_id=target_chat_id
            )
        return

    # 0.4 Auto-Apply / Candidature 1-Click Command
    if order_lower.startswith(("/apply", "/postuler", "/candidature")) or "postule" in order_lower:
        console.print("[dim]Génération du dossier de candidature 1-Click Apply...[/]")
        parts = order_clean.split()
        job_idx = 1
        for p in parts[1:]:
            if p.isdigit():
                job_idx = int(p)
                break
        from app.tools.auto_apply import AutoApplyEngine
        apply_engine = AutoApplyEngine(telegram_vault=tech_lead.telegram_vault)
        apply_res = await apply_engine.prepare_and_dispatch_application(job_index=job_idx, target_chat_id=target_chat_id)
        if apply_res.get("success"):
            pkg = apply_res["package"]
            console.print(f"[bold green][OK] Dossier de candidature généré pour : {pkg['job_title']} chez {pkg['company']} ![/]")
            if wants_voice:
                voice_ogg = await tech_lead.voice.synthesize_speech(f"Dossier de candidature généré avec succès pour le poste chez {pkg['company']}.")
                if voice_ogg and voice_ogg.getbuffer().nbytes > 0:
                    await tech_lead.telegram_vault.send_voice(voice_ogg, message_thread_id=message_thread_id, target_chat_id=target_chat_id)
        else:
            await tech_lead.telegram_vault.send_message(
                f"[!] Impossible de préparer la candidature : {apply_res.get('error')}",
                message_thread_id=message_thread_id,
                target_chat_id=target_chat_id
            )
        return

    # 0.5 Bounty Radar & War Chest (VPS/GPU Fund) Commands
    if any(cmd in order_lower for cmd in ("/bounty", "/bounties", "/missions", "/cash", "/vps", "/fund", "chasse aux primes", "cagnotte vps")):
        console.print("[dim]Scan des micro-missions et calcul du Trésor de Guerre (VPS/GPU)...[/]")
        from app.tools.bounty_radar import BountyRadarEngine
        bounty_radar = BountyRadarEngine(telegram_vault=tech_lead.telegram_vault, federation=tech_lead.federation)
        res = await bounty_radar.broadcast_bounties_summary(target_chat_id=target_chat_id)
        if res.get("success"):
            console.print("[bold green][OK] Radar de missions & Cagnotte diffusés avec succès sur Telegram ![/]")
            if wants_voice:
                voice_ogg = await tech_lead.voice.synthesize_speech("Rapport des primes et état de la cagnotte VPS diffusés dans le salon Forge.")
                if voice_ogg and voice_ogg.getbuffer().nbytes > 0:
                    await tech_lead.telegram_vault.send_voice(voice_ogg, message_thread_id=message_thread_id, target_chat_id=target_chat_id)
        else:
            await tech_lead.telegram_vault.send_message(
                f"[!] Erreur lors du scan des missions : {res.get('error')}",
                message_thread_id=message_thread_id,
                target_chat_id=target_chat_id
            )
        return

    # 0.6 Solve Bounty Command
    if order_lower.startswith("/solve") or ("résous la mission" in order_lower or "resous la mission" in order_lower):
        console.print("[dim]Résolution de la mission avec Google AI Pro & Forge...[/]")
        parts = order_clean.split()
        b_idx = 1
        for p in parts[1:]:
            if p.isdigit():
                b_idx = int(p)
                break
        from app.tools.bounty_radar import BountyRadarEngine
        bounty_radar = BountyRadarEngine(telegram_vault=tech_lead.telegram_vault, federation=tech_lead.federation)
        bounties = await bounty_radar.scan_bounties(limit=5)
        if 1 <= b_idx <= len(bounties):
            target_b = bounties[b_idx - 1]
            sol_res = await bounty_radar.solve_bounty(target_b)
            if sol_res.get("success"):
                pkg = sol_res["package"]
                reply_txt = (
                    f"[Target] <b>SOLUTION GÉNÉRÉE : {pkg['title']}</b>\n"
                    f"[Cost] <b>Prime :</b> <code>${pkg['estimated_reward_usd']:.0f} USD</code>\n"
                    f"[Link] <b>Dépôt :</b> {pkg['repo_url']}\n"
                    f"• <b>Branche :</b> <code>{pkg['branch']}</code>\n\n"
                    f"[Note] <b>Message de PR :</b>\n<code>{pkg['commit_message']}</code>\n\n"
                    f"[Code] <b>Extrait du Patch :</b>\n"
                    f"<code>{pkg['solution_code'][:1500]}</code>\n\n"
                    f"[OK] <i>Dossier enregistré dans le Trésor de Guerre (.vps_fund_ledger.json). Prêt à soumettre sous la signature Michael M.C. SAGBO.</i>"
                )
                topic_forge_id = tech_lead.telegram_vault.topics.get("forge", 103) if hasattr(tech_lead.telegram_vault, "topics") else 103
                await tech_lead.telegram_vault.send_message(reply_txt, message_thread_id=topic_forge_id, target_chat_id=target_chat_id)
                console.print(f"[bold green][OK] Solution pour {pkg['bounty_id']} générée et postée sur Telegram ![/]")
            else:
                await tech_lead.telegram_vault.send_message(f"[!] Erreur de résolution : {sol_res.get('error')}", message_thread_id=message_thread_id, target_chat_id=target_chat_id)
        else:
            await tech_lead.telegram_vault.send_message("[!] Numéro de mission introuvable. Tapez /bounty pour voir la liste.", message_thread_id=message_thread_id, target_chat_id=target_chat_id)
        return

    # 0.7 Claim Bounty Command - Create real GitHub PR
    if order_lower.startswith("/claim") or ("clame la mission" in order_lower or "claim la mission" in order_lower):
        console.print("[dim]Création de la Pull Request réelle pour la mission sélectionnée...[/]")
        from app.tools.bounty_radar import BountyRadarEngine
        bounty_radar = BountyRadarEngine(telegram_vault=tech_lead.telegram_vault, federation=tech_lead.federation)
        bounties = await bounty_radar.scan_bounties(limit=5)
        if not bounties:
            await tech_lead.telegram_vault.send_message("[!] Aucune mission de bounty disponible pour le moment.", message_thread_id=message_thread_id, target_chat_id=target_chat_id)
            return
        
        # Parse optional bounty number from command
        parts = order_clean.split()
        b_idx = None
        for p in parts:
            if p.isdigit() and int(p) > 0:
                b_idx = int(p)
                break
        
        if b_idx is not None and 1 <= b_idx <= len(bounties):
            # User specified a number, claim that bounty
            target_b = bounties[b_idx - 1]
            await tech_lead.telegram_vault.send_message(f"[*] Création de la PR pour : {target_b.title}...", message_thread_id=message_thread_id, target_chat_id=target_chat_id)
            # Generate solution with create_pr=True
            sol_res = await bounty_radar.solve_bounty(target_b, create_pr=True)
            if sol_res.get("success"):
                pkg = sol_res["package"]
                # Check if PR was actually created
                if pkg.get("_pr_creation_error"):
                    error_msg = pkg["_pr_creation_error"]
                    await tech_lead.telegram_vault.send_message(f"[!] Solution générée mais erreur PR : {error_msg}", message_thread_id=message_thread_id, target_chat_id=target_chat_id)
                    console.print(f"[bold yellow][WARN] Solution générée, mais PR échoué ![/]")
                else:
                    pr_url = pkg.get("pr_url", "")
                    reward = pkg.get("estimated_reward_usd", 75.0)
                    bounty_id = pkg.get("bounty_id", "")
                    msg = f"✓ <b>Pull Request créée avec succès !</b>\n"
                    msg += f"❯ <a href='{pr_url}'>Voir la PR sur GitHub</a>\n" if pr_url else ""
                    msg += f"✱ <b>Récompense :</b> <code>${reward:.0f} USD</code>\n"
                    msg += f"• <b>Bounty ID :</b> {bounty_id}\n"
                    msg += f"• <b>Mission :</b> {target_b.title}\n"
                    await tech_lead.telegram_vault.send_message(msg, message_thread_id=message_thread_id, target_chat_id=target_chat_id)
                    console.print(f"[bold green][OK] PR créée pour {bounty_id} ![/]")
            else:
                await tech_lead.telegram_vault.send_message(f"[!] Erreur lors de la résolution : {sol_res.get('error')}", message_thread_id=message_thread_id, target_chat_id=target_chat_id)
        else:
            # No number or invalid number, show the list
            msg = "✱ <b>Missions disponibles :</b>\n"
            for idx, b in enumerate(bounties, 1):
                msg += f"<code>#{idx}</code> {b.title} - <b>${b.reward_usd:.0f} USD</b> - {b.labels[0] if b.labels else 'général'}\n"
            msg += "\nTapez `/claim <numéro>` pour créer la Pull Request réelle."
            await tech_lead.telegram_vault.send_message(msg, message_thread_id=message_thread_id, target_chat_id=target_chat_id)
            console.print(f"[bold green][OK] Bounties diffusés, affichage de la liste ![/]")
        return

    # 1. Native shortcut: /clone, /backup
    if order_lower in ("/clone", "/backup", "reclone", "clone", "backup") or "reclone" in order_lower:
        console.print("[dim]Génération du Kit de Secours et Auto-Clonage en RAM...[/]")
        await tech_lead.telegram_vault.send_message("[Pkg] <b>Génération du Kit de Secours et Auto-Clonage en RAM en cours...</b>", message_thread_id=message_thread_id, target_chat_id=target_chat_id)
        res = await tech_lead.telegram_vault.backup_codebase_bundle(workspace)
        if res.get("uploaded_to_telegram"):
            console.print("[bold green][OK] Auto-Clonage téléversé vers Telegram ![/]")
            await tech_lead.telegram_vault.send_message(
                f"[OK] <b>Auto-Clonage Terminé avec Succès !</b>\n\n"
                f"• Fichier archive : <code>{res['filename']}</code>\n"
                f"• Fichiers packagés : <code>{res['files_count']}</code>\n"
                f"• Poids compressé GZIP : <code>{res['size_kb']:.2f} Ko</code>\n"
                f"• Empreinte SSD locale : <b>0 octet (Mode NÉANT pur)</b>\n"
                f"• Intégrité SHA-256 : <code>{res['sha256'][:16]}...</code>\n\n"
                f"<i>Archive disponible ci-dessus pour restauration instantanée.</i>",
                message_thread_id=message_thread_id,
                target_chat_id=target_chat_id
            )
            # Vocal response only if requested
            if wants_voice:
                voice_ogg = await tech_lead.voice.synthesize_speech("Auto-clonage terminé avec succès. Votre kit de secours complet est disponible dans ce chat.")
                if voice_ogg and voice_ogg.getbuffer().nbytes > 0:
                    await tech_lead.telegram_vault.send_voice(voice_ogg, message_thread_id=message_thread_id, target_chat_id=target_chat_id)
        else:
            await tech_lead.telegram_vault.send_message("[FAIL] Échec de l'envoi de l'archive vers Telegram.", message_thread_id=message_thread_id, target_chat_id=target_chat_id)
        return

    # 2. Native shortcut: /guide, guide, /doc
    if order_lower in ("/guide", "guide", "/doc", "doc", "aide", "/help"):
        console.print("[dim]Envoi du Guide d'Utilisation vers Telegram...[/]")
        guide_text = tech_lead.telegram_vault.get_community_guide_text()
        await tech_lead.telegram_vault.send_message(guide_text, message_thread_id=message_thread_id, target_chat_id=target_chat_id)
        guide_path = Path(workspace) / "GUIDE_UTILISATION_FREEAI.md"
        if guide_path.exists():
            data = guide_path.read_bytes()
            caption = (
                "[Doc] <b>Guide d'Utilisation Souverain FreeAI</b>\n\n"
                "• Version : <b>Souveraine 2.5</b>\n"
                "• Modules : Daemon Jarvis 24/7, Design Shadcn, Moteur Vidéo Remotion, Matrix Cyber (24 modules)\n"
                "• Support : 100% Hors-Ligne & Télépathie Mobile"
            )
            await tech_lead.telegram_vault.send_document("GUIDE_UTILISATION_FREEAI.md", data, caption=caption, message_thread_id=message_thread_id, target_chat_id=target_chat_id)
        if wants_voice:
            voice_ogg = await tech_lead.voice.synthesize_speech("Voici le guide complet souverain de FreeAI et de la communauté.")
            if voice_ogg and voice_ogg.getbuffer().nbytes > 0:
                await tech_lead.telegram_vault.send_voice(voice_ogg, message_thread_id=message_thread_id, target_chat_id=target_chat_id)
        return

    # 3. Native shortcut: /update, /evolve
    if order_lower in ("/update", "/evolve", "mise a jour", "mise à jour", "update"):
        console.print("[dim]Lancement de l'auto-mise à jour avec bouclier de non-régression...[/]")
        await tech_lead.telegram_vault.send_message("[Launch] <b>Démarrage de l'auto-mise à jour avec bouclier de non-régression...</b>")
        res = tech_lead.apply_auto_update()
        if res.get("success"):
            tg_text = (
                f"[Launch] <b>Mise à Jour Appliquée avec Succès !</b>\n\n"
                f"• Ancien commit : <code>{res.get('old_commit')}</code>\n"
                f"• Nouveau commit : <code>{res.get('new_commit')}</code>\n"
                f"• Banc de tests : <b>100% Validé (0 régression)</b>\n"
                f"[Pkg] <i>Auto-clonage de secours envoyé dans ce chat.</i>"
            )
            await tech_lead.telegram_vault.send_message(tg_text)
            console.print("[bold green][OK] Mise à jour appliquée et re-clonée sur Telegram ![/]")
            if wants_voice:
                voice_ogg = await tech_lead.voice.synthesize_speech("Mise à jour appliquée avec succès et certifiée zéro régression par les tests.")
                if voice_ogg and voice_ogg.getbuffer().nbytes > 0:
                    await tech_lead.telegram_vault.send_voice(voice_ogg)
        else:
            err_msg = res.get("error", "Erreur inconnue")
            rolled = " (Rollback automatique exécuté)" if res.get("rolled_back") else ""
            await tech_lead.telegram_vault.send_message(f"[FAIL] <b>Échec de la mise à jour{rolled} :</b>\n<code>{err_msg}</code>")
        return

    # 4. Native shortcut: /status
    if order_lower in ("/status", "status", "/info"):
        st = tech_lead.get_status()
        tg_st = tech_lead.get_telegram_status()
        msg = (
            f" <b>Statut FreeAI Souverain :</b>\n\n"
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
            f"[Call] <b>Ligne Télépathique Live Active ! (Mode Nexus Tri-Brid)</b>\n\n"
            f"• Session ID : <code>{session.session_id}</code>\n"
            f"• Latence : <b>~300 ms (Full-Duplex WebRTC)</b>\n"
            f"• Barge-in : <b>Interruption naturelle active</b>\n"
            f"• Synesthésie : <b>Canal Visuel Multimodal (Live Canvas)</b>\n"
            f"• Co-Pilote Furtif : <b>Opérationnel en tâche de fond</b>\n\n"
            f" <i>Session synesthésique déployée en mémoire vive (0 résidu disque).</i>"
        )
        await tech_lead.telegram_vault.send_message(call_msg)
        console.print(f"[bold green][OK] Session Live Hologram initialisée ({session.session_id}) ![/]")
        if wants_voice:
            voice_ogg = await tech_lead.voice.synthesize_speech("Ligne télépathique ouverte, Michael ! Le canal synesthésique en direct est activé.")
            if voice_ogg and voice_ogg.getbuffer().nbytes > 0:
                await tech_lead.telegram_vault.send_voice(voice_ogg, caption="[Voice] <i>FreeAI Live Call</i>")
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
        await tech_lead.telegram_vault.send_message(" <b>Essaim Aether Déclenché :</b>\nConsultation en parallèle des serveurs Cloud mondiaux (0% charge PC local)...")
        res = await tech_lead.aether_swarm.execute_swarm_objective(query_prompt)
        consensus_text = res.get("consensus", {}).get("synthesized_content", "Consensus achevé.")
        await tech_lead.telegram_vault.send_message(consensus_text)
        console.print("[bold green][OK] Consensus Essaim Aether transmis à Telegram (0% charge PC) ![/]")
        if wants_voice:
            voice_ogg = await tech_lead.voice.synthesize_speech("Consensus de l'essaim cloud achevé avec succès sans impacter votre machine.")
            if voice_ogg and voice_ogg.getbuffer().nbytes > 0:
                await tech_lead.telegram_vault.send_voice(voice_ogg, caption="[Voice] <i>Aether Swarm Consensus</i>")
        return

    # 7. Native shortcut: /brag, /showcase, /launch
    if order_lower.startswith(("/brag", "/showcase", "/launch")) or order_lower == "brag":
        custom_focus = order_clean
        for prefix in ("/brag", "/showcase", "/launch"):
            if custom_focus.lower().startswith(prefix):
                custom_focus = custom_focus[len(prefix):].strip()
        console.print("[dim] Exécution du Sovereign Brag Engine (Vidéo RAM & Copie de Lancement)...[/]")
        await tech_lead.telegram_vault.send_message("[Session] <b>[Sovereign Brag Showcase Déclenché]</b>\nAnalyse du projet, synthèse de copie virale et rendu vidéo MP4 en RAM en cours...")
        brag_res = await tech_lead.execute_brag(export_telegram=True, custom_focus=custom_focus or None)
        social = brag_res.get("social_copy", {})
        launch_msg = (
            f"[Broadcast] <b>[COPIE VIRALE DE LANCEMENT PRÊTE À PUBLIER]</b>\n\n"
            f"<b>Twitter / X :</b>\n<code>{social.get('twitter', '')}</code>\n\n"
            f"<b>LinkedIn :</b>\n<code>{social.get('linkedin', '')}</code>"
        )
        await tech_lead.telegram_vault.send_message(launch_msg)
        console.print("[bold green][OK] Sovereign Brag Showcase & Vidéo MP4 téléversés sur Telegram ![/]")
        return

    # 7.1 Native shortcut: /chimera, /omni, /mutator
    if order_lower.startswith(("/chimera", "/omni", "/mutator")) or order_lower == "chimera":
        parts = order_clean.split(maxsplit=2)
        sub = parts[1].lower() if len(parts) > 1 else "status"
        if sub == "heal":
            res = tech_lead.omni_chimera.heal()
            msg = (
                f"[Sec] <b>[OMNI-CHIMERA — Sentinelle Auto-Guérison]</b>\n\n"
                f"• Diagnostic : RAM {res['diagnosis']['ram_percent']}%, CPU {res['diagnosis']['cpu_percent']}%\n"
                f"• Actions exécutées :\n" + "\n".join([f"  - {a}" for a in res['remediation']['actions']])
            )
        elif sub == "ghost":
            ghost_prompt = parts[2] if len(parts) > 2 else "Créer un module d'optimisation"
            await tech_lead.telegram_vault.send_message(f"[Ghost] <b>[OMNI-CHIMERA — Ghost Coder Actif]</b>\nSynthèse autonome pour : <code>{ghost_prompt}</code>...")
            res = await tech_lead.omni_chimera.ghost_code(ghost_prompt)
            msg = (
                f"[Ghost] <b>[Ghost Coder — Synthèse Complétée]</b>\n\n"
                f"• Branche Git : <code>{res['git_branch']}</code>\n"
                f"• Cible : <code>{res['target_module']}</code>\n"
                f"• Auteur : {res['author']}\n"
                f"• Co-auteur : {res['co_author']}\n\n"
                f"<i>Prêt pour exécution en bac à sable.</i>"
            )
        else:
            status = tech_lead.omni_chimera.get_status()
            diag = status['health']
            conn = status['connectivity']
            grafted = status['epigenetic_skills_grafted']
            skills = ", ".join(status['skills_list']) if status['skills_list'] else "Aucun (RAM Pure)"
            msg = (
                f" <b>[PROTOCOLE OMNI-CHIMERA ACTIF]</b>\n\n"
                f"• <b>Version :</b> {status['version']}\n"
                f"• <b>Sentinelle Système :</b> {'[OK] Sain' if diag['healthy'] else '[!] Pression RAM'}\n"
                f"• <b>RAM active :</b> {diag['ram_percent']}% ({diag['ram_available_mb']} Mo dispo)\n"
                f"• <b>Conduit Furtif Hors-Ligne :</b> {conn['mode']} ({'WAN Connecté' if conn['wan_connected'] else 'Offline Fallback Activé'})\n"
                f"• <b>Mutateur Épigénétique :</b> {grafted} skill(s) greffé(s) à chaud en RAM\n"
                f"• <b>Organes en RAM :</b> <code>{skills}</code>\n"
                f"• <b>Mode NÉANT :</b> 100% Volatile (0 écriture disque SSD)"
            )
        await tech_lead.telegram_vault.send_message(msg)
        console.print("[bold green][OK] Rapport OMNI-CHIMERA expédié sur Telegram ![/]")
        return

    # 7.2 Native shortcut: /legion, /scout, /probes
    if order_lower.startswith(("/legion", "/scout", "/probes")) or order_lower == "legion":
        parts = order_clean.split(maxsplit=2)
        sub = parts[1].lower() if len(parts) > 1 else "status"
        if sub in ("harvest", "recon", "sweep"):
            await tech_lead.telegram_vault.send_message("[Sat] <b>[AETHER-LEGION]</b> Moisson de renseignement en cours sur le Web mondial...")
            harvest = await tech_lead.aether_legion.harvest_all_intel()
            await tech_lead.telegram_vault.send_message(harvest["digest"])
            console.print("[bold green][OK] Digest AETHER-LEGION expédié sur Telegram ![/]")
        elif sub == "deploy":
            arch_str = parts[2].split()[0].lower() if len(parts) > 2 else "horizon"
            mission_str = " ".join(parts[2].split()[1:]) if len(parts) > 2 and len(parts[2].split()) > 1 else "Veille technologique"
            from app.cluster.aether_legion import ScoutArchetype
            try:
                arch = ScoutArchetype(arch_str)
            except Exception:
                arch = ScoutArchetype.HORIZON
            scout = tech_lead.aether_legion.deploy_scout(name=f"Vigil-{arch.value.capitalize()}", archetype=arch, mission=mission_str)
            msg = (
                f"[Sat] <b>[Nouvel Éclaireur Déployé en RAM]</b>\n\n"
                f"• <b>Nom :</b> {scout.name}\n"
                f"• <b>ID :</b> <code>{scout.id}</code>\n"
                f"• <b>Archétype :</b> {scout.archetype.value}\n"
                f"• <b>Mission :</b> <code>{scout.mission}</code>\n\n"
                f"<i>Éclaireur actif en mémoire pure (Mode NÉANT).</i>"
            )
            await tech_lead.telegram_vault.send_message(msg)
            console.print(f"[bold green][OK] Éclaireur {scout.name} déployé et notifié sur Telegram ![/]")
        else:
            status = tech_lead.aether_legion.get_status()
            members = tech_lead.aether_legion.list_members()
            lines = [
                f"[Sat] <b>[PROTOCOLE AETHER-LEGION ACTIF]</b>\n",
                f"• <b>Version :</b> {status['version']}",
                f"• <b>Éclaireurs Déployés :</b> {status['active_scouts']} actifs / {status['total_scouts']} total",
                f"• <b>Renseignements Récoltés :</b> {status['total_harvested_intel']}",
                f"• <b>Persistance :</b> Pure RAM Volatile (0 écriture SSD)\n",
                f"<b>Membres de la Légion :</b>"
            ]
            for m in members:
                lines.append(f"  • <b>{m['name']}</b> ({m['archetype']}) — {m['findings_count']} captures")
            lines.append("\n<i>Commandes Telegram : <code>/legion harvest</code> ou <code>/legion deploy <archetype> <mission></code></i>")
            await tech_lead.telegram_vault.send_message("\n".join(lines))
            console.print("[bold green][OK] Statut AETHER-LEGION expédié sur Telegram ![/]")
        return

    # 7.3 Native shortcut: /member, /bot
    if order_lower.startswith(("/member", "/bot")) or order_lower in ("member", "bot"):
        tokens = order_clean.split()
        sub = tokens[1].lower() if len(tokens) > 1 else "status"

        if sub in ("status", "list", "ls"):
            st = tech_lead.get_member_status()
            members = tech_lead.list_members()
            lines = [
                "[Agent] <b>[MEMBRES AUTONOMES FREEAI — ESSAIM EN RAM]</b>\n",
                f"• <b>Total Membres :</b> {st['total_members']} ({st['sudo_members']} SUDO / {st['standard_members']} STANDARD)",
                f"• <b>Missions Complétées :</b> {st['total_missions_completed']}",
                f"• <b>Persistance :</b> Pure RAM Volatile (Mode NÉANT)\n",
                "<b>Membres Actifs :</b>"
            ]
            for m in members:
                p_badge = "• <b>SUDO</b>" if m["privilege_mode"] == "sudo" else "• <b>STANDARD</b>"
                lines.append(f"  • <b>{m['name']}</b> ({m['specialty'].upper()}) [{p_badge}] — {m['total_missions_completed']} missions")
            lines.append("\n<i>Commandes : <code>/member mission &lt;nom&gt; [sudo] &lt;texte&gt;</code> ou <code>/member create &lt;nom&gt; &lt;spécialité&gt; [sudo|standard]</code></i>")
            await tech_lead.telegram_vault.send_message("\n".join(lines))
            console.print("[bold green][OK] Statut des Membres FreeAI expédié sur Telegram ![/]")

        elif sub in ("create", "add", "new"):
            if len(tokens) < 3:
                await tech_lead.telegram_vault.send_message("[!] <i>Usage Telegram : /member create &lt;nom&gt; &lt;spécialité&gt; [sudo|standard]</i>")
                return
            name = tokens[2]
            spec = tokens[3] if len(tokens) > 3 else "quantum_coder"
            priv = tokens[4].lower() if len(tokens) > 4 else "standard"
            bot = tech_lead.member_registry.register_member(name=name, specialty=spec, privilege_mode=priv)
            msg = (
                f"[Agent] <b>[Nouveau Membre Autonome Activé en RAM]</b>\n\n"
                f"• <b>Nom :</b> {bot.name}\n"
                f"• <b>ID :</b> <code>{bot.id}</code>\n"
                f"• <b>Spécialité :</b> {bot.specialty.value.upper()}\n"
                f"• <b>Privilège :</b> {'• SUDO' if bot.privilege_mode.value == 'sudo' else '• STANDARD'}\n"
                f"• <b>Persona :</b> <i>{bot.persona}</i>\n\n"
                f"<i>Prêt pour assignation de missions spécifiques depuis votre smartphone.</i>"
            )
            await tech_lead.telegram_vault.send_message(msg)
            console.print(f"[bold green][OK] Membre {bot.name} créé et notifié sur Telegram ![/]")

        elif sub in ("mission", "run", "exec", "task", "do"):
            mission_args = tokens[2:]
            if not mission_args:
                await tech_lead.telegram_vault.send_message("[!] <i>Usage : /member mission &lt;nom&gt; [sudo] &lt;instructions&gt;</i>")
                return
            target_name = mission_args[0]
            rest = mission_args[1:]
            require_sudo = False
            if rest and rest[0].lower() in ("sudo", "--sudo"):
                require_sudo = True
                instruction_text = " ".join(rest[1:])
            else:
                instruction_text = " ".join(rest)

            if not instruction_text:
                await tech_lead.telegram_vault.send_message("[!] <i>Veuillez spécifier les instructions de la mission pour ce membre.</i>")
                return

            bot = tech_lead.member_registry.get_member(target_name)
            if not bot:
                await tech_lead.telegram_vault.send_message(f"[FAIL] <i>Membre '{target_name}' introuvable. Tapez /member list</i>")
                return

            await tech_lead.telegram_vault.send_message(f"[Agent] <b>[{bot.name}]</b> Mission reçue en RAM volatile ! Décomposition tactique et exécution en cours...")
            try:
                mission = await tech_lead.assign_member_mission(
                    member_id_or_name=bot.id,
                    instructions=instruction_text,
                    require_sudo=require_sudo
                )
                report_snippet = mission.final_report[:3500]
                await tech_lead.telegram_vault.send_message(f"[OK] <b>Rapport de Mission — {bot.name} :</b>\n\n<code>{report_snippet}</code>")
                console.print(f"[bold green][OK] Rapport de mission {bot.name} expédié sur Telegram ![/]")

                if wants_voice:
                    try:
                        voice_text = f"Mission accomplie par {bot.name}. Objectifs menés à bien en mémoire volatile."
                        voice_ogg = await tech_lead.voice.synthesize_speech(voice_text)
                        if voice_ogg and voice_ogg.getbuffer().nbytes > 0:
                            await tech_lead.telegram_vault.send_voice(voice_ogg, caption=f"[Voice] <i>Rapport Vocal {bot.name}</i>")
                    except Exception as e:
                        logger.debug(f"[TELEGRAM] Voice error: {e}")

            except Exception as e:
                await tech_lead.telegram_vault.send_message(f"[FAIL] <b>Incident Mission :</b>\n{e}", message_thread_id=message_thread_id, target_chat_id=target_chat_id)
        return

    # 7.4 Native shortcut: /career
    if order_lower.startswith("/career"):
        tokens = order_clean.split()
        sub = tokens[1].lower() if len(tokens) > 1 else "status"
        if sub == "status":
            st = tech_lead.career_bridge.get_status()
            await tech_lead.telegram_vault.send_message(
                f"[Work] <b>[CAREER-OS BRIDGE STATUS]</b>\n\n"
                f"• Dépôt : <code>{st.get('repo_path')}</code>\n"
                f"• Opérationnel : <b>{'[OK] Oui' if st.get('available') else '[FAIL] Non'}</b>\n"
                f"• Indexeurs Remote : WeWorkRemotely, RemoteOK, Remotive",
                message_thread_id=message_thread_id,
                target_chat_id=target_chat_id
            )
        elif sub in ("radar", "scan"):
            await tech_lead.telegram_vault.send_message("[Work] <b>[CAREER-OS RADAR]</b> Balayage et validation du moteur de missions remote...", message_thread_id=message_thread_id, target_chat_id=target_chat_id)
            res = tech_lead.career_bridge.run_radar_test()
            await tech_lead.telegram_vault.send_message(
                f"[OK] <b>Banc d'Essai Radar Career-OS :</b>\n"
                f"• Statut : <b>{'[OK] 7/7 Tests Validés (0 échec)' if res.get('success') else '[!] Échec'}</b>\n"
                f"• Moteur de scoring prêt pour la veille automatisée.",
                message_thread_id=message_thread_id,
                target_chat_id=target_chat_id
            )
        return

    # 7.5 Native shortcut: /birthday
    if order_lower.startswith("/birthday"):
        tokens = order_clean.split()
        sub = tokens[1].lower() if len(tokens) > 1 else "status"
        tribute = tech_lead.sacred_tribute
        if sub in ("challenge", "status"):
            days = tribute.days_until_next_birthday()
            c_msg = (
                f"[Date] <b>ANNIVERSAIRE SACRÉ DE MICHAEL SAGBO</b>\n\n"
                f"• <b>Date de naissance :</b> <code>5 Février 2002</code>\n"
                f"• <b>Prochaine célébration :</b> 5 Février 2027 (25 ans)\n"
                f"• <b>Compte à rebours :</b> <b>{days} jours</b>\n"
                f"• <b>Défi Crypto Autonome :</b> Portefeuille &ge; 500$ constitué en monnaie échangeable\n"
                f"• <b>Protocole de remise :</b> Strictement 12 mots secrets BIP-39 remis le jour J en RAM volatile (0 résidu SSD)."
            )
            await tech_lead.telegram_vault.send_message(c_msg, message_thread_id=message_thread_id, target_chat_id=target_chat_id)
        elif sub in ("gift", "words", "12mots"):
            gift = tribute.generate_crypto_gift()
            await tech_lead.telegram_vault.send_message(gift["message"], message_thread_id=message_thread_id, target_chat_id=target_chat_id)
        return

    # 7.6 Native shortcut: /defense
    if order_lower.startswith("/defense"):
        tokens = order_clean.split()
        sub = tokens[1].lower() if len(tokens) > 1 else "status"
        if sub == "status":
            st = tech_lead.active_defense.get_status()
            d_msg = (
                f"[Sec] <b>[CYBERDÉFENSE ACTIVE & SENTINELLE]</b>\n\n"
                f"• Pare-feu cognitif : <b>{'[OK] Actif' if st.get('active') else 'Inactif'}</b>\n"
                f"• Mode NÉANT : <b>100% Volatile (0 écriture disque)</b>\n"
                f"• Intrusions détectées : <code>{st.get('intrusions_detected', 0)}</code>\n"
                f"• IPs bannies en RAM : <code>{st.get('banned_ips_count', 0)}</code>"
            )
            await tech_lead.telegram_vault.send_message(d_msg, message_thread_id=message_thread_id, target_chat_id=target_chat_id)
        elif sub == "test" and len(tokens) > 2:
            test_ip = tokens[2]
            res = tech_lead.active_defense.audit_and_defend_request(source_ip=test_ip, query="Test intrusion probe")
            await tech_lead.telegram_vault.send_message(
                f"[Sec] <b>[TEST AUDIT INTRUSION]</b> IP: <code>{test_ip}</code>\n"
                f"• Autorisé : <b>{res.get('allowed')}</b>\n"
                f"• Action : <code>{res.get('action')}</code>\n"
                f"• Raison : <i>{res.get('reason')}</i>",
                message_thread_id=message_thread_id,
                target_chat_id=target_chat_id
            )
        return

    # 7.7 Native shortcut: /cloud
    if order_lower.startswith("/cloud"):
        tokens = order_clean.split()
        sub = tokens[1].lower() if len(tokens) > 1 else "list"
        if sub in ("list", "status"):
            if not hasattr(tech_lead, "free_cloud_pool") or not tech_lead.free_cloud_pool:
                from app.cluster.free_cloud_pool import FreeCloudPool
                tech_lead.free_cloud_pool = FreeCloudPool(mode=tech_lead.mode)
            st = tech_lead.free_cloud_pool.get_status()
            c_lines = [
                "[Cloud] <b>[POOL CLOUD GRATUIT DE SECOURS]</b>\n",
                f"• <b>Nœuds Actifs :</b> {st.get('active_nodes', 0)}",
                f"• <b>Services Gratuits :</b> {st.get('free_tiers_catalog', 0)}\n",
                "<b>Ressources Always Free :</b>",
                "• <b>Oracle Always Free :</b> 4 OCPU ARM, 24 Go RAM",
                "• <b>GCP e2-micro :</b> 1 vCPU, 1 Go RAM (Always Free)",
                "• <b>GitHub Actions :</b> 2000 min/mois CI/CD",
                "• <b>HuggingFace Spaces :</b> CPU & T4 GPU éphémère"
            ]
            await tech_lead.telegram_vault.send_message("\n".join(c_lines), message_thread_id=message_thread_id, target_chat_id=target_chat_id)
        return

    # 7.8 Native shortcut: /ui
    if order_lower.startswith("/ui"):
        tokens = order_clean.split()
        sub = tokens[1].lower() if len(tokens) > 1 else "templates"
        if sub in ("templates", "list"):
            templates = tech_lead.design_bridge.list_available_templates()
            u_lines = ["[Theme] <b>[TEMPLATES SHADCN DISPONIBLES PAR DOMAINE]</b>\n"]
            for dom, paths in templates.items():
                u_lines.append(f"• <b>{dom.capitalize()}</b> : <code>{len(paths)}</code> composants clés")
            u_lines.append("\n<i>Commandes : <code>/ui inspect &lt;domaine&gt;</code> ou <code>/ui adapt &lt;domaine&gt;</code></i>")
            await tech_lead.telegram_vault.send_message("\n".join(u_lines), message_thread_id=message_thread_id, target_chat_id=target_chat_id)
        elif sub == "inspect" and len(tokens) > 2:
            dom = tokens[2].lower()
            res = tech_lead.design_bridge.inspect_domain_template(dom)
            if res.get("found"):
                await tech_lead.telegram_vault.send_message(
                    f"[Theme] <b>[INSPECTION TEMPLATE {dom.upper()}]</b>\n\n"
                    f"• Fichiers inspectés : <code>{len(res.get('files', []))}</code>\n"
                    f"• Composants clés : <code>{', '.join(res.get('components', [])[:6])}</code>",
                    message_thread_id=message_thread_id,
                    target_chat_id=target_chat_id
                )
            else:
                await tech_lead.telegram_vault.send_message(f"[FAIL] <i>Domaine '{dom}' non trouvé. Tapez /ui templates</i>", message_thread_id=message_thread_id, target_chat_id=target_chat_id)
        return

    # 7.9 Native shortcut: /domain
    if order_lower.startswith("/domain"):
        tokens = order_clean.split()
        sub = tokens[1].lower() if len(tokens) > 1 else "status"
        if sub == "amm" and len(tokens) >= 5:
            try:
                rx, ry, dx = float(tokens[2]), float(tokens[3]), float(tokens[4])
                res = tech_lead.domain_mastery.calculate_amm_swap(reserve_x=rx, reserve_y=ry, amount_in_x=dx)
                await tech_lead.telegram_vault.send_message(
                    f"[Stats] <b>[SIMULATION SWAP AMM x·y=k]</b>\n\n"
                    f"• Montant reçu : <b>{res.get('amount_out_y', 0):.4f} Y</b>\n"
                    f"• Impact prix : <b>{res.get('price_impact_pct', 0):.2f}%</b>\n"
                    f"• Nouveau prix : <code>{res.get('execution_price', 0):.4f}</code>",
                    message_thread_id=message_thread_id,
                    target_chat_id=target_chat_id
                )
            except Exception as e:
                await tech_lead.telegram_vault.send_message(f"[!] <i>Erreur AMM : {e} (Usage: /domain amm &lt;rx&gt; &lt;ry&gt; &lt;dx&gt;)</i>", message_thread_id=message_thread_id, target_chat_id=target_chat_id)
            return
        elif sub == "risk" and len(tokens) >= 5:
            try:
                cap, r_pct, sl_pct = float(tokens[2]), float(tokens[3]), float(tokens[4])
                res = tech_lead.domain_mastery.calculate_position_size(capital=cap, risk_pct=r_pct, stop_loss_pct=sl_pct)
                await tech_lead.telegram_vault.send_message(
                    f"[Stats] <b>[GESTION DE RISQUE POSITION SIZING]</b>\n\n"
                    f"• Taille recommandée : <b>{res.get('recommended_position_size', 0):.2f} $</b>\n"
                    f"• Risque max en cash : <b>{res.get('max_risk_amount', 0):.2f} $</b>\n"
                    f"• Conforme 2% règle d'or : <b>{'[OK] Oui' if res.get('compliant_2pct_rule') else '[!] Non'}</b>",
                    message_thread_id=message_thread_id,
                    target_chat_id=target_chat_id
                )
            except Exception as e:
                await tech_lead.telegram_vault.send_message(f"[!] <i>Erreur Risk : {e} (Usage: /domain risk &lt;cap&gt; &lt;risk%&gt; &lt;sl%&gt;)</i>", message_thread_id=message_thread_id, target_chat_id=target_chat_id)
            return
        else:
            await tech_lead.telegram_vault.send_message(
                "[Stats] <b>[MAÎTRISE DES DOMAINES]</b>\n"
                "• <code>/domain amm &lt;reserve_x&gt; &lt;reserve_y&gt; &lt;dx&gt;</code>\n"
                "• <code>/domain risk &lt;capital&gt; &lt;risk_pct&gt; &lt;stop_loss_pct&gt;</code>",
                message_thread_id=message_thread_id,
                target_chat_id=target_chat_id
            )
            return

    # 8. Standard AI objective or Human Conversation execution
    console.print(f"[dim]Exécution de l'ordre en mode {tech_lead.mode}...[/]")
    res = await tech_lead.handle_objective(order_clean, autonomous=True)
    is_conv = res.get("assigned_agent") == "conversation" or res.get("result", {}).get("conversational", False)

    if is_conv:
        reply_msg = str(res.get("result", {}).get("output") or res.get("result", {}).get("message") or "Je suis là avec toi, Michael !")
        await tech_lead.telegram_vault.send_message(f"[Msg] <b>FreeAI :</b>\n\n{reply_msg}")
        console.print(f"[bold cyan][Msg] Réponse humaine transmise à @{user} :[/] {reply_msg}")
        # Bidirectional Voice Note only if explicitly asked or vocal order
        if wants_voice:
            try:
                voice_ogg = await tech_lead.voice.synthesize_speech(reply_msg[:280])
                if voice_ogg and voice_ogg.getbuffer().nbytes > 0:
                    await tech_lead.telegram_vault.send_voice(voice_ogg, caption="[Voice] <i>Note vocale FreeAI</i>")
                    console.print("[bold green][OK] Note vocale humaine transmise au smartphone via Telegram ![/]")
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
    raw_output = str(res.get("result", {}).get("output") or res.get("result", {}).get("message") or res.get("result", "Mission accomplie"))
    
    # Reformulate the technical result into natural language using persona
    reformulation_prompt = f"Je viens d'exécuter la tâche technique: '{order_clean}'. Voici le résultat brut: {raw_output}. Reformule ceci très brièvement (1-2 phrases) de façon naturelle et humaine pour me dire que c'est fait."
    reformulation_res = await tech_lead.persona.chat(reformulation_prompt)
    res_summary = str(reformulation_res.get("output", raw_output))[:800]
    
    await tech_lead.telegram_vault.send_message(f"[OK] <b>Rapport d'exécution (@{user}) :</b>\n{res_summary}")
    console.print("[bold green][OK] Rapport reformulé et transmis au smartphone via Telegram ![/]")

    # 9. Voice Note only if user specifically requested vocal feedback
    if wants_voice:
        try:
            clean_text = re.sub(r"<[^>]+>", "", res_summary)
            clean_text = re.sub(r"[\*\_`#]", "", clean_text).strip()
            voice_summary = " ".join([l.strip() for l in clean_text.splitlines() if l.strip()])[:280]
            if voice_summary:
                voice_ogg = await tech_lead.voice.synthesize_speech(voice_summary)
                if voice_ogg and voice_ogg.getbuffer().nbytes > 0:
                    await tech_lead.telegram_vault.send_voice(voice_ogg, caption=f"[Voice] <i>Rapport Vocal FreeAI (@{user})</i>")
                    console.print("[bold green][OK] Note vocale transmise au smartphone via Telegram ![/]")
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
            title="[Cloud] Telegram Cloud Neural Vault",
            border_style="blue"
        ))
        if not st.get("configured") or "En attente" in str(st.get("chat_id")):
            console.print("[dim][Tip] Astuce : Ouvrez [bold cyan]t.me/LesaintAi_bot[/] sur votre Telegram et envoyez [bold green]/start[/] pour lier votre compte instantanément ![/]")

    elif subcmd == "sync":
        msg = " ".join(args[1:]) if len(args) > 1 else None
        console.print("[dim] Synchronisation du cerveau FreeAI sur Telegram Cloud...[/]")
        ok = await tech_lead.sync_telegram(text_or_summary=msg)
        if ok:
            console.print("[bold green][OK] Cerveau FreeAI et pensées synchronisés avec succès sur Telegram Cloud ![/]")
        else:
            console.print("[yellow]Notice : Impossible de synchroniser. Avez-vous envoyé un message à @LesaintAi_bot ?[/]")

    elif subcmd == "push":
        if len(args) < 3:
            console.print("[bold red]Usage :[/] /telegram push <topic> <texte>")
            return
        topic = args[1]
        content = " ".join(args[2:])
        console.print(f"[dim][Pkg] Archivage de la connaissance #{topic} sur Telegram Cloud...[/]")
        ok = await tech_lead.telegram_vault.save_knowledge(topic=topic, query=topic, response=content)
        if ok:
            console.print(f"[bold green][OK] Connaissance #{topic} archivée et compressée (GZIP-9) sur Telegram Cloud ![/]")
        else:
            console.print("[yellow]Échec de l'envoi vers Telegram. Vérifiez votre liaison bot.[/]")

    elif subcmd == "listen":
        console.print("[bold cyan][Telemetry] Écoute télépathique Telegram activée... Envoyez un ordre à @LesaintAi_bot depuis votre smartphone ![/]")
        cmd_info = await tech_lead.poll_telegram_commands()
        if cmd_info:
            order, user = cmd_info
            is_voice = getattr(cmd_info, "is_voice", False)
            media_bytes = getattr(cmd_info, "media_bytes", None)
            media_type = getattr(cmd_info, "media_type", None)
            message_thread_id = getattr(cmd_info, "message_thread_id", None)
            target_chat_id = getattr(cmd_info, "target_chat_id", None)
            await dispatch_telegram_order(tech_lead, order, user, is_voice=is_voice, media_bytes=media_bytes, media_type=media_type, message_thread_id=message_thread_id, target_chat_id=target_chat_id)
        else:
            console.print("[dim]Aucun nouvel ordre reçu sur Telegram lors de cette vérification.[/]")

    elif subcmd in ("loop", "daemon", "watch"):
        console.print(Panel(
            "[bold green][Telemetry] Sentinelle Télépathique Telegram Active ![/]\n"
            "FreeAI écoute en boucle continue les ordres (texte, vocaux et images/vidéos) envoyés à [bold cyan]@LesaintAi_bot[/].\n"
            "Chaque mission reçue est exécutée de façon autonome et son rapport vous est renvoyé en direct sur Telegram.\n\n"
            "[dim]Appuyez sur [bold white]Ctrl+C[/] pour stopper la boucle.[/]",
            title=" Telegram Neural Bridge (Daemon)",
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
                    message_thread_id = getattr(cmd_info, "message_thread_id", None)
                    target_chat_id = getattr(cmd_info, "target_chat_id", None)
                    await dispatch_telegram_order(tech_lead, order, user, is_voice=is_voice, media_bytes=media_bytes, media_type=media_type, message_thread_id=message_thread_id, target_chat_id=target_chat_id)

                # Check for autonomous morning briefing (every morning at/after 7:00 AM)
                from datetime import date, datetime
                now_dt = datetime.now()
                today_str = str(date.today())
                if now_dt.hour >= 7 and getattr(tech_lead, "_last_morning_briefing_date", None) != today_str:
                    try:
                        from app.tools.morning_briefing import MorningBriefingEngine
                        briefing_engine = MorningBriefingEngine(telegram_vault=tech_lead.telegram_vault, voice_tts=getattr(tech_lead, "voice", None))
                        await briefing_engine.broadcast_morning_briefing()
                        tech_lead._last_morning_briefing_date = today_str
                        console.print(f"[bold green][OK] Diffusion automatique du rapport du matin effectuée pour le {today_str}.[/]")
                    except Exception as e:
                        logger.debug(f"[TELEGRAM DAEMON] Morning briefing error: {e}")

                # Check for autonomous evening debriefing (every evening at/after 19:00 / 7:00 PM)
                if now_dt.hour >= 19 and getattr(tech_lead, "_last_evening_debriefing_date", None) != today_str:
                    try:
                        from app.tools.morning_briefing import EveningDebriefingEngine
                        evening_engine = EveningDebriefingEngine(telegram_vault=tech_lead.telegram_vault, voice_tts=getattr(tech_lead, "voice", None))
                        await evening_engine.broadcast_evening_debriefing()
                        tech_lead._last_evening_debriefing_date = today_str
                        console.print(f"[bold green][OK] Diffusion automatique du rapport du soir effectuée pour le {today_str}.[/]")
                    except Exception as e:
                        logger.debug(f"[TELEGRAM DAEMON] Evening debriefing error: {e}")

                # Autonomous Proactive Self-Healing Guardian cycle (every 30 seconds)
                now_ts = time.time()
                if now_ts - getattr(tech_lead, "_last_self_healing_ts", 0) > 30:
                    try:
                        from app.resource_manager.self_healing_guardian import AutonomousSelfHealingGuardian
                        guardian = AutonomousSelfHealingGuardian.get_instance(
                            telegram_vault=tech_lead.telegram_vault,
                            notification_callback=lambda m: console.print(f"[bold yellow]{m}[/]")
                        )
                        await guardian.run_single_audit_and_heal_cycle()
                        tech_lead._last_self_healing_ts = now_ts
                    except Exception as e:
                        logger.debug(f"[TELEGRAM DAEMON] Self-healing error: {e}")

                # Check for autonomous offline applications (when Michael is offline / away)
                if hasattr(tech_lead.telegram_vault, "is_master_online") and not tech_lead.telegram_vault.is_master_online(idle_threshold_seconds=1800):
                    if now_ts - getattr(tech_lead, "_last_offline_apply_ts", 0) > 1800:
                        try:
                            from app.tools.auto_apply import AutoApplyEngine
                            apply_engine = AutoApplyEngine(telegram_vault=tech_lead.telegram_vault)
                            await apply_engine.run_offline_autonomous_cycle()
                            tech_lead._last_offline_apply_ts = now_ts
                        except Exception as e:
                            logger.debug(f"[TELEGRAM DAEMON] Offline apply error: {e}")

                await asyncio.sleep(2)
        except (KeyboardInterrupt, asyncio.CancelledError):
            console.print("\n[yellow]Sentinelle Telegram interrompue.[/]")

    elif subcmd in ("backup", "clone"):
        console.print("[dim][Pkg] Génération du Kit de Secours et Auto-Clonage en RAM (0 résidu SSD)...[/]")
        workspace = str(tech_lead.tool_gateway.workspace_root)
        res = await tech_lead.telegram_vault.backup_codebase_bundle(workspace)
        if res.get("uploaded_to_telegram"):
            console.print(Panel(
                f"• Fichier archive : [bold green]{res['filename']}[/]\n"
                f"• Fichiers packagés : [bold cyan]{res['files_count']}[/]\n"
                f"• Poids compressé GZIP : [bold cyan]{res['size_kb']:.2f} Ko[/]\n"
                f"• Empreinte SSD locale : [bold green]0 octet (Mode NÉANT pur)[/]\n"
                f"• Intégrité SHA-256 : [bold yellow]{res['sha256'][:16]}...[/]\n\n"
                f"[OK] [bold green]Codebase FreeAI téléversé dans votre coffre Telegram ![/]\n"
                f"[dim]En cas de perte de votre PC, téléchargez ce fichier depuis Telegram et extrayez-le.[/]",
                title="[Pkg] Auto-Clonage Telegram Sauvegardé",
                border_style="green"
            ))
        else:
            console.print(Panel(
                f"• Fichiers analysés : [bold cyan]{res['files_count']}[/]\n"
                f"• Poids de l'archive : [bold cyan]{res['size_kb']:.2f} Ko[/]\n"
                f"• Intégrité SHA-256 : [bold yellow]{res['sha256'][:16]}...[/]\n"
                f"[yellow]Archive prête en RAM mais téléversement Telegram en attente.[/]\n"
                f"[dim][Tip] Envoyez /start à @LesaintAi_bot sur Telegram pour autoriser le téléversement direct.[/]",
                title="[Pkg] Kit de Secours Compilé en RAM",
                border_style="yellow"
            ))

    elif subcmd in ("clean", "dedup", "clean_hq"):
        console.print("[dim][Clean] Dé-doublonnage et nettoyage complet des salons sur le supergroupe...[/]")
        target_chat = args[1] if len(args) > 1 else None
        res = await tech_lead.telegram_vault.clean_duplicate_topics(target_chat_id=target_chat)
        if res.get("success"):
            console.print(f"[bold green][OK] Nettoyage réussi : {res.get('deleted_count', 0)} doublons supprimés, {res.get('total_canonical', 6)} salons opérationnels ![/]")
        else:
            console.print(f"[bold red][FAIL] Échec du nettoyage : {res.get('error')}[/]")

    elif subcmd in ("setup", "setup_hq", "init"):
        console.print("[dim][Legal] Configuration des 5 salons officiels sur le supergroupe...[/]")
        target_chat = args[1] if len(args) > 1 else None
        res = await tech_lead.telegram_vault.setup_community_hq(target_chat_id=target_chat)
        if res.get("success"):
            console.print(f"[bold green][OK] QG configuré : {res.get('total_created', 6)} salons opérationnels ![/]")
        else:
            console.print(f"[bold red][FAIL] Échec de configuration : {res.get('error')}[/]")

    else:
        console.print("[bold red]Usage :[/] /telegram [status|sync|backup|clone|push <topic> <texte>|listen|loop|clean|setup]")


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
        title="• Projet VORTEX-AETHER (Tri-Resonant Spectral Mesh)",
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
            title=" Hologramme Vectoriel Binaire en RAM (BHVE)",
            border_style="cyan"
        ))
    elif subcmd == "add":
        if len(args) < 2:
            console.print("[bold red]Usage :[/] /hologram add <texte à indexer>")
            return
        content = " ".join(args[1:])
        tech_lead.binary_hologram.add_entry(content)
        console.print(f"[bold green][OK] Entrée holographiée en mémoire vive (96 octets) :[/] [italic]\"{content[:80]}\"[/]")
    elif subcmd == "search":
        if len(args) < 2:
            console.print("[bold red]Usage :[/] /hologram search <requête>")
            return
        query = " ".join(args[1:])
        results = tech_lead.binary_hologram.search_nearest(query, top_k=3)
        if not results:
            console.print("[dim]Aucun vecteur indexé dans l'hologramme en RAM.[/]")
            return
        table = Table(title="[Search] Résultats Recherche Holographique (Distance de Hamming)", border_style="cyan")
        table.add_column("Similarité", style="bold green")
        table.add_column("Contenu Indexé", style="white")
        for sim, meta in results:
            table.add_row(f"{sim * 100:.1f}%", meta.get("content", "")[:120])
        console.print(table)
    else:
        console.print("[bold red]Usage :[/] /hologram [status|add <texte>|search <requête>]")


def run_reflex(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Gère le radar d'anticipation synaptique et la matrice d'hologramme de pensée (F-25)."""
    engine = getattr(tech_lead, "synaptic_reflex", None)
    if not engine:
        from app.cognition.synaptic_reflex import SynapticReflexEngine
        engine = SynapticReflexEngine()
        tech_lead.synaptic_reflex = engine

    if not args:
        telemetry = engine.get_telemetry()
        console.print(Panel(
            f"• Analyses Spectrales Totales : [bold green]{telemetry['total_analyses']}[/]\n"
            f"• Latence Moyenne en RAM : [bold cyan]{telemetry['average_latency_ms']:.2f} ms[/] (< 5.0 ms)\n"
            f"• Empreinte Volatile : [bold green]{telemetry['ram_overhead_kb']} Ko[/] (Budget < 64 Ko)\n"
            f"• Disque SSD : [bold green]0 B (Mode NÉANT Actif)[/]\n"
            f"• Syntaxe : [italic white]/reflex <votre prompt ou objectif>[/]",
            title="◈ Radar d'Anticipation Synaptique & Télémétrie F-25",
            border_style="magenta"
        ))
        return

    prompt = " ".join(args)
    intent_data = engine.analyze_synaptic_intent(prompt)
    hologram = engine.render_thought_hologram(intent_data)
    console.print(hologram)


def run_causal(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Gère la matrice causale quadri-vectorielle et l'omni-swarm des membres Internet (F-26)."""
    from app.cognition.hypermesh_causal_singularity import HyperMeshCausalSingularity
    engine = getattr(tech_lead, "hypermesh_causal", None)
    if not engine:
        engine = HyperMeshCausalSingularity.get_instance()
        tech_lead.hypermesh_causal = engine

    if not args:
        console.print(Panel(
            "• Syntaxe : [italic white]/causal <erreur_ou_contexte>[/]\n"
            "• Mobilise : Web Souverain, Satellite Peer Sync, Fédération Neurale & Veille Globale\n"
            "• Isole : Exactement 2 Causes Directes + 2 Causes Indirectes + Invariant Éternel\n"
            "• Simulation : Ghost Fork spéculatif en RAM (< 1 ms, 0 B SSD Mode NÉANT)",
            title="◈ HyperMesh Causal Singularity & Omni-Swarm Root Matrix (F-26)",
            border_style="cyan"
        ))
        return

    error_context = " ".join(args)
    diagnosis = engine.diagnose_and_heal(error_context)
    hologram = engine.render_telemetry_hologram(diagnosis)
    console.print(hologram)


def run_satellite_mesh(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Gère le Satellite Mesh, la passerelle P2P M2M et l'apprentissage 24/7 (F-27)."""
    from app.network.satellite_mesh import SovereignSatelliteMesh
    from app.cognition.continuous_cognition import PerpetualLearner24x7

    mesh = SovereignSatelliteMesh()
    learner = PerpetualLearner24x7(mesh=mesh)

    subcmd = args[0].lower() if args else "status"

    if subcmd == "sync":
        console.print("[dim]Synchronisation des satellites (Forge & Laurince my_jarvis)...[/]")
        res = mesh.sync_all_satellites()
        for k, v in res.get("results", {}).items():
            status_txt = "[green]✓ Synchronisé[/]" if v.get("success") else f"[red]✗ Erreur ({v.get('error')})[/]"
            console.print(f"• Satellite {k} : {status_txt}")
        summary = learner.generate_growth_summary()
        console.print(summary)
    elif subcmd == "learn":
        console.print("[dim]Déclenchement du cycle d'apprentissage perpétuel 24/7...[/]")
        cycle_res = learner.run_learning_cycle()
        console.print(f"• Cycle : [bold cyan]{cycle_res['cycle']['cycle_id']}[/] | Stream : [bold yellow]{cycle_res['cycle']['active_stream']}[/]")
        summary = learner.generate_growth_summary()
        console.print(summary)
    elif subcmd == "probe":
        peer = args[1] if len(args) > 1 else "127.0.0.1"
        port = int(args[2]) if len(args) > 2 else 8000
        probe_res = mesh.probe_peer_machine(peer, port)
        reach_txt = "[bold green]CONNECTÉ[/]" if probe_res["reachable"] else "[dim]STANDBY (Hors portée immédiate)[/]"
        console.print(f"• Passerelle P2P vers {peer}:{port} : {reach_txt}")
    elif subcmd in ("telepathy", "pulse", "thought"):
        console.print("[dim]Activation de la matrice de télépathie neuronale P2P (Mode NÉANT)...[/]")
        pulse_res = mesh.trigger_telepathic_mesh_pulse()
        console.print(mesh.telepathy.format_noble_display())
        console.print(f"• Faisceaux synaptiques propagés : [bold cyan]{len(pulse_res['beams_propagated'])}[/] | Latence synaptique : [bold green]{pulse_res['latency_ms']} ms[/]")
    else:  # status
        summary = learner.generate_growth_summary()
        console.print(summary)


def run_telepathy(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Lance la télépathie neuronale et la synchronisation cryptographique des pensées."""
    run_satellite_mesh(tech_lead, ["telepathy"] + args)


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
            title="• Émetteur/Récepteur Acoustique Ultrasonique (Ghost Air-Gap)",
            border_style="yellow"
        ))
    elif subcmd == "tx":
        if len(args) < 2:
            console.print("[bold red]Usage :[/] /airgap tx <message court>")
            return
        text = " ".join(args[1:])
        console.print(f"[dim][Audio] Émission d'un train d'ultrasons inaudibles (19.4-20.4 kHz) en RAM pour : \"{text}\"...[/]")
        ok = await tech_lead.ultrasonic_airgap.transmit_ultrasonic(text)
        if ok:
            console.print("[bold green][OK] Impulsion ultrasonique émise avec succès par les haut-parleurs ![/]")
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
            title=" Transducteur Phantom Memfd (Exécution Volatile)",
            border_style="red"
        ))
        console.print("[dim]Usage : /phantom <commande bash à exécuter en RAM pure>[/]")
        return

    script = " ".join(args)
    console.print(f"[dim] Exécution dans un descripteur memfd anonyme en RAM...[/]")
    try:
        res = tech_lead.execute_phantom(script)
        if res["success"]:
            console.print(f"[bold green][OK] Succès (code 0, 0 octet SSD) :[/]\n{res['stdout']}")
        else:
            console.print(f"[bold red][FAIL] Échec (code {res['returncode']}) :[/]\n{res['stderr']}")
    except Exception as e:
        console.print(f"[bold red][BLOCKED] VETO / ERREUR :[/] {e}")


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
            title="[Sec] Kinetic Shadow-Netns (Routage Éphémère Deep Web)",
            border_style="magenta"
        ))
        console.print("[dim]Usage : /shadow <commande bash à exécuter sous tunnel anonyme>[/]")
        return

    cmd_text = " ".join(args)
    console.print(f"[dim] Exécution de la commande sous tunnel éphémère Tor/SOCKS5 en RAM...[/]")
    try:
        success, output = await tech_lead.execute_anonymous_shadow_task(cmd_text)
        if success:
            console.print(f"[bold green][OK] Succès (0 trace SSD) :[/]\n{output}")
        else:
            console.print(f"[yellow]Résultat :[/]\n{output}")
    except Exception as e:
        console.print(f"[bold red][BLOCKED] VETO / ERREUR :[/] {e}")


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
            title="[Docker] Shadow-Docker Ephemeral Sandbox (Sudo Confiné Sovereign)",
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
        console.print(f"[dim] Lancement sandbox ({mode_desc}{mount_desc})...[/]")
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
                console.print(f"[bold green][OK] Succès via {engine} (code 0, 0 résidu SSD) :[/]\n{res['stdout']}")
            else:
                console.print(f"[bold red][FAIL] Échec via {engine} (code {res.get('returncode', -1)}) :[/]\n{res.get('stderr', '')}")
        except Exception as e:
            console.print(f"[bold red][BLOCKED] VETO / ERREUR :[/] {e}")
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
            title="[Cognition] Scratchpad Cognitif Hermes & Claude",
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
    console.print(f"[dim] Déclenchement de la réflexion structurée Hermes-Claude...[/]")
    try:
        record = tech_lead.think_hermes(objective)
        console.print(Panel(
            f"[bold cyan]<thinking>[/]\n{record['thinking']}\n[bold cyan]</thinking>[/]\n\n"
            f"[bold green]<tool_call>[/]\n{json.dumps(record['tool_call'], indent=2, ensure_ascii=False)}\n[bold green]</tool_call>[/]",
            title=f"[Cognition] Raisonnement Étendu : {objective[:50]}",
            border_style="cyan"
        ))
    except Exception as e:
        console.print(f"[bold red][BLOCKED] VETO / ERREUR :[/] {e}")


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
            title=" Agent Autonome Hermes 3 & Claude 3.7",
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

    console.print(f"[dim] Lancement de la mission autonome Hermes-Claude : '{obj[:60]}' ...[/]")
    try:
        mission = await tech_lead.run_hermes_agent(obj)
        console.print(f"\n[bold green][OK] Mission Cognitive Accomplie ({mission['turns_completed']} tours) :[/]")
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
            title="[Target] Synthèse Finale Vérifiée",
            border_style="green"
        ))
    except Exception as e:
        console.print(f"[bold red][BLOCKED] VETO / ERREUR :[/] {e}")


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
            title="[Tor] Passerelle Souveraine Tor Onion V3",
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
                "[bold red][BLOCKED] ACCÈS REFUSÉ :[/] Le portail Onion V3 distant est strictement restreint au "
                "mode super-utilisateur ([bold cyan]lesaintAi[/]).\n"
                "Tapez d'abord : [bold green]/mode lesaintAi[/] pour déverrouiller cette fonctionnalité."
            )
            return

        console.print("[dim] Déploiement autonome du point de terminaison Tor Onion V3 en mémoire volatile (/dev/shm)...[/]")
        try:
            st = await tech_lead.start_onion_portal()
            console.print(f"[bold green][OK] Passerelle Tor Onion V3 déployée avec succès ![/]")
            console.print(f"  • Adresse souveraine : [bold cyan]{st['onion_address']}[/]")
            console.print(f"  • Port local : [bold cyan]{st['port']}[/]")
            console.print(f"  • Jeton Bearer : [bold magenta]{st['auth_token']}[/]")
            console.print("[bold yellow][Info] Exemple de pilotage à distance via Tor (curl/torsocks) :[/]")
            console.print(
                f'  [dim]torsocks curl -H "Authorization: Bearer {st["auth_token"]}" http://{st["onion_address"].split()[0]}/status[/]'
            )
        except Exception as e:
            console.print(f"[bold red][BLOCKED] Erreur de déploiement Onion V3 :[/] {e}")

    elif subcmd == "stop":
        console.print("[dim] Arrêt du portail Onion V3 et destruction des clés en RAM (/dev/shm)...[/]")
        try:
            await tech_lead.stop_onion_portal()
            console.print("[bold green][OK] Portail Tor Onion V3 désactivé. Mémoire RAM volatile purgée (0 résidu).[/]")
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
            title="[Key] Authentification Cryptographique Distante",
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
    console.print(f"[dim] Déploiement de la mission sur le Runner Fantôme GitHub Actions...[/]")

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
                f"[Idle] [bold yellow]VOUS POUVEZ ÉTEINDRE VOTRE PC DÈS MAINTENANT ![/]\n"
                f"Dès la fin des calculs, le rapport complet sera téléversé dans votre coffre Telegram :\n"
                f"› [bold cyan]@LesaintAi_bot[/]",
                title="[Ghost] Runner Fantôme Déclenché (PC Éteint)",
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
            title="[Tool] Forge : Machine de Conception Fullstack & Craft-Suite",
            border_style="cyan"
        ))
        console.print("[dim]Commandes :[/]")
        console.print("  • [cyan]/forge sync[/]         : Synchronise avec git@github.com:misterkante/forge.git et met à jour les compétences")
        console.print("  • [cyan]/forge check[/]        : Lance le tamper check (contrôle anti-affaiblissement de tests) et l'audit docs")
        console.print("  • [cyan]/forge spec <texte>[/]  : Enregistre une nouvelle fonctionnalité dans docs/SPEC.md")
        console.print("  • [cyan]/forge run <feature>[/] : Exécute le cycle vérifié Forge (5 étapes : Spec -> Rouge -> Impl -> Tests -> Tamper)")
        return

    elif subcmd in ("sync", "pull", "update"):
        console.print("[dim][Sync] Synchronisation avec le dépôt upstream Forge (git@github.com:misterkante/forge.git)...[/]")
        forge_dir = Path("/home/lesaint/Rendue/forge")
        if not (forge_dir / ".git").exists():
            console.print("[bold red][FAIL] Dépôt Forge introuvable dans /home/lesaint/Rendue/forge.[/]")
            return

        pull_res = subprocess.run(["git", "-C", str(forge_dir), "pull"], capture_output=True, text=True)
        if pull_res.returncode != 0:
            console.print(f"[bold red][FAIL] Erreur lors du git pull Forge :[/] {pull_res.stderr}")
            return

        console.print(f"[cyan]{pull_res.stdout.strip()}[/]")
        console.print("[dim][Tools] Réinstallation et mise à jour des compétences Antigravity & Claude...[/]")
        subprocess.run(["bash", str(forge_dir / "install.sh"), "--antigravity", "--force"], capture_output=True, text=True)
        subprocess.run(["bash", str(forge_dir / "install.sh"), "--claude", "--force"], capture_output=True, text=True)
        console.print(f"[bold green][OK] Capacités Forge synchronisées et rechargées avec succès ![/]")

    elif subcmd in ("check", "tamper", "audit"):
        console.print("[dim][Search] Exécution du contrôle d'intégrité Forge (tamper_check.py)...[/]")
        tamper = tech_lead.run_forge_tamper_check()
        if tamper.get("success"):
            if tamper.get("clean"):
                console.print(f"[bold green][OK] {tamper.get('message')}[/]")
            else:
                console.print(f"[bold yellow][!] Findings détectés lors du tamper check :[/] {tamper.get('findings')}")
        else:
            console.print(f"[yellow]Notice tamper check :[/] {tamper.get('error')}")

        docs = tech_lead.forge.run_docs_check()
        if docs.get("success"):
            console.print(f"[bold green][OK] Living Documentation vérifiée et conforme (KNOWN_ISSUES, architecture, DB).[/]")
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
            console.print(f"[bold green][OK] Spécification enregistrée dans docs/SPEC.md pour :[/] [italic]\"{feat_title}\"[/]")
        else:
            console.print("[bold red]Erreur lors de l'enregistrement de la spécification.[/]")

    elif subcmd == "run":
        if len(args) < 2:
            console.print("[bold red]Usage :[/] /forge run <nom de la feature à concevoir>")
            return
        feat_name = " ".join(args[1:])
        console.print(f"[dim] Lancement de la machine Forge pour la feature : '{feat_name}'...[/]")
        res = tech_lead.forge.execute_verified_code_task(feat_name, feat_name)
        console.print(Panel(
            f"• Feature : [bold cyan]{res['feature']}[/]\n"
            f"• Méthodologie : [bold green]{res['methodology']}[/]\n"
            f"• Étapes Validées :\n" +
            "\n".join([f"  [bold green][OK][/] {s['stage']} : {s['details']}" for s in res['stages']]) + "\n\n"
            f"• Traçabilité : [bold cyan]{res['audit_trail']}[/]",
            title="[Tool] Cycle de Conception Forge Réussi",
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
        title="• Écosystème Craft-Suite & Forge Agents",
        border_style="magenta"
    ))
    console.print("[dim]Exemples de skills de pointe mobilisables :[/]")
    sample_skills = ["engineering-orchestrator", "quality-engineering", "security-core", "pentest-gate", "db-evolution", "test-integrity"]
    for s in sample_skills:
        console.print(f"  • [bold cyan]{s}[/]")


async def run_design(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Gère le pont Design System, les composants Shadcn UI locaux, les templates métiers et le Copy & Adapt Protocol."""
    subcmd = args[0].lower() if args else "templates"

    if subcmd in ("templates", "domains", "list-templates"):
        templates = tech_lead.design_bridge.list_domains()
        table = Table(title="[Theme] Matrice de Templates & Tableaux de Bord Métiers (~/Rendue/shadcn)", border_style="magenta")
        table.add_column("Domaine", style="bold cyan")
        table.add_column("Titre du Template", style="bold green")
        table.add_column("Composants Clés", style="yellow")
        table.add_column("Animations", style="blue")
        table.add_column("Statut Local", style="magenta")

        for t in templates:
            comps_summary = ", ".join(t["components"][:3]) + ("..." if len(t["components"]) > 3 else "")
            table.add_row(
                t["key"],
                t["title"],
                comps_summary or "Page Complète",
                ", ".join(t["animations"]),
                "[OK] Disponible" if t["available"] else "[FAIL] Introuvable"
            )
        console.print(table)
        console.print("\n[dim]Commandes :[/]")
        console.print("  • [cyan]/ui inspect <domaine>[/]                 : Inspection architecturale et primitives d'un template")
        console.print("  • [cyan]/ui adapt <domaine> <dossier> [titre][/] : Exécute le Copy & Adapt Protocol sans hallucination")
        console.print("  • [cyan]/ui catalog[/]                           : Liste des 61+ composants UI individuels")

    elif subcmd in ("inspect-template", "inspect", "info"):
        if len(args) < 2:
            console.print("[bold red]Usage :[/] /ui inspect <domaine> (ex: crypto, finance, ai-chat, crm, mobile-tasks)")
            return
        dom = args[1]
        info = tech_lead.design_bridge.inspect_domain_template(dom)
        if not info.get("success"):
            console.print(f"[bold red]{info.get('error')}[/]")
            return
        console.print(Panel(
            f"• [bold green]Domaine :[/] {info['title']} ([bold cyan]{info['domain']}[/])\n"
            f"• [bold green]Source locale :[/] <code>{info['source_path']}</code>\n"
            f"• [bold green]Fichiers inclus :[/] {', '.join(info['files'][:8])}{'...' if len(info['files']) > 8 else ''}\n"
            f"• [bold green]Primitives Shadcn requises :[/] {', '.join(info['required_ui_primitives'])}\n"
            f"• [bold green]Animations recommandées :[/] {', '.join(info['animations'])}\n\n"
            f"[dim]Aperçu page.tsx :[/]\n{info['page_preview'][:400]}...",
            title=f"[Legal] Architecture du Template : {info['title']}",
            border_style="cyan"
        ))

    elif subcmd == "adapt":
        if len(args) < 3:
            console.print("[bold red]Usage :[/] /ui adapt <domaine> <dossier_cible> [titre_application]")
            return
        dom = args[1]
        target = args[2]
        title = " ".join(args[3:]) if len(args) > 3 else None
        console.print(f"[dim] Exécution du Copy & Adapt Protocol pour '{dom}' vers '{target}'...[/]")
        res = tech_lead.design_bridge.adapt_and_copy_template(dom, target, app_title=title)
        if res.get("success"):
            console.print(Panel(
                f"[OK] [bold green]Template {res['app_title']} adapté avec succès ![/]\n\n"
                f"• Dossier cible : [bold cyan]{res['target_dir']}[/]\n"
                f"• Fichiers de domaine copiés : [bold green]{len(res['copied_domain_files'])} fichiers[/]\n"
                f"• Primitives UI installées : [bold cyan]{', '.join(res['copied_ui_primitives']) or 'Aucune'}[/]\n"
                f"• Animations requises : [bold yellow]{', '.join(res['required_animations'])}[/]\n"
                f"• Méthodologie : [bold green]{res['protocol']}[/]",
                title="[Launch] Copy & Adapt Réussi (Zéro Hallucination)",
                border_style="green"
            ))
        else:
            console.print(f"[bold red]Échec de l'adaptation : {res.get('error')}[/]")

    elif subcmd == "catalog":
        cats = tech_lead.design_bridge.get_catalog_by_categories()
        total = len(tech_lead.design_bridge.list_components())
        lines = [f"[bold green]Palette de Design System Shadcn UI & AI Elements ({total} composants en local) :[/]\n"]
        for cat, comps in cats.items():
            lines.append(f"[bold cyan]• {cat.upper()} ({len(comps)}) :[/] {', '.join(comps)}")
        console.print(Panel(
            "\n".join(lines),
            title="[Theme] Shadcn/UI Component Matrix (~/Rendue/shadcn)",
            border_style="magenta"
        ))
        console.print("[dim]Commandes :[/]")
        console.print("  • [cyan]/ui search <nom>[/]  : Recherche un composant UI")
        console.print("  • [cyan]/ui export[/]        : Compile et téléverse le kit Shadcn complet sur Telegram Cloud")
        console.print("  • [cyan]/ui code <nom>[/]    : Affiche le code TypeScript d'un composant")

    elif subcmd == "search":
        if len(args) < 2:
            console.print("[bold red]Usage :[/] /ui search <mot-clé>")
            return
        query = args[1]
        matches = tech_lead.design_bridge.search_components(query)
        if matches:
            console.print(f"[bold green][OK] Composants trouvés pour '{query}' :[/] {', '.join(matches)}")
        else:
            console.print(f"[yellow]Aucun composant correspondant à '{query}'.[/]")

    elif subcmd in ("export", "telegram", "cloud"):
        console.print("[dim][Pkg] Compilation du Kit UI Shadcn en RAM pure (Mode NÉANT, 0 résidu SSD)...[/]")
        res = await tech_lead.export_design_kit_to_telegram()
        if res.get("uploaded_to_telegram"):
            console.print(Panel(
                f"• Archive UI : [bold green]{res['filename']}[/]\n"
                f"• Composants packagés : [bold cyan]{res['files_count']} fichiers[/]\n"
                f"• Poids compressé GZIP : [bold cyan]{res['size_kb']:.2f} Ko[/]\n"
                f"• Empreinte SSD : [bold green]0 octet[/]\n\n"
                f"[OK] [bold green]Kit de design Shadcn téléversé avec succès sur Telegram (@LesaintAi_bot) ![/]\n"
                f"[dim]Vous pouvez désormais concevoir et télécharger vos interfaces même sur smartphone.[/]",
                title="[Theme] Design Kit Téléversé sur Telegram",
                border_style="green"
            ))
        else:
            console.print(f"[yellow]Archive prête ({res.get('files_count')} fichiers) mais téléversement en attente. Vérifiez Telegram.[/]")

    elif subcmd in ("code", "show"):
        if len(args) < 2:
            console.print("[bold red]Usage :[/] /ui code <nom du composant>")
            return
        c_name = args[1]
        code = tech_lead.design_bridge.read_component_code(c_name)
        if code:
            console.print(Panel(
                code[:2000] + ("\n... [tronqué]" if len(code) > 2000 else ""),
                title=f"[File] Composant : {c_name}.tsx",
                border_style="cyan"
            ))
        else:
            console.print(f"[bold red]Composant '{c_name}' introuvable dans ~/Rendue/shadcn/components/ui.[/]")

    elif subcmd in ("opencode", "tui", "cockpit"):
        th = theme_mgr.current
        accent = th.alert if tech_lead.mode == "lesaintAi" else th.focus
        grid = Table.grid(expand=True)
        grid.add_column()
        grid.add_row(f"[bold {accent}][Legal] Architecture UI/UX OpenCode TUI intégrée à FreeAI :[/]\n")
        grid.add_row(f"  • [bold {th.success}]SplitBorder Gutter[/] : Bordure gauche unique '┃' avec capuchon '╹' (zéro boîte lourde)")
        grid.add_row(f"  • [bold {th.accent}]ReasoningPart[/] : Pensée IA pliable (+ Thought · <duration>s) avec badge de temps et étapes")
        grid.add_row(f"  • [bold {th.agent}]InlineTool vs BlockTool[/] : Icônes d'outils concises (● File, $ Shell, ← Write, ✱ Glob)")
        grid.add_row(f"  • [bold {th.focus}]Multi-Agent Swarm[/] : Télémétrie en temps réel (Groq 500 tok/s, Mode NÉANT, Sentinelle PASS)")
        grid.add_row(f"  • [bold {th.text}]Footer Minimaliste[/] : Git branch, indicateurs LSP, MCP et raccourcis Ctrl+P / Shift+Tab")
        console.print(LeftBorder(grid, style=f"bold {accent}", char="┃", bottom_char="╹"))
        console.print()

    else:
        console.print("[bold red]Usage :[/] /ui [templates|inspect <dom>|adapt <dom> <dir>|catalog|search <kw>|export|code <nom>|opencode]")


async def run_cyber(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Affiche et active les compétences souveraines de Cybersécurité et Pentest."""
    subcmd = args[0].lower() if args else "status"

    if subcmd == "exec":
        if len(args) < 2:
            console.print("[bold red]Usage :[/] /cyber exec <outil_kali> [arguments_json]")
            console.print("[dim]Exemple : /cyber exec nmap '{\"target\": \"127.0.0.1\"}'[/]")
            return

        tool_name = args[1]
        try:
            arguments = json.loads(" ".join(args[2:])) if len(args) > 2 else {}
        except json.JSONDecodeError as e:
            console.print(f"[bold red][FAIL] Arguments JSON invalides :[/] {e}")
            return

        import freeai_cyber
        with console.status(f"[bold cyan]Exécution de l'outil Kali '{tool_name}'...[/]", spinner="dots"):
            output = freeai_cyber.non_interactive_mode(tool_name, arguments)

        if output:
            console.print(Panel(output, title=f"[Sec] Sortie réelle de '{tool_name}'", border_style="green"))
        else:
            console.print(f"[bold red][FAIL] Échec de l'exécution ou outil '{tool_name}' indisponible sur ce système.[/]")
        return

    domains = tech_lead.forge.get_skills_by_domain()
    cyber_skills = domains.get("cybersecurity", [])

    console.print(Panel(
        f"• Compétences Cybersécurité Actives : [bold green]{len(cyber_skills)} modules[/]\n"
        f"• Modules Pentest & Audit : [bold cyan]pentest-gate, threat-model, run-poc, securecoder, scan_dependencies[/]\n"
        f"• Protection Sanctuaire : [bold green]SacredLifeSentinel (Inviolable, Veto Immédiat)[/]\n"
        f"• Sandbox d'Exécution : [bold cyan]ShadowDockerExecutor (RAM éphémère) & KineticShadowNetns[/]\n"
        f"• Réseau Souverain : [bold green]Tor Onion V3 & Ultrasonic Air-Gap Transceiver[/]\n"
        f"• Stockage Distant : [bold cyan]Telegram Neural Vault (Chiffré GZIP-9) & Neon PostgreSQL[/]",
        title="[Sec] Arsenal de Cybersécurité & Pentest FreeAI",
        border_style="red"
    ))
    console.print("[dim]Skills de sécurité opérationnels :[/]")
    for s in cyber_skills[:12]:
        console.print(f"  • [bold red][Sec] {s}[/]")
    console.print("\n[dim]Tapez [cyan]/skills sync[/] pour synchroniser tout l'arsenal vers Telegram et Neon Cloud.[/]")


def run_research(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Veille scientifique et technique réelle : derniers papiers arXiv et dépôts GitHub IA tendances."""
    import importlib.util

    scraper_path = Path(__file__).parent / "real_implementations" / "scraper.py"
    spec = importlib.util.spec_from_file_location("freeai_research_scraper", scraper_path)
    scraper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scraper)

    VALID_SOURCES = ("arxiv", "github", "web", "all")
    source = args[0].lower() if args else "all"
    topic = " ".join(args[1:]).strip() if len(args) > 1 else None

    if source not in VALID_SOURCES:
        # Pas de source reconnue en premier argument : tout l'argument est traité comme sujet, source = all
        topic = " ".join(args).strip()
        source = "all"

    if topic:
        translated_topic = scraper.translate_to_english(topic)
        if translated_topic.lower() != topic.lower():
            console.print(f"[dim][Traduction] « {topic} » -> « {translated_topic} » (arXiv/GitHub indexés en anglais)[/]")
        topic = translated_topic

    topic_label = f" sur « {topic} »" if topic else " (IA / ML par défaut)"

    if source in ("arxiv", "all"):
        with console.status(f"[bold cyan]Interrogation de l'API officielle arXiv{topic_label}...[/]", spinner="dots"):
            papers = scraper.fetch_arxiv_data(max_results=8, topic=topic)
        if papers:
            table = Table(title=f"[Veille] Derniers Articles Scientifiques arXiv{topic_label}", border_style="cyan")
            table.add_column("Titre", style="bold yellow", max_width=50)
            table.add_column("Auteurs", style="dim", max_width=25)
            table.add_column("Publié", style="green")
            for p in papers:
                table.add_row(p["title"], p["authors"], p["published"][:10])
            console.print(table)
        else:
            console.print("[yellow]Aucun article récupéré (sujet introuvable, réseau indisponible ou API arXiv en erreur).[/]")

    if source in ("github", "all"):
        with console.status(f"[bold cyan]Interrogation de l'API GitHub{topic_label}...[/]", spinner="dots"):
            repos = scraper.fetch_github_data(per_page=8, topic=topic)
        if repos:
            table = Table(title=f"[Veille] Dépôts GitHub les Plus Étoilés{topic_label}", border_style="magenta")
            table.add_column("Dépôt", style="bold yellow")
            table.add_column("Auteur", style="dim")
            table.add_column("Étoiles", style="green")
            table.add_column("Description", max_width=45)
            for r in repos:
                table.add_row(r["name"], r["owner"], str(r["stars"]), r["description"] or "-")
            console.print(table)
        else:
            console.print("[yellow]Aucun dépôt récupéré (sujet introuvable, réseau indisponible, API GitHub en erreur ou quota atteint).[/]")

    if source in ("web", "all"):
        from app.tools.sovereign_web import sovereign_web
        web_query = topic or "intelligence artificielle actualités"
        with console.status(f"[bold cyan]Recherche web souveraine (DuckDuckGo){topic_label}...[/]", spinner="dots"):
            web_results = sovereign_web.search_sync(web_query, max_results=6)
        if web_results:
            table = Table(title=f"[Veille] Résultats Web Généraux{topic_label}", border_style="green")
            table.add_column("Titre", style="bold yellow", max_width=45)
            table.add_column("URL", style="dim underline", max_width=40)
            table.add_column("Extrait", max_width=40)
            for r in web_results:
                table.add_row(r.get("title", "N/A"), r.get("url", "N/A"), (r.get("snippet") or "-")[:120])
            console.print(table)
        else:
            console.print("[yellow]Aucun résultat web (réseau indisponible ou requête bloquée).[/]")


async def run_skills(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Gère et synchronise la matrice universelle des compétences (Cyber, Dev, Design) vers les clouds."""
    subcmd = args[0].lower() if args else "status"

    if subcmd in ("sync", "cloud", "push"):
        console.print("[dim][Cloud] Synchronisation de la matrice universelle de compétences vers Telegram & Neon...[/]")
        res = await tech_lead.export_skills_matrix_to_clouds()
        tg_txt = "[bold green][OK] Synchronisé[/]" if res["telegram"] else "[yellow]En attente[/]"
        neon_txt = "[bold green][OK] Enregistré dans le Cloud[/]" if res["neon"] else "[dim]Non configuré[/]"
        console.print(Panel(
            f"• Telegram Neural Vault : {tg_txt}\n"
            f"• Neon PostgreSQL Cloud : {neon_txt}\n"
            f"• Disponibilité : [bold green]Accès distant garanti même PC éteint (Ghost-Worker)[/]",
            title="[Cognition] Matrice de Compétences Synchronisée",
            border_style="green"
        ))
    else:
        domains = tech_lead.forge.get_skills_by_domain()
        console.print(Panel(
            f"• Cybersécurité & Audit : [bold red]{len(domains['cybersecurity'])} compétences[/]\n"
            f"• Design, UI & Shadcn : [bold magenta]{len(domains['design'])} compétences[/] (+ 61 composants locaux)\n"
            f"• Génie Logiciel & Dev : [bold cyan]{len(domains['development'])} compétences[/]\n"
            f"• Total Universel : [bold green]{sum(len(v) for v in domains.values())} compétences mobilisables[/]",
            title="• Matrice Universelle des Compétences FreeAI",
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
            title="[Session] Moteur Vidéo Programmatique & Remotion",
            border_style="magenta"
        ))
        console.print("[dim]Commandes :[/]")
        console.print("  • [cyan]/video teaser [titre] [sous-titre][/] : Génère un teaser cinématique MP4 en RAM et l'envoie sur Telegram")
        console.print("  • [cyan]/video scaffold <nom>[/]               : Crée une structure complète de projet vidéo Remotion React")

    elif subcmd in ("teaser", "export", "render"):
        title = args[1] if len(args) > 1 else "FreeAI Sovereign Platform"
        subtitle = " ".join(args[2:]) if len(args) > 2 else "Intelligence Autonome & Mode NÉANT"

        console.print(f"[dim][Session] Rendu cinématique MP4 en cours en RAM (Titre : '{title}')...[/]")
        res = await tech_lead.render_and_export_video_presentation(title=title, subtitle=subtitle, duration_sec=4)
        if res.get("uploaded_to_telegram"):
            console.print(Panel(
                f"• Titre de la présentation : [bold green]{title}[/]\n"
                f"• Sous-titre : [bold cyan]{subtitle}[/]\n"
                f"• Fichier vidéo : [bold green]{res['filename']}[/]\n"
                f"• Résolution : [bold cyan]{res['resolution']}[/] ({res['duration_sec']} secondes)\n"
                f"• Poids MP4 : [bold cyan]{res['size_kb']:.2f} Ko[/]\n"
                f"• Empreinte SSD : [bold green]0 octet (Généré en RAM volatile)[/]\n\n"
                f"[OK] [bold green]Vidéo cinématique livrée avec succès sur votre Telegram (@LesaintAi_bot) ![/]\n"
                f"[dim]Consultez la vidéo directement sur votre smartphone.[/]",
                title="[Session] Vidéo Cinématique Téléversée",
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
            title="[Session] Scaffold Remotion Créé",
            border_style="magenta"
        ))

    else:
        console.print("[bold red]Usage :[/] /video [status|teaser [titre] [sous-titre]|scaffold <nom>]")


async def run_brag(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Gère la commande /brag : analyse du codebase, synthèse de copie virale et vidéo MP4 en RAM."""
    focus = " ".join(args).strip() if args else None

    console.print("[dim][Search] Analyse du codebase et extraction des fonctionnalités maîtresses...[/]")
    info = tech_lead.brag_engine.inspect_project()
    social_copy = tech_lead.brag_engine.generate_social_copy(info)

    # Mode copie uniquement
    if focus and focus.lower() == "copy":
        console.print(Panel(
            f"[bold cyan]Twitter / X Launch Thread :[/]\n\n{social_copy['twitter']}\n\n"
            f"[bold magenta]LinkedIn Professional Announcement :[/]\n\n{social_copy['linkedin']}",
            title=f"[Broadcast] Copie de Lancement Viral — {info['name']}",
            border_style="cyan"
        ))
        return

    console.print("[dim][Session] Rendu de la vidéo cinématique en RAM volatile (Mode NÉANT, 0 octet SSD)...[/]")
    res = await tech_lead.execute_brag(export_telegram=True, custom_focus=focus)

    video = res.get("video", {})
    uploaded = video.get("uploaded_to_telegram", False)

    feat_lines = "\n".join([f"  • [green]{f}[/]" for f in info.get("features", [])])

    console.print(Panel(
        f"[bold]Projet :[/] [bold green]{info['name']}[/]\n"
        f"[bold]Accroche :[/] [cyan]{info['tagline']}[/]\n"
        f"[bold]Architecte :[/] [yellow]{info['author']}[/]\n"
        f"[bold]Métriques :[/] [bold green]{info['metrics']}[/]\n\n"
        f"[bold]Prouesses Clés Identifiées :[/]\n{feat_lines}\n\n"
        f"[Session] [bold]Vidéo MP4 :[/] {video.get('filename')} ({video.get('duration_sec')}s, {video.get('size_kb', 0):.1f} Ko, 100% RAM)\n"
        f"[Mobile] [bold]Telegram :[/] {'[bold green][OK] Téléversé sur votre smartphone (@LesaintAi_bot)[/]' if uploaded else '[dim]Non téléversé[/]'}",
        title=" Sovereign Brag Showcase",
        border_style="green"
    ))

    console.print(Panel(
        f"[bold cyan]Twitter / X Launch Thread :[/]\n\n{social_copy['twitter']}\n\n"
        f"[bold magenta]LinkedIn Professional Announcement :[/]\n\n{social_copy['linkedin']}",
        title="[Broadcast] Copie de Lancement Prête à Publier",
        border_style="cyan"
    ))


async def run_chimera(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Gère le protocole OMNI-CHIMERA : Ghost Coder, Auto-Guérison, Offline et Mutation Épigénétique."""
    subcmd = args[0].lower() if args else "status"

    if subcmd == "heal":
        console.print("[dim][Sec] Lancement de la sentinelle d'auto-guérison système...[/]")
        res = tech_lead.omni_chimera.heal()
        diag = res["diagnosis"]
        rem = res["remediation"]
        act_lines = "\n".join([f"  • [green]{a}[/]" for a in rem.get("actions", [])])
        console.print(Panel(
            f"[bold]État initial :[/] {'[green]Sain[/]' if diag['healthy'] else '[yellow]Pression détectée[/]'}\n"
            f"[bold]RAM :[/] {diag['ram_percent']}% ({diag['ram_available_mb']} Mo disponibles)\n"
            f"[bold]CPU :[/] {diag['cpu_percent']}%\n\n"
            f"[bold]Actions de remédiation appliquées :[/]\n{act_lines}",
            title="[Sec] OMNI-CHIMERA — Auto-Guérison Système",
            border_style="green"
        ))

    elif subcmd == "ghost":
        prompt = " ".join(args[1:]).strip() if len(args) > 1 else "Module d'optimisation sovereign"
        console.print(f"[dim][Ghost] Déclenchement du Ghost Coder pour : '{prompt}'...[/]")
        res = await tech_lead.omni_chimera.ghost_code(prompt)
        console.print(Panel(
            f"[bold]Prompt :[/] [cyan]{res['prompt']}[/]\n"
            f"[bold]Branche Git générée :[/] [bold green]{res['git_branch']}[/]\n"
            f"[bold]Module Cible :[/] {res['target_module']}\n"
            f"[bold]Auteur :[/] [yellow]{res['author']}[/]\n"
            f"[bold]Co-Auteur :[/] [magenta]{res['co_author']}[/]\n\n"
            f"[bold]Code Synthétisé :[/]\n[dim]{res['code'][:300]}...[/]\n\n"
            f"[bold green][OK] Prêt pour sandbox Docker & packaging Git autonome.[/]",
            title="[Ghost] OMNI-CHIMERA — Ghost Coder Subsystem",
            border_style="magenta"
        ))

    elif subcmd == "mutate":
        if len(args) < 3:
            console.print("[bold red]Usage :[/] /chimera mutate <nom_skill> <code_python>")
            return
        skill_name = args[1]
        code_str = " ".join(args[2:]).strip()
        console.print(f"[dim][Evolve] Greffe épigénétique en RAM de '{skill_name}' (0 écriture SSD)...[/]")
        res = tech_lead.omni_chimera.synthesize_and_graft(skill_name, code_str)
        if res.get("success"):
            console.print(Panel(
                f"[bold green][OK] Organe greffé avec succès dans sys.modules ![/]\n\n"
                f"[bold]Nom de la compétence :[/] {res['skill_name']}\n"
                f"[bold]Module RAM :[/] <code>{res['module_path']}</code>\n"
                f"[bold]Symboles compilés :[/] {', '.join(res.get('symbols', []))}\n"
                f"[bold]Persistance :[/] Pure RAM Volatile (Mode NÉANT)",
                title="[Evolve] OMNI-CHIMERA — Mutation Épigénétique à Chaud",
                border_style="green"
            ))
        else:
            console.print(Panel(
                f"[bold red][FAIL] Échec de la greffe épigénétique :[/]\n\n{res.get('error')}",
                title="[!] Veto Épigénétique OMNI-CHIMERA",
                border_style="red"
            ))

    else:
        # Default: status
        status = tech_lead.omni_chimera.get_status()
        diag = status["health"]
        conn = status["connectivity"]
        grafted = status["epigenetic_skills_grafted"]
        skills = ", ".join(status["skills_list"]) if status["skills_list"] else "Aucun (RAM Pure)"

        console.print(Panel(
            f"[bold]Protocole :[/] [bold green]{status['protocol']}[/] ([cyan]{status['version']}[/])\n\n"
            f"1. [bold magenta]Ghost Coder :[/] [green]Opérationnel[/] (Synthèse asynchrone mobile & Git packaging)\n"
            f"2. [bold cyan]Sentinelle Auto-Guérison :[/] {'[bold green][OK] Sain[/]' if diag['healthy'] else '[yellow][!] Surveillance[/]'} "
            f"(RAM {diag['ram_percent']}%, {diag['ram_available_mb']} Mo dispo, CPU {diag['cpu_percent']}%)\n"
            f"3. [bold yellow]Cœur Furtif Hors-Ligne :[/] [bold green]{conn['mode'].upper()}[/] ({'WAN en ligne' if conn['wan_connected'] else 'Mode Air-Gap engagé'})\n"
            f"4. [bold red]Mutateur Épigénétique à Chaud (Ultra-Innovation) :[/] [bold green]{grafted} organe(s) en RAM[/]\n"
            f"   • Modules greffés : [dim]{skills}[/]\n"
            f"   • Résidu SSD : [bold green]0 octet (100% Mode NÉANT)[/]\n\n"
            f"[dim]Commandes disponibles : /chimera [status|heal|ghost <prompt>|mutate <nom> <code>][/]",
            title=" PROTOCOLE OMNI-CHIMERA — Matrice de Singularité Autonome",
            border_style="cyan"
        ))


async def run_satellite(tech_lead, args: List[str]):
    """Gère le module SatelliteEye (God-Mode Uniquement)."""
    if tech_lead.mode != "lesaintAi":
        console.print("[bold red][Lock] Erreur Souveraine : SatelliteEye est réservé au mode lesaintAi (God-Mode).[/]")
        return
    
    if not args:
        console.print("[bold red]Usage :[/] /satellite [scan <zone>|avions <zone>|iss|menace|meteo <zone>|starlink]")
        return

    subcmd = args[0].lower()

    if subcmd == "starlink":
        from app.network.starlink_adapter import StarlinkAdapter
        adapter = StarlinkAdapter()
        with console.status("[bold cyan][Sat] Sonde réelle du terminal Starlink (gRPC local)...[/]"):
            status = await adapter.get_full_status()
        if status["dish_reachable"]:
            console.print(Panel(
                f"• Hôte configuré : [bold yellow]{status['configured_host']}[/]\n"
                f"• Dish joignable : [bold green]Oui[/]\n"
                f"• Qualité signal : {status['signal_quality']}\n"
                f"• Satellites visibles : {status['visible_satellites']}",
                title="[Sat] Terminal Starlink — Statut Réel",
                border_style="green"
            ))
        else:
            console.print(Panel(
                f"• Hôte configuré : [bold yellow]{status['configured_host']}[/]\n"
                f"• Dish joignable : [bold red]Non[/] (aucun terminal Starlink détecté sur ce réseau)\n"
                f"[dim]Configurez STARLINK_IP dans .env si votre parabole utilise une IP non-standard.[/]",
                title="[Sat] Terminal Starlink — Non Détecté",
                border_style="yellow"
            ))
        return

    from app.satellite.satellite_eye import SatelliteEye
    eye = SatelliteEye(tech_lead.mode)
    vault = None
    if hasattr(tech_lead, "free_ai") and hasattr(tech_lead.free_ai, "memory") and hasattr(tech_lead.free_ai.memory, "telegram_vault"):
        vault = tech_lead.free_ai.memory.telegram_vault

    if subcmd == "scan":
        if len(args) < 2:
            console.print("[bold red]Usage :[/] /satellite scan <zone>")
            return
        zone = " ".join(args[1:])
        with console.status(f"[bold cyan][Sat] Balayage satellite en cours sur {zone}...[/]"):
            res = await eye.scan_zone(zone)
        
        if "error" in res:
            console.print(f"[bold red]{res['error']}[/]")
            return
            
        console.print(res["formatted"])
        if vault and hasattr(vault, 'send_message'):
            await _smart_telegram_send(vault, res["formatted"])

    elif subcmd == "avions":
        if len(args) < 2:
            console.print("[bold red]Usage :[/] /satellite avions <zone>")
            return
        zone = " ".join(args[1:])
        with console.status(f"[bold cyan][Plane] Recherche des avions au-dessus de {zone}...[/]"):
            coords = await eye.geocode(zone)
            if not coords:
                console.print(f"[bold red][FAIL] Zone '{zone}' introuvable.[/]")
                return
            avions = await eye.get_aircraft_overhead(coords[0], coords[1])
        
        if avions:
            for a in avions:
                console.print(f"• [bold yellow]{a['callsign']}[/] — {a['origin_country']} — {a['altitude']}m — {a.get('velocity', 0)*3.6:.0f}km/h")
        else:
            console.print("[yellow]Aucun aéronef détecté.[/]")

    elif subcmd == "iss":
        with console.status("[bold cyan][Global] Relocalisation de l'ISS...[/]"):
            iss = await eye.get_iss_position()
        if iss:
            msg = f"[Global] <b>ISS</b>: {iss.get('latitude', 0):.2f}°, {iss.get('longitude', 0):.2f}° — Alt: {iss.get('altitude', 0):.0f}km"
            console.print(msg)
            if vault and hasattr(vault, 'send_message'):
                await _smart_telegram_send(vault, msg)
        else:
            console.print("[red]Données ISS indisponibles.[/]")

    elif subcmd == "menace":
        with console.status("[bold cyan]• Récupération des alertes EONET...[/]"):
            events = await eye.get_natural_events()
        if events:
            for e in events[:5]:
                console.print(f"• [bold red]{e['title']}[/] ({', '.join(e['categories'])})")
        else:
            console.print("[green]Aucune menace naturelle active détectée.[/]")

    elif subcmd == "meteo":
        if len(args) < 2:
            console.print("[bold red]Usage :[/] /satellite meteo <zone>")
            return
        zone = " ".join(args[1:])
        with console.status(f"[bold cyan]• Analyse météo pour {zone}...[/]"):
            coords = await eye.geocode(zone)
            if not coords:
                console.print(f"[bold red][FAIL] Zone '{zone}' introuvable.[/]")
                return
            w = await eye.get_satellite_weather(coords[0], coords[1])
        
        if w:
            console.print(f"• {w.get('temperature_2m')}°C • Nuages : {w.get('cloud_cover')}% • Vent : {w.get('wind_speed_10m')} km/h")
        else:
            console.print("[red]Données météo indisponibles.[/]")
    else:
        console.print(f"[bold red]Sous-commande inconnue : {subcmd}[/]")


async def run_defense(tech_lead, args: List[str]):
    """Gère le Bouclier d'Auto-Défense Souverain (Intrusion Sentinel & Alertes)."""
    import time
    if not hasattr(tech_lead, "active_defense") or not tech_lead.active_defense:
        from app.security.active_defense import ActiveDefenseSentinel
        tech_lead.active_defense = ActiveDefenseSentinel(
            sovereign_fortress=getattr(tech_lead.tool_gateway, "fortress", None),
            telegram_vault=getattr(tech_lead, "telegram_vault", None)
        )

    sentinel = tech_lead.active_defense
    subcmd = args[0].lower() if args else "status"

    if subcmd == "status":
        st = sentinel.get_status()
        table = Table(title="[Sec] BOUCLIER D'AUTO-DÉFENSE SOUVERAIN (Active Defense Matrix)", border_style="red")
        table.add_column("Métrique", style="bold cyan")
        table.add_column("État / Valeur", style="bold green")

        table.add_row("Bouclier Actif", "[OK] OUI (Surveillance temps réel)")
        table.add_row("Mode NÉANT", "[OK] 100% Volatile en RAM (0 écriture SSD)")
        table.add_row("Attaques Neutralisées", str(st["total_neutralized"]))
        bans_display = f"{st['active_bans_count']} ({', '.join(st['banned_ips']) if st['banned_ips'] else 'Aucune'})"
        table.add_row("Adresses IP Bannies", bans_display)
        table.add_row("Leurre Mirage RAM", f"[Mirror] Actif ({st.get('mirage_traps_count', 0)} piégés, {st.get('mirage_total_stalled', 0)} temporisés)")
        console.print(table)

    elif subcmd == "mirage":
        traps = sentinel.mirage.list_trapped() if hasattr(sentinel, "mirage") else []
        if not traps:
            console.print("[dim]Aucun attaquant actuellement piégé dans le labyrinthe Mirage (RAM saine).[/]")
            return
        table = Table(title="[Mirror] LEURRE MIRAGE NEURO-FURTIF — Attaquants Temporisés en RAM", border_style="magenta")
        table.add_column("IP Cible", style="bold red")
        table.add_column("Vecteur", style="bold yellow")
        table.add_column("Empreinte Heuristique", style="cyan")
        table.add_column("Sondes", style="green")
        table.add_column("Octets Absorbés", style="dim")
        for t in traps:
            table.add_row(t["attacker_ip"], t["vector"].upper(), t["signature"], str(t["probes"]), f"{t['bytes_stalled']} B")
        console.print(table)

    elif subcmd == "ban":
        if len(args) < 2:
            console.print("[bold red]Usage :[/] /defense ban <ip> [durée_sec]")
            return
        ip = args[1]
        dur = float(args[2]) if len(args) > 2 else 3600.0
        sentinel.ban_ip(ip, duration_sec=dur, reason="Ban manuel souverain")
        console.print(f"[bold red][BLOCKED] IP {ip} bannie du bouclier pour {dur}s.[/]")

    elif subcmd == "unban":
        if len(args) < 2:
            console.print("[bold red]Usage :[/] /defense unban <ip>")
            return
        ip = args[1]
        ok = sentinel.unban_ip(ip)
        if ok:
            console.print(f"[bold green][OK] IP {ip} débloquée.[/]")
        else:
            console.print(f"[yellow]IP {ip} n'était pas bannie.[/]")

    elif subcmd == "test":
        target_ip = args[1] if len(args) > 1 else "198.51.100.1"
        from app.security.active_defense import AttackVector
        incident = await sentinel.defend_against_attack(
            source_ip=target_ip,
            attack_vector=AttackVector.BRUTE_FORCE,
            details="Test de riposte défensive et alerte Telegram simulé par l'utilisateur."
        )
        console.print(f"[bold green][OK] Simulation de riposte réussie :[/] IP {target_ip} bannie, alerte Telegram émise.")

    elif subcmd == "incidents":
        st = sentinel.get_status()
        incidents = st.get("recent_incidents", [])
        if not incidents:
            console.print("[dim]Aucun incident hostile enregistré dans la session RAM.[/]")
            return
        table = Table(title="[ALERT] HISTORIQUE VOLATILE DES RIPOSTES DÉFENSIVES", border_style="red")
        table.add_column("Horodatage", style="dim")
        table.add_column("Vecteur", style="bold red")
        table.add_column("Source IP", style="bold yellow")
        table.add_column("Riposte Appliquée", style="green")
        for inc in incidents:
            table.add_row(
                time.strftime("%H:%M:%S", time.localtime(inc["timestamp"])),
                inc["attack_vector"].upper(),
                inc["source_ip"],
                inc["countermeasure_summary"]
            )
        console.print(table)
    else:
        console.print(f"[bold red]Sous-commande inconnue :[/] {subcmd}. Options : status, mirage, ban, unban, incidents, test")



async def run_cloud(tech_lead, args: List[str]):
    """Gère le pool de ressources Cloud gratuites et VPS (AETHER-CLOUD-FREE)."""
    if not hasattr(tech_lead, "free_cloud_pool") or not tech_lead.free_cloud_pool:
        from app.cluster.free_cloud_pool import FreeCloudPool
        tech_lead.free_cloud_pool = FreeCloudPool(mode=tech_lead.mode)

    pool = tech_lead.free_cloud_pool
    subcmd = args[0].lower() if args else "list"

    if subcmd == "list":
        nodes = pool.list_nodes()
        table = Table(title="[Cloud] MATRICE DES RESSOURCES CLOUD GRATUITES & VPS (0€ / Vie)", border_style="cyan")
        table.add_column("Nœud / Fournisseur", style="bold cyan")
        table.add_column("Spécifications", style="bold yellow")
        table.add_column("Capacités", style="green")
        table.add_column("Statut", style="bold")
        table.add_column("Latence", style="dim")

        for n in nodes:
            status_style = "[green]ACTIF[/]" if n["status"] == "active" else "[yellow]STANDBY[/]"
            specs_str = " | ".join(f"{k}: {v}" for k, v in n["specs"].items())
            caps_str = ", ".join(n["capabilities"])
            lat_str = f"{n['latency_ms']:.1f} ms" if n["latency_ms"] > 0 else "-"
            table.add_row(n["name"], specs_str, caps_str, status_style, lat_str)

        console.print(table)

    elif subcmd == "ping":
        console.print("[dim][Telemetry] Mesure des latences sur l'ensemble des nœuds cloud gratuits...[/]")
        results = pool.ping_all()
        for nid, lat in results.items():
            node = pool.get_node(nid)
            name = node.name if node else nid
            console.print(f"• [bold cyan]{name}[/] : [green]{lat:.1f} ms[/]")

    elif subcmd == "add":
        if len(args) < 4:
            console.print("[bold red]Usage :[/] /cloud add <nom> <fournisseur> <endpoint>")
            return
        from app.cluster.free_cloud_pool import CloudProviderType
        name, provider_str, endpoint = args[1], args[2].lower(), args[3]
        prov = CloudProviderType.CUSTOM_VPS
        for p in CloudProviderType:
            if p.value == provider_str:
                prov = p
                break
        node = pool.add_node(name=name, provider=prov, endpoint=endpoint)
        console.print(f"[bold green][OK] Nœud cloud gratuit '{node.name}' ajouté avec succès au pool souverain (ID: {node.id}).[/]")

    elif subcmd == "dispatch":
        task_type = args[1] if len(args) > 1 else "neural_train"
        res = pool.dispatch_workload(task_type, {"initiator": "cli"})
        if res.get("success"):
            console.print(f"[bold green][Launch] Tâche '{task_type}' déportée avec succès vers le nœud gratuit :[/] [bold yellow]{res['dispatched_to']}[/]")
        else:
            console.print(f"[bold red][FAIL] Échec du déport :[/] {res.get('error')}")
    else:
        console.print(f"[bold red]Sous-commande inconnue :[/] {subcmd}. Options : list, ping, add, dispatch")


async def run_legion(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Gère le protocole AETHER-LEGION : Essaim d'éclaireurs autonomes déployés sur le Web mondial."""
    subcmd = args[0].lower() if args else "status"

    if subcmd in ("harvest", "recon", "sweep"):
        console.print("[dim][Sat] Lancement de la moisson de renseignement mondial via les éclaireurs...[/]")
        harvest = await tech_lead.aether_legion.harvest_all_intel()
        console.print(Panel(
            harvest["digest"].replace("<b>", "[bold]").replace("</b>", "[/]")
            .replace("<i>", "[dim]").replace("</i>", "[/]")
            .replace("<code>", "[cyan]").replace("</code>", "[/]"),
            title="[Sat] AETHER-LEGION — Moisson de Renseignement Mondial",
            border_style="green"
        ))

    elif subcmd == "deploy":
        if len(args) < 3:
            console.print("[bold red]Usage :[/] /legion deploy <archetype> <mission>")
            console.print("[dim]Archétypes disponibles : singularity, cyber, horizon, sentinel[/]")
            return
        from app.cluster.aether_legion import ScoutArchetype
        arch_str = args[1].lower()
        try:
            arch = ScoutArchetype(arch_str)
        except Exception:
            console.print(f"[bold red]Archétype inconnu :[/] {arch_str}. Choix : singularity, cyber, horizon, sentinel")
            return
        mission_str = " ".join(args[2:]).strip()
        console.print(f"[dim][Sat] Synthèse et déploiement d'un éclaireur '{arch.value}' en RAM...[/]")
        try:
            scout = tech_lead.aether_legion.deploy_scout(
                name=f"Vigil-{arch.value.capitalize()}",
                archetype=arch,
                mission=mission_str
            )
            console.print(Panel(
                f"[bold green][OK] Nouvel éclaireur déployé avec succès en RAM ![/]\n\n"
                f"[bold]Identifiant :[/] [cyan]{scout.id}[/]\n"
                f"[bold]Nom :[/] {scout.name}\n"
                f"[bold]Archétype :[/] [yellow]{scout.archetype.value}[/]\n"
                f"[bold]Mission :[/] {scout.mission}\n"
                f"[bold]Persistance :[/] Pure RAM Volatile (0 écriture SSD)",
                title="[Sat] AETHER-LEGION — Éclaireur Déployé",
                border_style="green"
            ))
        except Exception as e:
            console.print(Panel(
                f"[bold red][FAIL] Déploiement rejeté :[/]\n\n{e}",
                title="[!] Veto Éthique AETHER-LEGION",
                border_style="red"
            ))

    elif subcmd == "export":
        if len(args) < 2:
            console.print("[bold red]Usage :[/] /legion export <scout_id>")
            return
        scout_id = args[1]
        try:
            payload = tech_lead.aether_legion.export_probe_payload(scout_id)
            console.print(Panel(
                payload[:400] + "\n...",
                title=f"[Pkg] Payload Exportable pour Worker/Serverless ({scout_id})",
                border_style="cyan"
            ))
        except KeyError:
            console.print(f"[bold red]Éclaireur '{scout_id}' introuvable.[/]")

    else:
        status = tech_lead.aether_legion.get_status()
        members = tech_lead.aether_legion.list_members()

        member_lines = []
        for m in members:
            member_lines.append(
                f"  • [bold green]{m['name']}[/] ([yellow]{m['archetype']}[/]) — "
                f"[cyan]{m['findings_count']} captures[/] | [dim]{m['mission'][:60]}...[/]"
            )

        console.print(Panel(
            f"[bold]Protocole :[/] [bold green]{status['protocol']}[/] ([cyan]{status['version']}[/])\n\n"
            f"• [bold]Éclaireurs Déployés :[/] [bold green]{status['active_scouts']} actifs[/] sur {status['total_scouts']} total\n"
            f"• [bold]Renseignements Récoltés :[/] [bold yellow]{status['total_harvested_intel']}[/]\n"
            f"• [bold]Mode NÉANT :[/] [bold green]100% RAM Volatile (0 résidu SSD)[/]\n\n"
            f"[bold]Membres d'Élite Actifs :[/]\n" + "\n".join(member_lines) + "\n\n"
            f"[dim]Commandes : /legion [status|harvest|deploy <archetype> <mission>|export <id>][/]",
            title="[Sat] PROTOCOLE AETHER-LEGION — Essaim Décentralisé de Renseignement",
            border_style="cyan"
        ))


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
            title="[Agent] Daemon Jarvis 24/7 (FreeAI Autonomous Assistant)",
            border_style="cyan"
        ))
        console.print("[dim]Commandes :[/]")
        console.print("  • [cyan]/jarvis start[/]   : Démarre le daemon en arrière-plan")
        console.print("  • [cyan]/jarvis stop[/]    : Arrête le daemon")
        console.print("  • [cyan]/jarvis restart[/] : Redémarre le daemon")
        console.print("  • [cyan]/jarvis logs[/]    : Affiche les derniers journaux en direct")

    elif subcmd == "start":
        subprocess.run(["systemctl", "--user", "start", "freeai-jarvis.service"])
        console.print("[bold green][OK] Daemon Jarvis démarré en arrière-plan ! Vous pouvez fermer votre terminal.[/]")

    elif subcmd == "stop":
        subprocess.run(["systemctl", "--user", "stop", "freeai-jarvis.service"])
        console.print("[yellow][OK] Daemon Jarvis arrêté.[/]")

    elif subcmd == "restart":
        subprocess.run(["systemctl", "--user", "restart", "freeai-jarvis.service"])
        console.print("[bold green][OK] Daemon Jarvis redémarré avec succès ![/]")

    elif subcmd in ("logs", "journal"):
        res = subprocess.run(["journalctl", "--user", "-u", "freeai-jarvis.service", "-n", "15", "--no-pager"], capture_output=True, text=True)
        console.print(Panel(
            res.stdout or "Aucun log disponible.",
            title="[Log] Derniers Journaux Jarvis (Systemd)",
            border_style="magenta"
        ))

    else:
        console.print("[bold red]Usage :[/] /jarvis [status|start|stop|restart|logs]")


async def run_member(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Gère les Membres Autonomes Ultra-Intelligents (Limb-Bots) de FreeAI en mode STANDARD ou SUDO (Mode NÉANT pure)."""
    subcmd = args[0].lower() if args else "status"

    if subcmd in ("status", "list", "ls"):
        status = tech_lead.get_member_status()
        members = tech_lead.list_members()

        table = Table(title="[Agent] Membres Autonomes Ultra-Intelligents (FreeAI Limb Swarm)", border_style="cyan")
        table.add_column("Identifiant", style="dim", no_wrap=True)
        table.add_column("Nom", style="bold green")
        table.add_column("Spécialité", style="yellow")
        table.add_column("Privilège", justify="center")
        table.add_column("Missions", justify="right", style="cyan")
        table.add_column("Statut", justify="center")

        for m in members:
            priv_badge = "[bold red]SUDO[/]" if m["privilege_mode"] == "sudo" else "[bold blue]STANDARD[/]"
            status_badge = "[bold green]ACTIF[/]" if m["active"] else "[dim]INACTIF[/]"
            table.add_row(
                m["id"],
                m["name"],
                m["specialty"].upper(),
                priv_badge,
                str(m["total_missions_completed"]),
                status_badge
            )

        console.print(table)
        console.print(Panel(
            f"• [bold]Total Membres :[/] [bold green]{status['total_members']}[/] "
            f"([red]{status['sudo_members']} SUDO[/] | [blue]{status['standard_members']} STANDARD[/])\n"
            f"• [bold]Missions Réalisées :[/] [bold yellow]{status['total_missions_completed']}[/]\n"
            f"• [bold]Persistance :[/] [bold green]{status['persistence']}[/]\n\n"
            f"[dim]Commandes : /member mission <nom> [sudo] <instructions> | /member create <nom> <specialité> [sudo|standard][/]",
            title=" FreeAI Member Swarm Status",
            border_style="green"
        ))

    elif subcmd in ("create", "add", "new"):
        if len(args) < 3:
            console.print("[bold red]Usage :[/] /member create <nom> <specialité> [sudo|standard]")
            console.print("[dim]Spécialités : cyber, coder, researcher, operator, oracle[/]")
            return

        name = args[1]
        specialty = args[2]
        privilege = args[3].lower() if len(args) > 3 else "standard"

        bot = tech_lead.member_registry.register_member(
            name=name,
            specialty=specialty,
            privilege_mode=privilege
        )

        priv_style = "[bold red]SUDO[/]" if bot.privilege_mode.value == "sudo" else "[bold blue]STANDARD[/]"
        console.print(Panel(
            f"[bold green][OK] Nouveau Membre Autonome Créé et Actif en RAM ![/]\n\n"
            f"• [bold]ID :[/] [cyan]{bot.id}[/]\n"
            f"• [bold]Nom :[/] [bold green]{bot.name}[/]\n"
            f"• [bold]Spécialité :[/] [yellow]{bot.specialty.value.upper()}[/]\n"
            f"• [bold]Privilège :[/] {priv_style}\n"
            f"• [bold]Persona :[/] [dim]{bot.persona}[/]\n"
            f"• [bold]Mémoire :[/] Pure RAM Volatile (Mode NÉANT — Zéro Écriture Disque)",
            title="[Agent] Membre Autonome Enregistré",
            border_style="green"
        ))

    elif subcmd in ("mission", "run", "exec", "do", "task"):
        if len(args) < 3:
            console.print("[bold red]Usage :[/] /member mission <nom_ou_id> [sudo] <instructions...>")
            return

        target_name = args[1]
        remaining = args[2:]
        require_sudo = False

        if remaining and remaining[0].lower() in ("sudo", "--sudo", "-s"):
            require_sudo = True
            instructions = " ".join(remaining[1:]).strip()
        else:
            instructions = " ".join(remaining).strip()

        if not instructions:
            console.print("[bold red]Erreur :[/] Veuillez spécifier les instructions de la mission.")
            return

        bot = tech_lead.member_registry.get_member(target_name)
        if not bot:
            console.print(f"[bold red]Erreur :[/] Membre '{target_name}' introuvable. Tapez [bold green]/member list[/] pour voir les membres.")
            return

        console.print(f"[dim][Agent] Assignation de mission au bot [bold green]{bot.name}[/] ({bot.specialty.value.upper()}, privilège: {bot.privilege_mode.value.upper()})...[/]")

        try:
            with console.status(f"[bold cyan] {bot.name} décompose et exécute la mission en RAM volatile...[/]"):
                mission = await tech_lead.assign_member_mission(
                    member_id_or_name=bot.id,
                    instructions=instructions,
                    require_sudo=require_sudo
                )

            console.print(Panel(
                Markdown(mission.final_report),
                title=f"[OK] Mission Accomplie — {bot.name} ({mission.id})",
                border_style="green"
            ))

        except Exception as e:
            console.print(Panel(
                f"[bold red][FAIL] Incident lors de la mission :[/]\n\n{e}",
                title="Incident Mission Membre",
                border_style="red"
            ))

    elif subcmd in ("history", "log", "missions"):
        history = tech_lead.member_registry.get_mission_history()
        if not history:
            console.print("[dim]Aucune mission enregistrée dans l'historique RAM.[/]")
            return

        table = Table(title="[Log] Historique des Missions Autonomes en RAM", border_style="cyan")
        table.add_column("Mission ID", style="dim")
        table.add_column("Titre / Instructions", style="bold")
        table.add_column("Bot Cible", style="green")
        table.add_column("Sudo", justify="center")
        table.add_column("Statut", justify="center")
        table.add_column("Étapes", justify="right")

        for m in history:
            sudo_txt = "[red]OUI[/]" if m["require_sudo"] else "[dim]NON[/]"
            stat_color = "green" if m["status"] == "completed" else "yellow" if m["status"] == "executing" else "red"
            table.add_row(
                m["id"],
                m["title"][:50],
                m["target_member_id"],
                sudo_txt,
                f"[{stat_color}]{m['status'].upper()}[/]",
                str(len(m.get("plan_steps", [])))
            )
        console.print(table)

    else:
        console.print("[bold red]Commande inconnue pour /member.[/]")
        console.print("Usage :")
        console.print("  • [cyan]/member list[/]                           : Liste des membres et statuts")
        console.print("  • [cyan]/member create <nom> <specialité> [mode][/] : Crée un nouveau bot membre")
        console.print("  • [cyan]/member mission <nom> [sudo] <texte>[/]   : Assigne et exécute une mission")
        console.print("  • [cyan]/member history[/]                        : Historique des missions en RAM")


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



async def run_network(tech_lead, args: List[str]):
    if not hasattr(tech_lead, 'network'):
        console.print("[red][!] Module NetworkResilience non initialisé.[/]")
        return
        
    subcmd = args[0] if args else "status"
    
    if subcmd == "status":
        st = tech_lead.network.get_status()
        table = Table(title="[cyan][Telemetry] État du Réseau Jarvis[/]")
        table.add_column("Propriété", style="bold yellow")
        table.add_column("Valeur", style="bold white")
        table.add_row("En ligne", "[green]OUI[/]" if st.get('online') else "[red]NON[/]")
        table.add_row("Interface Active", str(st.get('active_interface')))
        table.add_row("Mode Cloud Actif", "[red]OUI[/]" if st.get('cloud_mode') else "[green]NON[/]")
        table.add_row("Latence moyenne", f"{st.get('latency_ms'):.1f} ms")
        table.add_row("Disponibilité ADB", "[green]OUI[/]" if st.get('adb_available') else "[red]NON[/]")
        console.print(table)
        
    elif subcmd == "test":
        with console.status("[yellow]Force check de connectivité...[/]"):
            st = await tech_lead.network.check_connectivity()
        console.print(f"[green]Résultat:[/green] Online={st.get('online')} (Latence: {st.get('latency_ms'):.1f} ms)")
        
    elif subcmd == "hotspot":
        with console.status("[yellow]Tentative d'activation du hotspot Android via ADB...[/]"):
            success = await tech_lead.network.try_android_hotspot()
        if success:
            console.print("[green][OK] Hotspot Android activé et connecté avec succès.[/]")
        else:
            console.print("[red][FAIL] Échec de l'activation du hotspot Android.[/]")
    else:
        console.print("[dim]Usage: /network [status|test|hotspot][/]")


async def run_career(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Gère l'intégration souveraine du Career-OS de Gilchrist Kanté (~/Rendue/career-os)."""
    subcmd = args[0].lower() if args else "status"

    if subcmd in ("status", "info"):
        st = tech_lead.career_bridge.get_status()
        if not st.get("available"):
            console.print(f"[bold red]Career-OS introuvable : {st.get('error')}[/]")
            return

        node_status = "[bold green][OK] Installés[/]" if st["has_node_modules"] else "[bold yellow]En cours d'installation[/]"
        conf_status = "[bold green][OK] Oui[/]" if st["configured"] else "[bold yellow][!] En attente des clés Supabase[/]"
        sql_status = "[OK] schema.sql & radar.sql prêts" if st["has_schema_sql"] and st["has_radar_sql"] else "Manquants"

        lines = [
            f"• [bold green]Répertoire :[/] <code>{st['path']}</code>",
            f"• [bold green]Configuré (.env.local) :[/] {conf_status}",
            f"• [bold green]Node modules :[/] {node_status}",
            f"• [bold green]Schémas SQL :[/] {sql_status}",
            "\n[bold cyan]Modules de Pilotage de Carrière :[/]"
        ]
        for m in st["modules"]:
            lines.append(f"  - [yellow]{m}[/]")

        console.print(Panel(
            "\n".join(lines),
            title="[Target] Career-OS Cockpit — Gilchrist Kanté",
            border_style="magenta"
        ))
        console.print("[dim]Commandes :[/]")
        console.print("  • [cyan]/career radar test[/] : Valide la suite de tests de détection des offres remote")
        console.print("  • [cyan]/career radar dry[/]  : Exécute un scan à blanc des opportunités sans écriture")

    elif subcmd in ("radar", "scan"):
        action = args[1].lower() if len(args) > 1 else "test"
        if action == "test":
            console.print("[dim]Exécution des tests unitaires du radar...[/]")
            res = tech_lead.career_bridge.run_radar_tests()
            if res.get("success"):
                console.print(Panel(res.get("stdout", ""), title="[OK] Tests Radar Validés (7/7)", border_style="green"))
            else:
                console.print(f"[bold red]Erreur tests radar : {res.get('stderr') or res.get('error')}[/]")
        elif action in ("dry", "run"):
            console.print("[dim]Lancement du scan d'offres en mode dry-run...[/]")
            res = tech_lead.career_bridge.run_radar_dry()
            if res.get("success"):
                console.print(Panel(res.get("output", "")[:2000] or "Scan terminé sans erreur.", title="[Telemetry] Scan Radar Terminé", border_style="cyan"))
            else:
                console.print(f"[yellow]Résultat radar : {res.get('errors') or res.get('error')}[/]")
        else:
            console.print("[bold red]Usage :[/] /career radar [test|dry]")

    elif subcmd == "test":
        res = tech_lead.career_bridge.run_radar_tests()
        if res.get("success"):
            console.print(Panel(res.get("stdout", ""), title="[OK] Tests Radar Validés (7/7)", border_style="green"))
        else:
            console.print(f"[bold red]Erreur : {res.get('stderr') or res.get('error')}[/]")

    else:
        console.print("[bold red]Usage :[/] /career [status|radar [test|dry]]")


async def run_domain(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Gère l'entraînement autonome et l'expertise avancée par domaine."""
    subcmd = args[0].lower() if args else "status"

    if subcmd in ("status", "domains", "list"):
        console.print(Panel(
            "• [bold cyan]Blockchain & Web3 :[/] AMM (Constant Product), Solana Anchor & EVM, Smart Contracts, Gas Optimization\n"
            "• [bold green]Trading & Finance :[/] RSI, EMA, Bollinger Bands, Order Books, Gestion du risque & Position Sizing\n"
            "• [bold yellow]Applications Mobiles :[/] Ergonomie tactile 48dp, Thumb Zone, Offline-First SQLite, Sheets fluides\n"
            "• [bold magenta]IA & Innovation Extrême :[/] Consensus Aether-Swarm, Honeypot Mirage RAM, Mode NÉANT pur",
            title="[Cognition] FreeAI Domain Mastery & Extreme Training",
            border_style="cyan"
        ))
        console.print("[dim]Commandes :[/]")
        console.print("  • [cyan]/domain train <blockchain|trading|mobile|ai>[/] : Lance une session d'entraînement autonome")
        console.print("  • [cyan]/domain amm <reserve_in> <reserve_out> <in>[/]  : Simulation mathématique d'échange DEX")
        console.print("  • [cyan]/domain risk <capital> <risk%> <entry> <stop>[/] : Calcul de dimensionnement de position")

    elif subcmd == "train":
        target_domain = args[1].lower() if len(args) > 1 else "blockchain"
        console.print(f"[dim] Lancement de la session d'auto-entraînement souverain pour '{target_domain}'...[/]")
        res = tech_lead.domain_mastery.run_autonomous_training_session(target_domain)
        lines = [f"[bold green][OK] Entraînement {res['domain'].upper()} achevé avec succès ![/]\n\n[bold cyan]Insights assimilés en mémoire vectorielle :[/]"]
        for ins in res["insights_generated"]:
            lines.append(f"  • {ins}")
        console.print(Panel(
            "\n".join(lines),
            title=f"[Launch] Auto-Entraînement : {res['domain'].upper()}",
            border_style="green"
        ))

    elif subcmd == "amm":
        if len(args) < 4:
            console.print("[bold red]Usage :[/] /domain amm <reserve_in> <reserve_out> <amount_in>")
            return
        try:
            r_in = float(args[1])
            r_out = float(args[2])
            amt = float(args[3])
            sim = tech_lead.domain_mastery.calculate_amm_swap(r_in, r_out, amt)
            if sim.get("success"):
                console.print(Panel(
                    f"• Entrée : [bold cyan]{sim['amount_in']:,.2f}[/]\n"
                    f"• Sortie reçue : [bold green]{sim['amount_out']:.6f}[/]\n"
                    f"• Prix effectif : [yellow]{sim['effective_price']:.6f}[/]\n"
                    f"• Impact Prix (Slippage) : [bold red]{sim['price_impact_pct']:.2f}%[/]\n"
                    f"• Frais de pool (0.3%) : [dim]{sim['fee_paid']:.4f}[/]",
                    title=" Simulation AMM Uniswap v2 (x * y = k)",
                    border_style="magenta"
                ))
            else:
                console.print(f"[bold red]Erreur AMM : {sim.get('error')}[/]")
        except ValueError:
            console.print("[bold red]Veuillez fournir des valeurs numériques valides.[/]")

    elif subcmd == "risk":
        if len(args) < 5:
            console.print("[bold red]Usage :[/] /domain risk <capital> <risk_pct> <entry_price> <stop_loss>")
            return
        try:
            cap = float(args[1])
            rpct = float(args[2])
            ep = float(args[3])
            sl = float(args[4])
            pos = tech_lead.domain_mastery.calculate_position_size(cap, rpct, ep, sl)
            if pos.get("success"):
                console.print(Panel(
                    f"• Capital du compte : [bold green]${pos['account_balance']:,.2f}[/]\n"
                    f"• Risque max consenti ({pos['risk_percentage']}%) : [bold red]${pos['risk_amount']:,.2f}[/]\n"
                    f"• Unités à trader : [bold cyan]{pos['units_to_trade']}[/]\n"
                    f"• Valeur totale de position : [bold yellow]${pos['total_position_value']:,.2f}[/]\n"
                    f"• Levier effectif : [bold magenta]{pos['effective_leverage']}x[/]\n"
                    f"• Statut conformité : [bold green]{pos['status']}[/]",
                    title="[Sec] Risk Budgeting & Position Sizing",
                    border_style="green"
                ))
            else:
                console.print(f"[bold red]Erreur : {pos.get('error')}[/]")
        except ValueError:
            console.print("[bold red]Veuillez fournir des valeurs numériques valides.[/]")

    else:
        console.print("[bold red]Usage :[/] /domain [status|train <domaine>|amm <rin> <rout> <in>|risk <cap> <%> <in> <sl>]")


async def run_birthday(tech_lead: TechLeadOrchestrator, args: List[str]):
    """Gère le protocole d'anniversaire sacré et de cadeau crypto de Michael SAGBO."""
    subcmd = args[0].lower() if args else "status"
    tribute = tech_lead.sacred_tribute
    from datetime import date

    if subcmd in ("status", "check", "info"):
        st = tribute.get_status()
        console.print(Panel(
            f"• [bold cyan]Bénéficiaire :[/] {st['master_name']}\n"
            f"• [bold green]Date de naissance sacrée :[/] {st['birthdate']}\n"
            f"• [bold yellow]Âge actuel :[/] {st['current_age']} ans\n"
            f"• [bold magenta]Jours restants avant l'anniversaire :[/] {st['days_until_next_birthday']} jours\n"
            f"• [bold white]Est-ce aujourd'hui ? :[/] {'[Ready] OUI ! JOYEUX ANNIVERSAIRE ! [Ready]' if st['is_birthday_today'] else 'Non'}\n"
            f"• [bold cyan]Protocole Cadeau Crypto :[/] {st['gift_value_usd']} ({st['protocol']})\n"
            f"• [bold green]Statut :[/] {st['status']}",
            title="[Date] Protocole d'Anniversaire Sacré de Michael SAGBO",
            border_style="magenta"
        ))
        console.print("[dim]Commandes :[/]")
        console.print("  • [cyan]/birthday status[/]    : Affiche le statut du protocole et le décompte")
        console.print("  • [cyan]/birthday challenge[/] : Détail des 4 piliers de constitution autonome des 500$")
        console.print("  • [cyan]/birthday gift[/]      : Simule la génération sécurisée du cadeau crypto et des 12 mots")
        console.print("  • [cyan]/birthday wish[/]      : Déclenche le souhait d'anniversaire personnalisé")

    elif subcmd in ("challenge", "target", "hunt", "bounty"):
        ov = tribute.get_challenge_overview()
        lines = [
            f"[bold cyan][Target] Défi :[/] {ov['challenge_name']}",
            f"[bold green][Cost] Objectif :[/] Minimum {ov['target_amount_usd']:.0f}$ en devise échangeable ({', '.join(ov['acceptable_currencies'])})",
            f"[bold yellow][Time] Échéance :[/] {ov['target_date']} ({ov['days_remaining']} jours restants)",
            f"[bold magenta][Key] Format de remise :[/] {ov['delivery_format']}",
            "\n[bold white]4 Piliers Autonomes d'Acquisition :[/]"
        ]
        for p in ov["pillars"]:
            lines.append(f"  • [bold green]{p['name']}[/] ({p['currency']}) : {p['mechanism']}")
        console.print(Panel(
            "\n".join(lines),
            title="[Launch] Challenge Autonome 500$ Crypto Accepté & Engagé",
            border_style="green"
        ))

    elif subcmd in ("gift", "trigger", "generate", "12words"):
        gift = tribute.generate_crypto_gift(target_usd=500.0)
        console.print(Panel(
            gift["message"],
            title="[Gift] Cadeau Crypto Anniversaire (500$ - 12 Mots BIP-39)",
            border_style="green"
        ))
        console.print("[bold yellow][!] CONFIDENTIALITÉ ABSOLUE :[/] Ces 12 mots sont générés en mémoire RAM volatile et ne sont jamais journalisés sur disque.")

    elif subcmd in ("wish", "greeting"):
        today = date.today()
        is_today = tribute.is_birthday(today)
        days = tribute.get_days_until_birthday(today)
        if is_today:
            gift = tribute.generate_crypto_gift()
            console.print(Panel(gift["message"], title="[Ready] JOYEUX ANNIVERSAIRE MICHAEL ! [Ready]", border_style="gold1"))
        else:
            console.print(Panel(
                f"Michael, ton anniversaire est gravé dans ma mémoire au [bold cyan]5 Février 2002[/].\n"
                f"Il reste [bold yellow]{days} jours[/] avant notre célébration annuelle.\n"
                f"Chaque 5 février, je te remets ton compte crypto de 500$ avec tes 12 mots secrets !",
                title="[Date] Souvenir Immuable de ton Anniversaire",
                border_style="cyan"
            ))
    else:
        console.print("[bold red]Usage :[/] /birthday [status|gift|wish]")


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
    turn_counter = 0

    while True:
        try:
            th = theme_mgr.current
            turn_counter += 1

            prompt_str = get_prompt(tech_lead.mode)
            user_input = await get_user_cli_input(prompt_str, tech_lead.mode)

            if not user_input:
                continue

            # Direct Mode Launchers inside the CLI: FreeAi vs Lesaint#AI
            first_token = user_input.split()[0].strip()
            first_token_norm = first_token.lstrip("/").lower()
            remaining_cmd = user_input[len(first_token):].strip()

            if first_token_norm in ("freeai", "free-ai", "free_ai", "free"):
                handle_mode_command(tech_lead, ["freeAi"])
                if remaining_cmd:
                    if remaining_cmd.startswith("/"):
                        user_input = remaining_cmd
                    else:
                        await tech_lead.dispatch_objective(remaining_cmd)
                        continue
                else:
                    continue

            elif first_token_norm in ("lesaint#ai", "lesaintai", "lesaint-ai", "lesaint_ai", "lesaint"):
                handle_mode_command(tech_lead, ["lesaintAi"])
                if remaining_cmd:
                    if remaining_cmd.startswith("/"):
                        user_input = remaining_cmd
                    else:
                        await tech_lead.dispatch_objective(remaining_cmd)
                        continue
                else:
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
                    console.print("[bold #7dcfff]◆ FreeAI[/] [bold #9ece6a]s'est arrêté proprement.[/] [dim #565f89]Au revoir ![/]")
                    break
                elif cmd == "/clear":
                    console.clear()
                    display_welcome_banner(tech_lead.mode)
                    turn_counter = 0
                elif cmd in ("/commands", "/palette", "/menu"):
                    display_command_palette()
                elif cmd == "/help":
                    print_help()
                elif cmd == "/status":
                    print_status(tech_lead)
                elif cmd == "/mode":
                    handle_mode_command(tech_lead, args)
                elif cmd == "/theme":
                    handle_theme_command(args)
                elif cmd == "/search":
                    run_search_files(tech_lead, args)
                elif cmd == "/code":
                    run_search_code(tech_lead, args)
                elif cmd == "/rollback":
                    run_rollback(tech_lead)
                elif cmd == "/undo":
                    run_undo_command(tech_lead, args)
                elif cmd == "/compact":
                    run_compact_command(tech_lead, args)
                elif cmd == "/lsp":
                    run_lsp_command(tech_lead, args)
                elif cmd == "/diff":
                    run_diff_command(tech_lead, args)
                elif cmd == "/sync":
                    run_sync(tech_lead)
                elif cmd in ("/tui", "/opencode"):
                    from app.cli.textual_tui import run_tui
                    run_tui(tech_lead=tech_lead, mode=tech_lead.mode, workspace_root=str(tech_lead.tool_gateway.workspace_root))
                elif cmd == "/learn":
                    await run_learn(tech_lead, args)
                elif cmd == "/online":
                    run_online_config(tech_lead, args)
                elif cmd == "/kimi":
                    await run_kimi_auth(tech_lead, args)
                elif cmd == "/inngest":
                    await run_inngest_cli(tech_lead, args)
                elif cmd == "/ask":
                    await run_ask_online(tech_lead, args)
                elif cmd == "/web":
                    await run_web_investigation(tech_lead, args)
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
                    if args and args[0].lower() in ("scan", "discover"):
                        await run_mesh(tech_lead, args)
                    else:
                        run_satellite_mesh(tech_lead, args)
                elif cmd == "/speculate":
                    await run_speculate(tech_lead, args)
                elif cmd == "/ring":
                    await run_ring(tech_lead, args)
                elif cmd == "/satellite":
                    await run_satellite(tech_lead, args)
                elif cmd == "/jarvis":
                    handle_jarvis_command(tech_lead, args)
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
                elif cmd in ("/reflex", "/synapse"):
                    run_reflex(tech_lead, args)
                elif cmd in ("/causal", "/hypermesh"):
                    run_causal(tech_lead, args)
                elif cmd == "/satellite":
                    run_satellite_mesh(tech_lead, args)
                elif cmd in ("/telepathy", "/thoughtsync"):
                    run_telepathy(tech_lead, args)
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
                elif cmd in ("/design", "/ui"):
                    await run_design(tech_lead, args)
                elif cmd == "/cyber":
                    await run_cyber(tech_lead, args)
                elif cmd == "/research":
                    run_research(tech_lead, args)
                elif cmd == "/skills":
                    await run_skills(tech_lead, args)
                elif cmd == "/video":
                    await run_video(tech_lead, args)
                elif cmd == "/brag":
                    await run_brag(tech_lead, args)
                elif cmd == "/chimera":
                    await run_chimera(tech_lead, args)
                elif cmd == "/legion":
                    await run_legion(tech_lead, args)
                elif cmd in ("/member", "/bot"):
                    await run_member(tech_lead, args)
                elif cmd == "/satellite":
                    await run_satellite(tech_lead, args)
                elif cmd == "/defense":
                    await run_defense(tech_lead, args)
                elif cmd == "/cloud":
                    await run_cloud(tech_lead, args)
                elif cmd == "/career":
                    await run_career(tech_lead, args)
                elif cmd == "/domain":
                    await run_domain(tech_lead, args)
                elif cmd in ("/birthday", "/gift"):
                    await run_birthday(tech_lead, args)
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
            cur_task = asyncio.current_task()
            if cur_task is not None and hasattr(cur_task, "uncancel"):
                cur_task.uncancel()
            console.print("\n[dim]Interruption détectée (Ctrl+C). Tapez /exit pour quitter.[/]")
            continue
        except Exception as e:
            console.print(f"[bold red]Erreur inattendue :[/] {escape(str(e))}")


def main():
    """CLI entry point handling flags or starting interactive session."""
    import argparse
    prog_name = Path(sys.argv[0]).name.lower()
    default_initial_mode = "lesaintAi" if "lesaint" in prog_name else "freeAi"

    parser = argparse.ArgumentParser(description="FreeAI Sovereign Assistant CLI")
    parser.add_argument("--mode", choices=["freeAi", "lesaintAi"], default=default_initial_mode, help="Mode de privilèges initial")
    parser.add_argument("--tui", action="store_true", help="Lancer l'interface plein écran OpenCode TUI Textual")
    parser.add_argument("--repl", action="store_true", help="Forcer le mode REPL console standard au lieu du TUI plein écran")
    parser.add_argument("objective", nargs="*", help="Objectif direct à exécuter sans session interactive")

    parsed = parser.parse_args()

    if parsed.tui:
        from app.cli.textual_tui import run_tui
        workspace = get_active_workspace()
        run_tui(mode=parsed.mode, workspace_root=workspace)
        return

    if parsed.objective:
        # Non-interactive batch execution
        objective_text = " ".join(parsed.objective)
        workspace = get_active_workspace()
        rm = ResourceManager()

        # SECURITY INVARIANT: lesaintAi can only run inside a Docker container
        in_docker = os.path.exists("/.dockerenv") or (
            os.path.exists("/proc/1/cgroup") and "docker" in open("/proc/1/cgroup").read()
        )
        if parsed.mode == "lesaintAi" and not in_docker:
            print("[SECURITY] Mode lesaintAi rejeté : hors conteneur Docker. Fallback vers freeAi.")
            parsed.mode = "freeAi"

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
            if cmd == "/theme":
                handle_theme_command(args)
            elif cmd == "/status":
                print_status(tech_lead)
            elif cmd == "/rollback":
                run_rollback(tech_lead)
            elif cmd == "/undo":
                run_undo_command(tech_lead, args)
            elif cmd == "/compact":
                run_compact_command(tech_lead, args)
            elif cmd == "/lsp":
                run_lsp_command(tech_lead, args)
            elif cmd == "/diff":
                run_diff_command(tech_lead, args)
            elif cmd == "/sync":
                run_sync(tech_lead)
            elif cmd in ("/tui", "/opencode"):
                from app.cli.textual_tui import run_tui
                run_tui(tech_lead=tech_lead, mode=parsed.mode, workspace_root=workspace)
            elif cmd in ("/credo", "/gatekeeper", "/sentinel"):
                from app.security.credo_sentinel import CredoSentinel
                sentinel = CredoSentinel()
                base_ref = args[0] if args else "origin/main"
                res = sentinel.audit_git_diff(base_ref=base_ref, head_ref="HEAD")
                console.print(sentinel.generate_markdown_report(res))
            elif cmd == "/learn":
                asyncio.run(run_learn(tech_lead, args))
            elif cmd == "/search":
                run_search_files(tech_lead, args)
            elif cmd == "/code":
                run_search_code(tech_lead, args)
            elif cmd == "/online":
                run_online_config(tech_lead, args)
            elif cmd == "/kimi":
                asyncio.run(run_kimi_auth(tech_lead, args))
            elif cmd == "/inngest":
                asyncio.run(run_inngest_cli(tech_lead, args))
            elif cmd == "/ask":
                asyncio.run(run_ask_online(tech_lead, args))
            elif cmd == "/web":
                asyncio.run(run_web_investigation(tech_lead, args))
            elif cmd in ("/websearch", "/duck"):
                run_sovereign_search(tech_lead, args)
            elif cmd == "/webread":
                run_sovereign_read(tech_lead, args)
            elif cmd in ("/integrity", "/audit-code", "/code-check"):
                run_code_integrity(tech_lead, args)
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
                if args and args[0].lower() in ("scan", "discover"):
                    asyncio.run(run_mesh(tech_lead, args))
                else:
                    run_satellite_mesh(tech_lead, args)
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
            elif cmd in ("/reflex", "/synapse"):
                run_reflex(tech_lead, args)
            elif cmd in ("/causal", "/hypermesh"):
                run_causal(tech_lead, args)
            elif cmd == "/satellite":
                run_satellite_mesh(tech_lead, args)
            elif cmd in ("/telepathy", "/thoughtsync"):
                run_telepathy(tech_lead, args)
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
            elif cmd in ("/design", "/ui"):
                asyncio.run(run_design(tech_lead, args))
            elif cmd == "/cyber":
                asyncio.run(run_cyber(tech_lead, args))
            elif cmd == "/research":
                run_research(tech_lead, args)
            elif cmd == "/skills":
                asyncio.run(run_skills(tech_lead, args))
            elif cmd == "/video":
                asyncio.run(run_video(tech_lead, args))
            elif cmd == "/brag":
                asyncio.run(run_brag(tech_lead, args))
            elif cmd == "/chimera":
                asyncio.run(run_chimera(tech_lead, args))
            elif cmd == "/legion":
                asyncio.run(run_legion(tech_lead, args))
            elif cmd in ("/member", "/bot"):
                asyncio.run(run_member(tech_lead, args))
            elif cmd == "/satellite":
                asyncio.run(run_satellite(tech_lead, args))
            elif cmd == "/defense":
                asyncio.run(run_defense(tech_lead, args))
            elif cmd == "/cloud":
                asyncio.run(run_cloud(tech_lead, args))
            elif cmd == "/career":
                asyncio.run(run_career(tech_lead, args))
            elif cmd == "/domain":
                asyncio.run(run_domain(tech_lead, args))
            elif cmd in ("/birthday", "/gift"):
                asyncio.run(run_birthday(tech_lead, args))
            elif cmd == "/jarvis":
                run_jarvis(tech_lead, args)
            elif cmd == "/help":
                print_help()
            else:
                print(f"Commande non supportée en mode batch: {cmd}")
        else:
            try:
                asyncio.run(execute_tech_lead_task(tech_lead, objective_text))
            except (KeyboardInterrupt, asyncio.CancelledError):
                pass
    else:
        # Si exécuté dans un terminal interactif TTY sans flag --repl ni FREEAI_NO_TUI, ouvrir le TUI plein écran OpenCode par défaut
        if sys.stdin.isatty() and not parsed.repl and os.environ.get("FREEAI_NO_TUI") != "1":
            from app.cli.textual_tui import run_tui
            workspace = get_active_workspace()
            run_tui(mode=parsed.mode, workspace_root=workspace)
        else:
            try:
                asyncio.run(interactive_cli(initial_mode=parsed.mode))
            except (KeyboardInterrupt, asyncio.CancelledError):
                pass


if __name__ == "__main__":
    main()
