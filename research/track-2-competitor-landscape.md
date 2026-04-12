# Track 2 — 경쟁자/유사기술 분석

조사일: 2026-04-11
대상 제안서: 필케어(PillCare) — 만성질환자·다약제 복용자를 위한 AI 복약 관리 에이전트
작성 원칙: 공식 출처(회사 홈페이지, 앱스토어 공식 설명, 공식 보도자료)만 인용. 미확인 기능은 "unclear" 명시.

---

## 비교표 (최종)

| # | 서비스명 | 국적 | DB 소스 | DUR 범위 | AI 방식 | 멀티프로필 | 액션 경계 | 무료/유료 | URL | 조사일 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 네이버 헬스케어 복약관리 | KR | 국내 (약 봉투 OCR 기반 자체 DB) | unclear (상호작용 경고 기능 공식 발표 없음) | OCR + 약 정보 요약 AI (처방전 자동 입력) | unclear | 단순 알림·복용 여부 체크 | 무료 | https://naver.me/ (네이버앱 헬스케어) | 2026-04-11 |
| 2 | 닥터나우 | KR | 국내 (처방전 기반) | 없음 (단일 처방 내 기록만) | AI 증상 체크, AI 의료 포털 (상담형) | unclear | 알림 + 포인트 리워드 (복약 기록 시 포인트) | 무료 | https://doctornow.co.kr | 2026-04-11 |
| 3 | 나만의닥터 (마이닥터) | KR | 국내 (사용자 직접 등록) | 없음 | 없음 (규칙 기반 알림) | unclear | 알림 + 포인트 리워드 | 무료 | https://my-doctor.io | 2026-04-11 |
| 4 | 올라케어 (KB 올라케어) | KR | 국내 (비대면진료 연동) | 없음 (공식 발표 없음) | 올라코디 (AI 맞춤형 헬스케어, 세부 tool-use 여부 unclear) | unclear | 정기 복약 알림 + 재진 안내 + 약 배송 | 무료 | https://www.kbollacare.com | 2026-04-11 |
| 5 | 굿닥 | KR | 해당없음 (복약관리 공식 기능 없음) | 없음 | 없음 | 가족 추가 O (병원 예약용) | 병원 접수·비대면진료 (복약 알림 공식 기능 미제공) | 무료 | https://www.goodoc.co.kr | 2026-04-11 |
| 6 | 똑닥 | KR | — | — (서비스 중단) | — | — | **복약관리 서비스 2023년 종료** | 무료 | https://ddocdoc.com | 2026-04-11 |
| 7 | 내가 먹는 약! 한눈에 (HIRA) | KR (정부) | 국내 (HIRA DUR 원본 데이터) | 멀티 처방 통합 (최근 1년 전체 투약이력 조회) | 없음 (조회 서비스) | 본인 인증 필요, 가족 대리 제한 | 단순 조회·알레르기/부작용 등록 (알림·에이전트 기능 없음) | 무료 | https://www.hira.or.kr | 2026-04-11 |
| 8 | Medisafe | US/IL | 국제 (자체 약물 DB + Apple Health Records 100+ 병원 연동) | **멀티 처방 통합 DUR** (여러 약국에서 받은 약도 통합, 4단계 상호작용 등급 minor/moderate/major/severe) | 규칙 기반 상호작용 체커 + Medisafe Care LLM 기반 Q&A (tool-use 에이전트 공식 발표 없음) | **O** (Dependents, 무료 1명·Premium 무제한) + Medfriend 보호자 연동 | 경고(4단계) + 보호자 알림 + 의사 공유 리포트 | Freemium (Premium 유료) | https://www.medisafe.com | 2026-04-11 |
| 9 | MyTherapy | DE | 국제 (자체 DB + 사용자 입력) | 단일 앱 내 약물 목록 기준 상호작용 체크 (공식 기능) | 없음 (규칙 기반) | 제한적 (일기/추적) | 알림 + 증상/측정 기록 + 의사용 리포트 | 무료 (광고 없음) | https://www.mytherapyapp.com | 2026-04-11 |
| 10 | Amazon Pharmacy PillPack | US | 국제 (약국 처방 데이터) | **멀티 처방 통합** (약사 수동 전체 약물 리뷰) | 없음 (약사 인력 리뷰 + 자동화 패킹) | 보호자(Caregiver) 기능 O | 분류 포장 배송 + 약사 24/7 상담 | 무료 (처방약 별도) | https://pharmacy.amazon.com/pillpack | 2026-04-11 |
| 11 | Hello Heart | US | 국제 (심혈관 중심, 자체 DB) | 복약 추적 중심 (상호작용 체커는 심혈관 약물 한정 unclear) | Hello Meds AI 어시스턴트 + 약사 리뷰 (2025 출시) | unclear | 알림 + 스마트 필박스(IoT) + 약사 리뷰 + 의사 리포트 | B2B2C (고용주/보험사 스폰서) | https://www.helloheart.com | 2026-04-11 |
| 12 | CareZone | US | — | — (**2021 서비스 종료**, Walmart 인수 후 내부 흡수) | — | — | — | — | https://carezone.com | 2026-04-11 |

