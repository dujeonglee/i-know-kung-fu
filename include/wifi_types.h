#ifndef WIFI_TYPES_H
#define WIFI_TYPES_H

#include <linux/types.h>
#include <linux/skbuff.h>

/* WiFi connection states */
enum wifi_state {
    WIFI_STATE_DISCONNECTED = 0,
    WIFI_STATE_SCANNING,
    WIFI_STATE_AUTHENTICATING,
    WIFI_STATE_ASSOCIATING,
    WIFI_STATE_CONNECTED,
    WIFI_STATE_ROAMING,
};

/* Security types */
enum wifi_security {
    WIFI_SEC_OPEN = 0,
    WIFI_SEC_WEP,
    WIFI_SEC_WPA2,
    WIFI_SEC_WPA3,
};

struct wifi_bss_info {
    u8  bssid[6];
    u8  ssid[32];
    u8  ssid_len;
    s32 rssi;
    u32 channel;
    enum wifi_security security;
};

struct wifi_config {
    u32 tx_power_dbm;
    u32 rts_threshold;
    u32 frag_threshold;
    bool qos_enabled;
};

#endif /* WIFI_TYPES_H */
