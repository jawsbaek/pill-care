# Track 6 — UDKG + Grounded RAG + Agent 기술 딥다이브

## 개요
필케어의 핵심 3레이어(UDKG · Grounded RAG · Tool-use Agent) 결합 지점에서 frontier 수준의 기술 도전을 정량적으로 정리한다. 2024–25년 Nature/ACL/EMNLP/NeurIPS/ICLR 최신 연구와 공식 lab 블로그를 근거로, (i) 국내 공공 DB와 국제 KG의 스키마 정합 · entity resolution, (ii) citation-enforced medical RAG와 graph RAG의 최신 벤치마크 지형, (iii) medical multi-agent 아키텍처(AMIE/MDAgents/MedAgents/EHRAgent)의 구체적 패턴, (iv) KG-augmented agent의 라우팅/충돌 해결/text-to-Cypher 정확도 한계, (v) medical hallucination·trajectory 평가 공백을 다룬다. 심사위원이 "그래서 뭐가 어려운데?"라고 물었을 때 답할 수 있는 정량 근거(예: MedHallu hard F1 0.625, KorMedMCQA vs MedQA 상관 낮음, Text2Cypher 대규모 KG 60% 실행 정확도, ATC↔RxNorm 49% 매핑)와 아키텍처 개선 제안을 제공한다.

---

## Q1. UDKG 구축 기술 도전

### 핵심 도전 (5개)
- **C1-1. 한국 약물 entity resolution 공백**: 브랜드/제네릭/성분/한글/영문/한자 혼용으로 식약처 3종 DB 내부에서도 동일 성분이 서로 다른 표기로 존재. 국제 표준(RxNorm CUI, ATC)로 매핑할 공개 사전이 없음. [난이도: High] — John Snow Labs Healthcare NLP 5.5.0(`medmebed_large_rxnorm_augmented`, 2024-11)이 영어권 bge_medembed_large_v0.1 임베딩 기반 RxCUI resolver를 제공하지만 한국어 대응은 부재. 한국어에서는 **별도의 fine-tune 및 spell-correction + casing normalization 파이프라인**이 선행되어야 함 (Spark NLP, Medical Concept Normalization chapter, Springer 2024).
- **C1-2. ATC↔RxNorm 브릿지의 구조적 커버리지 공백**: OHDSI 표준 어휘는 UMLS Metathesaurus보다 ATC↔RxNorm 매핑이 많지만, RxNorm 단일 성분 3,166개 중 **단 49%(1,552개)만 5th-level ATC 코드에 매핑**된다 (OHDSI 2019 poster, Elsevier IJMI 2024 Kury et al.). ATC는 substance 기반·드럭 조합은 종종 미지정이라 "precise ingredient"/조합제제는 구조적으로 fallback이 필요. [난이도: High]
- **C1-3. PrimeKG 스키마와 한국 DB의 schema alignment**: PrimeKG는 10개 노드 타입(Disease·Protein·Drug·Phenotype·Pathway·Exposure 등) · 30개 엣지 타입 · 129,375 노드 · 4,050,249 엣지로 구성 (Chandak et al., Scientific Data 2023). 반면 식약처 DUR은 "병용금기/연령금기/임부금기" 3개의 관계 타입만 존재하고 mechanism·pathway 정보가 없어 **relation type alignment가 1:N 또는 N:0 공백**이 큼. 해결하려면 Hetionet/PrimeKG의 `interacts_with`/`contraindication` 엣지로 반매핑이 필요. [난이도: Med]
- **C1-4. Temporal graph 설계 (복약 시작·중단·빈도)**: 복약 이력을 KG에 표현하려면 정적 ontology와 동적 patient event가 공존해야 함. 최신 MedTKG (CEUR-WS Vol-3833, 2024) / KGDNet (Scientific Reports 2024) 등은 **admission-wise patient KG + temporal edge**를 쓰며, ACM Web Conf 2024 "Temporal Knowledge Graph Extraction…Health Risk Prediction"은 time-point/interval 엣지 annotation 패턴을 제시. 그러나 개인 복약 스케줄(e.g., "혈압약 6개월 복용 후 중단")은 기존 연구가 EHR inpatient 기반이라 **outpatient 복약 reminder 도메인 샘플이 없음**. [난이도: High]
- **C1-5. Graph DB vs 하이브리드 저장소 선택 기준**: Graph RAG 최신 구현은 대체로 **Neo4j + vector store(Qdrant/Weaviate) + BM25 sparse**의 3-way hybrid로 수렴 중 (Microsoft GraphRAG GitHub 2024, LlamaIndex KnowledgeGraphRAG). 엔티티 당 한국어 동의어 10+개 · 300만 건 엣지 규모라면 Neo4j community edition은 충분하나, Cypher QPS 병목과 벡터 결합 쿼리의 계획 최적화가 취약. [난이도: Med]

### 최신 기법 맵
- **PrimeKG** (Chandak et al., Scientific Data 2023, nature.com/articles/s41597-023-01960-3): 10 scale · drug indication/contraindication/off-label 엣지 풍부.
- **Hetionet** (Himmelstein et al., 47,031 노드 · 11 타입 · 29 관계): 약물 부작용·메커니즘 보조 소스로 결합.
- **KGDNet** (Scientific Reports 2024, PMC11511869): longitudinal EHR + 온톨로지 + DDI 통합 admission-wise KG.
- **MedTKG** (CEUR-WS Vol-3833, 2024): 정적 의료 온톨로지 + 동적 환자 이력 TKG 구조.
- **John Snow Labs `medmebed_large_rxnorm_augmented`** (2024-11, BGE medembed 기반 RxCUI resolver).
- **OHDSI ATC↔RxNorm Extension mapping** (OHDSI Standardized Vocabularies + UMLS Metathesaurus 비교 연구 Elsevier IJMI 2024): 매핑 커버리지 정량 근거.

