# LangGraph Agent 아키텍처 상세 설계

> PillCare POC — LangGraph StateGraph 기반 복약 정보 안내 파이프라인
> 작성일: 2026-04-16
> 근거: 딥리서치 피드백 (2026-04-16) + v2 Plan

---

## 1. 아키텍처 개요

### 1-1. 설계 원칙

1. **Deterministic First**: 안전 관련 판단(DUR 병용금기)은 반드시 결정적 코드로 처리. LLM은 텍스트 생성만 담당.
2. **Single Agent + Tools**: MedAgentBoard (NeurIPS 2025) 연구에 따르면, 구조화된 약물 정보 태스크에서 multi-agent는 single agent + tool-use 대비 일관된 이점 없음. PillCare는 single LLM 노드 + 결정적 tool 노드 조합.
3. **LangGraph for Orchestration**: 모델 교체 유연성(Claude ↔ GPT-4o ↔ Gemini), checkpointing, conditional retry, 시각적 DAG 디버깅.
4. **Source Grounding**: 모든 생성 문장에 출처 티어 태그 강제. POC에서는 프롬프트 기반 태그, 프로덕션에서는 Anthropic Citations API.

### 1-2. 파이프라인 DAG

```
                    ┌─────────────┐
                    │  Entry      │
                    │  (initial   │
                    │   state)    │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ match_drugs │  ← Deterministic: EDI → Exact → FTS5 → Fuzzy
                    │  (Phase 1)  │     Input: raw_records, db_path
                    └──────┬──────┘     Output: matched_drugs, errors
                           │
                    ┌──────▼──────┐
                    │  check_dur  │  ← Deterministic: Multi-ingredient N×N
                    │  (Phase 1)  │     Input: matched_drugs, db_path
                    └──────┬──────┘     Output: dur_alerts
                           │
                    ┌──────▼──────┐
                    │collect_info │  ← Deterministic: DB lookup per drug
                    │  (Phase 1)  │     Input: matched_drugs, db_path
                    └──────┬──────┘     Output: drug_infos
                           │
                    ┌──────▼──────┐
                    │  generate   │  ← LLM: Claude Sonnet 4.6 via langchain-anthropic
                    │  (Phase 2)  │     Input: drug_infos, dur_alerts, _llm
                    └──────┬──────┘     Output: guidance_result
                           │
                    ┌──────▼──────┐
                    │   verify    │  ← Deterministic: 5-check guardrails
                    │  (Phase 3)  │     Input: guidance_result, dur_alerts
                    └──────┬──────┘     Output: errors, _retry_count
                           │
                    ┌──────▼──────┐
                    │ should_     │  ← Conditional: CRITICAL errors + retry < 2?
                    │   retry?    │
                    └──┬───────┬──┘
                 retry │       │ done
                    ┌──▼──┐  ┌─▼──┐
                    │ gen │  │END │
                    └─────┘  └────┘
```

---

## 2. GraphState 정의

```python
import operator
from typing import Annotated, TypedDict

# Public State: graph.invoke()의 입출력에 노출
class PublicState(TypedDict, total=False):
    profile_id: str               # 사용자 프로필 ID
    raw_records: list[dict]       # 파싱된 투약이력 레코드
    matched_drugs: list[dict]     # MatchedDrug.model_dump() 리스트
    dur_alerts: list[dict]        # DurAlertModel.model_dump() 리스트
    drug_infos: list[dict]        # DrugInfo asdict() 리스트
    guidance_result: dict | None  # GuidanceResult.model_dump()
    errors: Annotated[list[str], operator.add]  # reducer: 자동 누적

# Internal State: _retry_count는 callers에게 비공개
class GraphState(PublicState, total=False):
    _retry_count: int             # 재시도 횟수 (max 1)

# 클로저로 주입 (State에 포함하지 않음):
# - llm → _make_generate_node(llm) 
# - db_path → make_match_node(db_path), make_dur_node(db_path), make_collect_node(db_path)
#
# builder = StateGraph(GraphState, input_schema=PublicState, output_schema=PublicState)
```

### 2-1. State 전파 규칙

- LangGraph `StateGraph(TypedDict)`에서 각 노드는 **업데이트할 키만 반환**합니다.
- 반환하지 않은 키는 이전 값이 유지됩니다.
- `errors` 키는 `operator.add` reducer를 사용: 노드는 새 에러만 반환하면 자동 누적됩니다.
- `llm`과 `db_path`는 **클로저로 주입** — State에 넣으면 checkpointer 직렬화가 깨짐.
- `_llm`은 초기 state에서 설정되고, 어떤 노드도 반환하지 않으므로 전체 파이프라인에서 동일 인스턴스가 유지됩니다.
- `_retry_count`는 `verify` 노드에서만 증가시킵니다.

