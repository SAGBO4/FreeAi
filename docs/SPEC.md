# SPEC: Autonomous Sovereign Bounty Hunter & Self-Healing Defense

## 1. Overview
The FreeAi project requires critical robustness and security remediations in its GitHub CLI integrations and LZ4 training data synchronisation. Concurrently, it will evolve to include an "Autonomous Sovereign Bounty Hunter" and a "Self-Healing Defense" system.

## 2. Requirements & Acceptance Criteria

### 2.1. Robustness of GitHub CLI (Bounty Radar)
**Component:** `app/tools/bounty_radar.py` & `cli.py`
- **Requirement 1:** Safe URL Parsing.
  - *Acceptance Criterion:* `repo_path.split('/', 1)` must be wrapped in a validation layer. Malformed URLs must be rejected explicitly with a typed error, without causing a crash.
- **Requirement 2:** Pre-flight Authentication Check.
  - *Acceptance Criterion:* The system must execute `gh auth status` before any API-dependent operations. Unauthenticated states must halt the process cleanly.
- **Requirement 3:** Strict Subprocess Lifecycle.
  - *Acceptance Criterion:* All `gh` subprocess calls must use `asyncio.wait_for` with a configurable timeout. Timeout exceptions must trigger cancellation of the subprocess.
- **Requirement 4:** Network Resilience.
  - *Acceptance Criterion:* Transitory network failures must be retried using an exponential backoff strategy (e.g., up to 3 retries).

### 2.2. Security of Training Sync
**Component:** `app/training/` (`gradient_sync.py`, `coordinator.py`, `worker.py`)
- **Requirement 5:** Safe Decompression.
  - *Acceptance Criterion:* LZ4 decompression of `packed_delta` must validate a cryptographic checksum before processing.
  - *Acceptance Criterion:* Decompression must enforce a strict maximum size limit (e.g., 50MB) to prevent decompression bomb attacks.
- **Requirement 6:** Defensive Timeouts.
  - *Acceptance Criterion:* Worker heartbeats and HTTP requests must have hard timeouts configured.

### 2.3. Autonomous Sovereign Bounty Hunter
- **Requirement 7:** Automated Recon & Discovery.
  - *Acceptance Criterion:* The system asynchronously scans target scopes using the robustified `bounty_radar`, managing its own rate limits and authentication states.
- **Requirement 8:** Sovereign Life-cycle Management.
  - *Acceptance Criterion:* Discovered targets are queued and processed independently without manual user triggers.

### 2.4. Self-Healing Defense
- **Requirement 9:** Anomaly Detection & Recovery.
  - *Acceptance Criterion:* If a worker process fails or times out repeatedly, the coordinator automatically isolates the worker, kills the stalled process, and spawns a fresh instance (Self-Healing).

## 3. Production Scenarios
- **Scenario A:** A malformed GitHub URL is passed to Bounty Radar. The system rejects it cleanly without a stack trace.
- **Scenario B:** The LZ4 payload is tampered with. The checksum validation fails, and the sync payload is dropped securely.
- **Scenario C:** The network connection to GitHub drops during a bounty scan. The system pauses, applies exponential backoff, and resumes or fails gracefully.
- **Scenario D:** A worker stalls during training sync. The coordinator detects the missing heartbeat, terminates the worker, and provisions a replacement.

## 4. Feature F-31: The Sovereign Resultant Engine (SRE)

### 4.1. Overview
The Sovereign Resultant Engine unites Threat Intelligence, Tor Stealth Conduits, Multi-target Hermes Self-Healing Auditing (Local & Remote APIs), and Cloud Scout synthesis into a single autonomous pipeline.

### 4.2. Requirements & Acceptance Criteria
- **AC1: Threat Sentinel (IP/ASN & Tor Exit Inspection)**:
  - `ThreatSentinel` evaluates public IP addresses, queries official Tor bulk exit node lists, resolves BGP/ASN metadata, and validates E.164 phone numbering schemas.
