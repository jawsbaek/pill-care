# PillCare GCP 배포 런북 (Deployment Runbook)

## 목표

PillCare 코드가 main에 머지된 상태에서 실제 GCP 환경에 배포하고, 팀원이 접속하여 테스트할 수 있는 상태까지 완성한다.

## 전제 조건

- GCP 프로젝트 1개 (billing 활성화)
- `gcloud` CLI 설치 및 인증 완료
- GitHub 리포지토리: `jawsbaek/pill-care`
- 로컬에 빌드된 `data/pillcare.db` (또는 빌드 가능한 원본 데이터)

---

## Phase 1: GCP 프로젝트 초기 설정

### 1.1 API 활성화

```bash
PROJECT_ID=<your-project-id>

gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  aiplatform.googleapis.com \
  storage.googleapis.com \
  iap.googleapis.com \
  iam.googleapis.com \
  --project=$PROJECT_ID
```

### 1.2 Artifact Registry 생성

```bash
gcloud artifacts repositories create pillcare \
  --repository-format=docker \
  --location=asia-northeast3 \
  --description="PillCare Docker images" \
  --project=$PROJECT_ID
```

### 1.3 서비스 계정 생성

**Cloud Run 실행용:**
```bash
gcloud iam service-accounts create pillcare-runner \
  --display-name="PillCare Cloud Run Runner" \
  --project=$PROJECT_ID

# Vertex AI 호출 권한
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:pillcare-runner@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

# GCS 읽기 권한
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:pillcare-runner@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"
```

**CI/CD 배포용:**
```bash
gcloud iam service-accounts create pillcare-deployer \
  --display-name="PillCare CI/CD Deployer" \
  --project=$PROJECT_ID

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:pillcare-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.developer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:pillcare-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:pillcare-deployer@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"
```

---

## Phase 2: Workload Identity Federation (GitHub Actions)

### 2.1 WIF Pool + Provider 생성

```bash
# GitHub 리포지토리 ID 확인
REPO_ID=$(gh api repos/jawsbaek/pill-care --jq '.id')

# Pool 생성
gcloud iam workload-identity-pools create github \
  --location=global \
  --display-name="GitHub Actions Pool" \
  --project=$PROJECT_ID

# OIDC Provider 생성
gcloud iam workload-identity-pools providers create-oidc github-actions \
  --location=global \
  --workload-identity-pool=github \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository_id=assertion.repository_id,attribute.ref=assertion.ref" \
  --attribute-condition="assertion.repository_id=='$REPO_ID'" \
  --project=$PROJECT_ID
```

### 2.2 SA 바인딩

```bash
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')

gcloud iam service-accounts add-iam-policy-binding \
  pillcare-deployer@$PROJECT_ID.iam.gserviceaccount.com \
  --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/github/attribute.repository_id/$REPO_ID" \
  --role="roles/iam.workloadIdentityUser" \
  --project=$PROJECT_ID
```

### 2.3 GitHub Repository Variables 설정

GitHub Settings > Secrets and variables > Actions > Variables 에서:

| Variable | Value |
|----------|-------|
| `GCP_PROJECT_ID` | `<your-project-id>` |
| `WIF_PROVIDER` | `projects/<PROJECT_NUMBER>/locations/global/workloadIdentityPools/github/providers/github-actions` |
| `DEPLOYER_SA` | `pillcare-deployer@<PROJECT_ID>.iam.gserviceaccount.com` |

---

## Phase 3: 데이터베이스 준비 (GCS)

### 3.1 GCS 버킷 생성

```bash
gcloud storage buckets create gs://pillcare-data-$PROJECT_ID \
  --location=asia-northeast3 \
  --uniform-bucket-level-access \
  --project=$PROJECT_ID
```

### 3.2 DB 빌드 및 업로드

```bash
# 로컬에서 DB 빌드 (원본 데이터 필요)
uv run python -m pillcare.db_builder

# SHA256 계산
DB_SHA256=$(shasum -a 256 data/pillcare.db | awk '{print $1}')
echo "DB_SHA256=$DB_SHA256"

# GCS 업로드
gcloud storage cp data/pillcare.db gs://pillcare-data-$PROJECT_ID/pillcare.db
```

---

## Phase 4: 첫 배포 (수동)

CI/CD가 동작하기 전에 수동으로 첫 배포를 수행한다.

### 4.1 Docker 이미지 빌드 및 푸시

```bash
# Docker 인증
gcloud auth configure-docker asia-northeast3-docker.pkg.dev --quiet

# 빌드
docker build --platform linux/amd64 -t asia-northeast3-docker.pkg.dev/$PROJECT_ID/pillcare/app:v1 .

# 푸시
docker push asia-northeast3-docker.pkg.dev/$PROJECT_ID/pillcare/app:v1
```

### 4.2 Cloud Run 배포

