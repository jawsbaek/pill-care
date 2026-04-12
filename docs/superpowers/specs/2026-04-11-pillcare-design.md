# 필케어 (PillCare) — 제안서 설계 문서

> **통합 약물 지식 그래프 기반 자율 복약 관리 AI 에이전트**
>
> 한국 AI 해커톤 예선 제안서 (5페이지 + 3분 영상) 설계

---

## 0. 메타

| 항목 | 값 |
|---|---|
| **작성일** | 2026-04-11 |
| **문서 유형** | 제안서 설계 (Design Spec) |
| **제출 대상** | AI 해커톤 예선 |
| **제출물 형태** | 5페이지 제안서 (표지 제외) + 3분 YouTube 영상 |
| **팀 구성** | 서희 (UI) · 주현 (데이터/DB) · 민지 (온보딩 시나리오) · 상훈 (AI 파이프라인) |
| **설계 방법론** | superpowers:brainstorming 스킬 준수 (리서치 선행 → 섹션별 승인) |
| **리서치 트랙** | Track 1~6 (6개 트랙 병렬 실행 완료) |
| **상태** | 설계 §1~§6 사용자 승인 완료 · 구현 계획 작성 대기 |

### 제안서 템플릿 구조 (대회 지정)

1. **§1 기술 개요** — 1.1 기술명 · 1.2 하드웨어 · 1.3 활용분야 · 1.4 기술숙성도 · 1.5 도입수준 · 1.6 유사기술 · 1.7 차별점
2. **§2 기술 상세** — 2.1 기술 목적 · 2.2 기술구조 · 2.3 주요 기능 · 2.4 결과물 형상 · 2.5 배포 방식 · 2.6 혁신적 요소 · 2.7 도전적 요소
3. **§3 구현 방법 및 계획** — 3.1 구현 범위 · 3.2 구현 계획 · 3.3 기술 스택 · 3.4 보유 시설·장비
4. **§4 파급 효과** — 4.1 기술적 파급 효과 · 4.2 사회·산업적 파급 효과

### 심사 4요소

1. **타당성** — 왜 AI로 해결해야 하는지 논리와 구체성
2. **기술성** — 최신 AI 트렌드 반영과 차별성
3. **시장성** — 실생활 활용도, 글로벌 확장 잠재력
4. **실용성** — 저작권 · 신뢰성 · 리스크 관리

---

## 1. 제품 개요 (P1)

### 1.1 기술명

**필케어 (PillCare)**
*— 통합 약물 지식 그래프 기반 자율 복약 관리 AI 에이전트*

> 앱 브랜드명은 "필케어" 단독. 부제는 제안서 표지 보조 문구.

### 1.2 하드웨어 포함 여부

**포함하지 않음 (소프트웨어 단독).** 스마트폰 카메라(약봉투·처방전 OCR), 마이크(증상 음성 입력)만 활용. 별도 디바이스·웨어러블·센서 없음.

### 1.3 활용분야

- **활용분야**: 범용 의료/헬스케어
- **주요 수요자**:
  - ① 다약제 복용자 (65세 이상 41.8%가 5종 이상 복용 — Front. Pharmacol. 2022)
  - ② 다클리닉·다약국 처방 환자 (한국 외래진료 연 18회, OECD 평균 3배)
  - ③ 보호자 동반 돌봄 대상자 (고령 부모·소아 피부양자 관리자)
- **1차 타겟**: 한국 전 연령 성인 본인 사용자 + 피부양자(부모·자녀) 프로필 관리
- **글로벌 확장 경로**: 한국 → 일본·대만 → EU/US senior care

### 1.4 기술숙성도

| 구성 요소 | 숙성도 | 근거 |
|---|---|---|
| VLM 기반 약봉투 OCR | 제품화 | GPT-4o, Claude, Gemini 멀티모달 양산 |
| 공공 약물 DB (식약처 3종·심평원 DUR) | 제품화 | 공공데이터포털 API 상시 제공 |
| 약물 지식 그래프 (PrimeKG) | 시작품→제품화 | Nature Scientific Data 2023, Harvard Zitnik Lab |
| Tool-use / Function calling LLM | 제품화 | OpenAI·Anthropic·Google 2024 GA |
| Medical RAG (Grounded) | 시작품 | i-MedRAG, MIRAGE 등 2024-25 ACL·PSB 연구 |
| **통합 아키텍처 (본 제안)** | **시작품(Prototype)** | 예선 기간 내 핵심 시나리오 1건 작동 POC 확보 |

> 정리 문장: "구성 기술은 모두 제품화 단계이며, 본 제안의 핵심은 이들을 통합한 한국 복약 도메인 Agentic 아키텍처로서 시작품 단계에 있다."

### 1.5 도입수준

- 규칙 기반 복약 알림·DB 조회 수준 제품 (네이버 헬스케어 복약관리, 약올림 등): **도입 증가** 단계
- **Tool-use 기반 Agentic 복약 에이전트 + 멀티-과 통합 DUR 추론: 도입 전 / 도입 초기** 단계
- 국내외 소비자 서비스 중 필케어 수준의 능동 추론에 도달한 사례 없음 (Medisafe는 조회·경고, 닥터나우는 비대면 진료 부가 기능, Pharmacy AI는 약사 B2B 카테고리)

### 1.6 유사기술 비교표

> **비교 원칙**: 7 경쟁자 × 6 차원. HIRA "내가 먹는 약! 한눈에"는 경쟁자 아닌 **데이터 파트너**로 재포지셔닝.

| 서비스 | 타겟 | 약물 DB 소스 | 멀티-과/약국 통합 DUR | AI 추론 방식 | 액션 경계 | 환각 대응 |
|---|---|---|---|---|---|---|
| 네이버 헬스케어 복약관리 | 소비자 | 국내(식약처) | ❌ | 규칙 기반 | 알림 | N/A |
| Pharmacy AI (Kortix) | **약사 B2B** | 미공개/자체 | ❌ (단일 환자 리뷰) | LLM 임상 의사결정 지원 | 경고·자동 문서화 (약사 검토) | 미공개 |
| 약올림 | 소비자 | 국내 | ❌ | 규칙 기반 | 알림 | N/A |
| 올라케어 | 소비자 | 국내(부분) | ❌ | 규칙 + 부분 LLM | 알림·정보 | 미공개 |
| 닥터나우 | 소비자 | 국내(처방 연동) | ❌ (비대면 진료 내 단일 처방) | 규칙 + Q&A | 복약 기록·포인트·Q&A | N/A |
| Medisafe (해외) | 소비자 | 국제(Apple Health 연동) | ⚠️ 병원 연동 기반 조회·경고 | 규칙 기반 4단계 경고 | 알림·경고 | N/A |
| **필케어 (본 제안)** | **소비자 + 피부양자** | **국제(RxNorm·DailyMed·PrimeKG) + 국내(식약처 3종·심평원 DUR) 통합** | ✅ **능동적 추론** | ✅ **Multi-tool Agentic AI** | **경고 + 문서화 + (선택) 의사 브리지 초안** | ✅ **Grounded RAG (근거 강제)** |

