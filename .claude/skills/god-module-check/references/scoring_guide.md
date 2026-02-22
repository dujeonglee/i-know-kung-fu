# Software Architecture Maturity Reference
# WiFi Driver Team - 아키텍처 성숙도 기준표

## God Module Score 등급 기준

| Score | 등급 | 상태 | 설명 |
|-------|------|------|------|
| 4.5–5.0 | EXCELLENT 🟢 | 목표 달성+ | 단일 책임, 낮은 결합, 명확한 인터페이스 |
| 3.5–4.4 | GOOD 🟡 | 목표 수준 | 소수 책임, 관리 가능한 결합 |
| 2.5–3.4 | FAIR 🟠 | 개선 필요 | 여러 책임 혼재, 인터페이스 정리 필요 |
| 1.5–2.4 | POOR 🔴 | 위험 수준 | God Module 징후, 즉시 리팩토링 권장 |
| 0.0–1.4 | CRITICAL 💀 | 즉시 조치 | 전형적 God Module, 유지보수 불가 수준 |

## 팀 현황 (2025 기준)
- 현재 평균 점수: **1.5**
- 목표 점수: **4.0+**
- 기간: 2025 Q2 ~ Q4

## God Module 판별 지표

### Lines of Code
```
< 200줄  : 이상적 (단일 책임 가능성 높음)
200-500줄 : 적정 범위
500-800줄 : 위험 신호 (책임 분리 검토)
> 800줄  : God Module 확정 (즉시 분리 필요)
```

### Responsibility Count
```
1-2개 : 이상적
3-4개 : 수용 가능
5-6개 : 검토 필요
7개+  : God Module
```

### Coupling (외부 레이어 직접 호출)
```
0-2회  : 매우 낮음 (인터페이스 잘 분리됨)
3-5회  : 보통
6-10회 : 높음 (추상화 레이어 도입 검토)
10회+  : 매우 높음 (spaghetti 의존성)
```

## 순환 의존성 기준

### 허용 기준
- **0개**: 목표 (Clean Architecture)
- **1개**: 경고 (즉시 제거 계획 수립)
- **2개+**: 위반 (빌드 파이프라인 차단 권장)

### 일반적인 해결 패턴

**패턴 1: 인터페이스 헤더 분리**
```
Before: A.h ← B.h ← A.h (순환)
After:  A_interface.h ← both A.c and B.c (leaf node)
```

**패턴 2: 콜백 등록**
```
Before: core → mac → core (순환)
After:  core 가 mac에 콜백 등록,
        mac은 콜백 호출 (core를 직접 include 안 함)
```

**패턴 3: Event/Observer 패턴**
```
Before: wifi_core → cfg80211 → wifi_core
After:  wifi_core → event_bus ← cfg80211
        (두 모듈 모두 event_bus에만 의존)
```

## WiFi Driver 모듈 분리 권고안

### wifi_core.c → 분리 목표

| 분리 모듈 | 책임 | 예상 라인 | 예상 점수 |
|-----------|------|-----------|-----------|
| wifi_dev.c | Device lifecycle만 | ~80줄 | 4.5+ |
| wifi_tx.c | TX path + fragmentation | ~100줄 | 4.5+ |
| wifi_rx.c | RX path + reassembly | ~80줄 | 4.5+ |
| wifi_scan.c | Scanning logic | ~100줄 | 4.5+ |
| wifi_connect.c | Connection management | ~80줄 | 4.5+ |
| wifi_pm.c | Power management | ~50줄 | 5.0 |
| wifi_stats.c | Statistics | ~60줄 | 5.0 |
| wifi_config.c | Configuration | ~60줄 | 5.0 |
| wifi_fw.c | Firmware management | ~80줄 | 4.5+ |
| wifi_roam.c | Roaming | ~80줄 | 4.5+ |
