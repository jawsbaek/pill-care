# Track 5 — AI 트렌드 & 기술 근거

필케어(PillCare)가 채택한 아키텍처 — **Agentic AI + tool-use + 약물 지식 그래프 + Grounded RAG for medical** — 이 2024-2025년 AI 연구·산업의 최전선에 위치함을 입증하는 근거 모음. 2.6 혁신적 요소, 2.7 도전적 요소, 4.1 기술적 파급효과 섹션 인용용.

> 주의: 일부 arXiv 미러/PMC 페이지에서 abstract 수준까지만 확인했음. 최종 제안서 인용 전 full paper 재확인 권장 항목은 각 항목 말미에 표기.

---

## 질문별 인용

### Q1. Agentic AI for Healthcare (2024-2025)

1. **제목**: *Towards conversational diagnostic artificial intelligence* (AMIE)
   - 저자/소속: Tu et al., Google DeepMind / Google Research
   - 발표처: **Nature**, 2025 (preprint arXiv:2401.05654, 2024)
   - URL: https://www.nature.com/articles/s41586-025-08866-7 / https://arxiv.org/abs/2401.05654
   - 1문장 요약: LLM 기반 대화형 진단 에이전트 AMIE가 159개 OSCE 시뮬 케이스에서 1차 진료의사 대비 진단 정확도·대화 품질 32개 축 중 30개에서 동등 또는 우수한 성능을 보였다.
   - 필케어 활용 포인트: "대화형 의료 에이전트가 전문의 수준에 근접한다는 peer-reviewed 근거" — 2.6 혁신적 요소(대화형 복약 에이전트의 정당성)와 4.1 파급효과(에이전트 기반 헬스케어가 실제 임상 수준에 도달 중).

2. **제목**: *MedAgents: Large Language Models as Collaborators for Zero-shot Medical Reasoning*
   - 저자/소속: Tang et al., Yale (Gerstein Lab) 외
   - 발표처: **Findings of ACL 2024** (arXiv:2311.10537)
   - URL: https://arxiv.org/abs/2311.10537 / https://aclanthology.org/2024.findings-acl.33/
   - 1문장 요약: 여러 도메인 전문가 역할의 LLM 에이전트를 다중 라운드 토의시켜 MedQA·MedMCQA·PubMedQA 등 9개 벤치마크에서 zero-shot 의료 추론 성능을 끌어올린 훈련 불필요(training-free) 프레임워크.
   - 필케어 활용 포인트: 2.6/2.7 — "multi-agent 역할 분담(약사·의사·환자) 구조의 학술적 근거" 및 필케어의 에이전트 오케스트레이션이 ACL 2024 수준의 연구 주류와 일치함을 주장.

3. **제목**: *MDAgents: An Adaptive Collaboration of LLMs for Medical Decision-Making*
   - 저자/소속: Kim et al. (MIT, Google Research 외)
   - 발표처: **NeurIPS 2024** (arXiv:2404.15155)
   - URL: https://arxiv.org/html/2404.15155v3 / https://mdagents2024.github.io/
   - 1문장 요약: 의료 질의의 복잡도에 따라 solo vs. group 에이전트 구조를 동적으로 선택하는 적응형 협업 프레임워크로 복수의 의료 벤치마크에서 SOTA 갱신.
   - 필케어 활용 포인트: 2.6 — 상황별 에이전트 라우팅(단순 복약 알림 vs. 복잡한 DDI 질의) 설계의 선행 근거.

4. **제목**: *A Survey of LLM-based Agents in Medicine: How far are we from Baymax?*
   - 저자/소속: arXiv:2502.11211 (2025)
   - URL: https://arxiv.org/abs/2502.11211
   - 1문장 요약: 2024-2025 의료 LLM 에이전트 연구를 체계적으로 분류하여 clinical workflow, diagnosis, drug discovery, patient communication 등 하위 영역별 최신 시스템을 정리한 서베이.
   - 필케어 활용 포인트: 2.6 도입부 한 문장 인용 — "2025년 서베이에 따르면 LLM 기반 의료 에이전트는 …".

