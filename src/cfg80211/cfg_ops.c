// cfg_ops.c
// cfg80211 interface implementation
// Bridges between kernel wireless subsystem and driver

#include <linux/kernel.h>
#include "cfg_ops.h"
#include "../mac/mac_core.h"     // cfg80211 → mac (and mac → cfg = CYCLE)
#include "../core/wifi_core.h"   // cfg80211 → wifi_core (and wifi_core → cfg = CYCLE)

struct wifi_cfg_ops g_cfg_ops;

void cfg80211_notify_scan_started(void *netdev)
{
    pr_info("cfg80211: scan started event\n");
    // would call cfg80211_scan_started() kernel API
}

void cfg80211_notify_scan_done(void *netdev)
{
    pr_info("cfg80211: scan done event\n");
    // would call cfg80211_scan_done() kernel API
}

void cfg80211_notify_disconnected(void *netdev)
{
    pr_info("cfg80211: disconnected event\n");
    // would call cfg80211_disconnected() kernel API
}

void cfg80211_report_association(const u8 *bssid)
{
    pr_info("cfg80211: associated with %pM\n", bssid);
    // would call cfg80211_connect_result()
}

void cfg80211_report_disassociation(void)
{
    pr_info("cfg80211: disassociated\n");
}

// cfg80211 scan callback - called by kernel wireless stack
static int cfg_scan(void *dev, void *request)
{
    // Calls back into wifi_core! (bidirectional dependency)
    struct wifi_device *wifi_dev = dev;
    return wifi_core_scan_start(wifi_dev);  // cfg → wifi_core (CYCLE!)
}

// cfg80211 connect callback
static int cfg_connect(void *dev, void *params)
{
    // Direct mac call without going through wifi_core
    // cfg → mac (direct coupling)
    return 0;
}
