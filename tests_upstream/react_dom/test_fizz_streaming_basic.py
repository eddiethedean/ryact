from __future__ import annotations

from ryact import create_element
from ryact_dom.server import render_to_pipeable_stream


def test_pipeable_stream_calls_callbacks_and_writes_html() -> None:
    calls: list[str] = []
    chunks: list[str] = []

    def on_shell_ready() -> None:
        calls.append("shell")

    def on_all_ready() -> None:
        calls.append("all")

    stream = render_to_pipeable_stream(
        create_element("div", {"id": "x"}, "hi"),
        on_shell_ready=on_shell_ready,
        on_all_ready=on_all_ready,
    )

    stream.pipe(chunks.append)

    assert calls == ["shell", "all"]
    assert "".join(chunks) == '<div id="x">hi</div>'
