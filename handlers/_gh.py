"""handlers/_gh.py — thin GitHub REST helpers shared by the issue handlers.

Each handler mutates state files + rebuilds README/scrapbook, and uses these to
comment on / label / close the triggering issue. The git COMMIT is done by the
workflow afterward (handlers don't commit).

All calls degrade gracefully with no token (print instead of HTTP), so handlers
can be run locally against a fake event payload for testing.
"""

from __future__ import annotations

import json
import os

API = "https://api.github.com"


def load_event() -> dict:
    path = os.environ.get("GITHUB_EVENT_PATH")
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    # local testing fallback
    raw = os.environ.get("FAKE_EVENT")
    return json.loads(raw) if raw else {}


def repo() -> str:
    return os.environ.get("GITHUB_REPOSITORY", "frankiehope333-ctrl/frankiehope333-ctrl")


def _token() -> str | None:
    return os.environ.get("GITHUB_TOKEN")


def _req(method: str, url: str, payload: dict | None = None):
    token = _token()
    if not token:
        print(f"[dry-run no token] {method} {url} {payload or ''}")
        return None
    import requests
    r = requests.request(
        method, url, json=payload,
        headers={"Authorization": f"bearer {token}",
                 "Accept": "application/vnd.github+json"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json() if r.text else None


def comment(issue_number: int, body: str) -> None:
    _req("POST", f"{API}/repos/{repo()}/issues/{issue_number}/comments", {"body": body})


def close_issue(issue_number: int) -> None:
    _req("PATCH", f"{API}/repos/{repo()}/issues/{issue_number}", {"state": "closed"})


def add_label(issue_number: int, label: str) -> None:
    _req("POST", f"{API}/repos/{repo()}/issues/{issue_number}/labels", {"labels": [label]})


def issue_has_label(issue: dict, label: str) -> bool:
    return any(l.get("name") == label for l in issue.get("labels", []))
