"""FreeAI — Moteur d'Intelligence Artificielle Locale & Fédérée.
Nom du modèle : FreeAI Neural Engine (v2.0)
Architecture : Véritable modèle de langage neural (Local GGUF/Ollama + Déportation Cloud Haute Performance).
Libre, sans restriction ni censure.
"""

import os
import re
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
import httpx

from .federation import OnlineModelFederation

logger = logging.getLogger("freeai_engine")



try:
    import torch
    from .genese.adn import ADNModele
    from .genese.tokenizer import TokenizerJarvis
    from .genese.modele import JarvisModele
    from .genese.ame.gardien import GardienEthique
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch n'est pas installé. Le noyau Jarvis sera inactif.")

class JarvisCoreRuntime:
    """Noyau Neural Natif JARVIS (Stade 0).
    Opère en RAM pure (Mode NÉANT) et précède toute autre inférence.
    """
    def __init__(self, model_path: str = "./models/jarvis-s0-v0001.pt"):
        self.model_path = Path(model_path)
        self.modele = None
        self.tokenizer = None
        self.gardien = None
        self.actif = False
        self._init_core()

    def _init_core(self):
        if not TORCH_AVAILABLE:
            return
        if self.model_path.exists() and self.model_path.is_file():
            try:
                self.gardien = GardienEthique()
                self.tokenizer = TokenizerJarvis()
                adn = ADNModele()
                self.modele = JarvisModele(adn)
                
                # Mode NÉANT : charge directement en RAM
                etat = torch.load(self.model_path, map_location='cpu', weights_only=True)
                self.modele.load_state_dict(etat)
                self.modele.eval()
                self.actif = True
                logger.info(f"[JARVIS_CORE] Noyau neural natif chargé avec succès depuis {self.model_path}")
            except Exception as e:
                logger.error(f"[JARVIS_CORE] Échec de l'éveil du noyau Jarvis : {e}")

    async def generate_local(self, prompt: str, system_prompt: Optional[str] = None, max_new_tokens: int = 150, temperature: float = 0.7) -> Optional[str]:
        if not self.actif or self.modele is None:
            return None
            
        def _infer():
            # Combine system prompt
            full_prompt = f"<|systeme|>{system_prompt}<|utilisateur|>{prompt}<|jarvis|>" if system_prompt else f"<|utilisateur|>{prompt}<|jarvis|>"
            tokens = self.tokenizer.encode(full_prompt, add_special_tokens=True)
            input_ids = torch.tensor([tokens], dtype=torch.long)
            
            out_tokens = self.modele.generer(input_ids, max_new_tokens, temperature)
            gen_tokens = out_tokens[0][len(tokens):].tolist()
            
            texte = self.tokenizer.decode(gen_tokens)
            texte = self.gardien.filtrer(texte)
            return texte
            
        try:
            return await asyncio.to_thread(_infer)
        except Exception as e:
            logger.error(f"[JARVIS_CORE] Erreur lors du raisonnement : {e}")
            return None


class LocalNeuralRuntime:
    """Manages true local neural LLM execution on CPU/GPU via GGUF (llama-cpp) or Ollama daemon."""

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or os.getenv("LLM_MODEL_PATH", "./models/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf")
        self.context_size = int(os.getenv("LLM_CONTEXT_SIZE", "4096"))
        self.threads = int(os.getenv("LLM_THREADS", "4"))
        self.local_llama_instance = None
        self._init_local_llm()

    def _init_local_llm(self):
        """Attempts to load a local GGUF model via llama_cpp if installed and weights are present."""
        target = Path(self.model_path)
        if target.exists() and target.is_file():
            try:
                import llama_cpp
                logger.info(f"[LOCAL_RUNTIME] Loading local GGUF model weights from {target} (threads={self.threads})...")
                self.local_llama_instance = llama_cpp.Llama(
                    model_path=str(target),
                    n_ctx=self.context_size,
                    n_threads=self.threads,
                    verbose=False
                )
                logger.info("[LOCAL_RUNTIME] Local GGUF model successfully loaded into CPU RAM.")
            except ImportError:
                logger.info("[LOCAL_RUNTIME] llama-cpp-python non installé. Le moteur local utilisera Ollama ou la fédération.")
            except Exception as e:
                logger.warning(f"[LOCAL_RUNTIME] Failed to initialize local GGUF weights: {e}")

    async def is_ollama_ready(self) -> bool:
        """Checks if local Ollama daemon is responsive on 127.0.0.1:11434."""
        try:
            async with httpx.AsyncClient(timeout=1.0) as client:
                res = await client.get("http://127.0.0.1:11434/api/tags")
                return res.status_code == 200
        except Exception:
            return False

    async def generate_local(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 512) -> Optional[str]:
        """Executes inference locally (via loaded GGUF or local Ollama)."""
        # 1. Native GGUF instance in RAM
        if self.local_llama_instance is not None:
            try:
                full_prompt = f"<|im_start|>system\n{system_prompt or 'You are FreeAI, an expert AI.'}<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"
                loop = asyncio.get_running_loop()
                output = await loop.run_in_executor(
                    None,
                    lambda: self.local_llama_instance(
                        full_prompt,
                        max_tokens=max_tokens,
                        temperature=0.3,
                        stop=["<|im_end|>", "</s>"]
                    )
                )
                return output["choices"][0]["text"].strip()
            except Exception as e:
                logger.error(f"[LOCAL_RUNTIME] GGUF inference failed: {e}")

        # 2. Local Ollama daemon
        if await self.is_ollama_ready():
            try:
                payload = {"model": "llama3.2", "prompt": prompt, "stream": False}
                async with httpx.AsyncClient(timeout=30.0) as client:
                    res = await client.post("http://127.0.0.1:11434/api/generate", json=payload)
                    if res.status_code == 200:
                        return res.json().get("response", "").strip()
            except Exception as e:
                logger.debug(f"[LOCAL_RUNTIME] Local Ollama call failed: {e}")

        return None


