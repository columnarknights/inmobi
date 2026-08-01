#!/usr/bin/env python3
"""One-command teammate setup for the Automated Root-Cause Analyst.

Run from the repo root: `python3 setup_teammate.py`

What it does, fully automated:
  1. Creates implementation/.venv and installs the rca package into it.
  2. Prompts once for the team's ClickHouse Cloud credentials + your own
     Gemini API key (skipped if implementation/.env is already filled in —
     safe to re-run).
  3. Writes librechat/.env with freshly generated secrets (JWT/CREDS keys)
     and the same ClickHouse/Gemini values — this is the #1 cause of
     "JwtStrategy requires a secret" and missing-signup-option errors when
     someone hand-copies .env.example and misses a field.
  4. Starts the LibreChat containers (docker compose).
  5. Starts `rca mcp-serve` and `rca serve` on the host, in the background.
  6. Creates YOUR OWN personal "RCA Follow-up" agent in your LibreChat
     instance (via librechat/create_followup_agent.py) and writes its id
     into implementation/.env — this is the #2 cause of errors ("Agent not
     found" / "Insufficient permissions"): agent ids are specific to one
     LibreChat instance, so everyone needs their own.

Safe to re-run: existing .env files and an already-created agent are reused,
not recreated.
"""

import getpass
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
IMPL = ROOT / "implementation"
LIBRECHAT = ROOT / "librechat"
IS_WINDOWS = os.name == "nt"


def venv_bin(venv_dir: Path, name: str) -> str:
    if IS_WINDOWS:
        return str(venv_dir / "Scripts" / f"{name}.exe")
    return str(venv_dir / "bin" / name)


def run(cmd, cwd=None, **kw):
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    subprocess.run(cmd, cwd=cwd, check=True, **kw)


