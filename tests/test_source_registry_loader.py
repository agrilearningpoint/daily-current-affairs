import importlib.util
from pathlib import Path

from config import sources
from config.sources import get_rss_feed_urls


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_registry_returns_unique_feed_urls_by_job_type():
    daily_urls = get_rss_feed_urls("daily")
    weekly_urls = get_rss_feed_urls("weekly")
    weekly_only_url = next(
        source["rss"]
        for source in sources.LEVEL_1_AGRI
        if source["frequency"] == "weekly"
    )

    assert daily_urls
    assert len(daily_urls) == len(set(daily_urls))
    assert weekly_only_url not in daily_urls
    assert weekly_only_url in weekly_urls


def test_pipeline_source_fetch_uses_registry_by_default(tmp_path, monkeypatch):
    (tmp_path / "logs").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ALP_JOB_TYPE", raising=False)

    module = _load_module(
        REPO_ROOT / "pipeline" / "01_source_fetch.py",
        "source_fetch_under_test",
    )

    assert module.load_sources() == get_rss_feed_urls("daily")


def test_news_agent_reads_rss_fields_from_python_registry():
    module = _load_module(
        REPO_ROOT / "agents" / "03_news_collection.py",
        "news_collection_under_test",
    )

    assert module._extract_sources_from_python(
        REPO_ROOT / "config" / "sources.py"
    ) == get_rss_feed_urls("daily")
