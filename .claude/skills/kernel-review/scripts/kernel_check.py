#!/usr/bin/env python3
"""
kernel_check.py - Linux 커널 코딩 표준 정적 분석기
────────────────────────────────────────────────────
SKILL.md에서 이 스크립트를 실행 → stdout만 context에 inject

사용법:
  python3 kernel_check.py <file.c>
  python3 kernel_check.py src/core/wifi_core.c
"""

import sys
import os
import re
from dataclasses import dataclass, field


@dataclass
class Issue:
    line:     int
    pattern:  str
    severity: str   # CRITICAL / HIGH / MEDIUM / LOW
    message:  str
    suggest:  str


@dataclass
class CheckResult:
    name:   str
    passed: bool
    issues: list = field(default_factory=list)


# ─────────────────────────────────────────
# 체크 함수들
# ─────────────────────────────────────────

def check_skb_ownership(lines):
    """sk_buff 소유권 위반 탐지"""
    issues = []
    transfer_funcs = {'netif_rx', 'dev_kfree_skb', 'kfree_skb',
                      'mac_tx_submit', 'consume_skb'}
    skb_vars = set()

    for i, line in enumerate(lines, 1):
        # 소유권 이전 후 접근 패턴 (단순 휴리스틱)
        for fn in transfer_funcs:
            if fn + '(' in line:
                # 이전 라인에서 skb 변수 추출
                m = re.search(r'(\w*skb\w*)', line)
                if m:
                    skb_vars.add((m.group(1), i))

        # 소유권 이전 후 같은 skb 변수 접근 (5라인 내)
        for var, transfer_line in list(skb_vars):
            if i > transfer_line and i <= transfer_line + 5:
                if re.search(rf'\b{var}\b', line) and fn + '(' not in line:
                    # 이전 문장이 소유권 이전이었다면 잠재적 UAF
                    if '->' in line or '.' in line:
                        issues.append(Issue(
                            line=i,
                            pattern=f"post-transfer access: {var}",
                            severity="CRITICAL",
                            message=f"Potential use-after-free: '{var}' accessed after ownership transfer at line {transfer_line}",
                            suggest=f"Save needed fields before transfer: `u32 len = {var}->len;`"
                        ))

    return CheckResult(
        name="sk_buff Ownership",
        passed=len(issues) == 0,
        issues=issues
    )


def check_null_after_alloc(lines):
    """메모리 할당 후 NULL 체크 누락 탐지"""
    issues = []
    alloc_funcs = {'kmalloc', 'kzalloc', 'vmalloc', 'kstrdup',
                   'kcalloc', 'kmalloc_array'}
    # 할당된 변수: {varname: line_number}
    allocated = {}

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # 할당 패턴: `ptr = kzalloc(...)`
        for fn in alloc_funcs:
            m = re.match(rf'\s*(\w+)\s*=\s*{fn}\s*\(', line)
            if m:
                var = m.group(1)
                allocated[var] = i
                continue

        # 다음 1-2라인에서 if (!var) 또는 if (var == NULL) 체크
        for var, alloc_line in list(allocated.items()):
            if i == alloc_line + 1 or i == alloc_line + 2:
                if re.search(rf'if\s*\(\s*!{var}|if\s*\({var}\s*==\s*NULL', line):
                    allocated.pop(var, None)  # 체크됨
                    break

        # 5라인 이내에 체크 없이 사용
        for var, alloc_line in list(allocated.items()):
            if i == alloc_line + 3:
                # 체크 없이 3라인 지남 → 경고
                issues.append(Issue(
                    line=alloc_line,
                    pattern=f"no NULL check after {var} allocation",
                    severity="HIGH",
                    message=f"Missing NULL check after allocation of '{var}' (line {alloc_line})",
                    suggest=f"Add: `if (!{var}) return -ENOMEM;`"
                ))
                allocated.pop(var, None)

    return CheckResult(
        name="NULL Check After Alloc",
        passed=len(issues) == 0,
        issues=issues
    )


def check_gfp_flags(lines):
    """GFP 플래그 적절성 검사"""
    issues = []
    atomic_contexts = {'spin_lock', 'spin_lock_irq', 'spin_lock_irqsave',
                       'local_irq_disable', 'preempt_disable'}
    in_atomic = False
    atomic_line = 0

    for i, line in enumerate(lines, 1):
        # 아토믹 컨텍스트 진입 감지
        for ctx in atomic_contexts:
            if ctx + '(' in line:
                in_atomic = True
                atomic_line = i

        # 아토믹 컨텍스트 해제
        if any(x in line for x in ('spin_unlock', 'local_irq_enable', 'preempt_enable')):
            in_atomic = False

        # GFP_KERNEL을 아토믹 컨텍스트에서 사용
        if in_atomic and 'GFP_KERNEL' in line and 'kmalloc' in line or \
           in_atomic and 'GFP_KERNEL' in line and 'kzalloc' in line:
            issues.append(Issue(
                line=i,
                pattern="GFP_KERNEL in atomic context",
                severity="CRITICAL",
                message=f"GFP_KERNEL used inside atomic context (spinlock held since line {atomic_line})",
                suggest="Use GFP_ATOMIC in atomic/interrupt context"
            ))

    return CheckResult(
        name="GFP Flags",
        passed=len(issues) == 0,
        issues=issues
    )


