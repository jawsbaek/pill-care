# HIRA DUR v2026 — synthetic unit-test fixtures

These 8 CSV files are **synthetic placeholders** used by unit tests to exercise
the DUR ETL/normalizer/checker for all 8 HIRA DUR rule types. They are **not**
real HIRA data.

Real HIRA DUR CSVs require 공공데이터포털 인증키 and are fetched separately by
the team into a gitignored directory (e.g. `data/hira-dur-v2026/`). The
production `build_full_db` loader scans that directory and loads whichever
files are present.

## Column-name assumption

The exact HIRA column names for the 7 new rule types (age / pregnancy / dose /
duplicate / elderly / specific_age / pregnant_woman) were **not verified**
against the live 공공데이터포털 API schema at the time these fixtures were
written (internet access was not used for this subtask). The normalize
functions in `src/pillcare/dur_normalizer.py` use the column names shown in
each CSV below as a reasonable Korean-language guess following the pattern of
the existing 병용금기 CSV.

**When real HIRA CSVs are available**, verify each file's header row against
the corresponding `normalize_<rule>` function and adjust the column-name
literals in `dur_normalizer.py` (and these fixtures) to match. The table
schemas in `db_builder.py` are abstract (ingredient_code / ingredient_name /
reason / numeric bounds) and should not need to change.

## Files

| File                            | Rule type         | HIRA Korean name |
|---------------------------------|-------------------|------------------|
| combined_prohibition.csv        | combined          | 병용금기         |
| age_prohibition.csv             | age               | 연령금기         |
| pregnancy_prohibition.csv       | pregnancy         | 임부금기         |
| dose_warning.csv                | dose              | 용량주의         |
| duplicate_therapy.csv           | duplicate         | 효능군중복       |
| elderly_warning.csv             | elderly           | 노인주의         |
| specific_age.csv                | specific_age      | 특정연령         |
| pregnant_woman.csv              | pregnant_woman    | 임산부주의       |

All files are UTF-8 (with BOM tolerated by the normalizer). Real HIRA files
are typically CP949 — the normalizers accept an `encoding` argument.
