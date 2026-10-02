"""Resource Manager & RAM Watchdog (TDR §10)."""

import os
import time
import logging
from typing import Dict, Any, Callable, List
import psutil

logger = logging.getLogger("resource_manager")


class ResourceManager:
    def __init__(self, target_mb: int = 3500, hard_limit_mb: int = 4000):
        self.target_mb = target_mb
        self.hard_limit_mb = hard_limit_mb
        self.degraded_callbacks: List[Callable[[], None]] = []
        self.shutdown_callbacks: List[Callable[[], None]] = []
        self._is_degraded = False

    def register_degraded_callback(self, callback: Callable[[], None]):
        self.degraded_callbacks.append(callback)

    def register_shutdown_callback(self, callback: Callable[[], None]):
        self.shutdown_callbacks.append(callback)

    def get_process_memory_mb(self) -> float:
        """Returns RSS memory of the current process and its children in MB."""
        try:
            current_proc = psutil.Process(os.getpid())
            mem_bytes = current_proc.memory_info().rss
            for child in current_proc.children(recursive=True):
                try:
                    mem_bytes += child.memory_info().rss
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            return round(mem_bytes / (1024 * 1024), 2)
        except Exception as e:
            logger.error(f"Error reading process memory: {e}")
            return 0.0

    def get_system_stats(self) -> Dict[str, Any]:
        """Returns overall system memory and CPU stats."""
        vm = psutil.virtual_memory()
        cpu_pct = psutil.cpu_percent(interval=None)
        proc_mem_mb = self.get_process_memory_mb()

        status = "normal"
        if proc_mem_mb >= self.hard_limit_mb:
            status = "critical"
        elif proc_mem_mb >= self.target_mb:
            status = "degraded"

        return {
            "ai_process_rss_mb": proc_mem_mb,
            "status": status,
            "target_limit_mb": self.target_mb,
            "hard_limit_mb": self.hard_limit_mb,
            "system_ram_total_mb": round(vm.total / (1024 * 1024), 1),
            "system_ram_used_mb": round(vm.used / (1024 * 1024), 1),
            "system_ram_available_mb": round(vm.available / (1024 * 1024), 1),
            "cpu_percent": cpu_pct,
        }

    def check_memory_budget(self) -> str:
        """Checks limits and executes degradation or emergency stop callbacks."""
        stats = self.get_system_stats()
        status = stats["status"]
        proc_mem = stats["ai_process_rss_mb"]

        if status == "critical":
            logger.critical(
                f"[WATCHDOG] CRITICAL RAM EXCEEDED: {proc_mem} MB >= {self.hard_limit_mb} MB! Triggering controlled shutdown."
            )
            for cb in self.shutdown_callbacks:
                try:
                    cb()
                except Exception as e:
                    logger.error(f"Shutdown callback failed: {e}")
            return "critical"

        elif status == "degraded":
            if not self._is_degraded:
                logger.warning(
                    f"[WATCHDOG] RAM HIGH: {proc_mem} MB >= {self.target_mb} MB. Entering degraded mode."
                )
                self._is_degraded = True
                for cb in self.degraded_callbacks:
                    try:
                        cb()
                    except Exception as e:
                        logger.error(f"Degraded callback failed: {e}")
            return "degraded"

        else:
            if self._is_degraded:
                logger.info(f"[WATCHDOG] RAM normalized: {proc_mem} MB < {self.target_mb} MB.")
                self._is_degraded = False
            return "normal"
