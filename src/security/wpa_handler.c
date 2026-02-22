// wpa_handler.c
// WPA2/WPA3 Security Handler
//
// NOTE: This module is intentionally "clean" - no circular dependencies.
// It only depends on wifi_types.h (data types) - a leaf node in the dep graph.
// Compare this with wifi_core.c and mac_core.c to see the difference!

#include <linux/kernel.h>
#include <linux/skbuff.h>
#include <linux/random.h>
#include "wpa_handler.h"

// wpa_handler dependencies:
// wpa_handler → wifi_types (data only, no function deps)
// No other dependencies! Clean leaf module.

struct wpa_context {
    enum wifi_security  security_type;
    u8                  pmk[32];    // Pairwise Master Key
    u8                  ptk[64];    // Pairwise Transient Key
    u8                  gtk[32];    // Group Temporal Key
    bool                keys_installed;
};

int wpa_start_auth(void *sec_ctx, struct wifi_bss_info *bss)
{
    struct wpa_context *ctx = sec_ctx;
    if (!ctx || !bss)
        return -EINVAL;

    ctx->security_type = bss->security;

    switch (bss->security) {
    case WIFI_SEC_OPEN:
        ctx->keys_installed = true;  // No keys needed
        pr_info("wpa: open network, no auth required\n");
        return 0;

    case WIFI_SEC_WPA2:
        pr_info("wpa: starting WPA2 4-way handshake\n");
        // Would perform EAPOL 4-way handshake here
        // For demo: simulate success
        get_random_bytes(ctx->ptk, sizeof(ctx->ptk));
        ctx->keys_installed = true;
        return 0;

    case WIFI_SEC_WPA3:
        pr_info("wpa: starting WPA3 SAE handshake\n");
        // Would perform SAE (Simultaneous Authentication of Equals)
        get_random_bytes(ctx->pmk, sizeof(ctx->pmk));
        get_random_bytes(ctx->ptk, sizeof(ctx->ptk));
        ctx->keys_installed = true;
        return 0;

    default:
        pr_err("wpa: unsupported security type %d\n", bss->security);
        return -ENOTSUPP;
    }
}

int wpa_encrypt_skb(void *sec_ctx, struct sk_buff *skb)
{
    struct wpa_context *ctx = sec_ctx;

    if (!ctx || !ctx->keys_installed)
        return -ENOKEY;

    if (ctx->security_type == WIFI_SEC_OPEN)
        return 0;  // No encryption for open networks

    // Would perform CCMP/GCMP encryption here
    // For demo: just log
    pr_debug("wpa: encrypting skb len=%u\n", skb->len);
    return 0;
}

int wpa_decrypt_skb(void *sec_ctx, struct sk_buff *skb)
{
    struct wpa_context *ctx = sec_ctx;

    if (!ctx || !ctx->keys_installed)
        return -ENOKEY;

    if (ctx->security_type == WIFI_SEC_OPEN)
        return 0;

    pr_debug("wpa: decrypting skb len=%u\n", skb->len);
    return 0;
}

void wpa_reset(void *sec_ctx)
{
    struct wpa_context *ctx = sec_ctx;
    if (!ctx)
        return;

    memzero_explicit(ctx->ptk, sizeof(ctx->ptk));
    memzero_explicit(ctx->pmk, sizeof(ctx->pmk));
    memzero_explicit(ctx->gtk, sizeof(ctx->gtk));
    ctx->keys_installed = false;
    pr_info("wpa: security context reset\n");
}
