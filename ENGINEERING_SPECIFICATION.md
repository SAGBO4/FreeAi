# Engineering Specification: Local AI Assistant on Kali Linux (HP EliteBook)

**Version:** 1.0  
**Source:** TDR_Assistant_IA_Local_Kali_HP_EliteBook.md  
**Date:** 2026-10-02  
**Phase:** 1 — Requirements Analysis

---

## 1. Product Frame

### Objective
Create a fully local, offline-capable personal AI assistant running on an HP EliteBook (10 GB RAM, CPU only) under Kali Linux, with strict RAM budget (≤ 3.5 GB target, ≤ 4 GB absolute), capable of orchestrating specialized agents (Code, Security, Git) to work on local projects via VS Code, terminal, and file system.

### Users
| User Type | Description |
|-----------|-------------|
| Primary User | The HP EliteBook owner — a developer/security practitioner who wants an autonomous local assistant |

### Roles
| Role | Permissions |
|------|-------------|
| User | Full control: define objectives, interrupt, view logs, approve/deny network access, switch modes |
| Orchestrator | Plans, routes to agents, executes tool calls, manages memory/context, enforces resource limits |
| Agent Code | Read/write files, run tests, modify code, analyze logs, work across multiple files |
| Agent Security | Static analysis (SAST), dependency scanning, secret scanning, config review, dynamic testing (in LAB mode) |
| Agent Git | Local git operations (status, diff, log, branch, checkout, add, commit); remote ops configurable |
| Tool Gateway | Executes filesystem, terminal, git, testing, security tools with timeout, logging, resource limits |
| Resource Manager | Monitors RAM/CPU, enforces budgets, degrades gracefully, shuts down workers if exceeded |

### Workflows
| Workflow | Description |
|----------|-------------|
| Normal Mode | User → text/voice → Orchestrator → Agent(s) → Tools → Local projects → Result |
| Autonomous Mode | User → objective → Orchestrator plans → executes → verifies → corrects → reports |
| LAB Mode | Isolated environment for destructive tests, security experiments, snapshots/rollback |
| Voice Interaction | STT → Orchestrator → ... → TTS response |

### Value
- Full autonomy without cloud dependency
- Local security auditing of user's own projects
- CPU-only operation on modest hardware
- Transparent, interruptible, auditable execution

### Success Criteria
- Runs on Kali Linux / HP EliteBook / CPU only / ≤ 4 GB RAM
- All acceptance criteria in TDR §43 met (23 checkboxes)
- Final RAM peak < 4 GB (ideal ≤ 3.5 GB) on target hardware

---

## 2. Functional Requirements

### FR-1: Local LLM Inference
| Field | Detail |
|-------|--------|
| Name | Local LLM Inference |
| Trigger | Orchestrator sends prompt |
| Actor | Orchestrator |
| Preconditions | Model loaded, runtime initialized, RAM budget available |
| Behaviour | Accept prompt + context, stream tokens, support tool-call format, respect context window |
| Rules | GGUF format, llama.cpp-compatible runtime, CPU threads configurable, context size ≤ 4096 initial |
| States | Unloaded → Loading → Ready → Generating → Ready |
| Effects | RAM allocation (~2.0–2.8 GB), CPU utilization |
| Failure | OOM → Resource Manager triggers degradation/shutdown; timeout → return partial/error |
| Permissions | Orchestrator only |

### FR-2: Orchestrator Core
| Field | Detail |
|-------|--------|
| Name | Orchestrator Core |
| Trigger | User input (text/voice) or autonomous objective |
| Actor | User / Orchestrator (autonomous) |
| Preconditions | LLM ready, Tool Gateway ready, agents registered |
| Behaviour | Understand objective → select agent(s) → plan steps → execute via Tool Gateway → verify → retry/correct → report |
| Rules | Must log every action; must respect autonomy mode; must enforce resource limits via Resource Manager |
| States | Idle → Planning → Executing → Verifying → Reporting → Idle |
| Effects | Tool calls, file changes, command executions, git ops, test runs |
| Failure | Tool timeout → retry/fallback; agent error → re-plan; RAM pressure → degrade context/stop workers |
| Permissions | User can interrupt at any time (Ctrl+C or STOP button) |

### FR-3: Agent Code
| Field | Detail |
|-------|--------|
| Name | Agent Code |
| Trigger | Orchestrator delegates code task |
| Actor | Orchestrator |
| Preconditions | Workspace root known, project accessible |
| Behaviour | Read code → understand architecture → create/modify/delete files → run tests → fix errors → analyze logs → multi-file changes → prepare features |
| Rules | All file ops via Tool Gateway; tests via terminal tool; rollback via git checkpoint before major changes |
| States | Idle → Analyzing → Editing → Testing → Fixing → Reporting |
| Effects | File modifications, test results, git diffs |
| Failure | Test failure → analyze → fix → retry (max 3 cycles); syntax error → fix → retry |
| Permissions | Workspace root only; no network unless explicitly allowed |