### 기본 리스트 중 공식 정보 부족으로 제외/메모

- **약올림**: 국내 앱스토어/공식 보도에서 해당 명칭의 복약관리 앱 확인 불가. 유사 발음 서비스는 다수 존재하나 동명 앱 특정 불가 → "unclear" 처리
- **Pharmacy AI**: 국내 앱스토어에 "약 추적기, 알림 및 약 보관함 - 약국 AI" 명의로 존재. 개발자 소규모·공식 사이트 부재, 기능 주장은 이미지 인식 + 알림. 멀티 처방 통합 DUR 공식 주장 없음
- **필팩(한국)**: 한국 약사법상 의약품 온라인 유통 불가. 미국 Amazon PillPack이 국내 진출 없음 → 국내 경쟁자 아님
- **하이닥(Hidoc)**: 건강 Q&A/의사 상담 포털. 복약관리 앱 기능 공식 확인 불가
- **Pill Reminder apps**: 일반명사. 대표격 Medisafe/MyTherapy로 커버됨

---

## 서비스별 상세 카드

### 1. 네이버 헬스케어 복약관리

- 공식 URL: 네이버앱 > 전체서비스 > 헬스케어 (보도자료: mdtoday, news1, ftoday 2024-2025)
- 2024-25 최근 기능:
  - 약 봉투 OCR 촬영 → 처방약/복용 일정 자동 등록
  - 날짜별 복약 내역·증상 기록
  - 복용률 집계, 오늘 복용 여부
  - 헬스케어 허브(만보기, 병원 예약, 증상 체크, 실손보험 청구 등)와 통합
- 차별점(그들 주장): "OCR + AI로 입력 편의성", "네이버 생태계 통합"
- 검증 결과:
  - **멀티 처방 통합 DUR 기능은 공식 언급 없음** — OCR은 "입력 편의" 용도
  - 상호작용 경고·경고 등급화 기능 확인 불가
  - 만성질환자 장기 복약 전용 에이전트형 흐름 아님 (포털 내 한 탭)
- 출처: ftoday.co.kr (2024 보도), mdtoday.co.kr, news1.kr

### 2. 닥터나우

- 공식 URL: https://doctornow.co.kr, 앱스토어/Google Play
- 2024-25 최근 기능:
  - 비대면진료 + 약국 연계가 메인
  - "AI 의료 포털" 리브랜딩, 증상 입력 시 AI가 의심 질환 안내
  - 복약 기록 시 포인트 100pt, 혈당/혈압/체중 기록 10pt (순응도 리워드형)
- 차별점(그들 주장): "대한민국 1위 비대면진료"
- 검증 결과:
  - 복약관리는 **비대면진료의 보조 기능**이며, 포인트 리워드 중심
  - 멀티 처방 통합 DUR/상호작용 체크 공식 기능 없음
  - AI는 증상→질환 매칭용(진료 유입), 복약 에이전트 아님
- 출처: 닥터나우 공식 사이트, namu.wiki(참고용), Play Store 공식 설명

### 3. 나만의닥터 (MyDoctor)

- 공식 URL: https://my-doctor.io
- 2024-25 최근 기능:
  - 비대면진료 + 복약 기록 + 포인트 적립
  - 만성질환(당뇨/고혈압/고지혈증) 타겟 홍보
- 검증 결과:
  - 복약 기능 = 사용자 직접 등록 → 체크 → 포인트
  - AI/DUR/멀티처방 통합 **공식 기능 없음**
- 출처: my-doctor.io, Play Store 공식 설명

### 4. 올라케어 (KB 올라케어)

- 공식 URL: https://www.kbollacare.com
- 2024-25 최근 기능:
  - "올라코디" AI 기반 맞춤형 헬스케어 (블루앤트 공식 표현)
  - 정기 복약 알림 + 재진 안내 멤버십
  - 비대면진료·약 배송
