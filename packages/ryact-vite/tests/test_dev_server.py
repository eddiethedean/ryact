from __future__ import annotations

from pathlib import Path

from ryact_vite.dev_server import LiveReloadCounter, inject_livereload_into_html


def test_live_reload_counter_only_success_bumps() -> None:
    c = LiveReloadCounter()
    c.on_rebuild(2)
    assert c.version == 0
    c.on_rebuild(0)
    assert c.version == 1


def test_inject_livereload_before_body(tmp_path: Path) -> None:
    p = tmp_path / "index.html"
    p.write_text("<!doctype html><html><body><p>x</p></body></html>", encoding="utf8")
    inject_livereload_into_html(p)
    text = p.read_text(encoding="utf8")
    assert "__ryact_livereload.js" in text
    assert "</body>" in text


def test_inject_livereload_idempotent(tmp_path: Path) -> None:
    p = tmp_path / "index.html"
    p.write_text("<html><body></body></html>", encoding="utf8")
    inject_livereload_into_html(p)
    inject_livereload_into_html(p)
    assert p.read_text(encoding="utf8").count("__ryact_livereload.js") == 1
