/**
 * FreeAI Studio · OpenCode Client Engine
 * Implements full OpenCode UI interaction & real-time SSE streaming:
 * - Session lifecycle & persistence
 * - SSE Event consumer (reasoning, tool calls, text deltas, step telemetry)
 * - Docked prompt composer with expandable textarea, slash commands & pills
 * - Review panel & bottom terminal drawer
 */

class OpenCodeClient {
  constructor() {
    this.currentSessionId = null;
    this.sessions = [];
    this.models = [];
    this.agents = [];
    this.selectedModel = "freeai-local";
    this.selectedAgent = "Tech Lead";
    this.isBusy = false;
    this.eventSource = null;
    this.activeTurnElement = null;
    this.activeReasoningBody = null;
    this.activeReasoningShimmer = null;
    this.activeToolCards = {};
    this.activeAssistantText = null;
    this.assistantBuffer = "";

    this.initDOMElements();
    this.bindEvents();
    this.bootstrap();
  }

  initDOMElements() {
    this.timeline = document.getElementById("timeline-container");
    this.emptyHero = document.getElementById("empty-hero");
    this.textarea = document.getElementById("prompt-textarea");
    this.submitBtn = document.getElementById("submit-prompt-btn");
    this.sessionsContainer = document.getElementById("sessions-container");
    this.newSessionBtn = document.getElementById("new-session-btn");
    this.sessionTitleHeader = document.getElementById("current-session-title");
    this.statusPill = document.getElementById("global-status-pill");
    this.statusText = document.getElementById("global-status-text");

    // Popovers
    this.slashPopover = document.getElementById("slash-popover");
    this.modelPopover = document.getElementById("model-popover");
    this.agentPopover = document.getElementById("agent-popover");
    this.modelBtn = document.getElementById("model-selector-btn");
    this.agentBtn = document.getElementById("agent-selector-btn");
    this.modelLabel = document.getElementById("selected-model-label");
    this.agentLabel = document.getElementById("selected-agent-label");

    // Panels
    this.sidebar = document.getElementById("sidebar");
    this.sidebarToggleBtn = document.getElementById("sidebar-toggle-btn");
    this.diffPanel = document.getElementById("diff-panel");
    this.diffToggleBtn = document.getElementById("toggle-diff-btn");
    this.closeDiffBtn = document.getElementById("close-diff-btn");
    this.diffContentView = document.getElementById("diff-content-view");
    this.terminalDrawer = document.getElementById("terminal-drawer");
    this.terminalToggleBtn = document.getElementById("toggle-terminal-btn");
    this.closeDrawerBtn = document.getElementById("close-drawer-btn");
    this.terminalOutput = document.getElementById("terminal-output");
    this.terminalInput = document.getElementById("terminal-cmd-input");
    this.ramFooter = document.getElementById("footer-ram-info");
    this.agentsSidebarList = document.getElementById("agents-sidebar-list");
  }

