import pytest
from src.normalizers import normalize_date, normalize_phone, normalize_skill, normalize_country
from src.merger import Merger
from src.projector import Projector
from src.models import CanonicalProfile, Skill, Experience, Location


# ── Normalizers ──────────────────────────────────────────────────────────────

def test_normalize_date_iso():
    assert normalize_date("2020-05-15T00:00:00Z") == "2020-05"

def test_normalize_date_year_only():
    assert normalize_date("2021") == "2021"

def test_normalize_date_none():
    assert normalize_date(None) is None

def test_normalize_date_garbage():
    result = normalize_date("not-a-date")
    assert result is None or isinstance(result, str)

def test_normalize_phone_us_short():
    assert normalize_phone("555-0100") == "+15550100"

def test_normalize_phone_uk():
    assert normalize_phone("+44 20 7946 0958") == "+442079460958"

def test_normalize_phone_india():
    assert normalize_phone("+91 9124286319") == "+919124286319"

def test_normalize_phone_none():
    assert normalize_phone(None) is None

def test_normalize_skill_alias():
    assert normalize_skill(" js ") == "javascript"
    assert normalize_skill("React") == "react.js"
    assert normalize_skill("py") == "python"
    assert normalize_skill("golang") == "go"
    assert normalize_skill("sklearn") == "scikit-learn"

def test_normalize_skill_none():
    assert normalize_skill(None) is None

def test_normalize_country():
    assert normalize_country("United States") == "US"
    assert normalize_country("india") == "IN"
    assert normalize_country("UK") == "GB"
    assert normalize_country("IN") == "IN"


# ── Merger: Identity Resolution ───────────────────────────────────────────────

def test_merger_same_email_deduplicates():
    """Two profiles with the same email must merge into one."""
    p1 = CanonicalProfile(candidate_id="a", full_name="John Doe", emails=["john@example.com"])
    p2 = CanonicalProfile(candidate_id="b", full_name="John D.", emails=["john@example.com"])
    result = Merger().merge([("ATS", p1), ("GitHub", p2)])
    assert len(result) == 1
    assert result[0].full_name == "John D."  # GitHub has higher confidence

def test_merger_fuzzy_name_employer_deduplicates():
    """Same first name + employer should merge even with different emails."""
    p1 = CanonicalProfile(candidate_id="a", full_name="John Doe",
                          emails=["john.work@corp.com"],
                          experience=[Experience(company="TechCorp", title="Engineer")])
    p2 = CanonicalProfile(candidate_id="b", full_name="John Doe",
                          emails=["john.personal@gmail.com"],
                          experience=[Experience(company="TechCorp", title="Engineer")])
    result = Merger().merge([("RecruiterCSV", p1), ("ATS", p2)])
    assert len(result) == 1
    assert len(result[0].emails) == 2

def test_merger_different_people_not_merged():
    """Two people with different emails and names must stay separate."""
    p1 = CanonicalProfile(candidate_id="a", full_name="Alice", emails=["alice@x.com"])
    p2 = CanonicalProfile(candidate_id="b", full_name="Bob", emails=["bob@x.com"])
    result = Merger().merge([("ATS", p1), ("ATS", p2)])
    assert len(result) == 2

def test_merger_overall_confidence_computed():
    p = CanonicalProfile(candidate_id="a", full_name="Test User", emails=["t@x.com"])
    result = Merger().merge([("ATS", p)])
    assert result[0].overall_confidence is not None
    assert 0 < result[0].overall_confidence <= 1.0

def test_merger_years_experience():
    p = CanonicalProfile(candidate_id="a", full_name="Dev",
                         experience=[Experience(company="Corp", title="SWE", start="2022-01", end="2024-01")])
    result = Merger().merge([("ATS", p)])
    assert result[0].years_experience is not None
    assert result[0].years_experience > 1.5

