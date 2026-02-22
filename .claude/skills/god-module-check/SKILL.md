---
name: god-module-check
description: >
  Calculate God Module score (1.0–5.0) for WiFi driver source files.
  Evaluates lines of code, number of responsibilities, and coupling level.
  AUTO-LOAD when user mentions: God Module, architecture score, SAM score,
  module complexity, architecture maturity, 갓 모듈, 아키텍처 점수,
  모듈 복잡도, software architecture maturity
invocation: auto
allowed-tools: Bash, Read, Grep
---

# God Module Score Calculator Skill

## Supporting Files
이 Skill 디렉토리에 포함된 파일:
- `scripts/god_module_score.py` — 점수 계산 스크립트 (LOC/책임/커플링 측정)
- `references/scoring_guide.md` — 팀 기준표 및 등급 정의

## 분석 절차

### Step 1: 점수 계산 스크립트 실행
스크립트 코드는 context에 들어가지 않고 **실행 결과(stdout)만** 주입됩니다.
```bash
python3 .claude/skills/god-module-check/scripts/god_module_score.py <파일경로>
```

예시:
```bash
python3 .claude/skills/god-module-check/scripts/god_module_score.py src/core/wifi_core.c
```

### Step 2: 팀 기준표 참조
결과 해석 시 팀 기준이 필요하면 레퍼런스 문서를 읽습니다:
```bash
cat .claude/skills/god-module-check/references/scoring_guide.md
```

### Step 3: 분리 계획 제안
점수가 2.5 미만이면 구체적인 파일 분리 계획을 scoring_guide.md의
"WiFi Driver 모듈 분리 권고안"을 참고해서 제시합니다.

## 출력 형식 요구사항
- 스크립트 결과를 먼저 보여준 뒤 해설 추가
- 현재 1.5 → 목표 4.0+ 에 대한 gap 분석 포함
- 분리 후 각 파일의 예상 점수도 제시
