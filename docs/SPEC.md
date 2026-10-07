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
