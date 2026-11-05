"""Read-only multi-context runner with isolated reports and one standalone HTML."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import uuid
from validator import __version__
from validator.cli import positive
from validator.version import Version
from validator.consolidated_report import consolidate


def main(argv=None):
    parser = argparse.ArgumentParser(description="Analiza varios contextos y genera un HTML consolidado.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--target", "--target-version", required=True)
    parser.add_argument("--context", action="append", help="Repetible; por defecto todos los contextos de kubectl")
    parser.add_argument("--output", type=Path, default=Path("reports"))
    parser.add_argument("--context-timeout", type=positive, default=1800, help="Timeout total por contexto, segundos")
    args, forwarded = parser.parse_known_args(argv)
    # Explicit allowlist of main.py options: callers cannot redirect or reuse reports.
    allowed = {"--include-instances": 0, "--verbose": 0, "--verify-sources": 0,
               "--platform-catalog": 1, "--support-catalog": 1, "--platform-limit": 1, "--detectors-path": 1, "--readiness-config": 1,
               "--rules-path": 1, "--coverage-path": 1, "--operator-catalog": 1,
               "--timeout": 1, "--pluto-timeout": 1, "--max-queries": 1, "--page-size": 1,
               "--max-pages": 1, "--max-instances": 1, "--fail-on": 1}
    try:
        target = str(Version.parse(args.target))
        index = 0
        while index < len(forwarded):
            flag = forwarded[index]
            if flag not in allowed or index + allowed[flag] >= len(forwarded):
                raise ValueError("Opción adicional inválida; consulte batch.py --help y README.")
            index += 1 + allowed[flag]
        contexts = args.context
        if not contexts:
            result = subprocess.run(["kubectl", "config", "get-contexts", "-o", "name"], capture_output=True,
                                    text=True, encoding="utf-8", errors="replace", timeout=30, check=False, shell=False)
            if result.returncode:
                raise ValueError("No se pudieron enumerar los contextos de kubectl.")
            contexts = result.stdout.splitlines()
        contexts = list(dict.fromkeys(c for c in contexts if c.strip()))
        if not contexts:
            raise ValueError("No hay contextos para analizar.")
        run_dir = args.output / ("run-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
        run_dir.mkdir(parents=True)
        entries = []
        for index, context in enumerate(contexts, 1):
            slug = re.sub(r"[^A-Za-z0-9_-]", "_", context)[:60] or "context"
            directory = run_dir / f"{index:03d}-{slug}-{hashlib.sha256(context.encode()).hexdigest()[:8]}"
            directory.mkdir()
            print(f"[{index}/{len(contexts)}] {context}", flush=True)
            command = [sys.executable, str(Path(__file__).resolve().with_name("main.py")), "--context", context,
                       "--target", target, "--output", str(directory.resolve()), "--format", "all"] + forwarded
            try:
                env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
                result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace", env=env,
                    timeout=args.context_timeout, check=False, shell=False)
                (directory / "console.txt").write_text(getattr(result, "stdout", "") or "", encoding="utf-8", newline="\n")
                code = result.returncode
            except subprocess.TimeoutExpired as exc:
                partial = exc.stdout or ""
                if isinstance(partial, bytes):
                    partial = partial.decode("utf-8", errors="replace")
                (directory / "console.txt").write_text(partial + "\nTimeout del contexto; evaluación incompleta.\n", encoding="utf-8", newline="\n")
                code = 124
            except OSError:
                code = 2
            entries.append({"context": context, "exit_code": code, "target": target,
                            "report_path": str(directory / "report.json")})
            print(f"  Exit code: {code} · {directory}", flush=True)
        state = consolidate(entries, run_dir / "consolidated.html")
        # Portable index for traceability; paths are relative to this run directory.
        manifest = [e | {"report_path": str(Path(e["report_path"]).relative_to(run_dir))} for e in entries]
        (run_dir / "contexts.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
        print(f"Consolidado: {(run_dir / 'consolidated.html').resolve()} · {state}")
        return 2 if state == "ERROR" else 1 if any(e["exit_code"] == 1 for e in entries) else 0
    except (ValueError, OSError, subprocess.TimeoutExpired):
        print("ERROR: Revise argumentos, disponibilidad de kubectl y permisos de lectura/escritura.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
