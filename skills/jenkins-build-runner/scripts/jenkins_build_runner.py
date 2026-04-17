#!/usr/bin/env python3
"""This object is responsible for triggering only whitelisted Jenkins jobs."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from base64 import b64encode
from typing import Any


ALLOWED_PREFIX = "dev-"


def build_request(
    url: str,
    username: str,
    password: str,
    method: str = "GET",
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> urllib.request.Request:
    credentials = b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    request = urllib.request.Request(url=url, data=data, method=method)
    request.add_header("Authorization", f"Basic {credentials}")
    request.add_header("Accept", "application/json")
    if headers:
        for key, value in headers.items():
            request.add_header(key, value)
    return request


def fetch_json(url: str, username: str, password: str) -> dict[str, Any]:
    request = build_request(url, username, password)
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)


def fetch_crumb(jenkins_url: str, username: str, password: str) -> tuple[str, str] | None:
    crumb_url = urllib.parse.urljoin(jenkins_url.rstrip("/") + "/", "crumbIssuer/api/json")
    try:
        payload = fetch_json(crumb_url, username, password)
    except Exception:
        return None
    field = payload.get("crumbRequestField")
    crumb = payload.get("crumb")
    if field and crumb:
        return str(field), str(crumb)
    return None


def parse_params(raw_params: list[str]) -> dict[str, str]:
    params: dict[str, str] = {}
    for raw in raw_params:
        if "=" not in raw:
            raise ValueError(f"Invalid parameter format: {raw}")
        key, value = raw.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Invalid parameter key: {raw}")
        params[key] = value
    return params


def ensure_allowed(job_name: str) -> None:
    if not job_name.startswith(ALLOWED_PREFIX):
        raise PermissionError(
            f"Blocked: only jobs starting with '{ALLOWED_PREFIX}' can be triggered."
        )


def check_job_exists(jenkins_url: str, username: str, password: str, job_name: str) -> dict[str, Any]:
    job_path = "/".join(["job", urllib.parse.quote(job_name, safe="")])
    api_url = urllib.parse.urljoin(jenkins_url.rstrip("/") + "/", f"{job_path}/api/json")
    return fetch_json(api_url, username, password)


def trigger_job(
    jenkins_url: str,
    username: str,
    password: str,
    job_name: str,
    params: dict[str, str],
) -> tuple[int, str | None]:
    job_base = urllib.parse.urljoin(
        jenkins_url.rstrip("/") + "/", f"job/{urllib.parse.quote(job_name, safe='')}/"
    )
    if params:
        endpoint = urllib.parse.urljoin(job_base, "buildWithParameters")
        body = urllib.parse.urlencode(params).encode("utf-8")
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
    else:
        endpoint = urllib.parse.urljoin(job_base, "build")
        body = b""
        headers = {}

    crumb = fetch_crumb(jenkins_url, username, password)
    if crumb:
        headers[crumb[0]] = crumb[1]

    request = build_request(endpoint, username, password, method="POST", data=body, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.getcode(), response.headers.get("Location")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get("Location")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", required=True, help="Target Jenkins job name")
    parser.add_argument(
        "--param",
        action="append",
        default=[],
        help="Build parameter in key=value format. Can be used multiple times.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate only, do not trigger build")
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

    try:
        ensure_allowed(args.job)
        params = parse_params(args.param)
        job_info = check_job_exists(jenkins_url, jenkins_username, jenkins_password, args.job)
    except PermissionError as exc:
        print(str(exc), file=sys.stderr)
        return 3
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 4
    except urllib.error.HTTPError as exc:
        print(f"Job lookup failed: HTTP {exc.code}", file=sys.stderr)
        return 5
    except Exception as exc:  # noqa: BLE001
        print(f"Job lookup failed: {exc}", file=sys.stderr)
        return 5

    if args.dry_run:
        print(f"allowed=true job={args.job} dry_run=true params={len(params)}")
        print(f"url={job_info.get('url', '-')}")
        return 0

    status_code, location = trigger_job(
        jenkins_url,
        jenkins_username,
        jenkins_password,
        args.job,
        params,
    )

    if status_code in {200, 201, 202}:
        print(f"queued=true job={args.job} status={status_code}")
        if location:
            print(f"queue={location}")
        return 0

    print(f"queued=false job={args.job} status={status_code}", file=sys.stderr)
    if location:
        print(f"queue={location}", file=sys.stderr)
    return 6


if __name__ == "__main__":
    raise SystemExit(main())