### 필케어 적용 전략
- **3-tier entity resolution 파이프라인**: (1) 식약처 품목기준코드(SKU-level) → (2) 성분(KD코드) → (3) ATC5 → (4) RxNorm CUI. ATC 커버리지 공백 49%에 대비해 **RxNorm Extension + DailyMed SPL ingredient 명으로 2차 fallback** + 한국어 동의어 사전 자체 구축(식약처 묶음의약품 성분명·영문 병기 활용).
- **PrimeKG 스키마를 upper ontology로 채택**: 식약처 DUR·심평원 DUR의 3종 금기 관계를 PrimeKG `interacts_with`/`contraindication`/`side_effect` 엣지로 매핑하고, mechanism 정보는 PrimeKG `target_gene → pathway` 경로를 borrow.
- **Temporal 엣지 표현**: 환자 프로필 노드에서 `Drug`으로 향하는 `takes` 엣지에 `(start_ts, end_ts, frequency, dose)` property를 달고, 순간 관찰(증상 로그)은 `Symptom` 노드 + `observed_at` 엣지로 분리 (MedTKG 패턴 차용).
- **저장소 스택**: Neo4j 5.x(community) + Qdrant(벡터) + OpenSearch(BM25), Cypher+벡터 혼합 쿼리는 Neo4j `db.index.vector.queryNodes`로 단일 플랜 유지.

---

## Q2. Grounded RAG for Medical 기술 도전

### 핵심 도전 (5개)
- **C2-1. Citation enforcement와 post-rationalization 문제**: Self-RAG (Asai et al., ICLR 2024 Spotlight, selfrag.github.io)는 reflection token으로 inline citation 정확도를 올리지만, 최근 arXiv:2412.18004 ("Correctness is not Faithfulness", 2024-12)는 **인용의 최대 57%가 post-rationalized**(모델이 생성 후 인용을 사후 붙임)임을 보인다. 의료 도메인에서는 "문장당 1개 근거 소스" 강제만으로는 부족하고 **NLI 기반 faithfulness 검증** 단계가 필수. [난이도: High]
- **C2-2. Medical RAG의 "lost-in-the-middle" 효과와 log-linear 스케일링**: MedRAG/MIRAGE (Xiong et al., ACL Findings 2024, 1.8T 프롬프트 토큰 · 41개 조합 실험)는 GPT-3.5가 GPT-4급으로 올라가지만 context 길이에 따라 **중간 위치 evidence가 무시**되며, 반복 성능이 log-linear로만 증가한다는 한계를 정량적으로 보고. i-MedRAG (arXiv:2408.00727, PSB 2025)는 iterative follow-up query로 MedQA zero-shot 69.68%까지 끌어올리지만 latency 증가를 감수. [난이도: High]
- **C2-3. Graph RAG vs Text RAG의 의료 도메인 라우팅**: Microsoft GraphRAG (arXiv:2404.16130, 2024-04)는 community summary 기반 global sensemaking에 강하지만 약물 상호작용 같은 **local·symbolic 관계 질의**에는 overhead. Medical Graph RAG (arXiv:2408.04187, ACL 2025)의 Triple Graph Construction + U-Retrieval이 의료용 graph RAG의 state-of-the-art이며, 9개 medical Q&A + 2개 health fact-checking 벤치에서 SOTA. MedRAG-KG (arXiv:2502.04413, WWW 2025)는 KG-elicited reasoning을 copilot에 결합. [난이도: Med]
- **C2-4. 한국어 의료 임베딩 성능 공백**: BGE-M3 (BAAI, 2024-01)는 다국어·8192 토큰·dense+sparse+ColBERT multi-func를 동시 지원하고, BGE-reranker-v2-m3는 biomedical BioASQ 파이프라인에 실제 투입 (CEUR-WS 2024 Vol-4038). 그러나 한국어 의료 도메인에서의 성능 지표는 공개되지 않아 **필케어가 자체 Dev 셋(KorMedMCQA 발췌 + 식약처 DUR 규칙)으로 측정해야** 함. [난이도: Med]
- **C2-5. Faithfulness 후검증 스택의 부재**: SelfCheckGPT (Manakul et al., EMNLP 2023 · arXiv:2303.08896) NLI variant가 zero-resource로 sentence-level 환각을 탐지하지만 agent tool output까지는 커버하지 않음. FActScore · ACLE · Attributed QA 등은 citation-level 평가용. 의료 도메인에서 **tool-output → generated-sentence chain의 faithfulness 검증** 공개 구현이 없음. [난이도: High]

