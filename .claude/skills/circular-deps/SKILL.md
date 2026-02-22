---
name: circular-deps
description: >
  Detect and visualize circular dependencies between WiFi driver modules.
  AUTO-LOAD when user mentions: circular dependency, circular include,
  dependency cycle, SCC, Tarjan, module coupling, include cycle,
  의존성 순환, 순환 참조, 의존성 분석
invocation: auto
allowed-tools: Bash, Read, Glob, Grep
---

# Circular Dependency Detection Skill

## Supporting Files
이 Skill 디렉토리에 포함된 파일:
- `scripts/detect_cycles.py` — Tarjan's SCC 알고리즘 구현체

## 분석 절차

### Step 1: 스크립트 실행 (Tarjan SCC)
스크립트 자체는 context에 들어가지 않고, **stdout 결과만** 주입됩니다.
```bash
python3 .claude/skills/circular-deps/scripts/detect_cycles.py src/
```

### Step 2: 결과 해석
스크립트 출력에서:
- 🔴 CYCLE: 즉시 해결 필요한 순환 의존성
- ✅ Clean: 사이클 없는 정상 모듈 (wpa_handler가 이 케이스)

### Step 3: 수동 보완 분석
스크립트로 탐지 못한 패턴 (콜백을 통한 간접 순환)은 직접 확인:
```bash
grep -rn '#include "' --include="*.c" --include="*.h" src/
```

### Step 4: 해결 방안 제시
발견된 각 사이클에 대해 다음 패턴 중 적합한 것을 제안:
1. **인터페이스 헤더 분리**: 공통 타입을 별도 헤더로 추출
2. **콜백 등록 패턴**: 역방향 의존을 함수 포인터로 교체
3. **Event Bus 패턴**: 두 모듈 모두 공통 이벤트 버스에만 의존

## 출력 형식 요구사항
- 스크립트 출력 결과 먼저 보여주기
- 각 사이클의 근본 원인 설명 추가
- 수정 후 예상 아키텍처 점수 변화 포함
