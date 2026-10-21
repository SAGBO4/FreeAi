# Clarification Gate — Local AI Assistant

**Source:** Engineering Specification (Phase 1)  
**Date:** 2026-10-02  
**Gate:** Phase 2 — Clarification Gate

---

## 1. Blocking Test Results

| Unknown | Architecture Depends | Expensive to Reverse | Legal/Financial/Safety | Incompatible Readings | No Defensible Default | **Verdict** |
|---------|---------------------|---------------------|------------------------|----------------------|----------------------|-------------|
| U-1: Exact CPU model | ✅ | ✅ | ❌ | N/A | ✅ | **BLOCKING** |
| U-2: Actual free RAM | ✅ | ✅ | ❌ | N/A | ✅ | **BLOCKING** |
| U-3: Available disk space | ✅ | ✅ | ❌ | N/A | ✅ | **BLOCKING** |
| U-4: Which GGUF models pass quality | ✅ | ✅ | ❌ | N/A | ✅ | **BLOCKING** |
| U-5: llama-cpp-python wheel | ⚠️ | ❌ | ❌ | ❌ | ❌ | Non-blocking |
| U-6: STT/TTS model sizes | ❌ | ❌ | ❌ | ❌ | ❌ | Non-blocking |
| U-7: VS Code extension API | ❌ | ❌ | ❌ | ❌ | ❌ | Non-blocking |
| U-8: Dynamic security tools | ❌ | ❌ | ❌ | ❌ | ❌ | Non-blocking |
| U-9: LAB snapshot mechanism | ⚠️ | ⚠️ | ❌ | ❌ | ❌ | Non-blocking |
| U-10: Voice language/accent | ❌ | ❌ | ❌ | ❌ | ❌ | Non-blocking |

---

## 2. Non-Blocking Unknowns → Assumption Records

```
A-1  llama-cpp-python wheel available for Kali/CPU; if not, build from source
      Why needed:  Runtime selection for Phase 2
      Default:     Build from source if no wheel
      If wrong:    Add 5–10 min build time; no architecture change

A-2  STT/TTS models fit 0.3–0.5 GB budget (whisper.cpp tiny/base, piper)
      Why needed:  Voice phase (Phase 7) RAM budget
      Default:     whisper.cpp tiny (∼39 MB) + piper (∼50 MB); lazy-load
      If wrong:    Disable voice or reduce LLM context; no architecture change

A-3  VS Code extension API supports required chat/actions
      Why needed:  Extension timeline (post-MVP)
      Default:     CLI-first MVP; extension deferred
      If wrong:    Extension delayed; core system unaffected

A-4  Dynamic security tools (nuclei, OWASP ZAP, etc.) installable in LAB
      Why needed:  Agent Security dynamic tests
      Default:     Install via apt/pip in LAB environment
      If wrong:    Substitute tools; no architecture change

A-5  LAB snapshot/rollback via git + docker; evaluate btrfs/LVM in Phase 8
      Why needed:  LAB mode implementation
      Default:     Git checkpoints + docker containers for isolation
      If wrong:    Switch mechanism in Phase 8; isolated to LAB module

A-6  Voice language: English (configurable)
      Why needed:  STT model choice
      Default:     English; user can change in config
      If wrong:    Download different whisper model; no architecture change
```

---

## 3. Blocking Questions — Single Batch

### Hardware & Environment (must be resolved before Phase 1 benchmark)

**1. CPU Model**  
The TDR §46 Step 1 requires identifying the exact CPU.  
*What is the exact CPU model of the HP EliteBook?* (Run `lscpu` or `cat /proc/cpuinfo`)  
This determines: instruction sets (AVX2/AVX-512), core/thread count, llama.cpp optimization flags, and baseline `LLM_THREADS` value.

**2. Available RAM**  
The TDR §46 Step 2 requires verifying the 10 GB RAM and measuring free RAM.  
*How much RAM is free after OS + typical user applications are running?* (Run `free -h` under normal load)  
This validates the 4 GB AI budget and determines maximum model size.

**3. Disk Space**  
The TDR §46 Step 3 requires verifying disk space.  
*How much free space is available on the target partition for models (GGUF files 2–4 GB each)?* (Run `df -h /home`)  
This determines how many models can be cached for benchmarking.

### Model Selection (must be resolved before Phase 1 completes)

**4. Benchmark Model Candidates**  
The TDR §34 requires testing multiple small models and measuring RAM, CPU, tokens/sec, quality, tool calling.  
*Which specific GGUF models should be included in the benchmark?*  
Suggested default set (all ≤ 3B params, Q4_K_M or Q5_K_M quantization):
- `phi-3-mini-4k-instruct-q4_k_m.gguf` (3.8B, ∼2.3 GB)
- `qwen2.5-1.5b-instruct-q4_k_m.gguf` (1.5B, ∼1.0 GB)
- `qwen2.5-3b-instruct-q4_k_m.gguf` (3B, ∼1.9 GB)
- `gemma-2-2b-it-q4_k_m.gguf` (2B, ∼1.4 GB)
- `smollm2-1.7b-instruct-q4_k_m.gguf` (1.7B, ∼1.1 GB)
- `llama-3.2-1b-instruct-q4_k_m.gguf` (1B, ∼0.7 GB)

*Do you approve this candidate set, or do you want different models tested?*

---

## 4. Batch Size Check

4 blocking questions — under the ~10 question cap. Proceeding with single batch.

---

## 5. Gate Verdict

**Blocked** — 4 blocking unknowns remain. The project cannot proceed correctly to Phase 1 benchmark without answers to Questions 1–3 (hardware/environment) and Question 4 (benchmark scope). Hardware answers (1–3) are required before any benchmark can run. Question 4 can be answered with the suggested default set if no preference.

---

## 6. Next Steps

1. User provides hardware info (Questions 1–3) via terminal commands
2. User confirms or modifies benchmark model list (Question 4)
3. Gate clears → proceed to Technology Selection (Phase 3) and Architecture Proposal (Phase 4)
4. Validation Gate (Phase 5) will present full architecture for approval before implementation