# §1 기술 개요 (P1)

## 1.1 기술명

**필케어 (PillCare)** — 공인 데이터 기반 grounded 복약 정보 안내 AI 에이전트

## 1.2 하드웨어 포함 여부

포함하지 않음. 사용자 기기는 웹 브라우저만 요구한다.

## 1.3 활용분야

범용 의료·헬스케어 — **만성질환·다약제 복용 환자** 대상 복약 정보 안내.

- **1차 타겟**: 2025년 6월 기준 10종 이상·60일 이상 복용자 **171만 7천여 명** (65세 이상 80.6%, 2020 대비 +52.5%) [NHIS 2025]
- **수요 환경**: 외래진료 연 18회 (OECD 평균의 약 3배) [OECD Health at a Glance 2025]
- **확장 경로**: 한국(Phase 1) → 일본·대만(Phase 2) → EU/US senior care(Phase 3)

## 1.4 기술숙성도

| 구성 요소 | 숙성도 |
|---|---|
| 공공 약물 DB (식약처 3종 · HIRA DUR 8종) | 제품화 |
| SQLite + FTS5 trigram 검색 | 제품화 |
| LangGraph 기반 에이전트 파이프라인 (v1.1.6) | 제품화 |
| Gemini 2.5 Flash / Claude Sonnet 4.6 Structured Output | 제품화 |
| DeBERTa-v3 NLI · KURE-v1 임베딩 | 제품화 |
| Evidence Tier Tagging (MedConf 차용) · LLM-as-judge Critic (AMIE 차용) | 시작품 |
| GCP Cloud Run + Workload Identity + CI/CD | 제품화 |
| **통합 아키텍처 (본 제안)** | **시작품(Prototype)** |

> 구성 기술은 대부분 제품화 단계이며, 본 제안의 고유 지점은 이들을 결합한 한국 복약 도메인 grounded 에이전트 아키텍처다.

## 1.5 도입수준

- 규칙 기반 복약 알림·DB 조회 수준 앱 (네이버 헬스케어·약올림): **도입 증가**
- **Deterministic DUR + Grounded LLM 하이브리드 복약 에이전트**: **도입 전 / 도입 초기**
- 국내 소비자 서비스 중 HIRA DUR 8종 완전 적용 + LLM Structured Output + 출처 계층 강제 + LLM-as-judge critic 결합 사례는 공개 확인되지 않는다.

## 1.6 유사기술 비교표

| 서비스 | 타겟 | 약물 DB 소스 | 멀티-과/약국 통합 DUR | AI 추론 방식 | 환각 대응 |
|---|---|---|---|---|---|
| OpenAI ChatGPT Health (2025) | 소비자 | 학습 분포 | ❌ (개인 복약이력 미연동) | 범용 LLM Q&A | ❌ |
| Google MedLM / AMIE | 연구 | 의료 대화 데이터 | ❌ (소비자 미상용) | Multi-turn 진단 | 부분 |
| Ada Health (LLM 통합) | 소비자 | 자체 의료 DB | ❌ (증상 체커) | LLM + 증상 체커 | 부분 |
| Medisafe Care (2024) | 소비자 | 해외 DB | ⚠️ 리마인더 중심 | GenAI Q&A | ❌ |
| 카카오 케어챗 / 닥터나우 AI | 소비자 | 국내(부분) | ❌ | 범용 LLM · 비대면 | 미공개 |
| 네이버 헬스케어·약올림·올라케어 | 소비자 | 국내(부분) | ❌ | 규칙 기반 | N/A |
| **필케어 (본 제안)** | **소비자** | **식약처 3종 + HIRA DUR 8종 + KAERS / +RxNorm·DailyMed(결선)** | ✅ **결정론 N×N 성분쌍 + HIRA DUR 8종 룰** | ✅ **LangGraph 6-node** | ✅ **Evidence Tier + Critic + NLI + 6-layer** |

HIRA '내가 먹는 약 한눈에'는 경쟁자가 아닌 **데이터 파트너**로 포지셔닝 (2025 하반기 건강정보고속도로 1,263개소 확대).

## 1.7 차별점

**① 국내 최초 Deterministic DUR + Grounded LLM 하이브리드**
안전 판단(HIRA DUR 8종)은 SQL 결정론, 자연어 생성은 LLM Structured Output으로 분리. 두 레일이 서로 검증하며 LLM의 DUR 우회 불가. MedAgentBoard (NeurIPS 2025)의 "구조화 약물 태스크에서 단일 에이전트 + 도구 > 멀티 에이전트" 실증과 정합.

**② 능동적 멀티-과·멀티-약국 통합 DUR 추론**
한국은 외래진료 연 18회이지만 약국 단위 일회성 DUR만 존재. 필케어는 사용자의 전체 복약 이력을 단일 SQLite 허브에서 능동 추론 — 성분쌍 N×N 병용금기 + 연령·임부·용량·효능군중복·노인주의 등 8종 룰 — **171만 7천여 명**의 사각지대를 직접 겨냥.

**③ 한국 공공 데이터 완전 통합 + 국제 표준 브리지**
데모: 식약처 3종 + HIRA DUR 8종 + KAERS + 회수/판매중지 통합 SQLite + FTS5. 결선: RxNorm RRF + DailyMed SPL + ATC 브리지. OpenFDA FAERS는 한국인 정합성(HLA·CYP 변이) 이슈로 Phase 3 이연.

**④ Zero-License-Risk Data Stack**
공개 라이선스(KOGL Type 1 · Public Domain · CC0)만으로 구성. 2024-01 RxNav REST 폐지 이후 공백에 대응해 **RxNorm RRF 로컬 적재**로 대체. DrugBank(CC BY-NC) 등 상용 DDI DB 배제.

**⑤ AI Harness — 관측 · 평가 · CI 전 구간 내장**
Langfuse trace + RAGAS faithfulness/context-precision + **600 케이스 한국어 복약 gold set (자체 구축)** + GitHub Actions 3-gate CI. MedHallu(EMNLP 2025) GPT-4o F1 0.625 · Ren et al.(2026) 멀티턴 AUROC 0.5 붕괴 공백에 대한 시스템 수준 대응.
