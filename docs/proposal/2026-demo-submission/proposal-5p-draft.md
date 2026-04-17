# 필케어 (PillCare) — 제안서 초안 (5p, 데모 제출용)

> **공인 데이터 기반 grounded 복약 정보 안내 AI 에이전트**
> 작성일: 2026-04-17 / 근거: `docs/superpowers/specs/2026-04-17-pillcare-proposal-v2-design.md`

**본 초안 = `section-1-overview.md` + `section-2-technical.md` + `section-3-implementation.md` 순차 결합. PDF 조판 시 5페이지 강제 준수 확인 필요.**

---

## P1 — §1 기술 개요 + §2.1 도입부

### 1.1 기술명
**필케어 (PillCare)** — 공인 데이터 기반 grounded 복약 정보 안내 AI 에이전트

### 1.2 하드웨어 포함 여부
**미포함** — 순수 소프트웨어 서비스(웹 브라우저 기반). 로봇·자율주행·드론 등 물리시스템과 결합하지 않는다.

### 1.3 활용분야
전문 분야 5개 — **의료·헬스케어, 복약안전(DUR), 만성질환 관리, 환자 교육, 고령층 자가 건강관리**.

- **1차 타겟**: 2025-06 기준 10종+60일+ 복용자 **171만 7천여 명** (65세+ 80.6%, 2020 대비 +52.5%)
- **수요 환경**: 외래진료 연 18회 (OECD 평균 약 3배)
- **확장 경로**: 한국 → 일본·대만 → EU/US senior care

### 1.4 기술성숙도 — 시작품 단계
본 제안의 통합 아키텍처는 **시작품 단계** (파일롯 규모 시작품 + Cloud Run 공개 시연 + 200 gold set 현장 검증). 구성 기술은 대부분 제품화되어 있다.

| 구성 요소 | 단계 |
|---|---|
| 공인 데이터 허브 (식약처 3종 + HIRA DUR 8종 + KAERS + 회수) | 제품화 |
| SQLite + FTS5 trigram 검색 | 제품화 |
| LangGraph 기반 에이전트 파이프라인 (v1.1.6) | 제품화 |
| Gemini 2.5 Flash / Claude Sonnet 4.6 Structured Output | 제품화 |
| KURE-v1 임베딩 (Ko-MTEB 2025 SOTA) | 제품화 |
| Evidence Tier Tagging (MedConf 차용) · LLM-as-judge Critic (AMIE 차용) | 시작품 |
| GCP Cloud Run + Workload Identity + CI/CD | 제품화 |
| **통합 아키텍처 (본 제안)** | **시작품** |

### 1.5 도입 수준 — 도입 전
**본 기술: 도입 전** (2026-04 현재 Cloud Run 공개 데모·시연 단계, 상용 사용자·고객사 없음).

참고: 국내 규칙 기반 복약 앱(약올림·필로우 등)은 **도입 증가** 구간이나, HIRA DUR 8종 + Structured Output + 출처 계층 + LLM-as-judge critic을 결합한 **grounded 복약 에이전트는 공개 선행 사례 미확인**.

### 1.6 유사 기술
**국내**
- 규칙 기반 복약 알림 앱 — 약올림 · 필로우 · 올라케어 (복약 알림·기본 DB 조회)
- 범용 의료 LLM 서비스 — 카카오 케어챗 · 닥터나우 AI (비대면 상담·범용 질의응답)
- 공공 약물 조회 — HIRA '내가 먹는 약 한눈에' (경쟁자 아닌 **데이터 파트너**, 2025 하반기 건강정보고속도로 1,263개소 확대)

**해외**
- 범용 LLM 의료 모드 — OpenAI ChatGPT Health · Google Gemini · Ada Health (소비자 Q&A)
- 의료 에이전트 연구 — Google AMIE · MedAgentBoard (진단·대화형, 연구 단계)
- 복약 리마인더 앱 — Medisafe Care · MyTherapy (리마인더 + 일부 GenAI Q&A)

