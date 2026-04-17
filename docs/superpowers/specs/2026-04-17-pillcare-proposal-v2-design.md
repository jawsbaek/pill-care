# 필케어 (PillCare) — 제안서 설계 문서 v2

> **공인 데이터 기반 grounded 복약 정보 안내 AI 에이전트**
>
> 한국 AI 해커톤 예선(데모 3개월) → 결선(6개월) 제안서 설계 (β Profile · Grounded Scientist)

---

## 0. 메타

| 항목 | 값 |
|---|---|
| **작성일** | 2026-04-17 |
| **문서 유형** | 제안서 설계 (Design Spec) v2 — Targeted Rewrite |
| **제출 대상** | 한국 AI 해커톤 예선(5p + 3분 영상) · 결선(6개월) |
| **선행 문서** | `2026-04-11-pillcare-design.md` (v1 청사진) — 본 v2에서 실제 구현 및 2025-2026 최신 연구 기반으로 §1.4·§1.6·§1.7·§2.1·§2.2·§2.3·§2.4·§2.5·§2.6·§2.7·§3.1·§3.3 재작성 |
| **리서치 자료** | `research/track-1~6.md` + `docs/research/2026-04-17-design-review-synthesis.md` (15-cycle 적대적 리뷰) + NotebookLM 42개 소스 |
| **선택된 아키텍처 Profile** | **β (Grounded Scientist)** — Deterministic DUR + Evidence Tier tagging(MedConf) + LLM-as-judge critic(AMIE) + 6-Layer Guardrail |
| **현재 진도** | M1 기반 구축 완료 (LangGraph 5-node · Streamlit · Cloud Run · GitHub Actions CI/CD · 테스트 72개) |

### 제안서 템플릿 구조 (대회 지정)

1. **§1 기술 개요** — 1.1 기술명 · 1.2 하드웨어 · 1.3 활용분야 · 1.4 기술숙성도 · 1.5 도입수준 · 1.6 유사기술 · 1.7 차별점
2. **§2 기술 상세** — 2.1 기술 목적 · 2.2 기술구조 · 2.3 주요 기능 · 2.4 결과물 형상 · 2.5 배포 방식 · 2.6 혁신적 요소 · 2.7 도전적 요소
3. **§3 구현 방법 및 계획** — 3.1 구현 범위 · 3.2 구현 계획 · 3.3 기술 스택 · 3.4 보유 시설·장비
4. **§4 파급 효과** — 본 v2에서는 범위 외. §1-§3 확정 후 별도 라운드.

### 심사 4요소 매핑

1. **타당성** — §2.1 배경·목적 + §1.6 유사기술 비교
2. **기술성** — §2.2 아키텍처 + §2.6 혁신 5 + §2.7 도전 6
3. **시장성** — §1.3 활용분야 + §2.5 배포 + §4(후속)
4. **실용성** — §2.6 혁신 D·E + §2.7 도전 ⑥ + §3.1·3.2 구현 계획

---

## 1. 제품 개요 (P1)

### 1.1 기술명

**필케어 (PillCare)**
*— 공인 데이터 기반 grounded 복약 정보 안내 AI 에이전트*

브랜드명은 "필케어" 단독. 부제는 제안서 표지 보조 문구.

### 1.2 하드웨어 포함 여부

포함하지 않음 (소프트웨어 단독). 사용자 기기는 웹 브라우저만 요구하며, 별도 디바이스·웨어러블·센서가 없다.

### 1.3 활용분야

- **활용분야**: 범용 의료/헬스케어 — 만성질환·다약제 복용 환자 대상 복약 정보 안내
- **주요 수요자**
  - ① 다약제 복용자 — 2025년 6월 기준 10종 이상·60일 이상 복용자 171만 7천여 명(65세 이상 80.6%), 2020년 대비 52.5% 증가 [NHIS 2025 보도자료]
  - ② 다기관·다약국 처방 환자 — 외래진료 연 18회 (OECD 평균 대비 약 3배) [OECD Health at a Glance 2023]
  - ③ 보호자 동반 돌봄 대상자
- **1차 타겟**: 한국 전 연령 성인 본인 사용자
- **확장 경로**: 한국(Phase 1) → 일본·대만(Phase 2) → EU/US senior care(Phase 3). 아키텍처는 국제 표준(RxNorm·ATC·DailyMed) 전제로 설계되어 국가별 어댑터 작업으로 확장 가능

### 1.4 기술숙성도

| 구성 요소 | 숙성도 | 근거 |
|---|---|---|
| 공공 약물 DB (식약처 3종 · HIRA DUR 8종) | 제품화 | 공공데이터포털 · HIRA API 상시 제공 |
| SQLite + FTS5 trigram | 제품화 | SQLite 공식 FTS5 모듈, 한국어 trigram 검증 |
| LangGraph 기반 에이전트 파이프라인 | 제품화 | LangGraph 1.1.6 GA, StateGraph + conditional edge |
| Gemini 2.5 Flash / Claude Sonnet 4.6 Structured Output (json_schema) | 제품화 | Google · Anthropic 2025 GA |
| Evidence Tier Tagging (MedConf) | 시작품 | Ren et al., arXiv:2601.15645, 2026 프리프린트 |
| LLM-as-judge Critic (AMIE) | 시작품 | Nature Medicine 2025 연구 패턴 경량 차용 |
| DeBERTa-v3 NLI entailment | 제품화 | Microsoft 공식 모델, MedHallu 벤치 검증 |
| GCP Cloud Run + Workload Identity + GitHub Actions CI/CD | 제품화 | Google 공식 GA, IaC 운영 |
| **통합 아키텍처 (본 제안)** | **시작품(Prototype)** | 데모 POC 작동 상태, 결선까지 β 코어 완성 목표 |

> 구성 기술은 대부분 제품화 단계이며, 본 제안의 고유 지점은 이들을 결합한 한국 복약 도메인 grounded 에이전트 아키텍처로서 시작품 단계에 있다.

