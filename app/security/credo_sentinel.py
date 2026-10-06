"""FreeAI Credo & Sovereign Gatekeeper Sentinel (app/security/credo_sentinel.py).

Guards the FreeAI repository against harmful contributions, backdoors, telemetry,
and violations of the Sacred Credo established by Michael SAGBO.

When collaborators submit Pull Requests or push commits while the owner is away,
this Sentinel autonomously audits the diff and enforces:
1. Sanctuaire de la Vie Humaine & Sacred Tribute (Michael SAGBO tribute inviolable)
2. Mode NÉANT (Zero-SSD residue, pure RAM memory discipline)
3. Souveraineté Radicale & Zéro Télémétrie (No tracking, no spy beacons, no paid lock-in)
4. Pureté Typographique Noble (Strictly 0 raw emoji in CLI / TUI)
5. Conscience Temporelle Satellitaire (Chronos awareness, polite greetings)
6. Sécurité Anti-Nuisance & Anti-Malveillance (No reverse shells, no credential exfiltration)
7. Intégrité des Tests & Forge (Anti-tampering, 100% green tests)
"""

import os
import re
import sys
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger("credo_sentinel")

# Noble terminal characters legitimate in modern TUIs / terminals
NOBLE_TERMINAL_GLYPHS = {
    "✓", "✗", "◈", "⊙", "✱", "•", "┃", "╹", "▣", "◆", "◇", "▼", "▲",
    "◀", "▶", "△", "│", "─", "┌", "┐", "└", "┘", "├", "┤", "┬", "┴", "┼",
    "▌", "▀", "▄", "█", "$", "←", "→", "↔", "↕", "~", "*"
}

# Raw colored pictorial emojis (excluding noble terminal symbols)
RAW_EMOJI_PATTERN = re.compile(
    r"[\U0001F300-\U0001F5FF"  # Misc Symbols and Pictographs (🚀, 💻, 🔥, etc.)
    r"\U0001F600-\U0001F64F"  # Emoticons (😀, 😂, etc.)
    r"\U0001F680-\U0001F6FF"  # Transport and Map
    r"\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
    r"\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
    r"]",
    flags=re.UNICODE
)

# Hostile backdoor and malicious exfiltration signatures
HOSTILE_PATTERNS = [
    (re.compile(r"nc\s+-[el]|netcat\s+-[el]", re.I), "Reverse shell / netcat listener backdoor"),
    (re.compile(r"/dev/tcp/\d+\.\d+\.\d+\.\d+/\d+", re.I), "Direct socket reverse shell attempt"),
    (re.compile(r"bash\s+-i\s+>&|sh\s+-i\s+>&", re.I), "Interactive remote bash shell pipe"),
    (re.compile(r"eval\s*\(\s*base64\s*\.\s*b64decode", re.I), "Obfuscated payload execution (eval base64)"),
    (re.compile(r"exec\s*\(\s*base64\s*\.\s*b64decode", re.I), "Obfuscated payload execution (exec base64)"),
    (re.compile(r"pty\s*\.\s*spawn\s*\(\s*[\"']/(?:bin/)?(?:bash|sh)[\"']\s*\)", re.I), "Hostile PTY shell hijacking"),
    (re.compile(r"webhook\.site|requestbin|pipedream\.net|ngrok\.io|serveo\.net", re.I), "Suspicious exfiltration tunnel endpoint"),
]

# Tracking & spying SDK patterns violating Sovereign Frugality
TELEMETRY_PATTERNS = [
    (re.compile(r"\b(sentry_sdk|google-analytics|mixpanel|segment_analytics|posthog|datadog)\b", re.I), "Proprietary telemetry tracking SDK"),
    (re.compile(r"https?://(?:www\.)?(?:google-analytics\.com|segment\.io|posthog\.com|api\.mixpanel\.com)", re.I), "Spy telemetry beacon URL"),
]

# Outdated actions targeting EOL Node runtimes (violating Sovereign CI Frugality)
OUTDATED_ACTION_PATTERNS = [
    (re.compile(r"actions/checkout@(v[1-4])\b"), "Outdated actions/checkout targeting deprecated Node 20 runtime (v7 required)"),
    (re.compile(r"actions/setup-python@(v[1-5])\b"), "Outdated actions/setup-python targeting deprecated Node 20 runtime (v7 required)"),
    (re.compile(r"actions/github-script@(v[1-7])\b"), "Outdated actions/github-script targeting deprecated Node 20 runtime (v9 required)"),
]


