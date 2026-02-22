#!/usr/bin/env python3
"""
god_module_score.py - God Module 점수 계산기
─────────────────────────────────────────────
Skill의 SKILL.md에서 이 스크립트를 호출하면
stdout 결과만 context에 inject됨 (코드 자체는 들어가지 않음)

사용법:
  python3 god_module_score.py <file.c>
  python3 god_module_score.py src/core/wifi_core.c
"""

import sys
import os
import re
import subprocess


# ─────────────────────────────────────────
# 점수 테이블
# ─────────────────────────────────────────

LOC_TABLE = [
    (200,  5.0),
    (300,  4.0),
    (500,  3.0),
    (800,  2.0),
    (float('inf'), 1.0),
]

RESP_TABLE = [
    (2,  5.0),
    (4,  4.0),
    (6,  3.0),
    (9,  2.0),
    (float('inf'), 1.0),
]

COUPLING_TABLE = [
    (2,  5.0),
    (5,  4.0),
    (10, 3.0),
    (15, 2.0),
    (float('inf'), 1.0),
]

WEIGHTS = {'loc': 0.3, 'resp': 0.4, 'coupling': 0.3}


def lookup(value, table):
    for threshold, score in table:
        if value <= threshold:
            return score
    return 1.0


# ─────────────────────────────────────────
# 측정 함수들
# ─────────────────────────────────────────

def count_lines(filepath):
    with open(filepath, encoding='utf-8', errors='ignore') as f:
        return sum(1 for _ in f)