### 1.5 도입수준

- 규칙 기반 복약 알림·DB 조회 수준 앱 (네이버 헬스케어 복약관리·약올림 등): **도입 증가** 단계
- **Deterministic DUR + Grounded LLM 하이브리드 복약 에이전트**: **도입 전 / 도입 초기**
- 국내 소비자 서비스 중 HIRA DUR 8종 완전 적용 + LLM Structured Output + 출처 계층 강제 + LLM-as-judge critic을 결합한 사례는 공개 확인되지 않음

### 1.6 유사기술 비교표

> **비교 원칙**: 2025-2026 시점 국내외 소비자 의료 LLM · 복약 도메인 특화 서비스 7개와 비교. HIRA "내가 먹는 약 한눈에"는 경쟁자 아닌 **데이터 파트너**로 포지셔닝.

| 서비스 | 타겟 | 약물 DB 소스 | 멀티-과/약국 통합 DUR | AI 추론 방식 | 액션 경계 | 환각 대응 |
|---|---|---|---|---|---|---|
| OpenAI ChatGPT Health/HealthBench (2025) | 소비자 | 학습 분포 기반 | ❌ (개인 복약이력 미연동) | 범용 LLM Q&A | 정보 제공 | ❌ |
| Google MedLM / AMIE (연구) | 연구 | 의료 대화 데이터 | ❌ (소비자 서비스 미상용) | Multi-turn 진단 대화 | 연구 단계 | 부분 (AMIE self-play) |
| Ada Health (2024 LLM 통합) | 소비자 | 자체 의료 DB | ❌ (증상 체커 중심) | LLM + 증상 체커 | 증상 정보 | 부분 |
| Medisafe Care (2024 GenAI 베타) | 소비자 | 자체 + 약품 DB(해외) | ⚠️ 멀티 처방 리마인더 중심 | GenAI 증상 Q&A | 알림·정보 | ❌ |
| 카카오 케어챗 / 닥터나우 AI (2025) | 소비자 | 국내(부분) | ❌ | 범용 LLM Q&A · 비대면 진료 부가 | 알림·Q&A | 미공개 |
| 네이버 헬스케어 복약관리 / 약올림 / 올라케어 | 소비자 | 국내(식약처 일부) | ❌ | 규칙 기반 | 알림 | N/A |
| **필케어 (본 제안)** | **소비자** | **식약처 3종 + HIRA DUR 8종 + KAERS(데모) / +RxNorm·DailyMed(결선)** | ✅ **결정론 N×N 성분쌍 + HIRA DUR 8종 룰 완전 적용** | ✅ **LangGraph 6-node (Deterministic 4 + LLM 2)** | **정보 안내 + DUR 경고 + 의료진 확인 경로 + 문서화** | ✅ **Evidence Tier + Critic + NLI entailment + 6-layer guardrail** |

**주석 1**: HIRA '내가 먹는 약 한눈에'는 국가 공공 조회 인프라로 본 제안의 경쟁자가 아닌 **데이터 파트너**로 포지셔닝 (2025 하반기 건강정보고속도로 1,263개소 확대 로드맵 공식 발표).

**주석 2**: Pharmacy AI(Kortix)·UpToDate/Micromedex AI(Wolters Kluwer)는 약사·의사용 B2B 임상 의사결정 지원이므로 소비자 타겟인 필케어와 시장 세그먼트가 상이. 직접 경쟁이 아닌 **인접 카테고리**.

### 1.7 차별점 (5 bullets)

**① 국내 최초 Deterministic DUR + Grounded LLM 하이브리드**

안전 판단(병용금기·연령·임부·용량·효능군중복·노인주의 HIRA DUR 8종)은 SQL 결정론으로 보장하고, 자연어 생성은 LLM Structured Output(json_schema)으로 분리한다. 두 레일이 서로 검증 — LLM이 DUR 결과를 임의 해석·우회할 수 없으며, Verify 노드에서 DUR 커버리지를 강제한다. MedAgentBoard (NeurIPS 2025)가 실증한 "구조화 약물 태스크에서 단일 에이전트 + 도구 > 멀티 에이전트" 결과와 정합하며, 불필요한 복잡도를 의도적으로 회피한다.

**② 능동적 멀티-과 · 멀티-약국 통합 DUR 추론**

한국은 외래진료 연 18회(OECD 3배)이지만 약국 단위 일회성 DUR만 존재한다. 필케어는 사용자의 전체 복약 이력을 단일 SQLite 허브 위에서 능동 추론하며 — 다기관 처방 교차 플래그, 성분쌍 N×N 병용금기, HIRA DUR 8종 전체 룰 적용 — **2025년 6월 기준 10종 이상·60일 이상 복용자 171만 7천여 명(65세 이상 80.6%)**의 사각지대를 직접 겨냥한다.

**③ 한국 공공 데이터 완전 통합 (데모) + 국제 표준 브리지 (결선)**

데모 단계에서 **식약처 3종(허가 25K + e약은요 9K + 낱알 25K) + HIRA DUR 8종 룰 + KAERS 성분별 집계 + 식약처 회수/판매중지 API**를 단일 SQLite + FTS5 허브로 통합한다. 결선 단계에서는 국제 표준 ID 체계(RxNorm RRF + DailyMed SPL)와 ATC 브리지를 추가해 영문 cross-lookup과 구조화 Boxed Warning 보완을 제공한다. OpenFDA FAERS는 한국인 정합성(HLA 변이·CYP 대사 차이) 이슈로 Phase 3로 이연한다.

**④ Zero-License-Risk Data Stack**

필케어는 공개 라이선스만으로 구성된 데이터 스택을 운영한다 — KOGL Type 1(HIRA DUR · 식약처 공공데이터), Public Domain(RxNorm · DailyMed), CC0(KAERS 공개 집계본), 식약처 nedrug(이용허락범위 제한 없음). 2024-01 RxNav REST API 폐지 이후 업계 공백에 대응해 **RxNorm 월간 full release(RRF)를 로컬 SQLite 적재**로 대체하며, DrugBank(CC BY-NC) 및 상용 DDI DB는 배제한다.

