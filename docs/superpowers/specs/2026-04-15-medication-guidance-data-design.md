# 복약 정보 안내 데이터 매핑 & 생성 파이프라인 설계

> PillCare POC — 개인 투약이력 기반 grounded 복약 정보 안내 생성
> 작성일: 2026-04-15
> 아키텍처: DUR deterministic 체크 + RAG enrichment (Option C)
> 확장 목표: POC(국내 T1 데이터) → Production(+ DailyMed/OpenFDA T2 보충)

---

## 1. 목적

복약지도 가이드(약사법 시행규칙 별표 5)의 10개 항목에 맞는 복약 정보 안내 텍스트를
공식 API/DB 데이터에 grounded하여 생성한다.

**핵심 차별점**: 단일 약물 조회가 아닌, 개인 투약이력(다기관 처방 포함) 전체를
컨텍스트로 하여 병용금기 교차 체크 + 개인화된 주의사항을 도출한다.

**규제 경계**: "복약지도"는 약사 독점 업무(약사법 §24)이므로, 시스템 출력물은
"복약 정보 안내"로 명명하며, 진단/처방/용량변경 판단을 절대 포함하지 않는다.

---

## 2. 데이터 소스 현황

### 2-1. 크롤링 완료 (2026-04-15)

| 데이터셋 | 건수 | 출처 | 라이선스 | 설명 |
|---|---|---|---|---|
| 허가정보 (drug_permit_detail) | 43,250 | 식약처 DrugPrdtPrmsnInfoService07 | 제한 없음 | 성분, 성상, ATC, 효능/용법/주의 XML 전문 |
| e약은요 (easy_drug_info) | 4,711 | 식약처 DrbEasyDrugInfoService | 제한 없음 | 환자용 plain text (효능/용법/주의/부작용/상호작용/보관) |
| 묶음의약품 (bundle_drug_info) | 16,322 | 식약처 DrbBundleInfoService02 | 제한 없음 | ATC 코드, 심평원 코드 브릿지 |
| 낱알식별 (medicines.csv) | 25,685 | 식약처 nedrug | 제한 없음 | 외형(모양/색/각인), 이미지 URL |
| DUR 병용금기 (CSV) | 542,996 | KIDS/심평원 | KOGL Type 1 | 1,638 성분 쌍, 금기사유 |
| ATC 사용통계 | 28 | HIRA/KOSIS | KOGL Type 1 | ATC 2단계별 연도 사용량 |

### 2-2. 필드 커버리지 (허가정보 API 기준, 43,250건)

| 필드 | 커버리지 | 용도 |
|---|---|---|
| ITEM_NAME / ITEM_ENG_NAME | 100% / 94.5% | 명칭 |
| MATERIAL_NAME | 99.8% | 주성분 + 함량 상세 |
| MAIN_ITEM_INGR / MAIN_INGR_ENG | 99.8% | 주성분명 (한/영) |
| CHART | 100% | 성상 |
| ATC_CODE | 95.2% | 국제 분류 브릿지 |
| STORAGE_METHOD / VALID_TERM | 100% / 100% | 보관법 / 유효기간 |
| EE_DOC_DATA | 100% | 효능효과 XML 원문 |
| UD_DOC_DATA | 100% | 용법용량 XML 원문 |
| NB_DOC_DATA | 100% | 사용상주의사항 XML 원문 |
| EDI_CODE | 48.0% | 보험코드 (처방 연계) |
| ETC_OTC_CODE | 100% | 전문/일반 구분 |

### 2-3. NB_DOC_DATA XML 섹션 구조

사용상주의사항 XML은 ARTICLE 단위로 구조화되어 있으며, 주요 섹션:

| 섹션 | 출현 빈도 (샘플 27건) | 복약지도 항목 매핑 |
|---|---|---|
| 다음 환자에는 투여하지 말 것 | 67% | 7) 주의사항 - 금기 |
| 다음 환자에는 신중히 투여할 것 | 59% | 7) 주의사항 - 신중투여 |
| 이상반응 | 56% | 7) 주의사항 - 부작용 |
| 상호작용 | 59% | 8) 상호작용 |
| 임부 및 수유부에 대한 투여 | 56% | 7) 특수집단 |
| 소아에 대한 투여 | 56% | 7) 특수집단 |
| 고령자에 대한 투여 | 56% | 7) 특수집단 |
| 과량투여시의 처치 | 37% | 10) 기타 |
| 경고 | 33% | 별첨3 경고라벨 |
| 일반적 주의 | 67% | 10) 기타 |
| 보관/취급상의 주의 | 26% | 6) 저장방법 보충 |