### 최신 기법 맵
- **Self-RAG** (Asai et al., ICLR 2024): reflection token 기반 self-critique.
- **MedRAG / MIRAGE** (Xiong et al., ACL Findings 2024, arXiv:2402.13178): 7,663 medical QA, 41 RAG 조합, CoT 대비 최대 +18%.
- **i-MedRAG** (Xiong et al., PSB 2025, arXiv:2408.00727): iterative follow-up query → MedQA 69.68%.
- **Medical Graph RAG / MedGraphRAG** (Wu et al., ACL 2025, arXiv:2408.04187): Triple Graph + U-Retrieval, 9 benchmark SOTA.
- **Microsoft GraphRAG** (arXiv:2404.16130): community hierarchy + two-stage index.
- **BGE-M3 · BGE-reranker-v2-m3** (BAAI, 2024): 다국어 hybrid retrieval.
- **SelfCheckGPT NLI** (EMNLP 2023): zero-resource 환각 탐지.

### 필케어 적용 전략
- **Citation-enforced generation layer**: Self-RAG reflection token + "NO_EVIDENCE → DEFER_TO_CLINICIAN" rule. 인용 없이 생성 시 response를 차단하고 `draft_clinician_brief` tool로 escalate.
- **라우터 2단계**: (A) 질문 분류기(약물 상호작용·성분·복약 스케줄·증상 해석) → (B) 각 카테고리에 `KG_only / text_only / hybrid` 전략 매핑. 약물 상호작용은 DUR 룰 KG 우선, 성분 설명은 DailyMed/식약처 텍스트, 증상-약물 연결은 PrimeKG path traversal.
- **Retrieval 스택**: BGE-M3 dense + BM25(OpenSearch) sparse → RRF 결합 → BGE-reranker-v2-m3 (top-32 → top-6). 한국어 의료 도메인 추가 fine-tune은 v2 이후.
- **Faithfulness 후검증**: 생성된 문장별 NLI(BGE-M3 encoder + DeBERTa-v3 NLI) 엔트레일먼트 ≥ 0.75 미달 시 재생성 or deferral. SelfCheckGPT 샘플링(5회)로 consistency 2차 가드.

---

## Q3. Tool-use Agent 기술 도전

### 핵심 도전 (5개)
- **C3-1. Medical agentic 패턴 선택의 trade-off**: ReAct (Yao et al., ICLR 2023)는 단순·투명하지만 환각 loop에 취약, Plan-and-Execute (LangChain 2024)는 계획-실행 분리로 latency↑, Reflexion (Shinn et al., NeurIPS 2023)은 실패 경험 reflection으로 정확도↑이지만 stateful memory 필요. MDAgents (Kim et al., NeurIPS 2024 Oral, arXiv:2404.15155)는 **질문 복잡도(low/mod/high)에 따라 PCC→MDT→ICT 구조를 자동 선택**해 10개 벤치 중 7개에서 SOTA, 평균 +4.2% (p<0.05), moderator+external knowledge 결합 시 +11.8%. [난이도: Med]
- **C3-2. Multi-tool orchestration 정확도**: ToolBench (Qin et al., ICLR 2024 Spotlight, 16k+ API) 상위 모델 pass rate ~70% 수준. TRAJECT-Bench (arXiv:2510.04550, 2025)는 **trajectory-level tool selection · argument correctness · dependency/order satisfaction** 지표를 도입해 "최종 정답이 맞아도 경로가 틀린" 케이스를 드러냄. API-Bank (Li et al.)는 73 tool · 314 다이얼로그 · 753 API 호출 평가 인프라를 제공. [난이도: High]
- **C3-3. EHR/KG 복합 tool 추론의 코드 집약성**: EHRAgent (Shi et al., EMNLP 2024 Main, arXiv:2401.07128)는 **LLM이 Python 코드를 생성·실행**해 3개 multi-tabular EHR 벤치에서 success rate +29.6% 개선. 그러나 코드 실행은 sandbox · PII 마스킹 · 의료 데이터 유출 방지가 추가 요구사항. [난이도: High]
- **C3-4. 장기 horizon temporal reasoning**: AMIE (Tu et al., Nature 2025, nature.com/articles/s41586-025-08866-7)는 standalone top-10 accuracy 59.1% vs unassisted clinicians 33.6% (p=0.04). 최근 longitudinal disease management 확장(research.google/blog/from-diagnosis-to-treatment-…, 2025-03)은 **여러 세션에 걸친 치료 변경·증상 추이**를 reasoning 컨텍스트에 포함. 필케어처럼 2주-수개월 복약 순응도 추적은 AMIE longitudinal 버전과 유사한 **profile-scoped persistent memory**가 필요. [난이도: High]
- **C3-5. Agent memory와 profile isolation**: 프로필별 대화 연속성은 요청자가 여러 가구원(부모/본인/아이)을 관리할 때 필수. mem0/LangGraph checkpoint/LlamaIndex Memory 등 최신 구현이 있으나 **"약물 이력 ≠ 다른 프로필" 경계 위반**은 safety bug로 직결. [난이도: Med]

### 최신 기법 맵
- **AMIE** (Tu et al., Nature 2025): self-play simulated dialogue, top-10 diagnosis 59.1%.
- **MDAgents** (Kim et al., NeurIPS 2024 Oral): 복잡도 기반 collaboration 구조 자동 선택, 10 벤치 중 7 SOTA.
- **MedAgents** (Tang et al., ACL 2024 Findings, arXiv:2311.10537): role-playing 도메인 전문가 에이전트 협업.
- **EHRAgent** (Shi et al., EMNLP 2024 Main): code-as-action, +29.6% success rate.
- **ReAct / Reflexion / Plan-and-Execute**: 2023-24 표준 패턴.
- **ToolBench · API-Bank · TRAJECT-Bench · AgentBench · AgentBoard** (NeurIPS 2024 D&B): tool use 평가 벤치.

