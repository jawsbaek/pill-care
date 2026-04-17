# PillCare 설계 리뷰 종합 (15 사이클)

> 작성일: 2026-04-17
> 목적: 해커톤 제안서 v2 재작성에 반영할 15회 적대적 설계 리뷰 결과 통합
> 기반: `docs/superpowers/specs/2026-04-11-pillcare-design.md` + 실제 구현 (`src/pillcare/*`) + 2025-2026 최신 연구·서비스 동향

---

## 0. 리뷰 커버리지

| # | 축 | 주제 | 심각도 |
|---|---|---|:---:|
| R01 | 기술 선택 | Retrieval stack (SQLite + FTS5 + rapidfuzz) | 🟠 |
| R02 | 기술 선택 | Orchestration framework (LangGraph 5노드) | 🟡 |
| R03 | 기술 선택 | LLM 모델 선택 (Gemini 2.5 Flash + Claude) | 🟢 |
| R04 | 기술 선택 | Guardrails (5 post-verify + 금칙어) | 🟠 |
| R05 | 기술 선택 | Observability / Evaluation (현 거의 전무) | 🔴 |
| R06 | 선행사례 | 글로벌 소비자 의료 LLM (ChatGPT Medical 등) | 🟢 |
| R07 | 선행사례 | 복약 도메인 특화 AI 서비스 | 🟢 |
| R08 | 선행사례 | 의료 에이전트 연구 (AMIE·MedAgents·MedConf) | 🟡 |
| R09 | 선행사례 | 한국 의료 AI 상용/공공 (HIRA·네이버·카카오) | 🟢 |
| R10 | 한국 데이터 | 공공 데이터 공백 | 🟠 |
| R11 | 한국 데이터 | 국제 데이터 보완 전략 | 🟡 |
| R12 | 한국 데이터 | 한국어 의료 평가 벤치 공백 | 🟠 |
| R13 | 정합성 | 제안서 주장 vs 실제 구현 gap | 🔴 |
| R14 | 정합성 | 언어 정책 + 1안/2안 + 기능명 | 🔴 |
| R15 | 정합성 | 12주 × 4인 실행 가능성 | 🟠 |

**🔴 Critical (3)**: R05 Observability, R13 Spec-Reality Gap, R14 언어 정책
**🟠 High (5)**: R01, R04, R10, R12, R15

---

## 1. 차원별 핵심 발견

### A. 기술적으로 더 좋은 선택지 (R01-R05)

**권장 유지(현 구현 정당화)**:
- **Gemini 2.5 Flash 주 + Claude Sonnet 4.6 백업** 구성은 2025-2026 벤치마크 기준 경제성·의료 한국어 성능 균형 최적 (R03). KorMedMCQA Doctor 기준 Claude Opus 4 96.55 / Gemini 2.5 Pro 90.8 / GPT-5.1 90.11. 한국어 특화 LLM(HyperCLOVA X·Solar·Exaone)은 의료 벤치 공개 데이터 부족 → 생성용 부적합, rerank/embedding 보조 역할만 (R03).
- **LangGraph 5노드 + deterministic DUR**은 MedAgentBoard (NeurIPS 2025) "구조화 약물 태스크에서 multi-agent < single-agent+tools" 실증 결과와 정합 → 제안서 강력한 근거 (R08).

**권장 보완(6주 내)**:
- **P0 Observability**: Langfuse Cloud + `@observe` 데코레이터 (5줄 코드 변경) + RAGAS faithfulness/context-precision (R05). Gold set 200케이스 후 nightly regression. 심사관 "재현 가능한 평가 증거" 요구 대응.
- **P0 Guardrail 2계층 추가**: (a) 단어 replace 필터의 paraphrase 우회율 60~90% (Lakera 2024) → 의도 분류기(KoBigBird 임베딩 유사도 ≥0.7 차단) 또는 NLI entailment(DeBERTa-v3-xsmall 80MB) 추가 (R04).
- **P0 Retrieval 정규화**: 현 FTS5+rapidfuzz는 다성분 약물 false-negative 리스크. `main_ingr_eng` + 한글 성분명 양방향 동의어 테이블 + min_score 70→85 상향 + 함량·제형 exact guard (R01, 1주 작업).

**권장 로드맵 이관**:
- BGE-M3 hybrid retrieval, tool-use 루프, Citations API, Extended thinking — POC 후 Phase 2.

---

### B. 더 좋은 의학 LLM 서비스 사례 / 선행 연구 (R06-R09)

