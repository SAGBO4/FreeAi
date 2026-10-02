import os
import shutil
import tempfile
import pytest
from app.tools.video_engine import ProgrammaticVideoEngine


def test_video_engine_scaffold():
    engine = ProgrammaticVideoEngine()
    with tempfile.TemporaryDirectory() as tmp_dir:
        res = engine.generate_remotion_scaffold(
            output_dir=tmp_dir,
            project_name="TestProject",
            title="Test Video Title",
            features=["Feature 1", "Feature 2"]
        )
        assert res["success"] is True
        assert os.path.exists(os.path.join(tmp_dir, "package.json"))
        assert os.path.exists(os.path.join(tmp_dir, "remotion.config.ts"))
        assert os.path.exists(os.path.join(tmp_dir, "src", "Root.tsx"))
        assert os.path.exists(os.path.join(tmp_dir, "src", "MainVideo.tsx"))


def test_video_engine_in_memory_render():
    engine = ProgrammaticVideoEngine()
    res = engine.render_cinematic_teaser_in_ram(
        title="Test FreeAI Teaser",
        subtitle="In-Memory Validation",
        duration_sec=2
    )
    assert res["success"] is True
    assert res["filename"].endswith(".mp4")
    assert res["size_kb"] > 10
    assert len(res["data"]) > 0