---

## 3. 노드 상세 설계

### 3-1. match_drugs (Deterministic)

**책임**: 투약이력의 약물명을 DB의 item_seq에 매핑.

**4-Phase 전략**:

| Phase | 방법 | 조건 | 복잡도 |
|-------|------|------|--------|
| 1 | EDI 코드 정확 매칭 | `drug_code` 존재 + `edi_code` 인덱스 히트 | O(1) |
| 2 | `item_name` 정확 매칭 | 인덱스 히트 | O(1) |
| 3 | FTS5 trigram 검색 | `drugs_fts MATCH query` → top-5 → rapidfuzz 재순위 | O(log n) |
| 4 | rapidfuzz 전수 스캔 | `token_set_ratio ≥ 70` | O(n) |

**성분 코드 추출**: `MAIN_ITEM_INGR` 필드에서 정규식 `\[([A-Z]\d+)\]`로 추출.
- 단일 성분: `"[M040702]이부프로펜"` → `["M040702"]`
- 복합제: `"[M175201]클로르페니라민|[M146801]디히드로코데인"` → `["M175201", "M146801"]`

**반환**: `{"matched_drugs": [...], "errors": [...]}`

### 3-2. check_dur (Deterministic)

**책임**: 모든 약물 쌍의 모든 성분 조합에 대해 DUR 병용금기 확인.

**알고리즘**:
```
for (drug_A, drug_B) in combinations(matched_drugs, 2):
    for ingr_a in drug_A.ingr_codes:
        for ingr_b in drug_B.ingr_codes:
            if (ingr_a, ingr_b) in dur_lookup OR (ingr_b, ingr_a) in dur_lookup:
                emit DurAlert(
                    cross_clinic = (drug_A.department != drug_B.department)
                )
```

**복잡도**: 11약물 × 평균 1.5 성분 = ~16.5 성분 → C(16.5, 2) ≈ 136 쌍 × O(1) lookup = 즉시.

**핵심 기능**: `cross_clinic` 플래그 — 서로 다른 의료기관에서 처방된 약물 간 금기를 강조.

**반환**: `{"dur_alerts": [...]}`

### 3-3. collect_info (Deterministic)

**책임**: 매칭된 약물별로 drugs + drug_sections + drugs_easy 테이블을 조인하여 구조화된 정보 수집.

**반환 구조** (per drug):
```python
{
    "item_seq": "199701416",
    "item_name": "리도펜연질캡슐(이부프로펜)",
    "main_item_ingr": "[M040702]이부프로펜",
    "main_ingr_eng": "Ibuprofen",
    "entp_name": "(주)메디카코리아",
    "atc_code": "M01AE01",
    "chart": "주황색의 장방형 연질캡슐제",
    "storage_method": "실온보관(1-30℃)",
    "valid_term": "제조일로부터 24 개월",
    "sections": {
        "금기": "이 약에 과민증 환자",
        "상호작용": "다른 비스테로이드성 소염진통제와...",
        "이상반응": "쇽 증상, 소화성궤양..."
    },
    "easy": {
        "efcy_qesitm": "이 약은 감기로 인한 발열...",
        "use_method_qesitm": "성인은 1회 1-2캡슐...",
        "se_qesitm": "쇽 증상, 소화성궤양...",
        ...
    }
}
```

**반환**: `{"drug_infos": [...]}`

### 3-4. generate (LLM)

**책임**: 약물별로 복약 정보 안내문 10개 항목 생성.

**핵심 설계 결정**:

1. **Per-drug sequential generation**: 11약물을 한 번에 생성하지 않고, 약물별로 순차 호출. 이유:
   - 단일 호출로 110 섹션 생성 시 품질 저하 (lost-in-the-middle 효과)
   - 약물별 context를 깔끔하게 제공 가능
   - 실패 시 해당 약물만 재시도 가능

2. **System prompt**: `prompts.py`의 `SYSTEM_PROMPT` — 역할 경계, 출력 규칙, 10개 항목 체크리스트, 금칙 어휘 포함.

3. **User prompt**: `DRUG_GUIDANCE_TEMPLATE` — 약물 기본정보 + EE/UD XML 텍스트 + NB 섹션별 텍스트 + e약은요 텍스트 + DUR 경고를 구조화하여 전달.

