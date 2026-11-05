import json

from app.scoring import cmd_score, score_job


def test_score_counts_keywords_case_insensitive(tmp_path):
    p = tmp_path / "job.json"
    p.write_text(json.dumps({"description": "Python and SQL work", "keywords": ["python", "sql", "go"]}),
                 encoding="utf-8")
    assert score_job(p) == 2


def test_cmd_score_prints_score_line(tmp_path, capsys):
    p = tmp_path / "job.json"
    p.write_text(json.dumps({"description": "x", "keywords": ["x"]}), encoding="utf-8")
    assert cmd_score([str(p)]) == 0
    assert capsys.readouterr().out.strip() == "score: 1"


def test_cmd_score_missing_file_exits_two(tmp_path, capsys):
    assert cmd_score([str(tmp_path / "nope.json")]) == 2
    assert "no such file" in capsys.readouterr().err.lower()


def test_cmd_score_no_argument_exits_two(capsys):
    assert cmd_score([]) == 2