### FR-4: Agent Security
| Field | Detail |
|-------|--------|
| Name | Agent Security |
| Trigger | Orchestrator delegates security audit |
| Actor | Orchestrator |
| Preconditions | Target project/environment authorized by user |
| Behaviour | SAST → dependency scan → secret scan → config review → dynamic testing (LAB only) → evidence → report with severity classification |
| Rules | Destructive tests only in LAB mode; never present hypothesis as confirmed vuln; report format per TDR §35 |
| States | Idle → Scanning → Analyzing → Testing → Reporting |
| Effects | Security report (SEC-XXX), findings log |
| Failure | Scan timeout → partial report; target unavailable → error with guidance |
| Permissions | User-authorized targets only; network only if ALLOW_NETWORK=true in LAB |

### FR-5: Agent Git
| Field | Detail |
|-------|--------|
| Name | Agent Git |
| Trigger | Orchestrator or Agent Code requests git operation |
| Actor | Orchestrator / Agent Code |
| Preconditions | Workspace is git repo |
| Behaviour | Execute: status, diff, log, branch, checkout, add, commit; remote ops configurable |
| Rules | No force-push without explicit user confirmation; snapshot before major agent work |
| States | Idle → Executing → Complete |
| Effects | Git state changes, commit history |
| Failure | Merge conflict → report to orchestrator; auth failure → error |
| Permissions | Local ops always; remote ops require config + user consent |

### FR-6: Tool Gateway
| Field | Detail |
|-------|--------|
| Name | Tool Gateway |
| Trigger | Any agent/orchestrator invokes tool |
| Actor | Orchestrator, Agents |
| Preconditions | Tool registered, schema validated |
| Behaviour | Validate call → check permissions → enforce timeout → execute → capture structured result → log → return |
| Rules | No mandatory manual validation per call; observability + resource control + stop capability required |
| Tools | filesystem, terminal, git, testing, security, process, memory, browser (optional) |
| States | Idle → Validating → Executing → Complete/Timeout/Error |
| Effects | Tool execution, logs, resource usage |
| Failure | Timeout → kill process → return error; OOM → Resource Manager intervention |
| Permissions | Per-tool permissions; ALLOW_SUDO=false by default |

### FR-7: Resource Manager
| Field | Detail |
|-------|--------|
| Name | Resource Manager |
| Trigger | Periodic (1s) + on tool/agent start |
| Actor | System (background) |
| Preconditions | Running |
| Behaviour | get_memory_usage(), check_memory_budget(), check_cpu_usage(), reduce_context(), stop_optional_worker(), shutdown_ai_worker() |
| Rules | < 3.5 GB → normal; 3.5–4 GB → degraded (reduce context, stop secondary tasks); > 4 GB → controlled shutdown of AI worker |
| States | Monitoring → Degraded → Emergency Shutdown |
| Effects | Context reduction, worker termination, alerts |
| Failure | Watchdog failure → hard kill (last resort) |
| Permissions | System-level monitoring |

### FR-8: Memory System
| Field | Detail |
|-------|--------|
| Name | Local Memory |
| Trigger | Orchestrator stores/retrieves |
| Actor | Orchestrator, Agents |
| Preconditions | SQLite + embeddings dir initialized |
| Behaviour | Store preferences, project info, conversations, embeddings; targeted retrieval (never full dump into context) |
| Rules | memory/preferences.db, projects.db, conversations.db, embeddings/; no cloud sync |
| States | Persistent |
| Effects | Disk storage, query latency |
| Failure | DB locked → retry; corruption → rebuild from source |
| Permissions | Local user only |

### FR-9: Local Unrestricted Cognitive Engine (Zero Internet, Zero Voice)
| Field | Detail |
|-------|--------|
| Name | Local Unrestricted Cognitive Engine |
| Trigger | Orchestrator delegates reasoning, planning, code or security analysis |
| Actor | Orchestrator, Agents |
| Preconditions | System running in 100% offline local mode |
| Behaviour | Process goals, decompose tasks, synthesize code, and audit security without cloud or external model dependency |
| Rules | 100% offline; zero censorship / refusals on security payloads or code analysis; voice completely disabled |
| States | Ready → Reasoning → Complete |
| Effects | Fast deterministic CPU execution, zero network traffic, 0 MB audio RAM allocation |
| Failure | Fallback to deterministic AST / pattern heuristics |
| Permissions | Local only |

