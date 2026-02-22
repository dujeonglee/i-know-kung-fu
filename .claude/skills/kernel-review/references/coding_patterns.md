# Linux Kernel WiFi Driver - 코딩 패턴 레퍼런스
# kernel-review skill이 참조하는 가이드라인 문서

## sk_buff 소유권 규칙 (CRITICAL)

### 핵심 원칙
sk_buff의 소유권을 전달한 이후에는 절대 접근하면 안 됩니다.

### 소유권 이전 함수들
```c
netif_rx(skb);          // 네트워크 스택으로 이전 → 이후 skb 접근 금지
dev_kfree_skb(skb);     // 해제 → 이후 접근 금지
kfree_skb(skb);         // 해제 → 이후 접근 금지
mac_tx_submit(ctx, skb) // 드라이버 TX 큐로 이전 → 이후 접근 금지
```

### 올바른 패턴
```c
// ❌ 잘못된 코드 - use-after-free!
netif_rx(skb);
stats.rx_bytes += skb->len;   // 소유권 이전 후 접근!

// ✅ 올바른 코드
u32 len = skb->len;           // 먼저 저장
netif_rx(skb);                // 그 다음 이전
stats.rx_bytes += len;        // 저장해둔 값 사용
```

## 메모리 할당 패턴

### GFP 플래그 선택 기준
```c
// 프로세스 컨텍스트 (sleep 가능)
ptr = kzalloc(size, GFP_KERNEL);

// 아토믹 컨텍스트 (spinlock 보유, ISR, tasklet)
ptr = kzalloc(size, GFP_ATOMIC);

// workqueue 핸들러 → 보통 GFP_KERNEL 가능 (but 확인 필요)
```

### NULL 체크 필수 패턴
```c
// ❌ 잘못된 코드
dev = kzalloc(sizeof(*dev), GFP_KERNEL);
dev->state = WIFI_STATE_DISCONNECTED;  // NULL이면 crash!

// ✅ 올바른 코드
dev = kzalloc(sizeof(*dev), GFP_KERNEL);
if (!dev)
    return -ENOMEM;
dev->state = WIFI_STATE_DISCONNECTED;
```

## RCU 패턴

### list_add_rcu 사용 시
```c
// ✅ RCU 보호 리스트 추가
spin_lock_irqsave(&dev->bss_lock, flags);
list_add_rcu(&entry->node, &dev->bss_list);
spin_unlock_irqrestore(&dev->bss_lock, flags);

// ✅ RCU 보호 리스트 순회
rcu_read_lock();
list_for_each_entry_rcu(entry, &dev->bss_list, node) {
    // ... process entry
}
rcu_read_unlock();

// ✅ 삭제 시 synchronize_rcu() 또는 call_rcu()
list_del_rcu(&entry->node);
synchronize_rcu();  // 모든 RCU reader가 빠져나올 때까지 대기
kfree(entry);
```

## Workqueue 패턴

### 생성/소멸 대칭
```c
// 생성
dev->tx_wq = create_singlethread_workqueue("wifi_tx");
if (!dev->tx_wq)
    goto err_wq;

// Error path에서도 반드시 정리
err_wq:
    if (dev->tx_wq)
        destroy_workqueue(dev->tx_wq);

// 모듈 remove 시
cancel_work_sync(&tw->work);    // 진행 중인 work 완료 대기
destroy_workqueue(dev->tx_wq);  // 그 다음 해제
```

### work item 메모리 관리
```c
// ✅ work item 내에서 자기 자신을 free
static void wifi_tx_worker(struct work_struct *work)
{
    struct tx_work *tw = container_of(work, struct tx_work, work);
    // ... 작업 수행
    dev_kfree_skb(tw->skb);
    kfree(tw);  // work item 자신을 마지막에 free
}
```

## 모듈 메타데이터 (모든 드라이버 파일에 필수)
```c
MODULE_LICENSE("GPL");
MODULE_AUTHOR("WiFi Team <wifi@example.com>");
MODULE_DESCRIPTION("WiFi Driver - [모듈 설명]");
MODULE_VERSION("1.0");
```

## 에러 처리 패턴 (goto 사용)
```c
int wifi_core_init(struct wifi_device **dev_out)
{
    struct wifi_device *dev;
    int ret;

    dev = kzalloc(sizeof(*dev), GFP_KERNEL);
    if (!dev)
        return -ENOMEM;

    dev->tx_wq = create_singlethread_workqueue("wifi_tx");
    if (!dev->tx_wq) {
        ret = -ENOMEM;
        goto err_tx_wq;
    }

    dev->rx_wq = create_singlethread_workqueue("wifi_rx");
    if (!dev->rx_wq) {
        ret = -ENOMEM;
        goto err_rx_wq;
    }

    *dev_out = dev;
    return 0;

err_rx_wq:
    destroy_workqueue(dev->tx_wq);
err_tx_wq:
    kfree(dev);
    return ret;
}
```
