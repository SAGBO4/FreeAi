"""Live Remote-Review Browser Session for FreeAI Auto-Apply.

Opens a REAL, visible browser (Playwright/Chromium) on a virtual display (Xvfb),
pre-fills a job application form with the candidate's real information, and
exposes that live, interactive browser session over the local network as a
noVNC web link - so a human can open it from their phone or laptop, review the
pre-filled form with their own eyes, and click "Submit" themselves.

Deliberate design choice: this module NEVER clicks a final submit/send button.
Only the human reviewer does. Field auto-fill is best-effort and heuristic: it
reports exactly which fields it found and filled, and which it could not find,
rather than claiming a blanket success. Different job sites have wildly
different form markup, so 100% autofill on every site is not a realistic claim.

Security note: the noVNC web view is bound to the LAN (0.0.0.0) so a phone on
the same Wi-Fi can open it, and protected by a random one-time VNC password
embedded in the link. It is NOT meant to be port-forwarded to the public
Internet - that would hand control of a browser logged into real accounts to
anyone with the link.
"""

import asyncio
import logging
import secrets
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("freeai.live_review_browser")

NOVNC_WEB_ROOT = "/usr/share/novnc"
PROFILES_DIR = Path("./memory/browser_profiles/applications")
GENERATED_DIR = Path("./memory/applications")

# label/attribute keywords -> profile field, used for best-effort autofill.
# Matched case-insensitively against name/id/placeholder/aria-label/associated <label>.
FIELD_KEYWORDS: Dict[str, List[str]] = {
    "full_name": ["full name", "nom complet", "your name", "candidate name"],
    "first_name": ["first name", "prénom", "prenom", "given name"],
    "last_name": ["last name", "nom de famille", "family name", "surname"],
    "email": ["email", "e-mail", "courriel"],
    "phone": ["phone", "téléphone", "telephone", "mobile", "tel"],
    "city": ["city", "ville", "current location", "localisation", "lieu de résidence", "location"],
    "linkedin": ["linkedin"],
    "github": ["github"],
    "portfolio": ["portfolio", "website", "site web"],
    "cover_letter": ["cover letter", "lettre de motivation", "motivation", "message", "pitch", "why do you"],
}

FILE_KEYWORDS: Dict[str, List[str]] = {
    "resume": ["resume", "cv", "cv file", "upload resume", "upload cv", "curriculum"],
}