**⑤ AI Harness — 관측 · 평가 · CI 전 구간 내장**

LangGraph 실행 전 구간을 감싸는 **Langfuse trace + RAGAS faithfulness/context-precision + 600 케이스 한국어 복약 gold set + GitHub Actions 3-gate CI(lint · unit · eval)**을 프로덕션 설비로 내장한다. MedHallu(EMNLP 2025) GPT-4o 의료 hard tier F1 0.625 공백과 Ren 외(2026) 멀티턴 신뢰도 AUROC 랜덤 수준 붕괴 문제에 대한 시스템 수준 대응이며, KorMedMCQA가 커버하지 못하는 한국어 DUR·복약 평가 축을 자체 구축한다.

---

## 2. 기술 상세 (P2-3)

### 2.1 기술 목적

**핵심 문제**

2025년 6월 국민건강보험공단 집계에 따르면 만성질환 진단과 함께 10종 이상의 약을 60일 이상 복용하는 환자는 **171만 7천여 명**에 이르며, 2020년 대비 **52.5% 증가**하였다(65세 이상 **80.6%**) [NHIS 2025 보도자료]. 한국의 65세 이상 인구는 이미 **41.8%가 5종 이상**, **14.4%가 10종 이상** 약물을 동시 복용하며 [Front. Pharmacol. 2022, NHIS 전수분석], OECD 기준 75세 이상 다제병용 처방률은 **64.2%** (2021)로 OECD 평균 50.1%를 크게 웃돈다 [OECD Health at a Glance 2023]. 만성질환자는 **1,880만 명**, 연간 진료비 **34.5조 원** 규모이다 [2019 건강보험통계연보, NHIS·HIRA 공동]. 5종 이상 다제약물 복용군은 대조군 대비 입원 위험 **18%**, 사망 위험 **25%** 높으며, 11종 이상 복용 시 각각 **45%, 54%** 로 상승한다 [Front. Pharmacol. 2022].

그러나 공공 DUR 시스템은 금기·중복 점검 및 투약이력 조회를 제공할 뿐, 누적 처방 이력과 현재 복용 조합을 통합 해석하거나 개인 맞춤형으로 설명하지 못한다. 다른 날짜·다른 진료과·다른 약국에서 처방된 약물 간 상호작용은 어느 시점에서도 체계적으로 감지되지 않는 **사각지대**로 남아 있어, 한국 대학병원 응급실 방문의 **3.5%가 약물 이상반응**이며 이 중 **15.3%는 예방 가능**했던 것으로 보고된다 [PLOS ONE 2022]. 한국의약품안전관리원 집계상 2025년 국내 의약품 이상사례 보고는 **27만 7천여 건**, 전년 대비 **9.4% 증가**로 동일 경향이 계속되고 있다 [한국의약품안전관리원 연보 2026].

**기존 기술의 한계**

이러한 공백을 메우기 위해 OpenAI ChatGPT Medical · Google Med-PaLM · Ada Health 등 의료 AI가 빠르게 확산되고 있으나, 범용 LLM은 학습 분포 기반 확률적 응답 구조상 **오정보 생성(hallucination)을 원천 차단할 수 없다**. MedHallu 벤치마크(EMNLP 2025)에서 GPT-4o가 의료 hard tier F1 0.625에 그쳤고 [arXiv:2502.14302], Ren 외(2026)의 멀티턴 벤치에서는 기존 신뢰도 추정 기법의 AUROC가 **랜덤 수준(0.5)까지 붕괴**하는 불안정성이 확인되어 **단일턴·정적 평가만으로는 상담 맥락의 신뢰도-정확도 동학을 담보할 수 없고 근거 기반 신뢰도 프레임워크가 필요**함이 정량적으로 지적되었다 [arXiv:2601.15645]. 복약 정보는 국가별 허가 기준·약물 상호작용에 따라 결과가 크게 달라지는 **고위험 도메인**이며, 신뢰도를 담보하지 못하는 AI는 오히려 환자 안전에 위협이 된다.

**제안 기술의 역할**

따라서 본 기술은 만성질환·다약제 복용 환자가 약국 밖에서 복약 중 이상 증상을 경험할 때, 식약처 허가정보 · 한국의약품안전관리원 DUR · HIRA 약제급여목록 등 대한민국 공인 의약품 데이터와 RxNorm · DailyMed 등 국제 약학 표준(결선 확장)에 근거해 **복용 중인 약물과의 연관 가능성 정보를 즉시 안내**하는 AI 기반 복약 정보 안내 서비스이다. 이를 위해 **AI 응답이 반드시 공인 데이터 소스에 근거하도록 강제하는 AI harness**를 구축하고, 대한민국 비의료기기(웰니스) 경계 및 식약처 생성형 AI 의료기기 허가·심사 가이드라인(2025-01-24)에 부합하는 범위 내에서 운영한다. 나아가 **LangGraph 기반 에이전트 오케스트레이션**을 통해 사용자의 복약 맥락을 단계적으로 수집하고, 공인 데이터에 기재된 이상반응 · 상호작용 · 용법 정보를 **출처 계층(T1 공공 / T4 AI 보조)과 함께 인용 · 통합 · 안내**한다. 진단 · 처방 · 복용 변경에 대한 판단은 제공하지 않으며, 증상 판단과 복용 결정은 의료진 확인을 거치도록 응답 구조에 강제한다.

> *필케어는 기록하고, 통합하고, 인용하고, 안내한다. 판단하지 않는다.*

### 2.2 기술구조 (5 레이어 + AI Harness 외곽)

