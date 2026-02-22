---
name: kernel-review
description: >
  Check Linux kernel coding standards for WiFi driver code.
  Verifies coding style, memory allocation patterns, locking conventions,
  and sk_buff lifecycle correctness.
  AUTO-LOAD when user mentions: kernel style, coding standard, checkpatch,
  sk_buff ownership, RCU pattern, spinlock usage, GFP flags, 커널 코딩 스타일
invocation: auto
allowed-tools: Bash, Read, Grep
---

# Linux Kernel Coding Standard Review Skill

## Supporting Files
이 Skill 디렉토리에 포함된 파일:
- `scripts/kernel_check.py` — 정적 분석 스크립트 (sk_buff/GFP/NULL체크/workqueue)
- `references/coding_patterns.md` — WiFi 드라이버 올바른 코딩 패턴 가이드

## 분석 절차

### Step 1: 정적 분석 스크립트 실행
스크립트 코드 자체는 context window에 들어가지 않고 **결과(stdout)만** 주입됩니다.
```bash
python3 .claude/skills/kernel-review/scripts/kernel_check.py <파일경로>
```

exit code 의미:
- `0`: 이슈 없음
- `1`: MEDIUM/HIGH 이슈 있음
- `2`: CRITICAL 이슈 있음 (즉시 조치 필요)

### Step 2: 패턴 레퍼런스 참조
이슈 발견 시 올바른 패턴을 레퍼런스에서 확인:
```bash
cat .claude/skills/kernel-review/references/coding_patterns.md
```

### Step 3: 수동 보완 검사
스크립트가 탐지하지 못하는 패턴을 직접 grep으로 확인:
```bash
# RCU 패턴 확인
grep -n "rcu\|list_add_rcu\|rcu_read_lock" <파일>

# 에러 경로 확인
grep -n "goto err" <파일>
```

### Step 4: 수정 코드 제안
각 이슈에 대해 `references/coding_patterns.md`의 올바른 패턴을 참고하여
구체적인 수정 코드를 제시합니다.

## 출력 형식 요구사항
- 스크립트 결과 먼저 출력
- CRITICAL 이슈는 즉시 수정 코드 제안
- 레퍼런스 문서의 올바른 패턴 예시 인용
