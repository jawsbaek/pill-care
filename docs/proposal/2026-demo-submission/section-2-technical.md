# §2 기술 상세 (P2-P3)

## 2.1 기술 목적

2025년 6월 국민건강보험공단 집계에 따르면 만성질환과 함께 10종 이상의 약을 60일 이상 복용하는 환자는 **171만 7천여 명** (65세 이상 **80.6%**, 2020 대비 **+52.5%**)에 이른다 [1]. 65세 이상 인구는 이미 **41.8%가 5종 이상**, **14.4%가 10종 이상** 약물을 동시 복용하며 [2], OECD 기준 75세 이상 다제병용 처방률은 **64.2%** (2021)로 OECD 평균 50.1%를 크게 웃돈다 [3]. 만성질환자는 **1,880만 명**, 연간 진료비 **34.5조 원** 규모이며 [4], 5종 이상 복용군은 입원 위험 **+18%**, 사망 위험 **+25%**, 11종 이상에서 각각 **+45%, +54%** 로 상승한다 [2].

공공 DUR 시스템은 금기·중복 점검과 투약이력 조회를 제공할 뿐, 누적 처방 이력과 현재 복용 조합을 통합 해석하지 못한다. 다른 날짜·진료과·약국에서 처방된 약물 간 상호작용은 구조적 **사각지대**로 남아 있어, 한국 대학병원 응급실 방문의 **3.5%가 약물 이상반응**이며 이 중 **15.3%는 예방 가능**했다 [5]. 2025년 국내 의약품 이상사례 보고는 **27만 7천여 건**, 전년 대비 **+9.4%** [6].

이러한 공백을 범용 LLM이 메우려 하지만 구조적으로 오정보 생성(hallucination)을 차단할 수 없다. MedHallu 벤치마크(EMNLP 2025)에서 GPT-4o는 의료 hard tier F1 **0.625**에 그쳤고 [7], Ren et al.(2026) 멀티턴 벤치에서는 기존 신뢰도 추정 기법의 AUROC가 **랜덤 수준(0.5)까지 붕괴**하는 불안정성이 확인되었다 [8]. 복약 정보는 국가별 허가 기준과 약물 상호작용에 따라 결과가 크게 달라지는 **고위험 도메인**이며, 신뢰도를 담보하지 못하는 AI는 오히려 환자 안전에 위협이다.

따라서 본 기술은 만성질환·다약제 복용 환자가 약국 밖에서 복약 중 이상 증상을 경험할 때, 식약처 허가정보·한국의약품안전관리원 DUR·HIRA 약제급여목록 등 대한민국 공인 의약품 데이터와 국제 약학 표준(결선 RxNorm·DailyMed)에 근거해 **복용 중인 약물과의 연관 가능성 정보를 즉시 안내**하는 AI 기반 복약 정보 안내 서비스다. **AI harness**가 모든 응답을 공인 데이터에 근거하도록 강제하며, 대한민국 비의료기기(웰니스) 경계 및 식약처 생성형 AI 의료기기 허가·심사 가이드라인(2025-01-24)에 부합한다. LangGraph 기반 에이전트 오케스트레이션으로 복약 맥락을 단계적으로 수집하고, **출처 계층(T1 공공 / T4 AI 보조)과 함께 인용·통합·안내**한다. 진단·처방·복용 변경 판단은 제공하지 않는다.

> *필케어는 기록하고, 통합하고, 인용하고, 안내한다. 판단하지 않는다.*

---

[1] NHIS 2025-06 보도자료 · [2] Front. Pharmacol. 2022 (NHIS 전수분석) · [3] OECD Health at a Glance 2025 · [4] 건강보험통계연보 2024 (HIRA) · [5] PLOS ONE 2022 · [6] 한국의약품안전관리원 연보 2026 · [7] arXiv:2502.14302 · [8] arXiv:2601.15645

## 2.2 기술구조 (5 레이어 × AI Harness)

