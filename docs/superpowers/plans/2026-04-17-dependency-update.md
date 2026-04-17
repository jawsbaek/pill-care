# Dependency Update — Python 3.14 + Moderate Sweep Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Python 3.14로 런타임을 올리고 6개월 이상 경과하거나 major bump가 있는 의존성 4개(google-cloud-storage, streamlit, ruff)를 최신 stable로 업데이트한 후, 단일 PR로 `main`에 올린다.

**Architecture:** `pyproject.toml` + `Dockerfile` + `.python-version` + `uv.lock` 4개 파일 + 필요 시 `src/**/*.py` 린트 자동 수정. 로컬에서 `uv sync` → `ruff` → `pytest` → `docker build` 검증을 통과한 뒤 브랜치 푸시 + `gh pr create`.

**Tech Stack:** Python 3.14, uv, ruff 0.15, pytest 9, Docker (linux/amd64), GitHub Actions (CI) / GCP Cloud Run (CD).

**Spec:** `docs/superpowers/specs/2026-04-17-dependency-update-design.md`

---

## File Map

| 파일 | 변경 유형 | 책임 |
|---|---|---|
| `.python-version` | 수정 (이미 워크트리에 반영) | 로컬/CI uv에게 Python 3.14 지정 |
| `pyproject.toml` | 수정 | requires-python + 4개 의존성 pin 변경 |
| `Dockerfile` | 수정 | 빌더/런타임 베이스 이미지를 3.14로 |
| `uv.lock` | 재생성 | `uv lock --upgrade` 결과 |
| `src/**/*.py` | (조건부) 수정 | ruff 0.15 신규 규칙이 잡는 위반 자동 수정분 |

---

## Task 1: 사전 준비 — Python 3.14 설치 및 작업 브랜치 생성

**Files:** (파일 변경 없음)

- [ ] **Step 1: Python 3.14 설치**

Run:
```bash
uv python install 3.14
```
Expected: `Installed Python 3.14.x` 메시지 또는 `already installed` 메시지.

- [ ] **Step 2: 설치 확인**

Run:
```bash
uv python list | grep '3.14'
```
Expected: `cpython-3.14.x-macos-aarch64-none` 등 설치된 인터프리터 한 줄 이상 출력.

- [ ] **Step 3: 현재 git 상태 확인**

Run:
```bash
git status --short
```
Expected: `.python-version` 수정됨 (M), 그 외에 staged 변경은 없어야 함. 새 파일(`.claude/`, `docs/2601.15645v1.pdf`, `docs/research/`)은 untracked 상태 유지.

- [ ] **Step 4: 작업 브랜치 생성**

Run:
```bash
git checkout -b chore/deps-python-3.14
```
Expected: `Switched to a new branch 'chore/deps-python-3.14'`.

- [ ] **Step 5: 기준 테스트 실행 (옵션, 하지만 강력 권장)**

현재 Python 3.11 환경에서 기존 테스트가 통과하는지 베이스라인 확인. (실패하는 테스트가 있다면 이번 PR 범위 밖의 이슈이므로 먼저 파악만 해둔다.)

Run:
```bash
uv sync --frozen
uv run pytest --tb=short
```
Expected: 모든 테스트 통과. 실패하는 것이 있으면 실패한 테스트 이름을 기록해 두고 작업 계속.

---

## Task 2: Python 런타임 bump (커밋 1)

**Files:**
- Modify: `pyproject.toml` (`requires-python` 라인)
- Modify: `Dockerfile` (builder/runtime 베이스 이미지 2곳)
- Commit: `.python-version` (이미 3.14로 수정되어 있음)

- [ ] **Step 1: `pyproject.toml` requires-python 수정**

Edit `pyproject.toml`:
```toml
# 변경 전
requires-python = ">=3.11"

# 변경 후
requires-python = ">=3.14"
```

- [ ] **Step 2: `Dockerfile` 베이스 이미지 수정**

Edit `Dockerfile`:

