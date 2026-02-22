#ifndef MAC_CORE_H
#define MAC_CORE_H

// mac_core.h includes wifi_core.h → CIRCULAR DEPENDENCY (demo용)
#include "../../include/wifi_types.h"
#include "../core/wifi_core.h"   // ← wifi_core.c includes this file... CYCLE!

struct sk_buff;

// MAC layer interface
int  mac_associate(void *mac_ctx, struct wifi_bss_info *bss);
int  mac_disassociate(void *mac_ctx);
int  mac_tx_submit(void *mac_ctx, struct sk_buff *skb);
void mac_set_qos_tag(void *mac_ctx, struct sk_buff *skb);
int  mac_set_power_save(void *mac_ctx, bool enable);
int  mac_set_tx_power(void *mac_ctx, u32 dbm);

#endif /* MAC_CORE_H */
