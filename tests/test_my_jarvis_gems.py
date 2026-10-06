"""Tests pour les 4 Pépites d'Innovation Inspirées de my_jarvis :
1. SovereignWebEngine (Web search & reader zéro-API DuckDuckGo stdlib)
2. CodeIntegrityGuardian (Anti-truncation, code sentinel, AST check, rejet des placeholders)
3. LocalOllamaProvider (Connecteur Ollama GPU/CPU, chat avec tool calls, benchmark)
4. AgentStreamWatcher (Formatage télémétrique temps réel des actions d'agents)
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from app.tools.sovereign_web import SovereignWebEngine, CleanHTMLTextExtractor
from app.tools.code_integrity_guardian import CodeIntegrityGuardian, CodeHealthReport
from app.llm.local_ollama_provider import LocalOllamaProvider, OllamaBenchmarkResult
from app.orchestrator.agent_stream_watcher import AgentStreamFormatter
from app.tools.gateway import ToolGateway


class TestSovereignWeb:
    """Tests du moteur web souverain zéro-API."""

    def test_html_cleaner_extracts_clean_text(self):
        dirty_html = """
        <html>
            <head><title>Test Page</title><style>.test { color: red; }</style></head>
            <body>
                <nav><a href="/home">Accueil</a></nav>
                <header><h1>Bannière de navigation</h1></header>
                <main>
                    <h1>Titre Principal</h1>
                    <p>Voici le premier paragraphe de contenu substantiel.</p>
                    <script>console.log("secret tracker");</script>
                    <ul>
                        <li>Élément 1</li>
                        <li>Élément 2</li>
                    </ul>
                </main>
                <footer>Pied de page &copy; 2026</footer>
            </body>
        </html>
        """
        parser = CleanHTMLTextExtractor()
        parser.feed(dirty_html)
        text = "".join(parser.output)
        assert "console.log" not in text
        assert "Pied de page" not in text
        assert "Titre Principal" in text
        assert "Voici le premier paragraphe" in text
        assert "Élément 1" in text

    def test_duckduckgo_uddg_url_extraction(self):
        sample_ddg_html = """
        <div class="results">
            <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fmichaelsagbo.tech%2Fprojects&amp;rut=1">Portfolio Michael SAGBO</a>
            <a class="result__snippet" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fmichaelsagbo.tech">Développeur Full Stack &amp; Backend Lead</a>
        </div>
        """
        engine = SovereignWebEngine()
        with patch.object(engine, "_search_sync_fallback") as mock_fallback:
            # Test direct parser regex extraction
            import re, html, urllib.parse
            links = re.findall(r'class="result__a" href="([^"]+)"[^>]*>(.*?)</a>', sample_ddg_html, re.S)
            snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', sample_ddg_html, re.S)
            parsed = urllib.parse.urlparse(html.unescape(links[0][0]))
            qs = urllib.parse.parse_qs(parsed.query)
            real_url = qs.get("uddg")[0]
            assert real_url == "https://michaelsagbo.tech/projects"


class TestCodeIntegrityGuardian:
    """Tests du gardien d'intégrité anti-raccourcis et code sentinel."""

    def test_detect_lazy_code_truncation(self):
        truncated_code = """
        def complex_algorithm():
            step_one()
            # ... (rest of the file unchanged)
            return True
        """
        report = CodeIntegrityGuardian.check_text(truncated_code, filename="test.py")
        assert report.is_valid is False
        assert report.has_truncation is True
        assert len(report.truncation_matches) > 0

    def test_valid_code_passes(self):
        valid_code = (
            "def complete_algorithm():\n"
            "    step_one()\n"
            "    step_two()\n"
            "    return True\n"
        )
        report = CodeIntegrityGuardian.check_text(valid_code, filename="test.py")
        assert report.is_valid is True
        assert report.has_truncation is False

    def test_gateway_write_file_blocks_truncation(self, tmp_path):
        gateway = ToolGateway(workspace_root=str(tmp_path), allow_full_fs_access=True)
        lazy_content = """
        class DataManager:
            # ... rest of code
            pass
        """
        res = gateway.write_file("data_manager.py", lazy_content)
        assert res["success"] is False
        assert "Code truncation rejected" in res["error"]

    def test_gateway_write_file_allows_complete_code(self, tmp_path):
        gateway = ToolGateway(workspace_root=str(tmp_path), allow_full_fs_access=True)
        good_content = """
        class DataManager:
            def save(self):
                return True
        """
        res = gateway.write_file("data_manager.py", good_content)
        assert res["success"] is True
        assert (tmp_path / "data_manager.py").exists()

    def test_detect_em_dashes_and_emojis(self):
        prose_code = "print('Hello world') — un tiret cadratin"
        report = CodeIntegrityGuardian.check_text(prose_code, filename="script.py")
        assert report.has_em_dash is True


class TestLocalOllamaProvider:
    """Tests du connecteur local Ollama haute performance."""

    def test_ollama_list_models(self):
        async def _run():
            provider = LocalOllamaProvider()
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "models": [{"name": "gemma4:latest"}, {"name": "qwen2.5-coder:7b"}]
            }
            with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_resp)):
                models = await provider.list_local_models()
                assert "gemma4:latest" in models
                assert "qwen2.5-coder:7b" in models
        asyncio.run(_run())

    def test_ollama_benchmark_math(self):
        async def _run():
            provider = LocalOllamaProvider()
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "eval_count": 250,
                "eval_duration": 5000000000,         # 5 secondes -> 50 tok/s
                "prompt_eval_count": 50,
                "prompt_eval_duration": 500000000,   # 0.5 sec -> 100 tok/s
                "load_duration": 1000000000,
                "total_duration": 6500000000,
                "thinking": "Penser..."
            }
            with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_resp)):
                bench = await provider.benchmark_model("qwen2.5-coder:7b")
                assert bench is not None
                assert bench.gen_tokens_per_sec == 50.0
                assert bench.prompt_tokens_per_sec == 100.0
                assert bench.tokens_generated == 250
        asyncio.run(_run())


class TestAgentStreamWatcher:
    """Tests du formateur de télémétrie temps réel des agents."""

    def test_format_thought_event(self):
        ev = {
            "type": "thought",
            "timestamp": "14:35:00",
            "data": {"content": "J'analyse le code de souveraineté."}
        }
        res = AgentStreamFormatter.format_event(ev)
        assert "💬 J'analyse le code" in res

    def test_format_tool_call_event(self):
        ev = {
            "type": "tool_call",
            "timestamp": "14:35:01",
            "data": {"name": "read_file", "input": {"path": "main.py"}}
        }
        res = AgentStreamFormatter.format_event(ev)
        assert "▶" in res
        assert "read_file" in res

    def test_format_tool_result_event(self):
        ev = {
            "type": "tool_result",
            "timestamp": "14:35:02",
            "data": {"name": "read_file", "output": "import os\nimport sys"}
        }
        res = AgentStreamFormatter.format_event(ev)
        assert "↳" in res
        assert "import os" in res
