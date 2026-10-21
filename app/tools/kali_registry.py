"""Kali Linux Cyber Arsenal & Tool Registry for FreeAI.
Dynamically detects, inspects, and exposes local security software on Kali Linux
in standard Hermes 3 / Claude function-calling schemas.
Zero Cloud, Zero Simulation: 100% Real Local Binaries.
"""

import shutil
import subprocess
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("kali_registry")

# Catalog of primary Kali Linux tools mapped to their role & flags
KALI_TOOL_CATALOG = {
    "sqlmap": {
        "binary": "sqlmap",
        "category": "database_exploitation",
        "description": "Automatic SQL injection detection and database takeover tool.",
        "default_flags": ["--batch", "--random-agent", "--level=1", "--risk=1"],
        "schema": {
            "type": "object",
            "properties": {
                "target_url": {"type": "string", "description": "Target HTTP/HTTPS URL with parameters"},
                "extra_flags": {"type": "string", "description": "Additional sqlmap flags (e.g. --dbs, --dump)"}
            },
            "required": ["target_url"]
        }
    },
    "ffuf": {
        "binary": "ffuf",
        "category": "web_fuzzing",
        "description": "Fast web fuzzer written in Go for discovering endpoints, directories, and hidden parameters.",
        "default_flags": ["-mc", "200,301,302,403", "-t", "20"],
        "schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Target URL containing FUZZ keyword (e.g. http://localhost:8000/FUZZ)"},
                "wordlist": {"type": "string", "description": "Path to wordlist file"},
                "extra_flags": {"type": "string", "description": "Additional ffuf arguments"}
            },
            "required": ["url"]
        }
    },
    "nikto": {
        "binary": "nikto",
        "category": "web_vulnerability_scanner",
        "description": "Web server vulnerability scanner detecting dangerous files, outdated servers and misconfigurations.",
        "default_flags": ["-Tuning", "1,2,3", "-timeout", "10"],
        "schema": {
            "type": "object",
            "properties": {
                "host": {"type": "string", "description": "Target hostname or IP address (e.g. 127.0.0.1 or http://localhost:8000)"},
                "port": {"type": "integer", "description": "Target port (default 80/443 or custom)"}
            },
            "required": ["host"]
        }
    },
    "tshark": {
        "binary": "tshark",
        "category": "network_packet_analysis",
        "description": "Terminal-based Wireshark network protocol analyzer and packet capture.",
        "default_flags": ["-c", "25", "-q"],
        "schema": {
            "type": "object",
            "properties": {
                "interface": {"type": "string", "description": "Network interface (e.g. lo, eth0, wlan0)"},
                "capture_filter": {"type": "string", "description": "BPF capture filter (e.g. 'tcp port 80')"},
                "packet_count": {"type": "integer", "description": "Maximum number of packets to capture"}
            },
            "required": []
        }
    },
    "radare2": {
        "binary": "radare2",
        "category": "reverse_engineering",
        "description": "Advanced reverse engineering framework, disassembler, and binary analyzer.",
        "default_flags": ["-qc", "aaa; afl; izz"],
        "schema": {
            "type": "object",
            "properties": {
                "target_binary": {"type": "string", "description": "Path to executable binary or ELF file"},
                "commands": {"type": "string", "description": "Radare2 analysis commands (e.g. 'aaa; pdf @main')"}
            },
            "required": ["target_binary"]
        }
    },
    "binwalk": {
        "binary": "binwalk",
        "category": "firmware_forensics",
        "description": "Firmware analysis and extraction tool for searching binary images for embedded files.",
        "default_flags": ["-B"],
        "schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to binary or firmware file to analyze"},
                "extract": {"type": "boolean", "description": "Whether to extract identified file systems (-e)"}
            },
            "required": ["file_path"]
        }
    },
    "hydra": {
        "binary": "hydra",
        "category": "network_authentication_audit",
        "description": "Fast network logon cracker supporting SSH, FTP, HTTP, SMTP, MySQL, etc.",
        "default_flags": ["-t", "4", "-f"],
        "schema": {
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Target IP or hostname"},
                "service": {"type": "string", "description": "Target protocol (ssh, ftp, http-get, etc.)"},
                "username": {"type": "string", "description": "Username to audit"},
                "wordlist": {"type": "string", "description": "Path to password wordlist"}
            },
            "required": ["target", "service"]
        }
    },
    "hashcat": {
        "binary": "hashcat",
        "category": "cryptographic_audit",
        "description": "Advanced CPU/GPU hash cracker supporting MD5, SHA256, bcrypt, NTLM.",
        "default_flags": ["--runtime=30"],
        "schema": {
            "type": "object",
            "properties": {
                "hash_type": {"type": "integer", "description": "Hash mode number (e.g. 0=MD5, 1000=NTLM, 1400=SHA256)"},
                "hash_value": {"type": "string", "description": "Target hash string or hashfile path"},
                "wordlist": {"type": "string", "description": "Path to wordlist dictionary"}
            },
            "required": ["hash_type", "hash_value"]
        }
    },
    "aircrack-ng": {
        "binary": "aircrack-ng",
        "category": "wireless_security",
        "description": "802.11 WEP and WPA/WPA2-PSK key analyzing and audit program.",
        "default_flags": [],
        "schema": {
            "type": "object",
            "properties": {
                "cap_file": {"type": "string", "description": "Path to .cap or .pcap capture file"},
                "wordlist": {"type": "string", "description": "Wordlist file path"}
            },
            "required": ["cap_file"]
        }
    },
    "gh": {
        "binary": "gh",
        "category": "vulnerability_intelligence",
        "description": "GitHub CLI for querying public repos, security issues, and bounty tickets.",
        "default_flags": [],
        "schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Subcommand (e.g. 'issue list --label bounty')"}
            },
            "required": ["command"]
        }
    }
}


