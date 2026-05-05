"""Type stubs for the Rolldown PyO3 extension (built by maturin)."""

def bundle_roll(
    entry: str,
    out_dir: str,
    cwd: str,
    format: str,
    minify: bool,
    verbose: bool,
    defines: dict[str, str] | None,
) -> None: ...
