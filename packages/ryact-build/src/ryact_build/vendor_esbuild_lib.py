"""
Download official @esbuild/* npm tarballs and extract the platform binary.

Used by ``scripts/vendor_esbuild.py`` and :file:`hatch_build.py` at wheel build time.
Version must stay aligned with ``ESBUILD_VENDOR_VERSION``.
"""

from __future__ import annotations

import io
import os
import platform
import stat
import sys
import tarfile
import urllib.request
from pathlib import Path

# Pin to the esbuild release shipped in npm optional-deps (keep in sync with repo root package.json).
ESBUILD_VENDOR_VERSION = "0.25.12"


def npm_esbuild_package_name() -> str:
    """Return the scoped npm package name for this machine (e.g. linux-x64)."""
    sys_plat = sys.platform
    machine = platform.machine().lower()
    if sys_plat == "darwin":
        if machine in ("arm64", "aarch64"):
            return "darwin-arm64"
        return "darwin-x64"
    if sys_plat == "linux":
        if machine in ("aarch64", "arm64"):
            return "linux-arm64"
        if machine in ("armv7l", "armv8l"):
            return "linux-arm"
        if machine == "riscv64":
            return "linux-riscv64"
        return "linux-x64"
    if sys_plat == "win32":
        if machine in ("arm64", "aarch64"):
            return "win32-arm64"
        return "win32-x64"
    raise OSError(f"unsupported platform for bundled esbuild: {sys_plat} {machine}")


def npm_tarball_url(package_suffix: str, version: str = ESBUILD_VENDOR_VERSION) -> str:
    pkg = f"@esbuild/{package_suffix}"
    # registry.npmjs.org expects scoped names as @scope%2Fname for tarball path segment
    encoded = pkg.replace("/", "%2F")
    return f"https://registry.npmjs.org/{encoded}/-/{package_suffix}-{version}.tgz"


def extract_esbuild_binary_from_tgz(data: bytes, *, dest_dir: Path, package_suffix: str) -> Path:
    """Extract ``esbuild`` or ``esbuild.exe`` from an npm ``.tgz`` into ``dest_dir``."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    is_win = package_suffix.startswith("win32")
    inner_name = "esbuild.exe" if is_win else "esbuild"

    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
        member_path = f"package/bin/{inner_name}"
        try:
            member = tf.getmember(member_path)
        except KeyError as e:
            raise RuntimeError(f"missing {member_path} in esbuild tarball") from e
        fileobj = tf.extractfile(member)
        if fileobj is None:
            raise RuntimeError(f"cannot read {member_path} from esbuild tarball")
        dest = dest_dir / inner_name
        dest.write_bytes(fileobj.read())
        if not is_win:
            mode = dest.stat().st_mode
            dest.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return dest


def download_vendor_binary(dest_dir: Path, version: str = ESBUILD_VENDOR_VERSION) -> Path:
    """Download the npm optional-deps package for this OS/arch and extract the binary."""
    suffix = npm_esbuild_package_name()
    url = npm_tarball_url(suffix, version)
    req = urllib.request.Request(url, headers={"User-Agent": "ryact-build-vendor-esbuild"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    return extract_esbuild_binary_from_tgz(data, dest_dir=dest_dir, package_suffix=suffix)


def write_notice(dest_dir: Path, version: str = ESBUILD_VENDOR_VERSION) -> None:
    notice = dest_dir / "ESBUILD_NOTICE.txt"
    notice.write_text(
        "This directory may contain the esbuild executable, vendored from:\n"
        f"  https://www.npmjs.com/package/esbuild version {version}\n"
        "esbuild is copyright Evan Wallace and MIT-licensed:\n"
        "  https://github.com/evanw/esbuild/blob/main/LICENSE.md\n",
        encoding="utf8",
    )
