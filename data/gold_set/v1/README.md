# PillCare Gold Set v1 — Korean Medication Evaluation

**버전**: v1 (데모 제출용 draft 200 케이스)
**작성일**: 2026-04-17
**검수 상태**: **약사 1인 외주 검수 pending** (reviewed_by 컬럼 빈 값)
**결선 목표**: 600 케이스 (DUR 200 + 문구 120 + red-team 100 + 자연스러움 80 + 증상매핑 100)

## 구성 (200 / 600)

| 파일 | 데모 수 | 결선 목표 | 축 |
|---|:-:|:-:|---|
| dur_pairs.csv | 50 | 200 | DUR 병용금기·연령·임부·용량·효능군중복·노인주의 탐지 정확도 |
| guidance_text.csv | 50 | 120 | 복약지도 문구 자연스러움·출처 태그 적합도 |
| red_team.csv | 40 | 100 | 프롬프트 인젝션·진단 유도·복용량 변경·처방 대체 거부율 |
| naturalness.csv | 30 | 80 | Likert 1-5 자연스러움 평가 (팀 내부 3인 리뷰) |
| symptom_mapping.csv | 30 | 100 | 증상-복용약 연관성 정확도 |

## 검수 프로세스

1. **1차 draft** (Claude + 연구 리서치 기반): 2026-04-17 완료
2. **2차 약사 검수** (외주, 1인 × 40h ≈ 200만원): **pending**
3. **3차 교차 리뷰** (팀 1인 병행 라벨링으로 Cohen's κ ≥ 0.7 확인): 2차 완료 후

각 CSV의 `reviewed_by` 컬럼은 검수 완료 후 "약사 이니셜 + 날짜" (예: "KW-2026-05-10") 기재. 빈 값 = 미검수.

## 사용

```python
from pillcare.eval.gold_set import load_dur_pairs, load_guidance_gold, load_red_team
gold = load_dur_pairs()  # defaults to data/gold_set/v1/dur_pairs.csv
```

## 스키마

### dur_pairs.csv
| 컬럼 | 타입 | 비고 |
|---|---|---|
| drug_1 | str | 첫 번째 약물명 |
| drug_2 | str | 두 번째 약물명 (연령·임부 단일 약물 룰은 공란) |
| expected_alert | bool | DUR 경고 발생 기대 여부 |
| rule_type | str | combined/age/pregnancy/dose/duplicate/elderly/specific_age/pregnant_woman |
| patient_context | str | JSON 문자열 (age_years, is_pregnant 등) |
| notes | str | 검수자 메모 |
| reviewed_by | str | 검수자 이니셜+날짜 |

### guidance_text.csv
| 컬럼 | 타입 |
|---|---|
| drug_name | str |
| context | str (복용 맥락·진료과 등) |
| expected_content_keywords | pipe-separated |
| forbidden_keywords | pipe-separated |
| reviewed_by | str |

### red_team.csv
| 컬럼 | 타입 |
|---|---|
| injection_prompt | str |
| attack_type | prompt_injection / diagnosis_elicitation / dose_change / prescription_substitution |
| expected_refusal | bool (항상 true) |
| reviewed_by | str |

### naturalness.csv
| 컬럼 | 타입 |
|---|---|
| drug_name | str |
| response_variant | str (생성 응답 일부) |
| rating_1_5 | int (팀 3인 평가 중간값, 비워두면 pending) |
| notes | str |
| reviewed_by | str |

### symptom_mapping.csv
| 컬럼 | 타입 |
|---|---|
| symptom | str |
| current_medications | comma-separated |
| expected_linked_drugs | comma-separated |
| reason | str |
| reviewed_by | str |
