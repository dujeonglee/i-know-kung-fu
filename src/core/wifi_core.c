// wifi_core.c
// WiFi Core Module - Main driver entry point
//
// WARNING: This file is intentionally written as a "God Module" for demo purposes.
// It handles too many responsibilities and has circular dependencies.
// The code-reviewer and dependency-analyzer agents will detect these issues.

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/skbuff.h>
#include <linux/workqueue.h>
#include <linux/mutex.h>
#include <linux/rculist.h>
#include "include/wifi_types.h"
#include "src/mac/mac_core.h"       // mac depends back on wifi_core.h → CIRCULAR!
#include "src/cfg80211/cfg_ops.h"   // cfg depends on wifi_core.h → CIRCULAR!
#include "src/security/wpa_handler.h"

MODULE_LICENSE("GPL");
MODULE_AUTHOR("WiFi Team");
MODULE_DESCRIPTION("WiFi Driver Core - Demo (God Module Example)");

// ─────────────────────────────────────────
// RESPONSIBILITY 1: Device lifecycle
// ─────────────────────────────────────────
static struct wifi_device *g_wifi_dev;
static DEFINE_MUTEX(g_dev_lock);

struct wifi_device {
    struct net_device   *netdev;
    enum wifi_state      state;
    struct wifi_config   config;
    struct workqueue_struct *tx_wq;
    struct workqueue_struct *rx_wq;
    struct list_head     bss_list;
    spinlock_t           bss_lock;
    void                *fw_ctx;        // Firmware context
    void                *mac_ctx;       // MAC layer context
    void                *sec_ctx;       // Security context
};

int wifi_core_init(struct wifi_device **dev_out)
{
    struct wifi_device *dev;

    dev = kzalloc(sizeof(*dev), GFP_KERNEL);
    if (!dev)
        return -ENOMEM;

    spin_lock_init(&dev->bss_lock);
    INIT_LIST_HEAD(&dev->bss_list);
    dev->state = WIFI_STATE_DISCONNECTED;

    dev->tx_wq = create_singlethread_workqueue("wifi_tx");
    dev->rx_wq = create_singlethread_workqueue("wifi_rx");
    if (!dev->tx_wq || !dev->rx_wq) {
        kfree(dev);
        return -ENOMEM;
    }

    *dev_out = dev;
    g_wifi_dev = dev;
    pr_info("wifi_core: initialized\n");
    return 0;
}

void wifi_core_deinit(struct wifi_device *dev)
{
    if (!dev)
        return;
    destroy_workqueue(dev->tx_wq);
    destroy_workqueue(dev->rx_wq);
    kfree(dev);
    g_wifi_dev = NULL;
}

// ─────────────────────────────────────────
// RESPONSIBILITY 2: TX path
// ─────────────────────────────────────────
struct tx_work {
    struct work_struct  work;
    struct sk_buff      *skb;
    struct wifi_device  *dev;
};

static void wifi_tx_worker(struct work_struct *work)
{
    struct tx_work *tw = container_of(work, struct tx_work, work);
    struct sk_buff *skb = tw->skb;

    // Fragmentation
    if (skb->len > tw->dev->config.frag_threshold) {
        // TODO: fragment skb
        pr_warn("wifi_core: TX frag not implemented, dropping\n");
        dev_kfree_skb(skb);
        kfree(tw);
        return;
    }

    // QoS tagging (should be in mac layer!)
    if (tw->dev->config.qos_enabled) {
        // Direct MAC manipulation - bad coupling!
        mac_set_qos_tag(tw->dev->mac_ctx, skb);
    }

    // Encryption (should be in security layer!)
    wpa_encrypt_skb(tw->dev->sec_ctx, skb);

    // Hand off to HW
    mac_tx_submit(tw->dev->mac_ctx, skb);

    kfree(tw);
}

int wifi_core_tx(struct wifi_device *dev, struct sk_buff *skb)
{
    struct tx_work *tw;

    if (dev->state != WIFI_STATE_CONNECTED) {
        dev_kfree_skb(skb);
        return -ENOTCONN;
    }

    tw = kmalloc(sizeof(*tw), GFP_ATOMIC);
    if (!tw) {
        dev_kfree_skb(skb);
        return -ENOMEM;
    }

    INIT_WORK(&tw->work, wifi_tx_worker);
    tw->skb = skb;
    tw->dev = dev;
    queue_work(dev->tx_wq, &tw->work);
    return 0;
}

// ─────────────────────────────────────────
// RESPONSIBILITY 3: RX path
// ─────────────────────────────────────────
void wifi_core_rx(struct wifi_device *dev, struct sk_buff *skb)
{
    // Decryption (should be in security layer!)
    if (wpa_decrypt_skb(dev->sec_ctx, skb) < 0) {
        pr_warn("wifi_core: RX decrypt failed, dropping\n");
        dev_kfree_skb(skb);
        return;
    }

    // De-fragment
    // TODO: reassembly logic here

    // Pass to network stack
    skb->dev = dev->netdev;
    skb->protocol = eth_type_trans(skb, dev->netdev);
    netif_rx(skb);
}

// ─────────────────────────────────────────
// RESPONSIBILITY 4: Scanning
// ─────────────────────────────────────────
struct wifi_bss_entry {
    struct list_head    node;
    struct wifi_bss_info info;
    unsigned long       last_seen;
};

int wifi_core_scan_start(struct wifi_device *dev)
{
    if (dev->state != WIFI_STATE_DISCONNECTED) {
        pr_warn("wifi_core: can't scan while connected\n");
        return -EBUSY;
    }

    dev->state = WIFI_STATE_SCANNING;

    // Direct cfg80211 call (creates coupling to cfg layer!)
    cfg80211_notify_scan_started(dev->netdev);

    pr_info("wifi_core: scan started\n");
    return 0;
}