def prompt(label: str, secret: bool = False, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    reader = getpass.getpass if secret else input
    val = reader(f"  {label}{suffix}: ").strip()
    return val or (default or "")


def read_env(path: Path) -> dict:
    if not path.exists():
        return {}
    values = {}
    for line in path.read_text().splitlines():
        m = re.match(r"^([A-Z_][A-Z0-9_]*)=(.*)$", line)
        if m:
            values[m.group(1)] = m.group(2).strip()
    return values


def patch_env(path: Path, values: dict) -> None:
    text = path.read_text() if path.exists() else ""
    for key, val in values.items():
        pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
        if pattern.search(text):
            text = pattern.sub(f"{key}={val}", text)
        else:
            text += f"\n{key}={val}\n"
    path.write_text(text)


def wait_for(url: str, timeout: int = 60) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(2)
    return False


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def main() -> None:
    print("Automated Root-Cause Analyst — one-command teammate setup\n")

    # --- 1. Python env ---------------------------------------------------
    section("Setting up implementation/.venv")
    venv_dir = IMPL / ".venv"
    if not venv_dir.exists():
        run([sys.executable, "-m", "venv", ".venv"], cwd=IMPL)
    pip = venv_bin(venv_dir, "pip")
    python = venv_bin(venv_dir, "python")
    run([pip, "install", "--quiet", "-e", "."], cwd=IMPL)
    run([pip, "install", "--quiet", "playwright"], cwd=IMPL)
    run([python, "-m", "playwright", "install", "chromium"], cwd=IMPL)

    # --- 2. Credentials (implementation/.env) -----------------------------
    section("Configuring implementation/.env")
    env_path = IMPL / ".env"
    existing = read_env(env_path)
    if existing.get("CLICKHOUSE_HOST") and existing.get("GEMINI_API_KEY"):
        print("  Already configured — reusing existing implementation/.env.")
        creds = existing
    else:
        if not env_path.exists():
            shutil.copy(IMPL / ".env.example", env_path)
        print("  Enter the team's ClickHouse Cloud credentials and your own Gemini API key.")
        creds = {
            "CLICKHOUSE_HOST": prompt("CLICKHOUSE_HOST", default=existing.get("CLICKHOUSE_HOST")),
            "CLICKHOUSE_PORT": prompt("CLICKHOUSE_PORT", default=existing.get("CLICKHOUSE_PORT", "8443")),
            "CLICKHOUSE_USER": prompt("CLICKHOUSE_USER", default=existing.get("CLICKHOUSE_USER", "default")),
            "CLICKHOUSE_PASSWORD": prompt("CLICKHOUSE_PASSWORD", secret=True) or existing.get("CLICKHOUSE_PASSWORD", ""),
            "CLICKHOUSE_DATABASE": prompt("CLICKHOUSE_DATABASE", default=existing.get("CLICKHOUSE_DATABASE")),
            "GEMINI_API_KEY": prompt("GEMINI_API_KEY", secret=True) or existing.get("GEMINI_API_KEY", ""),
        }
        creds["CLICKHOUSE_SECURE"] = "true"
        patch_env(env_path, creds)
        print("  Wrote implementation/.env")

    # --- 3. librechat/.env -------------------------------------------------
    section("Configuring librechat/.env")
    lc_env = LIBRECHAT / ".env"
    lc_existing = read_env(lc_env)
    if lc_existing.get("JWT_SECRET") and lc_existing.get("CLICKHOUSE_HOST"):
        print("  Already configured — reusing existing librechat/.env.")
    else:
        if not lc_env.exists():
            shutil.copy(LIBRECHAT / ".env.example", lc_env)
        patch_env(lc_env, {
            "JWT_SECRET": secrets.token_hex(32),
            "JWT_REFRESH_SECRET": secrets.token_hex(32),
            "CREDS_KEY": secrets.token_hex(32),
            "CREDS_IV": secrets.token_hex(16),
            "ALLOW_EMAIL_LOGIN": "true",
            "ALLOW_REGISTRATION": "true",
            "GEMINI_API_KEY": creds["GEMINI_API_KEY"],
            "GOOGLE_KEY": creds["GEMINI_API_KEY"],
            "CLICKHOUSE_HOST": creds["CLICKHOUSE_HOST"],
            "CLICKHOUSE_PORT": creds.get("CLICKHOUSE_PORT", "8443"),
            "CLICKHOUSE_USER": creds["CLICKHOUSE_USER"],
            "CLICKHOUSE_PASSWORD": creds["CLICKHOUSE_PASSWORD"],
            "CLICKHOUSE_DATABASE": creds["CLICKHOUSE_DATABASE"],
            "CLICKHOUSE_SECURE": "true",
        })
        print("  Wrote librechat/.env with freshly generated secrets")

    # --- 4. LibreChat containers -------------------------------------------
    section("Starting LibreChat (docker compose)")
    run(["docker", "compose", "up", "-d"], cwd=LIBRECHAT)
    print("  Waiting for LibreChat to respond...")
    if not wait_for("http://localhost:3080/login", timeout=90):
        print("  WARNING: LibreChat didn't respond within 90s.")
        print("  Check: cd librechat && docker compose logs librechat")

    # --- 5. Host-side servers -----------------------------------------------
    section("Starting rca mcp-serve and rca serve")
    logs_dir = IMPL / ".setup_logs"
    logs_dir.mkdir(exist_ok=True)
    rca = venv_bin(venv_dir, "rca")

    def start_background(args, log_name):
        log_path = logs_dir / log_name
        return subprocess.Popen(
            [rca, *args], cwd=IMPL,
            stdout=open(log_path, "w"), stderr=subprocess.STDOUT,
        )

    if not wait_for("http://127.0.0.1:8001/mcp", timeout=1):
        start_background(["mcp-serve"], "mcp_serve.log")
    else:
        print("  rca mcp-serve already running on :8001, leaving it as-is.")
    if not wait_for("http://127.0.0.1:8000/api/meta", timeout=1):
        start_background(["serve"], "web_serve.log")
    else:
        print("  rca serve already running on :8000, leaving it as-is.")

    if not wait_for("http://127.0.0.1:8001/mcp", timeout=30):
        print("  WARNING: MCP server (port 8001) didn't come up — see implementation/.setup_logs/mcp_serve.log")
    if not wait_for("http://127.0.0.1:8000/api/meta", timeout=30):
        print("  WARNING: dashboard (port 8000) didn't come up — see implementation/.setup_logs/web_serve.log")

    # --- 6. Personal "RCA Follow-up" agent ----------------------------------
    section("Creating your personal 'RCA Follow-up' agent")
    if existing.get("LIBRECHAT_FOLLOWUP_AGENT_ID"):
        print(f"  Already set (LIBRECHAT_FOLLOWUP_AGENT_ID={existing['LIBRECHAT_FOLLOWUP_AGENT_ID']}), skipping.")
        print("  Delete that line from implementation/.env and re-run this script to recreate it.")
    else:
        result = subprocess.run(
            [python, "create_followup_agent.py"], cwd=LIBRECHAT,
            capture_output=True, text=True,
        )
        print(result.stdout)
        m = re.search(r"\(id=(\S+)\)", result.stdout)
        if result.returncode == 0 and m:
            agent_id = m.group(1)
            patch_env(env_path, {
                "LIBRECHAT_BASE_URL": "http://localhost:3080",
                "LIBRECHAT_FOLLOWUP_AGENT_ID": agent_id,
            })
            print(f"  Wrote LIBRECHAT_FOLLOWUP_AGENT_ID={agent_id} to implementation/.env")
            print("  Restarting rca serve so the dashboard picks it up...")
            subprocess.run(["pkill", "-f", f"{rca} serve"], check=False)
            time.sleep(1)
            start_background(["serve"], "web_serve.log")
            wait_for("http://127.0.0.1:8000/api/meta", timeout=15)
        else:
            print(result.stderr)
            print(
                "  Automatic agent creation failed. Follow the ~2-minute manual\n"
                "  steps in implementation/README.md under \"Setting it up\", then\n"
                "  add LIBRECHAT_FOLLOWUP_AGENT_ID=<the id> to implementation/.env\n"
                "  yourself and restart `rca serve`."
            )

    section("Done")
    print("  Dashboard:  http://127.0.0.1:8000")
    print("  LibreChat:  http://localhost:3080  (sign up with any email/password)")
    print("  Logs:       implementation/.setup_logs/")


if __name__ == "__main__":
    main()
