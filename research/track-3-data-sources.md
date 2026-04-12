# Track 3 — 데이터 소스 가용성 분석

> 필케어(PillCare) 해커톤 예선 제안서용 리서치 노트
> 조사 범위: 국제 약물 DB 7종, 국내 약물 DB 6종, 공개 지식 그래프 2종
> 조사 방법: 각 기관 공식 라이선스/약관/API 문서 WebFetch + 공공데이터포털 직접 확인
> 작성일: 2026-04-11

---

## 개요 테이블

| 소스명 | 제공기관 | 라이선스 | 접근방식 | 비용 | 제안서 | 프로토타입 | 상업화 |
|---|---|---|---|---|---|---|---|
| **RxNorm (데이터)** | NIH/NLM (미국) | Public domain (UMLS 라이선스 필요) | Bulk download / REST API | Free | Y | Y | Y |
| **RxNav Interaction API** | NIH/NLM | — | REST | — | 조건부 (주의) | **N** | **N** |
| **DrugBank** | Univ. Alberta / OMx | Academic: CC BY-NC 4.0 / Commercial: 별도 계약 | Bulk XML, API | Academic free / 상업 유료 (견적제) | 조건부 | 조건부 (Academic) | **N (유료 계약 필수)** |
| **DrugBank Open Data** | 동상 | CC0 | 파일 다운로드 | Free | Y | Y | Y (단, vocab만) |
| **SIDER 4.1** | EMBL | CC BY-NC-SA 4.0 | Bulk TSV | Free | Y | Y (비상업) | **N (비상업 한정)** |
| **OpenFDA** | US FDA | CC0 / Public domain | REST API | Free | Y | Y | Y |
| **DailyMed** | NIH/NLM | Public domain (US gov) | Web / bulk XML / REST | Free | Y | Y | Y |
| **UMLS Metathesaurus** | NIH/NLM | UMLS License (무료, 연간 보고서 의무) | 신청 후 승인 다운로드 | Free | Y | Y | 조건부 (source 별 SRL 확인) |
| **WHO ATC/DDD Index** | WHO CC Norway | 유료 라이선스 (상업·재배포) | 웹 조회 / 구매 | 상업 유료 | Y (코드 인용) | 조건부 | 조건부 (라이선스 계약 권장) |
| **식약처 의약품 낱알식별 API** | 식약처 / 공공데이터포털 | 이용허락범위 제한 없음 (사실상 KOGL Type 1 수준) | REST API + CSV 파일 | Free | Y | Y | Y |
| **식약처 의약품개요정보 API** | 식약처 / 공공데이터포털 | 제한 없음 | REST API | Free | Y | Y | Y |
| **식약처 묶음의약품정보서비스** | 식약처 | 제한 없음 | REST API (JSON+XML) | Free | Y | Y | Y |
| **심평원 DUR 의약품 목록 (파일)** | 건강보험심사평가원 | **KOGL Type 1 (출처표시)** | CSV 파일 다운로드 | Free | Y | Y | Y |
| **심평원 의약품사용정보조회 API** | HIRA | KOGL Type 1 | REST (XML) | Free | Y | Y | Y |
| **약학정보원 (health.kr)** | 약학정보원 | All rights reserved (명시적 API 없음) | 웹 조회만 | — | 조건부 (참고) | **N (별도 협약 필수)** | **N** |
| **KIMS Online** | KIMS (한미약품 계열) | 상용 라이선스 | 유료 API/DB | 유료 | 조건부 (언급) | N (유료) | 조건부 (유료 구독) |
| **DRKG** | Amazon Science (GNN4DR) | Apache-2.0 (+ 소스별 라이선스 주의) | GitHub bulk | Free | Y | Y | 조건부 (DrugBank 파생분 제외) |
| **PrimeKG** | Harvard Zitnik Lab | CC BY 4.0 | Harvard Dataverse CSV | Free | Y | Y | Y (출처표시) |
| **Hetionet** | Greene Lab | CC0 1.0 | Neo4j dump / TSV | Free | Y | Y | Y |

---

## 소스별 상세 1-pager

### 1. RxNorm (NIH/NLM)
- **제공기관**: U.S. National Library of Medicine (NIH/NLM)
- **URL**: https://www.nlm.nih.gov/research/umls/rxnorm/
- **라이선스**: RxNorm 어휘 자체는 미국 정부 저작물로 **public domain**. 단, UMLS 라이선스(무료) 수락이 공식 다운로드 조건. 일부 포함 용어는 Source Restriction Level(SRL)이 있어 개별 확인 필요.
- **접근방식**: 월간 풀 릴리스 bulk 다운로드(RRF) + REST API (RxNav). API는 키 불필요.
- **커버리지**: 미국 시판 의약품 중심 (성분/브랜드/임상 약물). 한국 제품은 직접 포함되지 않음. 영어.
- **비용**: Free
- **제한사항**: 재배포 시 "최신 버전 유지" 또는 "최신이 아님 명시" 의무 / NLM 크레딧 고지 / 일부 sub-source는 상업 재배포 제한.
- **사용 가능성**: 제안서[**Y**], 프로토타입[**Y**], 상업화[**Y**]
- **메모**: RxCUI는 필케어의 "국제 통합 ID" 축으로 가장 합리적. 한국 EDI 코드 ↔ RxCUI 공식 매핑은 없음 → **ATC 코드를 brige로 사용**하는 전략이 현실적.
- **출처 URL**: https://www.nlm.nih.gov/research/umls/rxnorm/docs/termsofservice.html , https://lhncbc.nlm.nih.gov/RxNav/APIs/RxNormAPIs.html