- **AC2: Stealth Conduit (SOCKS5/Tor Dynamic Detection & Fallback)**:
  - `StealthConduit` auto-detects active SOCKS5 proxy on `127.0.0.1:9050`. If Tor is offline, it falls back seamlessly to direct async egress without throwing unhandled exceptions.
- **AC3: Hermes Multi-Target Security Auditor (Local, Staging & Remote APIs)**:
  - `HermesAuditor` accepts any target URL (localhost, Docker containers, remote VPS, staging environments, bug bounty scopes).
  - Performs non-destructive checks: HTTP security headers (HSTS, CSP, X-Frame-Options), permissive CORS (`*`), exposed documentation (`/docs`, `/openapi.json`), and information disclosure (stack traces).
  - Generates typed remediation patches with specific header/config recommendations.
- **AC4: Sovereign Resultant Synthesis**:
  - `SovereignResultantEngine` coordinates ThreatSentinel, StealthConduit, HermesAuditor, and SovereignSearch.
  - Returns a unified `ResultantReport` with actionable threat and audit telemetry in volatile RAM (Mode NÉANT, 0 unneeded disk writes).
- **AC5: Zero-Simulation & Resilience Under Breakage**:
  - Live socket checks, real HTTP request handling, and explicit failover when remote services return HTTP 5xx or connection errors.

## 5. Feature F-32: Sovereign P2P Voice Conduit & Mesh (SVC)

### 5.1. Overview
The Sovereign P2P Voice Conduit provides carrier-free, operator-free encrypted voice communication and interactive AI voice bridging. Peers communicate using cryptographic node identities over direct P2P sockets or Tor SOCKS5 conduits in volatile RAM (Mode NÉANT), bypassing cellular BTS towers, telephone numbers, and billing registries.

### 5.2. Requirements & Acceptance Criteria
- **AC1: Cryptographic Audio Framing & Session Handshake**:
  - `VoicePacket` framing supporting raw PCM / Opus chunks with HMAC-SHA256 authentication and sequence counter.
  - Ephemeral session establishment in RAM with 0 disk persistence.
- **AC2: Transport Agnostic Routing (Tor SOCKS5 & Direct Socket)**:
  - Supports routing through Tor SOCKS5 (`127.0.0.1:9050`) or direct TCP/UDP socket with automatic detection and seamless fallback.
  - Latency monitoring and jitter buffer management in volatile ring buffers.
- **AC3: Carrier-Free Cryptographic Addressing**:
  - Zero requirement for E.164 phone numbers or SIM cards; nodes are addressed via `p2p://<peer_id>` or `onion://<hash>`.
- **AC4: Cognitive AI Voice Ingestion & Synthesis Bridge**:
  - Bidirectional in-RAM buffer for feeding incoming audio frames to speech recognition (STT) and streaming synthesized responses (TTS) directly into the call stream.
- **AC5: Robustness, Tamper Detection & Zero-Simulation**:
  - Rejection of tampered or forged audio packets, graceful reconnection on network interruption, verified through 100% real math/socket unit and integration tests.

## 6. Feature F-33: Zero-Touch Local Intercom & Apex Sovereign Resultant (ZTLI)

### 6.1. Overview
The Zero-Touch Local Intercom (ZTLI) enables instant, zero-install, zero-QR audio communication across local Wi-Fi / LAN subnets. Any device (smartphone or desktop) on the local subnet connects via `http://freeai.local:8088` (or direct IP) to an ephemeral, single-payload HTML5 intercom served directly from volatile RAM (Mode NÉANT, 0 disk I/O). The incoming audio stream connects bidirectionally to either the developer's terminal or the autonomous FreeAi voice agent. The Apex Sovereign Resultant unites ThreatSentinel, StealthConduit, HermesAuditor, and ZeroTouchIntercom into a master defense and communication mesh.