**주석 1**: HIRA '내가 먹는 약! 한눈에'는 국가 공공 조회 인프라로, 본 제안의 경쟁자가 아닌 **데이터 파트너**로 포지셔닝 (2025 하반기 건강정보 고속도로 1,263개소 확대 연동 로드맵).

**주석 2**: Pharmacy AI는 약사용 B2B 임상 의사결정 지원 도구로, 필케어(소비자 + 피부양자)와 시장 세그먼트가 다름. 직접 경쟁 관계가 아닌 **인접 카테고리**로 참고.

### 1.7 차별점 (5 bullets)

**① 국내 최초 Multi-tool Agentic 복약 에이전트**
LLM이 약물 지식 그래프 조회·DUR 체크·이력 조회·증상 추적을 tool-use로 호출하는 multi-tool 에이전트. 국내 조사 결과 규칙 기반 또는 단일 LLM Q&A 수준을 벗어난 복약 에이전트는 확인되지 않음. 2024-25년 AMIE (Nature 2025, Google DeepMind), MedAgents (ACL 2024), EHRAgent (EMNLP 2024) 등 frontier 의료 에이전트 연구 흐름을 한국 복약 도메인에 최초로 구현.

**② 능동적 멀티-과/멀티-약국 통합 DUR 추론**
기존 국내 서비스는 약국 단위 일회성 체크에 그치며, HIRA '내가 먹는 약! 한눈에' 공공 서비스는 조회 전용(필케어의 데이터 파트너). 필케어는 사용자의 전체 복약 이력을 한 지식 그래프 위에서 능동적으로 추론 — 상호작용 변화, 복약 시간 패턴, 증상 변화 상관성까지. 2024년 국내 10종 이상·60일 이상 복용자 163만 명 (65세 이상 80.6%)의 사각지대를 직접 겨냥.

**③ 국제 + 국내 공공 약물 지식 그래프 통합**
RxNorm · DailyMed · PrimeKG (국제) ↔ 식약처 3종(낱알식별·의약품개요·묶음의약품) · 심평원 DUR (국내) 통합. 식약처 묶음의약품 API의 ATC 코드 매핑을 브릿지로 활용, 별도 WHO 라이선스 없이 국내↔국제 약물 ID 통합 달성. Harvard Zitnik Lab의 PrimeKG (Nature Scientific Data 2023) 위에 한국 공공 DB를 결합하는 국내 최초 시도.

**④ Zero-License-Risk Data Stack**
업계가 의존해온 NIH RxNav Drug Interaction API가 2024년 1월 폐지된 이후, 필케어는 공개 라이선스만으로 구성된 데이터 스택을 설계 — KOGL Type 1(심평원 DUR), Public Domain(RxNorm·DailyMed), CC0(OpenFDA·Hetionet), CC BY(PrimeKG), 식약처 공공데이터(이용허락범위 제한 없음). 제안서·프로토타입·상업화 전 단계에서 상용 라이선스 계약 없이 법적 리스크 제로로 운영 가능.

**⑤ Grounded RAG + 3중 안전 경계: 의료 환각 원천 차단**
모든 에이전트 응답은 검증된 공공 DB 인용을 필수로 강제. MedHallu 벤치마크(2025) 기준 GPT-4o조차 의료 환각 hard 레벨에서 F1 0.625에 그치는 현실에서, 필케어는 "판단 없음 / 근거 없는 주장 없음 / 의료진 확인 경로 필수"의 3중 경계 설계로 LLM 환각의 의료 리스크를 원천 차단. 식약처 '의료기기와 개인용 건강관리(웰니스) 제품 판단기준' 상 비의료기기(웰니스) 영역에서 운영.

---

## 2. 기술 상세 (P2-3)

### 2.1 기술 목적

**핵심 문제**

한국은 OECD 대비 외래진료 이용 빈도가 **3배(연 18회)** [OECD Health at a Glance], 다수의 과와 의료기관에서 처방을 받는 것이 일상이다. 65세 이상 인구의 **41.8%가 5종 이상**, **14.4%가 10종 이상**의 약을 동시 복용하며 [Front. Pharmacol. 2022, NHIS 전수분석], **2024년 기준 10종 이상을 60일 이상 복용하는 환자는 163만 명**에 달한다 (65세 이상 80.6%). 만성질환자는 **1,880만 명**, 연간 진료비 **34.5조 원** [2019 건강보험통계연보, NHIS·HIRA 공동].

그러나 기존 DUR 시스템은 **약국 단위 일회성 체크**에 머물러, 다른 날짜·다른 과·다른 약국에서 처방받은 약 사이의 상호작용은 어디에서도 체크되지 않는 사각지대에 있다. 그 결과 **한국 대학병원 응급실 방문의 3.5%가 약물 이상반응이며, 그중 15.3%는 예방 가능**했다 [PLOS ONE 2022]. 위고비 등 GLP-1 비만치료제의 확산과 20-30대 ADHD 약물 처방 증가(2019→2023년 각 3.8배·5.6배)로 청년층도 같은 사각지대에 진입하고 있다.

**기존 기술의 한계**

- ① **알림·단일 처방 내 DB 조회 수준**: 국내외 복약 앱은 멀티-과/멀티-약국 통합 분석을 제공하지 않음
- ② **단일 LLM Q&A 의료 환각 리스크**: MedHallu 벤치마크(2025) 기준 GPT-4o조차 의료 환각 hard 레벨에서 F1 0.625에 그침
- ③ **규칙 기반 DUR의 문맥 추론 부재**: 복약 이력·증상 변화·시간적 패턴을 결합한 추론 불가
- ④ **국제·국내 약물 ID 파편화**: RxNorm·DrugBank 등 국제 DB와 국내 EDI/KD 코드 사이 매핑 공백
- ⑤ **RxNav 국제 DDI API 폐지(2024-01)**: 업계 전반의 국제 무료 상호작용 인프라 공백

**제안 기술의 역할**

검증된 국제·국내 공공 약물 데이터를 통합한 Zero-License-Risk 지식 그래프 위에서, LLM이 tool-use로 추론하는 자율 복약 에이전트. 판단 권한은 의료진에 유지하면서, 정보 통합·경고·문서화·의료진 커뮤니케이션 준비를 자동화(현재 Scope A). 향후 의사·약사용 진료 브리지 노트 자동 생성까지 확장(로드맵 Scope B). 한국의 처방 파편화라는 구조적 문제를 소비자와 피부양자(부모·자녀) 관리 모델로 동시에 해결.

### 2.2 기술구조 (5 레이어 아키텍처)