def detect_responsibilities(filepath):
    """
    책임(Responsibility) 식별:
    - "RESPONSIBILITY" 주석 마커
    - "// ──" 섹션 구분선
    - 주요 기능 키워드 패턴
    """
    responsibility_patterns = [
        r'RESPONSIBILITY\s+\d+',
        r'//\s*─{10,}',          # 섹션 구분선
        r'//\s*={10,}',
    ]

    # 기능 영역 키워드 (각각 독립 책임으로 카운트)
    functional_keywords = {
        'device lifecycle':  [r'_init\b', r'_deinit\b', r'_probe\b', r'_remove\b'],
        'TX path':           [r'_tx\b', r'tx_worker', r'tx_submit'],
        'RX path':           [r'_rx\b', r'rx_worker', r'netif_rx'],
        'scanning':          [r'scan_start', r'scan_result', r'scan_done'],
        'connection':        [r'connect\b', r'disconnect\b', r'assoc'],
        'power management':  [r'suspend\b', r'resume\b', r'power_save'],
        'statistics':        [r'stats\b', r'_stat\b', r'get_stats'],
        'config':            [r'set_tx_power', r'set_rts', r'set_frag'],
        'firmware':          [r'fw_load', r'fw_reset', r'firmware'],
        'roaming':           [r'roam', r'ROAM_'],
        'security':          [r'wpa_', r'encrypt', r'decrypt', r'auth\b'],
        'cfg80211 coupling': [r'cfg80211_notify', r'cfg80211_report'],
    }

    with open(filepath, encoding='utf-8', errors='ignore') as f:
        content = f.read()

    found_areas = []
    for area, patterns in functional_keywords.items():
        for pat in patterns:
            if re.search(pat, content):
                found_areas.append(area)
                break

    # 섹션 마커로도 카운트
    marker_count = sum(
        len(re.findall(pat, content))
        for pat in responsibility_patterns
    )

    return found_areas, max(len(found_areas), marker_count // 2)


def count_coupling(filepath):
    """외부 레이어 직접 호출 횟수"""
    coupling_patterns = [
        r'\bmac_\w+\(',        # mac layer calls
        r'\bcfg80211_\w+\(',   # cfg80211 calls
        r'\bwpa_\w+\(',        # security calls
        r'\bnet_\w+\(',        # net device calls
    ]
    with open(filepath, encoding='utf-8', errors='ignore') as f:
        content = f.read()

    calls = {}
    total = 0
    for pat in coupling_patterns:
        matches = re.findall(pat, content)
        if matches:
            layer = pat.split('_')[0].lstrip(r'\b')
            calls[layer] = len(matches)
            total += len(matches)

    return calls, total


# ─────────────────────────────────────────
# 리포트 출력
# ─────────────────────────────────────────

GRADE = {
    (4.5, 5.0): ("EXCELLENT", "🟢"),
    (3.5, 4.5): ("GOOD",      "🟡"),
    (2.5, 3.5): ("FAIR",      "🟠"),
    (1.5, 2.5): ("POOR",      "🔴"),
    (0.0, 1.5): ("CRITICAL",  "💀"),
}


def get_grade(score):
    for (lo, hi), (label, emoji) in GRADE.items():
        if lo <= score <= hi:
            return label, emoji
    return "CRITICAL", "💀"


def print_report(filepath, loc, responsibilities, resp_count,
                 coupling_calls, coupling_total):
    fname = os.path.basename(filepath)

    loc_score      = lookup(loc, LOC_TABLE)
    resp_score     = lookup(resp_count, RESP_TABLE)
    coupling_score = lookup(coupling_total, COUPLING_TABLE)

    final = (loc_score      * WEIGHTS['loc']
           + resp_score     * WEIGHTS['resp']
           + coupling_score * WEIGHTS['coupling'])

    label, emoji = get_grade(final)

    print("=" * 60)
    print(f"  God Module Score: {fname}")
    print("=" * 60)

    print(f"\n📏 Lines of Code: {loc}")
    print(f"   Score: {loc_score:.1f}/5.0  (weight 30%)")

    print(f"\n🎯 Responsibilities: {resp_count}개")
    for r in responsibilities:
        print(f"   • {r}")
    print(f"   Score: {resp_score:.1f}/5.0  (weight 40%)")

    print(f"\n🔗 Cross-layer Coupling: {coupling_total}회 외부 호출")
    for layer, count in sorted(coupling_calls.items()):
        print(f"   • {layer}_*() : {count}회")
    print(f"   Score: {coupling_score:.1f}/5.0  (weight 30%)")

    print(f"\n{'─'*60}")
    print(f"  {emoji}  Final Score : {final:.2f} / 5.0  [{label}]")
    print(f"      Team Target : 4.0+ / 5.0")
    gap = 4.0 - final
    if gap > 0:
        print(f"      Gap to goal : -{gap:.2f} points")
    else:
        print(f"      ✅ Already meets team target!")

    print(f"\n💡 Top Improvements:")
    suggestions = []
    if loc > 500:
        suggestions.append(f"Split {fname} into focused sub-modules (<300 lines each)")
    if resp_count > 5:
        top = responsibilities[:3]
        suggestions.append(f"Extract these to separate files: {', '.join(top)}")
    if coupling_total > 10:
        suggestions.append("Add abstraction layer (callback/interface) to reduce direct coupling")
    if not suggestions:
        suggestions.append("Consider further decomposition for maintainability")

    for i, s in enumerate(suggestions, 1):
        print(f"  {i}. {s}")

    # 분리 후 예상 점수
    expected_loc = min(loc // max(resp_count, 1), 250)
    exp_score = lookup(expected_loc, LOC_TABLE) * 0.3 + 4.5 * 0.4 + 4.5 * 0.3
    print(f"\n📈 After modularization: ~{exp_score:.1f}/5.0 (estimated)")
    print("=" * 60)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 god_module_score.py <file.c>", file=sys.stderr)
        sys.exit(1)

    filepath = sys.argv[1]
    if not os.path.isfile(filepath):
        print(f"Error: '{filepath}' not found", file=sys.stderr)
        sys.exit(1)

    loc = count_lines(filepath)
    responsibilities, resp_count = detect_responsibilities(filepath)
    coupling_calls, coupling_total = count_coupling(filepath)

    print_report(filepath, loc, responsibilities, resp_count,
                 coupling_calls, coupling_total)


if __name__ == "__main__":
    main()