### 2. RxNav Drug Interaction API ⚠️
- **상태**: **2024-01-02 폐지됨 (Discontinued)**. RxNav UI의 Interactions 탭도 함께 제거.
- **이유**: 유지보수 비용 / 데이터 제공자(DrugBank, ONCHigh) 라이선스 문제
- **영향**: 과거 "무료 상호작용 API"로 많이 인용되던 소스가 **더 이상 존재하지 않음**. 필케어 제안서에서 "RxNav로 DDI 조회" 같은 서술은 **절대 피해야** 함.
- **대안**: (a) DrugBank 유료 라이선스, (b) 국내 심평원 DUR 데이터로 자체 구축, (c) SIDER 등 연구용 소스 (비상업), (d) Open Source 지식 그래프(DRKG/PrimeKG/Hetionet)에서 파생.
- **사용 가능성**: 제안서[**조건부 - 역사적 맥락만**], 프로토타입[**N**], 상업화[**N**]
- **출처 URL**: https://blog.drugbank.com/nih-discontinues-their-drug-interaction-api/

### 3. DrugBank
- **제공기관**: University of Alberta / OMx Personal Health Analytics Inc.
- **URL**: https://go.drugbank.com/
- **라이선스**:
  - **Academic License**: 대학·비영리 연구자 대상, CC BY-NC 4.0 (비상업). 계정 생성 후 심사 신청.
  - **Open Data 서브셋 (vocabulary/structures)**: CC0 → 자유 이용 (식별자·이름 수준만).
  - **Commercial License**: 별도 견적 계약 필수. 가격은 비공개 (업계 정보상 연간 수천만 원~수억 원대).
- **접근방식**: 승인 후 XML bulk 다운로드 + 상업 고객 전용 API
- **커버리지**: 15,000+ 약물, ~1.8M 상호작용, 대사·타겟·부작용 (상업 full DB 기준). 영어.
- **비용**: Academic free / Commercial 유료
- **제한사항**: **비상업 조건부 학술 라이선스로 개발한 결과물을 상업 서비스에 투입 불가** → 프로토타입 후 상업화 시점에 재라이선스 필수.
- **사용 가능성**: 제안서[**조건부 - "Open Data + 상업 계약 옵션" 명시**], 프로토타입[**조건부 - Academic 또는 Open Data**], 상업화[**N - 유료 계약 전제**]
- **메모**: 제안서에는 "Open Data(CC0) 부분은 상업 이용 가능, 전체 DB는 본 출시 시점 계약 예정" 이라고 분리 서술하는 것이 정확.
- **출처 URL**: https://go.drugbank.com/releases/latest

### 4. SIDER 4.1 (Side Effect Resource)
- **제공기관**: EMBL (Kuhn et al.)
- **URL**: http://sideeffects.embl.de/
- **라이선스**: **CC BY-NC-SA 4.0** (비상업, 동일조건 변경 허락)
- **접근방식**: TSV bulk 파일 다운로드
- **커버리지**: 1,430개 약물 × 5,880 부작용 × 140K 연결 (SIDER 4.1, 2015년 최종 업데이트 — 10년째 정지)
- **비용**: Free (비상업)
- **제한사항**: 비상업 전용 / ShareAlike 전염성 / 업데이트 중단 상태
- **사용 가능성**: 제안서[**Y - 근거 데이터로 언급**], 프로토타입[**Y - 비상업 POC**], 상업화[**N**]
- **메모**: 상업 서비스에 그대로 삽입 불가. 제안서에서는 "부작용 패턴 학습의 레퍼런스" 정도로만 인용.
- **출처 URL**: http://sideeffects.embl.de/ (SSL 인증 이슈 있음)

### 5. OpenFDA ★
- **제공기관**: U.S. Food and Drug Administration
- **URL**: https://open.fda.gov/
- **라이선스**: **CC0 1.0 / Public domain** ("FDA waives all rights to the work worldwide"). 상업 사용 명시적 허용.
- **접근방식**: REST API (JSON). API 키 무료 발급.
- **Rate limit**: 키 없음 240 req/min·1,000/day per IP / 키 사용 시 240/min·**120,000/day** per key
- **커버리지**: Drug Adverse Events(FAERS), Drug Labels, NDC, Drugs@FDA, Recalls/Enforcement, Shortages. 미국 시판 제품 위주, 영어.
- **비용**: Free
- **제한사항**: 일부 dataset에 써드파티 저작권 마킹 가능 (개별 확인) / 한도 초과 시 문의.
- **사용 가능성**: 제안서[**Y**], 프로토타입[**Y**], 상업화[**Y**]
- **메모**: 필케어의 "국제 부작용·리콜 시그널" 트리거로 최적. 한국 약물에는 직접 적용 안 되므로 성분(ingredient) 또는 ATC 매칭으로 교차 이용.
- **출처 URL**: https://open.fda.gov/terms/ , https://open.fda.gov/apis/authentication/

