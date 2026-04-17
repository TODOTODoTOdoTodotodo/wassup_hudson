---
name: jenkins-build-status
description: Use when the user wants the current Jenkins build or job status, a summary of multiple Jenkins items, failing jobs, running builds, or recent build health. Prefer the configured Jenkins MCP tools when they are available; fall back to the bundled status script when MCP is unavailable in the current session or when a compact summary across many jobs is faster.
---

# Jenkins Build Status

Use this skill to inspect Jenkins job health without changing Jenkins state.

## First-run requirement

Before any status lookup, check whether the `jenkins` MCP server is available in the current session.

1. Check MCP availability first.
2. If the `jenkins` MCP server is missing, connect it before continuing.
3. Required connection values such as Jenkins URL, username, API token, or password must be gathered through user interaction at runtime.
4. Do not hardcode secrets in the skill, examples, or repository files.

## Workflow

1. Confirm the request is status-only.
2. Check whether the `jenkins` MCP server is available in the current session.
3. If it is missing, ask the user for the required connection values and connect Jenkins MCP first.
4. Prefer Jenkins MCP tools if the `jenkins` MCP server is available in the current session.
5. Use the bundled script when:
   - MCP tools are not exposed in the session
   - the user wants a compact summary across many jobs
   - you need a quick filter by name or status
6. Return a concise summary first:
   - running jobs
   - failed or unstable jobs
   - disabled jobs
   - notable last build numbers and timestamps

## MCP-first guidance

When Jenkins MCP tools are available, prefer read-only tools such as:

- `get_all_items`
- `query_items`
- `get_build`
- `get_running_builds`
- `get_build_console_output` only when the user explicitly asks for logs or failure details

Do not trigger builds or stop builds unless the user explicitly asks.

## Script fallback

Use `scripts/jenkins_job_status.py` for table-style summaries.

Required environment variables:

- `JENKINS_URL`
- `JENKINS_USERNAME`
- `JENKINS_PASSWORD`

These values must come from interactive user input or the active shell environment at runtime. Do not commit real values.

Common usage:

```bash
python3 skills/jenkins-build-status/scripts/jenkins_job_status.py
python3 skills/jenkins-build-status/scripts/jenkins_job_status.py --match dcr
python3 skills/jenkins-build-status/scripts/jenkins_job_status.py --only failing
python3 skills/jenkins-build-status/scripts/jenkins_job_status.py --only running --limit 20
```

## Output shape

Keep the answer compact. Summarize first, then list the most relevant jobs with:

- job name
- current state
- last build number
- last build result
- build age

If there are no failures or running jobs, state that explicitly.
