---
name: jenkins-build-status
description: Jenkins의 현재 빌드 상태, 실행 중인 잡, 실패한 잡, 여러 잡의 요약 상태가 필요할 때 사용한다. 현재 세션에 구성된 Jenkins MCP 툴이 있으면 우선 사용하고, 세션에서 MCP를 바로 쓸 수 없거나 여러 잡을 짧게 요약해야 하면 포함된 상태 조회 스크립트로 폴백한다.
---

# Jenkins Build Status

Jenkins 상태를 읽기 전용으로 확인할 때 사용하는 스킬이다.

## 빠른 시작

1. 현재 세션에 `jenkins` MCP 서버가 있는지 먼저 확인한다.
2. 없으면 Jenkins URL, 계정, 토큰 또는 비밀번호를 사용자 인터랙션으로 입력받아 연결한다.
3. 연결이 되면 MCP 기반으로 상태를 조회한다.
4. MCP가 현재 세션에서 보이지 않으면 `scripts/jenkins_job_status.py`로 폴백한다.

## 최초 1회 필수 규칙

상태 조회를 시작하기 전에 반드시 `jenkins` MCP 서버 존재 여부를 확인한다.

1. MCP 연결 여부를 먼저 확인한다.
2. `jenkins` MCP 서버가 없으면 조회 전에 연결부터 수행한다.
3. Jenkins URL, 사용자명, API 토큰 또는 비밀번호는 런타임 사용자 인터랙션으로 수집한다.
4. 스킬 본문, 예시, 저장소 파일에는 실제 시크릿을 하드코딩하지 않는다.

## 동작 절차

1. 요청이 상태 조회 전용인지 확인한다.
2. 현재 세션에 `jenkins` MCP 서버가 있는지 확인한다.
3. MCP가 없으면 필요한 연결 값을 사용자에게 받아 먼저 Jenkins MCP를 연결한다.
4. MCP가 있으면 읽기 전용 Jenkins MCP 툴을 우선 사용한다.
5. 아래 조건이면 번들 스크립트로 폴백한다.
   - 현재 세션에 MCP 툴이 노출되지 않음
   - 여러 잡을 짧은 표 형태로 요약해야 함
   - 이름 또는 상태 필터로 빠르게 조회하는 편이 효율적임
6. 응답은 요약부터 먼저 준다.
   - 실행 중인 잡
   - 실패 또는 불안정한 잡
   - 비활성화된 잡
   - 눈여겨볼 최근 빌드 번호와 시각
7. 실패한 잡이 있으면 연쇄 확인이 필요한 관련 잡까지 함께 본다.
   - 동일 서비스군으로 보이는 잡
   - 동일 배치/프론트/백엔드 계열로 보이는 잡
   - 이름 패턴상 같이 움직일 가능성이 높은 잡
8. 실패 리포트에는 실패 잡만 나열하지 말고, 관련 잡 상태를 함께 묶어서 제시한다.

## MCP 우선 사용 규칙

Jenkins MCP 툴이 보이면 아래 읽기 전용 툴을 우선 사용한다.

- `get_all_items`
- `query_items`
- `get_build`
- `get_running_builds`
- `get_build_console_output`

`get_build_console_output`은 사용자가 로그나 실패 원인을 명시적으로 요청했을 때만 사용한다.

사용자가 명시적으로 요청하지 않는 한 빌드 실행이나 중단은 하지 않는다.

## 스크립트 폴백

표 형태의 상태 요약이 필요하면 `scripts/jenkins_job_status.py`를 사용한다.

필수 환경변수:

- `JENKINS_URL`
- `JENKINS_USERNAME`
- `JENKINS_PASSWORD`

이 값들은 런타임 사용자 입력 또는 현재 셸 환경에서 받아야 한다. 실제 값은 커밋하지 않는다.

사용 예시:

```bash
python3 skills/jenkins-build-status/scripts/jenkins_job_status.py
python3 skills/jenkins-build-status/scripts/jenkins_job_status.py --match dcr
python3 skills/jenkins-build-status/scripts/jenkins_job_status.py --only failing
python3 skills/jenkins-build-status/scripts/jenkins_job_status.py --only running --limit 20
```

실패 리포트 예시:

```bash
python3 skills/jenkins-build-status/scripts/jenkins_job_status.py --only failing --include-related
```

## 응답 형식

응답은 짧고 바로 읽히게 유지한다. 먼저 전체 요약을 주고, 필요한 잡만 아래 항목으로 정리한다.

- 잡 이름
- 현재 상태
- 최근 빌드 번호
- 최근 빌드 결과
- 경과 시간

실패한 잡이 있으면 추가로 아래 내용을 포함한다.

- 연쇄 확인이 필요한 관련 잡 목록
- 관련 잡의 현재 상태
- 같은 계열에서 동시에 깨진 잡이 있는지 여부

실패 잡이나 실행 중인 잡이 없으면 그 사실을 명확히 적는다.