**글로벌 소비자 의료 LLM** (R06): ChatGPT Health/HealthBench, Google AMIE, Ada Health, K Health 모두 존재하지만 **"약국 밖 이상 증상 → 복용 중인 약물과의 연관성 즉시 안내"** 프레임(2안)으로 한국 공공 DUR을 grounding 소스로 쓰는 서비스는 **부재**. Apple/Samsung Health AI는 OS 레벨 리마인더 수준.

**복약 특화 AI** (R07): Medisafe Care(2024 GenAI), MyTherapy, MedAware, Pharmacy AI (Kortix), UpToDate/Micromedex AI 모두 **단일 처방 또는 B2B·영문·비-한국약 중심**. 다기관·다약국 + 성분 단위 교차 DUR + 한국 공공 DB grounding 조합은 국내 유일.

**의료 에이전트 연구 차용 패턴** (R08) — **실제 5노드 LangGraph에 얹을 수 있는 것**:
1. **MedConf (arXiv:2601.15645, 2026)**: Claim을 Supported/Missing/Contradictory 3-way 태깅 → PillCare `generate` 출력 claim-level 검증 추가.
2. **EHRAgent (EMNLP 2024)**: 자연어 → 코드 변환으로 환각 감소 → `match_drugs` 단계에서 이미 적용 중(LLM 자유생성 없이 FTS5 쿼리 실행).
3. **i-MedRAG (ACL 2025)**: 부족 시 1회 재검색 self-ask → `collect_info` 확장에 적용 가능.
4. **AMIE self-critique (Nature 2025)**: critic node 1회 추가 → 현 `verify` 노드를 LLM-as-judge로 승격 가능 (비용 대 효과 검토).
5. **MDAgents adaptive collaboration (NeurIPS 2024 Oral)**: 난이도별 분기 → CRITICAL DUR flag 있을 때만 추가 검증 노드 트리거.

**한국 의료 AI 경쟁·파트너** (R09):
- **데이터 파트너 (Tier A)**: HIRA(건강정보고속도로 2025 하반기 1,263개소), 식약처 nedrug, KIDS, 약학정보원. "내가 먹는 약 한눈에" 카톡 간편인증 '25.8 시행.
- **잠재 경쟁자**: 카카오 케어챗, 닥터나우 AI, 올라케어 — 모두 DUR deterministic grounding 미보유 → 차별화 유지.
- **파트너십 제안 대상**: 한국보건의료정보원, 대한약사회, 보건복지부 마이데이터 TF, NIA.

**식약처 AI 의료기기 가이드라인(2025)** 체크리스트 — PillCare 비의료기기(웰니스) 유지 조건:
- 금지: 진단/치료/예후 예측/치료반응 모니터링 표현, 증상→질환명 매핑, 복용량 변경 지시, 처방 대체 추천
- 허용: 이미 처방된 약의 정보 요약·복용법 알림·병용금기 경고(공공 데이터 출처 표기), 교육 목적
- 2025.1.24 '생성형 AI 의료기기 허가·심사 가이드라인' + 2025.5.7 디지털의료기기 분류 가이드라인 준수 필수.

---

### C. 한국 데이터 공백 + 국제 보완 (R10-R12)

**미활용 한국 공공 데이터 → POC 12주 내 통합 우선순위**:
1. **HIRA DUR 8종 룰 전체** (현재 병용금기만) — 연령·임부·용량·효능군중복·노인주의 추가 시 deterministic 안전성 **4-5배 확장**. 공공데이터포털 CSV/엑셀 배포, 즉시 통합 (R10).
2. **HIRA 약제급여목록표** — 성분-제품-ATC 매핑 keystone, 제네릭 동등성 판단 (R10).
3. **식약처 회수·판매중지 API** — 실시간 안전성 차단 (RECALL 태그), 1주 내 (R10).
4. **KAERS 성분별 이상사례 집계** — 한국인 보고 빈도 상위 부작용 표시 (R10).

**국제 데이터 보완 (반드시 3개)** (R11):
- **RxNorm RRF 월간 + ATC 브리지** (Public Domain 수준 UMLS) — 한국 KD코드 → ATC → RxCUI 체인, 영문 cross-lookup.
- **OpenFDA FAERS** (CC0) — KAERS 미공개 raw의 국제 signal 보완.
- **DailyMed SPL** (Public Domain) — 한국 pdf 허가사항의 구조화 XML 대안, Pregnancy/Lactation 섹션, Boxed Warning.

**제외 확정**: DrugBank Open Data (CC BY-NC, 상업 불가), Hetionet (2017, PrimeKG 상위호환).
**조건부**: WHO ATC 상업 재배포 제한 — SaaS 배포 시 재검증 필요. 제안서 §1.7④ "Zero-License-Risk" 주장 유지하되 주석 명시.

