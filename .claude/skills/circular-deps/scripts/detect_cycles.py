#!/usr/bin/env python3
"""
detect_cycles.py - Tarjan's SCC 기반 순환 의존성 탐지기
────────────────────────────────────────────────────────
Skill의 SKILL.md가 이 스크립트를 bash로 실행하면:
  - 스크립트 실행 코드 자체는 context에 들어가지 않음
  - 실행 결과(stdout)만 context에 inject됨
  → context window 절약의 핵심!

사용법:
  python3 detect_cycles.py [directory]
  python3 detect_cycles.py src/
"""

import sys
import os
import re
from collections import defaultdict


# ─────────────────────────────────────────
# 1. 의존성 그래프 구성
# ─────────────────────────────────────────

def collect_includes(directory):
    """C/H 파일에서 로컬 #include 관계를 수집"""
    graph = defaultdict(set)   # module → {depends_on, ...}
    file_map = {}              # short_name → full_path

    for root, _, files in os.walk(directory):
        for fname in files:
            if not fname.endswith(('.c', '.h')):
                continue
            fpath = os.path.join(root, fname)
            # 짧은 이름: src/core/wifi_core.c 형태
            short = os.path.relpath(fpath, start=os.path.dirname(directory))
            file_map[short] = fpath
            graph[short]  # 노드 등록 (엣지 없어도)

    # 각 파일의 #include "" 파싱
    for short, fpath in file_map.items():
        try:
            with open(fpath, encoding='utf-8', errors='ignore') as f:
                for line in f:
                    m = re.match(r'\s*#include\s+"([^"]+)"', line)
                    if not m:
                        continue
                    inc = m.group(1)
                    # 포함된 헤더를 실제 파일 경로로 resolve
                    base_dir = os.path.dirname(fpath)
                    candidate = os.path.normpath(os.path.join(base_dir, inc))
                    candidate_short = os.path.relpath(candidate,
                                        start=os.path.dirname(directory))
                    if candidate_short in file_map:
                        graph[short].add(candidate_short)
        except OSError:
            pass

    return graph, file_map


# ─────────────────────────────────────────
# 2. Tarjan's SCC 알고리즘
# ─────────────────────────────────────────

def tarjan_scc(graph):
    """
    Tarjan's Strongly Connected Components 알고리즘
    사이클(크기>1인 SCC)을 찾아 반환
    """
    index_counter = [0]
    stack = []
    lowlinks = {}
    index = {}
    on_stack = {}
    sccs = []

    def strongconnect(v):
        index[v] = index_counter[0]
        lowlinks[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack[v] = True

        for w in graph.get(v, []):
            if w not in index:
                strongconnect(w)
                lowlinks[v] = min(lowlinks[v], lowlinks[w])
            elif on_stack.get(w):
                lowlinks[v] = min(lowlinks[v], index[w])

        if lowlinks[v] == index[v]:
            scc = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                scc.append(w)
                if w == v:
                    break
            if len(scc) > 1:   # 크기 1은 사이클 아님
                sccs.append(scc)

    for v in graph:
        if v not in index:
            strongconnect(v)

    return sccs


# ─────────────────────────────────────────
# 3. 출력 포맷
# ─────────────────────────────────────────

def short_name(path):
    """경로에서 파일명만 추출 (출력 간결하게)"""
    return os.path.basename(path)


def print_report(graph, cycles):
    total = len(graph)
    cyclic_nodes = set(node for cycle in cycles for node in cycle)
    clean_nodes = set(graph.keys()) - cyclic_nodes

    print("=" * 60)
    print("  Circular Dependency Analysis Report")
    print("  (Tarjan's SCC Algorithm)")
    print("=" * 60)

    # 의존성 그래프 요약
    print("\n📊 Dependency Graph Summary")
    print("-" * 40)
    for node, deps in sorted(graph.items()):
        dep_str = ', '.join(short_name(d) for d in sorted(deps)) or '(none)'
        status = "🔴" if node in cyclic_nodes else "✅"
        print(f"  {status} {short_name(node):<25} → {dep_str}")

    # 발견된 사이클
    print(f"\n🔍 Cycles Detected: {len(cycles)}")
    print("-" * 40)
    if not cycles:
        print("  ✅ No circular dependencies found!")
    else:
        for i, cycle in enumerate(cycles, 1):
            names = [short_name(n) for n in cycle]
            # 사이클을 화살표로 시각화
            chain = ' → '.join(names) + f' → {names[0]}'
            severity = "CRITICAL" if len(cycle) >= 3 else "HIGH"
            print(f"\n  🔴 CYCLE {i} [{severity}] ({len(cycle)}-node)")
            print(f"     {chain}")

            # 해결 방향 제시
            print(f"     💡 Fix: Extract shared interface header to break cycle")

    # 정상 모듈
    print(f"\n✅ Clean Modules ({len(clean_nodes)})")
    print("-" * 40)
    for node in sorted(clean_nodes):
        deps = graph[node]
        dep_count = len(deps)
        print(f"  ✅ {short_name(node):<25} ({dep_count} dependencies, no cycles)")

    # 메트릭 요약
    print("\n📈 Metrics")
    print("-" * 40)
    print(f"  Total modules  : {total}")
    print(f"  In cycles      : {len(cyclic_nodes)}")
    print(f"  Clean modules  : {len(clean_nodes)}")
    ratio = (len(clean_nodes) / total * 100) if total else 0
    print(f"  Cycle-free     : {ratio:.0f}%")

    # Architecture score 추정
    if len(cycles) == 0:
        score = 5.0
    elif len(cycles) <= 1:
        score = 3.5
    elif len(cycles) <= 2:
        score = 2.5
    else:
        score = 1.5
    print(f"\n  Circular Dep Score : {score}/5.0")
    print(f"  Team Target        : 5.0/5.0 (0 cycles)")
    print("=" * 60)


# ─────────────────────────────────────────
# 4. Entry point
# ─────────────────────────────────────────

def main():
    directory = sys.argv[1] if len(sys.argv) > 1 else "."
    if not os.path.isdir(directory):
        print(f"Error: '{directory}' is not a directory", file=sys.stderr)
        sys.exit(1)

    graph, file_map = collect_includes(directory)

    if not graph:
        print(f"No C/H files found in '{directory}'")
        sys.exit(0)

    cycles = tarjan_scc(graph)
    print_report(graph, cycles)

    # exit code: 사이클 있으면 1 (hook에서 감지 가능)
    sys.exit(1 if cycles else 0)


if __name__ == "__main__":
    main()