  bindEvents() {
    // Textarea Auto-expand & Keyboard shortcuts
    this.textarea.addEventListener("input", () => {
      this.textarea.style.height = "auto";
      this.textarea.style.height = Math.min(this.textarea.scrollHeight, 200) + "px";
      this.handleInputTriggers();
    });

    this.textarea.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        if (this.slashPopover.classList.contains("open")) {
          const selected = this.slashPopover.querySelector(".popover-item.selected") || this.slashPopover.querySelector(".popover-item");
          if (selected) {
            this.executeSlashCommand(selected.dataset.cmd);
            return;
          }
        }
        this.submitPrompt();
      } else if (e.key === "Escape") {
        this.closeAllPopovers();
        if (this.isBusy) {
          this.abortExecution();
        }
      }
    });

    // Submit / Abort button
    this.submitBtn.addEventListener("click", () => {
      if (this.isBusy) {
        this.abortExecution();
      } else {
        this.submitPrompt();
      }
    });

    // New Session
    this.newSessionBtn.addEventListener("click", () => this.createNewSession());

    // Popover Toggles
    this.modelBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      this.togglePopover(this.modelPopover);
    });
    this.agentBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      this.togglePopover(this.agentPopover);
    });
    document.addEventListener("click", () => this.closeAllPopovers());

    // Drawer & Panel toggles
    this.sidebarToggleBtn.addEventListener("click", () => this.sidebar.classList.toggle("collapsed"));
    this.diffToggleBtn.addEventListener("click", () => {
      this.diffPanel.classList.toggle("open");
      if (this.diffPanel.classList.contains("open")) this.fetchDiff();
    });
    this.closeDiffBtn.addEventListener("click", () => this.diffPanel.classList.remove("open"));
    this.terminalToggleBtn.addEventListener("click", () => this.terminalDrawer.classList.toggle("open"));
    this.closeDrawerBtn.addEventListener("click", () => this.terminalDrawer.classList.remove("open"));

    // Terminal command runner
    this.terminalInput.addEventListener("keydown", async (e) => {
      if (e.key === "Enter") {
        const cmd = this.terminalInput.value.trim();
        if (!cmd) return;
        this.terminalInput.value = "";
        this.appendTerminalOutput(`\n❯ ${cmd}\n`);
        try {
          const res = await fetch("/api/v1/terminal/execute", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ command: cmd })
          });
          const data = await res.json();
          if (data.stdout) this.appendTerminalOutput(data.stdout + "\n");
          if (data.stderr) this.appendTerminalOutput(`[ERR] ${data.stderr}\n`);
        } catch (err) {
          this.appendTerminalOutput(`Erreur: ${err.message}\n`);
        }
      }
    });

    // Quick starter cards
    document.querySelectorAll(".starter-card").forEach(card => {
      card.addEventListener("click", () => {
        this.textarea.value = card.dataset.prompt;
        this.textarea.dispatchEvent(new Event("input"));
        this.submitPrompt();
      });
    });

    // Slash popover item click
    this.slashPopover.addEventListener("click", (e) => {
      const item = e.target.closest(".popover-item");
      if (item) {
        this.executeSlashCommand(item.dataset.cmd);
      }
    });
  }

  async bootstrap() {
    await this.fetchModels();
    await this.fetchAgents();
    await this.fetchSessions();
    this.startResourceTelemetry();
  }

  // ==========================================================================
  // Session & Data Management
  // ==========================================================================
  async fetchSessions() {
    try {
      const res = await fetch("/api/v1/sessions");
      this.sessions = await res.json();
      this.renderSessionsList();
      if (this.sessions.length > 0 && !this.currentSessionId) {
        this.switchSession(this.sessions[0].id);
      } else if (this.sessions.length === 0) {
        await this.createNewSession();
      }
    } catch (e) {
      console.error("Failed to load sessions:", e);
    }
  }

  renderSessionsList() {
    this.sessionsContainer.innerHTML = "";
    this.sessions.forEach(sess => {
      const item = document.createElement("div");
      item.className = `session-item ${sess.id === this.currentSessionId ? "active" : ""}`;
      item.innerHTML = `
        <span class="session-item-title">${escapeHtml(sess.title)}</span>
        <button class="session-item-del" title="Supprimer">✕</button>
      `;
      item.querySelector(".session-item-title").addEventListener("click", () => this.switchSession(sess.id));
      item.querySelector(".session-item-del").addEventListener("click", (e) => {
        e.stopPropagation();
        this.deleteSession(sess.id);
      });
      this.sessionsContainer.appendChild(item);
    });
  }

  async createNewSession() {
    try {
      const res = await fetch("/api/v1/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: "Nouvelle Session FreeAI" })
      });
      const newSess = await res.json();
      this.sessions.unshift(newSess);
      this.renderSessionsList();
      this.switchSession(newSess.id);
    } catch (e) {
      console.error("Error creating session:", e);
    }
  }

  async deleteSession(sessionId) {
    try {
      await fetch(`/api/v1/sessions/${sessionId}`, { method: "DELETE" });
      this.sessions = this.sessions.filter(s => s.id !== sessionId);
      this.renderSessionsList();
      if (this.currentSessionId === sessionId) {
        if (this.sessions.length > 0) {
          this.switchSession(this.sessions[0].id);
        } else {
          await this.createNewSession();
        }
      }
    } catch (e) {
      console.error("Error deleting session:", e);
    }
  }

  async switchSession(sessionId) {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
    this.currentSessionId = sessionId;
    this.renderSessionsList();

    const session = this.sessions.find(s => s.id === sessionId);
    if (session) {
      this.sessionTitleHeader.textContent = session.title;
    }

    // Clear timeline and render messages
    this.timeline.innerHTML = "";
    try {
      const res = await fetch(`/api/v1/sessions/${sessionId}`);
      const data = await res.json();
      if (data.messages && data.messages.length > 0) {
        data.messages.forEach(msg => {
          if (msg.role === "user") {
            this.appendUserMessage(msg.content);
          } else {
            this.appendAssistantMessage(msg.content);
          }
        });
      } else {
        this.timeline.appendChild(this.emptyHero);
      }
    } catch (e) {
      this.timeline.appendChild(this.emptyHero);
    }

    // Connect SSE Stream
    this.connectSSE(sessionId);
  }

  // ==========================================================================
  // Real-Time SSE Stream Integration
  // ==========================================================================
  connectSSE(sessionId) {
    if (this.eventSource) {
      this.eventSource.close();
    }
    this.eventSource = new EventSource(`/api/v1/sessions/${sessionId}/stream`);

    this.eventSource.addEventListener("server.connected", (e) => {
      this.updateStatus("Connecté", "idle");
    });

    this.eventSource.addEventListener("server.heartbeat", (e) => {
      this.pulseDot();
    });

    this.eventSource.addEventListener("session.status", (e) => {
      const payload = JSON.parse(e.data);
      const data = payload.data || {};
      if (data.status === "busy") {
        this.setBusyState(true);
      } else if (data.status === "idle") {
        this.setBusyState(false);
      }
    });

    this.eventSource.addEventListener("session.next.step.started", (e) => {
      this.initAssistantTurn();
    });

    this.eventSource.addEventListener("session.next.reasoning.started", (e) => {
      this.initReasoningAccordion();
    });

    this.eventSource.addEventListener("session.next.reasoning.delta", (e) => {
      const payload = JSON.parse(e.data);
      const data = payload.data || {};
      if (this.activeReasoningBody) {
        this.activeReasoningBody.textContent += data.delta;
        this.activeReasoningBody.scrollTop = this.activeReasoningBody.scrollHeight;
      }
      if (data.heading && this.activeReasoningShimmer) {
        this.activeReasoningShimmer.textContent = `Thinking: ${data.heading}`;
      }
    });

    this.eventSource.addEventListener("session.next.reasoning.ended", (e) => {
      if (this.activeReasoningShimmer) {
        this.activeReasoningShimmer.textContent = "Pensée & Raisonnement terminé";
        this.activeReasoningShimmer.classList.remove("reasoning-shimmer");
      }
    });

    this.eventSource.addEventListener("session.next.tool.called", (e) => {
      const payload = JSON.parse(e.data);
      const data = payload.data || {};
      this.createToolCard(data);
    });

    this.eventSource.addEventListener("session.next.tool.success", (e) => {
      const payload = JSON.parse(e.data);
      const data = payload.data || {};
      this.updateToolCard(data, "completed");
    });

    this.eventSource.addEventListener("session.next.tool.failed", (e) => {
      const payload = JSON.parse(e.data);
      const data = payload.data || {};
      this.updateToolCard(data, "failed");
    });

    this.eventSource.addEventListener("session.next.text.started", (e) => {
      this.initAssistantText();
    });

    this.eventSource.addEventListener("session.next.text.delta", (e) => {
      const payload = JSON.parse(e.data);
      const data = payload.data || {};
      if (this.activeAssistantText) {
        this.assistantBuffer += data.delta;
        if (window.marked) {
          this.activeAssistantText.innerHTML = marked.parse(this.assistantBuffer);
        } else {
          this.activeAssistantText.textContent = this.assistantBuffer;
        }
        this.scrollToBottom();
      }
    });

    this.eventSource.addEventListener("session.next.text.ended", (e) => {
      this.assistantBuffer = "";
    });

    this.eventSource.addEventListener("session.next.step.ended", (e) => {
      this.setBusyState(false);
      this.fetchDiff();
    });

    this.eventSource.onerror = (err) => {
      console.warn("[SSE] Disconnected or reconnecting...", err);
      this.updateStatus("Reconnexion...", "busy");
    };
  }

  // ==========================================================================
  // Timeline UI Construction
  // ==========================================================================
  appendUserMessage(text) {
    if (this.emptyHero.parentNode === this.timeline) {
      this.timeline.removeChild(this.emptyHero);
    }
    const msg = document.createElement("div");
    msg.className = "message-user";
    msg.textContent = text;
    this.timeline.appendChild(msg);
    this.scrollToBottom();
  }

  appendAssistantMessage(markdownContent) {
    if (this.emptyHero.parentNode === this.timeline) {
      this.timeline.removeChild(this.emptyHero);
    }
    const container = document.createElement("div");
    container.className = "message-assistant";
    const textEl = document.createElement("div");
    textEl.className = "assistant-text";
    textEl.innerHTML = window.marked ? marked.parse(markdownContent) : markdownContent;
    container.appendChild(textEl);
    this.timeline.appendChild(container);
    this.scrollToBottom();
  }

  initAssistantTurn() {
    if (this.emptyHero.parentNode === this.timeline) {
      this.timeline.removeChild(this.emptyHero);
    }
    const turn = document.createElement("div");
    turn.className = "message-assistant";
    this.timeline.appendChild(turn);
    this.activeTurnElement = turn;
    this.scrollToBottom();
  }

  initReasoningAccordion() {
    if (!this.activeTurnElement) this.initAssistantTurn();
    const accordion = document.createElement("div");
    accordion.className = "reasoning-accordion";
    accordion.innerHTML = `
      <div class="reasoning-header">
        <div class="reasoning-title-group">
          <span>🧠</span>
          <span class="reasoning-shimmer">Thinking...</span>
        </div>
        <span>▾</span>
      </div>
      <div class="reasoning-body"></div>
    `;
    const body = accordion.querySelector(".reasoning-body");
    const header = accordion.querySelector(".reasoning-header");
    header.addEventListener("click", () => {
      body.style.display = body.style.display === "none" ? "block" : "none";
    });

    this.activeTurnElement.appendChild(accordion);
    this.activeReasoningBody = body;
    this.activeReasoningShimmer = accordion.querySelector(".reasoning-shimmer");
    this.scrollToBottom();
  }

  createToolCard(toolData) {
    if (!this.activeTurnElement) this.initAssistantTurn();
    const card = document.createElement("div");
    card.className = "tool-card";
    const partId = toolData.part_id || `tool_${Date.now()}`;
    card.id = partId;
    card.innerHTML = `
      <div class="tool-card-header">
        <div class="tool-name-group">
          <span>⚙️</span>
          <span>${escapeHtml(toolData.tool_name)}</span>
        </div>
        <span class="tool-badge running">En cours</span>
      </div>
      <div class="tool-card-body" style="display: none;">${escapeHtml(JSON.stringify(toolData.arguments || {}, null, 2))}</div>
    `;
    const header = card.querySelector(".tool-card-header");
    const body = card.querySelector(".tool-card-body");
    header.addEventListener("click", () => {
      body.style.display = body.style.display === "none" ? "block" : "none";
    });

    this.activeTurnElement.appendChild(card);
    this.activeToolCards[partId] = card;
    this.scrollToBottom();
  }

  updateToolCard(toolData, status) {
    const partId = toolData.part_id;
    const card = this.activeToolCards[partId] || document.getElementById(partId);
    if (!card) return;

    const badge = card.querySelector(".tool-badge");
    badge.className = `tool-badge ${status}`;
    const duration = toolData.duration_ms ? ` (${toolData.duration_ms}ms)` : "";
    badge.textContent = status === "completed" ? `Succès${duration}` : `Erreur${duration}`;

    const body = card.querySelector(".tool-card-body");
    if (toolData.output) {
      body.textContent = toolData.output;
      body.style.display = "block";
    }
    this.scrollToBottom();
  }

  initAssistantText() {
    if (!this.activeTurnElement) this.initAssistantTurn();
    const textEl = document.createElement("div");
    textEl.className = "assistant-text";
    this.activeTurnElement.appendChild(textEl);
    this.activeAssistantText = textEl;
    this.assistantBuffer = "";
  }

  scrollToBottom() {
    this.timeline.scrollTop = this.timeline.scrollHeight;
  }

  // ==========================================================================
  // Prompt Submission & Controls
  // ==========================================================================
  async submitPrompt() {
    const text = this.textarea.value.trim();
    if (!text || this.isBusy) return;

    this.textarea.value = "";
    this.textarea.style.height = "auto";
    this.appendUserMessage(text);
    this.setBusyState(true);

    try {
      await fetch(`/api/v1/sessions/${this.currentSessionId}/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: text,
          model: this.selectedModel,
          agent_role: this.selectedAgent
        })
      });
    } catch (e) {
      console.error("Submit error:", e);
      this.setBusyState(false);
    }
  }

  async abortExecution() {
    if (!this.currentSessionId) return;
    try {
      await fetch(`/api/v1/sessions/${this.currentSessionId}/abort`, { method: "POST" });
      this.setBusyState(false);
      this.updateStatus("Interrompu", "idle");
    } catch (e) {
      console.error("Abort error:", e);
    }
  }

  setBusyState(busy) {
    this.isBusy = busy;
    if (busy) {
      this.submitBtn.classList.add("stop");
      this.submitBtn.innerHTML = "<span>■</span>";
      this.submitBtn.title = "Arrêter l'exécution (Esc)";
      this.updateStatus("Génération en cours...", "busy");
    } else {
      this.submitBtn.classList.remove("stop");
      this.submitBtn.innerHTML = "<span>➤</span>";
      this.submitBtn.title = "Envoyer (Enter)";
      this.updateStatus("Prêt", "idle");
    }
  }

  updateStatus(text, mode) {
    this.statusText.textContent = text;
    if (mode === "busy") {
      this.statusPill.classList.add("busy");
    } else {
      this.statusPill.classList.remove("busy");
    }
  }

  pulseDot() {
    const dot = this.statusPill.querySelector(".status-dot");
    dot.style.transform = "scale(1.4)";
    setTimeout(() => { dot.style.transform = "scale(1)"; }, 300);
  }

  // ==========================================================================
  // Popovers & Slash Commands
  // ==========================================================================
  handleInputTriggers() {
    const text = this.textarea.value;
    if (text.startsWith("/")) {
      this.slashPopover.classList.add("open");
    } else {
      this.slashPopover.classList.remove("open");
    }
  }

  executeSlashCommand(cmd) {
    this.textarea.value = "";
    this.textarea.style.height = "auto";
    this.closeAllPopovers();

    if (cmd === "/clear") {
      this.timeline.innerHTML = "";
      this.timeline.appendChild(this.emptyHero);
    } else if (cmd === "/new") {
      this.createNewSession();
    } else if (cmd === "/diff") {
      this.diffPanel.classList.add("open");
      this.fetchDiff();
    } else if (cmd === "/status") {
      this.terminalDrawer.classList.add("open");
    } else {
      this.textarea.value = cmd + " ";
      this.textarea.focus();
    }
  }

  closeAllPopovers() {
    document.querySelectorAll(".popover-menu").forEach(p => p.classList.remove("open"));
  }

  togglePopover(el) {
    const wasOpen = el.classList.contains("open");
    this.closeAllPopovers();
    if (!wasOpen) el.classList.add("open");
  }

  // ==========================================================================
  // Models & Agents Catalogs
  // ==========================================================================
  async fetchModels() {
    try {
      const res = await fetch("/api/v1/models");
      this.models = await res.json();
      this.modelPopover.innerHTML = "";
      this.models.forEach(m => {
        const item = document.createElement("div");
        item.className = `popover-item ${m.id === this.selectedModel ? "selected" : ""}`;
        item.innerHTML = `<span class="cmd">${escapeHtml(m.name)}</span><span class="desc">${escapeHtml(m.speed)}</span>`;
        item.addEventListener("click", () => {
          this.selectedModel = m.id;
          this.modelLabel.textContent = m.name.split(" ")[0] + " " + (m.name.split(" ")[1] || "");
          this.closeAllPopovers();
        });
        this.modelPopover.appendChild(item);
      });
    } catch (e) {}
  }

  async fetchAgents() {
    try {
      const res = await fetch("/api/v1/agents");
      this.agents = await res.json();
      this.agentPopover.innerHTML = "";
      this.agentsSidebarList.innerHTML = "";

      this.agents.forEach(a => {
        // Popover item
        const item = document.createElement("div");
        item.className = `popover-item ${a.name === this.selectedAgent ? "selected" : ""}`;
        item.innerHTML = `<span class="cmd">${a.glyph} ${escapeHtml(a.name)}</span>`;
        item.addEventListener("click", () => {
          this.selectedAgent = a.name;
          this.agentLabel.textContent = a.name;
          this.closeAllPopovers();
        });
        this.agentPopover.appendChild(item);

        // Sidebar item
        const sideItem = document.createElement("div");
        sideItem.className = "agent-pill-item";
        sideItem.innerHTML = `
          <div class="agent-badge-dot" style="background: ${a.color};"></div>
          <span>${a.glyph} ${escapeHtml(a.name)}</span>
        `;
        sideItem.addEventListener("click", () => {
          this.selectedAgent = a.name;
          this.agentLabel.textContent = a.name;
        });
        this.agentsSidebarList.appendChild(sideItem);
      });
    } catch (e) {}
  }

  // ==========================================================================
  // Diff & Terminal Integration
  // ==========================================================================
  async fetchDiff() {
    try {
      const res = await fetch("/api/v1/diff");
      const data = await res.json();
      if (data.diff) {
        this.diffContentView.innerHTML = formatDiff(data.diff);
      } else {
        this.diffContentView.innerHTML = `<div style="color: var(--v2-grey-500); padding: 10px;">Aucune modification non validée dans le répertoire git.</div>`;
      }
    } catch (e) {
      this.diffContentView.textContent = "Erreur de chargement du diff.";
    }
  }

  appendTerminalOutput(text) {
    this.terminalOutput.textContent += text;
    this.terminalOutput.scrollTop = this.terminalOutput.scrollHeight;
  }

  startResourceTelemetry() {
    setInterval(async () => {
      try {
        const res = await fetch("/resources");
        const stats = await res.json();
        if (stats && stats.rss_mb !== undefined) {
          this.ramFooter.textContent = `RAM: ${Math.round(stats.rss_mb)} MB`;
        }
      } catch (e) {}
    }, 4000);
  }
}

// Helpers
function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function formatDiff(rawDiff) {
  const lines = rawDiff.split("\n");
  return lines.map(line => {
    if (line.startsWith("+") && !line.startsWith("+++")) {
      return `<div class="diff-add">${escapeHtml(line)}</div>`;
    } else if (line.startsWith("-") && !line.startsWith("---")) {
      return `<div class="diff-del">${escapeHtml(line)}</div>`;
    } else if (line.startsWith("@@")) {
      return `<div style="color: #60a5fa; font-weight: bold;">${escapeHtml(line)}</div>`;
    }
    return `<div>${escapeHtml(line)}</div>`;
  }).join("");
}

// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", () => {
  window.freeAiClient = new OpenCodeClient();
});