### 6. DailyMed
- **제공기관**: NIH/NLM
- **URL**: https://dailymed.nlm.nih.gov/
- **라이선스**: NLM 자료는 **public domain** (정부 저작물). SPL(Structured Product Labeling) XML bulk 제공.
- **접근방식**: Web 조회 / SPL bulk ZIP 다운로드 / RESTful service
- **커버리지**: FDA 등록 제품 라벨 전체 (~100K+), 실사용 용법·금기·경고·상호작용 섹션 포함. 영어.
- **비용**: Free
- **제한사항**: 큰 저작권 제약 없음. 공식 라이선스 페이지 직접 문구는 검증 필요.
- **사용 가능성**: 제안서[**Y**], 프로토타입[**Y**], 상업화[**Y**]
- **메모**: OpenFDA와 보완 관계. 라벨 원문 NLP로 "DDI 섹션" 추출해 RxCUI 기반 그래프 구축 가능.
- **출처 URL**: https://dailymed.nlm.nih.gov/dailymed/help.cfm
- **검증 필요 표시**: DailyMed 라이선스 페이지 문구는 explicit verification needed (현재 help 페이지에서 직접 확인 불가).

### 7. UMLS Metathesaurus
- **제공기관**: NIH/NLM
- **URL**: https://www.nlm.nih.gov/research/umls/
- **라이선스**: **UMLS Metathesaurus License Agreement** — 무료지만 개인별 계정·연간 사용 보고서 의무. 200+ source vocab 각각에 Source Restriction Level(SRL 0~4).
- **접근방식**: UTS 계정 승인 후 풀 릴리스 RRF 다운로드 + REST API (UTS)
- **커버리지**: 200+ 생의학 용어체계 통합 (RxNorm, SNOMED CT, MeSH, ICD 등)
- **비용**: Free (UTS 계정)
- **제한사항**:
  - 일부 source는 non-US 사용자 제한, 번역 금지, 상업 재배포 불가
  - **어휘 자체를 판매/재배포 금지**
  - 통합 앱에 embed는 가능
  - **한국어 추가 지원 없음**
- **사용 가능성**: 제안서[**Y**], 프로토타입[**Y**], 상업화[**조건부 - SRL 재확인 필수**]
- **메모**: 상업화 시점에 사용 source 리스트를 뽑아 SRL별로 법무 검토 필요.
- **출처 URL**: https://www.nlm.nih.gov/research/umls/knowledge_sources/metathesaurus/release/license_agreement.html

### 8. WHO ATC/DDD Index
- **제공기관**: WHO Collaborating Centre for Drug Statistics Methodology (노르웨이 FHI)
- **URL**: https://atcddd.fhi.no/
- **라이선스**: **유료 라이선스** (재배포·상업). 웹 무료 검색만 허용, bulk 파일 다운로드·API 재배포는 별도 계약.
- **접근방식**: 웹 검색 / 구매 (bulk data files, annual license)
- **커버리지**: ~6,000 성분, 계층 분류 5단계 (Anatomical → Chemical substance), DDD. 다국어 아님(영어).
- **비용**: 연간 라이선스 유료 (수백 EUR 수준부터, 기관 규모에 따라 상이)
- **제한사항**:
  - 가격 결정·상환 기초로 사용 금지 (misuse 정의)
  - 마케팅 도구 금지
  - 코드 자체를 DB에 bulk로 포함해 재배포 시 계약 필수
- **사용 가능성**: 제안서[**Y** - 분류 체계 언급은 자유], 프로토타입[**조건부** - 소수 코드 수동 매핑], 상업화[**조건부** - 라이선스 계약 권장]
- **메모**: 국내 식약처 API가 **ATC 코드를 이미 포함**해 제공하므로, 필케어는 "식약처 제공 ATC"를 그대로 이용하면 WHO와 직접 계약 우회 가능. 다만 국제 확장 시 재검토.
- **출처 URL**: https://atcddd.fhi.no/use_of_atc_ddd/

### 9. 식약처 의약품 낱알식별 정보 API ★ (로컬 medicines.csv의 출처)
- **제공기관**: 식품의약품안전처 / data.go.kr
- **URL**: https://www.data.go.kr/data/15075057/openapi.do , https://nedrug.mfds.go.kr/
- **라이선스**: "이용허락범위 제한 없음" (상업 이용 가능, 사실상 KOGL Type 1 수준)
- **접근방식**: REST OpenAPI (JSON+XML) + CSV 파일 다운로드 (개발계정 10,000/일, 운영계정 심의 후 확장)
- **커버리지**: 국내 허가 의약품 약 25,000~30,000 품목. ITEM_SEQ, 제품명(한/영), 제조사, 모양·색·크기·각인, 이미지 URL, 분류코드·분류명, ETC_OTC 구분, 허가일, **EDI_CODE** 제공.
- **비용**: Free
- **제한사항**: 활용 신청 후 운영계정 전환은 심의승인
- **사용 가능성**: 제안서[**Y**], 프로토타입[**Y**], 상업화[**Y**]
- **메모**: 로컬 `medicines.csv` (25,689행, 헤더: ITEM_SEQ, ITEM_NAME, ENTP_NAME, CHART, ITEM_IMAGE, ..., ATC 필드 없음, EDI_CODE 있음) = 본 데이터셋 확정. 필케어 "사진 기반 알약 식별" 기능의 근간.
- **출처 URL**: https://www.data.go.kr/data/15075057/openapi.do