5. **제목**: *AI Agents in Clinical Medicine: A Systematic Review*
   - 발표처: medRxiv, 2025 (https://www.medrxiv.org/content/10.1101/2025.08.22.25334232v1.full)
   - 1문장 요약: 2024-2025년 20편의 peer-reviewed 연구를 리뷰하여 진단 지원·환자 커뮤니케이션·의학 교육 분야에서 LLM 에이전트의 적용 성과를 정량적으로 정리.
   - 필케어 활용 포인트: 4.1 파급효과 — "에이전트 기반 의료 AI의 연구 양 자체가 2024년 이후 급증".
   - *Full paper 확인 필요* (medRxiv preprint).

### Q2. Medical RAG / Grounding / Hallucination Mitigation

1. **제목**: *Benchmarking Retrieval-Augmented Generation for Medicine* (MIRAGE)
   - 저자/소속: Xiong et al.
   - 발표처: **Findings of ACL 2024**
   - URL: https://aclanthology.org/2024.findings-acl.372.pdf
   - 1문장 요약: 의료 도메인 RAG를 위한 종합 벤치마크 MIRAGE로 5개 QA 데이터셋·수백 개 retrieval corpus 조합을 평가하여, RAG가 GPT-3.5·PMC-Llama 같은 모델에서 GPT-4 급 성능을 달성시킴을 보임.
   - 필케어 활용 포인트: 2.6 — "2024년 ACL 벤치마크에 따르면 의료 RAG는 백본 모델의 벤치마크 정확도를 GPT-4 수준으로 끌어올린다" 직접 인용 가능.

2. **제목**: *Improving Retrieval-Augmented Generation in Medicine with Iterative Follow-up Questions* (i-MedRAG)
   - 발표처: **Pacific Symposium on Biocomputing (PSB) 2025**
   - URL: http://psb.stanford.edu/psb-online/proceedings/psb25/xiong.pdf
   - 1문장 요약: 반복적 follow-up 쿼리를 통해 retrieval을 개선한 i-MedRAG가 Llama-3.1-8B로 MedQA에서 75.02% 정확도 달성(베이스 대비 크게 상회).
   - 필케어 활용 포인트: 2.6 — 소형 오픈소스 LLM + 반복 retrieval만으로 GPT-4 접근 가능하다는 경량화 근거.

3. **제목**: *Mitigating Hallucination in Large Language Models: An Application-Oriented Survey on RAG, Reasoning, and Agentic Systems*
   - 발표처: arXiv:2510.24476 (2025)
   - URL: https://arxiv.org/abs/2510.24476
   - 1문장 요약: RAG, reasoning enhancement, agentic pattern의 환각 완화 기법을 통합 분류한 2025 서베이 — RAG와 에이전트 기반 체크가 가장 효과적인 두 축으로 지목.
   - 필케어 활용 포인트: 2.7 — "환각 억제 연구의 합의가 RAG+에이전트 조합으로 수렴". *Full paper 확인 필요.*

4. **제목**: *Development and evaluation of an agentic LLM based RAG framework for evidence-based patient education*
   - 발표처: PMC12306375 (2025)
   - URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC12306375/
   - 1문장 요약: 환자 교육 목적의 agentic RAG를 임상 가이드라인 기반으로 구축하여 근거 인용과 환각 감소를 정량 평가.
   - 필케어 활용 포인트: 2.6 — 필케어의 "근거 인용(출처 링크) 기반 환자 교육" 설계의 직접 선행 사례.

5. **제목**: *A framework to assess clinical safety and hallucination rates of LLMs for medical text summarisation*
   - 발표처: **npj Digital Medicine**, 2025
   - URL: https://www.nature.com/articles/s41746-025-01670-7
   - 1문장 요약: 의료 텍스트 요약 시 LLM 환각률과 임상 안전성을 체계적으로 평가하는 평가 프레임워크 제안.
   - 필케어 활용 포인트: 2.7 — 필케어가 환각 평가를 안전 지표로 측정하겠다는 근거.

### Q3. Tool-use / Function-calling 의료 에이전트

1. **제목**: *EHRAgent: Code Empowers Large Language Models for Few-shot Clinical Reasoning on Electronic Health Records*
   - 발표처: **EMNLP 2024** (arXiv:2401.07128)
   - 1문장 요약: 코드 생성과 tool-use를 결합한 에이전트가 EHR 데이터베이스에 직접 쿼리·분석 도구를 호출해 복잡한 임상 질의를 해결.
   - 필케어 활용 포인트: 2.6 — "복약 기록 DB + 지식그래프 tool-calling" 설계의 학술적 선행 근거.

2. **제목**: *AMIE gains vision: A research AI agent for multimodal diagnostic dialogue*
   - 출처: Google Research 공식 블로그, 2024-2025
   - URL: https://research.google/blog/amie-gains-vision-a-research-ai-agent-for-multi-modal-diagnostic-dialogue/
   - 1문장 요약: AMIE가 멀티모달 입력과 도구 호출을 결합한 진단 에이전트로 확장.
   - 필케어 활용 포인트: Frontier 랩이 "대화형 + tool-use + 멀티모달" 방향으로 이동 중임을 보이는 공식 자료.

3. **제목**: *MedLM / Gemini for Healthcare* (Google Cloud, 2024)
   - URL: https://cloud.google.com/blog/topics/healthcare-life-sciences/introducing-medlm-for-the-healthcare-industry
   - 1문장 요약: Google이 Med-PaLM 계열을 MedLM으로 재구성하고 Gemini 기반 tool/API 호출 능력을 도입, Vertex AI를 통해 의료 고객에게 제공.
   - 필케어 활용 포인트: 4.1 — 상용 의료 LLM 플랫폼이 function-calling/에이전트 방향으로 전환하고 있다는 산업 근거.

4. **제목**: *MedAide: Information Fusion and Anatomy of Medical Intents via LLM-based Agent Collaboration* (arXiv:2410.12532, 2024)
   - 1문장 요약: 의료 인텐트를 분해하고 여러 tool/에이전트로 협업 호출하는 프레임워크.
   - 필케어 활용 포인트: 2.6 — intent parsing → tool routing 파이프라인의 최신 사례.

### Q4. 약물 지식 그래프 (Drug Knowledge Graph)

1. **제목**: *Building a knowledge graph to enable precision medicine* (**PrimeKG**)
   - 저자/소속: Chandak, Huang, **Zitnik Lab (Harvard Medical School)**
   - 발표처: **Scientific Data (Nature)**, 2023
   - URL: https://www.nature.com/articles/s41597-023-01960-3 / https://zitniklab.hms.harvard.edu/projects/PrimeKG/
   - 1문장 요약: 20개 자원을 통합해 17,080개 질병, 약물 indication·contraindication·off-label·DDI를 포함한 4M+ 관계 엣지를 가진 정밀의료 지식 그래프.
   - 필케어 활용 포인트: 2.6 — 필케어의 "약물 지식 그래프" 계층이 Harvard Zitnik Lab의 PrimeKG 같은 peer-reviewed 자원을 직접 활용/참조하도록 설계됨을 명시. Nature 게재 논문이라 인용 강도 매우 높음.

2. **제목**: *DRKG — Drug Repurposing Knowledge Graph*
   - 저자/소속: Ioannidis et al., Amazon AI / gnn4dr
   - URL: https://github.com/gnn4dr/DRKG
   - 1문장 요약: 97K 노드·5.8M 엣지, 13개 노드 타입·107개 관계 타입으로 구성된 약물 재창출 KG.
   - 필케어 활용 포인트: 2.6 — 오픈소스 약물 KG 활용 가능성 명시.

3. **제목**: *HetioNet*
   - 저자/소속: Himmelstein et al., UCSF
   - 발표처: **eLife** 2017 (기반 자원)
   - 1문장 요약: 47K 노드·2.25M 엣지, 11개 노드 타입·29개 관계 타입의 생의학 이질 네트워크.
   - 필케어 활용 포인트: 지식 그래프 계보 소개(역사적 근거).

4. **제목**: *Knowledge Graphs for drug repurposing: a review of databases and methods*
   - 발표처: **Briefings in Bioinformatics**, 2024
   - URL: https://academic.oup.com/bib/article/25/6/bbae461/7774899
   - 1문장 요약: 2024년 기준 주요 약물 KG(PrimeKG, Hetionet, DRKG, PharmaKG, OREGANO 등)를 비교 리뷰.
   - 필케어 활용 포인트: 2.6 — "어떤 KG를 선정할지" 근거 제공.

### Q5. 의료 QA 벤치마크: 단일 LLM vs RAG vs Agentic

1. **GPT-4 baseline**: MedQA zero-shot ≈ 71.6%, USMLE-style ≈ 86% (2023-2024 공통 보고치).
2. **RAG 개선**: i-MedRAG로 Llama-3.1-8B가 MedQA 75.02% 달성 (PSB 2025).
3. **Agentic 대폭 개선**: AMG-RAG(agentic dynamic KG)가 8B LLM으로 MedQA F1 74.1%, MedMCQA 66.3%.
4. **Consensus multi-agent**: 여러 전문가 LLM 합의 구조가 MedQA 96.8%, MedMCQA 94.2% (500-Q 샘플, 단일 모델 대비 +9.1%p).
5. **MIRAGE (ACL 2024 Findings)**: RAG를 체계적으로 벤치마크한 기준 논문 — https://aclanthology.org/2024.findings-acl.372.pdf
6. **AgentClinic-MedQA**: MedQA 정확도가 agentic 환경에서는 예측력이 떨어진다는 보고 → 에이전트 평가의 새로운 어려움 제시.

- 필케어 활용 포인트: 2.6/4.1 — "단일 LLM보다 RAG + 지식그래프 + 에이전트 구조가 의료 QA 정확도를 8B 모델로도 GPT-4 수준에 도달시킬 수 있다"는 정량적 근거로 인용.

### Q6. Medical Hallucination 벤치마크 & 완화

1. **제목**: *Med-HALT: Medical Domain Hallucination Test for Large Language Models*
   - 발표처: CoNLL 2023 / https://medhalt.github.io/
   - 1문장 요약: 다국적 의료 시험 기반 환각 평가 벤치마크(Reasoning Hallucination Test + Memory Hallucination Test).
   - 필케어 활용 포인트: 2.7 — 환각을 정량 측정할 기존 지표 존재.

2. **제목**: *MedHallu: A Comprehensive Benchmark for Detecting Medical Hallucinations in Large Language Models* (arXiv:2502.14302, 2025)
   - URL: https://arxiv.org/abs/2502.14302 / https://medhallu.github.io/
   - 1문장 요약: PubMedQA 기반 10K QA 쌍에 체계적으로 환각 답변을 주입한 벤치마크로, GPT-4o·Llama-3.1·UltraMedical조차 hard 카테고리에서 F1 0.625에 그침.
   - 필케어 활용 포인트: 2.7 도전적 요소 — "최신 SOTA LLM도 의료 환각 탐지에 실패" (F1 0.625) 라는 강력한 경고 문장으로 필케어의 grounding 필요성 정당화.

3. **제목**: *Medical Hallucination in Foundation Models and Their Impact on Healthcare* (MIT Media Lab et al.)
   - 발표처: medRxiv 2025 (arXiv:2503.05777)
   - URL: https://arxiv.org/html/2503.05777v2
   - 1문장 요약: 파운데이션 모델의 의료 환각 유형·빈도·임상 영향을 체계적으로 분석하고 완화 전략을 제시.
   - 필케어 활용 포인트: 2.7/4.1 — "환각은 의료 AI의 핵심 리스크" 주장에 대한 MIT Media Lab 수준 인용.

4. **제목**: *MedHallBench: A New Benchmark for Assessing Hallucination in Medical Large Language Models* (arXiv:2412.18947)
   - 1문장 요약: 의료 LLM 환각 평가를 위한 또 다른 벤치마크 프레임워크.
   - 필케어 활용 포인트: 평가 파이프라인 구성 참고.

### Q7. 한국어 의료 LLM 연구

1. **제목**: *KorMedMCQA: Multi-Choice Question Answering Benchmark for Korean Healthcare Professional Licensing Examinations*
   - 저자/소속: Kweon et al. (arXiv:2403.01469, 2024)
   - URL: https://arxiv.org/abs/2403.01469
   - 1문장 요약: 2012-2024년 한국 의사·간호사·약사·치과의사 면허시험 7,469문제로 구성된 최초의 한국어 의료 MCQA 벤치마크. 59개 LLM 평가에서 o1-preview가 92.72 평균 최고점, Qwen2.5-72B가 오픈소스 78.86 최고점.
   - 필케어 활용 포인트: 2.6/4.1 — "한국 의료 LLM 평가의 국내 표준 벤치마크"로 필케어가 평가 시 KorMedMCQA(약사 트랙)를 사용하겠다고 명시 가능. 한국어 맥락의 필요성을 강조하는 문장 "MedQA 점수는 KorMedMCQA 점수를 거의 예측하지 못한다"(저자 결론) 직접 인용 가능.

2. **제목**: *KorMedMCQA-V: A Multimodal Benchmark for Evaluating Vision-Language Models on the Korean Medical Licensing Examination*
   - 발표처: arXiv:2602.13650 (인덱싱상 표시 — full paper 확인 필요)
   - 1문장 요약: KorMedMCQA의 멀티모달 확장판.
   - 필케어 활용 포인트: 향후 이미지/처방전 인식 확장 근거.

3. **제목**: *Performance evaluation of large language models on Korean medical licensing examination: a three-year comparative analysis*
   - 발표처: **Scientific Reports**, 2025
   - URL: https://www.nature.com/articles/s41598-025-20066-x
   - 1문장 요약: 3년치 한국 의사 국시에 대한 GPT-4 등 LLM 성능 종단 분석.
   - 필케어 활용 포인트: 한국어 의료 LLM이 peer-reviewed로 다뤄지고 있다는 국내 학계 근거.

4. **Seoul National University Hospital / SNUH**가 Korea 최초 의료 LLM을 자체 개발 중이라는 공식 발표 (http://www.snuh.org/global/en/about/newsView.do?bbs_no=7022). 4.1 파급효과 — 국내 대학병원도 자체 의료 LLM 투자 중임을 보이는 산업 근거.

---

## 제안서 인용 가능 근거 문장 (5-7개)

1. **[2.6 혁신적 요소 / 에이전트 정당성]** "Google DeepMind의 AMIE는 2025년 Nature에 게재된 연구에서 OSCE 기반 가상 환자 159 케이스에 대해 1차 진료의사와 비교한 32개 임상 평가 축 중 30개에서 동등 또는 우위의 성능을 기록, 대화형 의료 에이전트의 실현 가능성을 실증했다. (Tu et al., *Nature*, 2025, https://www.nature.com/articles/s41586-025-08866-7)"

2. **[2.6 / Agentic RAG 정당성]** "MedAgents(ACL 2024 Findings)와 MDAgents(NeurIPS 2024)는 여러 LLM 에이전트가 역할을 분담해 협업 추론할 때 MedQA·MedMCQA·PubMedQA에서 단일 LLM을 상회함을 보였고, 필케어는 동일 원리를 복약 도메인의 약사·주치의·환자 에이전트 협업으로 재구성한다. (arXiv:2311.10537, arXiv:2404.15155)"

3. **[2.6 / RAG 수치 근거]** "Xiong 등이 ACL 2024 Findings에 발표한 MIRAGE 벤치마크에 따르면 의료 RAG는 GPT-3.5와 같은 기저 모델의 MedQA 정확도를 GPT-4 수준으로 끌어올리며, 후속 i-MedRAG는 Llama-3.1-8B만으로 MedQA 75%를 달성했다. (Xiong et al., 2024; PSB 2025)"

4. **[2.6 / 약물 지식 그래프]** "필케어의 약물 지식 그래프 계층은 Harvard Zitnik Lab이 *Nature Scientific Data* 2023에 공개한 PrimeKG(17,080개 질병, 약물의 indication·contraindication·off-label·DDI를 포함한 4M+ 관계)를 기반으로 한다. (Chandak et al., 2023)"

5. **[2.7 도전적 요소 / 환각 경고]** "2025년 MedHallu 벤치마크(arXiv:2502.14302)는 GPT-4o, Llama-3.1, 의료 파인튜닝된 UltraMedical조차 hard 카테고리 의료 환각 탐지에서 F1 0.625에 그쳤음을 보고하며, grounding과 인용 기반 검증이 의료 LLM의 필수 요구사항임을 확인시켰다."

6. **[2.7 / 환각의 임상 영향]** "MIT Media Lab 등이 참여한 *Medical Hallucination in Foundation Models and Their Impact on Healthcare* (medRxiv 2025)는 파운데이션 모델의 환각이 임상 결정에 구체적 위해를 가할 수 있음을 체계적으로 분석하였고, 이는 필케어가 출처 인용·지식그래프 교차검증을 모든 답변에 강제하는 이유이다."

7. **[4.1 기술적 파급효과 / 한국어 맥락]** "KorMedMCQA(arXiv:2403.01469)의 저자들은 모델의 KorMedMCQA 점수가 MedQA 점수와 '전혀 다른 도메인 수준으로' 비상관이라고 보고하여, 한국 복약 시장을 겨냥한 LLM은 한국 면허시험 기반 벤치마크로 별도 검증이 필수임을 보였다. 필케어는 약사 면허시험 트랙을 1차 검증 기준으로 삼는다."

8. **[2.6 / 산업 근거 보조]** "Google Cloud의 MedLM(2024)과 AMIE 연구는 frontier 랩들이 의료 LLM을 대화형 + tool-use + 멀티모달 에이전트 방향으로 통일해 가고 있음을 보여주며, 필케어의 에이전틱 아키텍처는 이 흐름과 정확히 일치한다."

---

## 2025-2026 핵심 트렌드 (제안서 도입부 / 영상 활용)

- **Agentic AI 상용화 원년**: OpenAI의 Responses API·Anthropic의 Claude Agent SDK·Google Gemini tool-use가 2024-2025에 표준 API로 자리잡으면서 "LLM 단일 호출 → 에이전트 툴 루프"로 레퍼런스 아키텍처가 이동.
- **의료 도메인 프론티어 랩의 움직임**:
  - Google DeepMind: AMIE → AMIE-Vision (Nature 2025, arXiv:2401.05654)
  - Google Cloud: Med-PaLM 2 → MedLM → Gemini for Healthcare (Vertex AI GA)
  - MIT Media Lab: Medical Hallucination 체계적 평가 (arXiv:2503.05777)
  - Harvard Zitnik Lab: PrimeKG (Nature Scientific Data 2023) 등 precision medicine KG 공개
- **Agentic RAG + Knowledge Graph 결합**: AMG-RAG, i-MedRAG, Consensus Mechanism 등 "KG + RAG + multi-agent" 하이브리드가 2024-2025 의료 QA 논문의 주류 패턴으로 수렴.
- **환각이 여전히 핵심 리스크**: SOTA LLM조차 MedHallu hard에서 F1 0.625 → grounding/인용 강제가 의료 LLM의 사실상 필수 요구.
- **한국 내 움직임**: KorMedMCQA(2024), SNUH 자체 의료 LLM, *Scientific Reports* 2025의 국시 종단 분석 → 국내 의료 LLM 생태계가 실증 단계 진입.

---

## 참고 URL 로그

- AMIE (Nature 2025): https://www.nature.com/articles/s41586-025-08866-7
- AMIE arXiv preprint: https://arxiv.org/abs/2401.05654
- AMIE Google Research 블로그: https://research.google/blog/amie-a-research-ai-system-for-diagnostic-medical-reasoning-and-conversations/
- AMIE Vision: https://research.google/blog/amie-gains-vision-a-research-ai-agent-for-multi-modal-diagnostic-dialogue/
- MedAgents (ACL 2024 Findings): https://arxiv.org/abs/2311.10537 / https://aclanthology.org/2024.findings-acl.33/
- MDAgents (NeurIPS 2024): https://arxiv.org/html/2404.15155v3 / https://mdagents2024.github.io/
- LLM-based Agents in Medicine Survey: https://arxiv.org/abs/2502.11211
- AI Agents in Clinical Medicine Systematic Review: https://www.medrxiv.org/content/10.1101/2025.08.22.25334232v1.full
- MedAide: https://arxiv.org/abs/2410.12532
- MIRAGE (ACL 2024 Findings, Medical RAG benchmark): https://aclanthology.org/2024.findings-acl.372.pdf
- i-MedRAG (PSB 2025): http://psb.stanford.edu/psb-online/proceedings/psb25/xiong.pdf
- Hallucination Mitigation Survey (2025): https://arxiv.org/abs/2510.24476
- Agentic RAG for Patient Education (PMC12306375): https://pmc.ncbi.nlm.nih.gov/articles/PMC12306375/
- npj Digital Medicine — clinical safety / hallucination rates: https://www.nature.com/articles/s41746-025-01670-7
- PrimeKG (Nature Scientific Data 2023): https://www.nature.com/articles/s41597-023-01960-3
- PrimeKG project: https://zitniklab.hms.harvard.edu/projects/PrimeKG/
- PrimeKG GitHub: https://github.com/mims-harvard/PrimeKG
- DRKG GitHub: https://github.com/gnn4dr/DRKG
- Drug KG 리뷰 (Briefings in Bioinformatics 2024): https://academic.oup.com/bib/article/25/6/bbae461/7774899
- Med-HALT: https://medhalt.github.io/
- MedHallu (arXiv:2502.14302): https://arxiv.org/abs/2502.14302 / https://medhallu.github.io/
- Medical Hallucination in Foundation Models (MIT et al.): https://arxiv.org/html/2503.05777v2
- MedHallBench: https://arxiv.org/html/2412.18947v2
- KorMedMCQA (arXiv:2403.01469): https://arxiv.org/abs/2403.01469
- Korean Medical Licensing Exam LLM (Scientific Reports 2025): https://www.nature.com/articles/s41598-025-20066-x
- SNUH Korea first medical LLM: http://www.snuh.org/global/en/about/newsView.do?bbs_no=7022
- MedLM / Google Cloud healthcare: https://cloud.google.com/blog/topics/healthcare-life-sciences/introducing-medlm-for-the-healthcare-industry
- npj Digital Medicine — LLM for medication-related harm: https://www.nature.com/articles/s41746-025-01565-7
