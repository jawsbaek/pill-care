# PillCare GCP 클라우드 배포 설계

## 목표

PillCare POC를 GCP 최소 인프라로 배포하여 소규모(5-10명) 팀원/지인이 접속해 테스트할 수 있는 환경을 구축한다.

## 아키텍처 개요

```
GitHub (push main)
  └─ GitHub Actions
       ├─ lint + pytest (57 tests)
       ├─ Docker build (multi-stage uv)
       ├─ Artifact Registry push
       └─ Cloud Run deploy
            ├─ GCS에서 pillcare.db 다운로드 (시작 시, @st.cache_resource)
            ├─ Vertex AI Gemini 2.5 Flash 호출 (ADC 인증)
            └─ IAP로 Google 계정 인증 (--iap 플래그)
```

## 1. LLM 전환: Claude → Gemini (Vertex AI)

### 패키지

- `langchain-google-genai>=4.0.0` 사용 (`langchain-google-vertexai`의 `ChatVertexAI`는 deprecated)
- `ChatGoogleGenerativeAI(model="gemini-2.5-flash", vertexai=True, project=..., location="asia-northeast3")`

### 모델 선택 근거

| 모델 | Input $/1M | Output $/1M | 비고 |
|------|-----------|------------|------|
| gemini-2.0-flash | - | - | **2026-06 종료 예정, 사용 불가** |
| gemini-2.5-flash | $0.30 | $2.50 | 한국어 의료 트리아지 정확도 73.8% (최고), thinkingBudget 조절 가능 |
| gemini-2.5-pro | $1.25 | $10.00 | flash 대비 4x 비용, POC에는 과잉 |

**선택: gemini-2.5-flash** — 비용 대비 품질 최적, 한국어 의료 텍스트 검증됨.

### 인증

Cloud Run 서비스 계정의 Application Default Credentials(ADC)로 자동 인증. API 키 불필요.

```bash
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:pillcare-runner@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

### 안전 필터 설정

Gemini 안전 필터가 의료 컨텐츠(부작용, 금기사항)를 차단할 수 있으므로, 명시적으로 설정:

```python
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    vertexai=True,
    project=PROJECT_ID,
    location="asia-northeast3",
    max_output_tokens=5000,
    safety_settings={
        "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
        "HARM_CATEGORY_HARASSMENT": "BLOCK_ONLY_HIGH",
    },
)
```

### Structured Output 전환 (CRITICAL)

Gemini는 Claude 대비 마크다운 섹션 헤더/인라인 태그 포맷이 불안정하다. 기존 regex 파싱 방식은 Gemini에서 깨질 위험이 높다.

**해결**: `with_structured_output(Pydantic, method="json_schema")` 사용으로 regex 파싱 제거.

```python
from pydantic import BaseModel
from typing import Literal

class DrugSection(BaseModel):
    section_name: Literal[
        "명칭", "성상", "효능효과", "투여의의", "용법용량",
        "저장방법", "주의사항", "상호작용", "투여종료후", "기타",
    ]
    content: str
    source_tier: Literal["T1:허가정보", "T1:e약은요", "T1:DUR", "T4:AI"]

class DrugGuidanceOutput(BaseModel):
    drug_name: str
    sections: list[DrugSection]

structured_llm = llm.with_structured_output(DrugGuidanceOutput, method="json_schema")
```

**이점**:
- LLM 응답이 스키마에 강제 준수되어 파싱 오류 제거
- Claude/Gemini 모두 동일 Pydantic 모델 사용 — 모델 교체가 LLM 객체 1줄 변경으로 완료
- source_tier가 Literal enum이므로 guardrails 검증이 단순해짐

### 프롬프트 호환성 대응

| 항목 | Claude | Gemini | 대응 |
|------|--------|--------|------|
| SystemMessage 준수력 | 강함 | 약함 | HumanMessage에 핵심 규칙 중복 + few-shot 예시 추가 |
| 파라미터명 | `max_tokens` | `max_output_tokens` | 명시적으로 `max_output_tokens=5000` 사용 |
| 한국어 품질 | 자연스러운 환자 친화 문체 | 형식적/공식적 문체 | 프롬프트에 문체 지시 강화 |
| 토큰 카운팅 | Claude 토크나이저 | Gemini 토크나이저 (한국어 10-15% 더 많음) | max_output_tokens 여유분 확보 (5000) |

---

## 2. 데이터: GCS → Cloud Run

### 전략

Pre-built SQLite DB를 GCS 버킷에 저장하고, 컨테이너 시작 시 Python으로 다운로드.

```
gs://pillcare-data/pillcare.db → /tmp/pillcare.db
```

### 구현

```python
from google.cloud import storage
import hashlib

GCS_BUCKET = "pillcare-data"
GCS_BLOB = "pillcare.db"
DB_LOCAL_PATH = "/tmp/pillcare.db"
EXPECTED_SHA256 = "..."  # DB 빌드 시 생성, 환경변수로 주입