- 차별점(그들 주장): "AI 환자 맞춤형 헬스케어", "500만 이용자"(보도자료 수치)
- 검증 결과:
  - "올라코디"의 tool-use/에이전트 내부 구조는 공식 비공개 → unclear
  - 멀티 처방 통합 DUR 공식 기능 없음
  - KB금융 인수 후 앱테크/멤버십 성격 강화, 에이전트형 복약 안전성 담당 아님
- 출처: fnnews, 대한금융신문, Play Store

### 5. 굿닥 (Goodoc)

- 공식 URL: https://www.goodoc.co.kr
- 2024-25 최근 기능:
  - 병원 접수·예약, 비대면진료, 실시간 약국/병원 검색
  - 가족 추가 기능(병원 예약 대상자 관리)
- 검증 결과:
  - **복약관리는 공식 기능 리스트에 없음** — 병원 접근/진료 플랫폼
  - DUR, AI 복약, 에이전트 해당없음
- 출처: goodoc.co.kr, 앱스토어 공식 설명

### 6. 똑닥 (DdocDoc)

- 공식 URL: https://ddocdoc.com
- 2024-25 상태:
  - **복약관리 서비스·약국 서비스·문서 보관 서비스 중단**
  - 현재는 병원 예약/실시간 대기순서 중심
- 검증 결과: 경쟁 대상 아님 (pivot out)
- 출처: namu.wiki(서비스 중단 기록), 앱스토어 공식 설명(복약 기능 미표기)

### 7. 내가 먹는 약! 한눈에 (건강보험심사평가원)

- 공식 URL: https://www.hira.or.kr/rb/dur/form.do?pgmid=HIRAA050300000100
- 기능:
  - **DUR 데이터 기반 최근 1년 투약이력 조회** (전국 병원·약국 통합)
  - 알레르기·부작용 등록
  - 2024-25: 카카오톡·건강e음 앱·정부24 채널 확장, 매번 인증 생략 간소화
- 검증 결과:
  - **국내에서 유일하게 "멀티 처방·멀티 약국 통합 투약이력"을 공식 제공하는 국가 인프라**
  - 단, 이것은 **조회 서비스**이며 알림·에이전트·능동적 상호작용 경고(환자 대상)를 제공하지 않음
  - 필케어가 이 API/데이터 연동을 활용 못 하면 "국내 통합 이력 표면"만 약점으로 남음
- 출처: hira.or.kr 공식, gov.kr, khidi.or.kr 공지

**→ 전략 시사점: 필케어는 HIRA 투약이력 조회(공공데이터/마이데이터)를 인제스트 소스로 활용하면서, 그 위에 능동적 에이전트·경고·이중 처방 감지 계층을 쌓는 구도로 포지셔닝해야 함.**

### 8. Medisafe (US/IL) — ⚠️ 최대 위협

- 공식 URL: https://www.medisafe.com
- 2024-25 최근 기능:
  - **멀티 약국/멀티 처방 통합**: Apple Health Records로 미국 100+ 병원 시스템에서 자동 임포트
  - **Drug-to-drug interaction checker** 내장, 4단계 등급(minor/moderate/major/severe)
  - severe/major 발견 시 Updates 섹션 알림 + 의사 상담 권고
  - **Dependent profiles**: 무료 1명, Premium 무제한
  - **Medfriend**: 복용 미확인 시 보호자에게 자동 알림 (71% 순응도 개선 자체 발표)
  - Medisafe Care (B2B: 제약사 파트너십, 환자 지원 프로그램)
- 차별점(그들 주장): "#1 Pill Reminder", "멀티 복약·멀티 약국 지원", "가족/보호자 생태계"
- 검증 결과:
  - **멀티 처방 통합 DUR을 이미 공식적으로 제공 (확정)**
  - AI는 규칙 기반 상호작용 체커 + LLM Q&A 수준. **Tool-use / agentic orchestration 공식 발표는 확인 안 됨** (unclear, 그러나 B2B 환자 프로그램에 대화형 개입 있음)
  - 한국어/국내 약물 DB·HIRA 연동 없음, 한국 미출시(앱스토어 한국 계정 설치 가능하나 미국 DB 기준)
- 출처: medisafe.com 공식, medisafeapp.com (공식 자회사 블로그), Apple App Store

### 9. MyTherapy (독일, smartpatient GmbH)