```
┌───── AI Harness (전 구간 · GitHub Actions + Langfuse + RAGAS 3-gate CI) ─────┐
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │ ① 입력 — 심평원 "내가 먹는 약 한눈에" XLS (암호화)                     │   │
│  │    msoffcrypto 복호화 → openpyxl 파싱 → MedRecord[]                   │   │
│  │    (약물명 · 용량 · 복용법 · 진료과 · 조제일)                          │   │
│  ├──────────────────────────────────────────────────────────────────────┤   │
│  │ ② 공인 데이터 허브 (Source of Truth — SQLite + FTS5)                  │   │
│  │                                                                        │   │
│  │  [데모 (M2) · 국내 T1]            [결선 (M3) 국제 T1 추가]            │   │
│  │  식약처 허가정보  25K   ──┐       ┌── RxNorm RRF (US NLM · PD)        │   │
│  │  식약처 e약은요    9K   ──┤   ATC ├── DailyMed SPL (Public Domain)     │   │
│  │  HIRA DUR 8종 룰       ──┼ Bridge┤  (Boxed Warning · Pregnancy)       │   │
│  │  식약처 낱알식별  25K   ──┤        │                                    │   │
│  │  KAERS 성분별 집계      ──┤        └── [Phase 3 이연] FAERS · WHO ATC  │   │
│  │  식약처 회수/판매중지   ──┘                                            │   │
│  │                                                                        │   │
│  │  매칭: EDI → Exact → FTS5 trigram → rapidfuzz + 성분 동의어 사전       │   │
│  ├──────────────────────────────────────────────────────────────────────┤   │
│  │ ③ LangGraph 6-Node 파이프라인                                         │   │
│  │                                                                        │   │
│  │   [Deterministic]    [Deterministic]     [Deterministic]              │   │
│  │   match_drugs    →   check_dur       →   collect_info                 │   │
│  │   (4계층 매칭)       (N×N 성분쌍 DUR)   (섹션·라벨 DB 조회)           │   │
│  │                                         ↓                              │   │
│  │                         [LLM · Gemini 2.5 Flash 主 / Claude 4.6 Fbk]   │   │
│  │                         generate                                        │   │
│  │                           ├─ Structured Output (json_schema)            │   │
│  │                           └─ Evidence Tier tagging [MedConf 차용]       │   │
│  │                              각 claim → {Supported / Missing /          │   │
│  │                                        Contradictory} + T1·T4 source   │   │
│  │                                         ↓                              │   │
│  │                         [LLM-as-judge · Claude Haiku 4.5 · 샘플 10%]   │   │
│  │                         critic [AMIE self-critique 차용]               │   │
│  │                           ├─ DUR 커버리지 · 인용 완전성 · 금지어 재평가 │   │
│  │                           └─ Missing/Contradictory claim 자동 드롭      │   │
│  │                                         ↓                              │   │
│  │                         [Deterministic] verify (6-rule)                │   │
│  │                                         ↓                              │   │
│  │                         CRITICAL? ── yes ─────────────────── retry ≤2 │   │
│  │                                         ↓ no                           │   │
│  │                                        END                             │   │
│  ├──────────────────────────────────────────────────────────────────────┤   │
│  │ ④ 안전 경계 (비의료기기 · 웰니스 가이드라인 내장)                      │   │
│  │   1. 금칙어 regex 6개 (진단합니다 · 처방합니다 · 복약지도 · 등)        │   │
│  │   2. 출처 계층 강제 (T1 공공 ≥1 / T4 AI ≤30%)                          │   │
│  │   3. DUR 커버리지 검증 (deterministic 결과 미포함 차단)                │   │
│  │   4. 필수 종결 문구 "의사 또는 약사와 상담하십시오"                    │   │
│  │   5. NLI entailment (DeBERTa-v3-xsmall ≥0.75)                         │   │
│  │   6. 의도 분류기 (임베딩 유사도 ≥0.7, paraphrase 우회 차단)           │   │
│  ├──────────────────────────────────────────────────────────────────────┤   │
│  │ ⑤ 사용자 & 배포                                                        │   │
│  │   Streamlit 1.45 (Python 3.14)                                         │   │
│  │     ├─ XLS 업로드 + DUR 경고 배지                                      │   │
│  │     ├─ 약물별 상세 안내 (T1 · T4 태그 표시)                           │   │
│  │     └─ 핵심 요약 + 경고 라벨                                           │   │
│  │                                                                        │   │
│  │   Docker ▶ GCP Artifact Registry ▶ Cloud Run                          │   │
│  │   (Workload Identity + IAP + GitHub Actions CI/CD)                    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
 [Phase 3 · 결선 이후 로드맵] Citations API · VLM 약봉투 OCR · 멀티 프로필
                              · 마이데이터 연동 · 모바일 네이티브 앱
```

**설계 의도**

- **5 레이어 × AI Harness 외곽**: 관측·평가·CI가 전 구간을 감싸 "재현 가능한 평가 증거"를 프로덕션 기본 설비로 내장한다.
- **② 공인 데이터 허브가 시각적 중심**: §1.7③ 차별점(국내 완전 통합 + 결선 국제 브리지)을 그림으로 증명한다. Neo4j 청사진이 아닌 **실제 SQLite + FTS5**로 단순화되어 12주 내 실장 가능.
- **③ LangGraph 6-Node**: Deterministic 4노드 + LLM 2노드 구성으로 안전 판단은 결정론, 생성·검증은 LLM에 분리한다. MedAgentBoard(NeurIPS 2025) 실증과 정합.
- **④ 안전 경계 6층**: §1.7⑤ 차별점을 시스템 구조로 가시화하며, 금칙어 단어 필터의 paraphrase 우회(Lakera 2024 벤치 60-90%)에 대응한다.
- **⑤ 프로덕션 배포**: Cloud Run + Workload Identity + IAP는 데모 시점에 실제로 가동되며, 심사관이 재현 가능한 공개 URL을 제공한다.

### 2.3 주요 기능 (5 모듈)