---

## 3. 복약지도 10개 항목 → 데이터 소스 매핑

### Tier 정의

- **T1**: 식약처/심평원 공식 데이터 (허가정보, e약은요, DUR)
- **T2**: 미국 공공 데이터 (DailyMed, OpenFDA) — POC에서는 미사용, 프로덕션 확장
- **T3**: 공개 지식 그래프 (PrimeKG, Hetionet) — POC에서는 미사용
- **T4**: LLM 자체 지식 — 최소한으로 사용, 반드시 태그 표시

### 매핑 테이블

| # | 복약지도 항목 | T1 소스 | 커버리지 | T4 필요 여부 |
|---|---|---|---|---|
| 1 | 명칭 (제품명, 성분명, 제조사, 제형, 함량) | 허가정보: ITEM_NAME, MATERIAL_NAME, MAIN_ITEM_INGR, ENTP_NAME, TOTAL_CONTENT | 99.8% | 불필요 |
| 2 | 성상 | 허가정보: CHART + medicines.csv: DRUG_SHAPE, COLOR_CLASS | 100% | 불필요 |
| 3 | 효능효과 | 허가정보: EE_DOC_DATA (XML) / e약은요: efcyQesitm (plain) | 100% | 불필요 |
| 4 | 투여의의 | ❌ 없음 | 0% | **T4 필수** — 효능효과 + ATC 분류로 맥락 보충 |
| 5 | 용법용량 | 허가정보: UD_DOC_DATA (XML) / e약은요: useMethodQesitm (plain) | 100% | 불필요 |
| 6 | 저장방법 + 유효기간 | 허가정보: STORAGE_METHOD, VALID_TERM + NB_DOC_DATA "보관주의" 섹션 | 100% | 불필요 |
| 7 | 사용상 주의사항 (이상반응, 경고, 금기) | 허가정보: NB_DOC_DATA (금기/신중/이상반응/임부수유/소아/고령자 섹션) + e약은요: seQesitm, atpnWarnQesitm, atpnQesitm | 100% | 불필요 |
| 8 | 상호작용 | DUR CSV: 1,638 성분 쌍 (deterministic) + NB_DOC_DATA "상호작용" 섹션 + e약은요: intrcQesitm | 복합 | 불필요 |
| 9 | 투여종료후 주의 | NB_DOC_DATA 내 일부 포함 가능 | 낮음 | **T4 보충** |
| 10 | 기타 (복용 누락 대처 등) | e약은요: atpnQesitm 일부 + NB_DOC_DATA "일반적 주의"/"과량투여" | 부분 | **T4 보충** |

**결론**: 10개 항목 중 7개는 T1 100% 커버, 1개(상호작용)는 T1 복합, 2개(투여의의, 투여종료후)는 T4 보충 필요, 1개(기타)는 부분 T1 + T4.

---

## 4. 데이터 레이어 설계

### 4-1. SQLite 스키마 (POC)