- 공식 URL: https://www.mytherapyapp.com
- 2024-25 최근 기능:
  - 복약/증상/측정값 통합 트래커 (혈압·혈당·체중·기분·통증)
  - **약물 상호작용 체크**: 앱 내 등록 약물 목록 기준 (자체 DB)
  - 리필 알림, 의사용 PDF 리포트
  - 광고 없는 무료 모델 (제약사·연구 파트너십 수익)
- 검증 결과:
  - 상호작용 체커 존재하나 **"멀티 약국/처방 자동 통합 임포트"는 공식 언급 없음** (수동 입력 기반)
  - AI 에이전트/LLM 기반 대화형 개입 공식 기능 없음
  - 한국어 UI 지원은 제한적 (공식 지원 언어 중 한국어 포함 여부 unclear)
- 출처: mytherapyapp.com 공식, 앱스토어 공식 설명

### 10. Amazon Pharmacy PillPack

- 공식 URL: https://pharmacy.amazon.com/pillpack
- 2024-25 최근 기능:
  - **멀티 처방 통합 → 시간대별 분류 포장 배송** (2개 이상 복용자 타겟)
  - 약사가 **전체 약물 목록 상호작용 수동 리뷰**
  - 24/7 약사 상담
  - Medicare Part D 확장 (2024)
  - 보호자(Caregiver) 계정 기능
- 검증 결과:
  - **멀티 처방 통합 DUR은 "약사 인력 리뷰"로 제공** (소프트웨어 에이전트 아님)
  - 필케어와는 비즈니스 모델 자체가 다름 (물리 배송 + 약사 인력)
  - 한국 미진출 (약사법 제약)
- 출처: pharmacy.amazon.com, aboutamazon.com 공식 보도자료

### 11. Hello Heart

- 공식 URL: https://www.helloheart.com
- 2024-25 최근 기능:
  - 심혈관 질환(고혈압/콜레스테롤) 특화 디지털 치료제
  - **Hello Meds**: AI 어시스턴트 + 연결된 스마트 필박스 + 약사 리뷰 (2025 신규)
  - 알고리즘 기반 high-risk 환자 식별
  - B2B2C (고용주·건강보험 스폰서)
- 검증 결과:
  - **Hello Meds가 "AI assistant"를 명시적으로 마케팅** → 에이전트형 접근 요소 존재
  - 단, 범위는 심혈관 중심 단일 도메인, 다약제 통합 에이전트 아님
  - 한국 미진출, 국내 약물 DB 미연동
- 출처: helloheart.com 공식, 2025-04 Business Wire 보도자료(Connected Pill Box), fiercehealthcare 인터뷰

### 12. CareZone

- 공식 URL: https://carezone.com (현재 splash 페이지만)
- 상태:
  - **2021년 서비스 종료**
  - 2020년 Walmart가 $200M에 기술·IP 인수, 내부 Walmart Pharmacy 기술로 흡수
- 검증 결과: 경쟁 대상 아님 (역사적 참고)
- 출처: fiercehealthcare.com (Walmart 인수), techenhancedlife.com

---

## 추가 발굴 후보 (위 기본 리스트 외)

### 국내

| 서비스 | 유형 | 위협도 | 메모 |
|---|---|---|---|
| **내가 먹는 약! 한눈에 (HIRA)** | 정부 공공 서비스 | **HIGH** | 국내 유일 멀티 약국 통합 투약이력. 조회만 가능 → 파트너 or 데이터 소스로 활용 필요 |
| 아이약 (i-Yak) | 개인 개발 앱 | LOW | 알림·혈당·약사 상담. 소규모, AI/DUR 없음 |
| 약먹자 (Yak Meokja) | 개인 개발 앱 | LOW | 건강기록 + 복약 알림. AI/상호작용 없음 |
| 파프리카 케어 | 복약지도 앱 | LOW | 복약 지도문 중심, 에이전트 아님 |
| 먼약 (AI 의약품 검색) | 의약품 식별 | LOW | 이미지 식별 검색 중심, 복약관리/DUR 아님 |
| AI Pharm (올댓페이) | 약국 POS B2B | MED | 약국용 POS + AI 상담/복약지도. 환자앱 아님. 향후 B2C 확장 가능 |
| 삼천당제약 할머니 복약 안내 (2026 시범) | 제약사 맞춤 안내 | MED | "환자별 상태·복약이력 기반 AI 상담" 공표. 세부 기능 공개 전 |

### 해외