def check_module_metadata(lines, filepath):
    """MODULE_LICENSE 등 필수 메타데이터 확인"""
    issues = []
    content = '\n'.join(lines)

    # .c 파일에서만 체크
    if not filepath.endswith('.c'):
        return CheckResult(name="Module Metadata", passed=True)

    # 주 드라이버 파일인지 판단 (module_init 또는 MODULE_LICENSE 있으면)
    if 'module_init' not in content and 'MODULE_LICENSE' not in content:
        return CheckResult(name="Module Metadata", passed=True)  # 보조 파일

    required = {
        'MODULE_LICENSE': 'Required for kernel module',
        'MODULE_AUTHOR':  'Identifies maintainer',
        'MODULE_DESCRIPTION': 'Describes module purpose',
    }
    for macro, reason in required.items():
        if macro not in content:
            issues.append(Issue(
                line=1,
                pattern=f"missing {macro}",
                severity="MEDIUM",
                message=f"{macro} not found — {reason}",
                suggest=f'Add: {macro}("...");'
            ))

    return CheckResult(
        name="Module Metadata",
        passed=len(issues) == 0,
        issues=issues
    )


def check_workqueue_cleanup(lines):
    """Workqueue 생성 후 cleanup 확인"""
    issues = []
    content = '\n'.join(lines)

    created = len(re.findall(r'create_\w*workqueue\(', content))
    destroyed = len(re.findall(r'destroy_workqueue\(', content))

    if created > destroyed:
        issues.append(Issue(
            line=0,
            pattern="workqueue leak",
            severity="HIGH",
            message=f"Workqueue created {created}x but destroyed {destroyed}x — possible leak",
            suggest="Ensure destroy_workqueue() called in error paths and cleanup"
        ))

    return CheckResult(
        name="Workqueue Lifecycle",
        passed=len(issues) == 0,
        issues=issues
    )


# ─────────────────────────────────────────
# 리포트
# ─────────────────────────────────────────

SEVERITY_EMOJI = {
    'CRITICAL': '🚨',
    'HIGH':     '🔴',
    'MEDIUM':   '🟡',
    'LOW':      '🟢',
}


def verdict_emoji(passed):
    return "✅ PASS" if passed else "❌ FAIL"


def print_report(filepath, results):
    fname = os.path.basename(filepath)
    all_issues = [iss for r in results for iss in r.issues]
    critical = sum(1 for i in all_issues if i.severity == 'CRITICAL')
    high     = sum(1 for i in all_issues if i.severity == 'HIGH')

    overall = "✅ PASS" if critical == 0 and high == 0 else \
              "⚠️  WARN" if critical == 0 else "❌ FAIL"

    print("=" * 60)
    print(f"  Kernel Coding Standards Check: {fname}")
    print(f"  Overall: {overall}")
    print("=" * 60)

    for result in results:
        mark = "✅" if result.passed else "❌"
        print(f"\n{mark} {result.name}")
        if not result.issues:
            print("   No issues found.")
        else:
            for iss in result.issues:
                emoji = SEVERITY_EMOJI.get(iss.severity, '•')
                loc = f"line {iss.line}" if iss.line > 0 else "file-level"
                print(f"   {emoji} [{iss.severity}] {loc}: {iss.message}")
                print(f"      → {iss.suggest}")

    if all_issues:
        print(f"\n📊 Summary: {len(all_issues)} issues "
              f"({critical} CRITICAL, {high} HIGH, "
              f"{sum(1 for i in all_issues if i.severity=='MEDIUM')} MEDIUM)")
    else:
        print("\n✅ All checks passed!")
    print("=" * 60)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 kernel_check.py <file.c>", file=sys.stderr)
        sys.exit(1)

    filepath = sys.argv[1]
    if not os.path.isfile(filepath):
        print(f"Error: '{filepath}' not found", file=sys.stderr)
        sys.exit(1)

    with open(filepath, encoding='utf-8', errors='ignore') as f:
        lines = f.read().splitlines()

    results = [
        check_skb_ownership(lines),
        check_null_after_alloc(lines),
        check_gfp_flags(lines),
        check_module_metadata(lines, filepath),
        check_workqueue_cleanup(lines),
    ]

    print_report(filepath, results)

    has_critical = any(
        iss.severity == 'CRITICAL'
        for r in results for iss in r.issues
    )
    sys.exit(2 if has_critical else (1 if any(r.issues for r in results) else 0))


if __name__ == "__main__":
    main()
