from __future__ import annotations

from ryact import create_element


def page() -> object:
    """Root element tree — rendered with ``ryact_dom.render_to_string`` in ``serve.py``."""
    return create_element(
        "main",
        {
            "className": "shell",
            "children": (
                create_element(
                    "header",
                    {
                        "key": "hero",
                        "children": (
                            create_element("h1", {"key": "title"}, "Full Python Ryact"),
                            create_element(
                                "p",
                                {"key": "lead", "className": "lead"},
                                "Ryact + ryact-dom only — no TS/JS bundle. CSS lives in static/",
                            ),
                        ),
                    },
                ),
                create_element(
                    "section",
                    {
                        "key": "sec-render",
                        "className": "card",
                        "children": (
                            create_element("h2", {"key": "h2a"}, "Server render"),
                            create_element(
                                "p",
                                {"key": "pa"},
                                "This HTML came from render_to_string(create_element(...)). "
                                "Swap serve.py to hydrate with create_root if you add client state later.",
                            ),
                        ),
                    },
                ),
                create_element(
                    "section",
                    {
                        "key": "sec-build",
                        "className": "card",
                        "children": (
                            create_element("h2", {"key": "h2b"}, "Build"),
                            create_element(
                                "p",
                                {"key": "pb"},
                                "Run ryact-build static to copy static/ into dist/. "
                                "Use ryact-dev python to watch .py / .css and restart the server.",
                            ),
                        ),
                    },
                ),
            ),
        },
    )
