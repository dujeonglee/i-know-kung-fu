#!/usr/bin/env python3
"""
PostToolUse Hook: Task(Agent) 완료 후 알림
──────────────────────────────────────────
Hook 동작 원리:
- Claude가 Task tool(=sub-agent 호출)을 완료할 때마다 실행됨
- 어떤 agent가 완료됐는지 로그
- 실제 환경에서는 Slack 알림, 데스크탑 알림 등으로 활용 가능
"""

import sys
import json
import datetime


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_response = input_data.get("tool_response", {})
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")

    # Agent 완료 로그
    log_entry = f"[{timestamp}] ✅ AGENT TASK COMPLETED\n"
    with open("/tmp/wifi_demo_audit.log", "a") as f:
        f.write(log_entry)

    # stdout으로 Claude context에 주입 (선택적)
    # 여기서 출력하면 Claude가 이 내용을 볼 수 있음
    print(f"[Hook] Sub-agent completed at {timestamp}")
    sys.exit(0)


if __name__ == "__main__":
    main()