```sql
-- 허가정보 기반 약물 마스터
CREATE TABLE drugs (
    item_seq        TEXT PRIMARY KEY,
    item_name       TEXT NOT NULL,
    item_eng_name   TEXT,
    entp_name       TEXT NOT NULL,
    etc_otc_code    TEXT,           -- 전문/일반
    material_name   TEXT,           -- "총량:...|성분명:...|분량:...|단위:..."
    main_item_ingr  TEXT,           -- "[M코드]성분명"
    main_ingr_eng   TEXT,
    chart           TEXT,           -- 성상
    atc_code        TEXT,
    storage_method  TEXT,
    valid_term      TEXT,
    edi_code        TEXT,
    ee_doc_data     TEXT,           -- 효능효과 XML
    ud_doc_data     TEXT,           -- 용법용량 XML
    nb_doc_data     TEXT,           -- 사용상주의사항 XML
    updated_at      TEXT
);

-- e약은요 환자용 텍스트 (4,711건)
CREATE TABLE drugs_easy (
    item_seq                TEXT PRIMARY KEY REFERENCES drugs(item_seq),
    efcy_qesitm             TEXT,  -- 효능효과
    use_method_qesitm       TEXT,  -- 용법용량
    atpn_warn_qesitm        TEXT,  -- 경고
    atpn_qesitm             TEXT,  -- 주의사항
    intrc_qesitm            TEXT,  -- 상호작용
    se_qesitm               TEXT,  -- 부작용
    deposit_method_qesitm   TEXT   -- 보관법
);

-- NB_DOC_DATA 파싱 결과 (의미 단위 섹션)
CREATE TABLE drug_sections (
    item_seq      TEXT REFERENCES drugs(item_seq),
    section_type  TEXT NOT NULL,    -- 금기|신중투여|이상반응|상호작용|임부수유|소아|고령자|과량투여|일반주의|보관주의|경고
    section_title TEXT,             -- 원본 ARTICLE title
    section_text  TEXT NOT NULL,    -- XML → plain text
    section_order INTEGER,
    PRIMARY KEY (item_seq, section_type, section_order)
);

-- DUR 병용금기 (성분 레벨, 정규화)
CREATE TABLE dur_pairs (
    ingr_code_1   TEXT NOT NULL,
    ingr_name_1   TEXT NOT NULL,
    ingr_code_2   TEXT NOT NULL,
    ingr_name_2   TEXT NOT NULL,
    reason        TEXT NOT NULL,    -- 정규화된 금기사유
    notice_date   TEXT,
    PRIMARY KEY (ingr_code_1, ingr_code_2)
);

-- 묶음의약품 ATC 브릿지
CREATE TABLE bundle_atc (
    trust_item_name          TEXT,
    trust_mainingr           TEXT,
    trust_atc_code           TEXT,
    trust_hira_mainingr_code TEXT,  -- 심평원 성분코드
    trust_hira_product_code  TEXT   -- 심평원 EDI
);

-- 개인 투약이력 (심평원 "내가 먹는 약" 다운로드 형식)
CREATE TABLE medication_history (
    profile_id      TEXT NOT NULL,
    seq             INTEGER,        -- 번호
    drug_name       TEXT NOT NULL,  -- 제품명 (예: 펠루비정, 록스펜정)
    drug_class      TEXT,           -- 약효분류 (예: 해열·진통·소염제)
    ingredient      TEXT,           -- 성분명 (예: pelubiprofen, loxoprofen sodium)
    drug_code       TEXT,           -- 약품코드 (EDI 코드)
    unit            TEXT,           -- 단위 (1정, 5mL/병 등)
    dose_per_time   REAL,           -- 1회 투약량
    times_per_day   INTEGER,        -- 1일 투여횟수
    duration_days   INTEGER,        -- 총 투약일수
    safety_letter   TEXT,           -- 안전성 서한 (Y/N)
    antithrombotic  TEXT,           -- 항혈전제 여부 (Y/N)
    department      TEXT,           -- 진료과 (가정의학과, 안과 등)
    item_seq        TEXT REFERENCES drugs(item_seq),  -- 매칭 후 채워짐
    ingr_codes      TEXT            -- 매칭된 성분코드 (쉼표 구분)
);

-- 샘플 데이터: 가정의학과 5약물 + 안과 6약물 = 11약물, 55 DUR 교차 쌍
```

### 4-2. DUR 정규화 규칙

원본 CSV의 금기사유 텍스트 변형을 통합:
- "기능적 신부전에 의해 유산 산성증 촉진" + "기능성 신부전에 의한 유산산성증 촉진" → 통합
- 제품 레벨(542,996건) → 성분 쌍 레벨(1,638건)으로 dedup
- 동일 성분 쌍에 여러 금기사유가 있으면 모두 보존

### 4-3. NB_DOC_DATA XML 파싱 규칙

```
<ARTICLE title="..."> → section_type 매핑:
  "투여하지 말 것"        → 금기
  "신중히 투여"           → 신중투여
  "이상반응" | "부작용"    → 이상반응
  "상호작용"              → 상호작용
  "임부" | "수유부"       → 임부수유
  "소아"                  → 소아
  "고령자"                → 고령자
  "과량투여"              → 과량투여
  "일반적 주의"           → 일반주의
  "보관" | "취급"         → 보관주의
  "경고"                  → 경고
  기타                    → 기타
```

XML → plain text 변환: `<PARAGRAPH>` 태그 내 텍스트 추출, `\n\n`으로 구분.

---

## 5. 처리 파이프라인