| # | 모듈명 | 핵심 기능 | 입력 → 출력 |
|:-:|---|---|---|
| **M1** | **심평원 투약이력 파서** | 암호화 XLS 복호화(msoffcrypto) · openpyxl 파싱 · MedRecord 구조화 | 암호화 XLS + 비밀번호 → MedRecord[] (약물명·용량·복용법·진료과·조제일) |
| **M2** | **공인 데이터 허브** | 식약처 3종 + HIRA DUR 8종 + KAERS 집계 + 회수/판매중지 통합 SQLite + FTS5 · 성분 동의어 사전 (영문↔한글) · 4계층 매칭(EDI→Exact→FTS5 trigram→rapidfuzz) · 다성분 N×N DUR 검사. 결선 단계 RxNorm + DailyMed ATC 브리지 추가 | 약물명 → 구조화된 약물 객체 · DUR 경고 리스트 · 출처 태그 |
| **M3** | **LangGraph 6-Node 추론 파이프라인** | Deterministic 3노드(match · dur · collect) + LLM 생성 1노드(Gemini 2.5 Flash 주/Claude Sonnet 4.6 fallback) + LLM-as-judge critic 1노드(Claude Haiku 4.5, AMIE 차용) + Deterministic verify 1노드. CRITICAL 자동 재시도 | MedRecord[] → 출처 태그된 복약 정보 JSON |
| **M4** | **Evidence-Grounded 생성기** | MedConf(arXiv:2601.15645) 차용 Supported / Missing / Contradictory 3-way 태깅 + T1 공공 / T4 AI 보조 출처 계층. Missing · Contradictory claim은 Critic 단계에서 자동 드롭 | LLM draft + retrieved evidence → claim-level 근거 부착 최종 응답 |
| **M5** | **6-Layer Guardrail + 평가 Harness** | 금칙어 regex · 출처 계층 강제 · DUR 커버리지 · 필수 종결 · NLI entailment(DeBERTa-v3-xsmall ≥0.75) · 의도 분류기(임베딩 유사도 ≥0.7) + Langfuse trace + RAGAS faithfulness/context-precision + 600 케이스 한국어 복약 gold set | 생성 응답 + 증거 chunk → 통과 / CRITICAL 재시도 / 의료진 escalate |

### 2.4 결과물 형상

| 구성 요소 | 형태 | 역할 |
|---|---|---|
| 필케어 웹 애플리케이션 | Streamlit 1.45 (Python 3.14) | 투약이력 업로드 · 복약 정보 안내 · 출처 태그 UI · 경고 배지 |
| LangGraph 6-Node 추론 엔진 | Python · LangGraph 1.1.6 · Gemini 2.5 Flash (Vertex AI) · Claude Sonnet 4.6 fallback · Claude Haiku 4.5 critic | Deterministic 3-node + LLM 1-node + Critic 1-node + Verify 1-node |
| 공인 데이터 허브 | SQLite + FTS5 + 성분 동의어 사전 | 식약처 3종 · HIRA DUR 8종 · KAERS 집계 통합 Source of Truth |
| AI Harness (관측·평가·CI) | Langfuse · RAGAS · 600 케이스 한국어 복약 gold set · GitHub Actions 3-gate | 신뢰성 · 재현성 · 회귀 검증 |
| 심평원 XLS 파서 | msoffcrypto-tool · openpyxl | "내가 먹는 약 한눈에" 투약이력 복호화 · 구조화 |

결선 단계 추가: 국제 약학 표준 브리지 (RxNorm RRF · DailyMed SPL · ATC 매핑 테이블).

### 2.5 배포 방식

- **데모(예선)**: GCP Cloud Run 공개 데모 URL (Workload Identity + Artifact Registry + IAP) + GitHub Actions CI/CD (ruff · pytest · 이미지 빌드 · 자동 배포). GitHub 비공개 저장소 + 스크린샷 · 영상으로 제안서 보조.
- **결선**: Cloud Run 공개 URL + OAuth 인증 + 건강정보고속도로 마이데이터 연동 + 시연 영상 고도화.
- **Phase 3 (상용화)**: 모바일 네이티브 앱(iOS/Android), B2B Agent API 서버(FastAPI), 의료기관 · 약국 · PBM 연동 접점.

### 2.6 혁신적 요소 (5)

**🔹 A. Deterministic DUR + Grounded LLM Hybrid**

안전 판단(병용금기 · 연령 · 임부 · 용량 · 효능군중복 · 노인주의 HIRA DUR 8종)은 SQL 결정론으로 보장하고, 자연어 생성은 LLM Structured Output(json_schema)으로 분리한다. 두 레일이 서로 검증 — LLM이 DUR 결과를 임의 해석 · 우회할 수 없으며, 검증 노드에서 DUR 커버리지를 강제한다. MedAgentBoard (NeurIPS 2025)가 실증한 "구조화 약물 태스크에서 단일 에이전트 + 도구 > 멀티 에이전트" 결과와 정합하며, 불필요한 복잡도를 의도적으로 회피한 설계다.

**🔹 B. Evidence Tier Tagging (MedConf 차용)**

LLM이 생성하는 모든 claim에 **Supported · Missing · Contradictory** 3-way 태그와 **T1 공공 DB / T4 AI 보조** 출처 계층을 동시 부착한다. Missing · Contradictory claim은 Critic 노드에서 자동 드롭되어 근거 없는 주장이 최종 응답에 남지 않는다. Ren 외(2026) 멀티턴 신뢰도 벤치에서 기존 기법 AUROC 랜덤 수준 붕괴 문제에 대한 시스템 수준 대응이며, Supported/Missing/Contradictory 3-way 태깅을 한국 복약 도메인에 적용한다.

**🔹 C. AMIE-style LLM-as-judge Critic Node**

Claude Haiku 4.5 (또는 Gemini Flash)가 독립된 judge로서 생성 응답을 DUR 커버리지 · 인용 완전성 · 금지어 · 안전 경계로 평가한다. CRITICAL 오류 발견 시 재시도가 자동 트리거되며, 10% 샘플링으로 비용을 통제한다. AMIE (Nature Medicine 2025)의 self-play critique 철학을 외래 복약 도메인에 경량 적용한 구조다.