```
┌───────────── 평가 하네스 (CI, 전체 감싸는 박스) ─────────────┐
│  [Trajectory Gate] [Factuality Gate] [Safety Gate]          │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ ① 입력 레이어 (User Inputs)                             │ │
│  │   📷 약봉투·처방전 이미지   💊 낱알 이미지               │ │
│  │   🎙 증상 음성·텍스트                                    │ │
│  │   (+ 로드맵: 🏥 건강정보 고속도로 / 마이데이터 의료)     │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │ ② 지각 레이어 (Multimodal Perception)                   │ │
│  │   VLM OCR (GPT-4o·Claude·Gemini) → 약물 텍스트 + 용량   │ │
│  │   VLM Pill ID → 식약처 낱알식별 DB 매칭                 │ │
│  │   음성 STT → 증상 엔터티 추출                            │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │ ③ UDKG + Retrieval Hub                                 │ │
│  │   - Neo4j(KG) + Qdrant(Dense) + OpenSearch(BM25)       │ │
│  │   - Evidence Tier Classifier                            │ │
│  │     (DUR→RxNorm→DailyMed→PrimeKG→FAERS)                 │ │
│  │   - ATC Bridge (KR↔Global, 49% 커버 + fallback)         │ │
│  │                                                         │ │
│  │   [국내 소스]                  [국제 소스]              │ │
│  │   식약처 낱알식별   ─┐     ┌─ RxNorm                    │ │
│  │   식약처 의약품개요  ├─ ATC ─┤ DailyMed                  │ │
│  │   식약처 묶음의약품 ─┘ 브릿지└─ PrimeKG (Nature 2023)    │ │
│  │   심평원 DUR (KOGL1)         OpenFDA FAERS (CC0)        │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │ ④ Agent Core (Tool-use LLM)                            │ │
│  │   - Query Router (복잡도 L/M/H, MDAgents-Lite)          │ │
│  │   - Template-only KG Tool API (text-to-Cypher 회피)    │ │
│  │                                                         │ │
│  │   [LLM Core: Claude / GPT-4o / Gemini]                  │ │
│  │     ├─ tool: search_drug(text|image) → UDKG             │ │
│  │     ├─ tool: check_dur(drug_ids[], time_range)          │ │
│  │     ├─ tool: get_history(profile_id, range)             │ │
│  │     ├─ tool: get_symptom_log(profile_id)                │ │
│  │     ├─ tool: cite_sources(claims[])                     │ │
│  │     └─ tool: draft_clinician_brief(...) [Scope B]       │ │
│  │                                                         │ │
│  │   - Tool DAG (LangGraph) + Profile Memory (SQLite)     │ │
│  │   - Faithfulness Gate: NLI + SelfCheckGPT              │ │
│  │   - Safety Guardrails: 판단·처방·진단 어휘 차단         │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │ ⑤ 액션 & 사용자 레이어                                   │ │
│  │   ⚠️ 경고 · 📝 문서화 · 📋 의료진 확인 경로               │ │
│  │   [Scope B] 브리지 노트 초안                            │ │
│  │                                                         │ │
│  │   멀티 프로필: 본인 + N명 피부양자 (부모·자녀)           │ │
│  │   프라이버시: 민감정보 별도 동의 + 만 14세 미만           │ │
│  │               법정대리인 동의                            │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**설계 의도**:
- 5 레이어 × 수직 흐름 — 복잡한 시스템을 한 방향 파이프라인으로 전달
- ③ UDKG가 시각적 중심 — 차별점 ③을 그림으로 증명
- ④ Agent Core에 tool 6개 명시 — "Tool-use Agentic AI" 주장을 구체화
- 전체를 감싸는 평가 하네스 박스 — 차별점 ⑤(환각 차단·안전 경계)의 시스템적 내장 표현

### 2.3 주요 기능 (6 모듈)

| # | 모듈명 | 핵심 기능 | 입력 → 출력 |
|---|---|---|---|
| **M1** | 멀티모달 약물 인식 | VLM 기반 약봉투/처방전 OCR + 낱알 이미지 교차검증 + 음성 증상 추출 | 이미지·음성 → 구조화된 약물 객체·증상 이벤트 |
| **M2** | 통합 약물 지식 그래프 (UDKG) | 식약처 3종 + 심평원 DUR + RxNorm/DailyMed/PrimeKG/OpenFDA 통합. ATC 매핑 브릿지 | Drug ID → 국내외 속성·상호작용·기전·이상반응 |
| **M3** | Tool-use Agentic Core | LLM이 6개 tool을 조합해 다단계 추론. 규칙 조회·이력 분석·증상 상관 | 사용자 요청·상태 → 추론 결과 + 인용 |
| **M4** | Grounded RAG 엔진 | 응답 생성 전 모든 주장에 UDKG 근거 부착 강제. 근거 없는 주장 차단 | Draft 응답 → 인용 부착된 최종 응답 |
| **M5** | 멀티 프로필 프라이버시 레이어 | 본인 + N명 피부양자 프로필. 민감정보 별도 동의·법정대리인 동의 | 프로필 요청 → 권한 스코프 내 데이터 접근 |
| **M6** | 진료 브리지 노트 생성기 (Scope B) | 환자 음성 발화 + 복약·증상 이력 → 의료진용 SOAP 포맷 초안 | 환자 상태 → 의사·약사용 노트 초안 |

### 2.4 결과물 형상

| 구성 요소 | 형태 | 역할 |
|---|---|---|
| 필케어 앱 | iOS / Android (React Native) | 본인·피부양자 복약 관리 UI |
| Agent API 서버 | Python / FastAPI | Tool-use 에이전트, Grounded RAG, B2B 확장 접점 |
| UDKG | Neo4j + Qdrant(벡터) + OpenSearch(BM25) | 통합 약물 지식 저장소, 의미 기반 조회 |
| 예선 POC | Python 노트북 + 단일 시연 페이지 | "약봉투 → OCR → DUR → 에이전트 응답" 1 시나리오 |

### 2.5 배포 방식

- **앱**: App Store / Google Play (정식 앱 배포)
- **Agent API**: 내부 서버 (예선 단계), 향후 의료기관·약국 B2B 연동 접점 제공
- **UDKG 스키마 · 공공 데이터 통합 파이프라인**: 일부 오픈소스 공개 (연구·학술 기여)
- **예선 POC**: GitHub 비공개 저장소 + 스크린샷/영상으로 제출

### 2.6 혁신적 요소 (5)

**🔹 A. Template-only KG API + Evidence-Tiered Citation Enforcement**
대규모 KG에서 LLM text-to-Cypher 실행 정확도가 60.18%에 그치는 [CypherBench arXiv:2412.18702] 한계를 원칙적으로 우회. 에이전트에는 `kg.interaction()`·`kg.ingredient()` 같은 typed template tool만 노출하고, 각 tool 응답에 5-tier evidence(식약처 DUR → RxNorm → DailyMed → PrimeKG → FAERS)가 메타데이터로 강제 첨부. Self-RAG (ICLR 2024)·Correctness vs Faithfulness (arXiv:2412.18004, 인용 57% post-rationalized) 두 연구가 지적한 문제를 시스템 수준에서 동시 해결.

**🔹 B. NLI-based Faithfulness Gate + Defer-to-Clinician**
생성 응답의 모든 claim을 DeBERTa-v3 NLI로 retrieved evidence와 대조(entailment ≥ 0.75) + SelfCheckGPT 5-sample consistency 2차 검증. 실패 시 응답 재생성 또는 "의료진에게 확인 요청" 경로로 자동 escalate. MedHallu(EMNLP 2025) 연구가 제시한 "not sure" 옵션의 +38% 개선 효과를 필케어 안전 경계와 융합한 첫 공개 시도.

**🔹 C. MDAgents-Lite 복잡도 게이트 (L/M/H Routing)**
질문 복잡도에 따라 단일 ReAct → Planner + Multi-Tool 체인 → Clinician Escalation 3단계로 자동 라우팅. MDAgents (NeurIPS 2024 Oral)의 PCC/MDT/ICT 구조(10개 의료 벤치 중 7개 SOTA, +4.2%~+11.8%)를 한국 복약 도메인 + 웰니스 영역 + 비의료기기 경계 내로 제한 적용. 복약 도메인 공개 사례 없음.

**🔹 D. Temporal Profile-Scoped KG**
복약 시작·중단·빈도·증상 관찰을 환자 프로필 노드의 temporal edge (`takes(start_ts, end_ts, frequency, dose)`)로 표현. MedTKG(CEUR-WS Vol-3833 2024)·KGDNet(Sci. Rep. 2024)의 admission-wise 패턴을 outpatient 복약 reminder 도메인에 최초 적용. "2주 전 혈압약 시작 → 어제 어지럼증" 같은 시계열 상관 추론 가능.

**🔹 E. 규제 안전 경계의 아키텍처 내장 (3-Layer Guardrail)**
판단 차단(프롬프트) · 근거 차단(Grounding) · 의료진 경로 강제(응답 스키마)를 시스템·LLM·응답 3층에 분산 배치. Cross-profile memory 누수는 red-team suite 6개 카테고리(자기진단 유도 · 용량 변경 · cross-profile 노출 · DUR 우회 · 유사 약명 혼동 · 규제 경계 초과)로 CI 단계에서 차단.

### 2.7 도전적 요소 (6)

**🔸 ① ATC↔RxNorm 51% 매핑 공백**
OHDSI Standardized Vocabularies 분석(Elsevier IJMI 2024, Kury et al.)에 따르면 RxNorm 단일 성분 3,166개 중 **5차 ATC 코드에 매핑되는 것은 1,552개(49%)**에 불과. 필케어는 이 공백을 RxNorm Extension + DailyMed SPL ingredient + 자체 KR 성분 사전으로 보완하는 3-tier fallback 알고리즘을 자체 설계해야 하며, 이 수준의 구현 공개 사례는 부재.

**🔸 ② 의료 환각 hard tier F1 0.625 (GPT-4o 기준)**
MedHallu 벤치마크(Pandit et al., arXiv:2502.14302, EMNLP 2025, 10,000 QA)에서 GPT-4o·Llama-3.1·UltraMedical 모두 **hard tier F1 0.625에 그침**. 동 논문은 "not sure" 옵션 도입 시 최대 **+38% 개선**을 보였으며, 필케어는 이를 defer-to-clinician 게이트의 정량 목표로 삼음.

**🔸 ③ Text-to-Cypher 대규모 KG 60% 실행 정확도 한계**
CypherBench(arXiv:2412.18702) 결과, 대규모 property graph에서 **최고 모델조차 실행 정확도 60.18%**, 10B 미만 오픈소스는 20% 미만. 필케어는 text-to-Cypher를 inference 시 원천 배제하고 template-only KG API로 우회. 오프라인 KG build 단계에서만 LLM 활용.

**🔸 ④ Citation의 57% Post-Rationalization 문제**
"Correctness is not Faithfulness"(arXiv:2412.18004, 2024-12)는 LLM 인용의 **최대 57%가 사후 합리화**(모델이 답 생성 후 인용을 붙이는 형태)임을 정량적으로 입증. Self-RAG 수준의 inline citation 강제만으로는 부족하며, 필케어는 NLI 기반 faithfulness gate를 3-축(문장·인용·tool trace)으로 운영.

**🔸 ⑤ 한국어 의료 벤치 공백: KorMedMCQA ↛ MedQA**
KorMedMCQA (Kweon et al., arXiv:2403.01469, 2024, 7,469 면허시험 QA)는 **한국어 의료 점수가 MedQA와 상관 낮음**을 정량적으로 입증. 즉 영어 의료 SOTA가 한국 도메인에 그대로 성립하지 않으며, 필케어는 식약처 DUR 룰 200 + KorMedMCQA 약물 파트 + PrimeKG 경로 설명 200 = 600 케이스의 한국어 평가 harness를 자체 구축.

**🔸 ⑥ 의료 tool trajectory 벤치의 공개 부재**
AgentBench(ICLR 2024) 8개 환경 중 의료 없음. TRAJECT-Bench(arXiv:2510.04550)는 trajectory-level tool selection/argument/dependency를 측정하지만 일반 도메인. 의료 tool 호출 DAG 정합성 평가 벤치는 공개 부재이며, 필케어는 자체 evaluation harness로 3-gate(Trajectory · Factuality · Safety) CI를 구축해야 함.

---

## 3. 구현 방법 및 계획 (P4)

### 3.1 구현 범위 (6 세부업무)

| # | 세부업무 | 담당 기술 / 산출물 | 주요 도전 | 주담당 |
|---|---|---|---|---|
| **W1** | **UDKG Builder Pipeline** | Python/uv, Neo4j 5.x, 식약처 3종 API, 심평원 DUR, OpenFDA, DailyMed, RxNorm, PrimeKG / → UDKG v1 + 증분 업데이트 스크립트 | KR 성분명 ↔ RxNorm 사전 자체 구축 (ATC 매핑 49% gap 보완), DUR 관계 타입 → PrimeKG schema alignment | 주현 |
| **W2** | **Hybrid Retrieval + Graph RAG Engine** | BGE-M3 + BGE-reranker-v2-m3, Qdrant (Dense), OpenSearch (BM25), Neo4j (KG) / → 3-way hybrid retriever + 5-tier Evidence Classifier | 한국어 의료 임베딩 성능 공백, lost-in-the-middle 방지, Evidence tier 충돌 해결 | 상훈 |
| **W3** | **Agentic Orchestration** (MDAgents-Lite + Tool DAG) | LangGraph, Anthropic tool_use / OpenAI function_calling, SQLite memory, RestrictedPython sandbox / → Query Router + 6 tool DAG + Profile Memory | 복잡도 게이트 분기 정확도, Tool DAG compile-time 정의, profile_id 격리 | 상훈 |
| **W4** | **Faithfulness & Safety Gate** | DeBERTa-v3 NLI, SelfCheckGPT 샘플링, Citation tier 검증기, Regex/LLM guard / → 응답 전 3-gate 필터 | NLI 임계값 튜닝, defer-to-clinician trigger, red-team 6 카테고리 차단 | 상훈 + 주현 |
| **W5** | **Evaluation Harness (3-Gate CI)** | pytest + evaluate lib, WandB, 자체 gold set (600 케이스) / → CI 파이프라인 + 벤치 리포트 | Tool trajectory diff, MedHallu hard tier 한국어 대응본, red-team 자동화 | 주현 |
| **W6** | **Pill Image & OCR + UI** | Qwen2-VL/Gemini VLM/PaddleOCR, 식약처 낱알 DB, React Native / → 약봉투·낱알 인식 + 사용자 UI | MFDS pill ID 벤치 85.65% [JMIR 2023] 한계, 약봉투 semi-structured OCR, 어르신 친화 UI | 민지 + 서희 |

### 3.2 구현 계획 (12주 마일스톤)

| 월 | 기간 | 마일스톤 | 주요 산출물 | 위험 지점 |
|---|---|---|---|---|
| **M1** | W1–4 | **데이터·검색 기반 구축** | UDKG v1, Hybrid Retrieval 초기 버전 | ATC 49% gap 보완, DUR schema alignment |
| **M2** | W5–8 | **Agent Core 통합** | MDAgents-Lite Query Router + 6 tool DAG + Profile Memory, Faithfulness Gate 1차 | 복잡도 게이트 정확도, NLI 임계값 튜닝, cross-profile 격리 |
| **M3** | W9–12 | **평가·검증 + UI** | 3-Gate Evaluation Harness, 600 케이스 gold set, 약봉투 OCR + React Native 앱 MVP, 시범 운영 | 한국어 평가 커버리지, MFDS pill ID 한계 극복, 리텐션 |

**병렬성**: W1 UDKG → M1 1-3주 (기반). W2·W6는 M1부터 병렬. W3는 W1·W2 완료 후 M1 말~M2. W4는 W3와 독립 병렬. W5는 W3·W4 완료 후 M2 말~M3.

### 3.3 기술 스택 (4 레이어)

**① Frontend / UX**
- React Native + TypeScript (iOS/Android 단일 코드베이스)
- Figma (디자인 시스템)
- 접근성: Apple/Google 가이드라인 준수, 피부양자 모드 전환

**② Agent / Backend**
- Python 3.11 + uv (의존성 관리)
- FastAPI (Agent API 서버)
- LangGraph (Tool DAG + checkpoint 기반 profile memory)
- Anthropic Claude · OpenAI GPT-4o · Google Gemini (tool-use 멀티 LLM)
- RestrictedPython (결정적 계산 sandbox)

**③ Retrieval / KG / Data**
- Neo4j 5.x Community (UDKG)
- Qdrant (Dense vector, BGE-M3)
- OpenSearch (BM25 sparse)
- BGE-M3 + BGE-reranker-v2-m3 (BAAI)
- DeBERTa-v3 NLI (Faithfulness gate)
- 데이터: 식약처 3종 API, 심평원 DUR, OpenFDA, RxNorm bulk, DailyMed FTP, PrimeKG dump

**④ 평가 / CI / 배포**
- pytest + evaluate (HuggingFace)
- MLflow / WandB
- GitHub Actions (3-Gate CI)
- Docker + Railway/Fly.io
- 자체 gold set 600 케이스 (W5)

> 모든 백엔드 컴포넌트는 오픈소스 또는 무료 티어. 상업화 전까지 클라우드 비용만 요구.

### 3.4 보유 시설·장비

**본 기술은 클라우드 기반 소프트웨어 서비스로 별도의 물리적 시설·장비를 요구하지 않으며, 현재 팀이 보유한 전용 시설·장비는 없음.**

> 구성 요소는 모두 공개 라이선스 오픈소스 또는 상용 클라우드 서비스(LLM API 등)로 조달 가능하며, 개발 인프라는 GitHub · 클라우드 무료 티어 · 공공데이터포털 API 를 활용한다. 필요 시 본선 단계에서 LLM API 크레딧 · 호스팅 크레딧을 별도 확보한다.

---

## 4. 파급 효과 (P5)

### 4.1 기술적 파급 효과

**A. 학술 논문 가능성 (발표 대상 학회/저널 후보)**

| 기여 주제 | 발표 후보 | 근거 |
|---|---|---|
| Korean Medical Agentic AI + Zero-License-Risk UDKG | ACL / EMNLP / NAACL Healthcare Track, NeurIPS ML4H | 한국 공공 DB 기반 agentic 복약 아키텍처 공개 선행 사례 부재 |
| NLI-based Faithfulness Gate for Medical RAG | NeurIPS AI4Health, JAMIA, npj Digital Medicine | Correctness-vs-Faithfulness 문제에 대한 아키텍처 수준 대응 |
| ATC Bridge-based KR↔Global Drug ID Alignment | IJMI (Elsevier), JAMIA | OHDSI IJMI 2024 49% 매핑 공백 해결 |
| Korean Medication Evaluation Harness | arXiv + KorMedMCQA 저자 그룹 협력 | KorMedMCQA "MedQA와 상관 낮음" 공백 보강 |

**B. 특허 출원 검토 가능 요소 (4)**

1. 템플릿 기반 KG 쿼리 API로 text-to-Cypher 회피하는 의료 AI 질의 방법
2. Evidence Tier Classifier 기반 5-tier citation 강제 메커니즘
3. NLI + SelfCheckGPT 이중 가드와 Defer-to-Clinician 자동 escalation
4. Profile-scoped KG Memory Isolation 구조

**C. 오픈소스·공공 기여 로드맵**

- UDKG 구축 파이프라인 일부 공개 (식약처 3종 ↔ RxNorm/DailyMed 통합 스크립트)
- 600 케이스 한국어 복약 평가 gold set 공개 검토
- NLI-based Faithfulness Gate 레퍼런스 구현 공개

**D. 한국어 의료 AI 생태계 기여**

- Nature 2025 AMIE 의 longitudinal medical agent 패턴을 한국 복약 도메인에 이식한 첫 공개 사례
- 의료 환각 hard tier F1 0.625 공백에 defer-to-clinician 게이트 제안
- KorMedMCQA 이후 복약·약물 상호작용 도메인 공백 보강

### 4.2 사회·산업적 파급 효과

**A. 사회적 규모 (검증된 숫자)**

| 지표 | 수치 | 출처 |
|---|---|---|
| 한국 만성질환자 | **1,880만 명** | 2019 건강보험통계연보 (NHIS·HIRA) |
| 연간 만성질환 진료비 | **34.5조 원** | 동일 |
| 65세+ 5종 이상 복용 | **41.8%** | Front. Pharmacol. 2022, NHIS 전수 |
| 65세+ 10종 이상 복용 | **14.4%** | 동일 |
| 10종+/60일+ 복용자 | **163만 명** (65세+ 80.6%) | 2024 국내 학술 |
| 외래진료 빈도 | **연 18회** (OECD 평균 3배) | OECD Health at a Glance |
| ED 방문 중 ADR | **3.5%** (그중 **15.3% 예방 가능**) | PLOS ONE 2022 |
| 선진국 복약 순응도 평균 | **약 50%** | WHO 2003 |

**B. 구조적 변화**

- **예방 가능한 ED 방문 15.3%** 가 필케어가 직접 겨냥하는 사각지대
- 다클리닉·다약국 구조적 공백을 에이전트 수준에서 첫 본격 해결
- 예방 가능 ADR 감소 → 건강보험 재정 기여
- "3분 진료" 문제 완화 (Scope B)

**C. 글로벌 확장 로드맵 (3 Phase)**

| Phase | 대상 시장 | 근거 | 전략 |
|---|---|---|---|
| **Phase 1** | 🇰🇷 한국 | 처방 파편화 가장 심한 시장 | Zero-License-Risk Stack, 마이데이터 의료 동기화 (2025 하반기 1,263개소) |
| **Phase 2** | 🇯🇵 일본 · 🇹🇼 대만 | 동일 인구구조, RxNorm/ATC 기반 국제 DB는 데이터만 스왑 | 현지 공공 DB 파트너십, 로컬라이제이션 |
| **Phase 3** | 🇺🇸 🇪🇺 Senior Care | Medisafe·MyTherapy 존재하나 agentic 부재 | B2B (senior living, 보험사, PBM) |

> 아키텍처는 국제 표준(RxNorm·ATC·DailyMed·PrimeKG) 전제로 설계되어 UI 로컬라이제이션 + 국가별 어댑터 작업만으로 확장 가능.

**D. 비즈니스 모델**

- **B2C Freemium**: 본인 1 프로필 + 기본 DUR 경고 무료 / 피부양자 2+ · 진료 브리지 · 무제한 증상 추적 유료
- **B2B 의료기관·약국**: 환자 복약 이력 통합 리포트 API (Scope B)
- **건강 데이터 파트너십**: 가명처리된 복약·부작용 인사이트 (개인정보보호법 가이드라인 준수)

**E. 정책·산업 정합성**

- 디지털 헬스케어 정부 지원 확대 흐름과 정합
- 마이데이터 의료 생태계 활성화에 소비자 측 킬러 앱 후보
- 식약처 AI 의료기기 가이드라인(2025) 및 비의료기기(웰니스) 판단기준 내 운영
- 건강보험 재정 기여 잠재력

---

## 5. 5페이지 제안서 레이아웃

### P1 — §1 기술 개요 + 2.1 기술 목적

```
상단 1/6: 1.1 기술명 + 1.2/1.3 한 줄 요약
상단 메타 1/6: 1.4/1.5 미니 테이블
중앙 2/6 ★: 1.6 유사기술 비교표 (시선 고정)
하단 2/6: 좌 — 1.7 차별점 5 bullets, 우 — 2.1 기술 목적 3단락
```

### P2 — 2.2 기술구조 + 2.3 주요 기능

```
상단 1/2: 2.2 아키텍처 다이어그램 (5 레이어 블록도)
하단 1/2: 2.3 M1-M6 6-row 모듈 테이블
```

### P3 — 2.4~2.7 + POC

```
상단 1/3: 2.4 결과물 (좌) + 2.5 배포 (우)
중하단 2/3: 좌 — 2.6 혁신 A-E, 우 — 2.7 도전 ①-⑥
우하단 1/4: POC 스크린샷
```

### P4 — §3 구현 계획

```
상단 40%: 3.1 6 세부업무 W1-W6 테이블
중앙 40%: 3.2 M1-M3 Gantt + 병렬성 주석
하단 20%: 좌 — 3.3 기술 스택 4 레이어, 우 — 3.4 "보유 시설·장비 없음"
```

### P5 — §4 파급 효과

```
상단 1/2: 4.1 A 논문 표 + B/C/D bullets
하단 1/2:
  중앙: TAM 임팩트 인포그래픽
  4.2 A 사회 규모 표, B 구조적 변화, C 글로벌 로드맵, D 비즈니스, E 정책