**한국 데이터 단독 공백 3개** → 국제 데이터로만 메울 수 있음 (R11):
- 희귀/장기 이상반응 시그널 (KAERS raw 비공개)
- 구조화 Boxed Warning/Contraindication (식약처 pdf 한계)
- 국제 성분명/영문 교차조회

**평가 벤치마크 공백** (R12):
- KorMedMCQA는 약물 관련 문항 비율 **8~12%** 추정, DUR·복약지도 특화 부재.
- **자체 gold set 600 케이스는 정당** — 최소 150(해커톤), 권장 400, 이상 1000.
- 구성: DUR pair 200 + 인용 평가 120 + red-team 100 + 자연스러움 80 + 증상매핑 100.
- 검수: 약사 1명 × 40h (~200만원) + 의사 자문 10h.
- LLM-as-judge: 축 1·3은 deterministic, 축 2·4는 GPT-4/Claude judge + few-shot rubric kappa 0.7+ 가능.
- 하이브리드: deterministic 30% + LLM judge 50% + human 20%.

---

### D. 정합성 체크 — 가장 위험한 Gap (R13-R15)

**심사관이 가장 먼저 발견할 5대 모순** (R13):

| # | 제안서 주장 (2026-04-11) | 실제 구현 (2026-04-17) | 심각도 |
|---|---|---|:---:|
| 1 | Neo4j + Qdrant + OpenSearch UDKG | SQLite 단일 DB | 🔴 |
| 2 | Tool-use Agentic (6 tool: search_drug/check_dur/…) | tool_use 전혀 미사용, structured output만 | 🔴 |
| 3 | VLM OCR + 낱알 이미지 + 음성 STT 멀티모달 입력 | 심평원 XLS 파일 업로드만 | 🔴 |
| 4 | NLI Faithfulness Gate + DeBERTa-v3 + SelfCheckGPT | banned words replace + 5 post-verify만 | 🟠 |
| 5 | React Native iOS/Android + FastAPI | Streamlit + Cloud Run | 🟠 |

**해결 방향**: 제안서 v2에서 **세 구역 분리** — (a) "현재 POC 동작 범위", (b) "예선 기간 내 완성 목표", (c) "본선 후 Phase 2 로드맵". 미구현 항목은 (b) 또는 (c)로 재배치.

**언어 정책 위험 문구 TOP 3** (R14):

| 위치 | 원문 | 문제 | 교체안 |
|---|---|---|---|
| 1안 서두 | "대한민국 복약지도 가이드에 부합하는 응답만을 생성" | 약사법 §24 약사 전속 복약지도를 AI가 수행 선언 → 규제 탈락 리스크 | "대한민국 공인 의약품 데이터(DUR·식약처 허가정보)에 근거한 정보만 인용·안내" |
| 1안/기능명 | "복약지도 에이전트 오케스트레이션" | 금지어 "복약지도" 포함 | "복약 정보 안내 에이전트 오케스트레이션" |
| 2안 | "복약 상담 프로세스", "복약 안전 관리" | 약사법 상담 경계 접근, "관리"는 능동 개입 뉘앙스 | "복약 맥락 수집 대화 프로세스", "복약 이력 기록·정보 안내 서비스" |

**공식 명칭 통일안** (R14): `복약 정보 안내` — 코드 상수 `MEDICATION_INFO_GUIDANCE`로 단일화. "복약 가이드", "복약 안내" 혼용 정리.

**하이브리드 서두 초안** (R14):
> "만성질환·다약제 복용자가 약국 밖에서 이상 증상을 경험할 때, 공인 의약품 데이터(DUR·식약처 허가정보)에 근거해 복용 약물과의 **연관 가능성 정보를 즉시 안내**하는 AI 기반 복약 정보 안내 서비스. 에이전트 오케스트레이션을 통해 사용자의 복약 맥락을 단계적으로 수집하고, 공인 데이터에 기재된 이상반응·상호작용 정보를 **출처와 함께 인용·통합·안내**합니다. 진단·처방·복용 변경 판단은 제공하지 않으며, 의료진 확인을 권고합니다."
> *"필케어는 기록하고, 통합하고, 인용하고, 알립니다. 판단하지 않습니다."*

**6주 실행 계획 재정의** (R15):
- **W7-W8**: Gold set 50-100 (deliverable: CSV), 자동 평가 harness, red-team 20
- **W9**: DUR 6종 확장 (병용금기 + 연령/임부/용량/효능군중복/노인주의) + 회귀
- **W10**: UI 폴리싱 (경고 배지, 출처 인용 UI, 에러 한국어화)
- **W11**: 제안서 5p 초안·리뷰·확정 + 3분 영상 촬영·편집
- **W12**: 최종 QA·배포·FAQ

