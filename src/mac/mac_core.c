// mac_core.c
// MAC (Medium Access Control) Layer
// Handles 802.11 frame processing, association, and QoS

#include <linux/kernel.h>
#include <linux/skbuff.h>
#include "mac_core.h"
#include "../cfg80211/cfg_ops.h"    // mac → cfg (another dependency)

// mac_core → wifi_core → mac_core (CIRCULAR via headers)
// mac_core → cfg80211 → mac_core (ANOTHER CYCLE!)

struct mac_context {
    u8   bssid[6];
    u32  assoc_id;
    bool qos_enabled;
    u32  tx_power;
    bool power_save;
};

int mac_associate(void *mac_ctx, struct wifi_bss_info *bss)
{
    struct mac_context *ctx = mac_ctx;
    if (!ctx || !bss)
        return -EINVAL;

    memcpy(ctx->bssid, bss->bssid, 6);

    // Notify cfg80211 about association
    // mac → cfg80211 dependency
    cfg80211_report_association(bss->bssid);

    pr_info("mac: associated with %pM\n", bss->bssid);
    return 0;
}

int mac_disassociate(void *mac_ctx)
{
    struct mac_context *ctx = mac_ctx;
    if (!ctx)
        return -EINVAL;

    memset(ctx->bssid, 0, 6);
    cfg80211_report_disassociation();   // mac → cfg again
    pr_info("mac: disassociated\n");
    return 0;
}

int mac_tx_submit(void *mac_ctx, struct sk_buff *skb)
{
    // Would submit to HW ring buffer
    pr_debug("mac: TX submit len=%u\n", skb->len);
    dev_kfree_skb(skb);
    return 0;
}

void mac_set_qos_tag(void *mac_ctx, struct sk_buff *skb)
{
    // Set QoS TID based on DSCP
    // skb->priority = ...
}

int mac_set_power_save(void *mac_ctx, bool enable)
{
    struct mac_context *ctx = mac_ctx;
    if (!ctx)
        return -EINVAL;
    ctx->power_save = enable;
    pr_info("mac: power save %s\n", enable ? "ON" : "OFF");
    return 0;
}

int mac_set_tx_power(void *mac_ctx, u32 dbm)
{
    struct mac_context *ctx = mac_ctx;
    if (!ctx)
        return -EINVAL;
    ctx->tx_power = dbm;
    pr_info("mac: TX power set to %u dBm\n", dbm);
    return 0;
}
