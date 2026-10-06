"""Agent Stream Watcher & Real-Time Tool Call Formatter (Inspiré de my_jarvis/watch).
Permet de visualiser en temps réel les délibérations de l'agent, ses appels d'outils et leurs résultats :
- '💬 [Thought / Chat]' : flux de raisonnement et messages.
- '▶ [Tool Call]' : nom de l'outil et arguments formatés.
- '↳ [Tool Result]' : résultat de l'exécution condensé.

S'intègre directement avec SessionEvents, EventHub et le TUI / CLI d'OpenCode.
Mode NÉANT : 100% en RAM, zéro fichier temporaire sur SSD.
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime


class AgentStreamFormatter:
    """Formate les événements d'agents pour un affichage terminal ultra-lisible."""

    @staticmethod
    def format_event(event: Dict[str, Any], max_len: int = 140) -> str:
        """Transforme un événement brut (SessionEvent / PhantomBus) en ligne télémétrique."""
        ev_type = event.get("type", "")
        data = event.get("data", {})
        ts = event.get("timestamp", datetime.now().strftime("%H:%M:%S"))

        if ev_type in ("thought", "message", "agent_message"):
            content = data.get("content") or data.get("text") or str(data)
            clean = content.replace("\n", " ").strip()
            return f"[{ts}] 💬 {clean[:max_len]}"

        elif ev_type in ("tool_call", "tool_use", "call_tool"):
            tool_name = data.get("name") or data.get("tool") or "unknown_tool"
            args = data.get("arguments") or data.get("input") or {}
            args_str = json.dumps(args, ensure_ascii=False) if isinstance(args, dict) else str(args)
            return f"[{ts}] ▶ \033[1;36m{tool_name}\033[0m: {args_str[:max_len]}"

        elif ev_type in ("tool_result", "tool_output", "result"):
            tool_name = data.get("name") or data.get("tool") or ""
            out = data.get("output") or data.get("result") or data.get("content") or ""
            out_str = str(out).replace("\n", " ").strip()
            prefix = f"({tool_name}) " if tool_name else ""
            return f"[{ts}]   \033[1;32m↳\033[0m {prefix}{out_str[:max_len]}"

        elif ev_type in ("error", "warning"):
            msg = data.get("message") or data.get("error") or str(data)
            return f"[{ts}] \033[1;31m✖ [ERREUR]\033[0m {str(msg)[:max_len]}"

        else:
            return f"[{ts}] ℹ [{ev_type}] {str(data)[:max_len]}"


# Singleton instance
stream_formatter = AgentStreamFormatter()
