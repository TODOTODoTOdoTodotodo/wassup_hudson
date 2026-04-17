---
name: jenkins-build-runner
description: Jenkins 빌드 실행이 필요할 때 사용한다. 단, 잡 이름이 dev- 로 시작하는 경우에만 허용한다. 현재 세션의 jenkins MCP 서버를 먼저 확인하고, 없으면 Jenkins URL, 계정, 토큰 또는 비밀번호를 사용자 인터랙션으로 입력받아 연결한다. 쓰기 가능한 Jenkins MCP 툴이 없으면 포함된 실행 스크립트로 폴백한다.
---

# Jenkins Build Runner

Jenkins 빌드를 실행할 때 사용하는 스킬이다. 이 스킬은 `dev-` 로 시작하는 잡만 허용한다.

## 빠른 시작

1. 현재 세션에 `jenkins` MCP 서버가 있는지 먼저 확인한다.
2. 없으면 Jenkins URL, 계정, 토큰 또는 비밀번호를 사용자 인터랙션으로 입력받아 연결한다.
3. 사용자가 요청한 잡 이름이 `dev-` 로 시작하는지 먼저 확인한다.
4. `dev-` 패턴이 아니면 즉시 거부한다.
5. 가능하면 쓰기 가능한 Jenkins MCP 툴을 사용하고, 없으면 `scripts/jenkins_build_runner.py` 로 폴백한다.

## 최초 1회 필수 규칙

1. `jenkins` MCP 서버 존재 여부를 먼저 확인한다.
2. MCP가 없으면 조회나 실행 전에 먼저 연결한다.
3. Jenkins URL, 사용자명, API 토큰 또는 비밀번호는 런타임 사용자 인터랙션으로 수집한다.
4. 저장소 파일, 스킬 본문, 예제에는 실제 시크릿을 하드코딩하지 않는다.

## 실행 안전 규칙

1. 잡 이름이 반드시 `dev-` 로 시작해야 한다.
2. `dev-` 로 시작하지 않으면 실행하지 않는다.
3. 사용자가 명시적으로 실행을 요청한 경우에만 빌드를 시작한다.
4. 운영, QA, 배포 성격의 잡이라도 이름이 `dev-` 가 아니면 모두 거부한다.
5. 실행 전에 가능하면 대상 잡 이름과 파라미터를 다시 짧게 확인한다.

## 권장 절차

1. 먼저 상태를 확인해 대상 잡이 존재하는지 본다.
2. 사용자가 실행 의사를 명확히 표현했는지 확인한다.
3. 잡 이름이 `dev-` 패턴인지 확인한다.
4. 파라미터가 있으면 이름과 값을 정리한다.
5. MCP 쓰기 툴이 있으면 그것을 우선 사용한다.
6. 없으면 스크립트 폴백을 사용한다.
7. 실행 후에는 큐 등록 여부 또는 응답 코드를 짧게 보고한다.

## 스크립트 폴백

실행 스크립트는 `scripts/jenkins_build_runner.py` 이다.

필수 환경변수:

- `JENKINS_URL`
- `JENKINS_USERNAME`
- `JENKINS_PASSWORD`

이 값들은 런타임 사용자 입력 또는 현재 셸 환경에서 받아야 한다. 실제 값은 커밋하지 않는다.

사용 예시:

```bash
python3 skills/jenkins-build-runner/scripts/jenkins_build_runner.py --job dev-sample-job --dry-run
python3 skills/jenkins-build-runner/scripts/jenkins_build_runner.py --job dev-sample-job
python3 skills/jenkins-build-runner/scripts/jenkins_build_runner.py --job dev-sample-job --param branch=develop --param force=true
```

## 응답 형식

응답은 짧게 유지한다.

- 실행 허용 여부
- 대상 잡 이름
- 파라미터 유무
- 큐 등록 성공 여부 또는 실패 이유

거부 시에는 `dev- 패턴이 아니라서 차단됨` 을 명확히 적는다.
