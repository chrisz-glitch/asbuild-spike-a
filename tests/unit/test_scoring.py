import json

from app.scoring import score_command, score_job


def test_score_job_counts_keywords_case_insensitive():
    job = {"description": "Python and llm work", "keywords": ["python", "LLM", "rust"]}
    assert score_job(job) == 2


def test_score_job_missing_fields_is_zero():
    assert score_job({}) == 0


def test_score_command_prints_score(tmp_path, capsys):
    p = tmp_path / "job.json"
    p.write_text(json.dumps({"description": "AI work", "keywords": ["AI"]}), encoding="utf-8")
    assert score_command([str(p)]) == 0
    assert capsys.readouterr().out.strip().splitlines()[-1] == "score: 1"


def test_score_command_missing_file_exits_two(tmp_path, capsys):
    assert score_command([str(tmp_path / "nope.json")]) == 2
    assert "no such file" in capsys.readouterr().err


def test_score_command_no_argument_is_usage_error(capsys):
    assert score_command([]) == 2
    assert "usage" in capsys.readouterr().err
