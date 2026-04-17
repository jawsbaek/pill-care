# PDF 조판 노트

## 현재 상태 (2026-04-17)

- **빌드**: HTML 성공 / PDF 스킵 (xelatex 미설치 환경)
- **페이지 수**: 미측정 (PDF 미생성). HTML 기준 본문 ~9.2KB (153 markdown lines).
- **사용 폰트**: Pretendard (1차), NanumGothic (fallback)
- **HTML 아티팩트**: `docs/proposal/2026-demo-submission/proposal-5p.html`
- **PDF 아티팩트**: 미생성 (빌드 머신에 `brew install basictex` 후 재실행 필요)

> HTML을 브라우저 "인쇄 → PDF 저장"으로 변환해도 임시 제출본 1차 리뷰는 가능.
> 최종 제출용 PDF는 xelatex 빌드로 생성 권장 (폰트 embedding 보장).

## xelatex 환경 설치 (macOS)

```bash
brew install pandoc basictex
sudo tlmgr update --self
sudo tlmgr install xecjk koreanfonts collection-xetex
# Pretendard 폰트 (한국 제안서 표준)
brew tap homebrew/cask-fonts
brew install --cask font-pretendard
# (대안) NanumGothic
brew install --cask font-nanum-gothic
```

그 후 `bash scripts/build_proposal_pdf.sh` 재실행.

## 5페이지 초과 시 튜닝 순서

1. **margin 축소**: 1.5cm → 1.2cm → 1.0cm (빌드 스크립트 `-V geometry:margin=...`)
2. **fontsize 축소**: 9pt → 8.5pt → 8pt (8pt 이하 시 가독성 저하 주의)
3. **줄 간격 축소**: `-V linestretch=0.95` 추가 (기본 1.0)
4. **본문 압축**:
   - §2.1 기술 목적: 3단락 → 2단락 (배경 통계 bullet 변환)
   - §2.7 도전 ①-⑥ 각 문장 10% 축약
   - §1.6 비교표: "카카오 케어챗/닥터나우 AI" 행과 "네이버·약올림·올라케어" 행을 1행으로 병합
5. **테이블 압축**: §2.4 결과물 형상 · §3.3 스택을 세미콜론 구분 inline list로 변환
6. **헤더 레벨 축소**: `###` 헤더를 **bold 문장**으로 변환 (공백 절약)

## 5페이지 내 통과 시 품질 체크

- 페이지 내 여백 균형 확인 (P1-P5 각 페이지 80% 이상 채워져야 균형감).
- 표·다이어그램 잘림(페이지 경계 걸침) 없는지 확인 — 필요 시 `\pagebreak` 삽입.
- 표지(옵션): 대회 규정에 따라 별도 표지 필요 시 추가 페이지 사용 (본문 5p 제약 제외).
- Figma PNG (§1.6 비교표·§2.2 아키텍처 다이어그램·§3.2 Gantt)는 B5에서 300dpi로 삽입.

## 빌드 실패 시 체크리스트

- `! LaTeX Error: File 'xecjk.sty' not found.` → `sudo tlmgr install xecjk`
- `! Package fontspec Error: The font "Pretendard" cannot be found.` → Pretendard 시스템 폰트 설치 누락. `brew install --cask font-pretendard` 또는 NanumGothic fallback 경로 자동 사용됨.
- `! Missing character` 경고 → 한자/이모지 fallback 폰트 미지정. `-V mainfontfallback="Apple SD Gothic Neo"` 옵션 추가.