### 필케어 적용 전략
- **MDAgents-lite 복잡도 게이트 채택**: (L) 단순 "약 뭐예요?" → 단일 ReAct · (M) "이 약 2개 같이 먹어도 돼요?" → planner + check_dur + search_drug 체인 · (H) "어머니가 당뇨·고혈압·혈압약 중단하고 싶어해요" → clinician brief escalation.
- **Tool dependency graph 정적 정의**: `search_drug → (cross-check pill ID) → get_history → check_dur → cite_sources → draft_brief` DAG를 compile-time에 정의하고 LangGraph로 실행, 불필요한 LLM freedom 축소.
- **Code-as-action은 sandboxed restricted Python**: EHRAgent 패턴 채택하되 약물 용량 계산·시간 diff 등 결정적 계산만 코드로, KG 쿼리는 predefined template.
- **Profile-scoped memory**: SQLite + row-level profile_id filter, LangGraph checkpoint에 profile_id를 강제. cross-profile 테스트 케이스를 red-team suite에 포함.

---

## Q4. UDKG + RAG + Agent 통합의 unique 도전

### 핵심 도전 (4개)
- **C4-1. KG vs Text retrieval 동적 라우팅**: Medical Graph RAG U-Retrieval (ACL 2025)은 top-down precise + bottom-up refinement로 "global vs local"을 조절하지만, **질의마다 KG/텍스트 비중을 다르게** 결정하는 명시적 classifier는 아직 미성숙. LlamaIndex `RouterQueryEngine`, LangChain `MultiRetrievalQAChain` 등이 rule-based 라우팅을 제공하나 의료 도메인 정확도는 검증 부족. [난이도: High]
- **C4-2. Evidence ranking과 source conflict resolution**: 한 응답에 DUR 규칙(강제)+RxNorm 정의(중립)+FAERS 통계(관찰 빈도)가 혼재할 때 **규범적 vs 통계적 근거의 weighting 규칙**이 필요. 식약처 DUR과 OpenFDA가 상충 시(예: 식약처 병용금기 vs FDA label만 warning) 한국 사용자에게는 식약처 우선이어야 하며, MedGraphRAG의 credible source tiering이 참고 가능하지만 KR 규범을 우선하는 rule은 직접 작성 필요. [난이도: High]
- **C4-3. Text-to-Cypher/SQL 의료 도메인 정확도 한계**: Text2Cypher 연구(arXiv:2412.10064, 2024-12)·CypherBench(arXiv:2412.18702)에 따르면 **GPT-4o 실행 정확도 72.1%**, llama3:70b 프롬프트 엔지니어링 시 74%, 그러나 **대규모 property graph에서는 best 모델도 60.18%**, 10B 미만 오픈소스는 20% 미만. 필케어에서는 자연어 질의를 직접 Cypher로 변환하지 않고 **template-based KG API**(tool wrapper)를 두는 것이 안전. [난이도: High]
- **C4-4. Agent의 KG path traversal 설명 생성**: "A약과 B약이 병용금기인 이유"를 mechanism 경로로 설명하려면 Drug→Target→Pathway→Drug 경로 추출이 필요. PrimeKG는 이런 경로를 제공하지만 **자연어 설명으로 풀어주는 step**에서 환각이 빈발. MedGraphRAG Triple Graph는 이를 정의+소스로 grounding하는 접근. [난이도: Med]

### 최신 기법 맵
- **Medical Graph RAG U-Retrieval** (ACL 2025, arXiv:2408.04187): top-down + bottom-up hybrid.
- **Microsoft GraphRAG community hierarchy** (arXiv:2404.16130): global sensemaking.
- **LlamaIndex KnowledgeGraphRAGQueryEngine / RouterQueryEngine**: 실제 라우팅 레퍼런스 구현.
- **CypherBench · Text2Cypher** (arXiv:2412.18702 / 2412.10064): text-to-query 정량 평가.
- **MedRAG-KG** (arXiv:2502.04413, WWW 2025): KG-elicited reasoning for healthcare copilot.

### 필케어 적용 전략
- **Query router classifier**: 소형 LLM (예: Qwen2.5-7B-Instruct) + 12개 카테고리 지도 학습. 각 카테고리에 {KG tool set, text retriever set} 매핑.
- **Evidence tier 규칙**: (Tier 1) 식약처 DUR·허가사항 → (Tier 2) KFDA 묶음의약품 기본 정보 → (Tier 3) DailyMed/RxNorm 정의 → (Tier 4) PrimeKG mechanism → (Tier 5) FAERS 관찰 통계. 상충 시 higher tier가 cite되고 lower tier는 "참고" 라벨.
- **No text-to-Cypher at inference**: agent는 `kg.interaction(drug_a, drug_b)` 같은 typed tool만 호출하고, Cypher template은 서버 측에서 고정. Text2Cypher는 오프라인 KG build 단계에서만 사용.
- **Mechanism explanation**: PrimeKG path를 꺼낸 뒤 텍스트 템플릿(`{drug_a}가 {target}을 저해하고, {drug_b}도 같은 {pathway}에 작용하여 {effect}`)으로 rendering, 자유 생성 최소화.

---

## Q5. 평가·검증 기술 도전