4. **출력 파싱**: LLM 응답에서 `### N. 섹션명` 헤더를 정규식으로 추출, 각 섹션의 `[T1:...]` / `[T4:AI]` 태그로 source tier 판별.

5. **별첨3 경고라벨**: NB_DOC_DATA "경고" 섹션 + atpnWarnQesitm + DUR 경고에서 추출 (LLM 호출 전 deterministic).

**LLM 호출 패턴** (langchain-anthropic):

```python
from langchain_anthropic import ChatAnthropic

llm = ChatAnthropic(
    model="claude-sonnet-4-6",
    max_tokens=4096,
    # Prompt caching: langchain-anthropic 자동 지원
    # (system prompt + tool defs가 반복 호출 시 캐시됨)
)

messages = [
    SystemMessage(content=SYSTEM_PROMPT),
    HumanMessage(content=formatted_drug_prompt),
]

response = llm.invoke(messages)
```

**반환**: `{"guidance_result": GuidanceResult.model_dump()}`

### 3-5. verify (Deterministic)

**책임**: 생성 결과에 대한 5가지 사후 검증.

| # | 검증 | 실패 시 | 심각도 |
|---|------|---------|--------|
| 1 | DUR 커버리지 | GuidanceResult.dur_warnings에 DUR 경고 약물쌍 누락 (구조화된 필드 매칭, 자유 텍스트 매칭 아님) | **CRITICAL** (재시도) |
| 2 | 출처 태그 존재 | 섹션에 `[T1:...]` 또는 `[T4:AI]` 태그 없음 | WARNING |
| 3 | T4 비율 | T4 섹션이 전체의 30% 초과 | **CRITICAL** (재시도) |
| 4 | 필수 종결 문구 | 주의사항/상호작용/투여종료후 섹션에 "의사 또는 약사와 상담하십시오" 누락 | WARNING |
| 5 | 금칙어 | "진단합니다", "처방합니다" 등 포함 | WARNING (자동 제거) |

**재시도 조건**: CRITICAL 에러 + `_retry_count < 2` → generate 노드로 루프백. (verify는 항상 _retry_count를 증가시키므로, 첫 verify 후 count=1에서 재시도 가능, 두 번째 verify 후 count=2에서 종료.)

**반환**: `{"errors": [...], "_retry_count": N+1}`

---

## 4. 데이터 흐름 상세

### 4-1. 초기 State 생성 (app.py → run_pipeline)

```python
initial_state = {
    "profile_id": "user-001",
    "raw_records": [
        {"drug_name": "알게텍정", "drug_code": "057600010", "department": "가정의학과"},
        {"drug_name": "펠루비정", "drug_code": "671803380", "department": "가정의학과"},
        {"drug_name": "코대원정", "drug_code": None, "department": "가정의학과"},
        {"drug_name": "록스펜정", "drug_code": "648500640", "department": "안과"},
        # ... 11 drugs total
    ],
    "matched_drugs": [],
    "dur_alerts": [],
    "drug_infos": [],
    "guidance_result": None,
    "errors": [],
    "db_path": "data/pillcare.db",
    "_llm": ChatAnthropic(model="claude-sonnet-4-6", max_tokens=4096),
    "_retry_count": 0,
}
```

### 4-2. 각 노드 후 State 변화

```
[Entry] → raw_records: 11 records
    ↓
[match_drugs] → matched_drugs: 11 MatchedDrug (ingr_codes 포함)
    ↓
[check_dur] → dur_alerts: N개 DurAlert (cross_clinic 플래그 포함)
    ↓
[collect_info] → drug_infos: 11 DrugInfo (sections + easy 포함)
    ↓
[generate] → guidance_result: GuidanceResult (11 DrugGuidance + warnings + summary + labels)
    ↓
[verify] → errors: [검증 결과], _retry_count: 1
    ↓
[should_retry?] → "done" (또는 CRITICAL이면 "retry" → generate)
    ↓
[END] → 최종 state 반환
```

---

## 5. 프로덕션 확장 경로

### 5-1. Anthropic Citations API (POC → Production)

POC에서는 프롬프트 기반 `[T1:허가정보]` 태그를 사용합니다. 프로덕션에서는:

```python
# Production: Citations API 활용
response = anthropic_client.messages.create(
    model="claude-sonnet-4-6",
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "document",
                "source": {"type": "text", "media_type": "text/plain", "data": drug_label_text},
                "title": f"{item_name} 허가정보",
                "citations": {"enabled": True},
            },
            {"type": "text", "text": guidance_prompt},
        ],
    }],
)
# 응답에 char-level citation 위치 자동 포함 → post-rationalization 문제 해결
```

