# Architecture Proposal: F-17 Full-Screen TUI OpenCode Réplique Souveraine

## 1. Component Tree (Textual App, Screens, Widgets)

The application will be built using a hierarchical component tree managed by Textual.

*   **`FreeAIApp`** (`textual.app.App`): The root application instance handling the alternate screen buffer, global state, and keyboard shortcuts.
*   **`MainScreen`** (`textual.screen.Screen`): The primary layout screen using CSS Grid for the 5-zone structure.
    *   **`TopHeader`**: Displays active session tabs.
    *   **`CollapsibleSidebar`**: A left-hand pane (toggled via `Ctrl+B`) containing:
        *   `SessionList`: History of ephemeral sessions.
        *   `FileTree` / `DirectoryTree`: Workspace file explorer.
        *   `AgentList`: Status of available/active AI agents.
    *   **`ChatContainer`** (`ScrollableContainer`): The central captive scroll area.
        *   **`ChatMessage`**: Represents an individual user or assistant message. Contains styling for the "LeftBorder" (`┃` and `╹`).
        *   **`ThoughtAccordion`**: A collapsible widget (amber colored) spawned dynamically within a `ChatMessage` to house agent reasoning (e.g., `<think>` tags).
    *   **`InputArea`**: Anchored bottom text area for user prompts, supporting multi-line input and metadata tags.
    *   **`StatusBar`**: The bottom-most bar displaying LSP status (`• N LSP`), Git branch, and essential keybindings.

## 2. Data Flow (Streaming & Rendering)

1.  **Input Submission**: The user presses `Enter` in the `InputArea`. A message event is emitted.
2.  **Protection**: The `FreeAIApp` immediately locks the `InputArea` to prevent double-submissions (AC7).
3.  **UI Update**: A new `ChatMessage` representing the user's prompt is appended to the `ChatContainer`. A placeholder `ChatMessage` for the assistant is also appended, displaying the initial LeftBorder `┃`.
4.  **Async Inference**: An asynchronous worker is spawned to query the LLM. 
5.  **Streaming Tokens**: 
    *   The LLM yields tokens via an async generator.
    *   Tokens are batched slightly and dispatched to the UI thread using Textual's message queue (`App.post_message` or `call_from_thread`).
    *   If a `<think>` token is detected, a `ThoughtAccordion` widget is instantiated and appended to the current `ChatMessage`. Subsequent tokens are routed to this accordion.
    *   Upon `</think>`, routing returns to the main message body.
6.  **Finalization**: The stream ends. The `ChatMessage` border is capped with `╹`, the telemetry epilogue `▣` is appended, and the `InputArea` is unlocked.

## 3. Concurrency and Async (RAM < 70MB, 0 SSD Writes)

*   **Non-blocking UI**: All LLM network calls and heavy processing are offloaded to Textual workers (`@work(exclusive=True, thread=False)` to use `asyncio` tasks natively). This ensures the UI thread remains perfectly responsive (0 ms UI latency, 40fps zero-flicker rendering).
*   **Memory Frugality (Mode NÉANT)**: 
    *   To maintain an RSS under 70MB, the DOM size must be bounded. `ChatContainer` will prune old `ChatMessage` widgets if the history exceeds a safe threshold, relying on the background `SessionManager` to hold the raw text in lightweight Python primitives.
    *   Rich Markdown parsing will be optimized to re-render only the latest chunk being streamed, rather than the entire document on every token, mitigating CPU and memory spikes.
*   **0 SSD Writes**: The entire state (chat history, LSP cache, UI state) resides purely in Python memory. Database operations (if any) will strictly target `sqlite:///:memory:`. Large IPC or inter-process buffers, if required, will utilize anonymous memory-backed files (`os.memfd_create`) rather than disk.

## 4. State Management

*   **Reactive State**: Textual's `@reactive` decorators will manage UI state. 
    *   `app.is_generating` (boolean) automatically disables the `InputArea` and updates the `StatusBar`.
    *   `app.sidebar_open` (boolean) triggers CSS transitions to collapse/expand the `CollapsibleSidebar` without full screen recalculations.
*   **Ephemeral Session Manager**: A singleton `SessionManager` holds the single source of truth for conversational context. It is strictly in-memory and handles the `/compact` logic (distilling history) without writing to disk.

## 5. Tech Stack Decisions

*   **Framework**: `Textual` (latest 0.x/1.x). Chosen for its robust `asyncio` integration, DOM-based widget tree, and CSS styling which makes the 5-zone layout trivial compared to raw `curses` or `prompt_toolkit`.
*   **Styling & Rendering**: `Textual CSS (.tcss)` to enforce layout and colors. `Rich` for markdown rendering, strictly configured to disable all emojis and enforce typographic glyphs (AC6).
*   **Fallback Strategy**: Textual's `Resize` event will be monitored. If `width < 60` or `height < 15`, a full-screen `DegradedModeScreen` (showing a clear warning) is pushed to the stack to prevent UI corruption (AC8).

---
*Decision record for F-17 architecture. Ready for validation gate.*
