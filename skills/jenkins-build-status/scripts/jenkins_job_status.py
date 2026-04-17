#!/usr/bin/env python3
"""This object is responsible for summarizing Jenkins job status in read-only mode."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from base64 import b64encode
from datetime import datetime, timezone
from typing import Any


ENV_TOKENS = {"dev", "qa", "stg", "prod", "loc", "local"}
GENERIC_TOKENS = {
    "kube",
    "job",
    "jobs",
    "batch",
    "bat",
    "front",
    "backend",
    "back",
    "api",
    "admin",
    "web",
    "service",
    "worker",
    "fargate",
    "mo",
    "pc",
}
FAIL_STATES = {"FAILURE", "UNSTABLE", "ABORTED"}


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


def tokenize_job_name(name: str) -> list[str]:
    tokens = [token for token in re.split(r"[^a-z0-9]+", name.lower()) if token]
    cleaned: list[str] = []
    for token in tokens:
        if token in ENV_TOKENS or token in GENERIC_TOKENS:
            continue
        if token.isdigit():
            continue
        cleaned.append(token)
    return cleaned


def is_related_job(source: dict[str, Any], candidate: dict[str, Any]) -> bool:
    if source["name"] == candidate["name"]:
        return False
    source_tokens = source["tokens"]
    candidate_tokens = candidate["tokens"]
    if not source_tokens or not candidate_tokens:
        return False
    overlap = len(set(source_tokens) & set(candidate_tokens))
    if overlap >= 2:
        return True
    if source_tokens[0] == candidate_tokens[0] and overlap >= 1:
        return True
    return False


def state_rank(state: str) -> int:
    order = {
        "RUNNING": 0,
        "FAILURE": 1,
        "UNSTABLE": 2,
        "ABORTED": 3,
        "SUCCESS": 4,
        "DISABLED": 5,
        "NOT_BUILT": 6,
        "UNKNOWN": 7,
    }
    return order.get(state, 99)


def print_failure_report(jobs: list[dict[str, Any]], limit: int) -> None:
    failing_jobs = [job for job in jobs if job["state"] in FAIL_STATES][: max(limit, 0)]
    if not failing_jobs:
        return

    print()
    print("FAILURE_REPORT")
    for job in failing_jobs:
        related = [candidate for candidate in jobs if is_related_job(job, candidate)]
        related.sort(key=lambda item: (state_rank(item["state"]), item["name"]))
        related = related[:5]
        print(
            f"- {job['name']} state={job['state']} build={job['last_number']} "
            f"result={job['last_result']} age={job['age']}"
        )
        if related:
            related_summary = ", ".join(
                f"{item['name']}[{item['state']}/{item['last_number']}]"
                for item in related
            )
            print(f"  related: {related_summary}")
        else:
            print("  related: none")


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
    parser.add_argument(
        "--include-related",
        action="store_true",
        help="When failures exist, include a chained related-job report",
    )
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
            "tokens": tokenize_job_name(raw_job.get("name", "-")),
        }
        if job["building"]:
            job["state"] = "RUNNING"
        jobs.append(job)

    filtered = [job for job in jobs if matches_filter(job, args.match, args.only)]
    filtered.sort(key=lambda job: (job["state"] != "RUNNING", job["state"], job["name"]))
    filtered = filtered[: max(args.limit, 0)]

    running = sum(1 for job in jobs if job["state"] == "RUNNING")
    failing = sum(1 for job in jobs if job["state"] in FAIL_STATES)
    disabled = sum(1 for job in jobs if job["state"] == "DISABLED")

    print(f"total={len(jobs)} running={running} failing={failing} disabled={disabled}")
    print(f"{'JOB':40} {'STATE':10} {'BUILD':>7} {'RESULT':10} {'AGE':>6}")
    for job in filtered:
        print(
            f"{job['name'][:40]:40} {job['state'][:10]:10} {str(job['last_number']):>7} "
            f"{str(job['last_result'])[:10]:10} {job['age']:>6}"
        )
    if args.include_related or args.only == "failing":
        print_failure_report(jobs, args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