라인 2 (builder):
```dockerfile
# 변경 전
FROM --platform=linux/amd64 ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

# 변경 후
FROM --platform=linux/amd64 ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder
```

라인 23 (runtime):
```dockerfile
# 변경 전
FROM --platform=linux/amd64 python:3.11-slim-bookworm

# 변경 후
FROM --platform=linux/amd64 python:3.14-slim-bookworm
```

- [ ] **Step 3: 변경 diff 확인**

Run:
```bash
git diff .python-version pyproject.toml Dockerfile
```
Expected: `.python-version`이 `3.11 → 3.14`, `pyproject.toml`의 `requires-python`이 `>=3.11 → >=3.14`, `Dockerfile`에 `python3.11 → python3.14` 변경 2건.

- [ ] **Step 4: 커밋**

Run:
```bash
git add .python-version pyproject.toml Dockerfile
git commit -m "$(cat <<'EOF'
chore(python): bump runtime to 3.14

.python-version, pyproject requires-python, Dockerfile builder/runtime
베이스 이미지를 3.14로 올린다. uv.lock 재생성과 의존성 bump는 후속 커밋.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```
Expected: 3개 파일이 포함된 커밋 생성.

---

## Task 3: google-cloud-storage 2.x → 3.x (커밋 2)

**Files:**
- Modify: `pyproject.toml` (GCS 라인)

- [ ] **Step 1: `pyproject.toml` GCS 라인 수정**

Edit `pyproject.toml`:
```toml
# 변경 전
"google-cloud-storage>=2.18.0,<3.0.0",

# 변경 후
"google-cloud-storage>=3.10,<4.0",
```

- [ ] **Step 2: `gcs_loader.py` 예외 임포트 없는지 재확인 (코드 변경 없음 검증)**

Grep 도구 사용:
- 패턴: `resumable_media|InvalidResponse|DataCorruption`
- 경로: `src/`

Expected: 매치 없음. 있으면 `src/pillcare/gcs_loader.py` 임포트를 `google.cloud.storage.exceptions`로 수정해야 함. (설계 단계 감사 결과는 매치 없음.)

- [ ] **Step 3: 커밋**

Run:
```bash
git add pyproject.toml
git commit -m "$(cat <<'EOF'
chore(deps): upgrade google-cloud-storage 2.18 → 3.10

google-resumable-media 통합이 포함된 3.0 major bump. 현재 코드는
google.cloud.storage 기본 API만 사용하므로 소스 변경 불필요.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```
Expected: 1개 파일 커밋.

---

## Task 4: streamlit 1.45 → 1.56 (커밋 3)

**Files:**
- Modify: `pyproject.toml` (streamlit 라인)

- [ ] **Step 1: `pyproject.toml` streamlit 라인 수정**

Edit `pyproject.toml`:
```toml
# 변경 전
"streamlit==1.45.1",

# 변경 후
"streamlit==1.56.0",
```

- [ ] **Step 2: 코드에 experimental API 미사용 재확인**

Grep 도구 사용:
- 패턴: `st\.experimental_|st\.beta_`
- 경로: `src/`

Expected: 매치 없음. 매치가 있으면 각 호출을 현행 stable API로 치환 후 진행.

- [ ] **Step 3: 커밋**

Run:
```bash
git add pyproject.toml
git commit -m "$(cat <<'EOF'
chore(deps): upgrade streamlit 1.45 → 1.56

app.py는 st.cache_resource, st.file_uploader 등 stable API만 사용.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```
Expected: 1개 파일 커밋.

---

## Task 5: ruff >=0.9 → ==0.15.11 pin (커밋 4)

**Files:**
- Modify: `pyproject.toml` ([dependency-groups.dev] ruff 라인)

- [ ] **Step 1: `pyproject.toml` ruff 라인 수정**

Edit `pyproject.toml`:
```toml
# 변경 전
dev = [
    "pytest==9.0.3",
    "ruff>=0.9.0",
]

# 변경 후
dev = [
    "pytest==9.0.3",
    "ruff==0.15.11",
]
```