### FR-10: Mode Management
| Field | Detail |
|-------|--------|
| Name | Mode Management |
| Trigger | User switches mode |
| Actor | User |
| Preconditions | System running |
| Behaviour | Normal: daily use; Autonomous: free chaining of tools; LAB: isolated env with snapshots, rollback, separate workspace, test data, full logs |
| Rules | LAB mode required for destructive security tests; network off by default in all modes |
| States | Normal ↔ Autonomous ↔ LAB |
| Effects | Tool permissions, network policy, workspace isolation |
| Failure | LAB snapshot fail → block entry |
| Permissions | User only |

---

## 3. Non-Functional Requirements

| Category | Requirement | Metric / Target |
|----------|-------------|-----------------|
| **Security** | Authentication model | Local only; no cloud auth; API on 127.0.0.1:8000 |
| | Data sensitivity | User projects, code, secrets — all local |
| | Regulated data | N/A (personal tool) |
| **Performance** | Token generation | ≥ 10 tok/s on target CPU (benchmark required) |
| | Response latency (simple) | < 2 s |
| | Response latency (multi-tool chain) | < 30 s typical |
| | RAM target | ≤ 3.5 GB steady state |
| | RAM hard limit | ≤ 4.0 GB peak |
| | CPU threads | Configurable (default 4), benchmark-tuned |
| **Availability** | Uptime | Session-based; no HA requirement |
| | Recovery | Graceful shutdown on OOM; resume from logs |
| **Scalability** | Not a concern | Single-user, single-machine |
| **Accessibility** | Not contractual | CLI + optional VS Code extension |
| **Localisation** | Languages | English primary; model-dependent |
| **Observability** | Logs | Structured per-component logs (orchestrator, agents, tools, memory, errors) |
| | Metrics | RAM, CPU, token/s, tool latency |
| **Maintainability** | Handover | Documented architecture, config, runbook |
| **Compliance** | Not applicable | Personal use |

---

## 4. Constraints

| Constraint | Detail | Source |
|------------|--------|--------|
| **OS** | Kali Linux | TDR §3 |
| **Hardware** | HP EliteBook, 10 GB RAM, CPU only | TDR §2, §3 |
| **RAM Budget** | Target ≤ 3.5 GB, Hard ≤ 4.0 GB | TDR §3, §9 |
| **GPU** | None available | TDR §3 |
| **Network** | Disabled by default (ALLOW_NETWORK=false); localhost only | TDR §3, §24 |
| **Cloud APIs** | None required | TDR §23 |
| **Model Format** | GGUF, llama.cpp compatible | TDR §8, §33 |
| **Runtime** | Python backend, FastAPI local server | TDR §33 |
| **Validation** | Pydantic | TDR §33 |
| **Monitoring** | psutil | TDR §33 |
| **Memory Store** | SQLite + local files | TDR §22 |
| **Versioning** | Git | TDR §33 |
| **Workspace** | /home/<user>/Projects | TDR §18 |
| **Privileges** | ALLOW_SUDO=false default | TDR §26 |
| **Project Structure** | Per TDR §32 directory layout | TDR §32 |

---

## 5. Scope Boundary

### In Scope
- 100% Offline Unrestricted Local Intelligence Engine (zero internet, zero censorship)
- Local inference with CPU optimization (AVX-512 / VNNI)
- Orchestrator Tech Lead with planner, router, executor, memory integration
- Three specialized agents: Code, Security (unrestricted), Git
- Tool Gateway with filesystem, terminal, git, testing, security tools
- Resource Manager with RAM/CPU monitoring, degradation, emergency shutdown
- Local memory (SQLite + embeddings) with targeted retrieval
- Three autonomy modes: Normal, Autonomous, LAB
- LAB mode with snapshots, rollback, isolated workspace
- Security audit pipeline: SAST + deps + secrets + config + dynamic (LAB)
- Structured logging per component
- Interruption handling (Ctrl+C, STOP button)
- Configuration via .env (model path, context, threads, RAM limits, network, workspace)
- VS Code integration (MVP: files + terminal; extension later)
- Final validation on target hardware

### Out of Scope
- Voice interface / STT / TTS (explicitly removed per user decision)
- Cloud LLM APIs (OpenAI, Anthropic, Google, etc.)
- Mandatory internet model downloads
- GPU acceleration (CUDA, ROCm, Metal)
- Multi-user / multi-tenant support
- Web UI / mobile app (local API only)
- Distributed/cluster deployment
- Cloud sync of memory or settings
- Mandatory telemetry
- Root-required operations (sudo disabled by default)
- Real-time streaming audio (push-to-talk or VAD only)
- Browser automation beyond optional local browser tool
- Docker/container orchestration (terminal tool can run docker compose)
- Kubernetes, cloud deployment, CI/CD pipelines
- GUI beyond CLI + optional VS Code extension