**4인 분담**: 서희(UI + 영상 모션) / 주현(DUR 6종 + gold set) / 민지(스토리보드·제안서 문제 섹션) / 상훈(평가 harness + red-team + 기술 섹션)

---

## 2. 제안서 v2에 반영할 Critical 결정 (TOP 10)

1. **§2.1 서두 문구**: 1안 제거, 2안 기반 하이브리드 초안 (R14 제공) 채택. "복약지도" 전면 삭제.
2. **§2.2 아키텍처 다이어그램**: Neo4j/Qdrant/OpenSearch 제거 → 실제 스택(SQLite + FTS5 + rapidfuzz + LangGraph 5노드 + Gemini/Claude + Streamlit + Cloud Run)으로 재도식. MedAgentBoard 인용으로 "single-agent+tools" 정당화.
3. **§2.3 주요 기능**: M1-M6 → M1-M4로 축소. VLM OCR·음성·진료브리지(Scope B)·멀티 프로필 삭제/로드맵. 새 M: (M1) 심평원 XLS 투약이력 파싱, (M2) 식약처 3종 + HIRA DUR 8종 통합 DB, (M3) LangGraph 5노드 + 출처 계층 생성, (M4) 5-rule post-verify + NLI/의도분류기 추가.
4. **§2.4 결과물**: React Native 삭제. "Streamlit 웹 POC + Cloud Run 배포 완료 + GitHub Actions CI/CD" 실증.
5. **§2.6 혁신**: 청사진 5개 → 실제 구현 기반 5개로 교체:
   - (A) 국내 최초 **식약처 3종 + HIRA DUR 8종 + 낱알** 통합 SQLite + FTS5 — 법·라이선스·성능 동시 해결
   - (B) **Deterministic DUR + Structured LLM**의 2단 안전 경계 (MedAgentBoard 2025 정합)
   - (C) **Source-tier Citation Enforcement** (T1 공공 ≥1 / T4 AI ≤30%) — 환각 원천 차단
   - (D) **LangGraph Guardrail Loop** — 5 post-verify + CRITICAL retry 자동 escalate
   - (E) **프로덕션 배포 완료** — Cloud Run + Workload Identity + 72 테스트, 심사 즉시 재현 가능
6. **§2.7 도전**: MedHallu (F1 0.625), **MedConf (AUROC 0.5 붕괴, 2026-01 arXiv:2601.15645, Ren et al., NTU+Wuhan)**, KorMedMCQA (MedQA 상관 낮음), ATC-RxNorm 49% 매핑 공백, DUR 8종 중 국내 공백 3개. 각각 PillCare 대응 1줄.
7. **§3.1 W1-W6**: R15 권고 반영. "완료 / 진행 / 로드맵" 3구역 명시. W6 OCR → "XLS 업로드로 대체".
8. **§3.2 12주 마일스톤**: M1-M3 재산정. 현재 W6/12 도달. 남은 6주 W7-W12는 평가·확장·UI·제안서·영상에 집중.
9. **§3.3 스택**: 4 레이어 → **현재 구현 스택 (Python 3.11/uv, LangGraph 1.1.6, Gemini 2.5 Flash via Vertex, Claude Sonnet 4.6 fallback, SQLite + FTS5, rapidfuzz, Pydantic 2.13, Streamlit 1.45, GCP Cloud Run + Artifact Registry + Workload Identity, GitHub Actions)**. Phase 2 로드맵 스택은 별도 박스.
10. **§3.4 평가 계층 신설**: Langfuse Cloud trace + RAGAS faithfulness/context-precision + 자체 gold set 200 케이스(해커톤 목표) — 심사 "재현 가능 평가 증거" 대응.

---

## 3. 제안서 §4 파급효과 재작성 시 반영 예정 (다음 라운드)

- 2안 서두의 최신 통계 (2025-06 기준 171만 7천 명, OECD 64.2%, 5+ 18%/25%, 11+ 45%/54%, 이상사례 27만 7천건 +9.4%)
- 2025 ChatGPT Medical 출시 + MedConf 벤치 인용
- HIRA 건강정보고속도로 1,263개소 2025 하반기 로드맵
- 파트너십 Tier A/B/C 명시 (R09)

---

*본 종합은 `docs/superpowers/specs/2026-04-17-pillcare-proposal-v2-design.md` 작성의 근거 문서로 사용된다.*