@st.cache_resource
def load_database() -> str:
    """Download DB from GCS with integrity verification."""
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(GCS_BLOB)
    blob.download_to_filename(DB_LOCAL_PATH)

    # SHA256 무결성 검증
    sha256 = hashlib.sha256()
    with open(DB_LOCAL_PATH, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    if sha256.hexdigest() != os.environ.get("DB_SHA256", ""):
        raise RuntimeError("DB integrity check failed")

    # SQLite 무결성 검증
    import sqlite3
    conn = sqlite3.connect(DB_LOCAL_PATH)
    result = conn.execute("PRAGMA integrity_check").fetchone()
    conn.close()
    if result[0] != "ok":
        raise RuntimeError(f"SQLite integrity check failed: {result[0]}")

    return DB_LOCAL_PATH
```

### DB 업데이트 프로세스 (수동, POC)

```bash
# 1. 로컬에서 크롤링 + DB 빌드
uv run python -m pillcare.db_builder

# 2. SHA256 계산
shasum -a 256 data/pillcare.db

# 3. GCS 업로드
gsutil cp data/pillcare.db gs://pillcare-data/pillcare.db

# 4. Cloud Run 환경변수 업데이트 (SHA256)
gcloud run services update pillcare --set-env-vars DB_SHA256=<hash>
```

---

## 3. 컨테이너

### Dockerfile

```dockerfile
# === Stage 1: Builder ===
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# 의존성 레이어 (캐시 최적화)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# 소스 코드 복사 + 프로젝트 설치
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# === Stage 2: Runtime ===
FROM python:3.11-slim-bookworm

RUN groupadd --system --gid 999 nonroot \
    && useradd --system --gid 999 --uid 999 --create-home nonroot

COPY --from=builder --chown=nonroot:nonroot /app /app

ENV PATH="/app/.venv/bin:$PATH"
USER nonroot
WORKDIR /app

EXPOSE 8501

ENTRYPOINT ["streamlit", "run", "src/pillcare/app.py", \
    "--server.port=8501", \
    "--server.address=0.0.0.0", \
    "--server.headless=true", \
    "--server.enableWebsocketCompression=false"]
```

### .dockerignore

```
data/
tests/
docs/
research/
person_sample/
.claude/
.venv/
__pycache__/
*.pyc
.env
.git/
```

### Python 버전

프로젝트 `.python-version`이 3.11이므로 Docker 이미지도 **python:3.11-slim-bookworm** 사용 (불일치 방지).

---

## 4. Cloud Run 설정

```bash
gcloud run deploy pillcare \
  --region asia-northeast3 \
  --image asia-northeast3-docker.pkg.dev/$PROJECT_ID/pillcare/app:$SHA \
  --memory 2Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 2 \
  --concurrency 1 \
  --timeout 600 \
  --no-allow-unauthenticated \
  --iap \
  --cpu-boost \
  --service-account pillcare-runner@$PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars "GCS_BUCKET=pillcare-data,GCS_BLOB=pillcare.db,DB_SHA256=$DB_HASH,LOG_LEVEL=WARNING"
```

### 설정 근거

| 항목 | 값 | 근거 |
|------|-----|------|
| memory | 2Gi | Python + Streamlit + SQLite(100MB /tmp) + FTS5 인덱스 + LangGraph. 1Gi는 부족 우려 |
| timeout | 600s | 11개 약물 순차 LLM 호출(3-5s/건) + 재시도 = 최대 ~440s. 300s 초과 가능 |
| concurrency | 1 | Streamlit은 단일 사용자 세션 기반, 병렬 요청 시 메모리 스파이크 방지 |
| max-instances | 2 | POC 비용 상한. 동시 2명까지 |
| min-instances | 0 | 비용 절약 (사용하지 않을 때 $0). 콜드스타트 15-25s 허용 |
| cpu-boost | 활성 | 콜드스타트 시 CPU 부스트로 시작 시간 단축 |
| WebSocket compression | false | IAP 프록시와의 호환성 문제 방지 |

### IAP 인증

```bash
# IAP 활성화 (Cloud Run 직접 통합, Load Balancer 불필요, 무료)
gcloud run deploy pillcare --iap --no-allow-unauthenticated

# 사용자 권한 부여
gcloud beta iap web add-iam-policy-binding \
  --member=user:someone@gmail.com \
  --role=roles/iap.httpsResourceAccessor \
  --region=asia-northeast3 \
  --resource-type=cloud-run \
  --service=pillcare
```

**주의사항**:
- gmail.com 외부 사용자 초대 시 **custom OAuth consent screen** 설정 필요
- IAP 우회 방지: ingress 설정이 `internal-and-cloud-load-balancing`인지 확인
  ```bash
  gcloud run services describe pillcare \
    --format='value(metadata.annotations["run.googleapis.com/ingress"])'
  ```
- WebSocket + IAP 호환성: Streamlit 버전을 `1.45.x` 이하로 고정 검토 (Tornado 6.5.1 회귀 이슈)

---

## 5. 서비스 계정 (최소 권한)

```bash
# 전용 서비스 계정 생성
gcloud iam service-accounts create pillcare-runner \
  --display-name="PillCare Cloud Run"

# 필요한 역할만 부여
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:pillcare-runner@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"          # Vertex AI 호출

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:pillcare-runner@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"     # GCS DB 다운로드
```

---

## 6. CI/CD: GitHub Actions

### Workload Identity Federation 설정

키 파일 대신 OIDC 토큰 사용 (short-lived, 자동 만료).

```bash
# 1. Workload Identity Pool 생성
gcloud iam workload-identity-pools create "github" \
  --location="global" \
  --display-name="GitHub Actions Pool"

# 2. OIDC Provider 생성
gcloud iam workload-identity-pools providers create-oidc "github-actions" \
  --location="global" \
  --workload-identity-pool="github" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository_id=assertion.repository_id,attribute.ref=assertion.ref" \
  --attribute-condition="assertion.repository_id=='REPO_ID' && assertion.ref=='refs/heads/main'"

# 3. 배포용 서비스 계정에 역할 부여
gcloud iam service-accounts create pillcare-deployer \
  --display-name="PillCare CI/CD Deployer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:pillcare-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.developer"              # run.admin 대신 (최소 권한)

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:pillcare-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:pillcare-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
```

### GitHub Actions Workflow

```yaml
name: CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  REGION: asia-northeast3
  PROJECT_ID: ${{ vars.GCP_PROJECT_ID }}
  SERVICE: pillcare
  IMAGE: asia-northeast3-docker.pkg.dev/${{ vars.GCP_PROJECT_ID }}/pillcare/app

jobs:
  lint-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --frozen
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run pytest --tb=short

  build-deploy:
    needs: [lint-test]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
    steps:
      - uses: actions/checkout@v4

      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ vars.WIF_PROVIDER }}
          service_account: ${{ vars.DEPLOYER_SA }}

      - run: gcloud auth configure-docker ${{ env.REGION }}-docker.pkg.dev --quiet

      - uses: docker/setup-buildx-action@v3

      - uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: ${{ env.IMAGE }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - uses: google-github-actions/deploy-cloudrun@v2
        with:
          service: ${{ env.SERVICE }}
          image: ${{ env.IMAGE }}:${{ github.sha }}
          region: ${{ env.REGION }}
```

### GitHub 보안

- 모든 third-party action은 **SHA 고정** 권장 (태그 대신)
- `permissions`는 job 레벨에서 최소로 설정 (`contents: read`, `id-token: write`)
- PR에서는 lint-test만 실행, deploy는 main push에서만

---

## 7. 로깅 및 모니터링

### Cloud Logging 통합

Python `logging` 모듈을 JSON 포맷으로 설정하여 Cloud Logging에 구조화된 로그 전송.

```python
import logging
import json

class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "severity": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        })

handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "WARNING"), handlers=[handler])
```

**개인정보 보호**: LOG_LEVEL=WARNING으로 설정하여 사용자 쿼리(투약 이력)가 로그에 남지 않도록 함.

### 비용 알림

```bash
# GCP Budget Alert 설정 ($50/월 한도)
gcloud billing budgets create \
  --billing-account=$BILLING_ACCOUNT \
  --display-name="PillCare POC" \
  --budget-amount=50 \
  --threshold-rule=percent=80 \
  --threshold-rule=percent=100
```

### LangGraph 안전장치

- `recursion_limit` 명시 (기본 25, 무한 루프 방지)
- 앱 레벨 rate limit: 사용자당 일 100건 제한 검토

---

## 8. 비용 예상 (월간, 소규모 사용)

| 항목 | 예상 비용 |
|------|----------|
| Cloud Run (min=0, 5-10 사용자, 30분/일) | ~$7-10 |
| GCS (100MB 저장 + 다운로드) | ~$0 |
| Artifact Registry (이미지 저장) | ~$0 |
| Vertex AI Gemini 2.5 Flash | ~$5-15 (사용량 비례) |
| IAP | 무료 |
| Budget Alert | 무료 |
| **합계** | **~$12-25/월** |

---

## 9. 확장 경로

```
현재 (POC):
  로컬 DB 빌드 → GCS 수동 업로드 → Cloud Run 수동 배포
  단일 리전, min=0, max=2

향후 (Production):
  Cloud Scheduler → Cloud Run Job (크롤링+빌드) → GCS 자동 업로드
  Cloud Run 자동 반영 (새 DB 감지)
  다중 리전, min=1, Cloud SQL 전환 검토
  LLM: Claude ↔ Gemini A/B 테스트 (Structured Output로 모델 교체 1줄)
```

---

## 10. GCP 서비스 활성화 체크리스트

```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com \
  storage.googleapis.com \
  iap.googleapis.com \
  cloudbuild.googleapis.com
```

---

## 11. UI 면책 문구 (개인정보보호법 대응)

앱 메인 화면에 표시:

> 이 서비스는 의료 행위가 아니며, 전문 의료인의 상담을 대체하지 않습니다.
> 제공되는 정보는 공개된 식약처 데이터를 기반으로 하며, 개인의 건강 상태에 따라 다를 수 있습니다.