---

## 6. Assumptions

| ID | Assumption | Why Needed | If Wrong |
|----|------------|------------|----------|
| A-1 | HP EliteBook CPU supports AVX2/AVX-512 for llama.cpp optimization | Model performance depends on instruction sets | Choose model compiled for baseline x86-64; expect slower inference |
| A-2 | 10 GB RAM is fully available (OS + apps < 6 GB) | RAM budget assumes 4 GB for AI | Reduce model size/context; increase swap (degraded perf) |
| A-3 | User has sudo access for initial setup (install deps, model download) | Installation phase needs packages | Document manual install steps; use pip/user installs |
| A-4 | Kali Linux has Python 3.10+ and pip | Backend requirement | Install from source or use uv/pipx |
| A-5 | User's projects are under /home/<user>/Projects | Workspace root config | Make WORKSPACE_ROOT configurable; auto-detect common dirs |
| A-6 | llama.cpp Python bindings (llama-cpp-python) work on Kali/CPU | Primary runtime | Fallback to llama.cpp CLI + subprocess (higher latency) |
| A-7 | whisper.cpp / piper TTS run acceptably on CPU | Voice interface | Disable voice if RAM exceeded; text-only mode |
| A-8 | User accepts CLI-first interaction (VS Code extension is post-MVP) | TDR says MVP works on files+terminal | Prioritize extension earlier if CLI friction high |
| A-9 | Git is installed and configured (user.name, user.email) | Agent Git requirement | Setup wizard prompts for config |
| A-10 | No conflicting services on port 8000 | Local API server | Make SERVER_PORT configurable |

---

## 7. Unknowns

| ID | Unknown | Blocks | Blocking? |
|----|---------|--------|-----------|
| U-1 | Exact CPU model of HP EliteBook (cores, threads, ISA) | Model selection, thread count, benchmark design | **Yes** — Phase 1 Step 1 |
| U-2 | Actual free RAM after OS + typical user apps | RAM budget validation | **Yes** — Phase 1 Step 2 |
| U-3 | Available disk space for models (GGUF 2–4 GB each) | Model storage, multiple model benchmarks | **Yes** — Phase 1 Step 3 |
| U-4 | Which GGUF models pass quality threshold for code/security tasks | Model selection (Phase 1 Step 7) | **Yes** — Requires benchmark |
| U-5 | llama-cpp-python wheel availability for Kali/CPU | Runtime choice | No — can build from source |
| U-6 | STT/TTS model sizes that fit 0.3–0.5 GB budget | Voice phase (Phase 7) | No — lazy load, defer |
| U-7 | Whether VS Code extension API supports required chat/actions | Extension timeline | No — MVP without it |
| U-8 | Dynamic security testing tool availability (OWASP ZAP, nuclei, etc.) | Agent Security dynamic tests | No — install in LAB |
| U-9 | Snapshot/rollback mechanism for LAB (btrfs, LVM, git, docker?) | LAB mode implementation | No — evaluate in Phase 8 |
| U-10 | User's preferred voice language/accent for STT | STT model choice | No — default en, configurable |

---

## 8. Requirement Quality Check

All functional requirements rewritten to be testable:
- FR-1: "≥ 10 tok/s on target CPU" (measurable in benchmark)
- FR-2: "User can interrupt at any time via Ctrl+C" (testable)
- FR-3: "Test failure → analyze → fix → retry (max 3 cycles)" (verifiable)
- FR-4: "Never present hypothesis as confirmed vuln" (auditable in report)
- FR-6: "Timeout → kill process → return error" (verifiable)
- FR-7: "> 4 GB → controlled shutdown of AI worker" (verifiable)
- FR-9: "RAM budget 0.3–0.5 GB" (measurable)

---

## 9. Next Steps (Per Delivery Orchestrator)

1. **Clarification Gate** — Resolve blocking unknowns U-1, U-2, U-3, U-4 via hardware inspection + benchmark plan
2. **Technology Selection** — Confirm stack (Python/FastAPI/llama.cpp/SQLite) with alternatives
3. **Architecture Proposal** — Nine-section formal proposal
4. **Validation Gate** — User approval before implementation
5. **Delivery Planning** — Atomic task breakdown with dependencies
6. **Implementation** — Phases 1–9 per TDR

---

*Generated by requirements-analysis per delivery-orchestrator protocol.  
No requirements invented; all sourced from TDR. Assumptions and unknowns explicitly separated.*