void wifi_core_scan_result(struct wifi_device *dev, struct wifi_bss_info *bss)
{
    struct wifi_bss_entry *entry;
    unsigned long flags;

    entry = kzalloc(sizeof(*entry), GFP_KERNEL);
    if (!entry)
        return;

    memcpy(&entry->info, bss, sizeof(*bss));
    entry->last_seen = jiffies;

    spin_lock_irqsave(&dev->bss_lock, flags);
    list_add_rcu(&entry->node, &dev->bss_list);
    spin_unlock_irqrestore(&dev->bss_lock, flags);
}

void wifi_core_scan_done(struct wifi_device *dev)
{
    dev->state = WIFI_STATE_DISCONNECTED;
    cfg80211_notify_scan_done(dev->netdev);  // coupling again!
    pr_info("wifi_core: scan done\n");
}

// ─────────────────────────────────────────
// RESPONSIBILITY 5: Connection management
// ─────────────────────────────────────────
int wifi_core_connect(struct wifi_device *dev, struct wifi_bss_info *target)
{
    int ret;

    dev->state = WIFI_STATE_AUTHENTICATING;

    // Direct security call without abstraction
    ret = wpa_start_auth(dev->sec_ctx, target);
    if (ret) {
        pr_err("wifi_core: auth failed %d\n", ret);
        dev->state = WIFI_STATE_DISCONNECTED;
        return ret;
    }

    dev->state = WIFI_STATE_ASSOCIATING;

    ret = mac_associate(dev->mac_ctx, target);
    if (ret) {
        pr_err("wifi_core: assoc failed %d\n", ret);
        dev->state = WIFI_STATE_DISCONNECTED;
        return ret;
    }

    dev->state = WIFI_STATE_CONNECTED;
    pr_info("wifi_core: connected to %pM\n", target->bssid);
    return 0;
}

void wifi_core_disconnect(struct wifi_device *dev)
{
    mac_disassociate(dev->mac_ctx);
    wpa_reset(dev->sec_ctx);
    dev->state = WIFI_STATE_DISCONNECTED;
    cfg80211_notify_disconnected(dev->netdev);  // coupling!
}

// ─────────────────────────────────────────
// RESPONSIBILITY 6: Power management
// ─────────────────────────────────────────
int wifi_core_suspend(struct wifi_device *dev)
{
    mac_set_power_save(dev->mac_ctx, true);
    pr_info("wifi_core: suspended\n");
    return 0;
}

int wifi_core_resume(struct wifi_device *dev)
{
    mac_set_power_save(dev->mac_ctx, false);
    pr_info("wifi_core: resumed\n");
    return 0;
}

// ─────────────────────────────────────────
// RESPONSIBILITY 7: Statistics
// ─────────────────────────────────────────
struct wifi_stats {
    u64 tx_packets;
    u64 rx_packets;
    u64 tx_bytes;
    u64 rx_bytes;
    u32 tx_errors;
    u32 rx_errors;
    u32 tx_dropped;
    u32 rx_dropped;
};

static struct wifi_stats g_stats;

void wifi_core_update_tx_stats(u32 bytes, bool success)
{
    if (success) {
        g_stats.tx_packets++;
        g_stats.tx_bytes += bytes;
    } else {
        g_stats.tx_errors++;
        g_stats.tx_dropped++;
    }
}

void wifi_core_update_rx_stats(u32 bytes, bool success)
{
    if (success) {
        g_stats.rx_packets++;
        g_stats.rx_bytes += bytes;
    } else {
        g_stats.rx_errors++;
        g_stats.rx_dropped++;
    }
}

void wifi_core_get_stats(struct wifi_stats *out)
{
    memcpy(out, &g_stats, sizeof(*out));
}

// ─────────────────────────────────────────
// RESPONSIBILITY 8: Config management
// (Should be a separate config module)
// ─────────────────────────────────────────
int wifi_core_set_tx_power(struct wifi_device *dev, u32 dbm)
{
    if (dbm > 30) {
        pr_err("wifi_core: tx power %u dBm exceeds regulatory limit\n", dbm);
        return -EINVAL;
    }
    dev->config.tx_power_dbm = dbm;
    return mac_set_tx_power(dev->mac_ctx, dbm);  // mac coupling
}

int wifi_core_set_rts_threshold(struct wifi_device *dev, u32 thresh)
{
    dev->config.rts_threshold = thresh;
    return 0;
}

// ─────────────────────────────────────────
// RESPONSIBILITY 9: Firmware management
// (Definitely should be its own module!)
// ─────────────────────────────────────────
int wifi_core_fw_load(struct wifi_device *dev, const char *fw_path)
{
    // Firmware loading logic embedded in core - bad!
    pr_info("wifi_core: loading firmware from %s\n", fw_path);
    // ... would use request_firmware() here
    return 0;
}

int wifi_core_fw_reset(struct wifi_device *dev)
{
    pr_info("wifi_core: resetting firmware\n");
    wifi_core_deinit(dev);
    return wifi_core_init(&dev);
}

// ─────────────────────────────────────────
// RESPONSIBILITY 10: Roaming
// (Complex enough to be its own module)
// ─────────────────────────────────────────
#define ROAM_RSSI_THRESHOLD  -75  /* dBm */

void wifi_core_check_roaming(struct wifi_device *dev, s32 current_rssi)
{
    if (dev->state != WIFI_STATE_CONNECTED)
        return;

    if (current_rssi < ROAM_RSSI_THRESHOLD) {
        pr_info("wifi_core: RSSI %d dBm below threshold, triggering roam scan\n",
                current_rssi);
        dev->state = WIFI_STATE_ROAMING;
        wifi_core_scan_start(dev);  // self-call creating complexity
    }
}