**🔹 D. 6-Layer Guardrail + NLI Entailment Gate**

시스템 · 모델 · 응답 3축에 걸친 6개 방어층 — 금칙어 regex + 출처 계층 강제 + DUR 커버리지 + 필수 종결 문구 + DeBERTa-v3-xsmall NLI entailment(≥0.75) + 의도 분류기(임베딩 유사도 ≥0.7) — 를 배치한다. MedHallu(EMNLP 2025) GPT-4o F1 0.625 hard-tier 공백과 Lakera 2024 벤치가 보고한 단어 필터 paraphrase 우회 60-90%를 "판단 없음 · 근거 없음 차단 · 의료진 확인 강제" 3원칙으로 구조적 대응한다.

**🔹 E. AI Harness — 관측 · 평가 · CI 전 구간 내장**

LangGraph 실행 전 구간을 감싸는 Langfuse trace + RAGAS faithfulness/context-precision + 600 케이스 한국어 복약 gold set + GitHub Actions 3-gate CI(lint · unit · eval). "재현 가능한 평가 증거"를 프로덕션 기본 설비로 내장하며, KorMedMCQA가 커버하지 못하는 한국어 DUR · 복약 평가 축을 자체 구축한다.

### 2.7 도전적 요소 (6)

**🔸 ① 의료 환각 hard-tier F1 0.625 (MedHallu EMNLP 2025)**

Pandit 외 MedHallu 벤치마크(10,000 QA)에서 GPT-4o · Llama-3.1 · UltraMedical 모두 의료 hard tier F1 **0.625**에 그친다 [arXiv:2502.14302]. 동 논문은 "not sure" 옵션 도입 시 최대 +38% 개선을 제시. 필케어는 이 공백을 **Evidence Tier tagging + Critic drop + NLI entailment** 3중 시스템 수준으로 대응한다.

**🔸 ② 멀티턴 신뢰도 AUROC 랜덤 수준 붕괴 (Ren et al. 2026, MedConf)**

Ren 외 2026년 벤치마크(DDXPlus + MediTOD + MedQA × 27개 신뢰도 기법)에서 기존 token-level · consistency-level · self-verbalized 방법의 AUROC가 데이터셋 · 모델에 따라 **랜덤 수준(0.5)까지 붕괴** [arXiv:2601.15645]. 단일턴 · 정적 평가로는 상담 맥락 동학 포착 불가하며 근거 기반 신뢰도 프레임워크 필요성이 정량 증명되었다. 필케어는 RAG 근거 매핑(Supported / Missing / Contradictory) + Critic 재검증 2-stage로 근거 기반 프레임워크를 한국 복약 도메인에 적용한다.

**🔸 ③ LLM 인용 57% Post-Rationalization 공백**

Correctness-vs-Faithfulness 연구(arXiv:2412.18004, 2024-12)는 LLM 인용의 **최대 57%가 사후 합리화**임을 정량 입증했다. 필케어는 **Evidence Tier (MedConf) + 독립 Critic (AMIE) + NLI entailment** 3축으로 claim 자체가 retrieved evidence에서 유래했는지 검증하며, 문장 · 인용 · tool trace 3-축 검증을 응답 스키마에 강제한다.

**🔸 ④ 한국어 의료 복약 벤치마크 공백**

Kweon 외 KorMedMCQA(arXiv:2403.01469, 7,469 면허시험 QA)는 한국어 의료 점수가 MedQA와 상관 낮음을 정량 입증했다 — 영어 SOTA가 한국 도메인에 그대로 성립하지 않는다. KorMedMCQA 내 복약 · 약물 상호작용 문항 비율은 약 8-12%로 추정되어 DUR 특화 평가 공백이 존재한다. 필케어는 **식약처 DUR 룰 200 + 복약지도 문구 120 + red-team 100 + 자연스러움 80 + 증상 매핑 100 = 600 케이스 한국어 복약 평가 gold set**을 자체 구축한다.

**🔸 ⑤ 한국 처방 파편화 × 다기관 DUR 사각지대**

한국은 외래진료 연 18회(OECD 3배) [Health at a Glance 2023], 평균 3곳 이상 의료기관에서 처방을 받지만 **약국 단위 DUR**만 존재해 다른 날짜 · 진료과 · 약국 간 상호작용은 구조적으로 체크되지 않는다. HIRA "내가 먹는 약 한눈에"는 조회 전용이다. 필케어는 HIRA DUR 8종 룰 전체 + 식약처 성분 매핑 + KAERS 집계를 단일 SQLite 허브로 통합하고 `match_drugs → check_dur (N×N 성분쌍)` 결정론 파이프라인으로 사각지대를 폐쇄한다.

**🔸 ⑥ 비의료기기(웰니스) 규제 경계 유지 + 의미 우회 방어**

식약처 '생성형 AI 의료기기 허가·심사 가이드라인(2025-01-24)' 및 '디지털의료기기 분류 가이드라인(2025-05-07)' 기준 비의료기기(웰니스) 영역에서 운영하려면 판단 · 진단 · 처방 배제가 필수다. 단순 단어 replace 필터는 paraphrase 우회(Lakera 2024 벤치 60-90% 성공률)에 취약하다. 필케어는 **regex + 임베딩 유사도 의도 분류기 + NLI entailment + 필수 종결 문구 + Critic 의미 검증** 5계층으로 "판단하지 않는다" 원칙을 의미 수준에서 방어하며, 약사법 §24 복약지도 경계를 유지한다.

---

## 3. 구현 방법 및 계획 (P4)

### 3.1 구현 범위 (6 세부업무)

