# Dependency Update — Python 3.14 + Moderate Sweep

- **Date:** 2026-04-17
- **Scope:** Python 런타임 + 애플리케이션/개발 의존성 일괄 업데이트
- **Status:** Design approved — 구현 대기

## 1. 배경과 목표

PillCare는 현재 Python 3.11 + LangGraph 기반 POC다. 프로젝트가 아직 구축 단계이므로
오래된 의존성이 쌓이기 전에 런타임과 라이브러리를 모던 버전으로 정렬한다.

업데이트 기준 (사용자 결정):

1. **Python 3.14 확정** — 2025-10 릴리스, 생태계 wheel 준비 확인됨
2. **6개월 이상 경과한 라이브러리**는 최신 stable로 업데이트
3. **메이저 버전 업데이트가 있는 라이브러리**는 최신 major stable로 업데이트
4. 그 외 패치/마이너 업데이트는 **이 PR에서는 건드리지 않음**
5. **단일 PR**, 커밋은 논리 단위로 분리

## 2. 현재 상태 스냅샷 (2026-04-17 PyPI 기준)

| 패키지 | 현재 | PyPI 최신 | 릴리스 경과(일) | 분류 |
|---|---|---|---|---|
| python | 3.11 | 3.14.x | — | **UPDATE** (사용자 결정) |
| google-cloud-storage | 2.18.0 (`<3.0.0`) | 3.10.1 | 634 | **MAJOR + STALE** |
| streamlit | 1.45.1 | 1.56.0 | 340 | **STALE (>6mo)** |
| ruff | >=0.9.0 | 0.15.11 | 463 | **STALE (>6mo)** |
| anthropic | 0.95.0 | 0.96.0 | 3 | skip (patch, fresh) |
| langchain-core | 1.2.30 | 1.2.31 | 2 | skip (patch, fresh) |
| langchain-anthropic | 1.4.0 | 1.4.0 | 31 | skip (up-to-date) |
| langchain-google-genai | 4.2.2 | 4.2.2 | 2 | skip (up-to-date) |
| langgraph | 1.1.6 | 1.1.6 | 14 | skip (up-to-date) |
| pydantic | 2.13.1 | 2.13.1 | 2 | skip (up-to-date) |
| rapidfuzz | 3.14.5 | 3.14.5 | 10 | skip (up-to-date) |
| msoffcrypto-tool | 6.0.0 | 6.0.0 | 95 | skip (up-to-date) |
| python-dotenv | 1.2.2 | 1.2.2 | 47 | skip (up-to-date) |
| pytest | 9.0.3 | 9.0.3 | 10 | skip (up-to-date) |
| openpyxl | 3.1.5 | 3.1.5 | 658 | **skip** — 상류에 신 버전 없음 (유일한 stable) |

**업데이트 대상: 4건 (Python 3.14 포함).**

## 3. Python 3.14 호환성 확인

PyPI 휠/클래시파이어 확인 결과:

- **cp314 네이티브 휠 제공:** `rapidfuzz 3.14.5`, `pydantic-core 2.46.1` (pydantic의 내부 네이티브 의존)
- **pure-python + 3.14 classifier:** streamlit 1.56.0, google-cloud-storage 3.10.1, anthropic 0.95.0,
  langchain-core 1.2.30, msoffcrypto-tool 6.0.0, pydantic 2.13.1
- **pure-python + classifier 미갱신:** langgraph 1.1.6 (classifier 3.13까지), openpyxl 3.1.5
  (classifier 3.9까지). 둘 다 pure-python이므로 런타임에서 문제될 가능성은 낮음.

→ Python 3.14에서 `uv sync` 와 `pytest` 실행으로 검증한다.

## 4. Breaking Change 영향 분석

### 4.1 google-cloud-storage 2.x → 3.10.1

**공식 3.0 Migration Note 요약 (GitHub README):**

- `google-resumable-media` 라이브러리 통합
- `google.resumable_media.common.InvalidResponse` / `DataCorruption` →
  `google.cloud.storage.exceptions.InvalidResponse` / `DataCorruption`
- 임시 하위호환: 새 예외가 옛 예외의 서브클래스
- 그 외 공개 API 변경 없음

**코드 영향 (`src/pillcare/gcs_loader.py`):**

```python
from google.cloud import storage
client = storage.Client()
bucket = client.bucket(bucket_name)
blob = bucket.blob(blob_name)
blob.download_to_filename(tmp_path)
```

→ `resumable_media` 예외를 임포트하지 않음. **코드 변경 불필요.**

### 4.2 streamlit 1.45.1 → 1.56.0

사용 API 감사 결과 (`src/pillcare/app.py`):
`st.cache_resource`, `st.set_page_config`, `st.title`, `st.caption`, `st.info`,
`st.error`, `st.warning`, `st.success`, `st.file_uploader`, `st.text_input`,
`st.button`, `st.spinner`, `st.subheader`, `st.expander`, `st.markdown`,
`st.write` — 모두 stable. `st.experimental_*` / `st.beta_*` 사용 없음.

→ **코드 변경 불필요.** 다만 로컬에서 앱 기동 한 번 확인.

### 4.3 ruff 0.9.0 → 0.15.11

- 프로젝트에 ruff 설정 파일 없음 (`[tool.ruff]` 블록 부재, `ruff.toml` 부재)
- 0.9 → 0.15 사이에 **기본 stable rule이 확장**되었을 수 있음
- **조치:** 로컬에서 `ruff check .` 실행 → 새 위반은 `ruff check --fix` 자동 수정 우선,
  자동 수정 불가한 것만 코드를 수정. `# noqa` 추가는 피한다.

### 4.4 Python 3.11 → 3.14 (3년치 점프)

