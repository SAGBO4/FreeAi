"""Tests for Sovereign Zero-API Web Intelligence and Code Integrity Guardian."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from app.security.code_integrity_guardian import (
    CodeIntegrityGuardian,
    FORBIDDEN_EMOJI_REGEX,
    PLACEHOLDER_REGEX,
)
from app.tools.sovereign_web import SovereignWebEngine, TextContentExtractor


def test_text_content_extractor() -> None:
    """Verifies that TextContentExtractor strips script/style and extracts clean text."""
    html_sample = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title><style>body { color: red; }</style></head>
    <body>
        <nav><a href="/">Home</a></nav>
        <h1>Article Title</h1>
        <p>This is the first paragraph with <b>bold</b> text.</p>
        <script>console.log("secret");</script>
        <footer>Footer content to ignore</footer>
    </body>
    </html>
    """
    extractor = TextContentExtractor()
    extractor.feed(html_sample)
    clean_text = extractor.get_text()

    assert "Article Title" in clean_text
    assert "This is the first paragraph with bold text." in clean_text
    assert "body { color: red; }" not in clean_text
    assert "console.log" not in clean_text
    assert "Footer content" not in clean_text


def test_sovereign_web_search_parsing() -> None:
    """Verifies DuckDuckGo HTML result parsing without network calls."""
    mock_html = """
    <div class="result results_links">
      <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fdoc&rut=1">Python Documentation</a>
      <a class="result__snippet">Official Python documentation, tutorials, and libraries.</a>
    </div>
    """
    engine = SovereignWebEngine()
    with patch.object(engine, "_fetch_html", return_value=mock_html):
        results = engine.search("python documentation", max_results=5)

    assert len(results) == 1
    assert results[0]["title"] == "Python Documentation"
    assert results[0]["url"] == "https://example.com/doc"
    assert "Official Python documentation" in results[0]["snippet"]


def test_placeholder_regex_detection() -> None:
    """Verifies detection of lazy AI truncation placeholders."""
    samples_failing = [
        "# ... (rest of the code)",
        "// ... (remaining)",
        "/* ... */",
        "# ... reste du fichier",
        "# ... (unchanged)",
    ]
    for sample in samples_failing:
        assert PLACEHOLDER_REGEX.search(sample) is not None, f"Failed to match: {sample}"

    sample_clean = "def foo():\n    return 42\n"
    assert PLACEHOLDER_REGEX.search(sample_clean) is None


def test_code_integrity_guardian_scans_file() -> None:
    """Verifies that CodeIntegrityGuardian flags truncation placeholders in files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        dirty_file = tmp_path / "bad_code.py"
        dirty_file.write_text(
            "def calculate():\n    x = 10\n    # ... (rest of the code)\n    return x\n",
            encoding="utf-8",
        )

        guardian = CodeIntegrityGuardian(root_dir=tmp_path)
        findings = guardian.scan_file(dirty_file)

        assert len(findings) >= 1
        assert any(f.defect_type == "TRUNCATION_PLACEHOLDER" for f in findings)


def test_code_integrity_guardian_clean_file() -> None:
    """Verifies that clean code produces zero defects."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        clean_file = tmp_path / "clean_code.py"
        clean_file.write_text(
            "def calculate() -> int:\n    x = 10\n    y = 20\n    return x + y\n",
            encoding="utf-8",
        )

        guardian = CodeIntegrityGuardian(root_dir=tmp_path)
        findings = guardian.scan_file(clean_file)

        assert len(findings) == 0


def test_sanitize_file_emojis() -> None:
    """Verifies automatic in-place emoji removal."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        dirty_file = tmp_path / "emoji_file.py"
        dirty_file.write_text('msg = "Hello 🚀 world 💥"\n', encoding="utf-8")

        guardian = CodeIntegrityGuardian(root_dir=tmp_path)
        modified = guardian.sanitize_file_emojis(dirty_file)

        assert modified is True
        cleaned_content = dirty_file.read_text(encoding="utf-8")
        assert "🚀" not in cleaned_content
        assert "💥" not in cleaned_content
        assert "Hello world" in cleaned_content