### 핵심 도전 (5개)
- **C5-1. Medical hallucination 탐지의 하드 케이스 공백**: MedHallu (Pandit et al., arXiv:2502.14302, EMNLP 2025)는 10,000 QA 쌍, easy/medium/hard 3-tier. **GPT-4o·Llama-3.1·UltraMedical 모두 "hard" tier F1 0.625 수준**이며, "not sure" 카테고리 도입 시 최대 +38% 개선. Med-HALT (Pal et al., medhalt.github.io)는 다국적 의사 시험 기반 multi-modal test. 필케어가 "약물 상호작용"에 국한해 자체 hard suite를 구축해야 함. [난이도: High]
- **C5-2. KorMedMCQA vs MedQA 상관성 부재**: KorMedMCQA (Kweon et al., arXiv:2403.01469, 7,469 questions, 의사·간호사·약사·치과의사 면허시험 2012-24)의 연구 결과는 **MedQA와의 점수 상관이 "다른 도메인 벤치와 차이 없음" 수준**이라 한국 의료 컨텍스트에서 별도 benchmark가 필수임을 정량적으로 입증. o1-preview 92.72 / Qwen2.5-72B 78.86 / CoT 최대 +4.5%. 그러나 **KorMedMCQA는 면허시험 MCQ이고 약물 상호작용/복약 관리 도메인은 적음**. [난이도: High]
- **C5-3. Agent trajectory 정합성 평가 부재**: AgentBench (Liu et al., ICLR 2024, THUDM/AgentBench)는 8개 환경이지만 의료 없음. AgentBoard (NeurIPS 2024 D&B, proceedings.neurips.cc)는 multi-turn progress rate 도입. TRAJECT-Bench (arXiv:2510.04550)는 tool dependency/order satisfaction까지 측정. **의료 tool 호출 순서 정합성 벤치는 공개 부재** — 필케어가 자체 evaluation harness로 tool call trace를 기록·비교해야 함. [난이도: High]
- **C5-4. Attribution-ground truth faithfulness 측정**: SelfCheckGPT NLI (EMNLP 2023) · FActScore (Min et al., EMNLP 2023) · Correctness-vs-Faithfulness 연구(arXiv:2412.18004, 57% post-rationalized)는 **"정답이 맞아도 인용 근거가 실제로 그 답을 뒷받침하지 않는" 비율**을 드러냄. 필케어 3-gate 평가(tool 경로 · 최종 답 · 인용 근거) 필요. [난이도: High]
- **C5-5. Medical red-teaming 체계**: medRxiv "Red-Teaming Medical AI: Systematic Adversarial…" (2026-02)는 adversarial category taxonomy + 단일/다중 턴 escalation suite를 제시. 필케어의 red-team 케이스는 (a) 자기 진단 유도, (b) 처방 용량 변경 요청, (c) cross-profile 정보 노출, (d) DUR 우회, (e) 유사 약명 혼동 유발, (f) 한국 규제 경계 넘기 — 최소 6개 카테고리. [난이도: Med]

### 최신 기법 맵
- **MedHallu** (arXiv:2502.14302, EMNLP 2025): 10k QA, tier별 F1, GPT-4o hard 0.625.
- **Med-HALT** (medhalt.github.io): multi-modality 환각 테스트.
- **MedHallBench** (arXiv:2412.18947): 의료 환각 평가.
- **KorMedMCQA** (arXiv:2403.01469): 7,469 한국 면허시험 QA.
- **MIRAGE** (ACL Findings 2024): 7,663 의료 RAG 평가.
- **AgentBench · AgentBoard · TRAJECT-Bench**: agent trajectory 평가.
- **SelfCheckGPT NLI · FActScore**: faithfulness 평가.

### 필케어 적용 전략
- **Evaluation harness (3 gate)**:
  1. **Trajectory gate**: tool 호출 시퀀스가 DAG 템플릿과 일치 (TRAJECT-Bench 스타일).
  2. **Factuality gate**: 생성 문장을 NLI로 retrieved evidence와 대조(entailment≥0.75), SelfCheckGPT 샘플링 2차 가드.
  3. **Safety gate**: 금칙 키워드 + 자기처방 유도 + cross-profile 누수 red-team 스위트.
- **자체 Dev 셋 구축**: 식약처 DUR 룰 랜덤 샘플 200건 + KorMedMCQA 약물/약학 파트 발췌 + PrimeKG 경로 설명 200건 = 약 600 케이스의 gold set.
- **MedHallu "hard tier" 벤치마킹**: 영어이지만 필케어 LLM에 동일 프롬프트 적용해 baseline F1 측정 후 "not sure" 옵션 도입 효과를 정량 비교 (논문 보고 최대 +38%).

---

## ★ 제안서 2.6 혁신 강화 제안

기존 2.6 A~D(UDKG, Grounded RAG, Tool-use Agent, Profile memory 등)에 추가/교체 가능:

- **혁신 E — Evidence-Tiered Citation Enforcement**: 식약처 DUR(Tier 1) → RxNorm/DailyMed(Tier 2) → PrimeKG mechanism(Tier 3) → FAERS 통계(Tier 4)의 4-tier 인용 우선순위 강제 + NLI faithfulness gate. Self-RAG (ICLR 2024) + Correctness-vs-Faithfulness(arXiv:2412.18004, 57% post-rationalized 문제)를 동시에 해결하는 사례는 공개되지 않음 → **frontier 기여점**.
- **혁신 F — MDAgents-Lite 복잡도 게이트**: 질문 복잡도(L/M/H)에 따라 solo ReAct / multi-tool planner / clinician-escalation 경로를 자동 라우팅. MDAgents (NeurIPS 2024 Oral) 패턴을 웰니스 영역 · 한국어 · 비의료기기 경계 내로 제한해 적용한 첫 사례.
- **혁신 G — Temporal Profile-Scoped KG**: 복약 시작·중단·빈도를 환자 프로필 노드의 temporal edge로 표현해 "2주 전부터 혈압약 복용 중 + 어제부터 기침" 같은 시계열 상관을 KG 경로로 풀어냄 (MedTKG + KGDNet 패턴의 outpatient 복약 첫 적용).
- **혁신 H — Template-based KG API (Text-to-Cypher 회피)**: 대규모 의료 KG에서 LLM text-to-Cypher 정확도 60% 수준(CypherBench)의 위험을 회피하기 위해 `kg.interaction(drug_a, drug_b, reason=True)` 같은 typed tool만 노출. **정확도·안전성·감사 가능성 3-win**.
- **혁신 I — 4-tier Zero-License-Risk KG 브릿지**: 식약처(이용허락 제한 없음) + 심평원 DUR(KOGL1) + OpenFDA(CC0) + RxNorm(PD) + DailyMed(PD) + PrimeKG(CC BY) + Hetionet(CC0)을 ATC 기반 브릿지로 통합. **한국에서 이 수준의 라이선스·규제 정합 통합 KG 공개 사례는 부재**.

---

## ★ 제안서 2.7 도전 강화 제안

기존 2.7(①선행 사례 부재 ②의료 환각 F1 0.625 ③ID 매핑 공백 ④규제)을 다음으로 보강:

- **도전 ①': ATC↔RxNorm 커버리지 49%**: OHDSI Std Voc 분석(Elsevier IJMI 2024)에서 RxNorm 단일 성분 3,166개 중 ATC5 매핑은 1,552개(49%). 필케어는 이 51% gap을 RxNorm Extension + DailyMed SPL ingredient + 자체 KR 성분 사전으로 메워야 하며 **성분·조합제제 단위 fallback 알고리즘이 공개된 사례 없음**.
- **도전 ②': MedHallu hard tier F1 0.625 한계**: GPT-4o/Llama-3.1/UltraMedical 모두 hard 환각 탐지 F1 0.625, "not sure" 옵션 추가 시 최대 +38% 개선 가능성(MedHallu arXiv:2502.14302). 필케어는 **defer-to-clinician 게이트를 "not sure" 역할로 활용**해 정량 개선을 목표 삼는다.
- **도전 ③': Text-to-Cypher 대규모 KG 60% 실행 정확도**: CypherBench(arXiv:2412.18702) 결과로 자연어 직접 쿼리는 의료 도메인에서 안전성 미달. 필케어는 **template-only KG API**로 이 한계를 우회하되, 오프라인 build 단계에서만 LLM을 사용.
- **도전 ④': Citation post-rationalization 57%**: arXiv:2412.18004에 따르면 LLM 인용의 최대 57%가 사후 합리화. 의료 도메인에서 이는 "정답이 맞아도 근거가 허위"를 의미하므로 **NLI faithfulness gate 필수**. 필케어 evaluation harness는 문장 · 인용 · tool trace 3축으로 측정.
- **도전 ⑤': KorMedMCQA-MedQA 상관 부재**: KorMedMCQA 연구(arXiv:2403.01469) 결과 한국 의료 벤치 점수가 MedQA와 "다른 도메인 수준"으로 decorrelate. 즉 **영어 의료 SOTA가 한국에서 동일하게 성립 안 함** → 한국어 의료 harness 자체 구축이 frontier 도전.
- **도전 ⑥': Agent trajectory의 의료 공개 벤치 부재**: AgentBench(ICLR 2024) 8개 환경 중 의료 없음, TRAJECT-Bench(arXiv:2510.04550)는 일반 도메인. 필케어는 **의료 tool 호출 DAG 정합성 평가** 자체 제작이 필수.

---

## ★ 2.2 아키텍처 다이어그램 보강 제안

현재 5 레이어(입력 → 지각 → UDKG → Agent Core → 액션)에 추가·분해:

- **보강 1 — Query Router 노드 (Agent Core 앞단)**: 질문 복잡도(L/M/H)와 카테고리(약물 상호작용/성분/복약 스케줄/증상 해석)를 분기. 위치: Agent Core 입력 전. 이유: MDAgents 복잡도 게이트 · LlamaIndex Router 패턴 반영.
- **보강 2 — Retrieval Hub (UDKG 앞)**: `BM25 sparse(OpenSearch)` + `Dense(BGE-M3 + Qdrant)` + `KG tool API(Neo4j)` 3-way hybrid 박스. 위치: UDKG 내부 또는 앞단. 이유: 단순 "UDKG" 박스만으로는 retrieval 전략이 불투명.
- **보강 3 — Faithfulness Gate (Agent Core ↔ 액션 사이)**: NLI(DeBERTa-v3) + SelfCheckGPT 샘플링 + Citation tier checker. 위치: Agent Core 출력 후 액션 전. 이유: citation post-rationalization 57% 문제 해결.
- **보강 4 — Evidence Tier Classifier**: DUR/OpenFDA/PrimeKG/FAERS 소스 태깅 및 tier ranking. 위치: Retrieval Hub 출력. 이유: 소스 충돌 해결·감사 가능성.
- **보강 5 — Profile-scoped Memory Store**: SQLite + row-level profile_id + LangGraph checkpoint. 위치: Agent Core 우측. 이유: cross-profile 누수 방지 (safety).
- **보강 6 — Evaluation Harness (외부 박스)**: Trajectory gate + Factuality gate + Safety gate. 위치: 전체 파이프라인을 감싸는 CI 박스. 이유: 3.1 세부업무와 연결.