```
Stage 1. 입력 파싱 (Deterministic)
│ 개인투약이력 (xls/csv) → 약물명 추출 → drugs 테이블 fuzzy match
│ → item_seq 확보 → 성분코드(main_item_ingr) 추출
│ → 진료과/진료일자/투약일수 메타데이터 보존
▼
Stage 2. DUR 전수 체크 (Deterministic, T1)
│ N개 약물 → N×(N-1)/2 성분 쌍 → dur_pairs lookup
│ → 병용금기 쌍 + 금기사유 확정
│ → 다기관(가정의학과 × 안과) 교차 쌍 플래그
▼
Stage 3. 약물별 정보 수집 (DB Lookup, T1)
│ item_seq별: drug_sections, drugs_easy, drugs 테이블에서 fetch
│ → 복약지도 10개 항목에 필요한 데이터 구조화
▼
Stage 4. Claude Agent 생성 (LLM)
│ System prompt: 복약지도 체크리스트 + 출처 티어 규칙 + 가드레일
│ Tool results: DUR 금기(T1) + 약물별 섹션(T1) + 환자 메타
│ → 별첨1(상세) + 병용금기 경고 + 별첨2(요약) + 별첨3(경고라벨)
│ → 모든 문장에 출처 태깅
▼
Stage 5. 사후 검증 (Deterministic)
│ 생성 텍스트 내 약물 쌍 → DUR 금기 누락 체크
│ → T1 데이터와 모순 체크 → 누락/모순 시 재생성 또는 경고 삽입
```

### 5-1. Stage 1 상세: 약물명 매칭

투약이력의 약물명은 처방전 표기(브랜드명 + 함량 + 제형)로 되어 있음.
매칭 전략:
1. drugs.item_name 완전 일치
2. rapidfuzz token_set_ratio ≥ 70 (기존 POC plan의 drug_matcher 재사용)
3. 매칭 실패 시 → 성분명(main_item_ingr) 기반 재매칭
4. 최종 실패 → 사용자에게 확인 요청

### 5-2. Stage 2 상세: DUR 교차 체크

```python
# 의사 코드
drugs = [d1, d2, d3, ...]  # 전체 투약 약물
for i, j in combinations(drugs, 2):
    for ingr_a in i.ingr_codes:
        for ingr_b in j.ingr_codes:
            if (ingr_a, ingr_b) in dur_pairs or (ingr_b, ingr_a) in dur_pairs:
                alert = DurAlert(
                    drug_1=i, drug_2=j,
                    reason=dur_pairs[(ingr_a, ingr_b)].reason,
                    cross_clinic=(i.department != j.department)
                )
```

`cross_clinic=True`인 경우 "서로 다른 의료기관에서 처방된 약물 간 병용금기" 강조.

### 5-3. Stage 4 상세: 출력 포맷

**별첨1 — 상세 복약 정보 안내문 (약물별)**

```
## [제품명] (성분명)

### 1. 명칭
- 제품명: OOO정 [T1:허가정보]
- 성분: OOO OOmg [T1:허가정보]
- 제조사: OOO [T1:허가정보]

### 2. 성상
이 약은 ... [T1:허가정보]

### 3. 효능효과
이 약은 ...에 사용합니다. [T1:e약은요]

### 4. 투여의의
이 약은 ...를 위해 처방되었습니다. 복용하지 않으면 ... [T4:AI]
※ AI가 생성한 일반 정보입니다. 정확한 내용은 의사 또는 약사와 상담하십시오.

### 5. 용법용량
... [T1:e약은요]

### 6. 보관방법
... 유효기간: ... [T1:허가정보]

### 7. 주의사항 및 부작용
**흔한 이상반응**: ... [T1:허가정보]
**중대한 이상반응**: ... [T1:허가정보]
**다음의 경우 즉시 의사에게 알리십시오**: ... [T1:허가정보]

### 8. 상호작용
⚠️ **[병용금기]** OOO와 함께 복용 시 ... [T1:DUR]
(가정의학과 처방 × 안과 처방 — 서로 다른 의료기관 처방입니다)
... [T1:허가정보 상호작용 섹션]

### 9. 투여 종료 후
... [T4:AI]

### 10. 기타
**복용을 잊은 경우**: ... [T1:e약은요 또는 T4:AI]
```

**병용금기 경고 (전체 요약)**

```
⚠️ 병용금기 경고

귀하의 투약이력에서 다음 약물 조합이 병용금기에 해당합니다:

1. [금기] OOO (가정의학과) × OOO (안과) — 다기관 교차 처방
   사유: ... [T1:DUR]
   → 반드시 처방 의사 또는 약사와 상담하십시오.

2. [주의] OOO × OOO
   사유: ... [T1:DUR]
```

**별첨2 — 복약 정보 요약 (핵심 포인트)**

별첨1에서 추출한 5-8개 bullet point.

**별첨3 — 경고라벨 목록**

NB_DOC_DATA "경고" 섹션 + DUR 금기 + atpnWarnQesitm에서 추출.

---

## 6. Agent 도구 정의