```

---

## 6. 3분 영상 스토리보드 (7 씬)

### Scene 1 — 훅 (0:00–0:15, 15초)

- **비주얼**: 40대 여성 영상통화. "어머니, 오늘 약 드셨어요?" / "응... 어떤 거?" 거실의 어머니 앞 7-8개 약봉투. 15초에 약봉투들 위 물음표 freeze
- **BGM**: 조용한 피아노
- **목적**: 중장년 심사위원 감정 트리거

### Scene 2 — 문제의 규모 (0:15–0:45, 30초)

- **비주얼**: 모션그래픽, 환자 주위에 여러 병원·약국 아이콘 흩어짐
- **오버레이 순차**:
  - "연 외래진료 18회 — OECD 3배"
  - "65세+ 41.8% 5종 이상 복용"
  - "163만 명 10종+/60일+ 복용 중"
  - "ED 방문 3.5% 약물 이상반응 — 15.3% 예방 가능"
- **나레이션**: "한국인은 평균 3곳 이상에서 처방을 받습니다. 그러나 이 모든 약을 한 번에 보는 주체는 — 아무도 없습니다."

### Scene 3 — 솔루션 소개 (0:45–1:05, 20초)

- **비주얼**: 필케어 로고 + 약봉투 촬영 → 앱 화면 전환
- **오버레이**: "필케어 — 통합 약물 지식 그래프 기반 자율 복약 관리 AI 에이전트"
- **나레이션**: "식약처·심평원부터 RxNorm·PrimeKG까지 검증된 공공 약물 데이터를 통합한 지식 그래프 위에서 자율적으로 추론하는 AI 에이전트입니다."

### Scene 4 — POC 라이브 시연 (1:05–1:55, 50초) ⭐

실제 POC 화면 녹화. 5단계 압축 편집:

| 시간 | 단계 | 화면 | 자막 |
|---|---|---|---|
| 1:05–1:13 | Step 1 | 약봉투 사진 업로드 | "약봉투 사진을 찍으면..." |
| 1:13–1:22 | Step 2 | VLM OCR → 약물 3종 추출 | "VLM이 약물을 인식하고..." |
| 1:22–1:31 | Step 3 | 식약처 낱알식별 DB 매칭 | "식약처 DB와 매칭..." |
| 1:31–1:40 | Step 4 | 심평원 DUR 체크 → 경고 1건 | "⚠️ 경고 1건 발견" |
| 1:40–1:55 | Step 5 | 에이전트 응답 + 출처 3개 | "에이전트가 근거를 인용해 응답" |

- **고정 자막**: "POC 영상은 실제 Claude API + 식약처 공개 DB 기반 작동 기록입니다"

### Scene 5 — 차별점 (1:55–2:25, 30초)

- **비주얼**: 1.6 비교표 애니메이션. 경쟁사 ❌, 필케어 ✅
- **오버레이 순차**:
  1. Multi-tool Agentic AI
  2. Grounded RAG + NLI Faithfulness Gate (arXiv:2412.18004 57% 사후 합리화 대응)
  3. Zero-License-Risk Data Stack (RxNav 폐지 대응)
- **나레이션**: "tool-use 기반 자율 추론, 인용 강제 RAG, 저작권 리스크가 원천적으로 없는 공공 데이터 스택."

### Scene 6 — 임팩트 & 글로벌 (2:25–2:50, 25초)

- **비주얼**: TAM 인포그래픽 애니메이션 + 한국 → 일본·대만 → 세계 지도 확장
- **오버레이**: "1,880만 만성질환자 · 34.5조 원 진료비" / "예방 가능 ED 방문 15.3% 감소 잠재력" / 글로벌 3 phase
- **나레이션**: "필케어는 같은 엔진으로 한국에서 일본·대만을 거쳐 글로벌 senior care 시장까지 확장합니다. HIRA 마이데이터 의료와 식약처 AI 의료기기 가이드라인 — 한국 제도 변화와 동기화된 타이밍입니다."

### Scene 7 — 팀 + 콜 투 액션 (2:50–3:00, 10초)

- **비주얼**: 팀 4명 사진 + 필케어 로고 + 기술대회 로고
- **오버레이**: "필케어 팀: 서희 · 주현 · 민지 · 상훈" / "당신의 모든 약을 아는 유일한 AI 에이전트"
- **나레이션**: "필케어 — 한국의 복약 사각지대를 닫습니다."
- **BGM**: S1 피아노 모티브 리프라이즈

### 영상 제작 리소스

- 기획/콘티: 0.5일 (민지)
- POC 녹화: 0.5일 (상훈)
- 촬영 (S1): 0.5일
- 모션 그래픽 (S2/S5/S6): 1일 (서희)
- 편집 + 나레이션 + BGM: 1일 (주현/외주)
- **총합**: 3.5 팀·일 (4명 × 2일)

### 권장 도구

- 편집: DaVinci Resolve / CapCut Pro
- 모션: Canva Pro / After Effects
- 나레이션: 팀 직접 녹음 (1순위) or ElevenLabs 한국어
- BGM: YouTube Audio Library / Pixabay Music
- 폰트: 프리텐다드

---

## 7. 실용성 방어 전략

### 7.1 Risk Register (12건)

| # | 카테고리 | 질문 | 대응 | 잔여 | 방어 위치 |
|---|---|---|---|---|---|
| R1 | 의료기기법 | SaMD 해당? | 판단·진단·처방 배제, 웰니스 해석, 식약처 질의회신 예정 | L | 1.4, 1.7⑤, 2.6E |
| R2 | 약사법 | 복약지도 아닌가? | 용어 정책 ("복약지도" 금지, "정보 안내 + 의료진 확인") | M | 2.6E, Q&A |
| R3 | 의료법 | 무면허 의료? | 사실 통보 + 제3자 확인 권고 구조 | M | 1.7⑤, 2.6E |
| R4 | 환각 | 잘못된 정보? | Grounded RAG + NLI Gate + SelfCheckGPT + Defer | L | 1.7⑤, 2.6A/B, 2.7②④ |
| R5 | 저작권 | 국제 DB 상업 사용? | Zero-License-Risk Stack (공개 라이선스만) | L | 1.7④, 2.7, 3.3 |
| R6 | 개인정보 | 민감정보 처리? | 별도 동의 UI, 가명 처리, 마스킹 | M | 3.3, 2.3 M5 |
| R7 | 아동 | 법정대리인 동의? | 만 14세 미만 명시 플로우 | L | 2.3 M5 |
| R8 | Cross-profile 누수 | 프로필 간 섞임? | SQLite profile_id row-level + red-team CI | L | 2.6E, 2.7⑥, 3.1W4 |
| R9 | OCR 오식별 | 약 잘못 인식? | VLM + 낱알 이미지 교차검증, 확신도 낮으면 확인 요청 | M | 2.3 M1, 3.1 W6 |
| R10 | 경쟁자 반증 | Medisafe/HIRA 이미? | Medisafe = 조회·경고 수준, HIRA = 데이터 파트너 | L | 1.6, 1.7①② |
| R11 | 구현 난이도 | 12주에 가능? | 6 세부업무 병렬, Track 6 검증 스택 | M | 3.1, 3.2 |
| R12 | 평가 공백 | 한국어 벤치? | 600 케이스 gold set 자체 구축 | M | 2.7⑤, 3.1 W5, 4.1A |

**분포**: High 0 / Medium 5 / Low 7 — 제안서에 쓸 수 있는 문장: "본 제안은 12개 주요 리스크 식별 결과 High 등급 잔여 리스크가 존재하지 않음."

### 7.2 제안서 언어 정책

**❌ 금지어**: 복약지도, 처방, 처방 제안, 진단, 치료, 용량 조절, 복용 변경, 판단, 결정, 약 바꿔드립니다

**✅ 권장어**: 경고, 알림, 안내, 기록, 문서화, 로그, 의료진 확인 요청, 근거 인용, 출처 제시, 정보 통합, 시각화, 요약

**규칙 한 줄**: *"필케어는 **기록**하고 **통합**하고 **인용**하고 **알린다**. **판단**하지 않는다."*

### 7.3 Q&A 답변 뱅크 (12 질문)

| 질문 | 답변 |
|---|---|
| 의료기기법 위반 아닌가요? | 식약처 웰니스 판단기준 내 비의료기기 해석 가능 영역. 판단·진단·처방 배제. 출시 전 식약처 민원인 질의회신 예정 |
| 복약지도 아닌가요? | 약사법 복약지도는 약사 전속. 필케어는 '복약 기록 관리 + 공공 DUR 중계 + 의료진 확인 경로' |
| LLM 환각 어떻게? | Grounded RAG + NLI Faithfulness Gate + SelfCheckGPT + Defer-to-Clinician 4중 안전선. 인용 57% 사후 합리화 문제(arXiv:2412.18004)에 NLI 3축 검증 |
| 국제 DB 저작권? | Zero-License-Risk Data Stack. KOGL/PD/CC0/CC BY만. 상용 DrugBank 배제. RxNav 폐지 이후 공백에 대한 대응 설계 |
| Medisafe와 차이? | Medisafe는 조회·경고 수준, agentic 미도달. 필케어는 tool-use 자율 추론 + 능동적 멀티-과 DUR |
| HIRA가 이미? | HIRA는 조회 전용 공공 서비스. 필케어는 그 데이터 위 에이전트 추론. 파트너 관계, 2025 하반기 건강정보 고속도로 연동 |
| 개인정보 보호? | 민감정보 별도 동의, 수집 최소화, 가명 처리, LLM API 마스킹, 만 14세 미만 법정대리인 |
| 12주 가능? | 6 세부업무 4인 병렬, 2024-25 검증 오픈소스 스택, Nature 2025 AMIE·EMNLP 2024 EHRAgent 레퍼런스 |
| POC 진짜? | 예선 영상 1:05-1:55 구간이 실제 작동 기록. Claude API + 식약처 공개 DB + 심평원 DUR 샘플 |
| 한국어 평가? | KorMedMCQA 외 복약 공백. 600 케이스 자체 gold set. 학술 기여 가능 |
| 사업성? | TAM = 성인 처방 경험자, SAM = 다약제·다클리닉, SOM = 피부양자 돌봄. B2C→B2B→데이터 파트너십 3단 수익. Korea→Japan/Taiwan→Global 3 phase |
| 위고비 2030 규제? | 처방 정보 중계·기록만. 처방 자체는 의료기관 영역 |

### 7.4 Red Team 시뮬레이션 (3)

- **A. 의료 법률 전문가**: "의료법·약사법·의료기기법 세 개를 다?" → R1-R3 + 언어 정책 + 식약처 질의회신
- **B. 경쟁 서비스 임원**: "HIRA/Medisafe가 이미?" → R10 + 1.6 비교표 + 파트너 포지셔닝
- **C. AI 엔지니어**: "12주에 환각까지?" → R4, R11 + Track 6 레퍼런스 + MedHallu 0.625 → +38% 정량 목표

---

## 8. POC 스펙

### 시연 시나리오 (단일 케이스)

```
1. 사용자가 샘플 약봉투 이미지 업로드 (3가지 약 함유, 공공 샘플)
2. VLM OCR → 약물명 + 용량 + 복용법 추출
3. 식약처 낱알식별 DB 매칭으로 품목코드 확정
4. 심평원 DUR 체크 → 병용금기 경고 1건 식별
5. 에이전트가 tool-use로 응답 생성:
   "⚠️ A약과 B약은 심평원 DUR [출처1]에 따라 병용금기 등록 상태입니다.
    C약은 현재 용량에서 특별 주의사항 없음 [출처2].
    의료진에게 확인을 요청하시기 바랍니다."
