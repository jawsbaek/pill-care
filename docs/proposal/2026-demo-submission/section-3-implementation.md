# §3 구현 방법 및 계획 (P4)

## 3.1 구현 범위 (W1-W6)

| # | 세부업무 | 담당 기술 / 산출물 | 주요 도전 | 주담당 |
|:-:|---|---|---|:-:|
| W1 | **공인 데이터 허브 ETL** | Python 3.14·uv·SQLite+FTS5·식약처 3종+HIRA DUR 8종+KAERS+회수·성분 동의어 사전 | DUR 8종 스키마 정규화, 실시간 차단, 동의어 800+ 쌍 | 주현 |
| W2 | **약물 매칭 엔진** | 4계층 매칭(EDI→Exact→FTS5→rapidfuzz)·N×N DUR·매칭 신뢰도 | 제형·함량 noise, 오탈자, false-negative 방지, min_score 85 튜닝 | 주현 |
| W3 | **LangGraph 6-Node 파이프라인** | LangGraph 1.1.6·Gemini 2.5 Flash·Claude 4.6 fallback·Haiku 4.5 critic·Pydantic Structured Output·CRITICAL 재시도 | Critic judge 평가 기준, 멀티 프로바이더 스키마 동등성 | 상훈 |
| W4 | **Evidence Tier + 5-Layer Guardrail** | MedConf S/M/C 태깅+T1/T4 계층+금칙어+DUR 커버리지([CRITICAL])+종결+KURE-v1 의도 분류기(≥0.70) | paraphrase 우회 차단, Critic drop 임계값, DUR 커버리지 재시도 루프 | 상훈+주현 |
| W5 | **AI Harness (관측·평가·CI)** | Langfuse·RAGAS·600 한국어 복약 gold set·GitHub Actions 3-gate | 약사 검수 일정, LLM-as-judge κ≥0.7, RAGAS 한국어 judge 튜닝 | 주현+상훈 |
| W6 | **Streamlit UI + Cloud Run** | Streamlit 1.45·XLS 업로드+출처 태그+DUR 경고·Docker·Artifact Registry·Workload Identity+IAP·CI/CD | 어르신 UI, XLS 오류 복구, cold-start, IAP 권한 | 민지+서희 |

**병렬성**: W1·W2 순차(M1) · W3·W4 병렬(M2) · W5·W6 M2말~M3 진행.

## 3.2 구현 계획 (6개월 · 4-마일스톤)

| 마일스톤 | 기간 | 산출물 | 위험 지점 |
|:-:|---|---|---|
| **M1 기반** | W1-W6 | W1-W2 데이터 허브·매칭 엔진, W3 LangGraph 초기, W4 4-layer guardrail 기초, W6 Cloud Run 배포+CI/CD | 잔여 정규화 튜닝 |
| **M2 데모 제출(예선)** | W7-W12 | W3 Critic 노드 + W4 Evidence Tier + 5-Layer Guardrail(의도 분류기) + W5 Langfuse+RAGAS+gold 200+red-team 10 + HIRA DUR 8종 + 제안서 5p + 3분 영상 | Critic 품질 튜닝, 의도 분류기 임계값, 영상 일정 |
| **M3 결선 전반** | W13-W18 | Gold 200→600·MedHallu KR subset 50·RxNorm+DailyMed ATC 브리지·red-team 20 CI·출처 태그 UI 고도화 | ATC 49% 공백 보완, RxNorm 월간 인프라, 약사 검수 |
| **M4 결선 후반** | W19-W24 | 마이데이터 연동(건강정보고속도로)·출처 인용 UI·Gemini vs Claude A/B·파트너십(약사회·NIA) 논의·발표 자료 | 마이데이터 API 공개 일정, 시연 환경 |

## 3.3 기술 스택 (4 레이어)

**① Frontend** — Streamlit 1.45 (Python 3.14) + KWCAG 2.2 AA 목표

**② Agent / Backend** — Python 3.14 + uv · LangGraph 1.1.6 · Gemini 2.5 Flash (Vertex AI asia-northeast3, 주) · Claude Sonnet 4.6 (Fallback) · Claude Haiku 4.5 (Critic 10% 샘플) · Pydantic 2.13 (json_schema)

**③ Data / Retrieval / Safety** — SQLite + FTS5 trigram · rapidfuzz 3.14.5 · 성분 동의어 사전 · KURE-v1 의도 분류기 (HF 캐시 ~400MB, fail-open) · [데모] 식약처 3종 + HIRA DUR 8종 + KAERS · [결선] + RxNorm RRF + DailyMed SPL + ATC 브리지

**④ Observability / Evaluation / CI·CD** — Langfuse (@observe) · RAGAS (faithfulness·context precision·answer relevance) · 600 케이스 gold set (자체 구축 목표) · pytest + pytest-cov · GitHub Actions (ruff·pytest·build·deploy) · Docker · GCP Artifact Registry + Cloud Run + Workload Identity + IAP + Secret Manager

## 3.4 보유 시설·장비

본 기술은 클라우드 기반 소프트웨어 서비스이며, 팀이 보유한 전용 시설·장비는 없다.