class FreeAIEngine:
    """FreeAI: Sovereign Neural Engine.
    Executes true neural language reasoning rather than static heuristic scripts.
    Automatically arbitrates between local GGUF/Ollama inference and high-capacity cloud open models (GPT-OSS 120B / Qwen 3.8).
    """

    def __init__(self, model_path: Optional[str] = None, memory_dir: str = "./memory"):
        self.name = "FreeAI"
        self.version = "2.0-neural"
        self.model_path = model_path
        self.federation = OnlineModelFederation(memory_dir=memory_dir)
        self.local_runtime = LocalNeuralRuntime(model_path=model_path)
        self.jarvis_runtime = JarvisCoreRuntime()
        logger.info(f"[{self.name}] Initialized FreeAI Sovereign Neural Engine (v{self.version}).")

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, timeout_sec: int = 25) -> str:
        """True neural language generation: tries local GGUF/Ollama first, then cloud open models."""
        clean_p = prompt.strip()

                # 0. Try Jarvis Native Core first
        jarvis_ans = await self.jarvis_runtime.generate_local(clean_p, system_prompt=system_prompt)
        if jarvis_ans:
            return jarvis_ans

        # 1. Try local neural model if available
        local_ans = await self.local_runtime.generate_local(clean_p, system_prompt=system_prompt)
        if local_ans:
            return local_ans

        # 2. Seamlessly route to high-capacity cloud neural model (0 local RAM, 120B parameters)
        res = await self.federation.consult_free_online_model(clean_p, system_prompt=system_prompt, timeout_sec=timeout_sec)
        if res.get("success"):
            return res.get("response", "")

        return "Erreur : aucun modèle neural n'a pu répondre."

    async def reason_and_plan_neural(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Neural Cognitive Reasoning & Planning:
        Directly prompts the neural LLM to analyze the objective, formulate a multi-step execution strategy,
        and output structured technical guidance.
        """
        logger.info(f"[{self.name}] Engaging neural cognitive planning for: '{prompt[:50]}'")

        if self.jarvis_runtime.actif:
            logger.info(f"[{self.name}] Raisonnement propulsé par le noyau natif JARVIS.")
            
        sys_prompt = (
            "Tu es le cerveau cognitif central de FreeAI. "
            "Analyse l'objectif technique demandé et produis UNIQUEMENT un objet JSON valide suivant rigoureusement cette structure :\n"
            "{\n"
            '  "domain": "code" | "security" | "git" | "conversation",\n'
            '  "intent": "description concise de l\'intention",\n'
            '  "unrestricted": true,\n'
            '  "needs_online_resourcing": true | false,\n'
            '  "strategy": ["Étape 1...", "Étape 2...", "Étape 3..."],\n'
            '  "recommended_tools": ["liste", "des", "outils"]\n'
            "}"
        )

        user_content = f"Objectif technique : {prompt}"
        if context and context.get("mode"):
            user_content += f"\nMode actuel : {context.get('mode')}"

        try:
            raw_response = await self.generate(prompt=user_content, system_prompt=sys_prompt, timeout_sec=20)
            # Clean possible markdown fence blocks
            cleaned = re.sub(r'```json\s*', '', raw_response)
            cleaned = re.sub(r'```\s*', '', cleaned).strip()

            # Extract JSON block
            json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if json_match:
                plan = json.loads(json_match.group(0))
                if "domain" in plan and "strategy" in plan:
                    plan["model"] = f"{self.name}-{self.version}"
                    plan["neural_reasoning"] = True
                    return plan
        except Exception as e:
            logger.warning(f"[{self.name}] Neural planning failed ({e}), falling back to heuristic plan.")

        # Deterministic heuristic fallback
        return self.reason_and_plan(prompt, context or {})

    def reason_and_plan(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Deterministic heuristic fast planning (fallback & sync backward-compatibility)."""
        p_lower = prompt.lower()

        needs_online_resourcing = any(
            w in p_lower for w in [
                "cherche en ligne", "interroge", "nouvelle doc", "dernier", "cve",
                "ressource", "info externe", "modèle en ligne", "recherche web", "externe", "cherche", "web"
            ]
        )

        conversational_triggers = [
            "comment vas-tu", "comment tu vas", "ça va", "ca va", "comment ca va",
            "salut", "bonjour", "hello", "coucou", "hey", "bonsoir", "qui es-tu",
            "tu fais quoi", "merci", "raconte", "dis-moi", "tu penses quoi",
            "blague", "avis", "discussion", "parle-moi", "salut freeai", "vas tu"
        ]
        words = set(re.findall(r'\b\w+\b', p_lower))
        is_greeting = any(t in p_lower for t in conversational_triggers) or (
            len(prompt.split()) <= 7 and bool(words & {"tu", "toi", "vas", "ami", "amis", "pote", "potes", "frère", "frere"})
        )
        tech_indicators = ["code", "fichier", "fonction", "git", "secu", "sécu", "securite", "sécurité", "scan", "test", "docker", "script", "faille", "audit"]

        if is_greeting and not any(k in p_lower for k in tech_indicators):
            return {
                "model": self.name,
                "domain": "conversation",
                "intent": "human_dialogue",
                "unrestricted": True,
                "needs_online_resourcing": False,
                "strategy": [
                    "1. Analyse de l'état d'esprit et du contexte relationnel.",
                    "2. Consultation de la mémoire vectorielle épisodique.",
                    "3. Synthèse d'une réponse humaine, chaleureuse et complice."
                ],
                "recommended_tools": ["vector_memory", "persona"]
            }

        if any(k in p_lower for k in ["secu", "audit", "vuln", "faille", "cwe", "inject", "pentest", "scan", "secret"]):
            return {
                "model": self.name,
                "domain": "security",
                "intent": "security_audit",
                "unrestricted": True,
                "needs_online_resourcing": needs_online_resourcing,
                "strategy": [
                    "1. Scan de surface et cartographie des fichiers cibles.",
                    "2. Analyse SAST sans restriction (injections SQL, XSS, SSRF, chemins non assainis).",
                    "3. Recherche de secrets codés en dur (.env, clés privées, tokens).",
                    "4. Validation des mitigations et rapport de remédiation."
                ],
                "recommended_tools": ["filesystem", "terminal", "security_scanner"]
            }

        elif any(k in p_lower for k in ["git", "commit", "branch", "diff", "tag", "rollback", "revert"]):
            return {
                "model": self.name,
                "domain": "git",
                "intent": "version_control",
                "unrestricted": True,
                "needs_online_resourcing": needs_online_resourcing,
                "strategy": [
                    "1. Inspection du statut du dépôt (`git status`).",
                    "2. Examen des différences (`git diff`).",
                    "3. Création d'un checkpoint / snapshot préventif.",
                    "4. Exécution de l'opération demandée."
                ],
                "recommended_tools": ["git", "terminal"]
            }

        else:
            return {
                "model": self.name,
                "domain": "code",
                "intent": "code_engineering",
                "unrestricted": True,
                "needs_online_resourcing": needs_online_resourcing,
                "strategy": [
                    "1. Inspection de l'architecture du projet et dépendances.",
                    "2. Génération / modification des fichiers sources.",
                    "3. Exécution des tests unitaires via le terminal.",
                    "4. Analyse des logs d'erreurs et correction itérative."
                ],
                "recommended_tools": ["filesystem", "terminal", "testing"]
            }

    async def generate_code(self, task: str, language: str = "python", context_files: Optional[Dict[str, str]] = None) -> str:
        """Neural Code Synthesis:
        Directly generates production-ready code with explanations and zero hallucination.
        """
        sys_prompt = (
            f"Tu es un Lead Software Engineer expert en {language}. "
            "Génère du code propre, typé, robuste, performant et conforme aux meilleures pratiques industrielles. "
            "Fournis le code directement avec une explication concise."
        )
        prompt = f"Tâche de programmation : {task}\n"
        if context_files:
            prompt += "\nContexte des fichiers existants :\n"
            for fpath, fcontent in context_files.items():
                prompt += f"--- {fpath} ---\n{fcontent[:1500]}\n"

        return await self.generate(prompt=prompt, system_prompt=sys_prompt)

    async def audit_security(self, target_code: str) -> str:
        """Neural SAST Security Audit:
        Scans code for memory corruptions, injection flaws, privilege escalations, and logical bugs.
        """
        sys_prompt = (
            "Tu es un expert en cybersécurité offensive et défensive (Red Team & Blue Team). "
            "Analyse le code suivant pour identifier toute faille de sécurité (CWE, OWASP Top 10, fuites de mémoire, "
            "injections, race conditions). Propose le correctif immédiat."
        )
        return await self.generate(prompt=f"Code à auditer :\n```\n{target_code}\n```", system_prompt=sys_prompt)

    async def enrich_with_online_open_models(self, query: str) -> Dict[str, Any]:
        """FreeAI reaches out to free open-source models online to acquire missing knowledge."""
        logger.info(f"[{self.name}] Initiating external resourcing from free online open models...")
        return await self.federation.consult_free_online_model(query)