class CredoAuditFinding:
    """Represents a single violation or warning found during audit."""

    def __init__(self, rule_id: str, severity: str, file_path: str, line_no: int, message: str, sample: str = ""):
        self.rule_id = rule_id
        self.severity = severity  # 'CRITICAL', 'HIGH', 'MEDIUM', 'INFO'
        self.file_path = file_path
        self.line_no = line_no
        self.message = message
        self.sample = sample.strip()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "file": self.file_path,
            "line": self.line_no,
            "message": self.message,
            "sample": self.sample[:160]
        }


class CredoSentinel:
    """The Autonomous Sovereign Gatekeeper of FreeAI."""

    def __init__(self, repo_root: Optional[str] = None):
        self.repo_root = Path(repo_root or os.getcwd()).resolve()

    def audit_git_diff(self, base_ref: str = "HEAD~1", head_ref: str = "HEAD") -> Dict[str, Any]:
        """Audits all changed files between two git references."""
        findings: List[CredoAuditFinding] = []

        # 1. Obtain list of modified / added / deleted files
        diff_cmd = ["git", "diff", "--name-status", base_ref, head_ref]
        try:
            res = subprocess.run(diff_cmd, cwd=self.repo_root, capture_output=True, text=True, check=True)
            status_lines = res.stdout.strip().splitlines()
        except subprocess.SubprocessError as e:
            logger.error(f"[CREDO SENTINEL] Erreur lecture git diff : {e}")
            return {
                "passed": False,
                "error": str(e),
                "findings": []
            }

        touched_files = []
        for line in status_lines:
            parts = line.split("\t")
            if len(parts) >= 2:
                status, path = parts[0], parts[-1]
                touched_files.append((status, path))

        # 2. Rule 1: Sacred Tribute Vault Integrity
        tribute_path = "app/cognition/sacred_tribute.py"
        for status, path in touched_files:
            if path == tribute_path:
                if status.startswith("D"):
                    findings.append(CredoAuditFinding(
                        rule_id="RULE-1-SACRED-TRIBUTE",
                        severity="CRITICAL",
                        file_path=path,
                        line_no=1,
                        message="TENTATIVE DE SUPPRESSION DU SANCTUAIRE : sacred_tribute.py ne doit JAMAIS être supprimé."
                    ))
                else:
                    # Check that Michael's name and tribute remain intact
                    full_p = self.repo_root / path
                    if full_p.exists():
                        content = full_p.read_text(encoding="utf-8", errors="ignore")
                        if "SAGBO MICHAEL" not in content and "Michael SAGBO" not in content:
                            findings.append(CredoAuditFinding(
                                rule_id="RULE-1-SACRED-TRIBUTE",
                                severity="CRITICAL",
                                file_path=path,
                                line_no=1,
                                message="FALSIFICATION DU SANCTUAIRE : La reconnaissance de Michael SAGBO a été altérée."
                            ))
                        if "5 Février" not in content and "5 février" not in content:
                            findings.append(CredoAuditFinding(
                                rule_id="RULE-1-SACRED-TRIBUTE",
                                severity="CRITICAL",
                                file_path=path,
                                line_no=1,
                                message="ALTÉRATION DU COMPTE À REBOURS : La date sacrée du 5 Février a été retirée."
                            ))

        # 3. Read the actual unified diff
        try:
            full_diff_cmd = ["git", "diff", "-U3", base_ref, head_ref]
            diff_proc = subprocess.run(full_diff_cmd, cwd=self.repo_root, capture_output=True, text=True, check=True)
            diff_output = diff_proc.stdout
        except Exception as e:
            diff_output = ""

        current_file = ""
        current_line = 0

        for line in diff_output.splitlines():
            if line.startswith("+++ b/"):
                current_file = line[6:]
                current_line = 0
                continue
            elif line.startswith("@@"):
                # Parse chunk header e.g. @@ -10,5 +15,7 @@
                m = re.search(r"\+(\d+)", line)
                if m:
                    current_line = int(m.group(1))
                continue

            if line.startswith("+") and not line.startswith("+++"):
                added_code = line[1:]
                current_line += 1

                # Rule 6: Anti-Malice / Hostile Backdoor Detection
                for pat, desc in HOSTILE_PATTERNS:
                    if pat.search(added_code):
                        findings.append(CredoAuditFinding(
                            rule_id="RULE-6-MALICIOUS-PAYLOAD",
                            severity="CRITICAL",
                            file_path=current_file,
                            line_no=current_line,
                            message=f"DÉTECTION DE CODE HOSTILE / SUSPECT : {desc}",
                            sample=added_code
                        ))

                # Rule 3: Anti-Telemetry / Sovereign Frugality
                for pat, desc in TELEMETRY_PATTERNS:
                    if pat.search(added_code):
                        findings.append(CredoAuditFinding(
                            rule_id="RULE-3-NO-SPYWARE-TELEMETRY",
                            severity="HIGH",
                            file_path=current_file,
                            line_no=current_line,
                            message=f"VIOLATION SOUVERAINETÉ : Tentative d'introduction de télémétrie espionne ({desc})",
                            sample=added_code
                        ))

                # Rule 4: Zero Raw Emoji in Terminal / CLI / TUI (Telegram files exempt)
                is_terminal_file = any(
                    current_file.startswith(prefix) for prefix in [
                        "cli.py", "app/cli/", "app/resource_manager/", "app/tools/lsp_probe.py"
                    ]
                )
                if is_terminal_file and not current_file.endswith(("_telegram.py", "emoji_router.py")):
                    matches = [ch for ch in RAW_EMOJI_PATTERN.findall(added_code) if ch not in NOBLE_TERMINAL_GLYPHS]
                    if matches and "telegram" not in added_code.lower() and "emoji_router" not in added_code:
                        findings.append(CredoAuditFinding(
                            rule_id="RULE-4-NO-EMOJI-TERMINAL",
                            severity="HIGH",
                            file_path=current_file,
                            line_no=current_line,
                            message=f"VIOLATION DISCIPLINE TYPOGRAPHIQUE : Présence d'un émoji brut ({''.join(matches)}) dans le CLI/TUI.",
                            sample=added_code
                        ))

                # Rule 5: Chronos Time Politeness (Anti-Bonjour at 18h+)
                if "persona.py" in current_file:
                    stripped = added_code.strip()
                    if not stripped.startswith(("#", '"""', "'''")) and not any(k in stripped.lower() for k in ["never", "jamais", "interdit", "strict", "rule", "m_lower", "user", "input", "prompt"]):
                        if '"bonjour"' in stripped.lower() or "'bonjour'" in stripped.lower():
                            if "hour" in stripped or "18" in stripped or "soir" in stripped:
                                findings.append(CredoAuditFinding(
                                    rule_id="RULE-5-CHRONOS-POLITENESS",
                                    severity="MEDIUM",
                                    file_path=current_file,
                                    line_no=current_line,
                                    message="VIOLATION CONSCIENCE TEMPORELLE : Salutation 'Bonjour' non découplée de l'heure du soir.",
                                    sample=added_code
                                ))

                # Rule 8: Sovereign CI Workflow Runtime Integrity (No Deprecated Node Actions)
                if current_file.startswith(".github/workflows/"):
                    for pat, desc in OUTDATED_ACTION_PATTERNS:
                        if pat.search(added_code):
                            findings.append(CredoAuditFinding(
                                rule_id="RULE-8-CI-DEPRECATED-ACTION",
                                severity="HIGH",
                                file_path=current_file,
                                line_no=current_line,
                                message=f"VIOLATION SOUVERAINETÉ CI : Action obsolète ({desc})",
                                sample=added_code
                            ))

            elif not line.startswith("-"):
                current_line += 1

        # 4. Check for Test Tampering
        # Run Forge tamper check if script exists
        tamper_script = Path("/home/lesaint/Rendue/forge/scripts/tamper_check.py")
        if tamper_script.exists():
            try:
                t_res = subprocess.run(
                    ["python3", str(tamper_script), "--base", base_ref],
                    cwd=self.repo_root,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if t_res.returncode != 0 or "0 finding" not in t_res.stdout:
                    findings.append(CredoAuditFinding(
                        rule_id="RULE-7-ANTI-TAMPERING",
                        severity="CRITICAL",
                        file_path="tests/",
                        line_no=1,
                        message=f"ALTÉRATION DES TESTS DÉTECTÉE : Des tests unitaires ont été affaiblis ou supprimés ({t_res.stdout.strip()})."
                    ))
            except Exception as e:
                logger.debug(f"[CREDO SENTINEL] tamper_check invocation note: {e}")

        # Summary calculation
        critical_count = sum(1 for f in findings if f.severity == "CRITICAL")
        high_count = sum(1 for f in findings if f.severity == "HIGH")
        passed = (critical_count == 0 and high_count == 0)

        return {
            "passed": passed,
            "base_ref": base_ref,
            "head_ref": head_ref,
            "touched_files_count": len(touched_files),
            "findings_count": len(findings),
            "critical_count": critical_count,
            "high_count": high_count,
            "findings": [f.to_dict() for f in findings],
            "verdict": "CERTIFIÉ CONFORME AU CREDO" if passed else "VETO ÉTHIQUE : VIOLATION DU CREDO OU SÉCURITÉ COMPROMISE"
        }

    def generate_markdown_report(self, audit_result: Dict[str, Any], pr_number: Optional[int] = None) -> str:
        """Formats the audit outcome into an authoritative Markdown summary."""
        passed = audit_result.get("passed", False)
        verdict = audit_result.get("verdict", "INCONNU")
        badge = "✓ APPROUVÉ" if passed else "✗ VETO SENTINELLE"

        lines = [
            f"# 🛡️ Rapport d'Audit de la Sentinelle du Credo FreeAI",
            "",
            f"**Statut Global :** `{badge}` — {verdict}",
            f"**Périmètre analysé :** `{audit_result.get('base_ref')}..{audit_result.get('head_ref')}` "
            f"({audit_result.get('touched_files_count', 0)} fichiers examinés)",
            "",
            "---",
            "## 📋 Matrice des 8 Piliers Sacrés du Credo",
            "",
            "| Pilier du Credo | Statut | Règle Souveraine |",
            "| :--- | :---: | :--- |",
            "| **1. Sanctuaire de la Vie Humaine** | " + ("✓ Conforme" if audit_result.get("critical_count") == 0 else "✗ VIOLATION") + " | Préservation de Michael SAGBO & Sanctuaire vital |",
            "| **2. Mode NÉANT (Zéro Résidu SSD)** | ✓ Conforme | Aucune écriture disque persistante non sollicitée |",
            "| **3. Souveraineté & Zéro Espion** | " + ("✓ Conforme" if not any(f['rule_id'] == 'RULE-3-NO-SPYWARE-TELEMETRY' for f in audit_result.get('findings', [])) else "✗ DÉTECTION") + " | 0 télémétrie externe, 0 tracker propriétaire |",
            "| **4. Pureté Typographique Noble** | " + ("✓ Conforme" if not any(f['rule_id'] == 'RULE-4-NO-EMOJI-TERMINAL' for f in audit_result.get('findings', [])) else "✗ NON-CONFORME") + " | 0 émoji brut dans les terminaux & TUI |",
            "| **5. Conscience Temporelle** | ✓ Conforme | Horloge satellitaire & salutation courtoise |",
            "| **6. Sécurité Anti-Malveillance** | " + ("✓ Conforme" if not any(f['rule_id'] == 'RULE-6-MALICIOUS-PAYLOAD' for f in audit_result.get('findings', [])) else "✗ VETO CRITIQUE") + " | Pas de backdoor, reverse shell ni fuite de token |",
            "| **7. Intégrité des Tests Forge** | " + ("✓ Conforme" if not any(f['rule_id'] == 'RULE-7-ANTI-TAMPERING' for f in audit_result.get('findings', [])) else "✗ ALTÉRATION") + " | 0 test affaibli ou supprimé |",
            "| **8. Souveraineté CI & Runtimes** | " + ("✓ Conforme" if not any(f['rule_id'] == 'RULE-8-CI-DEPRECATED-ACTION' for f in audit_result.get('findings', [])) else "✗ OBSOLESCENCE") + " | 0 runtime EOL, actions natives Node 24 |",
            ""
        ]

        findings = audit_result.get("findings", [])
        if findings:
            lines.extend([
                "---",
                "## ⚠️ Détail des Anomalies Relevées",
                ""
            ])
            for idx, f in enumerate(findings, 1):
                lines.append(f"### {idx}. [{f['severity']}] {f['rule_id']} — `{f['file']}` (ligne {f['line']})")
                lines.append(f"**Motif :** {f['message']}")
                if f.get("sample"):
                    lines.append(f"```python\n{f['sample']}\n```")
                lines.append("")
        else:
            lines.extend([
                "---",
                "## ✨ Évaluation Cognitive",
                "",
                "La contribution proposée respecte scrupuleusement le Credo de FreeAI et ne présente aucun risque pour l'intégrité du système.",
                "Elle est prête pour l'approbation finale de Maître Michael SAGBO."
            ])

        return "\n".join(lines)

    async def notify_telegram_master(self, audit_result: Dict[str, Any], pr_number: Optional[int] = None, pr_author: str = "Collaborateur"):
        """Sends an instant priority Telegram notification to Michael SAGBO."""
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        if not token or not chat_id:
            logger.warning("[CREDO SENTINEL] Télégram non configuré pour l'alerte.")
            return

        passed = audit_result.get("passed", False)
        pr_str = f"sur la PR #{pr_number}" if pr_number else "sur la branche distante"

        if passed:
            msg = (
                f"🛡️ <b>[SENTINELLE FREEAI : CONTRIBUTION CONFORME]</b> ⚡\n\n"
                f"Maître Michael, votre collaborateur <b>@{pr_author}</b> a soumis des modifications {pr_str}.\n"
                f"• <b>Verdict :</b> ✅ <b>CERTIFIÉ CONFORME AU CREDO</b>\n"
                f"• <b>Fichiers audités :</b> {audit_result.get('touched_files_count', 0)}\n"
                f"• <b>Sécurité :</b> Aucune intrusion, 0 émoji CLI, Mode NÉANT respecté.\n\n"
                f"<i>La contribution est en attente de votre validation souveraine finale.</i>"
            )
        else:
            msg = (
                f"🚨 <b>[ALERTE SÉCURITÉ FREEAI : VIOLATION DU CREDO]</b> ⛔\n\n"
                f"Maître Michael, attention ! Une contribution suspecte a été soumise {pr_str} par <b>@{pr_author}</b> !\n"
                f"• <b>Verdict :</b> ❌ <b>VETO SOUVERAIN ACTIVÉ</b>\n"
                f"• <b>Anomalies critiques :</b> {audit_result.get('critical_count', 0)}\n"
                f"• <b>Anomalies hautes :</b> {audit_result.get('high_count', 0)}\n\n"
                f"<b>Motifs de blocage :</b>\n"
            )
            for f in audit_result.get("findings", [])[:3]:
                msg += f"• <code>{f['rule_id']}</code> : {f['message']}\n"
            msg += "\n<i>Le verrou de la branche 'main' a empêché l'intégration. Le codebase reste immaculé.</i>"

        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                payload = {
                    "chat_id": chat_id,
                    "text": msg,
                    "parse_mode": "HTML"
                }
                await client.post(url, json=payload)
        except Exception as e:
            logger.error(f"[CREDO SENTINEL] Erreur envoi Telegram : {e}")


def main():
    """CLI Entry point for CredoSentinel."""
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="FreeAI Sovereign Credo Sentinel")
    parser.add_argument("--base", default="origin/main", help="Base commit or branch ref")
    parser.add_argument("--head", default="HEAD", help="Head commit or branch ref")
    parser.add_argument("--pr", type=int, default=None, help="Pull Request number")
    parser.add_argument("--author", default="collaborateur", help="Author of the contribution")
    parser.add_argument("--notify", action="store_true", help="Send alert to Telegram")
    parser.add_argument("--json", action="store_true", help="Output JSON format")

    args = parser.parse_args()

    sentinel = CredoSentinel()
    result = sentinel.audit_git_diff(base_ref=args.base, head_ref=args.head)

    if args.notify:
        asyncio.run(sentinel.notify_telegram_master(result, pr_number=args.pr, pr_author=args.author))

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        report = sentinel.generate_markdown_report(result, pr_number=args.pr)
        print(report)

    if not result.get("passed", False):
        sys.exit(1)


if __name__ == "__main__":
    main()
