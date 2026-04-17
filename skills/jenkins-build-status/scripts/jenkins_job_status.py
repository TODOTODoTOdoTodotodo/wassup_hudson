#!/usr/bin/env python3
"""This object is responsible for summarizing Jenkins job status in read-only mode."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from base64 import b64encode
from datetime import datetime, timezone
from typing import Any


def build_request(url: str, username: str, password: str) -> urllib.request.Request:
    credentials = b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    request = urllib.request.Request(url)
    request.add_header("Authorization", f"Basic {credentials}")
    request.add_header("Accept", "application/json")
    return request


def fetch_json(url: str, username: str, password: str) -> dict[str, Any]:
    request = build_request(url, username, password)
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)


def classify_job(job: dict[str, Any]) -> str:
    color = (job.get("color") or "").lower()
    last_build = job.get("lastBuild") or {}
    if job.get("building") or "anime" in color:
        return "RUNNING"
    if color == "disabled":
        return "DISABLED"
    result = (last_build.get("result") or "").upper()
    if result:
        return result
    if color.startswith("blue"):
        return "SUCCESS"
    if color.startswith("red"):
        return "FAILURE"
    if color.startswith("yellow"):
        return "UNSTABLE"
    if color.startswith("aborted"):
        return "ABORTED"
    if color.startswith("notbuilt"):
        return "NOT_BUILT"
    return "UNKNOWN"


def format_age(timestamp_ms: Any) -> str:
    if not timestamp_ms:
        return "-"
    try:
        timestamp = datetime.fromtimestamp(int(timestamp_ms) / 1000, tz=timezone.utc)
    except (TypeError, ValueError):
        return "-"
    delta = datetime.now(timezone.utc) - timestamp
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    if seconds < 86400:
        return f"{seconds // 3600}h"
    return f"{seconds // 86400}d"


def matches_filter(job: dict[str, Any], match: str | None, only: str) -> bool:
    name = (job.get("name") or "").lower()
    state = (job.get("state") or "").lower()
    if match and match.lower() not in name:
        return False
    if only == "all":
        return True
    if only == "running":
        return state == "running"
    if only == "failing":
        return state in {"failure", "unstable", "aborted"}
    if only == "disabled":
        return state == "disabled"
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--match", help="Substring filter for job names")
    parser.add_argument(
        "--only",
        choices=["all", "running", "failing", "disabled"],
        default="all",
        help="Status filter",
    )
    parser.add_argument("--limit", type=int, default=50, help="Maximum rows to print")
    args = parser.parse_args()

    jenkins_url = os.environ.get("JENKINS_URL")
    jenkins_username = os.environ.get("JENKINS_USERNAME")
    jenkins_password = os.environ.get("JENKINS_PASSWORD")

    if not all([jenkins_url, jenkins_username, jenkins_password]):
        print(
            "Missing required environment variables: JENKINS_URL, JENKINS_USERNAME, JENKINS_PASSWORD",
            file=sys.stderr,
        )
        return 2

    tree = "jobs[name,url,color,lastBuild[number,result,timestamp,building]]"
    api_url = urllib.parse.urljoin(jenkins_url.rstrip("/") + "/", "api/json") + f"?tree={tree}"

    try:
        payload = fetch_json(api_url, jenkins_username, jenkins_password)
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to fetch Jenkins status: {exc}", file=sys.stderr)
        return 1

    jobs: list[dict[str, Any]] = []
    for raw_job in payload.get("jobs", []):
        last_build = raw_job.get("lastBuild") or {}
        job = {
            "name": raw_job.get("name", "-"),
            "state": classify_job(raw_job | {"lastBuild": last_build}),
            "last_number": last_build.get("number", "-"),
            "last_result": (last_build.get("result") or "-"),
            "age": format_age(last_build.get("timestamp")),
            "url": raw_job.get("url", "-"),
            "building": last_build.get("building", False),
        }
        if job["building"]:
            job["state"] = "RUNNING"
        jobs.append(job)

    filtered = [job for job in jobs if matches_filter(job, args.match, args.only)]
    filtered.sort(key=lambda job: (job["state"] != "RUNNING", job["state"], job["name"]))
    filtered = filtered[: max(args.limit, 0)]

    running = sum(1 for job in jobs if job["state"] == "RUNNING")
    failing = sum(1 for job in jobs if job["state"] in {"FAILURE", "UNSTABLE", "ABORTED"})
    disabled = sum(1 for job in jobs if job["state"] == "DISABLED")

    print(f"total={len(jobs)} running={running} failing={failing} disabled={disabled}")
    print(f"{'JOB':40} {'STATE':10} {'BUILD':>7} {'RESULT':10} {'AGE':>6}")
    for job in filtered:
        print(
            f"{job['name'][:40]:40} {job['state'][:10]:10} {str(job['last_number']):>7} "
            f"{str(job['last_result'])[:10]:10} {job['age']:>6}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