### 1.7 차별점
① **Deterministic DUR + Grounded LLM 하이브리드** — 안전 판단은 SQL 결정론, 설명만 LLM Structured Output (MedAgentBoard NeurIPS 2025 정합)
② **멀티-과·약국 통합 DUR** — HIRA 8종 + N×N 성분쌍으로 171만 명 사각지대 해소
③ **한국 공공 데이터 완전 통합 + 국제 브리지** — 데모: 식약처+HIRA+KAERS+회수 / 결선: RxNorm+DailyMed
④ **Zero-License-Risk Stack** — KOGL Type 1 · Public Domain · CC0만 사용, DrugBank(CC BY-NC) 등 상용 DDI 배제
⑤ **AI Harness** — 6-Layer Guardrail(금칙어·출처·DUR·종결·NLI ≥0.75·의도 ≥0.70) + Langfuse + RAGAS + 600 gold set + GitHub Actions 3-gate

### 2.1 기술 목적 (도입부)
공공 DUR은 약국 단위 일회성 체크에 머물러 다기관 처방 간 상호작용은 **사각지대**로 남아 있고, ED 방문의 3.5%가 약물 이상반응·그중 **15.3% 예방 가능**. 범용 LLM은 구조적으로 환각 차단이 불가능해(MedHallu F1 0.625, Ren et al. 2026 AUROC 랜덤 붕괴) 고위험 복약 도메인에선 환자 안전 위협이 된다.

따라서 **AI harness가 공인 데이터 근거 응답만 강제**하고 LangGraph 에이전트가 복약 맥락을 단계적 수집·**출처 계층(T1 공공 / T4 AI)과 함께 인용·통합·안내**한다. 판단·진단·처방은 배제한다.

> *필케어는 기록하고, 통합하고, 인용하고, 안내한다. 판단하지 않는다.*

---

## P2 — §2.2 기술구조 + §2.3 주요 기능

### 2.2 기술구조
5-layer × AI Harness 외곽 다이어그램 — `section-2-technical.md#22-기술구조-5-레이어-x-ai-harness` 참조. 핵심: SQLite + FTS5 허브, LangGraph 6-Node (match→dur→collect→generate→critic→verify), 5-Layer Guardrail.

### 2.3 주요 기능 (5 모듈)
| # | 모듈 | 핵심 기능 |
|:-:|---|---|
| M1 | 심평원 투약이력 파서 | 암호화 XLS 복호화·MedRecord 구조화 |
| M2 | 공인 데이터 허브 | 식약처 3종+HIRA DUR 8종+KAERS+회수 통합 SQLite+FTS5, 4계층 매칭, N×N DUR |
| M3 | LangGraph 6-Node 추론 | Deterministic 3 + LLM(Gemini/Claude) + Critic(Haiku 10% 샘플) + Verify. CRITICAL 재시도 |
| M4 | Evidence-Grounded 생성기 | MedConf S/M/C 태깅 + T1/T4 계층, Missing/Contradictory 자동 드롭 |
| M5 | 5-Layer Guardrail + Eval | 금칙어·출처·DUR(CRITICAL)·종결·의도(KURE-v1 ≥0.70) + Langfuse + RAGAS + 600 gold set |

---

## P3 — §2.4 결과물 · §2.5 배포 · §2.6 혁신 · §2.7 도전

### 2.4 결과물 형상
Streamlit 1.45 웹 · LangGraph 1.1.6 추론 엔진 · SQLite+FTS5 허브 · AI Harness(Langfuse+RAGAS+600 gold set) · Cloud Run 배포.

### 2.5 배포 방식
데모: Cloud Run 공개 URL + IAP + CI/CD · 결선: OAuth + 마이데이터 연동 · Phase 3: 모바일+B2B API.

### 2.6 혁신 A-E
- **A.** Deterministic DUR + Grounded LLM Hybrid (MedAgentBoard NeurIPS 2025)
- **B.** Evidence Tier Tagging (MedConf arXiv:2601.15645)
- **C.** AMIE-style LLM-as-judge Critic (Nature Medicine 2025)
- **D.** 5-Layer Guardrail + KURE-v1 Intent Classifier (≥0.70, paraphrase-bypass 방어)
- **E.** AI Harness — Langfuse + RAGAS + 600 gold set + GitHub Actions 3-gate