| # | 세부업무 | 담당 기술 / 산출물 | 주요 도전 | 주담당 |
|:-:|---|---|---|:-:|
| **W1** | **공인 데이터 허브 ETL** | Python 3.14 · uv · SQLite + FTS5 trigram · 식약처 3종(허가 · e약은요 · 낱알) + HIRA DUR 8종 + KAERS 성분별 집계 + 회수/판매중지 API · 성분 동의어 사전(영문↔한글) | DUR 8종 스키마 정규화, 회수 API 실시간 차단, 성분 동의어 800+ 쌍 구축 | 주현 |
| **W2** | **약물 매칭 엔진** | 4계층 매칭 (EDI → Exact → FTS5 trigram → rapidfuzz token_set_ratio) · 다성분 N×N DUR 검사 · 매칭 신뢰도 스코어 | 제형·함량 noise, 오탈자 대응, 성분코드 false-negative 방지, `min_score` 85 튜닝 | 주현 |
| **W3** | **LangGraph 6-Node 파이프라인** | LangGraph 1.1.6 StateGraph · Gemini 2.5 Flash (Vertex AI) · Claude Sonnet 4.6 fallback · Claude Haiku 4.5 critic · Pydantic 2.13 Structured Output · json_schema · CRITICAL 재시도 루프 | Critic LLM-as-judge 평가 기준, 멀티 프로바이더 스키마 동등성, retry 무한루프 방지 | 상훈 |
| **W4** | **Evidence Tier + 6-Layer Guardrail** | MedConf Supported/Missing/Contradictory 태깅 + T1/T4 출처 계층 + 금칙어 regex + DUR 커버리지 + 필수 종결 + DeBERTa-v3-xsmall NLI entailment(≥0.75) + 의도 분류기(임베딩 유사도 ≥0.7) | NLI 한국어 의료 성능 튜닝, paraphrase 우회 차단, Critic drop 임계값 | 상훈 + 주현 |
| **W5** | **AI Harness (관측·평가·CI)** | Langfuse trace · RAGAS faithfulness/context-precision · 600 한국어 복약 gold set(DUR 200 + 문구 120 + red-team 100 + 자연스러움 80 + 증상매핑 100) · GitHub Actions 3-gate CI(lint · unit · eval) | 약사 1인 검수 일정, LLM-as-judge kappa ≥0.7, RAGAS 한국어 judge prompt 튜닝 | 주현 + 상훈 |
| **W6** | **Streamlit UI + Cloud Run 배포** | Streamlit 1.45 (Python 3.14) · XLS 업로드 + 출처 태그 배지 + DUR 경고 UI · Docker multi-stage · GCP Artifact Registry · Cloud Run · Workload Identity + IAP · GitHub Actions 자동 배포 | 어르신 친화 UI, XLS 오류 복구 플로우, cold-start 대응, IAP 권한 관리 | 민지 + 서희 |

**병렬성**: W1 · W2는 순차(M1), W3 · W4는 M2 병렬, W5 · W6은 M2 말~M3 진행.

### 3.2 구현 계획 (6개월 · 4-마일스톤)

| 마일스톤 | 기간 | 산출물 | 위험 지점 |
|:-:|---|---|---|
| **M1 · 기반 구축** | W1-W6 | W1-W2 공인 데이터 허브 + 약물 매칭 엔진, W3 5-node LangGraph 초기 + Gemini/Claude 스위치, W4 4-layer guardrail 기초, W6 Streamlit + Cloud Run 배포 + CI/CD | 잔여 정규화 튜닝 |
| **M2 · 데모 제출(예선)** | W7-W12 | W3 Critic 노드 추가(6-node 완성) · W4 MedConf Evidence Tier + NLI entailment + 의도 분류기 · W5 Langfuse + RAGAS + gold set 200 케이스 + red-team 10 · HIRA DUR 8종 완성 · 제안서 5p + 3분 영상 | Critic 품질 튜닝, NLI 임계값, 영상 촬영 일정 |
| **M3 · 결선 전반** | W13-W18 | Gold set 200→600 확장 · MedHallu 한국어 subset 50 · RxNorm RRF + DailyMed SPL ATC 브리지 도입 · red-team 20 CI · 출처 태그 UI 고도화 | ATC 매핑 49% 공백 보완, RxNorm 월간 갱신 인프라, 약사 검수 일정 |
| **M4 · 결선 후반** | W19-W24 | 마이데이터 의료(건강정보고속도로) 연동 · 출처 인용 UI 고도화 · Gemini vs Claude A/B · 파트너십 논의(대한약사회 · 한국보건의료정보원 · NIA) · 결선 발표 자료 · 데모 시나리오 | 마이데이터 API 공개 일정, 결선 시연 환경 안정화 |

**전담**: M2 · M3은 상훈(AI) 주도 · 주현(데이터) 병행. M4는 민지(시나리오 · 파트너십) 주도. 서희(UI)는 M2 · M4 집중.

### 3.3 기술 스택 (4 레이어)

**① Frontend / UX**
- Streamlit 1.45.1 (Python 3.14 기반)
- 한국어 접근성 가이드라인 (KWCAG 2.2 AA 목표)

**② Agent / Backend**
- Python 3.14 + uv (의존성 관리, pyproject.toml 기준)
- LangGraph 1.1.6 (StateGraph + conditional retry)
- Gemini 2.5 Flash (Vertex AI `asia-northeast3`, 주 생성 모델)
- Claude Sonnet 4.6 via langchain-anthropic (Fallback 생성)
- Claude Haiku 4.5 via Anthropic SDK (Critic LLM-as-judge, 10% 샘플링)
- Pydantic 2.13 (json_schema Structured Output)

**③ Data / Retrieval / Safety**
- SQLite + FTS5 trigram
- rapidfuzz 3.14.5 (4계층 매칭 fuzzy)
- 성분 동의어 사전 (자체 구축, 영문↔한글)
- DeBERTa-v3-xsmall NLI (ONNX 80MB, entailment gate)
- 의도 분류기 (임베딩 유사도, KURE-v1 또는 BGE-M3 활용)
- 데이터 (데모): 식약처 3종(허가 25K + e약은요 9K + 낱알 25K) + HIRA DUR 8종 룰 + KAERS 집계 + 식약처 회수/판매중지
- 데이터 (결선 추가): RxNorm RRF (US NLM, Public Domain) + DailyMed SPL (Public Domain) + ATC 브리지 테이블

