#!/usr/bin/env python3
"""
PreToolUse Hook: Bash 명령 실행 전 로깅
─────────────────────────────────────────
Hook 동작 원리:
- Claude가 Bash tool을 사용하려 할 때 이 스크립트가 먼저 실행됨
- stdin으로 tool 정보 JSON을 받음
- exit 0: 정상 진행
- exit 2: Claude에게 feedback 전달 (진행은 계속)
- stdout 출력: Claude의 context에 추가됨
"""

import sys
import json
import datetime

def main():
    try:
        # Claude가 stdin으로 tool 정보를 JSON으로 전달
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)  # JSON 파싱 실패 시 그냥 진행

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "")

    # 로그 기록
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] BASH CMD: {command[:80]}{'...' if len(command) > 80 else ''}\n"

    with open("/tmp/wifi_demo_audit.log", "a") as f:
        f.write(log_entry)

    # 위험한 명령 차단 (결정론적 안전장치)
    dangerous = ["rm -rf", "git push", "dd if=", "mkfs"]
    for danger in dangerous:
        if danger in command:
            # stdout으로 Claude에게 경고 전달
            print(f"⚠️  HOOK BLOCKED: Dangerous command detected: '{danger}'")
            sys.exit(2)  # exit 2 = Claude에게 feedback, 하지만 계속 진행

    # 정상: 아무것도 출력 안 함, exit 0
    sys.exit(0)

if __name__ == "__main__":
    main()