```
┌── AI Harness (GitHub Actions + Langfuse + RAGAS 3-gate CI) ───────┐
│ ┌─────────────────────────────────────────────────────────────┐  │
│ │ ① 입력 — 심평원 "내가 먹는 약" XLS (암호화)                  │  │
│ │    msoffcrypto 복호화 → MedRecord[] (약물·용량·진료과)       │  │
│ ├─────────────────────────────────────────────────────────────┤  │
│ │ ② 공인 데이터 허브 (SQLite + FTS5)                           │  │
│ │   [데모] 식약처 3종 + HIRA DUR 8종 + KAERS + 회수/판매중지   │  │
│ │   [결선] + RxNorm RRF + DailyMed SPL (ATC 브리지)            │  │
│ │   매칭: EDI → Exact → FTS5 trigram → rapidfuzz + 성분 사전  │  │
│ ├─────────────────────────────────────────────────────────────┤  │
│ │ ③ LangGraph 6-Node 파이프라인                                │  │
│ │   match → dur → collect → generate (Evidence Tier)           │  │
│ │         → critic (LLM-as-judge, 10% 샘플) → verify           │  │
│ │         → CRITICAL? retry (≤2)                               │  │
│ ├─────────────────────────────────────────────────────────────┤  │
│ │ ④ 5-Layer Guardrail                                          │  │
│ │   금칙어 · 출처 계층 · DUR 커버리지 · 종결 문구              │  │
│ │   · 의도 분류기 (KURE-v1 임베딩 ≥0.70)                       │  │
│ ├─────────────────────────────────────────────────────────────┤  │
│ │ ⑤ Streamlit → Cloud Run (Workload Identity + IAP + CI/CD)    │  │
│ └─────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

**설계 의도**: AI Harness 외곽 박스로 관측·평가·CI 전 구간 내장. ② 데이터 허브가 시각적 중심(§1.7③ 증명). ③ 6-Node는 Deterministic 4 + LLM 2로 안전성·생성 책임 분리.

## 2.3 주요 기능 (5 모듈)

| # | 모듈 | 핵심 기능 | 입력 → 출력 |
|:-:|---|---|---|
| M1 | 심평원 투약이력 파서 | 암호화 XLS 복호화·파싱 ("내가 먹는 약 한눈에" 호환) | XLS → MedRecord[] |
| M2 | 공인 데이터 허브 | 식약처 3종 + HIRA DUR 8종 + KAERS + 회수 통합 SQLite+FTS5, 4계층 매칭, N×N DUR | 약물명 → 구조화 약물·DUR 경고 |
| M3 | LangGraph 6-Node 추론 | Deterministic 3 + LLM(Gemini 2.5 Flash/Claude 4.6) + Critic(Haiku 4.5) + Verify. CRITICAL 자동 재시도 | MedRecord[] → 출처 태그 응답 |
| M4 | Evidence-Grounded 생성기 | MedConf Supported/Missing/Contradictory 태깅 + T1 공공 / T4 AI 계층. Missing/Contradictory 자동 드롭 | Draft + evidence → grounded 응답 |
| M5 | 5-Layer Guardrail + Eval | 금칙어·출처·DUR·종결·의도(KURE-v1 ≥0.70) + Langfuse·RAGAS·600 gold set | 응답 → 통과/재시도/escalate |

## 2.4 결과물 형상

| 구성 요소 | 형태 |
|---|---|
| 필케어 웹 | Streamlit 1.45 (Python 3.14) |
| 추론 엔진 | LangGraph 1.1.6 + Gemini 2.5 Flash + Claude 4.6 fallback + Haiku 4.5 critic |
| 데이터 허브 | SQLite + FTS5 + 성분 동의어 사전 (5,206 쌍) |
| AI Harness | Langfuse + RAGAS + 600 케이스 gold set + GitHub Actions 3-gate |
| 배포 | Cloud Run + Workload Identity + IAP + CI/CD |

결선 추가: RxNorm RRF · DailyMed SPL · ATC 브리지.

## 2.5 배포 방식

- **데모(예선)**: Cloud Run 공개 URL (IAP) + GitHub Actions CI/CD + 비공개 저장소 + 스크린샷·영상
- **결선**: Cloud Run + OAuth + 건강정보고속도로 마이데이터 연동 + 영상 고도화
- **Phase 3 (상용)**: 모바일 네이티브 앱, B2B Agent API, 의료기관·약국·PBM 연동

## 2.6 혁신적 요소

**A. Deterministic DUR + Grounded LLM Hybrid** — 안전 판단(HIRA DUR 8종)은 SQL 결정론, 자연어는 LLM Structured Output으로 분리. Verify 노드가 DUR 커버리지 강제. MedAgentBoard (NeurIPS 2025) 실증 정합.

**B. Evidence Tier Tagging (MedConf 차용)** — 모든 claim에 Supported/Missing/Contradictory 3-way 태그 + T1/T4 출처 계층. Missing·Contradictory는 Critic에서 자동 드롭. Ren et al.(2026) 근거 기반 프레임워크를 한국 복약 도메인에 적용.

**C. AMIE-style LLM-as-judge Critic Node** — Claude Haiku 4.5가 독립 judge로 DUR 커버리지·인용 완전성·금지 표현 재평가. CRITICAL 시 자동 재시도. 10% 샘플링으로 비용 통제. AMIE (Nature Medicine 2025) 차용.

**D. 5-Layer Guardrail + Intent Classifier** — 금칙어 regex + 출처 계층 (T1/T4) + DUR 커버리지 [CRITICAL] + 필수 종결 문구 + KURE-v1 임베딩 의도 분류기(≥0.70)의 5중 방어. Lakera 2024 벤치에서 단어 기반 필터는 paraphrase 공격에 **60-90%** 우회되므로, 임베딩 유사도 기반 의도 분류기가 "복용량을 줄이세요" 류 clinician-voice 우회를 의미 수준에서 차단한다. MedHallu(EMNLP 2025)의 correctness-vs-faithfulness 분리 주장에 부합하여, 본 guardrail은 faithfulness(출처 근거 유지)를 강제하고 correctness(의학적 사실성)는 Critic 노드의 10% 샘플링 재검증에 위임한다. NLI entailment 게이트는 drug-scoped retrieval 인프라가 선행돼야 correctness 보장이 가능하다는 구조적 한계로 v2 본 데모에서는 제외했다 (결선 단계 재도입 후보).

**E. AI Harness — 관측·평가·CI 전 구간 내장** — Langfuse trace + RAGAS + 600 gold set + GitHub Actions 3-gate. "재현 가능한 평가 증거"를 프로덕션 기본 설비로 내장. KorMedMCQA가 커버하지 못하는 한국어 DUR 평가 축 자체 구축.

## 2.7 도전적 요소

**① MedHallu F1 0.625** [arXiv:2502.14302] — GPT-4o도 의료 hard tier에서 F1 0.625. 필케어는 Evidence Tier + Critic 재검증 + 의도 분류기 3축 대응.

**② Ren et al.(2026) 멀티턴 신뢰도 AUROC 붕괴** [arXiv:2601.15645] — 기존 기법 AUROC가 랜덤 수준(0.5)까지 붕괴. 근거 기반 프레임워크 필요. 필케어는 RAG 근거 매핑(S/M/C) + Critic 재검증 2-stage로 대응.

**③ LLM 인용 57% Post-Rationalization** [arXiv:2412.18004] — 필케어는 Evidence Tier(Supported/Missing/Contradictory) + Critic 재검증 + 의도 분류기 3축 검증을 응답 스키마에 강제.

**④ 한국어 의료 벤치 공백** [KorMedMCQA, arXiv:2403.01469] — 한국어 점수가 MedQA와 상관 낮음. 필케어는 DUR 200 + 문구 120 + red-team 100 + 자연스러움 80 + 증상매핑 100 = **600 케이스 한국어 복약 평가 gold set** 자체 구축 목표.

**⑤ 한국 처방 파편화 × 다기관 DUR 사각지대** — 한국 외래 연 18회 · 약국 단위 DUR만 존재. 필케어는 HIRA DUR 8종 + 식약처 + KAERS를 SQLite 허브로 통합, `match → check_dur (N×N 성분쌍)` 결정론 파이프라인으로 폐쇄.

**⑥ 비의료기기(웰니스) 규제 경계 + 의미 우회 방어** — 식약처 생성형 AI 의료기기 가이드라인(2025)에 따라 판단·진단·처방 배제 필수. 필케어는 regex 금칙어 + 출처 계층(T1/T4) + DUR 커버리지 + 종결 문구 + KURE-v1 의도 분류기 5계층에 Critic 재검증(10% 샘플)을 더해 "판단하지 않는다" 원칙을 의미 수준에서 방어.