- [ ] **Step 2: 커밋**

Run:
```bash
git add pyproject.toml
git commit -m "$(cat <<'EOF'
chore(deps): pin ruff to 0.15.11

lint 동작 일관성을 위해 범위 지정 대신 정확 pin. 신규 기본 규칙
위반 수정은 후속 커밋에서 uv.lock과 함께 반영.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```
Expected: 1개 파일 커밋.

---

## Task 6: uv.lock 재생성 + 설치 검증

**Files:**
- Modify: `uv.lock` (전체 재생성)

- [ ] **Step 1: 락 파일 재생성**

Run:
```bash
uv lock --upgrade
```
Expected: 
- 성공 시 `Resolved N packages in Xms` 형식 메시지
- `uv.lock` 파일이 수정됨
- 해결 불가(no solution) 오류가 뜨면 즉시 중단하고 원인 파악 (대개는 Python 3.14 wheel 미제공 의존성)

- [ ] **Step 2: 의존성 설치**

Run:
```bash
uv sync --frozen
```
Expected: 
- `Using Python 3.14.x` 라인
- 모든 패키지가 빌드/다운로드됨
- 최종적으로 `Installed N packages` 메시지

- [ ] **Step 3: 설치된 핵심 버전 확인**

Run:
```bash
uv run python -c "import sys; print('py=', sys.version_info[:3])"
uv run python -c "import streamlit, google.cloud.storage as gcs, anthropic, langgraph, pydantic; print('streamlit=', streamlit.__version__); print('gcs=', gcs.__version__); print('anthropic=', anthropic.__version__); print('langgraph=', langgraph.__version__); print('pydantic=', pydantic.__version__)"
uv run ruff --version
```
Expected:
```
py= (3, 14, X)
streamlit= 1.56.0
gcs= 3.10.1 (혹은 3.10.x)
anthropic= 0.95.0
langgraph= 1.1.6
pydantic= 2.13.1
ruff 0.15.11
```
실패: 버전이 기대와 다르면 pyproject의 해당 라인을 재확인 후 Step 1부터 재실행.

---

## Task 7: ruff lint + format 통과

**Files:**
- (조건부) Modify: `src/**/*.py` — 자동 수정이 적용된 파일들

- [ ] **Step 1: lint 검사 (read-only)**

Run:
```bash
uv run ruff check . 2>&1 | tee /tmp/ruff-initial.log
```
Expected 분기:
- `All checks passed!` → Step 4로 이동
- `Found N errors` → Step 2로 진행

- [ ] **Step 2: 자동 수정 적용**

Run:
```bash
uv run ruff check --fix .
```
Expected: `Fixed M errors` 메시지. 남은 오류가 0이면 다음 단계.

- [ ] **Step 3: 남은 위반 수작업 수정 (해당 시)**

Run:
```bash
uv run ruff check .
```

- `Found 0 errors` → 다음 단계
- 남은 오류가 있으면: 각 오류를 개별 Edit으로 수정. **`# noqa` 추가는 피한다** — 코드 수정이 원칙.
- 변경이 과도해 이번 PR 스코프를 초과한다고 판단되면 중단하고 사용자에게 확인 요청.

- [ ] **Step 4: format 확인**

Run:
```bash
uv run ruff format --check .
```
Expected: `N files already formatted`. 만약 `Would reformat M files`가 뜨면 다음 단계.

- [ ] **Step 5: (조건부) format 적용**

Run:
```bash
uv run ruff format .
uv run ruff format --check .
```
Expected: 최종적으로 `N files already formatted`.

- [ ] **Step 6: 변경사항 요약 확인**

Run:
```bash
git status --short
git diff --stat
```
Expected: `uv.lock` + (조건부) `src/**/*.py` 수정 파일 목록. 예상 밖의 파일이 있으면 검토.

---

## Task 8: 테스트 스위트 통과