```bash
gcloud run deploy pillcare \
  --image=asia-northeast3-docker.pkg.dev/$PROJECT_ID/pillcare/app:v1 \
  --region=asia-northeast3 \
  --memory=2Gi \
  --cpu=1 \
  --concurrency=1 \
  --min-instances=0 \
  --max-instances=2 \
  --timeout=600 \
  --no-allow-unauthenticated \
  --cpu-boost \
  --service-account=pillcare-runner@$PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars="GCS_BUCKET=pillcare-data-$PROJECT_ID,GCS_BLOB=pillcare.db,DB_SHA256=$DB_SHA256,LOG_LEVEL=WARNING,GCP_PROJECT_ID=$PROJECT_ID,GCP_REGION=asia-northeast3,LLM_PROVIDER=gemini" \
  --project=$PROJECT_ID
```

---

## Phase 5: 접근 제어

### Option A: IAP (추천 — 보안 강화)

```bash
# Cloud Run에 IAP 활성화
gcloud run services update pillcare \
  --region=asia-northeast3 \
  --iap \
  --project=$PROJECT_ID

# 사용자 권한 부여
gcloud beta iap web add-iam-policy-binding \
  --member=user:<gmail-address> \
  --role=roles/iap.httpsResourceAccessor \
  --region=asia-northeast3 \
  --resource-type=cloud-run \
  --service=pillcare \
  --project=$PROJECT_ID
```

**주의**: gmail.com 외부 사용자는 OAuth consent screen 설정 필요.

### Option B: Public Access (빠른 POC 테스트)

```bash
gcloud run services update pillcare \
  --region=asia-northeast3 \
  --allow-unauthenticated \
  --project=$PROJECT_ID
```

이 경우 ci-cd.yml에서 `--no-allow-unauthenticated` 제거 필요.

---

## Phase 6: 검증

### 6.1 서비스 URL 확인

```bash
gcloud run services describe pillcare \
  --region=asia-northeast3 \
  --format='value(status.url)' \
  --project=$PROJECT_ID
```

### 6.2 Health Check

```bash
# IAP 없는 경우
curl -s https://<SERVICE_URL>/_stcore/health

# IAP 있는 경우 — 브라우저에서 직접 접속
```

### 6.3 기능 테스트 체크리스트

- [ ] 브라우저에서 서비스 URL 접속
- [ ] 면책 문구 표시 확인
- [ ] XLS 파일 업로드 + 비밀번호 입력
- [ ] "분석 시작" 버튼 클릭
- [ ] 파이프라인 실행 완료 (약물 매칭 → DUR 체크 → 복약 정보 생성)
- [ ] DUR 병용금기 경고 표시 확인
- [ ] 상세 복약 정보 섹션별 표시 + source_tier 태그
- [ ] 핵심 요약 표시
- [ ] 오류 없이 완료

---

## Phase 7: CI/CD 활성화

Phases 1-6 완료 후, GitHub Actions CI/CD가 자동으로 동작한다.

- `main` 브랜치 push → lint + test → Docker build → Cloud Run deploy
- PR → lint + test only

### GitHub Actions Variables 업데이트

ci-cd.yml의 env_vars에 GCS 설정이 없으므로, Cloud Run 서비스에 직접 설정한 환경변수가 유지된다. 코드 배포 시 환경변수는 덮어쓰지 않으므로 Phase 4에서 설정한 값이 계속 사용된다.

---

## DB 업데이트 프로세스

데이터 갱신 시:

```bash
# 1. 크롤링 + DB 재빌드
uv run python -m pillcare.db_builder

# 2. SHA256 계산
NEW_SHA=$(shasum -a 256 data/pillcare.db | awk '{print $1}')

# 3. GCS 업로드
gcloud storage cp data/pillcare.db gs://pillcare-data-$PROJECT_ID/pillcare.db

# 4. Cloud Run 환경변수 업데이트
gcloud run services update pillcare \
  --region=asia-northeast3 \
  --set-env-vars="DB_SHA256=$NEW_SHA" \
  --project=$PROJECT_ID
```

Cloud Run 인스턴스는 다음 콜드스타트 시 새 DB를 자동으로 다운로드한다.

---

## 비용 모니터링

```bash
# Budget Alert 설정 ($50/월)
gcloud billing budgets create \
  --billing-account=<BILLING_ACCOUNT_ID> \
  --display-name="PillCare POC" \
  --budget-amount=50USD \
  --threshold-rule=percent=0.8 \
  --threshold-rule=percent=1.0
```

---

## 문제 해결

| 증상 | 원인 | 해결 |
|------|------|------|
| 403 Forbidden | IAP 미설정 또는 권한 없음 | Phase 5 확인 |
| DB not found | GCS 환경변수 미설정 | `GCS_BUCKET` 확인 |
| LLM 호출 실패 | Vertex AI API 미활성화 또는 SA 권한 없음 | Phase 1.1, 1.3 확인 |
| Docker push 실패 | AR 미생성 또는 인증 실패 | Phase 1.2, 2.3 확인 |
| 콜드스타트 느림 (>30s) | min-instances=0 + GCS 다운로드 | min-instances=1 고려 |