### 6.2. Requirements & Acceptance Criteria
- **AC1: mDNS / Zeroconf Local Announcement**:
  - `ZeroTouchIntercom` advertises the sovereign intercom service as `freeai.local` on the local network using standard multicast DNS and unregisters cleanly upon shutdown.
- **AC2: Zero-Disk In-RAM Web Gateway (Mode NÉANT)**:
  - Serves an embedded, self-contained HTML5/WebRTC audio client directly from an in-memory string constant. Zero file reading or disk writes (`os.open` forbidden on request path).
- **AC3: Strict Pydantic Boundary Validation**:
  - Audio chunk and signaling payloads (`AudioSignalPayload`, `IntercomStatusResponse`) are rigorously validated via Pydantic schemas.
- **AC4: Dual-Channel Loopback (Terminal Live & Autonomous AI)**:
  - Audio frames ingested from the browser are routed in RAM to the terminal and to `VoiceCognitiveBridge` for autonomous speech recognition and synthesis.
- **AC5: Apex Resultant Engine Synthesis**:
  - `SovereignResultantEngine` incorporates `ZeroTouchIntercom`, exposing unified command `/intercom` and multi-dimensional status reporting.

## 7. Feature F-34: OurFreeModel Sovereign Bridge (OFMB)

### 7.1. Overview
The OurFreeModel Sovereign Bridge gives FreeAi direct, keyless access to cutting-edge frontier models (DeepSeek V4.1 Flash, GLM 5.3 Flash, MiMo V2.6, Nemotron 3.5, etc.) using the exact reverse-engineered protocols and mechanisms of `dsh-our-free-model`. It unifies three zero-cost conduits: OpenCode Zen Gateway (with strict v2 client fingerprinting), Kilo AI Public Keyless Gateway, and Local Standalone Forward Gateway detection.

### 7.2. Requirements & Acceptance Criteria
- **AC1: OpenCode Descending Session Minting & Canonicalization**:
  - `OurFreeModelEngine` implements time-descending 48-bit session encoding `ses_<12hex><14base62>` obeying `^[0-9a-f]{9}f[c-f][0-9a-f]$` on characters 4-16, with monotonic counter 1-63.
  - Generates deterministic sessions from conversation keys (`canonicalize_session`).
- **AC2: OpenCode v2 Client Fingerprint & Tool Hygiene**:
  - Exact headers: `Authorization: Bearer public`, `User-Agent: opencode/latest/2.0.26/cli`, `x-opencode-client: cli`, mirrored `x-opencode-session`, `x-opencode-session-id`, `x-session-affinity`, `x-session-id`, `x-opencode-project: global`, and strictly NO `x-opencode-request`.
  - Injects official verbatim `read` and `shell` tool declarations, with system prompt guidance note, and strictly removes `tool_choice: "none"`.
- **AC3: Kilo AI Keyless Gateway**:
  - Dynamic discovery and execution of `isFree: true` models from `https://api.kilo.ai/api/gateway/models`.
  - Direct OpenAI-compatible POST to `https://api.kilo.ai/api/gateway/chat/completions` with unified reasoning effort format and no API key required.
- **AC4: Local Standalone Forward Auto-Discovery**:
  - Detects local running instances of `dsh-our-free-model` forward proxy (ports 18900, 18899, 18923).
  - Automatically loads `forwardKey` from `~/.our-free-model/settings.json` or `~/.config/dsh/our-free-model/settings.json`.
- **AC5: OnlineModelFederation Integration & Mode NÉANT**:
  - Seamlessly integrates into `OnlineModelFederation` (`opencode_free`, `kilo_free`, `our_free_model_local`) in `app/llm/federation.py`.
  - Zero disk write during inference (100% ephemeral RAM, Mode NÉANT).

## 8. Feature F-35: Sovereign Kimi Web Bridge (SKWB)

