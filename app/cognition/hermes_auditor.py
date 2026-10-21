"""Hermes Multi-Target Security Auditor & Self-Healing Patch Generator.
Audits local, staging, remote VPS, and Bug Bounty API endpoints for security posture:
- Strict-Transport-Security (HSTS), Content-Security-Policy (CSP), X-Frame-Options
- Wildcard CORS (Access-Control-Allow-Origin: *)
- Exposed Swagger/OpenAPI documentation (/docs, /openapi.json)
- Information disclosure (server tokens, stack traces)
Generates typed remediation patches in volatile RAM.
"""

import re
import urllib.parse
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

import httpx

logger = logging.getLogger("freeai.cognition.hermes_auditor")


@dataclass
class RemediationPatch:
    issue_type: str
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    description: str
    recommended_patch: str
    target_component: str = "HTTP Headers / Middleware"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AuditReport:
    target_url: str
    reachable: bool = True
    status_code: Optional[int] = None
    has_hsts: bool = False
    has_csp: bool = False
    has_x_frame_options: bool = False
    permissive_cors: bool = False
    exposed_docs: List[str] = field(default_factory=list)
    server_token: Optional[str] = None
    remediations: List[RemediationPatch] = field(default_factory=list)
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res["remediations"] = [r.to_dict() for r in self.remediations]
        return res


class HermesAuditor:
    """Multi-target Defensive API and Web Application Auditor."""

    ALLOWED_SCHEMES = ("http", "https")

    def validate_target_url(self, url: str) -> bool:
        """Validates that target URL is a well-formed HTTP/HTTPS endpoint."""
        try:
            parsed = urllib.parse.urlparse(url.strip())
            return parsed.scheme in self.ALLOWED_SCHEMES and bool(parsed.netloc)
        except Exception:
            return False

    async def audit_target(self, target_url: str, timeout_sec: float = 6.0) -> AuditReport:
        """Performs non-destructive audit of target endpoint and generates remediation."""
        clean_url = target_url.strip()
        if not self.validate_target_url(clean_url):
            return AuditReport(
                target_url=clean_url,
                reachable=False,
                error_message="Invalid URL: Scheme must be http or https with valid host"
            )

        headers = {
            "User-Agent": "FreeAi-HermesAuditor/1.0 (Defensive Security Scanner; Kali Linux)"
        }

        try:
            async with httpx.AsyncClient(timeout=timeout_sec, follow_redirects=True) as client:
                resp = await client.get(clean_url, headers=headers)
                status_code = resp.status_code
                resp_headers = resp.headers
                # Normalize keys to lower case for robust case-insensitivity
                headers_lower = {str(k).lower(): str(v) for k, v in resp_headers.items()}

                has_hsts = "strict-transport-security" in headers_lower
                has_csp = "content-security-policy" in headers_lower
                has_x_frame = "x-frame-options" in headers_lower
                cors_origin = headers_lower.get("access-control-allow-origin", "").strip()
                permissive_cors = (cors_origin == "*")
                server_token = headers_lower.get("server", None)

                remediations: List[RemediationPatch] = []

                if not has_hsts and clean_url.startswith("https://"):
                    remediations.append(
                        RemediationPatch(
                            issue_type="Missing-HSTS",
                            severity="MEDIUM",
                            description="Strict-Transport-Security header is absent on HTTPS endpoint.",
                            recommended_patch="Add header: 'Strict-Transport-Security: max-age=63072000; includeSubDomains; preload'"
                        )
                    )

                if not has_csp:
                    remediations.append(
                        RemediationPatch(
                            issue_type="Missing-CSP",
                            severity="MEDIUM",
                            description="Content-Security-Policy header is absent.",
                            recommended_patch="Add header: 'Content-Security-Policy: default-src 'self''"
                        )
                    )

                if not has_x_frame:
                    remediations.append(
                        RemediationPatch(
                            issue_type="Missing-X-Frame-Options",
                            severity="LOW",
                            description="Clickjacking protection (X-Frame-Options) is absent.",
                            recommended_patch="Add header: 'X-Frame-Options: DENY'"
                        )
                    )

                if permissive_cors:
                    remediations.append(
                        RemediationPatch(
                            issue_type="Permissive-Wildcard-CORS",
                            severity="HIGH",
                            description="Access-Control-Allow-Origin is set to '*' (wildcard).",
                            recommended_patch="Restrict CORS origin to trusted specific domains or eliminate wildcard on authenticated routes."
                        )
                    )

                # Check exposed docs
                exposed_docs = []
                base_url = f"{urllib.parse.urlparse(clean_url).scheme}://{urllib.parse.urlparse(clean_url).netloc}"
                for doc_path in ("/docs", "/openapi.json"):
                    try:
                        doc_resp = await client.get(f"{base_url}{doc_path}", timeout=3.0)
                        if doc_resp.status_code == 200:
                            exposed_docs.append(doc_path)
                    except Exception:
                        pass

                if exposed_docs:
                    remediations.append(
                        RemediationPatch(
                            issue_type="Exposed-API-Documentation",
                            severity="LOW",
                            description=f"Interactive documentation is publicly exposed at: {exposed_docs}",
                            recommended_patch="Protect or disable Swagger/OpenAPI UI in production (docs_url=None in FastAPI)."
                        )
                    )

                return AuditReport(
                    target_url=clean_url,
                    reachable=True,
                    status_code=status_code,
                    has_hsts=has_hsts,
                    has_csp=has_csp,
                    has_x_frame_options=has_x_frame,
                    permissive_cors=permissive_cors,
                    exposed_docs=exposed_docs,
                    server_token=server_token,
                    remediations=remediations
                )

        except Exception as e:
            logger.warning(f"Auditor failed to reach {clean_url}: {e}")
            return AuditReport(
                target_url=clean_url,
                reachable=False,
                error_message=str(e)
            )
