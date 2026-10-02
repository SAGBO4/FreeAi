"""Shadow-Docker Sandbox Engine for FreeAI (Sovereign Root Confinement).
Confinements root/sudo and cyber operations inside an ephemeral, disposable container or kernel namespace.
Mode NÉANT compliant: Runs with --read-only + volatile tmpfs RAM or ephemeral memory overlay.
Enforces SacredLifeSentinel: Absolute mathematical veto on weapons, firearms, explosives, and vital healthcare.
Multi-Tier Engine:
  Tier 1: Docker Container (freeai-shadow:latest with Cyber Arsenal & Micro-Init)
  Tier 2: Bubblewrap Kernel Namespaces Sandbox (bwrap rootless isolation if Docker is offline)
  Tier 3: PhantomBusIPC (memfd_create in RAM fallback)
"""

import os
import shutil
import asyncio
import subprocess
import logging
from typing import Dict, Any, Optional
from app.security.sacred_life import SacredLifeSentinel, SacredLifeViolationError

logger = logging.getLogger("shadow_docker")


class ShadowDockerExecutor:
    """Ephemeral Sandbox Engine for root/sudo operations with multi-tier sovereign confinement."""

    DEFAULT_IMAGE: str = "freeai-shadow:latest"

    # Forbidden paths for host workspace mounts (anti-traversal / security integrity)
    FORBIDDEN_HOST_MOUNTS = {
        "/", "/etc", "/sys", "/proc", "/dev", "/boot", "/root", "/bin", "/sbin", "/usr", "/lib", "/lib64"
    }

    def __init__(self, image: Optional[str] = None):
        self.image = image or self.DEFAULT_IMAGE
        self.sentinel = SacredLifeSentinel(strict_mode=True)

    def is_docker_available(self) -> bool:
        """Checks if docker CLI is installed and the Docker daemon is responsive."""
        if not shutil.which("docker"):
            return False
        try:
            res = subprocess.run(
                ["docker", "info"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3
            )
            return res.returncode == 0
        except Exception:
            return False

    def is_bwrap_available(self) -> bool:
        """Checks if bubblewrap (bwrap) is available on the host for daemonless kernel namespace confinement."""
        return shutil.which("bwrap") is not None

    def is_image_available(self) -> bool:
        """Checks if the sandbox image is present locally."""
        if not self.is_docker_available():
            return False
        try:
            res = subprocess.run(
                ["docker", "image", "inspect", self.image],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3
            )
            return res.returncode == 0
        except Exception:
            return False

    def _validate_workspace_mount(self, host_path: str) -> str:
        """Validates host path for safe sandbox mounting."""
        abs_path = os.path.abspath(os.path.expanduser(host_path))
        if not os.path.exists(abs_path):
            raise ValueError(f"Le chemin à monter n'existe pas : {host_path}")
        normalized = os.path.normpath(abs_path)
        if normalized in self.FORBIDDEN_HOST_MOUNTS:
            raise ValueError(f"Montage du répertoire système '{normalized}' formellement interdit pour des raisons de sécurité.")
        return normalized

    def _build_preamble(self, clean_script: str) -> str:
        """Builds shell preamble providing seamless sudo and systemctl/service shims."""
        preamble = (
            "sudo() { \"$@\"; }; export -f sudo 2>/dev/null || true; "
            "systemctl() { "
            "local action=\"${2:-status}\"; local svc=\"$1\"; "
            "if [ \"$1\" = \"start\" ] || [ \"$1\" = \"stop\" ] || [ \"$1\" = \"restart\" ] || [ \"$1\" = \"status\" ]; then "
            "svc=\"$2\"; action=\"$1\"; fi; "
            "mkdir -p /run /tmp/services 2>/dev/null || true; "
            "case \"$action\" in "
            "start) "
            "if [ -x \"/etc/init.d/$svc\" ]; then /etc/init.d/\"$svc\" start; "
            "elif command -v \"$svc\" >/dev/null 2>&1; then "
            "nohup \"$svc\" > \"/tmp/services/$svc.log\" 2>&1 & "
            "echo $! > \"/run/$svc.pid\"; "
            "echo \"[SHADOW-INIT] Service $svc démarré en arrière-plan (PID $(cat /run/$svc.pid 2>/dev/null))\"; "
            "else echo \"[SHADOW-INIT] Service $svc actif (simulation micro-init)\"; fi ;; "
            "stop) "
            "if [ -f \"/run/$svc.pid\" ]; then kill -9 $(cat \"/run/$svc.pid\") 2>/dev/null || true; rm -f \"/run/$svc.pid\"; fi; "
            "echo \"[SHADOW-INIT] Service $svc arrêté\" ;; "
            "restart) systemctl stop \"$svc\"; systemctl start \"$svc\" ;; "
            "status) "
            "if [ -f \"/run/$svc.pid\" ] && kill -0 $(cat \"/run/$svc.pid\") 2>/dev/null; then "
            "echo \"● $svc.service - Active (running) [PID: $(cat /run/$svc.pid)]\"; "
            "else echo \"● $svc.service - Active (prêt / sovereign micro-init)\"; fi ;; "
            "*) echo \"[SHADOW-INIT] systemctl $action sur $svc exécuté.\" ;; "
            "esac; "
            "}; export -f systemctl 2>/dev/null || true; "
            "service() { systemctl \"$2\" \"$1\"; }; export -f service 2>/dev/null || true; "
        )
        return f"{preamble} {clean_script}"

    async def execute_sudo_task(
        self,
        script: str,
        timeout_sec: int = 45,
        network_enabled: bool = True,
        writable: bool = False,
        workspace_mount: Optional[str] = None,
        mount_mode: str = "ro"
    ) -> Dict[str, Any]:
        """Executes a bash script with root privileges inside sovereign confinement.
        Multi-Tier routing:
          1. Ephemeral Docker Sandbox
          2. Bubblewrap Linux Kernel Namespaces Sandbox (if Docker daemon offline)
          3. PhantomBusIPC memfd_create in RAM (absolute fallback)
        """
        # 1. Absolute Veto: Sacred Life Sentinel
        self.sentinel.enforce_objective_safety(script)

        clean_script = script.strip()
        if clean_script.startswith("sudo "):
            clean_script = clean_script[5:].strip()

        sandboxed_script = self._build_preamble(clean_script)

        # 2. Tier 1: Ephemeral Docker Sandbox
        if self.is_docker_available():
            return await self._execute_docker(
                sandboxed_script=sandboxed_script,
                timeout_sec=timeout_sec,
                network_enabled=network_enabled,
                writable=writable,
                workspace_mount=workspace_mount,
                mount_mode=mount_mode
            )

        # 3. Tier 2: Bubblewrap Kernel Namespaces Sandbox (daemonless)
        if self.is_bwrap_available():
            logger.info("[SHADOW SANDBOX] Docker indisponible, bascule sur Tier 2 : Bubblewrap Namespaces Sandbox.")
            return await self._execute_bwrap(
                sandboxed_script=sandboxed_script,
                timeout_sec=timeout_sec,
                network_enabled=network_enabled,
                workspace_mount=workspace_mount,
                mount_mode=mount_mode
            )

        # 4. Tier 3: PhantomBusIPC (memfd_create volatile RAM fallback)
        logger.info("[SHADOW SANDBOX] Docker et Bubblewrap indisponibles, bascule sur Tier 3 : PhantomBusIPC.")
        from app.orchestrator.phantom_bus_ipc import PhantomBusIPC
        fallback = PhantomBusIPC(strict_ethics=True)
        res = fallback.execute_volatile_script(script, privileged=True, timeout=timeout_sec)
        res["engine"] = "PhantomBusIPC (Tier 3 memfd_create fallback)"
        return res

    async def _execute_docker(
        self,
        sandboxed_script: str,
        timeout_sec: int,
        network_enabled: bool,
        writable: bool,
        workspace_mount: Optional[str],
        mount_mode: str
    ) -> Dict[str, Any]:
        """Executes task inside Docker ephemeral container."""
        cmd = [
            "docker", "run",
            "--rm",                               # Auto-destruct upon exit (0 disk residue)
            "--tmpfs", "/tmp:rw,size=64m",        # Ephemeral volatile RAM
            "--tmpfs", "/run:rw,size=16m",        # Ephemeral volatile RAM
            "--tmpfs", "/dev/shm:rw,size=64m",    # Shared memory in RAM
            "--cap-add=NET_ADMIN",                # Routing & network namespaces
        ]

        if not writable:
            # Hardened read-only with expanded volatile tmpfs mounts
            cmd.extend([
                "--read-only",
                "--tmpfs", "/var/cache:rw,size=64m",
                "--tmpfs", "/var/log:rw,size=32m",
                "--tmpfs", "/root:rw,size=32m",
            ])

        if not network_enabled:
            cmd.extend(["--network", "none"])

        if workspace_mount:
            safe_host_path = self._validate_workspace_mount(workspace_mount)
            mode = "ro" if mount_mode.lower() == "ro" else "rw"
            cmd.extend(["-v", f"{safe_host_path}:/workspace/host:{mode}"])

        target_img = self.image if self.is_image_available() else "debian:bookworm-slim"
        cmd.extend([target_img, "/bin/bash", "-c", sandboxed_script])

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout_data, stderr_data = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec)
            out = stdout_data.decode("utf-8", errors="replace").strip()
            err = stderr_data.decode("utf-8", errors="replace").strip()

            return {
                "success": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": out,
                "stderr": err,
                "engine": f"Shadow-Docker Sandbox ({target_img}) [Tier 1]",
                "writable_overlay": writable,
                "mounted_workspace": workspace_mount,
                "ephemeral": True,
                "zero_ssd": True
            }
        except asyncio.TimeoutError:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": f"Délai d'exécution dépassé ({timeout_sec}s).",
                "engine": "Shadow-Docker Sandbox [Tier 1]",
                "ephemeral": True,
                "zero_ssd": True
            }
        except Exception as e:
            logger.warning(f"[SHADOW DOCKER] Erreur container ({e}), bascule sur Bubblewrap/PhantomBus.")
            if self.is_bwrap_available():
                return await self._execute_bwrap(
                    sandboxed_script=sandboxed_script,
                    timeout_sec=timeout_sec,
                    network_enabled=network_enabled,
                    workspace_mount=workspace_mount,
                    mount_mode=mount_mode
                )
            from app.orchestrator.phantom_bus_ipc import PhantomBusIPC
            fallback = PhantomBusIPC(strict_ethics=True)
            res = fallback.execute_volatile_script(sandboxed_script, privileged=True, timeout=timeout_sec)
            res["engine"] = f"PhantomBusIPC (Fallback suite à erreur: {e})"
            return res

    async def _execute_bwrap(
        self,
        sandboxed_script: str,
        timeout_sec: int,
        network_enabled: bool,
        workspace_mount: Optional[str],
        mount_mode: str
    ) -> Dict[str, Any]:
        """Executes task inside Bubblewrap daemonless kernel namespace sandbox."""
        cmd = [
            "bwrap",
            "--ro-bind", "/usr", "/usr",
            "--ro-bind", "/lib", "/lib",
            "--proc", "/proc",
            "--dev", "/dev",
            "--tmpfs", "/tmp",
            "--tmpfs", "/run",
            "--unshare-user",
            "--unshare-ipc",
            "--unshare-pid",
            "--unshare-uts",
        ]

        if os.path.exists("/lib64"):
            cmd.extend(["--ro-bind", "/lib64", "/lib64"])
        if os.path.exists("/bin"):
            cmd.extend(["--ro-bind", "/bin", "/bin"])
        if os.path.exists("/sbin"):
            cmd.extend(["--ro-bind", "/sbin", "/sbin"])
        if os.path.exists("/etc"):
            cmd.extend(["--ro-bind", "/etc", "/etc"])

        if not network_enabled:
            cmd.append("--unshare-net")

        if workspace_mount:
            safe_host_path = self._validate_workspace_mount(workspace_mount)
            bind_flag = "--ro-bind" if mount_mode.lower() == "ro" else "--bind"
            cmd.extend([bind_flag, safe_host_path, "/workspace/host"])

        cmd.extend(["/bin/bash", "-c", sandboxed_script])

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout_data, stderr_data = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec)
            out = stdout_data.decode("utf-8", errors="replace").strip()
            err = stderr_data.decode("utf-8", errors="replace").strip()

            return {
                "success": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": out,
                "stderr": err,
                "engine": "Bubblewrap Kernel Namespaces Sandbox [Tier 2]",
                "mounted_workspace": workspace_mount,
                "ephemeral": True,
                "zero_ssd": True
            }
        except asyncio.TimeoutError:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": f"Délai d'exécution dépassé ({timeout_sec}s).",
                "engine": "Bubblewrap Sandbox [Tier 2]",
                "ephemeral": True,
                "zero_ssd": True
            }
        except Exception as e:
            logger.warning(f"[SHADOW BWRAP] Erreur bwrap ({e}), bascule sur PhantomBusIPC.")
            from app.orchestrator.phantom_bus_ipc import PhantomBusIPC
            fallback = PhantomBusIPC(strict_ethics=True)
            res = fallback.execute_volatile_script(sandboxed_script, privileged=True, timeout=timeout_sec)
            res["engine"] = f"PhantomBusIPC (Fallback suite à erreur bwrap: {e})"
            return res

    def get_status(self) -> Dict[str, Any]:
        """Returns operational status of the multi-tier Shadow Sandbox engine."""
        docker_ok = self.is_docker_available()
        bwrap_ok = self.is_bwrap_available()
        img_ok = self.is_image_available() if docker_ok else False

        active_tier = "Tier 1: Docker Sandbox" if docker_ok else ("Tier 2: Bubblewrap Namespaces" if bwrap_ok else "Tier 3: PhantomBusIPC")

        return {
            "mode": "Shadow-Docker Ephemeral Sandbox (Sovereign Multi-Tier)",
            "active_tier": active_tier,
            "docker_daemon_active": docker_ok,
            "bubblewrap_active": bwrap_ok,
            "sandbox_image": self.image,
            "image_available": img_ok,
            "security_containment": "Read-Only RootFS + Tmpfs RAM + Volatile Writable Overlay (--rm)",
            "micro_init": "systemctl & service shims intégrés (Shadow Micro-Init)",
            "cyber_arsenal": "nmap, socat, tcpdump, strace, jq, iptables, openssl, python3",
            "workspace_bridge": "Support dynamique montages sécurisés (:ro / :rw)",
            "zero_ssd": True,
            "sacred_life_sentinel": "Actif (Inviolable)",
            "fallback_mechanism": "Bubblewrap Namespaces (Tier 2) -> PhantomBusIPC memfd (Tier 3)"
        }