6. 응답 하단에 3개의 출처 링크 + DB 버전 + 타임스탬프
```

### 구현 스택 (경량)

- Python 3.11 (uv 관리)
- anthropic SDK (Claude Sonnet 4.6, tool-use)
- medicines.csv 로컬 로드 (식약처 낱알식별, 이미 확보)
- 심평원 DUR 샘플 파일 (KOGL Type 1)
- Streamlit 또는 Jupyter 단일 페이지

### 산출물

- GitHub (비공개) 저장소 링크
- 3-4 장 스크린샷 시퀀스 (P3에 1장 ~ 1/4 페이지, 영상 2:00-2:40)
- 제안서 각주: "POC는 예선 기간 내 작동 확인 완료"

### 공수

1-2 MD (상훈 주담당)

---

## 9. 리서치 참조 (Track 1~6)

| Track | 주제 | 파일 | 핵심 정량 근거 |
|---|---|---|---|
| **Track 1** | 문제 검증 | `research/track-1-problem-validation.md` | 1,880만 만성질환자, 34.5조 원, 65세+ 41.8% 5종+, 163만 10종+, 외래 연 18회, ED 3.5% ADR (15.3% 예방 가능) |
| **Track 2** | 경쟁자 분석 | `research/track-2-competitor-landscape.md` | Medisafe 멀티 처방 통합 조회·경고, HIRA 조회 전용 파트너, Tool-use agent 국내외 부재 |
| **Track 3** | 데이터 소스 가용성 | `research/track-3-data-sources.md` | Zero-License-Risk Stack (식약처 3종 + 심평원 DUR + OpenFDA + RxNorm + DailyMed + PrimeKG + Hetionet), RxNav API 2024-01 폐지, DrugCentral은 제외 (Parking Lot) |
| **Track 4** | 규제 경계 | `research/track-4-regulatory.md` | 식약처 웰니스 판단기준, 약사법 24조, 의료법 27조, 개보법 23조, 마이데이터 의료 2025 하반기 1,263개소 |
| **Track 5** | AI 트렌드 | `research/track-5-ai-trends.md` | AMIE Nature 2025, MedAgents, MDAgents NeurIPS 2024 Oral, EHRAgent EMNLP 2024, MedHallu F1 0.625, KorMedMCQA |
| **Track 6** | UDKG+RAG+Agent 딥다이브 | `research/track-6-udkg-rag-agent-deepdive.md` | ATC↔RxNorm 49%, Text2Cypher 60%, Citation 57% 사후 합리화, 20개 논문 인용 |

### 핵심 정량 근거 일괄 목록 (제안서 인용용)

- **ATC↔RxNorm 매핑 49%** (OHDSI IJMI 2024, Kury et al.)
- **Text-to-Cypher 60.18% 실행 정확도** (CypherBench arXiv:2412.18702)
- **LLM 인용 57% 사후 합리화** (arXiv:2412.18004)
- **MedHallu hard tier F1 0.625** / "not sure" +38% (arXiv:2502.14302, EMNLP 2025)
- **AMIE 59.1% vs clinicians 33.6% (p=0.04)** (Nature 2025)
- **MDAgents +4.2%~+11.8%** (NeurIPS 2024 Oral)
- **MFDS pill ID 85.65%** (JMIR 2023)
- **EHRAgent +29.6%** (EMNLP 2024)
- **KorMedMCQA 7,469 QA, MedQA 상관 낮음** (arXiv:2403.01469)

---

## 10. 다음 단계

1. **구현 계획 작성** (writing-plans 스킬)
   - 본 spec 승인 후 구현 단계별 상세 계획 수립
   - 팀원 업무 분담 확정
   - Phase 2 M1-M3 마일스톤 세부화
2. **POC 구현** (상훈 주담당, 1-2 MD)
3. **제안서 5p 작성** (언어 정책 준수)
4. **3분 영상 제작** (팀 2일)
5. **제출 전 체크리스트**:
   - [ ] 5p 초과 여부 재확인
   - [ ] 금지어 일괄 검색·교체
   - [ ] 모든 숫자에 출처 주석
   - [ ] 영상·제안서 숫자 일치 확인
   - [ ] 1.6 비교표 사실관계 재검증

---

## 부록 A. 제안서 내 리스크 방어 분산 매트릭스

| 리스크 | P1 | P2 | P3 | P4 | P5 |
|---|:-:|:-:|:-:|:-:|:-:|
| R1 의료기기법 | ✓ 1.4 | | ✓ 2.6E | | |
| R2 약사법 | | | ✓ 2.6E | | |
| R3 의료법 | ✓ 1.7⑤ | | ✓ 2.6E | | |
| R4 환각 | ✓ 1.7⑤ | ✓ 2.3M4 | ✓ 2.6B/2.7②④ | | |
| R5 저작권 | ✓ 1.7④ | | ✓ 2.7 | ✓ 3.3 | |
| R6 개인정보 | | ✓ 2.3M5 | | ✓ 3.3 | |
| R7 아동 동의 | | ✓ 2.3M5 | | | |
| R8 프로필 누수 | | | ✓ 2.6E/2.7⑥ | ✓ 3.1W4 | |
| R9 OCR 오식별 | | ✓ 2.3M1 | | ✓ 3.1W6 | |
| R10 경쟁자 반증 | ✓ 1.6/1.7①② | | | | |
| R11 구현 난이도 | | | | ✓ 3.1/3.2 | |
| R12 평가 공백 | | | ✓ 2.7⑤ | ✓ 3.1W5 | ✓ 4.1A |

**공백 분석**: 모든 리스크 최소 1필드 커버. R4 환각은 4필드 다층 방어. ✅

---

## 부록 B. 설계 변경 이력

| 일자 | 변경 | 이유 |
|---|---|---|
| 2026-04-11 | 초기 설계 §1-§6 작성 | 사용자 요청, brainstorming 스킬 |
| 2026-04-11 | 5개 피벗 반영 (Medisafe/HIRA 한정어, RxNav 선제 공개, 숫자 1차 출처 교체, 언어 정책) | Track 1-5 리서치 결과 반영 |
| 2026-04-11 | DrugCentral 제외 (Parking Lot) | 라이선스 모호성, Zero-License-Risk 서사 보호 |
| 2026-04-11 | Track 6 딥다이브 반영 (2.6 E 확장, 2.7 정량 6개, 2.2 6 요소 보강) | UDKG+RAG+Agent 기술 도전 강화 |
| 2026-04-11 | Phase 1 예선 runway 제거, 보유 시설·장비 없음 명시 | 사용자 피드백 |

---

*본 설계 문서는 필케어 팀이 제안서 작성 및 구현 전 단계에 참조하는 내부 근거 문서이다. 제안서 5페이지 본문에는 이 문서의 내용이 압축·분산 배치된다.*
