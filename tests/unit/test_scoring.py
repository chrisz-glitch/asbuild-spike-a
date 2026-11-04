"""The builder's own unit tests for S1 (free to change; they are not the proof)."""
import json

import pytest

from app.scoring import score_job


def test_counts_keywords_found_in_description(tmp_path):
    p = tmp_path / "job.json"
    p.write_text(json.dumps({"description": "AI governance for banks", "keywords": ["AI", "banks", "LLM"]}),
                 encoding="utf-8")
    assert score_job(str(p)) == 2


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        score_job(str(tmp_path / "nope.json"))