### 10. 식약처 의약품개요정보 API
- **제공기관**: 식약처 / data.go.kr
- **라이선스**: 이용허락범위 제한 없음
- **접근방식**: REST (JSON+XML), 10,000/일 (개발)
- **커버리지**: 효능, 사용법, 주의사항, 상호작용, 부작용, 보관법, 낱알이미지, 허가정보, **ATC 코드** 포함
- **비용**: Free
- **사용 가능성**: 제안서[**Y**], 프로토타입[**Y**], 상업화[**Y**]
- **메모**: 낱알식별 API와 ITEM_SEQ로 조인 가능. 필케어의 "복약 지침/주의사항" 본문 소스.
- **출처 URL**: https://www.data.go.kr/data/15075057/openapi.do

### 11. 식약처 묶음의약품정보서비스 API ★
- **제공기관**: 식약처
- **라이선스**: 이용허락범위 제한 없음
- **접근방식**: REST (JSON+XML)
- **커버리지**: 대표 품목기준코드 ↔ 동일/유사 성분 제품 그룹, 주성분, 함량, 심평원 코드, **ATC 코드** 매핑
- **비용**: Free
- **사용 가능성**: 제안서[**Y**], 프로토타입[**Y**], 상업화[**Y**]
- **메모**: **국내 EDI/품목코드 ↔ ATC ↔ RxNorm 브릿지의 핵심**. 필케어 통합 지식 그래프의 "한·국 매핑" 축 역할을 이 API 하나가 거의 해결해 줌.
- **출처 URL**: https://www.data.go.kr/data/15063908/openapi.do

### 12. 심평원 DUR 의약품 목록 (파일 dataset) ★★
- **제공기관**: 건강보험심사평가원
- **URL**: https://www.data.go.kr/data/15127983/fileData.do
- **라이선스**: **KOGL 제1유형 (출처표시)** — 상업 이용 명시적 허용
- **접근방식**: CSV 파일 다운로드 (연간 갱신, 2026-06-30 차기)
- **커버리지**: **병용금기, 연령금기, 임부금기, 노인주의** 의약품 품목 정보. 복합제는 대표성분명만.
- **비용**: Free
- **제한사항**: 연간 갱신 주기 → 실시간성 부족. 복합제 표현 제약.
- **사용 가능성**: 제안서[**Y**], 프로토타입[**Y**], 상업화[**Y**]
- **메모**: 필케어의 "국내 DUR 점검"의 라이선스적 기반. **필케어 제안서의 'RxNav 폐지 이후 대안'의 핵심 카드**. 이것이 있어서 상업화가 가능하다.
- **출처 URL**: https://www.data.go.kr/data/15127983/fileData.do

### 13. 심평원 의약품사용정보조회서비스 API
- **제공기관**: HIRA
- **URL**: https://www.data.go.kr/data/15047819/openapi.do
- **라이선스**: KOGL Type 1
- **접근방식**: REST API (XML), 14개 엔드포인트
- **커버리지**: 지역/의료기관/질환별 약효분류, ATC 3-4단계, 성분별 사용 통계
- **비용**: Free
- **사용 가능성**: 제안서[**Y**], 프로토타입[**Y**], 상업화[**Y**]
- **메모**: 개별 환자 데이터 아닌 통계 데이터지만, 필케어에서 "동일 질환 환자 평균 복약 패턴" 같은 인사이트 생성 가능.
- **출처 URL**: https://www.data.go.kr/data/15047819/openapi.do

### 14. 건강보험심사평가원 약가기준정보조회서비스
- **제공기관**: HIRA
- **URL**: https://data.edmgr.kr/dataView.do?id=www-data-go-kr-data-openapi-15054445
- **라이선스**: KOGL Type 1 (추정 - 동일 플랫폼)
- **접근방식**: REST API
- **커버리지**: 약제급여목록, 급여상한금액, 보험코드(EDI)
- **비용**: Free
- **사용 가능성**: 제안서[**Y**], 프로토타입[**Y**], 상업화[**Y**]
- **메모**: 필케어 "복약 비용 알림" 기능 확장에 사용 가능.
- **검증 필요**: 정확한 KOGL 등급 표시 확인 필요.

