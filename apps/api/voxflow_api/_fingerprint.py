"""A content hash of the Python source actually loaded at runtime.

Why this exists
---------------
`docker compose up -d --force-recreate` recreates the *container* from the
*existing image*. It does not rebuild. So you can `git pull`, recreate, and
still be running week-old code — with no error and no warning anywhere.

That failure mode is invisible: the deploy command succeeds, the container is
healthy, and the bug you just fixed is still there. Diagnosing it costs hours
because every hypothesis you form is about the bug rather than about the
staleness.

`preflight.sh` prints the fingerprint of your working tree and `selftest`
prints the fingerprint of the running image. If they differ, the image is
stale and nothing else in either report can be trusted. One glance, no guessing.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def code_fingerprint(root: Path | None = None) -> str:
    """12-hex digest over every .py file in the package.

    Path-independent (relative paths only) so the same source tree hashes
    identically on the host and inside the container, where it lives at a
    different absolute path.
    """
    root = root or Path(__file__).resolve().parent
    h = hashlib.sha256()
    for p in sorted(root.rglob("*.py"), key=lambda p: p.relative_to(root).as_posix()):
        if "__pycache__" in p.parts:
            continue
        h.update(p.relative_to(root).as_posix().encode())
        h.update(p.read_bytes())
    return h.hexdigest()[:12]


if __name__ == "__main__":
    print(code_fingerprint())
