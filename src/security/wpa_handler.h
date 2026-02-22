#ifndef WPA_HANDLER_H
#define WPA_HANDLER_H

#include "../../include/wifi_types.h"

struct sk_buff;

// WPA2/WPA3 security handler interface
int  wpa_start_auth(void *sec_ctx, struct wifi_bss_info *bss);
int  wpa_encrypt_skb(void *sec_ctx, struct sk_buff *skb);
int  wpa_decrypt_skb(void *sec_ctx, struct sk_buff *skb);
void wpa_reset(void *sec_ctx);

#endif /* WPA_HANDLER_H */