### 8.1. Overview
The Sovereign Kimi Web Bridge provides direct, serverless, and cloud-native access to Moonshot AI's Kimi models (Kimi K2.5 / K3) from FreeAi. It eliminates any requirement for a local proxy daemon or Node.js runtime by directly speaking the reverse-engineered Kimi Web authentication and streaming protocol (`https://kimi.moonshot.cn`), with graceful fallback to the official Moonshot developer API if an API key is configured.

### 8.2. Requirements & Acceptance Criteria
- **AC1: Automated Token Refresh & In-RAM Caching**:
  - `KimiWebBridge` exchanges user `refresh_token` (from `KIMI_REFRESH_TOKEN` or multi-token pool) for an ephemeral `access_token` via `GET https://kimi.moonshot.cn/api/auth/token/refresh`.
  - Caches `access_token` strictly in volatile memory (Mode NÉANT, 0 disk I/O) with TTL management and auto-renewal.
- **AC2: Ephemeral Chat Lifecycle Management**:
  - Creates and manages conversation sessions on `POST https://kimi.moonshot.cn/api/chat`.
  - Employs conversational state reuse or session-per-query isolation based on user settings.
- **AC3: SSE Stream Ingestion & Parsing**:
  - Streams tokens from `POST https://kimi.moonshot.cn/api/chat/{chat_id}/completion/stream`.
  - Parses incremental delta frames (`cmpl` event or `text` chunks) and terminates cleanly on `[DONE]` or stream completion.
- **AC4: Dual-Channel Fallback (Web Protocol & Official Platform API)**:
  - If `KIMI_API_KEY` is present, supports direct OpenAI-compatible querying of `https://api.moonshot.cn/v1/chat/completions`.
  - Seamlessly routes requests between Kimi Web (`kimi_web`) and Official API (`kimi`).
- **AC5: OnlineModelFederation Integration & Zero Disk Footprint**:
  - Integrates `kimi` and `kimi_web` into `OnlineModelFederation.CATALOG` in `app/llm/federation.py`.
  - Allows dynamic targeting via `/online kimi` or `/online kimi_web`.
  - 100% ephemeral in RAM (Mode NÉANT).

## 9. Feature F-36: Sovereign Kimi Interactive Playwright Authenticator (SKIPA)

### 9.1. Overview
The Sovereign Kimi Interactive Playwright Authenticator enables zero-manual-effort, assisted one-time onboarding for Moonshot Kimi AI. It automates browser launch via Playwright Chromium with anti-detection flags (`--disable-blink-features=AutomationControlled`, stealth user-agent, `navigator.webdriver` removal), directs the user to `https://kimi.moonshot.cn`, intercepts the authenticated `refresh_token` cookie upon user login (SMS/QR), saves it into `.env` and volatile memory, and closes the browser cleanly. From that point on, FreeAi runs 100% autonomously in RAM (Mode NÉANT) without ever needing a browser.

### 9.2. Requirements & Acceptance Criteria
- **AC1: Stealth Interactive Browser Context Launch**:
  - `KimiPlaywrightAuthenticator.launch_interactive_login(headless=False, timeout_sec=120)` initializes a Playwright Chromium context with anti-automation flags (`--disable-blink-features=AutomationControlled`, custom stealth scripts masking `navigator.webdriver`), navigating directly to `https://kimi.moonshot.cn`.
- **AC2: Network & Cookie Sniffing Engine**:
  - Actively polls and sniffs context cookies and network response headers on `kimi.moonshot.cn` for the `refresh_token` cookie or auth payload.
- **AC3: Automatic In-RAM & Environment Persistence**:
  - Upon capture of `refresh_token`, updates `KimiWebBridge.get_instance().set_refresh_token(...)` in RAM and writes/updates `KIMI_REFRESH_TOKEN` in `.env` if `.env` exists.