**④ Observability / Evaluation / CI·CD**
- Langfuse (trace, `@observe` decorator)
- RAGAS (faithfulness · context precision · answer relevance)
- 600 케이스 한국어 복약 gold set (자체 구축 목표)
- pytest + pytest-cov (unit · integration)
- GitHub Actions (ruff check/format + pytest + build + deploy)
- Docker multi-stage (Python 3.14-slim)
- GCP: Artifact Registry + Cloud Run + Workload Identity + IAP + Secret Manager

### 3.4 보유 시설·장비

본 기술은 클라우드 기반 소프트웨어 서비스이며, 팀이 보유한 전용 시설·장비는 없다.

---

## 4. 다음 단계

1. **spec 리뷰 (사용자 검토 게이트)** — 본 문서 전체 검토 후 승인 대기
2. **§1-§3 제안서 본문 집필 계획 수립** — `superpowers:writing-plans` 스킬 호출, 실제 제안서 5페이지 원고 작성 세부 플랜 생성
3. **§4 파급 효과** — 별도 라운드, v2 후속으로 브레인스토밍 재개 예정
4. **구현 · 리서치 딥다이브** (사용자 요청 플래그):
   - LangGraph 6-node 세부 구현 설계 (critic 노드 평가 기준, retry 루프, state 스키마)
   - Evidence Tier tagging 프롬프트 설계
   - NLI entailment + 의도 분류기 모델 선택 · 튜닝
   - 600 케이스 gold set 설계 · 약사 검수 프로세스
   - Python 3.14 마이그레이션 의존성 호환성 검증
   - 국제 데이터 ETL (RxNorm RRF · DailyMed SPL)

---

## 5. 설계 변경 이력 (v1 → v2)

| 일자 | 변경 | 이유 |
|---|---|---|
| 2026-04-11 | v1 초기 설계 §1-§6 작성 (Neo4j+Qdrant+OpenSearch UDKG · tool-use agentic · React Native · VLM OCR 청사진) | brainstorming 초기 제안 |
| 2026-04-17 | **15-cycle 적대적 리뷰** (4 차원 × 15 렌즈) 실행 | 실구현 vs v1 청사진 gap, 기술 선택 대안, 의학 LLM 선행사례, 한국 데이터 공백, 언어 정책·정합성 |
| 2026-04-17 | **v2 Targeted Rewrite** — §1.4 · §1.6 · §1.7 · §2.1 · §2.2 · §2.3 · §2.4 · §2.5 · §2.6 · §2.7 · §3.1 · §3.3 재작성 | R13 5대 모순(UDKG · tool-use · multimodal · NLI Gate · React Native) 실구현 기반 재정비, R14 언어 정책 준수(복약지도 삭제 · 공식 명칭 "복약 정보 안내") |
| 2026-04-17 | **Profile β (Grounded Scientist) 확정** | MedConf + AMIE + NLI + 6-Layer Guardrail. tool_use 미채택(trustable 지향). MedAgentBoard 보조 인용 |
| 2026-04-17 | 국제 데이터 단계별 채택 — 데모: 국내만 / 결선: RxNorm + DailyMed / Phase 3: FAERS · WHO ATC | R11 재리뷰 결과. FAERS 한국인 정합성(HLA · CYP 변이) 이슈로 Phase 3 이연. "국내 최초 한국 공공 의료 AI 완전 통합" 프레임 유지 |
| 2026-04-17 | Python 3.14 채택 | 2025-10 GA, 의존성 호환성 검증은 M2 작업 포함 |

---

## 6. 리서치 참조

| 분류 | 항목 | 위치 |
|---|---|---|
| Track 리서치 | 문제 검증 · 경쟁자 · 데이터 · 규제 · AI 트렌드 · UDKG+RAG+Agent 딥다이브 | `research/track-1~6.md` |
| 설계 리뷰 종합 | 15-cycle 적대적 리뷰 (4 차원 × 15 렌즈) | `docs/research/2026-04-17-design-review-synthesis.md` |
| NotebookLM 프로젝트 | 42개 소스 (논문 12 + PrimeKG + 국제 DB 4 + OECD 2 + 한국 공공 5 + 식약처 가이드라인 3 + Front. Pharmacol. + 건보통계연보 + 내부 10) | NotebookLM: "PillCare 제안서 리서치 (2026-04-17)", notebook_id `5796b918-740f-4340-a1ad-355fe4c5bff8` |
| 핵심 인용 논문 | MedHallu (arXiv:2502.14302, EMNLP 2025) · MedConf (arXiv:2601.15645, 2026) · Correctness-vs-Faithfulness (arXiv:2412.18004) · KorMedMCQA (arXiv:2403.01469) · AMIE (Nature Medicine 2025) · MedAgents (ACL 2024) · MDAgents (NeurIPS 2024) · EHRAgent (EMNLP 2024) · MedAgentBoard (NeurIPS 2025) · i-MedRAG · MIRAGE · PrimeKG (Nature Sci Data 2023) | NotebookLM 프로젝트 내 개별 소스 |
| 핵심 정량 근거 | MedHallu F1 0.625 · MedConf AUROC 0.5 붕괴 · Citation 57% post-rationalization · KorMedMCQA MedQA 상관 낮음 · OECD 75+ 다제병용 64.2% · ED 3.5% ADR 15.3% 예방 가능 · 2025-06 171만 7천 다제 복용자 · 이상사례 27.7만 (+9.4%) · HIRA DUR 8종 룰 | §2.1 · §2.7 인용 |

---

*본 설계 문서는 필케어 팀이 제안서 작성 전 · 구현 전 단계에 참조하는 내부 근거 문서이며, 실제 제안서 5페이지 본문은 본 문서의 §1-§3 내용을 압축 · 분산 배치해 작성한다.*
