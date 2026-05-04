from ._version_check import check_versions as _check_versions

_check_versions()

from .interop_runner import DomInteropRunner  # noqa: E402
from .props import cx, on, style, style_dict  # noqa: E402
from .root import create_root, hydrate_root  # noqa: E402
from .server import render_to_pipeable_stream, render_to_string  # noqa: E402

__version__ = "0.1.0"

__all__ = [
    "create_root",
    "hydrate_root",
    "render_to_pipeable_stream",
    "render_to_string",
    "DomInteropRunner",
    "cx",
    "on",
    "style",
    "style_dict",
    "__version__",
]