class KaliToolRegistry:
    """Discovers, validates, and exposes real Kali Linux tools for Hermes & Claude engines."""

    def __init__(self):
        self._installed_tools: Dict[str, str] = {}
        self._refresh_installed_tools()

    def _refresh_installed_tools(self) -> None:
        """Probes the host filesystem for local binaries in PATH."""
        self._installed_tools.clear()
        for tool_name, meta in KALI_TOOL_CATALOG.items():
            bin_name = meta["binary"]
            resolved = shutil.which(bin_name)
            if resolved:
                self._installed_tools[tool_name] = resolved

    def get_installed_tools(self) -> Dict[str, str]:
        """Returns dict of installed tool names and their real binary paths."""
        self._refresh_installed_tools()
        return dict(self._installed_tools)

    def is_tool_available(self, tool_name: str) -> bool:
        """Checks if a specific tool is actually installed and resolvable on PATH."""
        return tool_name in self.get_installed_tools()

    def get_hermes_tool_schemas(self) -> List[Dict[str, Any]]:
        """Converts available Kali tools into standard Nous Hermes 3 / Claude function schemas."""
        installed = self.get_installed_tools()
        schemas = []
        for tool_name, bin_path in installed.items():
            meta = KALI_TOOL_CATALOG.get(tool_name, {})
            schemas.append({
                "name": f"kali_{tool_name}",
                "description": f"[Local Kali Tool: {bin_path}] {meta.get('description', '')}",
                "parameters": meta.get("schema", {"type": "object", "properties": {}})
            })
        return schemas

    def build_tool_command(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[str]:
        """Constructs an executable CLI command string for a detected Kali tool."""
        clean_name = tool_name.replace("kali_", "")
        installed = self.get_installed_tools()
        if clean_name not in installed:
            logger.warning(f"[KALI_REGISTRY] Tool '{clean_name}' not installed on host.")
            return None

        bin_path = installed[clean_name]
        meta = KALI_TOOL_CATALOG.get(clean_name, {})
        default_flags = list(meta.get("default_flags", []))

        if clean_name == "sqlmap":
            target = arguments.get("target_url", "")
            extra = arguments.get("extra_flags", "")
            return f"{bin_path} -u '{target}' {' '.join(default_flags)} {extra}".strip()

        elif clean_name == "ffuf":
            url = arguments.get("url", "")
            wordlist = arguments.get("wordlist", "/usr/share/wordlists/dirb/common.txt")
            extra = arguments.get("extra_flags", "")
            return f"{bin_path} -u '{url}' -w '{wordlist}' {' '.join(default_flags)} {extra}".strip()

        elif clean_name == "nikto":
            host = arguments.get("host", "")
            port = arguments.get("port")
            port_flag = f"-p {port}" if port else ""
            return f"{bin_path} -h '{host}' {port_flag} {' '.join(default_flags)}".strip()

        elif clean_name == "tshark":
            iface = arguments.get("interface", "lo")
            count = arguments.get("packet_count", 25)
            filt = arguments.get("capture_filter", "")
            filt_flag = f"-f '{filt}'" if filt else ""
            return f"{bin_path} -i {iface} -c {count} {filt_flag} -q".strip()

        elif clean_name == "radare2":
            target = arguments.get("target_binary", "")
            cmds = arguments.get("commands", "aaa; afl")
            return f"{bin_path} -qc '{cmds}' '{target}'"

        elif clean_name == "binwalk":
            fpath = arguments.get("file_path", "")
            extract_flag = "-e" if arguments.get("extract") else "-B"
            return f"{bin_path} {extract_flag} '{fpath}'"

        elif clean_name == "hydra":
            target = arguments.get("target", "")
            svc = arguments.get("service", "ssh")
            user = arguments.get("username", "admin")
            wlist = arguments.get("wordlist", "/usr/share/wordlists/rockyou.txt")
            return f"{bin_path} -l {user} -P '{wlist}' {svc}://{target} {' '.join(default_flags)}".strip()

        elif clean_name == "hashcat":
            htype = arguments.get("hash_type", 0)
            hval = arguments.get("hash_value", "")
            wlist = arguments.get("wordlist", "/usr/share/wordlists/rockyou.txt")
            return f"{bin_path} -m {htype} '{hval}' '{wlist}' {' '.join(default_flags)}".strip()

        elif clean_name == "gh":
            cmd = arguments.get("command", "issue list")
            return f"{bin_path} {cmd}".strip()

        # Fallback generic invocation
        return f"{bin_path} {' '.join(default_flags)}".strip()
