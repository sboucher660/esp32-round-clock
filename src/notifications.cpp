#include "notifications.h"

#include <Arduino.h>
#include <TFT_eSPI.h>
#include <time.h>

#include "config.h"

extern TFT_eSPI tft;
extern Screen currentScreen;
extern void invalidateAllScreens();
extern void drawCurrentScreen(const struct tm &timeinfo);

static const uint16_t COL_EINK_PAPER = 0x3186;
static const uint16_t COL_EINK_INK = 0xE71C;
static const uint16_t COL_EINK_GRAY = 0x9CD3;
static const uint16_t COL_EINK_LINE = 0x4A69;

constexpr int kCenterX = 120;
constexpr int kVpX = 20;
constexpr int kVpW = 200;
constexpr int kLabelGap = 8;
constexpr int kSectionGap = 8;
constexpr int kAppBandH = 22;
constexpr int kTitleBandH = 30;
constexpr int kBodyBandH = 22;

struct MarqueeState {
  int scrollPx = 0;
  int lastDrawnPx = -1;
  int32_t scrollCarry = 0;
  uint32_t pauseUntil = 0;
  uint32_t lastScrollMs = 0;
  char lastText[84] = "";
};

struct AlertState {
  bool active = false;
  Screen returnScreen = SCREEN_CLOCK;
  uint32_t hideAtMs = 0;
  char app[20] = "";
  char title[44] = "";
  char body[80] = "";
};

static AlertState alert;
static String layoutKey;
static int notifyAppY = 0;
static int notifyTitleY = 0;
static int notifyBodyY = 0;
static MarqueeState appMarquee;
static MarqueeState titleMarquee;
static MarqueeState bodyMarquee;

static void copyTrunc(char *dst, const size_t n, const char *src) {
  if (!src || n == 0) {
    if (n > 0) {
      dst[0] = '\0';
    }
    return;
  }
  strncpy(dst, src, n - 1);
  dst[n - 1] = '\0';
}

static void applyMarqueeFont(uint8_t font) {
  tft.setTextFont(font);
  tft.setTextSize(1);
}

static int marqueeTextWidth(const char *text, const uint8_t font) {
  if (!text || !text[0]) {
    return 0;
  }
  applyMarqueeFont(font);
  int textW = tft.textWidth(text, font);
  if (textW <= 0) {
    textW = static_cast<int>(strlen(text)) * (font >= 4 ? 14 : 10);
  }
  return textW;
}

static void resetMarquee(MarqueeState &state) {
  state.scrollPx = 0;
  state.lastDrawnPx = -1;
  state.scrollCarry = 0;
  state.pauseUntil = millis() + 800;
  state.lastScrollMs = 0;
  state.lastText[0] = '\0';
}

static void advanceMarqueeScroll(MarqueeState &state, const int textW, const int viewportW) {
  const uint32_t now = millis();
  if (now < state.pauseUntil) {
    return;
  }

  if (state.lastScrollMs == 0) {
    state.lastScrollMs = now;
  }

  uint32_t dt = now - state.lastScrollMs;
  state.lastScrollMs = now;
  if (dt > 80) {
    dt = 80;
  }

  state.scrollCarry += static_cast<int32_t>(dt) * MARQUEE_SCROLL_PX_PER_SEC;
  while (state.scrollCarry >= 1000) {
    state.scrollCarry -= 1000;
    state.scrollPx++;
  }

  const int totalScroll = textW + viewportW;
  if (state.scrollPx >= totalScroll) {
    state.scrollPx = 0;
    state.scrollCarry = 0;
    state.pauseUntil = now + MARQUEE_SCROLL_PAUSE_MS;
    state.lastScrollMs = now;
  }
}

static void drawNotifyMarquee(const char *text, const int vx, const int vy, const int vw, const int vh,
                              const uint8_t font, const uint16_t color, MarqueeState &state) {
  if (!text || !text[0]) {
    return;
  }

  if (strcmp(state.lastText, text) != 0) {
    resetMarquee(state);
  }

  const int textW = marqueeTextWidth(text, font);
  const bool scroll = textW > vw;

  if (scroll) {
    advanceMarqueeScroll(state, textW, vw);
    if (state.scrollPx == state.lastDrawnPx && state.lastText[0] != '\0') {
      return;
    }
    state.lastDrawnPx = state.scrollPx;

    tft.setViewport(vx, vy, vw, vh);
    tft.fillRect(0, 0, vw, vh, COL_EINK_PAPER);
    tft.setTextColor(color, COL_EINK_PAPER);
    applyMarqueeFont(font);
    tft.setTextDatum(ML_DATUM);
    tft.drawString(text, vw - state.scrollPx, vh / 2, font);
    tft.resetViewport();
  } else {
    if (state.lastText[0] != '\0' && strcmp(state.lastText, text) == 0 && state.lastDrawnPx == 0) {
      return;
    }
    state.scrollPx = 0;
    state.scrollCarry = 0;
    state.lastDrawnPx = 0;

    tft.setViewport(vx, vy, vw, vh);
    tft.fillRect(0, 0, vw, vh, COL_EINK_PAPER);
    tft.setTextColor(color, COL_EINK_PAPER);
    applyMarqueeFont(font);
    tft.setTextDatum(MC_DATUM);
    tft.drawString(text, vw / 2, vh / 2, font);
    tft.resetViewport();
  }

  strncpy(state.lastText, text, sizeof(state.lastText) - 1);
  state.lastText[sizeof(state.lastText) - 1] = '\0';
}