### 15. 약학정보원 (health.kr)
- **제공기관**: Korea Pharmaceutical Information Center
- **URL**: https://www.health.kr/
- **라이선스**: "All Rights Reserved" (저작권 전유). **명시적 공개 API 없음.**
- **접근방식**: 웹 조회만 (검색 UI)
- **커버리지**: 의약품 상세, 성분/KPIC 약효분류, 식별검색, **약물 상호작용**, 복약정보 픽토그램, 허가 리뷰
- **비용**: 웹 무료 / 데이터 제공은 별도 협약 필요
- **제한사항**: 크롤링·자동 수집 이용 약관 금지 / 별도 협약 없이 앱에 embed 불가
- **사용 가능성**: 제안서[**조건부** - "국내 임상 전용 피처 협약 대상"으로 언급], 프로토타입[**N**], 상업화[**N** - 별도 계약 전제]
- **메모**: 국내 임상에서 가장 권위 있는 복약 정보 소스 중 하나지만, **필케어가 직접 의존하면 안 됨**. 협약 대상자로만 명기.
- **출처 URL**: https://www.health.kr/

### 16. KIMS Online
- **제공기관**: KIMS (한미약품 그룹)
- **URL**: https://www.kimsonline.co.kr/
- **라이선스**: 상용. 개인 구독 / 기관 구독.
- **접근방식**: 웹 / 일부 기관 API (B2B)
- **커버리지**: 국내 의약품 상세, 상호작용, 복약지도
- **비용**: 유료 구독
- **사용 가능성**: 제안서[**조건부**], 프로토타입[**N**], 상업화[**조건부** - B2B 계약]
- **메모**: 약학정보원과 유사한 포지션. 필케어가 "의료진 연계 기능"에서 B2B 파트너십 옵션으로 언급 가능.

### 17. DRKG (Drug Repurposing Knowledge Graph)
- **제공기관**: Amazon Science / gnn4dr
- **URL**: https://github.com/gnn4dr/DRKG
- **라이선스**: **Apache-2.0** (코드) + **소스별 라이선스 중첩** (데이터 노드·엣지)
- **접근방식**: GitHub bulk
- **커버리지**: 97,238 엔티티, 5.87M 트리플, 13 엔티티 타입 / 107 관계 / DrugBank·Hetionet·GNBR·STRING·IntAct·DGIdb 통합
- **비용**: Free
- **제한사항**: DrugBank 기원 엣지는 상업 사용 제한 가능성. 노드·엣지별 라이선스 속성 확인 필수.
- **사용 가능성**: 제안서[**Y** - 지식그래프 설계 레퍼런스], 프로토타입[**Y** - 연구용 POC], 상업화[**조건부** - DrugBank 파생 데이터 필터링]
- **메모**: 직접 제품에 embed보다는 **필케어 자체 KG 설계의 reference schema**로 활용.

### 18. PrimeKG (Harvard)
- **제공기관**: Harvard Zitnik Lab
- **URL**: https://github.com/mims-harvard/PrimeKG
- **라이선스**: **CC BY 4.0** (상업 이용 가능, 출처표시만)
- **접근방식**: Harvard Dataverse CSV
- **커버리지**: 129K 노드, 4.1M 관계, 약물·질환·표현형·유전자·경로·부작용·해부
- **비용**: Free
- **사용 가능성**: 제안서[**Y**], 프로토타입[**Y**], 상업화[**Y**]
- **메모**: 상업화 가능한 지식 그래프로는 가장 매력적. 필케어가 "만성질환 코호트 추론"을 제공할 때의 백본 후보.

### 19. Hetionet
- **제공기관**: Greene Lab (펜실베이니아)
- **URL**: https://het.io/
- **라이선스**: **CC0 1.0** (퍼블릭 도메인)
- **접근방식**: Neo4j dump / TSV
- **커버리지**: 47K 노드, 2.25M 엣지, 11 데이터 소스 통합 (약물, 질환, 유전자, 부작용, 해부, 경로 등)
- **비용**: Free
- **사용 가능성**: 제안서[**Y**], 프로토타입[**Y**], 상업화[**Y**]
- **메모**: PrimeKG보다 규모는 작지만 **라이선스 최상급(CC0)**. 상업화 리스크 제로.

---

## 추가 발굴 데이터 소스 (기본 리스트 외)

- **식약처 의약품 부작용 정보** (공공데이터포털, 이용허락범위 제한 없음) — 국내 부작용 시그널 데이터.
- **식약처 '실마리정보' (의약품 이상사례 실마리)** — 일반 공개는 제한적, 집계 통계만.
- **국가건강정보포털 (KDCA)** — 질환·약물 일반 교육 콘텐츠, 재배포는 출처표시.
- **식의약 데이터 포털 (data.mfds.go.kr)** — 식약처 자체 데이터 허브, 낱알식별 등 복수 API 직접 제공.
- **보건의료빅데이터개방시스템 (opendata.hira.or.kr)** — 심평원 허브, DUR 외 추가 API 다수.
- **MIMIC-IV** (PhysioNet, PhysioNet Credentialed Health Data License) — 환자 수준 처방 로그, **상업 이용 금지**, 과정 이수 필요. 필케어 학습 데이터로 프로토타입 가능.
- **DailyMed + OpenFDA 조합** — SPL 라벨 NLP로 상호작용 섹션 추출 → 자체 DDI 그래프 구축 (RxNav 폐지 이후 사실상 표준 대안).
- **DDInter 2.0 / DrugCombDB** — 학술 DDI 데이터셋, 보통 CC BY-NC.
- **Hugging Face Datasets**: `drugbank`, `ddi-extraction`, `pharmkg` 등 다수. 원천 라이선스 상속되므로 개별 확인 필수.
- **NDF-RT (Veterans Health Administration)** — 국제 클래스/약물 관계, UMLS 내 포함.