def _free_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _lan_ip() -> str:
    """Best-effort real LAN IP (not loopback, not a Docker bridge)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"


@dataclass
class AutofillReport:
    filled: List[str] = field(default_factory=list)
    not_found: List[str] = field(default_factory=list)
    file_uploaded: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filled_fields": self.filled,
            "fields_not_found": self.not_found,
            "file_uploaded": self.file_uploaded,
            "fully_automatic_success": False,  # never claimed: a human always reviews
        }


class LiveApplicationReviewSession:
    """One live, human-reviewable, pre-filled browser session for a single job application.
    Never submits anything itself - only prepares the page for a human to check and send."""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or secrets.token_hex(4)
        self.display_num = 90 + (hash(self.session_id) % 400)
        self.vnc_token = secrets.token_urlsafe(9)
        self.vnc_port = _free_tcp_port()
        self.web_port = _free_tcp_port()
        self._xvfb_proc: Optional[subprocess.Popen] = None
        self._x11vnc_proc: Optional[subprocess.Popen] = None
        self._websockify_proc: Optional[subprocess.Popen] = None
        self._playwright = None
        self._browser_context = None
        self._page = None
        self.started_at: Optional[float] = None
        self._auto_close_task: Optional[asyncio.Task] = None

    # ---- infrastructure ---------------------------------------------------

    def _require_tools(self) -> None:
        missing = [t for t in ("Xvfb", "x11vnc", "websockify") if not shutil.which(t)]
        if missing:
            raise RuntimeError(
                f"Outils manquants pour la revue navigateur distante : {', '.join(missing)}. "
                f"Installer avec: sudo apt-get install x11vnc novnc"
            )

    def _start_xvfb(self) -> None:
        self._xvfb_proc = subprocess.Popen(
            ["Xvfb", f":{self.display_num}", "-screen", "0", "1280x800x24", "-nolisten", "tcp"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        time.sleep(0.6)

    def _start_x11vnc(self) -> None:
        self._x11vnc_proc = subprocess.Popen(
            [
                "x11vnc", "-display", f":{self.display_num}",
                "-rfbport", str(self.vnc_port),
                "-localhost",
                "-passwd", self.vnc_token,
                "-forever", "-shared", "-noxdamage", "-quiet",
            ],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        time.sleep(0.6)

    def _start_websockify(self) -> None:
        self._websockify_proc = subprocess.Popen(
            [
                "websockify", f"--web={NOVNC_WEB_ROOT}",
                f"0.0.0.0:{self.web_port}", f"127.0.0.1:{self.vnc_port}",
            ],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        time.sleep(0.6)

    def get_review_url(self) -> str:
        host = _lan_ip()
        return (
            f"http://{host}:{self.web_port}/vnc.html"
            f"?autoconnect=true&resize=scale&password={self.vnc_token}"
        )

    # ---- browser lifecycle --------------------------------------------------

    async def start(self, job_url: str) -> None:
        self._require_tools()
        self._start_xvfb()
        self._start_x11vnc()
        self._start_websockify()
        self.started_at = time.time()

        from playwright.async_api import async_playwright

        profile_dir = PROFILES_DIR / "default"
        profile_dir.mkdir(parents=True, exist_ok=True)

        self._playwright = await async_playwright().start()
        self._browser_context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=False,
            env={"DISPLAY": f":{self.display_num}"},
            viewport={"width": 1280, "height": 800},
            args=["--start-maximized"],
        )
        self._page = await self._browser_context.new_page()
        await self._page.goto(job_url, wait_until="domcontentloaded", timeout=30000)

    async def generate_resume_pdf(self, resume_markdown_text_as_html: str) -> Path:
        """Renders the tailored resume to a real PDF using the same browser engine,
        so file-upload fields on the application form can receive an actual file."""
        GENERATED_DIR.mkdir(parents=True, exist_ok=True)
        out_path = GENERATED_DIR / f"resume_{self.session_id}.pdf"
        pdf_page = await self._browser_context.new_page()
        await pdf_page.set_content(resume_markdown_text_as_html, wait_until="load")
        await pdf_page.pdf(path=str(out_path), format="A4", margin={"top": "20mm", "bottom": "20mm", "left": "18mm", "right": "18mm"})
        await pdf_page.close()
        return out_path

    async def autofill(self, profile_values: Dict[str, str], resume_pdf_path: Optional[Path] = None) -> AutofillReport:
        """Best-effort heuristic autofill. Reports exactly what was filled vs not found.
        Never clicks submit/send - that stays a human action."""
        report = AutofillReport()
        page = self._page

        for field_key, keywords in FIELD_KEYWORDS.items():
            value = profile_values.get(field_key)
            if not value:
                continue
            filled = await self._fill_matching_field(page, keywords, value)
            (report.filled if filled else report.not_found).append(field_key)

        if resume_pdf_path and resume_pdf_path.exists():
            uploaded = await self._upload_matching_file(page, FILE_KEYWORDS["resume"], resume_pdf_path)
            if uploaded:
                report.file_uploaded = str(resume_pdf_path)
            else:
                report.not_found.append("resume_upload")

        return report

    async def _fill_matching_field(self, page, keywords: List[str], value: str) -> bool:
        try:
            candidates = await page.evaluate(
                """(keywords) => {
                    const norm = s => (s || '').toLowerCase();
                    const inputs = Array.from(document.querySelectorAll('input, textarea'));
                    const results = [];
                    inputs.forEach((el, idx) => {
                        if (el.type === 'file' || el.type === 'hidden' || el.type === 'submit' || el.type === 'button') return;
                        let labelText = '';
                        if (el.labels && el.labels.length) labelText = el.labels[0].innerText || '';
                        const haystack = [el.name, el.id, el.placeholder, el.getAttribute('aria-label'), labelText]
                            .map(norm).join(' | ');
                        const hit = keywords.some(k => haystack.includes(k.toLowerCase()));
                        if (hit) {
                            if (!el.dataset.freeaiIdx) el.dataset.freeaiIdx = String(idx);
                            results.push(el.dataset.freeaiIdx);
                        }
                    });
                    return results;
                }""",
                keywords,
            )
        except Exception as e:
            logger.debug(f"[LIVE_REVIEW] Field scan failed: {e}")
            return False

        if not candidates:
            return False

        target = page.locator(f'[data-freeai-idx="{candidates[0]}"]')
        try:
            await target.fill(value, timeout=3000)
            return True
        except Exception as e:
            logger.debug(f"[LIVE_REVIEW] Could not fill matched field: {e}")
            return False

    async def _upload_matching_file(self, page, keywords: List[str], file_path: Path) -> bool:
        try:
            candidate_idx = await page.evaluate(
                """(keywords) => {
                    const norm = s => (s || '').toLowerCase();
                    const inputs = Array.from(document.querySelectorAll('input[type=file]'));
                    for (let idx = 0; idx < inputs.length; idx++) {
                        const el = inputs[idx];
                        let labelText = '';
                        if (el.labels && el.labels.length) labelText = el.labels[0].innerText || '';
                        const haystack = [el.name, el.id, el.getAttribute('aria-label'), labelText]
                            .map(norm).join(' | ');
                        if (keywords.some(k => haystack.includes(k.toLowerCase()))) {
                            if (!el.dataset.freeaiFileIdx) el.dataset.freeaiFileIdx = 'f' + idx;
                            return el.dataset.freeaiFileIdx;
                        }
                    }
                    return null;
                }""",
                keywords,
            )
        except Exception as e:
            logger.debug(f"[LIVE_REVIEW] File input scan failed: {e}")
            return False

        if not candidate_idx:
            return False

        try:
            await page.locator(f'[data-freeai-file-idx="{candidate_idx}"]').set_input_files(str(file_path), timeout=5000)
            return True
        except Exception as e:
            logger.debug(f"[LIVE_REVIEW] Could not upload resume file: {e}")
            return False

    async def schedule_auto_close(self, idle_minutes: int = 25) -> None:
        async def _closer():
            await asyncio.sleep(idle_minutes * 60)
            logger.info(f"[LIVE_REVIEW] Session {self.session_id} idle timeout reached, closing.")
            await self.close()

        self._auto_close_task = asyncio.create_task(_closer())

    async def close(self) -> None:
        if self._auto_close_task:
            self._auto_close_task.cancel()
        try:
            if self._browser_context:
                await self._browser_context.close()
            if self._playwright:
                await self._playwright.stop()
        except Exception as e:
            logger.debug(f"[LIVE_REVIEW] Playwright shutdown error: {e}")

        for proc in (self._websockify_proc, self._x11vnc_proc, self._xvfb_proc):
            if proc:
                try:
                    proc.terminate()
                    proc.wait(timeout=3)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
        logger.info(f"[LIVE_REVIEW] Session {self.session_id} fully closed, no process left behind.")
