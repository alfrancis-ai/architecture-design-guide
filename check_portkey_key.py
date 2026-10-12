"""Check that a Portkey admin API key can read workspaces and analytics.

Read-only: it makes only GET calls, and never prints the key.

It reads the same finops/.env as run_local.py and run_local_logs.py:
    PORTKEY_ADMIN_API_KEY_DEV=...      the key (if missing, you're asked for it, hidden)
    PORTKEY_BASE_URL=...               optional; defaults to real Portkey
    PORTKEY_SSL_VERIFY=false           optional; skip TLS certificate checks, like
                                       lambda_function.py's ssl_verify=False (default true)

    python buildoutdocs/check_portkey_key.py
"""
import getpass
import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

# finops/, so .env is found whatever the current directory is (as in run_local.py).
FINOPS_DIR = Path(__file__).resolve().parent.parent
load_dotenv(FINOPS_DIR / ".env")

BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1")
METADATA_KEY = "api_key_order_number"
MAX_WORKSPACES = 3   # how many workspaces to check analytics for

# Like EnvironmentConfig.ssl_verify: false skips certificate checks (e.g. behind a
# proxy whose certificate Python rejects). lambda_function.py uses False.
SSL_VERIFY = os.getenv("PORTKEY_SSL_VERIFY", "true").lower() == "true"
SSL_CONTEXT = ssl.create_default_context() if SSL_VERIFY else ssl._create_unverified_context()


def get(path, key, **params):
    """GET a Portkey path. Returns (HTTP status, JSON body or error text)."""
    url = f"{BASE_URL}{path}" + (f"?{urllib.parse.urlencode(params)}" if params else "")
    request = urllib.request.Request(url, headers={"x-portkey-api-key": key})
    try:
        with urllib.request.urlopen(request, timeout=60, context=SSL_CONTEXT) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode(errors="replace")[:300]
    except urllib.error.URLError as error:   # no connection, proxy, certificate
        return None, str(error.reason)


def main():
    key = os.getenv("PORTKEY_ADMIN_API_KEY_DEV") or getpass.getpass("Portkey admin API key (hidden): ")
    end = datetime.now(timezone.utc).replace(microsecond=0)
    start = end - timedelta(days=1)
    window = {"time_of_generation_min": start.isoformat(), "time_of_generation_max": end.isoformat()}
    print(f"Portkey: {BASE_URL}  (SSL verify: {SSL_VERIFY})")
    print(f"Window:  last 24 hours, {start.isoformat()} to {end.isoformat()}\n")

    # 1. List workspaces (needs an admin key)
    status, body = get("/admin/workspaces", key)
    print(f"1. List workspaces -> HTTP {status}")
    if status is None:
        print(f"   {body}")
        print("   FAILED: couldn't reach Portkey (network, proxy or certificate); the key wasn't checked.")
        if "CERTIFICATE" in str(body).upper():
            print("   For a certificate error, PORTKEY_SSL_VERIFY=false in finops/.env skips the check.")
        return
    if status != 200:
        print(f"   {body}")
        print("   FAILED: the key can't list workspaces (not an admin key, or missing that permission).")
        return
    workspaces = body.get("data", [])
    print(f"   OK: {body.get('total', len(workspaces))} workspace(s); checking the first {MAX_WORKSPACES}")

    # 2. Analytics for a few workspaces: cost (cents), requests, cost per order number
    for workspace in workspaces[:MAX_WORKSPACES]:
        slug = workspace.get("slug")
        print(f"\n   Workspace: {workspace.get('name')} ({slug})")
        for metric in ("cost", "requests"):
            status, body = get(f"/analytics/graphs/{metric}", key, workspace_slug=slug, **window)
            value = body.get("summary", {}).get("total") if status == 200 else body
            unit = " cents" if metric == "cost" and status == 200 else ""
            print(f"   2. {metric:<8} -> HTTP {status}: {value}{unit}")
        status, body = get(f"/analytics/groups/metadata/{METADATA_KEY}", key, workspace_slug=slug, **window)
        if status == 200:
            groups = [(g.get("metadata_value"), g.get("cost")) for g in body.get("data", [])]
            print(f"   3. by {METADATA_KEY} -> HTTP 200: {groups or 'no requests with that metadata'}")
        else:
            print(f"   3. by {METADATA_KEY} -> HTTP {status}: {body}")


if __name__ == "__main__":
    main()

