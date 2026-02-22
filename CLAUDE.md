# WiFi Driver Demo Project - CLAUDE.md

이 파일은 Claude Code 세션 시작 시 자동으로 읽힙니다.
프로젝트의 핵심 context를 제공합니다.

## 프로젝트 목적
Claude Code의 **Agent**와 **Skill** 동작 원리를 설명하기 위한 데모.
실제 WiFi 드라이버 코드 패턴을 사용하여 실용성도 함께 보여줍니다.

## 프로젝트 구조
```
wifi-driver-demo/
├── .claude/
│   ├── agents/           ← Sub-agents (system prompts)
│   │   ├── planner.md         - 작업 계획 및 조율
│   │   ├── code-reviewer.md   - 코드 품질 검토
│   │   └── dependency-analyzer.md - 의존성 분석
│   ├── skills/           ← Skills (on-demand instruction injection)
│   │   ├── circular-deps/     - 순환 의존성 탐지
│   │   ├── god-module-check/  - 갓 모듈 점수 계산
│   │   └── kernel-review/     - 커널 코딩 표준 검사
│   ├── hooks/            ← Hooks (deterministic code)
│   └── settings.json         - 권한 및 hook 설정
│
├── src/
│   ├── core/wifi_core.c  ← 🚨 God Module 예시 (10개 책임, 순환 의존)
│   ├── mac/mac_core.c    ← 🔴 순환 의존성 참여
│   ├── cfg80211/cfg_ops.c ← 🔴 순환 의존성 참여
│   └── security/wpa_handler.c ← ✅ 정상 모듈 (leaf node)
└── include/wifi_types.h  ← 공용 타입 정의
```

## 의도적으로 심어둔 문제들
1. **God Module**: `wifi_core.c` — 10개 책임, ~300 라인
2. **순환 의존성**:
   - `wifi_core ↔ mac_core` (직접 순환)
   - `mac_core → cfg80211 → mac_core` (간접 순환)
3. **Cross-layer coupling**: core가 mac/cfg/security를 직접 호출

## 팀 목표
- God Module Score: 1.5 → 4.0+
- Module Circular Dependencies: 3개 사이클 → 0개
- Architecture Maturity Level: 1 → 4

## 사용 가능한 Skills
- `/circular-deps` : 순환 의존성 분석
- `/god-module-check` : 갓 모듈 점수 계산
- `/kernel-review` : 커널 코딩 표준 검사

## 코드 분석 시 주의사항
- 모든 분석은 Read-only (파일 수정 금지)
- 실제 빌드 환경 없음 (Linux 커널 헤더 없음) - 정적 분석만