static void resetAllMarquees() {
  resetMarquee(appMarquee);
  resetMarquee(titleMarquee);
  resetMarquee(bodyMarquee);
}

static int layoutBlockHeight() {
  int h = 22 + kLabelGap; // "Alert"
  h += kAppBandH + kLabelGap;
  if (alert.title[0]) {
    h += kTitleBandH + kSectionGap;
  }
  if (alert.body[0]) {
    h += kBodyBandH;
  }
  return h;
}

static void drawNotificationLayout() {
  tft.fillScreen(COL_EINK_PAPER);
  tft.drawCircle(kCenterX, 120, 118, COL_EINK_LINE);

  const int blockH = layoutBlockHeight();
  int y = 120 - blockH / 2 + 11;

  tft.setTextDatum(MC_DATUM);
  tft.setTextColor(COL_EINK_INK, COL_EINK_PAPER);
  tft.drawString("Alert", kCenterX, y, 2);
  y += 22 + kLabelGap;

  notifyAppY = y;
  y += kAppBandH + kLabelGap;

  if (alert.title[0]) {
    notifyTitleY = y;
    y += kTitleBandH + kSectionGap;
  } else {
    notifyTitleY = 0;
  }

  if (alert.body[0]) {
    notifyBodyY = y;
  } else {
    notifyBodyY = 0;
  }

  tft.fillRect(kVpX, notifyAppY, kVpW, kAppBandH, COL_EINK_PAPER);
  if (notifyTitleY > 0) {
    tft.fillRect(kVpX, notifyTitleY, kVpW, kTitleBandH, COL_EINK_PAPER);
  }
  if (notifyBodyY > 0) {
    tft.fillRect(kVpX, notifyBodyY, kVpW, kBodyBandH, COL_EINK_PAPER);
  }
}

void notificationShow(const char *app, const char *title, const char *body) {
  if (!alert.active) {
    alert.returnScreen = currentScreen;
  }

  copyTrunc(alert.app, sizeof(alert.app), app && app[0] ? app : "Notification");
  copyTrunc(alert.title, sizeof(alert.title), title ? title : "");
  copyTrunc(alert.body, sizeof(alert.body), body ? body : "");

  alert.active = true;
  alert.hideAtMs = millis() + NOTIFICATION_DISPLAY_MS;
  layoutKey = "";
  resetAllMarquees();

  invalidateAllScreens();
  drawNotificationScreen();
}

void notificationDismiss() {
  if (!alert.active) {
    return;
  }
  alert.active = false;
  currentScreen = alert.returnScreen;
  layoutKey = "";
  resetAllMarquees();
  invalidateAllScreens();

  struct tm timeinfo {};
  if (getLocalTime(&timeinfo)) {
    drawCurrentScreen(timeinfo);
  }
}

void notificationTick() {
  if (!alert.active) {
    return;
  }
  if (static_cast<int32_t>(millis() - alert.hideAtMs) >= 0) {
    notificationDismiss();
  }
}

bool notificationIsActive() { return alert.active; }

void drawNotificationScreen() {
  const String key = String(alert.app) + "|" + alert.title + "|" + alert.body;
  if (key != layoutKey) {
    layoutKey = key;
    resetAllMarquees();
    drawNotificationLayout();
    appMarquee.lastDrawnPx = -1;
    titleMarquee.lastDrawnPx = -1;
    bodyMarquee.lastDrawnPx = -1;
  }

  drawNotifyMarquee(alert.app, kVpX, notifyAppY, kVpW, kAppBandH, 2, COL_EINK_GRAY, appMarquee);

  if (notifyTitleY > 0) {
    drawNotifyMarquee(alert.title, kVpX, notifyTitleY, kVpW, kTitleBandH, 4, COL_EINK_INK,
                      titleMarquee);
  }

  if (notifyBodyY > 0) {
    drawNotifyMarquee(alert.body, kVpX, notifyBodyY, kVpW, kBodyBandH, 2, COL_EINK_GRAY,
                      bodyMarquee);
  }
}
