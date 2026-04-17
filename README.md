# wassup_hudson

Codex 스타일 워크플로우에서 Jenkins 상태를 읽기 전용으로 조회하기 위한 스킬과 보조 스크립트 모음입니다.

## 빠른 시작

1. `jenkins` MCP 서버가 현재 세션에 있는지 먼저 확인합니다.
2. 없으면 Jenkins URL, 계정, 토큰 또는 비밀번호를 사용자 인터랙션으로 입력받아 MCP를 연결합니다.
3. 상태 조회만 필요하면 스킬에 자연어로 요청합니다.
4. MCP를 바로 쓸 수 없으면 `.env`를 준비한 뒤 폴백 스크립트로 조회합니다.

`dev-` 패턴 잡만 실행해야 하면 별도의 실행 스킬을 사용합니다. 이 실행 스킬은 상태 조회 스킬과 동일한 Jenkins 접속 정보를 재사용하는 것을 기본으로 합니다.

스킬 설치 한 줄:

```text
skill-installer로 https://github.com/TODOTODoTOdoTodotodo/wassup_hudson.git 에 있는 skills/jenkins-build-status 스킬 설치해줘
```

```text
skill-installer로 https://github.com/TODOTODoTOdoTodotodo/wassup_hudson.git 에 있는 skills/jenkins-build-runner 스킬 설치해줘
```

설치 후에는 현재 Codex CLI 세션을 반드시 재시작해야 새 스킬이 반영됩니다.

상태 조회 스킬 자연어 예시:

- `현재 Jenkins에서 실행 중인 빌드 알려줘`
- `실패한 Jenkins 잡만 요약해줘`
- `dev-dcr 관련 잡 상태 정리해줘`
- `qa-kube 계열 현재 빌드 상태 보여줘`
- `최근에 불안정하거나 중단된 잡 알려줘`

실행 스킬 자연어 예시:

- `dev-user-api 잡 실행해줘`
- `dev-batch-job 를 branch=develop 파라미터로 실행해줘`
- `dev-admin-api 빌드 실행 전에 가능한지 먼저 확인해줘`

예시:

```bash
cp examples/.env.example .env
```

```bash
set -a
source ./.env
set +a
python3 skills/jenkins-build-status/scripts/jenkins_job_status.py --only running
```

## 저장소 구성

```text
skills/
  jenkins-build-status/
    SKILL.md
    agents/openai.yaml
    scripts/jenkins_job_status.py
  jenkins-build-runner/
    SKILL.md
    agents/openai.yaml
    scripts/jenkins_build_runner.py
examples/
  .env.example
```

## 포함 내용

- Jenkins 빌드/잡 상태를 조회하는 Codex 스킬
- `dev-` 패턴 잡만 실행할 수 있는 제한형 Jenkins 실행 스킬
- 여러 잡 상태를 빠르게 요약하는 읽기 전용 폴백 스크립트
- 실제 시크릿을 커밋하지 않기 위한 예시 환경파일

## 설치 방법

`skill-installer`를 사용할 때는 아래 명령으로 이 저장소의 스킬을 설치합니다.

```text
skill-installer로 https://github.com/TODOTODoTOdoTodotodo/wassup_hudson.git 에 있는 skills/jenkins-build-status 스킬 설치해줘
```

```text
skill-installer로 https://github.com/TODOTODoTOdoTodotodo/wassup_hudson.git 에 있는 skills/jenkins-build-runner 스킬 설치해줘
```

설치 후에는 현재 Codex CLI 세션을 반드시 종료하고 다시 시작해야 새 스킬이 반영됩니다.

## 최초 1회 동작 규칙

이 저장소의 스킬은 아래 순서로 동작하는 것을 전제로 합니다.

1. 현재 세션에 `jenkins` MCP 서버가 있는지 확인합니다.
2. 상태 조회 스킬이 이미 확보한 Jenkins 접속 정보가 있으면 실행 스킬도 동일한 값을 재사용합니다.
3. 없으면 상태 조회 전에 Jenkins MCP를 먼저 연결합니다.
4. Jenkins URL, 사용자명, 토큰 또는 비밀번호는 런타임에 사용자 인터랙션으로 수집합니다.
5. 저장소 파일, 스킬 본문, 예제에는 실제 시크릿을 넣지 않습니다.

## 실행 제한 규칙

- 빌드 실행은 `dev-` 로 시작하는 잡만 허용합니다.
- `qa-`, `stg-`, `prod-`, 기타 접두어 잡은 모두 차단합니다.
- 실행 전에 가능하면 상태를 먼저 확인하는 흐름을 권장합니다.
- 실행 스킬은 `--dry-run` 검증 경로를 제공합니다.

## 로컬 사용 방법

`examples/.env.example`를 복사해서 `.env`를 만든 뒤 자신의 Jenkins 접속 정보를 넣습니다.

```bash
cp examples/.env.example .env
```

그 다음 두 가지 방식 중 하나를 사용합니다.

- Codex 클라이언트에서 `jenkins` MCP 서버를 연결한 뒤 스킬에 자연어로 요청
- 동일한 환경변수를 export 한 뒤 폴백 스크립트를 직접 실행

## 폴백 스크립트 사용 예시

```bash
set -a
source ./.env
set +a
python3 skills/jenkins-build-status/scripts/jenkins_job_status.py
python3 skills/jenkins-build-status/scripts/jenkins_job_status.py --only running
python3 skills/jenkins-build-status/scripts/jenkins_job_status.py --only failing --limit 20
python3 skills/jenkins-build-status/scripts/jenkins_job_status.py --match dcr
```

실행 예시:

```bash
set -a
source ./.env
set +a
python3 skills/jenkins-build-runner/scripts/jenkins_build_runner.py --job dev-sample-job --dry-run
python3 skills/jenkins-build-runner/scripts/jenkins_build_runner.py --job dev-sample-job
python3 skills/jenkins-build-runner/scripts/jenkins_build_runner.py --job dev-sample-job --param branch=develop --param force=true
```

## 상태 해석

- `RUNNING`: 현재 빌드 중
- `SUCCESS`, `FAILURE`, `UNSTABLE`, `ABORTED`, `NOT_BUILT`: 최근 빌드가 완료된 상태
- `DISABLED`: 비활성화된 잡

## 안전 원칙

- 기본 목적은 읽기 전용 상태 조회입니다.
- 사용자가 명시적으로 요청하지 않는 한 빌드 실행이나 중단을 하지 않습니다.
- 실제 Jenkins 자격증명은 버전 관리 밖에서 관리해야 합니다.