### 5-2. Prompt Caching

```python
llm = ChatAnthropic(
    model="claude-sonnet-4-6",
    max_tokens=4096,
    model_kwargs={
        "extra_headers": {"anthropic-beta": "token-efficient-tools-2025-02-19"},
    },
)
# langchain-anthropic은 system prompt를 자동으로 cache_control: ephemeral로 처리
```

### 5-3. Extended Thinking (선택적)

복잡한 다약물 상호작용 분석 시:

```python
llm = ChatAnthropic(
    model="claude-sonnet-4-6",
    max_tokens=16000,
    thinking={"type": "adaptive"},  # Claude가 복잡도에 따라 자동 판단
)
```

### 5-4. MDAgents-Lite 복잡도 게이트 (향후)

```
[Query Router] → 복잡도 분류
    │
    ├── Low: "이 약 뭐예요?" → 단일 drug_info lookup (LLM 불필요)
    ├── Medium: "이 약 2개 같이 먹어도 돼요?" → check_dur + generate
    └── High: "어머니가 당뇨+고혈압+혈압약 중단 원해요" → clinician brief escalation
```

LangGraph의 conditional edge로 자연스럽게 구현 가능:

```python
graph.add_conditional_edges("classify_query", route_by_complexity, {
    "low": "simple_lookup",
    "medium": "match_drugs",  # 현재 파이프라인
    "high": "escalate_to_clinician",
})
```

### 5-5. SapBERT-KO-EN 임베딩 매칭 (향후)

drug_matcher Phase 5로 추가:

```python
# Phase 5: Semantic embedding fallback
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("snumin44/sap-bert-ko-en")
query_emb = model.encode(query)
# → Qdrant/FAISS에서 nearest neighbor 검색
```

---

## 6. 테스트 전략

### 6-1. 테스트 피라미드

| 레벨 | 범위 | 테스트 수 | LLM 필요 |
|------|------|----------|----------|
| Unit | 개별 함수 (extract_ingr_codes, _classify_title 등) | ~20 | No |
| Integration | 노드 단위 (match_drugs_node, check_dur_node 등) | ~15 | No |
| Pipeline | 전체 DAG (deterministic 노드 체인) | ~5 | Mocked |
| E2E | Streamlit + 실제 DB + 실제 LLM | 1 (수동) | Yes |

### 6-2. LLM 노드 테스트 전략

```python
# Mock LLM으로 generate 노드 테스트
mock_llm = MagicMock()
mock_response = MagicMock()
mock_response.content = (
    "### 1. 명칭\n[T1:허가정보] 리도펜연질캡슐\n\n"
    "### 3. 효능효과\n[T1:e약은요] 감기 발열 통증\n"
)
mock_llm.invoke.return_value = mock_response

# _generate_node 직접 호출
state["_llm"] = mock_llm
result = _generate_node(state)
assert result["guidance_result"] is not None
```

### 6-3. Guardrails 테스트 전략

각 guardrail 함수를 독립적으로 테스트:
- `verify_dur_coverage`: 약물명 포함/미포함 텍스트
- `verify_source_tags`: 태그 있음/없음 섹션
- `verify_t4_ratio`: 30% 이하/초과 케이스
- `verify_closing_phrase`: 종결 문구 있음/없음
- `filter_banned_words`: 금칙어 포함/미포함 텍스트

---

## 7. 의존성 & 호환성

| 패키지 | 역할 | 최소 버전 | 비고 |
|--------|------|----------|------|
| langgraph | 파이프라인 오케스트레이션 | 0.2.x | StateGraph, conditional_edges |
| langchain-anthropic | Claude LLM 래퍼 | 0.3.x | ChatAnthropic, prompt caching |
| langchain-core | 메시지 타입, 기반 클래스 | 0.3.x | SystemMessage, HumanMessage |
| anthropic | (langchain-anthropic 내부 의존) | 0.40.x | Citations API (향후) |
| pydantic | 스키마, 구조화 출력 | 2.x | BaseModel, Field |
| rapidfuzz | 문자열 퍼지 매칭 | 3.x | token_set_ratio |
| sqlite3 | 약물 DB (stdlib) | - | FTS5 trigram (3.34+) |

### 7-1. 버전 확인 명령

```bash
npx ctx7@latest library langgraph "LangGraph state graph"
npx ctx7@latest library langchain-anthropic "LangChain Anthropic"
```

context7에서 확인한 안정 버전을 `pyproject.toml`에 핀합니다.