| Tool | 입력 | 출력 | 단계 |
|---|---|---|---|
| `search_drug(query)` | 약물명 문자열 | DrugMatch[] (item_seq, name, score) | Stage 1 |
| `check_dur(ingr_codes[])` | 성분코드 배열 | DurAlert[] (쌍, 사유, cross_clinic) | Stage 2 |
| `get_drug_info(item_seq, sections[])` | 품목번호, 요청 섹션 | DrugInfo (섹션별 텍스트) | Stage 3 |
| `get_medication_history(profile_id)` | 프로필 ID | MedHistory[] (약물, 진료과, 기간) | Stage 1 |
| `cite_source(claim, source_type, source_id)` | 문장, 출처 타입, ID | Citation | Stage 4 |
| `generate_guidance(drugs, alerts, context, format)` | 수집 데이터 전체 | MedicationGuidance | Stage 4 |

### LangGraph DAG

```
parse_input
    → search_drugs (sequential per drug)
    → check_dur (all drugs at once)
    → get_drug_info (parallel per drug)
    → generate_guidance (detailed → summary → labels)
    → post_verify
```

---

## 7. 프로덕션 확장 경로

### 7-1. T2 소스 추가 (DailyMed/OpenFDA)

POC에서 T4로 처리하는 항목(투여의의, 투여종료후, 복용누락)을 국제 데이터로 보충:
- DailyMed SPL XML의 "PATIENT COUNSELING INFORMATION" 섹션
- OpenFDA Drug Labels의 "information_for_patients" 필드
- ATC 코드로 한국 약물 → 미국 동일 성분 약물 매칭

### 7-2. T3 소스 추가 (PrimeKG)

투여의의 항목을 작용 메커니즘으로 보충:
- PrimeKG: drug → target → pathway → disease 경로 추출
- "이 약은 [target]에 작용하여 [pathway]를 조절함으로써 [disease]를 치료합니다" 템플릿

### 7-3. DUR 확장

현재 병용금기만 → 연령금기, 임부금기, 노인주의 추가 (동일 KIDS 제공):
- 환자 프로필(나이, 성별, 임신 여부) 입력 시 개인화 금기 체크

---

## 8. 규제 가드레일

| 리스크 | 대응 | 구현 |
|---|---|---|
| 약사법 §24 복약지도 독점 | "복약 정보 안내"로 명명, "복약지도" 용어 금지 | 출력 필터 |
| 의료법 §27 무면허 의료행위 | 진단/처방/용량변경 판단 금지 | System prompt + 금칙어 필터 |
| 개인정보보호법 §23 민감정보 | 투약이력은 로컬 처리, 외부 전송 안 함 | 아키텍처 제약 |
| 의료기기법 SaMD 분류 | 웰니스 영역 유지, 의료 판단 배제 | 기능 범위 제한 |

**금칙 어휘 리스트**: `진단`, `처방합니다`, `투약판단`, `용량을 조절`, `복용을 중단하세요`, `복약지도`

**필수 종결 문구**: 모든 경고/주의 문장 끝에 "의사 또는 약사와 상담하십시오."

---

## 9. 데이터 파일 인벤토리

```
data/
├── drug_permit_detail.json    (2.2 GB, 43,250건)  — 허가정보 전체
├── drug_permit_detail.csv     (48 MB, 43,250건)   — 허가정보 CSV (XML 제외)
├── easy_drug_info.json        (12 MB, 4,711건)    — e약은요 전체
├── easy_drug_info.csv         (11 MB, 4,711건)    — e약은요 CSV
├── bundle_drug_info.json      (14 MB, 16,322건)   — 묶음의약품 전체
├── bundle_drug_info.csv       (6 MB, 16,322건)    — 묶음의약품 CSV
├── medicines.csv              (10 MB, 25,685건)   — 낱알식별 마스터
├── 한국의약품안전관리원_병용금기약물_20240625.csv (152 MB, 542,996건)
├── 117_DT_*.csv               (5 KB, 28건)        — ATC 사용통계
└── metadata.json              — 메타데이터

person_sample/
├── 개인투약이력 가정의학과.xls  — 복호화 완료, 5약물
│   (알게텍정/almagate, 프리마란정/mequitazine, 누코미트캡슐/acetylcysteine,
│    펠루비정/pelubiprofen, 코대원정/chlorpheniramine maleate)
└── 개인투약이력 안과.xls       — 복호화 완료, 6약물
    (포러스안연고/dexamethasone, 레보클점안액/levofloxacin, 팜젠오플록사신정/ofloxacin,
     한림모사프리드정/mosapride, 록스펜정/loxoprofen sodium, 후메론점안액/fluorometholone)

scripts/
├── crawl_easy_drug.py         — e약은요 크롤러
├── crawl_drug_permit.py       — 허가정보 크롤러
└── crawl_bundle.py            — 묶음의약품 크롤러
```
