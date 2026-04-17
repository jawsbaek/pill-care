# PillCare 데모 제출 (2026)

## 파일

| 파일 | 내용 | 상태 |
|---|---|---|
| `proposal-5p-draft.md` | 결합 초안 (P1-P5) | 팀 리뷰 대기 |
| `section-1-overview.md` | §1 기술 개요 | 초안 완료 |
| `section-2-technical.md` | §2 기술 상세 | 초안 완료 |
| `section-3-implementation.md` | §3 구현 방법 | 초안 완료 |
| `linguistic-policy-check.md` | 금지어 감사 | 통과 (0건) |
| `typesetting-notes.md` | PDF 조판 튜닝 가이드 | 참조 |
| `proposal-5p.html` | pandoc HTML 빌드 (팀 원격 리뷰용) | 자동 생성 |
| `proposal-5p.pdf` | pandoc xelatex PDF (최종 제출본) | 빌드 머신 필요 |

## 빌드

```bash
bash scripts/build_proposal_pdf.sh
# → proposal-5p.pdf (xelatex 필요, 없으면 자동 skip)
# → proposal-5p.html (fallback, 항상 생성)
```

## 빌드 환경 설치 (macOS)

```bash
brew install pandoc basictex
sudo tlmgr update --self
sudo tlmgr install xecjk koreanfonts collection-xetex
# Pretendard 폰트 (한국 제안서 표준) — 시스템에 별도 설치
brew tap homebrew/cask-fonts
brew install --cask font-pretendard
```

HTML만 필요한 팀 원격 리뷰 환경은 `pandoc`만 설치하면 됨.

## 남은 사람 작업

- **B5 (디자이너)**: §1.6 비교표 · §2.2 아키텍처 다이어그램 · §3.2 Gantt → Figma → PNG 300dpi → `assets/` 폴더에 배치 후 markdown에 `![](./assets/...png)` 삽입.
- **B6 (영상 PM)**: 3분 영상 (스토리보드 → POC 녹화 → 모션그래픽 → 나레이션 → 편집).
- **B7 (본 태스크)**: PDF 최종 조판 + 페이지 수 확인 + 대회 포털 제출. 현재 상태 — HTML 빌드 자동화 완료, PDF는 xelatex 설치된 머신에서 `bash scripts/build_proposal_pdf.sh` 실행.

## Gold Set

- `data/gold_set/v1/` — 200 케이스 draft (약사 검수 pending, A8 완료)
- 결선 목표 600 케이스