- **AC4: Clean Teardown & Timeout Guard**:
  - Closes the browser context and stops Playwright immediately upon successful extraction or if `timeout_sec` expires or if the user closes the window, preventing zombie browser processes.
- **AC5: CLI Integration & One-Touch Command**:
  - Exposes `/kimi login` in CLI and `TechLeadOrchestrator` with clear user feedback and instructions.

## 10. Feature F-37: Inngest Sovereign Durable Conduit (ISDC)

### 10.1. Overview
The Inngest Sovereign Durable Conduit provides resilient multi-LLM cascade execution across FreeAi's 49 online models. It is a genuine dual-engine architecture, and the two engines offer **different, non-interchangeable guarantees** - this distinction is load-bearing and must not be blurred in any future report:

- **Native engine (always on, Mode NÉANT)**: in-process step memoization (a dict keyed by `workflow_id`). Prevents re-executing an already-succeeded step during a retry *within the same running process*. It provides **no durability across a process crash, a reboot, or a Wi-Fi/PC shutdown** - the state is plain RAM of one process and is lost with it. This is the only engine active when the `inngest` package is absent or `INNGEST_EVENT_KEY` is unset.
- **Cloud engine (opt-in)**: activated only when the official `inngest` PyPI package is installed AND `INNGEST_EVENT_KEY` is set. The mission is sent as a signed event to Inngest Cloud (or a local Inngest Dev Server); Inngest registers and calls back into a durable function (`resilient-swarm-cascade`) via the real Inngest protocol mounted on `/api/inngest` (signature verification, function sync - not a hand-rolled stub). This is the only path that genuinely resumes a mission at its last completed step after this process restarts, and it still requires this FastAPI server to be reachable from Inngest (a public URL, or a tunnel such as ngrok/cloudflared for local dev) while a mission is in flight.

### 10.2. Requirements & Acceptance Criteria
- **AC1: Native Durable Step Engine**:
  - `InngestSovereignConduit.step_run(ctx, step_id, func, ...)` memoizes step results in `ctx.memoized_steps`, skipping completed steps on retry within the same process.
  - `step_sleep(ctx, step_id, seconds)` provides a non-blocking delay, recorded the same way.
  - Explicitly documented as non-durable across process restarts (see 10.1).
- **AC2: Multi-LLM Adaptive Circuit Breaker**:
  - `execute_resilient_swarm` cascades Groq LPU -> Kimi Web -> Kilo AI -> generic free-model fallback, escalating on empty/erroring steps without re-running earlier steps. Shared by both engines via `_run_cascade`.
- **AC3: Real Inngest Protocol Endpoint (`/api/inngest`)**:
  - When cloud mode is available, `register_inngest_routes` mounts the official `inngest.fast_api.serve(...)` handler (real signature verification and function registration), not a custom reimplementation.
  - When cloud mode is unavailable, mounts a stub that explicitly reports `cloud_mode_available: false` on GET and returns HTTP 503 on POST, so the absence of real Inngest protocol support cannot be silently mistaken for presence.
- **AC4: Ghost-Mission Telegram Telemetry Dispatch**:
  - On workflow completion or terminal failure, `dispatch_telemetry` sends execution metrics (workflow id, steps validated/failed, active engine) to Telegram Neural Vault without blocking the caller.
- **AC5: CLI & Orchestrator Integration (`/inngest`)**:
  - Exposes `/inngest status` and `/inngest swarm <prompt>` in `cli.py` / `TechLeadOrchestrator`.
- **AC6: Graceful Dual-Engine Selection**:
  - `InngestSovereignConduit.cloud_mode_available` is the single source of truth for which engine is active; `execute_resilient_swarm` picks the cloud engine (delegated, async, durable) when available and otherwise runs the native cascade synchronously in-process.

---

## 11. Feature F-38: Integrity Cleanup & Deprecation of Simulated Stubs