---

## ★ 권장 통합 조합 (Recommended Integration Stack)

### Stack A — 제안서 단계 (서면 설명용, 법적 리스크 0)
> 모든 소스는 문서화된 무료·상업 허용 소스만 사용
- **국내 백본**: 식약처 낱알식별 API + 의약품개요정보 API + **묶음의약품정보서비스** + 심평원 DUR 파일(KOGL Type 1) + 심평원 의약품사용정보
- **국제 백본**: RxNorm (public domain) + OpenFDA (CC0) + DailyMed (public domain) + PrimeKG (CC BY) + Hetionet (CC0)
- **브릿지**: ATC 코드 (식약처 API 내 내장, WHO 직접 라이선스 불필요)
- **언급만**: DrugBank Open Data (CC0 vocab), UMLS
- **제안서 메시지**: "상용 계약 없이도 전 단계 프로토타입·상용화 가능한 라이선스 조합"

### Stack B — 프로토타입 (POC, 해커톤~12개월)
- Stack A 전체 +
- DrugBank **Academic License** (심사 통과 전제, 비상업 범위)
- SIDER 4.1 (비상업, 부작용 근거)
- DRKG (DrugBank 파생 엣지 조심)
- MIMIC-IV (학습/검증 데이터, credentialed)

### Stack C — 상업화 (제품 출시 이후)
- **유지**: 식약처 전 API, 심평원 DUR 파일, OpenFDA, RxNorm, DailyMed, PrimeKG, Hetionet
- **제거 필수**: SIDER, DrugBank Academic, DRKG 중 DrugBank 파생 엣지, MIMIC-IV, 약학정보원/KIMS 임의 크롤
- **추가 계약 옵션 (선택)**:
  - DrugBank Commercial License (해외 확장 시점)
  - WHO ATC/DDD 기관 라이선스 (해외 확장 시점)
  - 약학정보원 / KIMS B2B 협약 (국내 임상 연계 기능)

### Stack D — "Zero-License-Risk" 최소 상업 조합 ⭐
> 하나라도 라이선스 문제가 터져도 완전히 운영 가능한 보수적 조합
- 식약처 낱알식별 + 묶음의약품 + 개요정보 API (국내, 제한 없음)
- 심평원 DUR 파일 (KOGL Type 1)
- OpenFDA (CC0)
- DailyMed (Public domain)
- RxNorm (Public domain)
- Hetionet (CC0)
- PrimeKG (CC BY 4.0)
- **이 7종만으로도 한국 환자 대상 필케어 MVP는 법적으로 100% 클리어**

---

## ⚠️ Show-stopper 리스크

### [CRITICAL] RxNav Drug Interaction API 폐지 (2024-01-02)
- NIH가 RxNav의 DDI API를 종료. "무료 국제 DDI API = RxNav" 가정이 무너짐.
- 필케어 제안서에서 **절대 이 API를 근거로 서술하면 안 됨**.
- **대응**: 국내 DDI는 심평원 DUR 파일(KOGL Type 1)로 완전 해결, 국제 DDI는 (a) DailyMed SPL 라벨 NLP 추출 + (b) PrimeKG/Hetionet 그래프 활용 + (c) 상업화 시점 DrugBank 유료 계약의 3-티어로 대응.
- **피벗 필요 여부**: NO. 대안 경로가 충분.

### [HIGH] DrugBank 상업 라이선스의 숨은 비용
- 학계 데모를 "그대로" 상용 서비스에 투입 못함. 필케어가 제안서에서 DrugBank를 "핵심 백본"으로 서술하면 심사관은 상업화 가능성에 의문.
- **대응**: 제안서에서 DrugBank는 "Open Data(CC0 vocab) 부분만 활용, 전체 DB는 상업화 시점 계약" 으로 분리 서술.
- **피벗**: 불필요.

### [MEDIUM] UMLS 상업 사용 시 SRL 개별 검토 부담
- 상용 출시 때 "어떤 source를 import했는지" 재감사 필요.
- **대응**: 상업화 리포지토리에 "UMLS sub-source 화이트리스트"를 두고 빌드 타임 필터.
- **피벗**: 불필요.

### [MEDIUM] 약학정보원·KIMS 데이터 무단 사용 금지
- 국내 임상 실무에서 가장 친숙한 소스지만 자동 수집·재배포 불가.
- **대응**: 제안서에서 B2B 파트너십 대상으로만 명기, 직접 의존 금지.
- **피벗**: 불필요.

### [LOW] WHO ATC/DDD 직접 라이선스
- 식약처 API가 ATC 코드를 내장 제공하므로 필케어는 WHO와 직접 계약 불필요. 단, 해외 확장 시점 재검토.