**Files:** (변경 없음)

- [ ] **Step 1: pytest 실행**

Run:
```bash
uv run pytest --tb=short
```
Expected: Task 1 Step 5의 베이스라인과 동일한 통과/실패 세트.
- 베이스라인이 all-pass였으면 여기도 all-pass.
- 새로운 실패가 있으면 원인을 특정:
  - Python 3.14 관련 deprecation → 해당 소스 수정
  - 의존성 bump 관련 API 변경 → 릴리스 노트 확인 후 소스 수정
  - 수정 불가 시 사용자에게 에스컬레이션.

- [ ] **Step 2: 앱 import smoke (런타임 에러 조기 포착)**

Run:
```bash
uv run python -c "import pillcare.app; print('ok')"
```
Expected: `ok`. ImportError가 나면 원인 분석.

---

## Task 9: Docker 빌드 검증

**Files:** (변경 없음)

- [ ] **Step 1: 이미지 빌드**

Run:
```bash
docker build -t pillcare:py314 .
```
Expected: 
- `Successfully tagged pillcare:py314`
- 중간 단계에서 `uv sync --locked --no-dev`가 성공해야 함.
- 실패 시: 실패 단계의 로그를 저장하고 원인 파악. Python 3.14 wheel 미제공이면 해당 패키지 다른 버전으로 조정 필요.

- [ ] **Step 2: (옵션) 컨테이너 기동 smoke**

Run:
```bash
docker run --rm -d --name pillcare-smoke -p 8501:8501 -e GCS_BUCKET=dummy -e GCS_BLOB=dummy pillcare:py314
sleep 5
curl -sS -o /dev/null -w "%{http_code}\n" http://localhost:8501/ || true
docker logs pillcare-smoke | tail -30
docker rm -f pillcare-smoke
```
Expected: HTTP 200 (Streamlit 첫 페이지 응답). GCS 없이 DB 다운로드가 실패해도 Streamlit 서버 자체는 기동하는지만 본다. 기동 자체가 실패하면 로그로 원인 파악.

옵션 단계이므로 로컬 Docker가 없으면 스킵하고 Task 10으로.

---

## Task 10: 최종 커밋 (커밋 5)

**Files:**
- Commit: `uv.lock`
- Commit: (조건부) ruff가 수정한 `src/**/*.py`

- [ ] **Step 1: 스테이징할 파일 확인**

Run:
```bash
git status --short
```
Expected: `uv.lock`이 M 상태. 조건부로 `src/pillcare/*.py`도 M.

- [ ] **Step 2: 스테이징**

Run:
```bash
git add uv.lock
# 조건부: ruff가 수정한 src 파일만 선택적으로
git add src/
```

- [ ] **Step 3: diff 최종 확인**

Run:
```bash
git diff --cached --stat
```
Expected: 주로 `uv.lock` 대규모 변경 + (있다면) 소수 `src/**/*.py` 라인 조정.

- [ ] **Step 4: 커밋**

lint 자동 수정이 있었다면:
```bash
git commit -m "$(cat <<'EOF'
chore(deps): relock uv.lock and fix ruff 0.15 lint findings

uv lock --upgrade 결과 반영. ruff 0.15.11의 신규 기본 규칙이
보고한 위반을 ruff check --fix로 자동 수정.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

lint 수정이 없었다면:
```bash
git commit -m "$(cat <<'EOF'
chore(deps): relock uv.lock

pyproject의 Python 3.14 + 4건 의존성 bump에 맞춰 락 재생성.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 5: 커밋 로그 최종 확인**

Run:
```bash
git log --oneline -6
```
Expected: 최근 5개가 이번 PR의 커밋, 그 아래는 `main`의 `f28aac3`.

---

## Task 11: 브랜치 푸시 + PR 생성

**Files:** (Git 원격 작업)

- [ ] **Step 1: 원격으로 푸시**

Run:
```bash
git push -u origin chore/deps-python-3.14
```
Expected: 새 원격 브랜치 생성 성공.

