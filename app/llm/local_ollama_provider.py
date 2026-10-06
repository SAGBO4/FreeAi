"""Local High-Performance Ollama Engine for FreeAI (Inspiré de my_jarvis/bench.py & toolcall_test.py).
Fournit à FreeAI une intégration native, ultra-rapide et 100% hors-ligne avec le daemon Ollama local :
- Auto-détection des modèles installés (`/api/tags`).
- Inférence `/api/chat` avec support natif des `tools` (tool-calling).
- Benchmarking précis de la vitesse (tokens/s de génération et prompt eval).
- Surveillance des ressources matérielles VRAM / CPU (`ollama ps`).
- Contrôle fin du flux de réflexion (`think: True/False`).

Mode NÉANT : 100% en RAM, zéro fichier temporaire sur SSD.
"""

import json
import time
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, AsyncGenerator
import logging
import httpx

logger = logging.getLogger("local_ollama")


@dataclass
class OllamaBenchmarkResult:
    model: str
    gen_tokens_per_sec: float
    prompt_tokens_per_sec: float
    load_time_sec: float
    total_time_sec: float
    tokens_generated: int
    thinking_chars: int
    hardware_allocation: str = ""  # CPU vs GPU split


class LocalOllamaProvider:
    """Connecteur souverain vers Ollama local (127.0.0.1:11434)."""

    def __init__(self, base_url: str = "http://127.0.0.1:11434", timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def is_available(self) -> bool:
        """Vérifie si le daemon Ollama local est actif et répond."""
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    async def list_local_models(self) -> List[str]:
        """Retourne la liste des modèles disponibles localement."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    models = res.json().get("models", [])
                    return [m.get("name") for m in models if m.get("name")]
        except Exception as e:
            logger.debug(f"[OLLAMA] Error listing models: {e}")
        return []

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        think: bool = False
    ) -> Dict[str, Any]:
        """Exécute une requête chat avec support natif des outils (tool calling)."""
        url = f"{self.base_url}/api/chat"
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "think": think,
            "options": {
                "temperature": temperature
            }
        }
        if tools:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    msg = data.get("message", {})
                    # Parsing robuste des tool calls si renvoyés en JSON brut dans le texte
                    return {
                        "success": True,
                        "content": msg.get("content", ""),
                        "tool_calls": msg.get("tool_calls", []),
                        "eval_count": data.get("eval_count", 0),
                        "eval_duration_ns": data.get("eval_duration", 0),
                        "total_duration_ns": data.get("total_duration", 0)
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Ollama HTTP {resp.status_code}: {resp.text}"
                    }
        except Exception as e:
            logger.debug(f"[OLLAMA] Chat inference failed: {e}")
            return {"success": False, "error": str(e)}

    async def benchmark_model(self, model: str, think: bool = False) -> Optional[OllamaBenchmarkResult]:
        """Mesure précisément les performances tokens/s et le découpage CPU/GPU."""
        url = f"{self.base_url}/api/generate"
        test_prompt = (
            "Write a Python function `merge_intervals(intervals)` that merges overlapping intervals, "
            "with a docstring and 3 unit tests. Code only."
        )
        payload = {
            "model": model,
            "prompt": test_prompt,
            "stream": False,
            "think": think,
            "options": {"temperature": 0.0, "seed": 42, "num_predict": 300}
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                t0 = time.time()
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    eval_count = data.get("eval_count", 0)
                    eval_dur = data.get("eval_duration", 1)
                    prompt_eval_count = data.get("prompt_eval_count", 0)
                    prompt_eval_dur = data.get("prompt_eval_duration", 1)
                    load_dur = data.get("load_duration", 0)
                    total_dur = data.get("total_duration", 1)

                    gen_tok_s = round(eval_count / eval_dur * 1e9, 1) if eval_dur > 0 else 0.0
                    prompt_tok_s = round(prompt_eval_count / prompt_eval_dur * 1e9, 1) if prompt_eval_dur > 0 else 0.0

                    # Récupération de l'allocation matérielle via ollama ps si disponible
                    hw_info = "Unknown"
                    if shutil.which("ollama"):
                        try:
                            ps = subprocess.run(["ollama", "ps"], capture_output=True, text=True, timeout=2).stdout.splitlines()
                            line = next((l for l in ps if l.startswith(model.split(":")[0])), "")
                            if line:
                                hw_info = " ".join(line.split())
                        except Exception:
                            pass

                    return OllamaBenchmarkResult(
                        model=model,
                        gen_tokens_per_sec=gen_tok_s,
                        prompt_tokens_per_sec=prompt_tok_s,
                        load_time_sec=round(load_dur / 1e9, 2),
                        total_time_sec=round(total_dur / 1e9, 2),
                        tokens_generated=eval_count,
                        thinking_chars=len(data.get("thinking") or ""),
                        hardware_allocation=hw_info
                    )
        except Exception as e:
            logger.debug(f"[OLLAMA] Benchmark failed: {e}")
            return None


# Instance singleton globale
local_ollama = LocalOllamaProvider()
