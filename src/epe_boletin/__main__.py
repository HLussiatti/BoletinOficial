import sys

from epe_boletin.cli import main

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

raise SystemExit(main())
