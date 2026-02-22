#ifndef CFG_OPS_H
#define CFG_OPS_H

// cfg80211 ops interface
// cfg80211 depends on mac_core AND wifi_core → creates cycle:
// wifi_core → cfg80211 → mac_core → cfg80211 (CYCLE!)

#include "../../include/wifi_types.h"
#include "../mac/mac_core.h"   // ← cfg depends on mac... mac depends on cfg!

void cfg80211_notify_scan_started(void *netdev);
void cfg80211_notify_scan_done(void *netdev);
void cfg80211_notify_disconnected(void *netdev);
void cfg80211_report_association(const u8 *bssid);
void cfg80211_report_disassociation(void);

// cfg80211 operations table (filled in during probe)
struct wifi_cfg_ops {
    int (*scan)(void *dev, void *request);
    int (*connect)(void *dev, void *params);
    int (*disconnect)(void *dev, u16 reason);
    int (*get_station)(void *dev, const u8 *mac, void *sinfo);
    int (*set_power_mgmt)(void *dev, bool enabled, int timeout);
};

extern struct wifi_cfg_ops g_cfg_ops;

#endif /* CFG_OPS_H */