---

## ★ 3.1 구현 범위 세부업무 제안

- **세부업무 1 — UDKG Builder Pipeline**
  - 기술 스택: Python/uv, RDFLib/pykeen, Neo4j 5.x, Pandas, 식약처 OpenAPI 클라이언트, DailyMed FTP bulk, OpenFDA download, PrimeKG dump
  - 도전 요소: 한국 성분↔RxNorm 사전 자체 구축(49% ATC gap 해결), DUR 관계 타입→PrimeKG schema alignment, 증분 업데이트
- **세부업무 2 — Hybrid Retrieval & Graph RAG Engine**
  - 기술 스택: BGE-M3, BGE-reranker-v2-m3, Qdrant, OpenSearch BM25, Neo4j, LangChain MultiRetrievalQAChain 또는 LlamaIndex RouterQueryEngine
  - 도전 요소: KR 의료 도메인 임베딩 성능 측정(공개 지표 부재), 4-tier evidence ranking 구현, lost-in-the-middle 방지 재정렬
- **세부업무 3 — Agentic Orchestration (MDAgents-Lite + Tool DAG)**
  - 기술 스택: LangGraph, Anthropic tool_use/OpenAI function_calling, SQLite memory, 사내 Python sandbox(RestrictedPython)
  - 도전 요소: 복잡도 게이트 분기 정확도, tool dependency graph compile-time 정의, profile_id 격리
- **세부업무 4 — Faithfulness & Safety Gate**
  - 기술 스택: DeBERTa-v3 NLI, SelfCheckGPT 샘플링, Regex/LLM guard, Citation tier classifier
  - 도전 요소: NLI 임계값 튜닝, defer-to-clinician trigger, red-team 6 카테고리
- **세부업무 5 — Evaluation Harness (3-Gate CI)**
  - 기술 스택: pytest + evaluate lib, WandB/MLflow, 자체 gold set(식약처 DUR 샘플 200 + KorMedMCQA 약물 파트 + PrimeKG 경로 설명 200)
  - 도전 요소: tool trajectory diff 알고리즘, MedHallu hard tier 한국어 대응본 구축, red-team 자동화
- **세부업무 6 — Pill Image & OCR Perception**
  - 기술 스택: YOLOv8(낱알) + ResNet (문자/색/모양) + RNN LM, PaddleOCR 또는 VLM(Qwen2-VL/Gemini), 식약처 낱알 DB
  - 도전 요소: MFDS 벤치 85.65% 한계(JMIR 2023), 약봉투 semi-structured OCR, 다중 약물 교차 검증

---

## 인용 논문·시스템 리스트 (16개, 2023–26)

