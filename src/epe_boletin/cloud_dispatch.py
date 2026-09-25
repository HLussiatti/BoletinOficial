"""Dispatch a single queued request to the repository's Actions workflow."""

from __future__ import annotations

import os
import re

import requests


class DispatchError(RuntimeError):
    pass


def configured() -> bool:
    return bool(os.environ.get("EPE_GITHUB_ACTIONS_TOKEN", "").strip()
                and os.environ.get("EPE_GITHUB_REPOSITORY", "").strip())


def dispatch(job_id: str, *, session: requests.Session | None = None) -> None:
    repository = os.environ.get("EPE_GITHUB_REPOSITORY", "").strip()
    token = os.environ.get("EPE_GITHUB_ACTIONS_TOKEN", "").strip()
    branch = os.environ.get("EPE_GITHUB_REF", "main").strip()
    if not (re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository)
            and re.fullmatch(r"[A-Za-z0-9_./-]+", branch)
            and re.fullmatch(r"[0-9a-f]{32}", job_id) and token):
        raise DispatchError("La ejecución externa no está configurada")
    endpoint = (f"https://api.github.com/repos/{repository}/actions/workflows/"
                "cloud-worker.yml/dispatches")
    try:
        response = (session or requests).post(
            endpoint, json={"ref": branch, "inputs": {"job_id": job_id}},
            headers={"Authorization": f"Bearer {token}",
                     "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28"}, timeout=8)
    except requests.RequestException as exc:
        raise DispatchError("No se pudo contactar al ejecutor") from exc
    if response.status_code != 204:
        raise DispatchError(f"GitHub no aceptó la ejecución (HTTP {response.status_code})")