### 2.7 도전 ①-⑥
① MedHallu F1 0.625 · ② Ren et al. 2026 AUROC 랜덤 붕괴 · ③ Citation 57% post-rationalization · ④ 한국어 의료 벤치 공백 · ⑤ 한국 처방 파편화 다기관 DUR 사각지대 · ⑥ 비의료기기 웰니스 규제 경계 + 의미 우회 방어.

---

## P4 — §3 구현 방법 및 계획

### 3.1 구현 범위 W1-W6
| # | 세부업무 | 주담당 |
|:-:|---|:-:|
| W1 | 공인 데이터 허브 ETL | 주현 |
| W2 | 약물 매칭 엔진 (4계층 + N×N DUR) | 주현 |
| W3 | LangGraph 6-Node 파이프라인 | 상훈 |
| W4 | Evidence Tier + 5-Layer Guardrail | 상훈+주현 |
| W5 | AI Harness (관측·평가·CI) | 주현+상훈 |
| W6 | Streamlit UI + Cloud Run | 민지+서희 |

### 3.2 구현 계획 (6개월 · 4-마일스톤)
| M | 기간 | 산출물 |
|:-:|---|---|
| M1 기반 | W1-W6 | 데이터 허브·매칭·LangGraph 초기·Cloud Run 배포 |
| M2 데모 제출 | W7-W12 | Critic + Evidence Tier + 5-Layer Guardrail + Langfuse + 200 gold + 제안서 + 영상 |
| M3 결선 전반 | W13-W18 | Gold 200→600 · RxNorm/DailyMed · red-team 20 |
| M4 결선 후반 | W19-W24 | 마이데이터 연동 · Gemini vs Claude A/B · 파트너십 |

### 3.3 기술 스택
**FE**: Streamlit 1.45 (Python 3.14) · **Agent**: LangGraph 1.1.6 + Gemini 2.5 Flash/Claude Sonnet 4.6/Haiku 4.5 critic · **Data/Safety**: SQLite+FTS5 · rapidfuzz · 성분 동의어 · KURE-v1 의도 분류기 (fail-open) · **Obs/CI**: Langfuse · RAGAS · 600 gold set · GitHub Actions · Cloud Run + Workload Identity

### 3.4 보유 시설·장비
본 기술은 클라우드 기반 소프트웨어 서비스이며, 팀이 보유한 전용 시설·장비는 없다.

---

## P5 — 참고 및 팀

### 팀 구성
서희 (UI) · 주현 (데이터/DB) · 민지 (시나리오·콘텐츠) · 상훈 (AI 파이프라인)

### 참조 리서치
- Track 1-6 (문제 검증 · 경쟁자 · 데이터 · 규제 · AI 트렌드 · UDKG+RAG+Agent 딥다이브)
- 15-사이클 적대적 설계 리뷰 (`docs/research/2026-04-17-design-review-synthesis.md`)
- NotebookLM 42개 소스 (arxiv 12 · 국제 DB · 한국 공공 · 식약처 가이드라인)

### 핵심 인용
- MedHallu (arXiv:2502.14302, EMNLP 2025) · MedConf (arXiv:2601.15645, 2026)
- Correctness-vs-Faithfulness (arXiv:2412.18004) · KorMedMCQA (arXiv:2403.01469)
- AMIE (Nature Medicine 2025) · MedAgentBoard (NeurIPS 2025)
- OECD Health at a Glance 2025 · 건강보험통계연보 2024 · Front. Pharmacol. 2022

---

**조판 TODO (사람 작업)**: (1) Markdown → PDF (pandoc 또는 Google Docs) · (2) 5페이지 강제 준수 최종 확인 · (3) §1.6 비교표·§2.2 다이어그램 Figma 시각화 (B5) · (4) §3.2 Gantt 차트 (B5) · (5) POC 실기기 스크린샷 3장 P3 우하단 삽입 (B6 완료 후) · (6) 대회 포털 제출.
