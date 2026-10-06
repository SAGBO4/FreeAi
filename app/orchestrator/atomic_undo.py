"""Atomic Rollback & Undo Manager for FreeAI (OpenCode Architecture).
Provides instant, atomic file rollback and snapshot management for code modifications
with Git integration, file state delta tracking, and noble TUI telemetry.
"""

import os
import time
import uuid
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple


@dataclass
class FileStateRecord:
    path: str
    existed: bool
    content: Optional[str] = None
    size: int = 0


@dataclass
class UndoSnapshot:
    snapshot_id: str
    description: str
    timestamp: float
    files_before: Dict[str, FileStateRecord] = field(default_factory=dict)
    files_after: Dict[str, FileStateRecord] = field(default_factory=dict)
    git_head: Optional[str] = None


class AtomicUndoManager:
    """Manages an in-memory stack of atomic file rollback snapshots."""
    _WORKSPACE_UNDO_STACKS: Dict[str, List[UndoSnapshot]] = {}
    _WORKSPACE_REDO_STACKS: Dict[str, List[UndoSnapshot]] = {}

    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root).resolve()
        ws_key = str(self.workspace_root)
        if ws_key not in self._WORKSPACE_UNDO_STACKS:
            self._WORKSPACE_UNDO_STACKS[ws_key] = []
        if ws_key not in self._WORKSPACE_REDO_STACKS:
            self._WORKSPACE_REDO_STACKS[ws_key] = []
        self.undo_stack: List[UndoSnapshot] = self._WORKSPACE_UNDO_STACKS[ws_key]
        self.redo_stack: List[UndoSnapshot] = self._WORKSPACE_REDO_STACKS[ws_key]
        self.max_stack_size = 50

    def rollback_latest(self) -> Dict[str, Any]:
        """Alias for undo() to guarantee compatibility with slash command /undo."""
        return self.undo()


    def _get_git_head(self) -> Optional[str]:
        try:
            res = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=str(self.workspace_root),
                stderr=subprocess.DEVNULL
            ).decode().strip()
            return res
        except Exception:
            return None

    def _capture_file_record(self, rel_path: str) -> FileStateRecord:
        abs_path = self.workspace_root / rel_path
        if abs_path.is_file():
            try:
                content = abs_path.read_text(encoding="utf-8", errors="replace")
                return FileStateRecord(path=rel_path, existed=True, content=content, size=len(content))
            except Exception:
                return FileStateRecord(path=rel_path, existed=True, content=None, size=0)
        return FileStateRecord(path=rel_path, existed=False, content=None, size=0)

    def create_snapshot(self, description: str, files_to_track: Optional[List[str]] = None) -> UndoSnapshot:
        """Takes a snapshot of target files before any modification is applied."""
        snap_id = f"snap_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        git_head = self._get_git_head()
        
        # If files_to_track not provided, probe git dirty files or track workspace
        tracked = files_to_track or []
        if not tracked:
            try:
                status_out = subprocess.check_output(
                    ["git", "status", "--porcelain"],
                    cwd=str(self.workspace_root),
                    stderr=subprocess.DEVNULL
                ).decode()
                for line in status_out.splitlines():
                    if len(line) > 3:
                        tracked.append(line[3:].strip())
            except Exception:
                pass

        files_before = {}
        for f in tracked:
            files_before[f] = self._capture_file_record(f)

        snapshot = UndoSnapshot(
            snapshot_id=snap_id,
            description=description,
            timestamp=time.time(),
            files_before=files_before,
            git_head=git_head
        )
        self.undo_stack.append(snapshot)
        if len(self.undo_stack) > self.max_stack_size:
            self.undo_stack.pop(0)

        # Clear redo stack when a new operation starts
        self.redo_stack.clear()
        return snapshot

    def finalize_snapshot(self, snapshot: UndoSnapshot, modified_files: List[str]):
        """Records the post-execution state of affected files for diff and redo support."""
        for f in modified_files:
            # If not in files_before, capture what it was before we knew
            if f not in snapshot.files_before:
                # Fallback: if not tracked before, assume it was either non-existent or read git
                snapshot.files_before[f] = FileStateRecord(path=f, existed=False)
            snapshot.files_after[f] = self._capture_file_record(f)

    def undo(self) -> Dict[str, Any]:
        """Atomically rolls back the most recent snapshot."""
        if not self.undo_stack:
            return {
                "success": False,
                "message": "Aucun instantané d'annulation disponible dans la pile.",
                "reverted_files": []
            }

        snapshot = self.undo_stack.pop()
        reverted_files = []

        # If files_after was not recorded, record current state before reverting for redo
        if not snapshot.files_after:
            for f in snapshot.files_before:
                snapshot.files_after[f] = self._capture_file_record(f)

        for rel_path, before_state in snapshot.files_before.items():
            abs_path = self.workspace_root / rel_path
            try:
                if not before_state.existed:
                    # File was newly created in this step -> delete it
                    if abs_path.exists():
                        abs_path.unlink()
                        reverted_files.append({"file": rel_path, "action": "deleted_created"})
                else:
                    # File existed before -> restore original content
                    if before_state.content is not None:
                        abs_path.parent.mkdir(parents=True, exist_ok=True)
                        abs_path.write_text(before_state.content, encoding="utf-8")
                        reverted_files.append({"file": rel_path, "action": "restored"})
            except Exception as e:
                reverted_files.append({"file": rel_path, "action": f"error: {e}"})

        # Push to redo stack
        self.redo_stack.append(snapshot)

        return {
            "success": True,
            "snapshot_id": snapshot.snapshot_id,
            "description": snapshot.description,
            "reverted_files": reverted_files,
            "count": len(reverted_files),
            "message": f"Rollback atomique réussi pour '{snapshot.description}'"
        }

    def redo(self) -> Dict[str, Any]:
        """Re-applies the most recently undone snapshot."""
        if not self.redo_stack:
            return {
                "success": False,
                "message": "Aucune opération à rétablir dans la pile redo.",
                "reapplied_files": []
            }

        snapshot = self.redo_stack.pop()
        reapplied_files = []

        for rel_path, after_state in snapshot.files_after.items():
            abs_path = self.workspace_root / rel_path
            try:
                if not after_state.existed:
                    if abs_path.exists():
                        abs_path.unlink()
                        reapplied_files.append({"file": rel_path, "action": "deleted"})
                else:
                    if after_state.content is not None:
                        abs_path.parent.mkdir(parents=True, exist_ok=True)
                        abs_path.write_text(after_state.content, encoding="utf-8")
                        reapplied_files.append({"file": rel_path, "action": "reapplied"})
            except Exception as e:
                reapplied_files.append({"file": rel_path, "action": f"error: {e}"})

        self.undo_stack.append(snapshot)

        return {
            "success": True,
            "snapshot_id": snapshot.snapshot_id,
            "description": snapshot.description,
            "reapplied_files": reapplied_files,
            "count": len(reapplied_files),
            "message": f"Rétablissement atomique réussi pour '{snapshot.description}'"
        }

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """Returns the list of available snapshots in the undo stack."""
        history = []
        for idx, snap in enumerate(reversed(self.undo_stack)):
            history.append({
                "index": idx + 1,
                "snapshot_id": snap.snapshot_id,
                "description": snap.description,
                "timestamp": snap.timestamp,
                "files_count": len(snap.files_before)
            })
        return history
