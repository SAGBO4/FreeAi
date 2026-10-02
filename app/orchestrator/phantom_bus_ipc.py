"""Phantom Memfd IPC Engine for FreeAI.
Creates in-memory volatile execution units via Linux native memfd_create system call.
Enforces SacredLifeSentinel: absolute mathematical veto on weapons, firearms, explosives,
and vital medical systems, while providing total freedom for sudo and computing operations.
Zero bytes written to SSD (Mode NÉANT).
"""

import os
import subprocess
from typing import Dict, Any, Optional
from app.security.sacred_life import SacredLifeSentinel, SacredLifeViolationError

class PhantomBusIPC:
    """Linux anonymous memory-file execution engine for zero-SSD volatile operations."""

    def __init__(self, strict_ethics: bool = True):
        self.sentinel = SacredLifeSentinel(strict_mode=strict_ethics)

    def execute_volatile_script(
        self,
        bash_script: str,
        privileged: bool = False,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """Executes a bash script entirely inside volatile RAM via memfd_create.
        Enforces the Sacred Life Veto before running.
        """
        # 1. Absolute Veto Check: Sacred Life Sentinel
        self.sentinel.enforce_objective_safety(bash_script)

        # 2. Allocate anonymous volatile memory descriptor (VFS RAM)
        if hasattr(os, "memfd_create"):
            fd = os.memfd_create("phantom_exec", getattr(os, "MFD_CLOEXEC", 1))
        else:
            import ctypes
            libc = ctypes.CDLL(None)
            fd = libc.syscall(319, b"phantom_exec", 1)  # NR_memfd_create on x86_64

        if fd < 0:
            raise OSError("Impossible de créer le descripteur memfd volatile.")

        try:
            # 3. Write script directly to volatile RAM
            os.write(fd, bash_script.encode("utf-8"))
            os.lseek(fd, 0, os.SEEK_SET)

            # 4. Construct execution target via /proc/self/fd/<fd>
            fd_path = f"/proc/self/fd/{fd}"
            cmd = ["/bin/bash", fd_path]

            # 5. Run process with inherited descriptor
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                pass_fds=(fd,),
                timeout=timeout
            )

            return {
                "success": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": proc.stdout.strip(),
                "stderr": proc.stderr.strip(),
                "memfd": True,
                "zero_ssd": True
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": f"Execution timed out after {timeout} seconds.",
                "memfd": True,
                "zero_ssd": True
            }
        except Exception as e:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "memfd": True,
                "zero_ssd": True
            }
        finally:
            try:
                os.close(fd)
            except OSError:
                pass

    def get_status(self) -> Dict[str, Any]:
        """Returns status of Phantom Bus IPC."""
        return {
            "mechanism": "Linux memfd_create VFS RAM",
            "zero_ssd": True,
            "sacred_life_sentinel": "Active (Inviolable)",
            "sudo_mode_authorized": True
        }
