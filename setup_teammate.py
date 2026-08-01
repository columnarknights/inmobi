#!/usr/bin/env python3
"""One-command teammate setup for the Automated Root-Cause Analyst.

Run from the repo root: `python3 setup_teammate.py`

What it does, fully automated:
  1. Creates implementation/.venv (only needed for the one-off browser
     automation in step 6 below -- the dashboard/MCP server themselves run in
     Docker now, not on the host).
  2. Prompts once for the team's ClickHouse Cloud credentials + your own
     Gemini API key (skipped if implementation/.env is already filled in --
     safe to re-run).
  3. Writes librechat/.env with freshly generated secrets (JWT/CREDS keys)
     and the same ClickHouse/Gemini values -- this is the #1 cause of
     "JwtStrategy requires a secret" and missing-signup-option errors when
     someone hand-copies .env.example and misses a field.
  4. `docker compose up -d --build --wait` from the repo root -- brings up
     LibreChat + its database + the ClickHouse MCP server + this project's
     own dashboard + MCP server, all from ONE command instead of three
     separate consoles, and waits until every service's healthcheck passes.
  5. Creates YOUR OWN personal "RCA Follow-up" agent in your LibreChat
     instance (via librechat/create_followup_agent.py) and writes its id
     into implementation/.env, then restarts the rca-dashboard container so
     it picks up the new value -- this is the #2 cause of errors ("Agent not
     found" / "Insufficient permissions"): agent ids are specific to one
     LibreChat instance, so everyone needs their own.

Safe to re-run: existing .env files, an already-created agent, and already-
built images are all reused, not recreated.
"""

import getpass
import os
import re
import secrets
import shutil
import subprocess
import sys
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


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def main() -> None:
    print("Automated Root-Cause Analyst — one-command teammate setup\n")

    # --- 1. Python env (only needed for the Playwright agent-creation step) ---
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

    # --- 4. Everything else: one docker compose, from the repo root --------
    section("Starting the stack (docker compose up -d --build --wait)")
    print("  This brings up LibreChat, its database, the ClickHouse MCP server,")
    print("  and this project's own dashboard + MCP server -- one command,")
    print("  no separate consoles. May take a minute the first time (image build).")
    try:
        run(["docker", "compose", "up", "-d", "--build", "--wait"], cwd=ROOT)
    except subprocess.CalledProcessError:
        print("  WARNING: not every service reported healthy in time.")
        print("  Check: docker compose ps   /   docker compose logs -f")

    # --- 5. Personal "RCA Follow-up" agent ----------------------------------
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
            print("  Restarting rca-dashboard so it picks up the new agent id...")
            run(["docker", "compose", "up", "-d", "--wait", "rca-dashboard"], cwd=ROOT)
        else:
            print(result.stderr)
            print(
                "  Automatic agent creation failed. Follow the ~2-minute manual\n"
                "  steps in implementation/README.md under \"Setting it up\", then\n"
                "  add LIBRECHAT_FOLLOWUP_AGENT_ID=<the id> to implementation/.env\n"
                "  yourself and run: docker compose up -d --wait rca-dashboard"
            )

    section("Done")
    print("  Dashboard:  http://127.0.0.1:8000")
    print("  LibreChat:  http://localhost:3080  (sign up with any email/password)")
    print("  Logs:       docker compose logs -f")
    print("  Stop all:   docker compose down")


if __name__ == "__main__":
    main()