| 서비스 | 유형 | 위협도 | 메모 |
|---|---|---|---|
| **NoHarm** (브라질 Noharm.ai) | 병원용 임상 AI | MED | LLM이 처방 실시간 분석 → 상호작용/중복/용량 오류 경고. 병원 B2B이지만 **agentic + DUR + LLM 조합의 레퍼런스**. npj Digital Medicine 2025 리뷰에 사례로 수록 |
| Hello Meds (Hello Heart 내) | 소비자앱 + IoT | MED | 위 11번 참조 |
| Generative AI 임상 의사결정 지원 연구물 다수 | 학술/연구 | LOW | 2025년 npj·Frontiers·Nature 리뷰에서 drug-drug interaction + LLM 사례 급증. 제품화된 B2C는 아직 드뭄 |

---

## ⚠️ 차별점 위협 분석

### (1) 멀티 처방·멀티 약국 통합 DUR을 이미 하는 곳?

**Yes — 3곳 확인**

1. **Medisafe** (해외): Apple Health Records로 다수 병원·약국 데이터 자동 임포트 + 4단계 상호작용 경고를 **소비자 앱 레벨에서 이미 제공**. 국내 진출 없음·한국 DB 없음
2. **HIRA "내가 먹는 약! 한눈에"** (국내 공공): 전국 병원·약국 통합 투약이력을 **국가 DUR 원본 데이터로 조회 제공**. 그러나 "조회" 서비스이며 능동적 경고·에이전트 없음
3. **Amazon PillPack** (해외): 약사 인력이 수동 리뷰. 국내 진출 없음

**국내 민간 앱/에이전트 중에서는 멀티 처방 통합 DUR을 공식 기능으로 내세우는 경쟁자 없음.** → 필케어의 국내 차별점은 유지 가능하되, 주장 표현은 "국내 민간 서비스 중 최초" 또는 "HIRA 통합이력 + 능동적 에이전트 + 국제 DB 보완" 식으로 정교화 필요.

### (2) Agentic / tool-use AI 복약 관리를 이미 하는 곳?

**No (완전한 agentic 복약 에이전트) / Partial (요소별로 있음)**

- Medisafe, 올라케어(올라코디), Hello Heart(Hello Meds), 닥터나우(AI 의료 포털) 등이 **"AI"를 마케팅**하나, 공식 발표상 구조는:
  - 규칙 기반 상호작용 체커 (Medisafe)
  - 단일 LLM Q&A 챗봇 (Hello Meds, 올라코디 추정)
  - 증상→질환 매칭 분류기 (닥터나우)
- **공식 자료상 "tool-use / function calling / multi-step planning / 이력 통합 기반 능동적 개입"을 수행하는 복약 전용 에이전트는 확인되지 않음**
- 유일한 인접 사례: **NoHarm (브라질)** — 병원 처방 분석에 LLM 에이전트 사용, B2B, 환자앱 아님
- 학술 리뷰(npj 2025, Frontiers 2025)도 "제품화 단계 이전"이라 평가

**→ 필케어의 "agentic AI 복약 에이전트" 포지션은 2026-04 시점 국내 최초 주장 가능. 단 주장 표현은 "소비자용 agentic 복약 에이전트로는 국내 최초" 수준으로 한정.**

### (3) 국제 + 국내 약물 DB 통합을 이미 하는 곳?

**No**

- **Medisafe**: 국제 DB만, 한국 KD(식약처)·HIRA DB 미연동
- **MyTherapy**: 자체 국제 DB, 국내 DB 없음
- **국내 앱 (네이버/닥터나우/올라케어/마이닥터 등)**: 국내 데이터 중심, 국제 약물/브랜드/여행자 복용약·해외 구매약 커버 없음
- **HIRA**: 국내 국가 DB 전용

**→ 국제 + 국내 DB 동시 통합은 실제로 미충족 영역. 필케어가 식약처 공공데이터 + HIRA 투약이력 + RxNorm/DrugBank(또는 그에 상응) 연동을 구현하면 확실한 차별점.**

---

## 피벗 필요 여부: **No (단, 주장 표현 조정 필수)**

### 유지할 차별점
1. **소비자용 agentic/tool-use 복약 에이전트 (국내 최초 주장 가능)**
2. **국제 + 국내 약물 DB 통합 + HIRA 투약이력 활용**
3. **만성질환·다약제 복용자 전용 UX (비대면진료 부가기능이 아닌 주력)**
4. **능동적 이중 처방 탐지 및 의사 브리지 시나리오**

