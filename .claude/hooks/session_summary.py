#!/usr/bin/env python3
"""
Stop Hook: 세션 종료 시 요약 생성
──────────────────────────────────
Hook 동작 원리:
- Claude가 응답을 완료(Stop)할 때 실행됨
- 세션 중 수행된 모든 Bash 명령을 요약
- 감사 로그로 저장
"""

import sys
import json
import datetime
import os


def main():
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 감사 로그 읽기
    log_path = "/tmp/wifi_demo_audit.log"
    commands = []
    if os.path.exists(log_path):
        with open(log_path) as f:
            commands = f.readlines()

    # 세션 요약 파일 생성
    summary = f"""
=== WiFi Driver Review Session Summary ===
Completed at: {timestamp}
Total tool uses logged: {len(commands)}

Recent activity:
{''.join(commands[-10:]) if commands else '  (none)'}
==========================================
"""

    summary_path = "/tmp/wifi_demo_session_summary.txt"
    with open(summary_path, "w") as f:
        f.write(summary)

    # 로그 초기화 (다음 세션을 위해)
    if os.path.exists(log_path):
        os.remove(log_path)

    print(f"[Hook] Session summary saved to {summary_path}")
    sys.exit(0)


if __name__ == "__main__":
    main()