- [ ] **Step 2: PR 본문 준비 (로컬 변수에 저장할 필요 없음 — 다음 단계에서 직접 HEREDOC 사용)**

- [ ] **Step 3: `gh pr create`**

Run:
```bash
gh pr create --title "chore: Python 3.14 + dependency sweep (gcs 3.x, streamlit 1.56, ruff 0.15)" --body "$(cat <<'EOF'
## Summary

- **Python 3.11 → 3.14** (`.python-version`, `pyproject.toml`, `Dockerfile`)
- **google-cloud-storage 2.18 → 3.10** (major, 634일 경과)
- **streamlit 1.45.1 → 1.56.0** (340일 경과)
- **ruff 0.9 → 0.15.11** (463일 경과, 정확 pin으로 전환)

업데이트 기준: 6개월 이상 경과 또는 major bump 존재.
상세 설계는 `docs/superpowers/specs/2026-04-17-dependency-update-design.md` 참고.

## Breaking change 영향

- GCS 3.0: `google-resumable-media` 통합. 우리 코드는 `storage.Client()` / `blob.download_to_filename()`만 사용하므로 소스 변경 없음.
- Streamlit 1.56: `app.py`는 stable API만 사용하므로 소스 변경 없음.
- Ruff 0.15: 신규 기본 규칙은 `ruff check --fix`로 처리.

## Test plan

- [ ] CI `lint-test` job 통과 (ruff check/format + pytest)
- [ ] Docker 이미지 빌드 성공 (main에 머지 후 `build-deploy` job)
- [ ] 로컬: `uv sync --frozen && uv run pytest` all-pass
- [ ] 로컬: `docker build -t pillcare:py314 .` 성공
- [ ] (수동) Cloud Run 배포 후 Streamlit 첫 페이지 200 응답

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```
Expected: `https://github.com/<owner>/<repo>/pull/<N>` URL 출력.

- [ ] **Step 4: PR URL 사용자에게 보고**

PR URL과 함께 다음 사항 요약:
- 5개 커밋의 목록
- 로컬 검증 결과 (pytest, ruff, docker build)
- CI 결과는 GitHub Actions에서 확인

---

## Rollback Playbook (문제 발생 시)

| 증상 | 조치 |
|---|---|
| Step 6-1에서 `uv lock --upgrade` 해결 불가 | 에러 메시지로 미호환 패키지 식별 → 해당 패키지를 한 단계 낮은 버전으로 고정 시도 → 불가 시 사용자에게 보고 후 중단 |
| Step 7에서 ruff 위반이 수십 건 이상 | `ruff check --fix`로 처리 못 하는 것만 남으면 수작업. 범위가 너무 크면 이번 PR에서 ruff pin만 유지하고 lint 수정은 별도 PR로 이관 (사용자 승인 후) |
| Step 8에서 기존 통과 테스트가 fail | 실패 원인이 Python 3.14 deprecation이면 소스 수정. 의존성 API 변경이면 해당 패키지 릴리스 노트 확인 후 수정. 불가 시 사용자에게 에스컬레이션. |
| Step 9에서 Docker 빌드 실패 | 단계별 로그 저장. 네이티브 휠 미존재면 해당 패키지 버전 재조정. |
| PR 머지 후 Cloud Run 배포 실패 | CI가 이전 성공 이미지 태그를 유지하므로 Cloud Run 콘솔에서 이전 revision으로 트래픽 복원. 그 다음 PR을 revert. |

---

## 완료 기준

1. 작업 브랜치 `chore/deps-python-3.14` 가 5개 커밋으로 `main`과 diverge
2. GitHub PR 생성됨
3. 로컬에서 `uv sync --frozen` + `uv run pytest` + `uv run ruff check .` + `uv run ruff format --check .` 모두 통과
4. 로컬에서 `docker build -t pillcare:py314 .` 성공
5. PR URL을 사용자에게 전달