### 표현에서 주의할 점 (제안서 1.7 방어력)
- "국내 최초 멀티 처방 통합 DUR" → ❌ HIRA가 국가 서비스로 먼저 존재. **"국내 최초 소비자 대상 능동적 멀티 처방 통합 DUR 에이전트"**로 수정
- "AI 복약 관리 최초" → ❌ 다수 경쟁자 마케팅 중. **"국내 최초 tool-use 기반 agentic 복약 관리"**로 수정
- "멀티 프로필 최초" → ❌ Medisafe Dependents/Medfriend가 선례. **"국내 앱 중 피부양자 대상 에이전트형 복약관리"**로 수정
- Medisafe 비교 열에서 "멀티 처방 통합 DUR = O"로 반드시 기재하고, 필케어의 추가 가치(한국어·국내 DB·에이전트·의사 브리지)를 행 단위로 분리

### 심사위원 5분 반증 방어 체크리스트
- [ ] Medisafe의 drug interaction checker 기능 존재 — 인정 후 차별화 표현
- [ ] HIRA "내가 먹는 약! 한눈에" 존재 — 인정 후 데이터 소스로 포지셔닝
- [ ] 네이버 복약관리 OCR 존재 — 인정 후 "OCR만으로는 에이전트 아님" 차별화
- [ ] 닥터나우/올라케어의 "AI" 문구 — 인정 후 구조(규칙/단일 Q&A vs tool-use) 차이 명시

---

## 참고 URL 로그

### 국내
- 네이버 헬스케어 복약관리: https://www.ftoday.co.kr/news/articleView.html?idxno=350718, https://www.mdtoday.co.kr/news/view/1065580734524762, https://www.news1.kr/it-science/general-it/5975791
- 닥터나우: https://doctornow.co.kr/, https://apps.apple.com/kr/app/id1513718380
- 나만의닥터: https://my-doctor.io/, https://play.google.com/store/apps/details?id=com.merakiplace.mydoctor
- 올라케어: https://www.kbollacare.com/, https://www.fnnews.com/news/202107301642097559
- 굿닥: https://www.goodoc.co.kr/, https://apps.apple.com/kr/app/id517637141
- 똑닥 (복약 서비스 종료): https://ddocdoc.com/, https://apps.apple.com/kr/app/id1014889755
- HIRA "내가 먹는 약! 한눈에": https://www.hira.or.kr/rb/dur/form.do?pgmid=HIRAA050300000100, https://www.gov.kr/portal/service/serviceInfo/PTR000051824
- Pharmacy AI (국내 개인 개발 앱): https://apps.apple.com/kr/app/id6738890447
- AI Pharm (B2B POS): https://m.dailypharm.com/user/news/143

### 해외
- Medisafe: https://www.medisafe.com/, https://www.medisafe.com/medisafe-launches-feature-to-alert-users-of-potentially-harmful-drug-interactions/, https://www.medisafe.com/caregiver-support/, https://medisafeapp.com/features/, https://apps.apple.com/us/app/medisafe-medication-management/id573916946
- MyTherapy: https://www.mytherapyapp.com/, https://apps.apple.com/us/app/mytherapy-medication-reminder/id662170995
- Amazon Pharmacy PillPack: https://pharmacy.amazon.com/pillpack, https://www.aboutamazon.com/news/retail/amazon-pharmacy-caregiver-medicare-pillpack, https://www.aboutamazon.com/news/retail/amazon-pharmacy-pillpack-feature
- Hello Heart: https://www.helloheart.com/, https://www.helloheart.com/press/hello-heart-unveils-connected-pill-box-to-improve-medication-adherence-employers-health-plans, https://www.helloheart.com/press/hello-heart-my-meds-virtual-pillbox, https://www.fiercehealthcare.com/health-tech/hello-heart-adds-medication-management-tools
- CareZone (종료): https://carezone.com/, https://www.fiercehealthcare.com/tech/walmart-buys-medication-management-technology-from-startup-carezone

### 학술/레퍼런스
- Agentic AI in Healthcare (PMC): https://pmc.ncbi.nlm.nih.gov/articles/PMC12890637/
- LLM agentic systems in medicine (Nature Machine Intelligence): https://www.nature.com/articles/s42256-024-00944-1
- GenAI & LLM in medication harm mitigation (npj Digital Medicine 2025): https://www.nature.com/articles/s41746-025-01565-7
- AI for medication adherence (Frontiers 2025): https://www.frontiersin.org/journals/digital-health/articles/10.3389/fdgth.2025.1523070/full
- LLM as CDSS for medication safety (PMC): https://pmc.ncbi.nlm.nih.gov/articles/PMC12629785/