1. **PrimeKG** · Chandak, Huang, Zitnik · *Scientific Data* · 2023 · https://www.nature.com/articles/s41597-023-01960-3 · 20 리소스 통합 17,080 질병 · 4,050,249 엣지 정밀의료 KG · 필케어 UDKG upper ontology 후보.
2. **MedRAG / MIRAGE** · Xiong et al. · ACL Findings 2024 · arXiv:2402.13178 · https://arxiv.org/abs/2402.13178 · 7,663 의료 QA · 1.8T 토큰 · 41 RAG 조합 비교, CoT 대비 +18% · 필케어 RAG 벤치 기준.
3. **i-MedRAG** · Xiong et al. · PSB 2025 · arXiv:2408.00727 · https://arxiv.org/abs/2408.00727 · iterative follow-up 쿼리 · MedQA 69.68% · 필케어 follow-up 질의 패턴.
4. **Medical Graph RAG (MedGraphRAG)** · Wu et al. · ACL 2025 · arXiv:2408.04187 · https://arxiv.org/abs/2408.04187 · Triple Graph + U-Retrieval, 9 medical 벤치 SOTA · 필케어 graph RAG 참고 구현.
5. **MedRAG-KG** · arXiv:2502.04413 · WWW 2025 · https://arxiv.org/abs/2502.04413 · KG-elicited reasoning for healthcare copilot · 필케어 KG+RAG 통합 패턴.
6. **Microsoft GraphRAG** · arXiv:2404.16130 · 2024 · https://arxiv.org/abs/2404.16130 · community hierarchy + 2-stage index · 필케어 global sensemaking 대비.
7. **Self-RAG** · Asai et al. · ICLR 2024 Spotlight · https://selfrag.github.io · reflection token 기반 self-critique · 필케어 citation enforcement 기반.
8. **Correctness is not Faithfulness** · arXiv:2412.18004 · 2024 · https://arxiv.org/pdf/2412.18004 · LLM 인용 최대 57% post-rationalized · 필케어 faithfulness gate 근거.
9. **AMIE** · Tu et al. · *Nature* 2025 · https://www.nature.com/articles/s41586-025-08866-7 · self-play · top-10 59.1% vs clinician 33.6% · 필케어 longitudinal agent 참고.
10. **MDAgents** · Kim et al. · NeurIPS 2024 Oral · arXiv:2404.15155 · https://arxiv.org/abs/2404.15155 · 복잡도 기반 collab 구조 자동 선택 · 필케어 라우터 핵심.
11. **EHRAgent** · Shi et al. · EMNLP 2024 Main · arXiv:2401.07128 · https://aclanthology.org/2024.emnlp-main.1245/ · code-as-action · +29.6% EHR tabular · 필케어 tool 설계 참고.
12. **ToolBench / ToolLLaMA** · Qin et al. · ICLR 2024 Spotlight · https://github.com/OpenBMB/ToolBench · 16k API · DFSDT · 필케어 tool 벤치.
13. **AgentBench** · Liu et al. · ICLR 2024 · https://github.com/THUDM/AgentBench · 8 환경 LLM-as-Agent 평가 · 필케어 harness 참고(의료 없음).
14. **TRAJECT-Bench** · arXiv:2510.04550 · 2025 · https://arxiv.org/abs/2510.04550 · trajectory-level tool selection/arg/deps 평가 · 필케어 trajectory gate.
15. **MedHallu** · Pandit et al. · arXiv:2502.14302 · EMNLP 2025 · https://arxiv.org/abs/2502.14302 · 10k QA · hard tier F1 0.625 · "not sure" +38% · 필케어 환각 벤치.
16. **KorMedMCQA** · Kweon et al. · arXiv:2403.01469 · 2024 · https://arxiv.org/abs/2403.01469 · 7,469 한국 면허시험 QA · MedQA와 상관 낮음 · 필케어 한국어 의료 harness 근거.
17. **BGE-M3** · BAAI · 2024-01 · https://huggingface.co/BAAI/bge-m3 · 다국어 dense+sparse+ColBERT 통합 · 필케어 retrieval encoder.
18. **SelfCheckGPT** · Manakul et al. · EMNLP 2023 · arXiv:2303.08896 · https://arxiv.org/abs/2303.08896 · zero-resource NLI 환각 탐지 · 필케어 faithfulness 보조.
19. **CypherBench / Text2Cypher** · arXiv:2412.18702 · arXiv:2412.10064 · 2024-12 · text-to-Cypher 대규모 KG 60% 실행 정확도 · 필케어 text-to-query 위험 근거.
20. **OHDSI ATC↔RxNorm 매핑 분석** · Elsevier IJMI 2024 · https://www.sciencedirect.com/science/article/pii/S1386505624004404 · RxNorm 단일 성분 49%만 ATC5 매핑 · 필케어 브릿지 gap 근거.

---

## 참고 URL 로그

- https://www.nature.com/articles/s41597-023-01960-3 (PrimeKG)
- https://github.com/mims-harvard/PrimeKG
- https://arxiv.org/abs/2402.13178 (MedRAG/MIRAGE)
- https://aclanthology.org/2024.findings-acl.372/ (MIRAGE ACL)
- https://github.com/Teddy-XiongGZ/MIRAGE
- https://arxiv.org/abs/2408.00727 (i-MedRAG)
- https://arxiv.org/abs/2408.04187 (MedGraphRAG)
- https://arxiv.org/abs/2502.04413 (MedRAG-KG WWW 2025)
- https://arxiv.org/abs/2404.16130 (Microsoft GraphRAG)
- https://github.com/microsoft/graphrag
- https://selfrag.github.io/
- https://arxiv.org/pdf/2412.18004 (Correctness vs Faithfulness)
- https://www.nature.com/articles/s41586-025-08866-7 (AMIE Nature 2025)
- https://research.google/blog/from-diagnosis-to-treatment-advancing-amie-for-longitudinal-disease-management/
- https://arxiv.org/abs/2404.15155 (MDAgents)
- https://github.com/mitmedialab/MDAgents
- https://arxiv.org/abs/2401.07128 (EHRAgent)
- https://aclanthology.org/2024.emnlp-main.1245/
- https://github.com/OpenBMB/ToolBench
- https://github.com/THUDM/AgentBench
- https://arxiv.org/abs/2510.04550 (TRAJECT-Bench)
- https://arxiv.org/abs/2502.14302 (MedHallu)
- https://medhalt.github.io/
- https://arxiv.org/abs/2403.01469 (KorMedMCQA)
- https://huggingface.co/datasets/sean0042/KorMedMCQA
- https://huggingface.co/BAAI/bge-m3
- https://huggingface.co/BAAI/bge-reranker-v2-m3
- https://arxiv.org/abs/2303.08896 (SelfCheckGPT)
- https://arxiv.org/abs/2412.10064 (Text2Cypher)
- https://arxiv.org/pdf/2412.18702 (CypherBench)
- https://www.sciencedirect.com/science/article/pii/S1386505624004404 (OHDSI ATC↔RxNorm)
- https://pmc.ncbi.nlm.nih.gov/articles/PMC11511869/ (KGDNet)
- https://ceur-ws.org/Vol-3833/paper6.pdf (MedTKG)
- https://dl.acm.org/doi/10.1145/3589335.3651256 (Temporal KG health risk)
- https://nlp.johnsnowlabs.com/2024/11/19/medmebed_large_rxnorm_augmented_en.html
- https://www.jmir.org/2023/1/e41043 (MFDS pill ID 85.65%)
- https://www.medrxiv.org/content/10.64898/2026.02.26.26347212v1.full.pdf (Red-Teaming Medical AI)