주요 주의사항:

- **표준 라이브러리 제거:** `cgi`, `crypt`, `imp`, `distutils` 등 — 현재 소스에서 grep 결과 사용처 없음
- **`asyncio` API 변경 가능성** — LangGraph 내부에서 사용, 상위 래퍼에 영향 없음
- **JIT / free-threaded (`--disable-gil`)** — 기본 꺼져 있음. 이 PR 스코프에서 활성화하지 않음.

## 5. 변경 파일 명세

### 5.1 `pyproject.toml`

```toml
# 변경 전
requires-python = ">=3.11"
dependencies = [
    ...
    "google-cloud-storage>=2.18.0,<3.0.0",
    ...
    "streamlit==1.45.1",
]
[dependency-groups]
dev = [
    "pytest==9.0.3",
    "ruff>=0.9.0",
]

# 변경 후
requires-python = ">=3.14"
dependencies = [
    ...
    "google-cloud-storage>=3.10,<4.0",
    ...
    "streamlit==1.56.0",
]
[dependency-groups]
dev = [
    "pytest==9.0.3",
    "ruff==0.15.11",
]
```

주: `ruff`는 lint 동작 일관성을 위해 `>=` 가 아니라 정확 pin(`==`)으로 변경.
GCS는 기존 스타일(range)을 유지하되 major를 3.x로 올린다.

### 5.2 `.python-version`

```
3.14
```

이미 작업 트리에 `3.11 → 3.14` 변경이 반영되어 있으며, 본 PR에서 함께 커밋한다.

### 5.3 `Dockerfile`

```dockerfile
# Stage 1
FROM --platform=linux/amd64 ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

# Stage 2
FROM --platform=linux/amd64 python:3.14-slim-bookworm
```

### 5.4 `uv.lock`

`uv lock --upgrade` 실행 후 재생성된 파일 커밋. 잠금 파일의 `upload-time` 등
부가 필드는 uv가 관리.

### 5.5 `.github/workflows/ci-cd.yml`

`astral-sh/setup-uv@v5` 가 `.python-version`을 자동 존중하므로 **변경 없음**.

### 5.6 (조건부) `src/**/*.py`

`ruff check --fix` 결과에 따라 자동 수정된 파일이 포함될 수 있음. 수동 수정이
필요한 위반은 케이스별로 리뷰 후 반영.

## 6. 검증 전략

| 단계 | 명령 | 합격 기준 |
|---|---|---|
| 1. Python 설치 | `uv python install 3.14` | 성공 |
| 2. 락 재생성 | `uv lock --upgrade` | 해결 충돌 없음 |
| 3. 설치 | `uv sync --frozen` | 성공 |
| 4. 린트 | `uv run ruff check .` | 0 위반 (혹은 자동수정 후 0) |
| 5. 포맷 | `uv run ruff format --check .` | 차이 없음 |
| 6. 테스트 | `uv run pytest --tb=short` | 기존 통과 테스트 모두 통과 |
| 7. Docker 빌드 | `docker build -t pillcare:py314 .` | 성공 |
| 8. (선택) 컨테이너 기동 smoke | `docker run -p 8501:8501 pillcare:py314` + HTTP 200 확인 | 응답 확인 |
| 9. CI | GitHub Actions `lint-test` job | green |

## 7. PR 구조 (단일 PR, 커밋 5개)

1. `chore(python): bump runtime to 3.14 (.python-version, Dockerfile, pyproject)`
2. `chore(deps): upgrade google-cloud-storage 2.18 → 3.10`
3. `chore(deps): upgrade streamlit 1.45 → 1.56`
4. `chore(deps): upgrade ruff 0.9 → 0.15 and fix new lint findings`
5. `chore(deps): relock uv.lock`

각 커밋은 개별적으로 빌드 가능할 필요는 없음 (단일 PR로 머지되므로), 단 리뷰어가
변경 의도를 쉽게 파악하도록 논리 단위를 보존한다.

## 8. 리스크 & 롤백

| 리스크 | 확률 | 영향 | 완화 |
|---|---|---|---|
| Python 3.14 런타임 deprecation 경고 | 중 | 저 | pytest 로그로 포착, 필요 시 후속 PR |
| ruff 0.15 신규 rule 위반이 대규모 | 중 | 중 | `--fix`로 자동 수정, 남는 것만 수작업 |
| GCS 3.x 런타임 회귀 | 낮 | 중 | 실배포 전 Cloud Run staging 이미지로 검증 |
| Docker 빌드 실패 (휠 미존재) | 낮 | 고 | 로컬 빌드를 PR 전에 완료 |

**롤백:** 단일 PR을 revert. Cloud Run은 이전 이미지 태그로 즉시 복원 가능
(CI 파이프라인 `:${{ github.sha }}` 태그 스킴 유지).

## 9. 범위 외 (이번 PR에서 다루지 않음)

- 6개월 이내 패치/마이너 업데이트 (anthropic 0.95→0.96, langchain-core 1.2.30→1.2.31 등)
- free-threaded Python / JIT 활성화
- openpyxl 교체 (상류에 신 버전 없음)
- LangChain 생태계의 향후 major bump (별도 PR에서 다룰 사안)
- Cloud Run 배포 스펙 변경 (`--memory`, `--cpu` 등)

## 10. 성공 정의

1. `main` 브랜치에서 CI `lint-test` 통과
2. Docker 빌드 성공
3. 로컬에서 Streamlit 앱 기동 후 기본 경로(파일 업로드 → 파이프라인 실행) 확인
4. 사용자 코드(`src/pillcare/*.py`)에 불필요한 수정 없음 (ruff 자동수정 제외)
