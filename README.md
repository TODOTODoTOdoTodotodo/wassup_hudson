# wassup_hudson

Read-only Jenkins status helpers for Codex-style MCP workflows.

## What this repository contains

- A Codex skill for Jenkins build and job status lookup
- A read-only fallback script for compact Jenkins summaries
- A safe sharing baseline with no real credentials committed

## Repository layout

```text
skills/
  jenkins-build-status/
    SKILL.md
    agents/openai.yaml
    scripts/jenkins_job_status.py
examples/
  .env.example
```

## First-run rule

The skill requires this behavior:

1. Check whether the `jenkins` MCP server exists in the current session.
2. If it is missing, connect Jenkins MCP before doing status lookups.
3. Jenkins URL, username, token, or password must be collected interactively at runtime.
4. Do not hardcode secrets in repository files.

## Suggested local setup

Create a local `.env` from `examples/.env.example` and fill in your own values.

```bash
cp examples/.env.example .env
```

Then either:

- connect a `jenkins` MCP server in your Codex client using runtime-provided values
- or export the same variables and run the fallback script directly

## Fallback script usage

```bash
set -a
source ./.env
set +a
python3 skills/jenkins-build-status/scripts/jenkins_job_status.py
python3 skills/jenkins-build-status/scripts/jenkins_job_status.py --only running
python3 skills/jenkins-build-status/scripts/jenkins_job_status.py --only failing --limit 20
python3 skills/jenkins-build-status/scripts/jenkins_job_status.py --match dcr
```

## Safety

- This repository is read-only by design for build status lookup
- It should not trigger builds unless you intentionally extend it
- Keep real Jenkins credentials outside version control