### 11.1. Overview
Purges all false claims and simulated stubs identified in `docs/explain.md`. Replaces misleading vocabularies ("future simulation", "satellite telepathy", "free cloud pool auto-deployment") with accurate, honest technical descriptions. Ensures FreeAi strictly complies with the Implementation Integrity constitutional rule (no stub handlers masquerading as real systems).

### 11.2. Requirements & Acceptance Criteria
- **AC1: Ghost Fork Heuristic Re-qualification**:
  - Refactors `simulate_ghost_fork` in `app/cognition/hypermesh_causal_singularity.py` to `evaluate_static_risk_heuristics`.
  - Replaces all CLI, TUI, and documentation references asserting "simulation of 4 futures" with "Static Heuristic Risk Assessment (Keywords)".
- **AC2: Honest Labeling of Theoretical/Hardware-Pending Stubs**:
  - Any module relying on unattached physical hardware (Starlink, raw radio RF) or non-existent external cloud provisioning (Free Cloud Pool) returns an explicit status `STATUS_SIMULATED_PENDING_HARDWARE` or `STATUS_THEORETICAL_CATALOGUE` instead of pretending execution succeeded.
- **AC3: Elimination of Dead/Fake Claims in CLI & Help**:
  - Cleans `cli.py` and `app/cli/smart_completer.py` so that no command description promises capabilities not backed by real code.
- **AC4: Regression Test Immunity**:
  - Preserves 100% test pass rate across existing test suites while eliminating misleading assertions.

Status: proposed

---

## 12. Feature F-39: Sovereign 49-Model Benchmark & Swarm Matrix

### 12.1. Overview
Delivers a dedicated, unified benchmark and multi-model consensus matrix utilizing the 49 real, verified online models documented in `disponible.md`. Allows users to evaluate any prompt or technical question simultaneously across all available inference channels with zero local RAM/disk footprint (Mode NÉANT), obtaining live latency measurements, response rankings, and synthesized consensus.

### 12.2. Requirements & Acceptance Criteria
- **AC1: 49-Model Catalog Ingestion & Federation Bridge**:
  - `Sovereign49BenchmarkMatrix` dynamically indexes all 49 operational models from the 5 verified channels: Kimi AI (Web), Kilo AI Gateway (18 free models), OpenRouter Gateway (17 free models), Groq Cloud LPU (11 models), and Google Gemini Pro (2 models).
- **AC2: Concurrent Asynchronous Dispatch Engine**:
  - `run_benchmark(prompt: str, mode: str = "fast", timeout_sec: int = 15)` executes concurrent queries using non-blocking HTTP streaming/gather.
  - Mode `"fast"` queries 5 champion models (1 representative per provider family).
  - Mode `"all"` queries all 49 models concurrently with semaphore-governed connection pooling to prevent socket exhaustion.
- **AC3: Live Telemetry & Metrics Capture**:
  - For every responding model, measures:
    - Real latency (in milliseconds).
    - Status (HTTP 200 vs timeout/rate-limit/network drop).
    - Response length (character count and token estimation).
    - Output snippet and first token latency when available.
  - Never fabricates or hallucinates output for unresponsive or rate-limited endpoints.
- **AC4: Cross-Model Consensus & Quality Scoring**:
  - Analyzes the multi-model responses to extract core agreed concepts, detecting the fastest responder, highest-density technical answer, and a unified sovereign resultant.
- **AC5: Rich CLI Integration (`/benchmark`)**:
  - Adds `/benchmark [prompt]` and `/benchmark all [prompt]` to `cli.py` and `TechLeadOrchestrator`.
  - Displays a clear Rich terminal table with columns: `N°`, `Fournisseur`, `Modèle`, `Latence (s)`, `Statut`, `Extrait Réponse`.
  - Prints the synthesized consensus summary at the bottom.
- **AC6: Strict Mode NÉANT Purity**:
  - 100% volatile memory execution: 0 SSD disk writes during benchmark execution.

Status: proposed







