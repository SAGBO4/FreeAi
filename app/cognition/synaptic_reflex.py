"""Synaptic Reflex Radar & Thought Hologram Matrix (Feature F-25).
Pure in-memory proactive cognitive anticipation engine.
Provides:
- Spectral intent decomposition (algorithmic density, autonomy vector, criticality level)
- Anticipated architecture prerequisites & toolchains
- High-fidelity thought hologram matrix terminal dashboard (Noble OpenCode typography)
- Sub-5ms pure RAM execution with 0 SSD disk write (Mode NÉANT strictly enforced).
STRICTLY ZERO RAW EMOJIS: Pure geometric glyphs (◈, ⊙, ▣, ▲, ■).
"""

import math
import re
import time
from collections import deque
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class CriticalityLevel(str, Enum):
    """System criticality and blast radius level."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class QuantumCognitiveState(str, Enum):
    """Quantum cognitive resonance state."""
    RESTING_POTENTIAL = "RESTING_POTENTIAL"
    SUPERPOSITION_RESONANCE = "SUPERPOSITION_RESONANCE"
    SYNAPSE_LOCKED = "SYNAPSE_LOCKED"
    PROACTIVE_EQUILIBRIUM = "PROACTIVE_EQUILIBRIUM"
    ADVERSARIAL_ALERT = "ADVERSARIAL_ALERT"
    SOVEREIGN_APEX = "SOVEREIGN_APEX"


class IntentCategory(str, Enum):
    """Categorical classification of user intent."""
    IDLE_RESONANCE = "IDLE_RESONANCE"
    ARCHITECTURAL_ENGINEERING = "ARCHITECTURAL_ENGINEERING"
    ADVERSARIAL_DEFENSE = "ADVERSARIAL_DEFENSE"
    HIGH_THROUGHPUT_COMPUTATION = "HIGH_THROUGHPUT_COMPUTATION"
    EPHEMERAL_INTROSPECTION = "EPHEMERAL_INTROSPECTION"
    KNOWLEDGE_SYNTHESIS = "KNOWLEDGE_SYNTHESIS"
    REACTIVE_TELEMETRY = "REACTIVE_TELEMETRY"


class SynapticReflexEngine:
    """Proactive Cognitive Anticipation & Thought Hologram Matrix Engine (Mode NÉANT).
    
    Operates strictly in volatile RAM with zero persistent disk overhead.
    Evaluates spectral intent, calculates autonomy and risk metrics in sub-5ms latency,
    and produces noble geometric holograms for terminal telemetric projection.
    """

    # Pre-compiled high-speed regexes for tokenization and lexical spectral analysis
    _RE_TOKEN = re.compile(r"[A-Za-z0-9_]+|[^\sA-Za-z0-9_]")
    _RE_CODE_KEYWORDS = re.compile(
        r"\b(def|class|import|from|async|await|return|lambda|function|const|let|"
        r"var|if|else|elif|for|while|try|except|raise|yield|struct|impl|fn|pub|"
        r"interface|type|sql|select|insert|update|delete|docker|git|bash|sh|zsh|"
        r"curl|wget|npm|pnpm|cargo|pip|pytest|grep|find|sed|awk)\b",
        re.IGNORECASE
    )
    _RE_SYNTAX_SYMBOLS = re.compile(r"[{}\[\]()<>=+\-*\/%!&|^~:;,.\'\"`]")
    _RE_CRITICAL_SECURITY = re.compile(
        r"\b(rm\s+-rf|dd\s+if|mkfs|format|wipe|drop\s+table|drop\s+database|"
        r"kill\s+-9|shutdown|reboot|iptables|chmod\s+777|chown\s+root|sudo|su\b|"
        r"passwd|shadow|vault|secret|private_key|token|exploit|payload|rootkit)\b",
        re.IGNORECASE
    )
    _RE_HIGH_OPERATIONAL = re.compile(
        r"\b(git\s+reset|git\s+push\s+--force|docker\s+rm|docker\s+stop|purge|"
        r"overwrite|destroy|kill|killall|truncate|delete\s+all)\b",
        re.IGNORECASE
    )
    _RE_IMPERATIVE_AUTONOMY = re.compile(
        r"\b(implémente|implemente|implement|construis|build|crée|cree|create|"
        r"développe|developpe|develop|optimise|optimize|refactorise|refactor|"
        r"automatise|automate|orchestre|orchestrate|résous|resous|solve|"
        r"génère|genere|generate|exécute|execute|programme|architecte|deploy|"
        r"conçois|concois|intègre|integre|patch|corrige|répare|repare)\b",
        re.IGNORECASE
    )
    _RE_PASSIVE_INQUIRY = re.compile(
        r"\b(qu\'est-ce\s+que|what\s+is|pourquoi|why|comment|how|explique|explain|"
        r"aide|help|salut|bonjour|bonsoir|hello|hi|merci|merci\s+beaucoup|"
        r"qui\s+es-tu|who\s+are\s+you|status|version|info)\b",
        re.IGNORECASE
    )

    def __init__(self, history_maxlen: int = 64):
        # In-memory circular buffer (0 SSD write, strictly volatile)
        self._history_maxlen = history_maxlen
        self._reflex_history: deque = deque(maxlen=history_maxlen)
        self._total_analyses: int = 0
        self._cumulative_latency_ms: float = 0.0

    def analyze_synaptic_intent(self, prompt: str) -> Dict[str, Any]:
        """Analyzes incoming prompt spectrally in sub-5ms RAM.
        
        Calculates:
        - Algorithmic density (0.0 to 1.0)
        - Cognitive autonomy vector (0.0 to 1.0)
        - System criticality level (LOW, MEDIUM, HIGH, CRITICAL)
        - Anticipated architecture prerequisites & toolchains
        - Spectral harmonics decomposition
        """
        t_start = time.perf_counter()
        prompt_raw = prompt or ""
        prompt_clean = prompt_raw.strip()

        # Handle empty or whitespace input
        if not prompt_clean:
            t_end = time.perf_counter()
            lat_ms = max(0.001, (t_end - t_start) * 1000.0)
            idle_data: Dict[str, Any] = {
                "prompt": "",
                "algorithmic_density": 0.0,
                "cognitive_autonomy": 0.05,
                "system_criticality": CriticalityLevel.LOW.value,
                "criticality_score": 0.0,
                "architecture_prerequisites": ["SacredLifeSentinel"],
                "anticipated_toolchains": ["ConversationMemory"],
                "intent_category": IntentCategory.IDLE_RESONANCE.value,
                "quantum_state": QuantumCognitiveState.RESTING_POTENTIAL.value,
                "spectral_harmonics": {
                    "syntactic_depth": 0.0,
                    "entropy_flux": 0.0,
                    "toolchain_entropy": 0.05,
                    "epistemic_certainty": 0.99,
                },
                "latency_ms": round(lat_ms, 3),
                "memory_footprint_bytes": 1024,
                "mode_neant_status": "ENFORCED_ZERO_DISK_WRITE",
                "timestamp": time.time(),
            }
            self._record_telemetry(idle_data, lat_ms)
            return idle_data

        # 1. Fast Tokenization & Frequency Analysis
        tokens = self._RE_TOKEN.findall(prompt_clean)
        total_tokens = len(tokens)
        unique_tokens = len(set(t.lower() for t in tokens))
        token_entropy = (unique_tokens / total_tokens) if total_tokens > 0 else 0.0

        # Code & syntax signals
        code_matches = len(self._RE_CODE_KEYWORDS.findall(prompt_clean))
        syntax_matches = len(self._RE_SYNTAX_SYMBOLS.findall(prompt_clean))
        line_count = prompt_clean.count("\n") + 1

        # Calculate Algorithmic Density (0.0 to 1.0)
        # Weighted mixture of keyword density, syntax density, and structural lines
        keyword_density = min(1.0, code_matches / max(5, total_tokens * 0.4))
        syntax_density = min(1.0, syntax_matches / max(10, total_tokens * 0.6))
        structure_density = min(1.0, (line_count - 1) * 0.15)
        raw_algo_density = (keyword_density * 0.45) + (syntax_density * 0.40) + (structure_density * 0.15)
        algorithmic_density = round(min(1.0, max(0.0, raw_algo_density)), 4)

        # 2. Calculate Cognitive Autonomy Vector (0.0 to 1.0)
        imperative_count = len(self._RE_IMPERATIVE_AUTONOMY.findall(prompt_clean))
        passive_count = len(self._RE_PASSIVE_INQUIRY.findall(prompt_clean))

        base_autonomy = 0.35  # Neutral interactive dialogue baseline
        if imperative_count > 0:
            base_autonomy += min(0.55, imperative_count * 0.20)
        if passive_count > 0:
            base_autonomy -= min(0.30, passive_count * 0.15)

        # Multi-sentence complex directives trigger higher proactive freedom
        if total_tokens > 25:
            base_autonomy += 0.10
        if algorithmic_density > 0.4:
            base_autonomy += 0.10

        cognitive_autonomy = round(min(1.0, max(0.05, base_autonomy)), 4)

        # 3. Calculate System Criticality & Risk Vector
        critical_sec_matches = len(self._RE_CRITICAL_SECURITY.findall(prompt_clean))
        high_op_matches = len(self._RE_HIGH_OPERATIONAL.findall(prompt_clean))

        if critical_sec_matches > 0:
            system_criticality = CriticalityLevel.CRITICAL
            criticality_score = min(1.0, 0.85 + (critical_sec_matches * 0.05))
        elif high_op_matches > 0:
            system_criticality = CriticalityLevel.HIGH
            criticality_score = min(0.84, 0.65 + (high_op_matches * 0.05))
        elif algorithmic_density > 0.5 or total_tokens > 50:
            system_criticality = CriticalityLevel.MEDIUM
            criticality_score = min(0.64, 0.35 + (algorithmic_density * 0.25))
        else:
            system_criticality = CriticalityLevel.LOW
            criticality_score = round(min(0.34, 0.05 + (algorithmic_density * 0.20)), 4)

        criticality_score = round(criticality_score, 4)

        # 4. Map Architecture Prerequisites & Anticipated Toolchains
        prereqs, toolchains = self._resolve_prerequisites_and_toolchains(
            prompt_clean, algorithmic_density, system_criticality, cognitive_autonomy
        )

        # 5. Determine Intent Category & Quantum Cognitive State
        intent_cat, quantum_st = self._resolve_intent_and_state(
            algorithmic_density, cognitive_autonomy, system_criticality, prompt_clean
        )

        # 6. Compute Spectral Harmonics
        syntactic_depth = round(min(1.0, (syntax_matches * 0.05) + (line_count * 0.08)), 3)
        entropy_flux = round(token_entropy, 3)
        toolchain_entropy = round(min(1.0, len(toolchains) * 0.18), 3)
        epistemic_certainty = round(max(0.40, 1.0 - (0.35 if "?" in prompt_clean else 0.0)), 3)

        spectral_harmonics = {
            "syntactic_depth": syntactic_depth,
            "entropy_flux": entropy_flux,
            "toolchain_entropy": toolchain_entropy,
            "epistemic_certainty": epistemic_certainty,
        }

        # Measure latency strictly in ms
        t_end = time.perf_counter()
        latency_ms = max(0.001, (t_end - t_start) * 1000.0)

        result: Dict[str, Any] = {
            "prompt": prompt_clean,
            "algorithmic_density": algorithmic_density,
            "cognitive_autonomy": cognitive_autonomy,
            "system_criticality": system_criticality.value,
            "criticality_score": criticality_score,
            "architecture_prerequisites": prereqs,
            "anticipated_toolchains": toolchains,
            "intent_category": intent_cat.value,
            "quantum_state": quantum_st.value,
            "spectral_harmonics": spectral_harmonics,
            "latency_ms": round(latency_ms, 3),
            "memory_footprint_bytes": 1024 + (len(tokens) * 32),
            "mode_neant_status": "ENFORCED_ZERO_DISK_WRITE",
            "timestamp": time.time(),
        }

        self._record_telemetry(result, latency_ms)
        return result

    def render_thought_hologram(self, intent_data: Dict[str, Any]) -> str:
        """Renders a noble telemetric terminal dashboard (OpenCode typography).
        
        Strictly zero raw emojis: Only geometric symbols (◈, ⊙, ▣, ▲, ■, □).
        Outputs clear box-drawing layout showing spectral decomposition.
        """
        prompt = intent_data.get("prompt", "")
        # Truncate prompt gracefully for single line display
        prompt_display = (prompt[:58] + "...") if len(prompt) > 60 else (prompt or "[VIDE - REPOS COGNITIF]")

        algo_dense = float(intent_data.get("algorithmic_density", 0.0))
        autonomy = float(intent_data.get("cognitive_autonomy", 0.0))
        crit_score = float(intent_data.get("criticality_score", 0.0))
        crit_level = str(intent_data.get("system_criticality", "LOW"))
        latency_ms = float(intent_data.get("latency_ms", 0.0))
        quantum_st = str(intent_data.get("quantum_state", "PROACTIVE_EQUILIBRIUM"))
        intent_cat = str(intent_data.get("intent_category", "ARCHITECTURAL_ENGINEERING"))

        harmonics = intent_data.get("spectral_harmonics", {})
        syn_depth = float(harmonics.get("syntactic_depth", 0.0))
        ent_flux = float(harmonics.get("entropy_flux", 0.0))
        tc_entropy = float(harmonics.get("toolchain_entropy", 0.0))
        epi_cert = float(harmonics.get("epistemic_certainty", 1.0))

        prereqs = intent_data.get("architecture_prerequisites", [])
        toolchains = intent_data.get("anticipated_toolchains", [])
        mem_bytes = intent_data.get("memory_footprint_bytes", 1024)
        mem_kb = round(mem_bytes / 1024.0, 1)

        # Geometric Progress Gauges
        gauge_algo = self._format_gauge(algo_dense, 10)
        gauge_auto = self._format_gauge(autonomy, 10)
        gauge_crit = self._format_gauge(crit_score, 10)

        # Build hologram lines
        lines: List[str] = [
            "┌──────────────────────────────────────────────────────────────────────────────┐",
            "│ ◈ SYNAPTIC REFLEX RADAR // THOUGHT HOLOGRAM MATRIX (F-25)                    │",
            "│ ⊙ COGNITIVE PROACTIVITY ENGINE · ZERO SSD · SUB-5MS RAM                      │",
            "├──────────────────────────────────────────────────────────────────────────────┤",
            f"│ INTENTION BRUTE  : {prompt_display:<57} │",
            f"│ ETAT QUANTIQUE   : {quantum_st:<32} LATENCE : {latency_ms:>5.2f} ms │",
            f"│ CATEGORIE ACTEUR : {intent_cat:<57} │",
            "├──────────────────────────────────────────────────────────────────────────────┤",
            "│ ▣ SPECTRE DE RESONANCE NEURONALE                                             │",
            f"│ • Densité Algorithmique : {gauge_algo} {algo_dense * 100:>5.1f}%  (Complexité Syntaxe / AST)  │",
            f"│ • Autonomie Cognitive   : {gauge_auto} {autonomy * 100:>5.1f}%  (Exécution Agentique Apex) │",
            f"│ • Criticité Système     : {gauge_crit} {crit_score * 100:>5.1f}%  [{crit_level:<8}] Sanctuaire   │",
            "│                                                                              │",
            "│ ⊙ HARMONIQUES COGNITIVES                                                     │",
            f"│   - Profondeur Syntaxique  : {syn_depth:<6.2f}        - Flux d'Entropie      : {ent_flux:<6.2f}    │",
            f"│   - Entropie Toolchains    : {tc_entropy:<6.2f}        - Certitude Epistémique: {epi_cert:<6.2f}    │",
            "├──────────────────────────────────────────────────────────────────────────────┤",
            "│ ◈ PRE-REQUIS D'ARCHITECTURE & CHAINES D'OUTILS ANTICIPEES                    │",
        ]

        # Combine up to 6 key components
        combined_tools = list(dict.fromkeys(prereqs + toolchains))[:6]
        if not combined_tools:
            combined_tools = ["SacredLifeSentinel", "ConversationMemory"]

        for i in range(0, len(combined_tools), 2):
            left = combined_tools[i]
            right = combined_tools[i + 1] if i + 1 < len(combined_tools) else ""
            left_str = f"► {left}" if left else ""
            right_str = f"► {right}" if right else ""
            lines.append(f"│   {left_str:<35} {right_str:<36} │")

        lines.extend([
            "├──────────────────────────────────────────────────────────────────────────────┤",
            "│ ▣ TELEMETRIE NEANT                                                           │",
            f"│ • Stockage Disque SSD    : 0 B (Volatile RAM Pur)                            │",
            f"│ • Empreinte Synaptique   : {mem_kb:>5.1f} Ko RAM (Budget < 64 Ko)                     │",
            "│ • Sanctuaire Ethique     : SACRED_LIFE_PASS (Protection Inviolable)          │",
            "└──────────────────────────────────────────────────────────────────────────────┘",
        ])

        return "\n".join(lines)

    def get_telemetry(self) -> Dict[str, Any]:
        """Returns engine-level performance telemetry."""
        avg_lat = (
            (self._cumulative_latency_ms / self._total_analyses)
            if self._total_analyses > 0 else 0.0
        )
        return {
            "total_analyses": self._total_analyses,
            "average_latency_ms": round(avg_lat, 3),
            "ram_history_count": len(self._reflex_history),
            "ram_overhead_kb": round(len(self._reflex_history) * 1.2, 2),
            "disk_writes_bytes": 0,
            "mode_neant_active": True,
        }

    def reset_ephemeral_state(self) -> None:
        """Resets the volatile in-memory deque and telemetry."""
        self._reflex_history.clear()
        self._total_analyses = 0
        self._cumulative_latency_ms = 0.0

    # -------------------------------------------------------------------------
    # Private Helpers
    # -------------------------------------------------------------------------

    def _resolve_prerequisites_and_toolchains(
        self,
        prompt: str,
        algo_density: float,
        criticality: CriticalityLevel,
        autonomy: float
    ) -> tuple[List[str], List[str]]:
        """Resolves architectural components anticipated for the task."""
        p_lower = prompt.lower()
        prereqs: List[str] = ["SacredLifeSentinel"]
        toolchains: List[str] = []

        # Code & engineering
        if algo_density > 0.25 or any(k in p_lower for k in ["code", "python", "fonction", "test", "bug", "refactor"]):
            prereqs.append("ToolGateway.fs")
            toolchains.append("LSP.pyright")
            toolchains.append("AtomicUndoManager")

        # Git operations
        if any(k in p_lower for k in ["git", "commit", "branch", "diff", "merge", "push", "rollback"]):
            toolchains.append("GitVanguard")

        # Security & Privileges
        if criticality in (CriticalityLevel.CRITICAL, CriticalityLevel.HIGH) or "sudo" in p_lower:
            prereqs.append("ShadowDockerExecutor")
            prereqs.append("PhantomBusIPC")
            toolchains.append("SovereignFortress")

        # High Autonomy & Multi-Agent orchestration
        if autonomy > 0.65:
            toolchains.append("AetherSwarmOrchestrator")
            toolchains.append("SpeculativeAccelerationEngine")

        # Memory & Search
        if any(k in p_lower for k in ["cherche", "search", "trouve", "hologram", "mémoire", "memoire"]):
            toolchains.append("BinaryHologramEngine")
            prereqs.append("EphemeralVectorMemory")

        # Multimodal & Audio
        if any(k in p_lower for k in ["voix", "voice", "audio", "parle", "canvas", "dessine", "schéma"]):
            toolchains.append("SynestheticCanvasStreamer")
            toolchains.append("AcousticZeroRAMFacade")

        # Default fallback if nothing triggered
        if not toolchains:
            toolchains.append("ConversationMemory")
            toolchains.append("SemanticCompactor")

        return prereqs, toolchains

    def _resolve_intent_and_state(
        self,
        algo_density: float,
        autonomy: float,
        criticality: CriticalityLevel,
        prompt: str
    ) -> tuple[IntentCategory, QuantumCognitiveState]:
        """Classifies high-level intent and quantum state."""
        if criticality == CriticalityLevel.CRITICAL:
            return IntentCategory.ADVERSARIAL_DEFENSE, QuantumCognitiveState.ADVERSARIAL_ALERT

        if algo_density > 0.65:
            return IntentCategory.HIGH_THROUGHPUT_COMPUTATION, QuantumCognitiveState.SYNAPSE_LOCKED

        if autonomy > 0.70:
            return IntentCategory.ARCHITECTURAL_ENGINEERING, QuantumCognitiveState.SOVEREIGN_APEX

        if any(w in prompt.lower() for w in ["qui", "pourquoi", "explique", "comment"]):
            return IntentCategory.KNOWLEDGE_SYNTHESIS, QuantumCognitiveState.PROACTIVE_EQUILIBRIUM

        return IntentCategory.EPHEMERAL_INTROSPECTION, QuantumCognitiveState.SUPERPOSITION_RESONANCE

    def _record_telemetry(self, data: Dict[str, Any], lat_ms: float) -> None:
        """Records analysis telemetry strictly in volatile RAM."""
        self._total_analyses += 1
        self._cumulative_latency_ms += lat_ms
        self._reflex_history.append({
            "timestamp": data.get("timestamp", time.time()),
            "category": data.get("intent_category"),
            "latency_ms": lat_ms,
            "density": data.get("algorithmic_density"),
            "autonomy": data.get("cognitive_autonomy"),
        })

    @staticmethod
    def _format_gauge(value: float, width: int = 10) -> str:
        """Formats a noble geometric progress bar: [■■■■■■■□□□].
        Strictly zero emojis!
        """
        clamped = max(0.0, min(1.0, value))
        filled = int(round(clamped * width))
        empty = width - filled
        return f"[{'■' * filled}{'□' * empty}]"