### 종합 결론
**Show-stopper 없음. 피벗 불필요.** 필케어는 **Stack D (Zero-License-Risk 조합)** 만으로도 국내 시장에서 합법적 상용화가 가능하며, 해외 확장 시점에 DrugBank / WHO / UMLS SRL 계약을 추가하는 단계적 전략이 현실적.

**제안서에서 강조할 킬러 문구 후보**:
> "필케어는 RxNav 종료(2024-01)에도 불구하고 심평원 DUR 파일(KOGL Type 1)과 PrimeKG(CC BY)를 활용, **상용 라이선스 계약 없이도** 국내 대상 MVP의 법적 기반을 완비하였습니다."

---

## 참고 URL 로그

- RxNorm Terms: https://www.nlm.nih.gov/research/umls/rxnorm/docs/termsofservice.html
- RxNav APIs: https://lhncbc.nlm.nih.gov/RxNav/APIs/RxNormAPIs.html
- NIH RxNav DDI 폐지 공지: https://blog.drugbank.com/nih-discontinues-their-drug-interaction-api/
- DrugBank Releases/License: https://go.drugbank.com/releases/latest
- OpenFDA Terms: https://open.fda.gov/terms/
- OpenFDA Authentication: https://open.fda.gov/apis/authentication/
- UMLS License Agreement: https://www.nlm.nih.gov/research/umls/knowledge_sources/metathesaurus/release/license_agreement.html
- DailyMed Help: https://dailymed.nlm.nih.gov/dailymed/help.cfm
- SIDER: http://sideeffects.embl.de/ (SSL issue 주의)
- WHO ATC/DDD: https://atcddd.fhi.no/use_of_atc_ddd/
- KOGL 라이선스: https://www.kogl.or.kr/info/license.do
- 공공데이터포털 - 식약처 낱알식별: https://www.data.go.kr/data/15075057/openapi.do
- 공공데이터포털 - 식약처 묶음의약품: https://www.data.go.kr/data/15063908/openapi.do
- 공공데이터포털 - 심평원 DUR 목록: https://www.data.go.kr/data/15127983/fileData.do
- 공공데이터포털 - 심평원 의약품사용정보: https://www.data.go.kr/data/15047819/openapi.do
- 심평원 보건의료빅데이터: https://opendata.hira.or.kr/op/opc/selectOpenApiInfoView.do
- 약학정보원: https://www.health.kr/
- DRKG: https://github.com/gnn4dr/DRKG
- PrimeKG: https://github.com/mims-harvard/PrimeKG
- Hetionet: https://het.io/

---

## 검증 필요 항목 (Explicit Verification Needed)
1. **DailyMed 공식 copyright/license 페이지 원문** — 공식 문구 확인 필요 (현재 help 페이지에서 직접 확인 실패)
2. **DrugBank 상업 라이선스 실제 가격** — 영업팀 견적 필수, 제안서 시점엔 "별도 계약" 수준으로 언급
3. **심평원 약가기준정보조회서비스 KOGL 등급** — Type 1 추정, 공식 표기 재확인
4. **UMLS 2026년 최신 SRL 표** — source별 상업 제한 목록은 매년 변경 가능
5. **한국어 UMLS 확장** — 현재 공식 확장 없음으로 파악, 국내 한의학/KOSTOM 등 별도 프로젝트 존재 가능성 추가 탐색 여지

---

## Addendum — DrugCentral 추가 조사 (2026-04-11)

> 사용자 요청으로 추가 조사한 소스. 기존 Stack D에는 포함되지 않았으나 **약리학적 근거 레이어**(Pharmacology Layer)로서 높은 가치가 있음.

### DrugCentral 1-pager
- **제공기관**: University of New Mexico, Translational Informatics Division (UNM TID). 2016년 최초 발표, NAR(Nucleic Acids Research) 저널에 주기적 업데이트 논문 게재
- **URL**: https://drugcentral.org/
- **최신 버전**: **2023년 11월 1일** (2024/2025 버전 없음). 업데이트 주기 연 1회 수준
- **라이선스**: ⚠️ **모호함 (verification needed)**
  - 사이트 하단 "License" 링크는 /privacy로 연결, 명시적 라이선스 문구 미확인
  - NAR 논문 자체는 Oxford OUP 표준 — 비상업 재사용 허용, 상업 재사용은 journals.permissions@oup.com 문의
  - 일부 외부 문서는 "CC BY-SA 4.0" 으로 기재하나 **공식 사이트에서 재확인 실패**
  - **결론**: 학술/연구/제안서 단계는 Y, **상업화 단계는 반드시 UNM TID 또는 OUP 라이선스 재확인 필요**