def test_merger_skills_union_across_sources():
    p1 = CanonicalProfile(candidate_id="a", full_name="Dev", emails=["dev@x.com"],
                          skills=[Skill(name="python", confidence=0.7, sources=["ATS"])])
    p2 = CanonicalProfile(candidate_id="b", full_name="Dev", emails=["dev@x.com"],
                          skills=[Skill(name="python", confidence=0.9, sources=["GitHub"]),
                                  Skill(name="react.js", confidence=0.9, sources=["GitHub"])])
    result = Merger().merge([("ATS", p1), ("GitHub", p2)])
    assert len(result) == 1
    skill_map = {s.name: s for s in result[0].skills}
    assert "python" in skill_map
    assert skill_map["python"].confidence == 0.9
    assert "ATS" in skill_map["python"].sources
    assert "GitHub" in skill_map["python"].sources
    assert "react.js" in skill_map


# ── Projector ─────────────────────────────────────────────────────────────────

def test_projector_on_missing_omit():
    """Fields with null values should be omitted when on_missing=omit."""
    config = {"fields": [{"path": "full_name", "required": False},
                         {"path": "phone", "from": "phones[0]"}],
              "on_missing": "omit", "include_confidence": False}
    p = CanonicalProfile(candidate_id="x", full_name="Test")
    result = Projector(config).project([p])
    assert len(result) == 1
    assert "phone" not in result[0]
    assert result[0]["full_name"] == "Test"

def test_projector_on_missing_error_raises():
    """Required missing field with on_missing=error must skip the profile."""
    config = {"fields": [{"path": "full_name", "required": True}],
              "on_missing": "error", "include_confidence": False}
    p = CanonicalProfile(candidate_id="x")  # no full_name
    result = Projector(config).project([p])
    assert result == []  # skipped, not crashed

def test_projector_skills_wildcard():
    """skills[].name path must return a flat list of skill name strings."""
    config = {"fields": [{"path": "skills", "from": "skills[].name", "normalize": "canonical"}],
              "on_missing": "null", "include_confidence": False}
    p = CanonicalProfile(candidate_id="x",
                         skills=[Skill(name="Python", confidence=0.9, sources=["ATS"]),
                                 Skill(name="JS", confidence=0.8, sources=["GitHub"])])
    result = Projector(config).project([p])
    assert len(result) == 1
    assert "python" in result[0]["skills"]
    assert "javascript" in result[0]["skills"]

def test_projector_field_rename():
    """'from' key remaps a canonical path to a different output field name."""
    config = {"fields": [{"path": "primary_email", "from": "emails[0]"}],
              "on_missing": "null", "include_confidence": False}
    p = CanonicalProfile(candidate_id="x", emails=["test@x.com"])
    result = Projector(config).project([p])
    assert result[0]["primary_email"] == "test@x.com"


# ── End-to-end pipeline ───────────────────────────────────────────────────────

def test_pipeline_end_to_end_merges_john_doe():
    """John Doe across ATS + GitHub (same email) must produce a single merged profile."""
    from src.pipeline import Pipeline
    p = Pipeline("mock_data", "mock_data/config.json")
    results = p.run()
    names = [r.get("full_name") for r in results]
    john_entries = [n for n in names if n and "John" in n and "Doe" in n]
    assert len(john_entries) == 1, f"Expected 1 John Doe, got {len(john_entries)}: {names}"

def test_pipeline_output_has_overall_confidence():
    from src.pipeline import Pipeline
    results = Pipeline("mock_data", "mock_data/config.json").run()
    for r in results:
        assert "overall_confidence" in r

def test_pipeline_graceful_on_missing_source():
    """Pipeline must not crash when data directory is empty."""
    import os, json, tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = os.path.join(tmpdir, "config.json")
        with open(config_path, "w") as f:
            json.dump({"fields": [{"path": "full_name"}], "on_missing": "null", "include_confidence": False}, f)
        from src.pipeline import Pipeline
        result = Pipeline(tmpdir, config_path).run()
        assert result == []
