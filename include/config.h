#pragma once

#include <stdint.h>

// Copy include/secrets.h.example to include/secrets.h and fill in Wi-Fi + location.

enum Screen : uint8_t {
  SCREEN_CLOCK = 0,
  SCREEN_WEATHER = 1,
  SCREEN_SPOTIFY = 2,
  SCREEN_NETWORK = 3,
  SCREEN_COUNT = 4
};

// NTP (POSIX TZ string). Examples:
//   US Eastern:  "EST5EDT,M3.2.0,M11.1.0"
//   UK:          "GMT0BST,M3.5.0/1,M10.5.0"
//   EU (Paris):  "CET-1CEST,M3.5.0,M10.5.0/3"
#ifndef TIMEZONE
#define TIMEZONE "EST5EDT,M3.2.0,M11.1.0"
#endif

// Open-Meteo uses decimal degrees (Joliette, Quebec)
#ifndef WEATHER_LAT
#define WEATHER_LAT 46.0247
#endif
#ifndef WEATHER_LON
#define WEATHER_LON -73.4513
#endif

// Page button: back BOOT only (GPIO 9). Tap and release — do not hold (flash mode).
// The side tact switch on many boards is a battery POWER key (PMIC), not an ESP GPIO.
#define BUTTON_PIN 9
#define BUTTON_DEBOUNCE_MS 50
#define BUTTON_COOLDOWN_MS 400

// 0 = pages change only via GPIO 9 button
#define AUTO_ROTATE_MS 0

// Display rotation: 0–3 (180° from previous setting)
#define DISPLAY_ROTATION 0

// How often to refresh weather / public IP (milliseconds)
#define WEATHER_REFRESH_MS (15UL * 60UL * 1000UL)
#define NETWORK_REFRESH_MS (10UL * 60UL * 1000UL)
#define SPOTIFY_REFRESH_MS (5UL * 1000UL)

// Spotify marquee: pixels per second (lower = slower) and pause at loop end (ms)
#define MARQUEE_SCROLL_PX_PER_SEC 30
#define MARQUEE_SCROLL_PAUSE_MS 2200

// Wi-Fi health: detect drops and reconnect (modem sleep disabled in firmware)
#define WIFI_CHECK_MS 3000UL
#define WIFI_RECONNECT_MS 12000UL

// HTTP page control (Mac send-page.sh over Wi-Fi, optional)
#define PAGE_HTTP_PORT 8080
#define MDNS_HOSTNAME "esp32-clock"

// Mac notification overlay duration (milliseconds)
#define NOTIFICATION_DISPLAY_MS 15000UL