- **접근방식**: 
  - (a) 웹 쿼리 인터페이스 (drugcentral.org)
  - (b) Smart API (https://drugcentral.org/OpenAPI)
  - (c) Bulk Download: 데이터베이스 덤프(PostgreSQL), drug-target interaction TSV, FDA/EMA/PMDA 승인 약물 CSV, 화학구조 SDF/SMILES/InChI
- **커버리지**:
  - 약물: 약 4,995개 (FDA + 전 세계 승인 + 단종 포함)
  - 약제학 레코드: 약 152,476개
  - 약물-타겟 관계 (drug-target interactions, 약물-약물 아님)
  - FAERS 연동: **성별·연령별 세분화된 이상반응 데이터**
  - 약리학(pharmacology) · 작용기전(MoA) · 적응증(indication) · ADR
  - SNOMED-CT 질병 어휘, OMOP 어휘 사용
  - 수의약품 1,805 bioactivities / 226 drugs
- **비용**: 무료 (학술 이용)
- **제한사항**:
  - ⚠️ DDI(drug-drug interaction) 데이터는 **직접 제공하지 않음** — 약물-**타겟** 상호작용만
  - 상업적 사용은 라이선스 재확인 필요
  - 한국 약물 커버리지 없음 (KFDA 승인 약물 미포함) — 국내 약물은 식약처 DB로만 커버 가능

### ★ 필케어 관점의 전략적 가치

DrugCentral은 **DUR(심평원) 의 "무엇"을 보완하는 "왜" 레이어** 로서 고유의 가치가 있음:
- 심평원 DUR: "A + B 병용금기"라는 **규칙** 제공
- DrugCentral: "A는 세로토닌 수용체, B도 세로토닌 수용체 → 세로토닌 증후군 리스크" 라는 **기전 근거** 제공
- FAERS 연동: "실제로 이 조합에서 보고된 이상반응 N건" 이라는 **실증 근거** 제공

이 세 레이어가 결합되면 필케어의 에이전트 응답이 다음 형태가 됨:
> "심평원 DUR 규칙 상 A와 B는 병용금기로 등록돼 있습니다 [DUR 근거]. 두 약물은 모두 세로토닌 5-HT 수용체에 작용하며 [DrugCentral 기전], FAERS 상 이 조합에서 보고된 이상반응은 N건입니다 [실증]. 의료진에게 확인을 요청하세요."

이것이 **Grounded RAG 의 3중 근거** (규칙 + 기전 + 실증) 를 만드는 핵심 자산이며, 차별점 ①(Agentic) + ③(통합 그래프) + ⑤(환각 차단) 모두를 강화.

### 사용 가능성 판정

| 단계 | 가능성 | 조건 |
|---|---|---|
| 제안서 단계 (근거 언급) | ✅ Y | 별도 허가 불필요, 인용만 |
| 프로토타입/POC (소량 데이터 활용) | ✅ Y | 학술/연구 목적 명시하여 사용 |
| 상업화 (앱 출시 후) | ⚠️ 조건부 | **UNM TID 또는 OUP와 라이선스 재확인 필수** — 상업화 시점에 별도 조치 |

### Stack D 업데이트 (Zero-License-Risk → "Low-License-Risk Core + Context Enrichment")

기존 Stack D는 "상용 계약 없이 MVP 전 단계 운영 가능"이 핵심 서사였음. DrugCentral은 이 핵심에 편입시키면 라이선스 모호성 때문에 서사가 약해짐. 따라서 다음과 같이 **계층 분리**:

- **Core Layer (Zero-License-Risk)**: 식약처 3종 + 심평원 DUR(KOGL Type 1) + OpenFDA(CC0) + RxNorm(PD) + DailyMed(PD) + PrimeKG(CC BY) + Hetionet(CC0)
  - 이 레이어만으로 MVP · 프로토타입 · 상업화 가능
- **Enrichment Layer (Academic-Safe, Commercial-Verify)**: DrugCentral (기전·FAERS 근거)
  - 제안서와 프로토타입에 사용, 상업화 시점엔 라이선스 재확인 후 유지 또는 대체

이렇게 계층을 분리하면:
1. 제안서 서사 "Zero-License-Risk"는 Core Layer로 방어
2. DrugCentral 추가는 "근거 품질 업그레이드"로 서사화
3. 상업화 시 라이선스 모호성이 문제되면 DrugCentral만 분리 교체 가능 (OpenFDA FAERS + PrimeKG 기전 경로로 대체)

### 출처

- DrugCentral 메인: https://drugcentral.org/
- DrugCentral Download: https://drugcentral.org/download
- DrugCentral Smart API: https://drugcentral.org/OpenAPI
- UNM Translational Informatics Division: https://datascience.unm.edu/drugcentral-2/
- NAR 원저 (2017): https://academic.oup.com/nar/article/45/D1/D932/2333938
- 2023 업데이트 논문 (PMC): https://pmc.ncbi.nlm.nih.gov/articles/PMC10692006/

### ✂️ 결정 (2026-04-11)
**DrugCentral은 현재 스택에서 제외 (Parking Lot 이동)**. 사유:
- 라이선스 모호성이 "Zero-License-Risk" 핵심 서사를 흐림
- 2023년 11월 이후 업데이트 없음 (신선도 낮음)
- DDI 데이터를 직접 제공하지 않아 Core 가치 제한적
- 향후 상업화 시점에 OpenFDA FAERS + PrimeKG 기전 경로로 동일 가치 확보 가능

재검토 조건: 상업화 단계에서 UNM TID/OUP와 라이선스 명확화가 이뤄지면 Enrichment Layer로 재편입 검토.
