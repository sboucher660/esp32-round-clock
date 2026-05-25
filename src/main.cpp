#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <Preferences.h>
#include <time.h>
#include <ArduinoJson.h>
#include <TFT_eSPI.h>

#include "config.h"
#include "notifications.h"

#if __has_include("secrets.h")
#include "secrets.h"
#else
#error "Copy include/secrets.h.example to include/secrets.h and set WIFI_SSID / WIFI_PASS"
#endif

#ifndef WIFI_SSID
#error "WIFI_SSID not defined in secrets.h"
#endif

#if defined(SPOTIFY_CLIENT_ID) && defined(SPOTIFY_CLIENT_SECRET) && defined(SPOTIFY_REFRESH_TOKEN)
#define SPOTIFY_ENABLED 1
#else
#define SPOTIFY_ENABLED 0
#endif

TFT_eSPI tft = TFT_eSPI();

// E-ink clock palette (dark gray "paper" + light ink)
static const uint16_t COL_EINK_PAPER = 0x3186;
static const uint16_t COL_EINK_INK = 0xE71C;
static const uint16_t COL_EINK_GRAY = 0x9CD3;
static const uint16_t COL_EINK_LINE = 0x4A69;

static const uint16_t COL_BG = 0x10A2;
static const uint16_t COL_RING = 0x4A69;
static const uint16_t COL_ACCENT = 0x5D1F;
static const uint16_t COL_TEXT = TFT_WHITE;
static const uint16_t COL_DIM = 0x8C71;

struct MarqueeState {
  int scrollPx = 0;
  int lastDrawnPx = -1;
  int32_t scrollCarry = 0;
  uint32_t pauseUntil = 0;
  uint32_t lastScrollMs = 0;
  char lastText[56] = "";
};

static TFT_eSprite spotifyTrackSprite(&tft);
static TFT_eSprite spotifyArtistSprite(&tft);
static bool spotifyMarqueeSpritesOk = false;

Screen currentScreen = SCREEN_CLOCK;

WebServer pageServer(PAGE_HTTP_PORT);
bool pageHttpReady = false;
Preferences rotationPrefs;
uint8_t displayRotation = DISPLAY_ROTATION;

void drawCurrentScreen(const struct tm &timeinfo);
bool initSpotifyMarqueeSprites();
void invalidateAllScreens();

void loadDisplayRotation() {
  rotationPrefs.begin("roundclk", false);
  displayRotation = rotationPrefs.getUChar("rot", DISPLAY_ROTATION) % 4;
}

void saveDisplayRotation() {
  rotationPrefs.putUChar("rot", displayRotation);
}

void applyDisplayRotation() {
  tft.setRotation(displayRotation);
  if (spotifyMarqueeSpritesOk) {
    spotifyTrackSprite.deleteSprite();
    spotifyArtistSprite.deleteSprite();
    spotifyMarqueeSpritesOk = false;
  }
  initSpotifyMarqueeSprites();
  invalidateAllScreens();
}

void rotateDisplayRight() {
  displayRotation = static_cast<uint8_t>((displayRotation + 1) % 4);
  applyDisplayRotation();
  saveDisplayRotation();
}

void rotateDisplayLeft() {
  displayRotation = static_cast<uint8_t>((displayRotation + 3) % 4);
  applyDisplayRotation();
  saveDisplayRotation();
}

struct WeatherData {
  bool valid = false;
  float tempC = 0;
  int weatherCode = 0;
  float windKmh = 0;
  uint32_t updatedMs = 0;
};

struct NetworkData {
  String publicIp;
  uint32_t publicIpUpdatedMs = 0;
  bool fetchingPublic = false;
};

struct SpotifyData {
  bool valid = false;
  bool hasTrack = false;
  bool playing = false;
  char track[56] = "";
  char artist[40] = "";
  uint32_t updatedMs = 0;
};

WeatherData weather;
NetworkData network;
SpotifyData spotify;

#if SPOTIFY_ENABLED
String spotifyAccessToken;
uint32_t spotifyTokenExpiresMs = 0;
#endif

bool wifiReady = false;
bool timeReady = false;
bool fetchingWeather = false;
bool fetchingSpotify = false;

uint32_t lastClockDraw = 0;
uint32_t lastWeatherFetchAttempt = 0;
uint32_t lastNetworkFetchAttempt = 0;
uint32_t lastSpotifyFetchAttempt = 0;
String lastClockKey;
String lastSecShown;
String lastWeatherKey;
String lastNetworkStaticKey;
int lastNetworkBars = -1;
String lastSpotifyStaticKey;
MarqueeState spotifyTrackMarquee;
MarqueeState spotifyArtistMarquee;

uint32_t lastButtonPressMs = 0;

uint32_t lastAutoRotateMs = 0;
bool buttonWasDown = false;

uint32_t lastWifiCheckMs = 0;
uint32_t lastWifiReconnectMs = 0;

void invalidateAllScreens() {
  lastClockKey = "";
  lastSecShown = "";
  lastWeatherKey = "";
  lastNetworkStaticKey = "";
  lastNetworkBars = -1;
  lastSpotifyStaticKey = "";
  spotifyTrackMarquee = MarqueeState{};
  spotifyArtistMarquee = MarqueeState{};
}

void resetMarquee(MarqueeState &state) {
  state.scrollPx = 0;
  state.lastDrawnPx = -1;
  state.scrollCarry = 0;
  state.pauseUntil = millis() + 800;
  state.lastScrollMs = 0;
  state.lastText[0] = '\0';
}

bool initSpotifyMarqueeSprites() {
  if (spotifyMarqueeSpritesOk) {
    return true;
  }
  spotifyMarqueeSpritesOk =
      spotifyTrackSprite.createSprite(200, 28) && spotifyArtistSprite.createSprite(200, 24);
  return spotifyMarqueeSpritesOk;
}

void applyMarqueeFont(TFT_eSPI &gfx, uint8_t font, uint8_t textSize) {
  gfx.setTextFont(font);
  gfx.setTextSize(font == 1 ? textSize : 1);
}

int marqueeCharWidth(uint8_t font, uint8_t textSize = 1) {
  applyMarqueeFont(tft, font, textSize);
  const int w = tft.textWidth("W", font);
  if (w > 0) {
    return w;
  }
  if (font == 1) {
    return 6 * textSize;
  }
  return font >= 4 ? 14 : 10;
}

int marqueeTextWidth(const char *text, uint8_t font, uint8_t textSize = 1) {
  if (!text || text[0] == '\0') {
    return 0;
  }

  applyMarqueeFont(tft, font, textSize);
  const int charW = marqueeCharWidth(font, textSize);
  const int len = static_cast<int>(strlen(text));
  int textW = tft.textWidth(text, font);
  const int estimatedW = len * charW;

  if (textW <= 0 || (len > 2 && textW < charW * 2)) {
    textW = estimatedW;
  }

  return textW;
}

bool marqueeNeedsScroll(const char *text, int viewportW, uint8_t font, uint8_t textSize = 1) {
  return marqueeTextWidth(text, font, textSize) > viewportW;
}

void advanceMarqueeScroll(MarqueeState &state, int textW, int viewportW) {
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

void spotifyDisplayChanged() {
  lastSpotifyStaticKey = "";
  resetMarquee(spotifyTrackMarquee);
  resetMarquee(spotifyArtistMarquee);
}

void truncateDisplay(char *dest, size_t destSize, const char *src) {
  if (destSize < 4) {
    return;
  }
  strncpy(dest, src, destSize - 1);
  dest[destSize - 1] = '\0';
  const size_t maxVisible = destSize - 4;
  if (strlen(dest) > maxVisible) {
    dest[maxVisible] = '\0';
    strcat(dest, "...");
  }
}

void initButtonPins() {
  pinMode(BUTTON_PIN, INPUT_PULLUP);
}

bool isButtonDown() {
  return digitalRead(BUTTON_PIN) == LOW;
}

// One page change per full press+release on GPIO 9 (BOOT).
// Do not hold BOOT during reset — that enters flash mode.
bool buttonPressed() {
  const bool down = isButtonDown();

  if (down && !buttonWasDown && (millis() - lastButtonPressMs) > BUTTON_COOLDOWN_MS) {
    buttonWasDown = true;
    return false;
  }

  if (!down && buttonWasDown) {
    buttonWasDown = false;
    lastButtonPressMs = millis();
    return true;
  }

  if (!down) {
    buttonWasDown = false;
  }

  return false;
}

void cycleScreen() {
  currentScreen = static_cast<Screen>((static_cast<uint8_t>(currentScreen) + 1) % SCREEN_COUNT);
  invalidateAllScreens();
}

void cycleScreenBackward() {
  const uint8_t idx =
      (static_cast<uint8_t>(currentScreen) + SCREEN_COUNT - 1) % SCREEN_COUNT;
  currentScreen = static_cast<Screen>(idx);
  invalidateAllScreens();
}

void applyPageChangeFromRemote() {
  struct tm timeinfo {};
  if (getLocalTime(&timeinfo)) {
    timeReady = true;
  }
  drawCurrentScreen(timeinfo);
}

void handlePageHttp() {
  if (!pageHttpReady) {
    return;
  }
  pageServer.handleClient();
}

void setupPageHttp() {
  if (!wifiReady) {
    return;
  }

  pageServer.on("/next", HTTP_GET, []() {
    cycleScreen();
    applyPageChangeFromRemote();
    pageServer.send(200, "text/plain", "ok\n");
  });
  pageServer.on("/prev", HTTP_GET, []() {
    cycleScreenBackward();
    applyPageChangeFromRemote();
    pageServer.send(200, "text/plain", "ok\n");
  });
  pageServer.on("/rotate/right", HTTP_GET, []() {
    rotateDisplayRight();
    applyPageChangeFromRemote();
    pageServer.send(200, "text/plain", "ok\n");
  });
  pageServer.on("/rotate/left", HTTP_GET, []() {
    rotateDisplayLeft();
    applyPageChangeFromRemote();
    pageServer.send(200, "text/plain", "ok\n");
  });
  pageServer.on("/info", HTTP_GET, []() {
    String body = "{\"ip\":\"" + WiFi.localIP().toString() + "\",\"mdns\":\"" MDNS_HOSTNAME
                   ".local\",\"rotation\":" + String(displayRotation) + "}";
    pageServer.send(200, "application/json", body);
  });

  pageServer.on("/notify", HTTP_POST, []() {
    if (!pageServer.hasArg("plain")) {
      pageServer.send(400, "text/plain", "POST JSON: app, title, body\n");
      return;
    }

    StaticJsonDocument<512> doc;
    const DeserializationError err = deserializeJson(doc, pageServer.arg("plain"));
    if (err) {
      pageServer.send(400, "text/plain", "bad json\n");
      return;
    }

    const char *app = doc["app"] | "Notification";
    const char *title = doc["title"] | "";
    const char *body = doc["body"] | doc["message"] | doc["subtitle"] | "";

    notificationShow(app, title, body);
    pageServer.send(200, "text/plain", "ok\n");
  });

  pageServer.on("/notify", HTTP_GET, []() {
    const String app = pageServer.hasArg("app") ? pageServer.arg("app") : "Notification";
    const String title = pageServer.hasArg("title") ? pageServer.arg("title") : "";
    const String body = pageServer.hasArg("body") ? pageServer.arg("body") : pageServer.arg("message");

    notificationShow(app.c_str(), title.c_str(), body.c_str());
    pageServer.send(200, "text/plain", "ok\n");
  });

  pageServer.begin();
  if (MDNS.begin(MDNS_HOSTNAME)) {
    MDNS.addService("http", "tcp", PAGE_HTTP_PORT);
  }
  pageHttpReady = true;
}

// USB serial from Mac: n/] = next page, p/[ = previous (see scripts/mac_page_control.py)
bool pollSerialCommands() {
  if (!Serial.available()) {
    return false;
  }

  bool changed = false;
  while (Serial.available()) {
    const char c = static_cast<char>(Serial.read());
    switch (c) {
      case 'n':
      case 'N':
      case 'f':
      case 'F':
      case ']':
        cycleScreen();
        changed = true;
        break;
      case 'p':
      case 'P':
      case 'b':
      case 'B':
      case '[':
        cycleScreenBackward();
        changed = true;
        break;
      case '>':
      case '.':
        rotateDisplayRight();
        changed = true;
        break;
      case '<':
      case ',':
        rotateDisplayLeft();
        changed = true;
        break;
      default:
        break;
    }
  }
  return changed;
}

const char *weatherDescription(int code) {
  if (code == 0) return "Clear";
  if (code <= 3) return "Cloudy";
  if (code <= 48) return "Fog";
  if (code <= 57) return "Drizzle";
  if (code <= 67) return "Rain";
  if (code <= 77) return "Snow";
  if (code <= 82) return "Showers";
  if (code <= 86) return "Snow";
  if (code <= 99) return "Storm";
  return "Unknown";
}

enum WeatherIcon : uint8_t { ICON_SUN, ICON_CLOUD, ICON_RAIN, ICON_SNOW, ICON_STORM, ICON_FOG };

WeatherIcon weatherIconType(int code) {
  if (code == 0) return ICON_SUN;
  if (code <= 3) return ICON_CLOUD;
  if (code <= 48) return ICON_FOG;
  if (code <= 57) return ICON_RAIN;
  if (code <= 67) return ICON_RAIN;
  if (code <= 77) return ICON_SNOW;
  if (code <= 82) return ICON_RAIN;
  if (code <= 86) return ICON_SNOW;
  if (code <= 99) return ICON_STORM;
  return ICON_CLOUD;
}

void drawScreenDots() {
  const int y = 224;
  const int spacing = 14;
  const int cx = 120 - (spacing * (SCREEN_COUNT - 1)) / 2;
  const bool eink = true;
  const uint16_t active = eink ? COL_EINK_INK : COL_ACCENT;
  const uint16_t inactive = eink ? COL_EINK_GRAY : COL_DIM;
  const uint16_t bg = eink ? COL_EINK_PAPER : COL_BG;

  for (uint8_t i = 0; i < SCREEN_COUNT; i++) {
    const int x = cx + i * spacing;
    if (i == static_cast<uint8_t>(currentScreen)) {
      tft.fillCircle(x, y, 4, active);
    } else {
      tft.fillCircle(x, y, 3, bg);
      tft.drawCircle(x, y, 3, inactive);
    }
  }
}

void drawStatusMessage(const char *line1, const char *line2 = nullptr) {
  tft.fillScreen(COL_BG);
  tft.setTextDatum(MC_DATUM);
  tft.setTextColor(COL_ACCENT, COL_BG);
  tft.drawString(line1, 120, 108, 4);
  if (line2) {
    tft.setTextColor(COL_DIM, COL_BG);
    tft.drawString(line2, 120, 148, 2);
  }
}

#if __has_include("apple_logo.h")
#include "apple_logo.h"
#define HAS_BOOT_LOGO_IMAGE 1
#else
#define HAS_BOOT_LOGO_IMAGE 0
#endif

void drawAppleLogoFallback(int cx, int cy) {
  const uint16_t ink = COL_EINK_INK;
  const uint16_t paper = COL_EINK_PAPER;

  tft.fillCircle(cx - 11, cy + 6, 28, ink);
  tft.fillCircle(cx + 11, cy + 6, 28, ink);
  tft.fillRect(cx - 30, cy - 10, 60, 40, ink);
  tft.fillCircle(cx, cy - 22, 10, paper);
  tft.fillCircle(cx + 27, cy + 14, 13, paper);
  tft.fillEllipse(cx - 10, cy - 36, 9, 15, ink);
  tft.fillTriangle(cx - 20, cy - 30, cx - 2, cy - 48, cx - 2, cy - 26, ink);
}

void drawBootSplash() {
#if HAS_BOOT_LOGO_IMAGE
  // Full-frame bitmap: paper background + centered logo (see scripts/png_to_logo_h.py)
  tft.setSwapBytes(true);
  tft.pushImage(0, 0, APPLE_LOGO_WIDTH, APPLE_LOGO_HEIGHT, apple_logo);
  tft.setSwapBytes(false);
#else
  tft.fillScreen(COL_EINK_PAPER);
  drawAppleLogoFallback(120, 112);
#endif

  tft.drawCircle(120, 120, 118, COL_EINK_LINE);
  tft.drawCircle(120, 120, 117, COL_EINK_LINE);
}

// --- E-ink style clock (page 1) ---
static const int CLOCK_WEEKDAY_Y = 76;
static const int CLOCK_DATE_Y = 96;
static const int CLOCK_TIME_Y = 142;

void drawClockTimeRow(const char *timeBuf, const char *secLine, bool redrawTime) {
  const uint8_t timeFont = 7;

  tft.setTextFont(timeFont);
  const int wTime = tft.textWidth(timeBuf, timeFont);
  tft.setTextFont(4);
  const int wSec = tft.textWidth(secLine, 4);
  const int totalW = wTime + wSec;
  const int x0 = 120 - totalW / 2;
  const int y = CLOCK_TIME_Y;

  if (redrawTime) {
    tft.fillRect(x0 - 8, y - 28, totalW + 16, 36, COL_EINK_PAPER);
  } else {
    tft.fillRect(x0 + wTime - 4, y - 28, wSec + 12, 36, COL_EINK_PAPER);
  }

  if (redrawTime) {
    tft.setTextDatum(ML_DATUM);
    tft.setTextColor(COL_EINK_INK, COL_EINK_PAPER);
    tft.setTextFont(timeFont);
    tft.drawString(timeBuf, x0, y, timeFont);
  }

  tft.setTextDatum(ML_DATUM);
  tft.setTextColor(COL_EINK_GRAY, COL_EINK_PAPER);
  tft.setTextFont(4);
  tft.drawString(secLine, x0 + wTime, y + 2, 4);
}

void drawClockScreen(const struct tm &timeinfo) {
  char timeBuf[16];
  char dateBuf[32];
  char secBuf[8];
  strftime(timeBuf, sizeof(timeBuf), "%H:%M", &timeinfo);
  strftime(dateBuf, sizeof(dateBuf), "%A", &timeinfo);
  char dayBuf[16];
  strftime(dayBuf, sizeof(dayBuf), "%d %B", &timeinfo);
  snprintf(secBuf, sizeof(secBuf), "%02d", timeinfo.tm_sec);

  const String clockKey = String(timeBuf) + dateBuf + dayBuf + (timeReady ? "t" : "f");

  if (clockKey == lastClockKey) {
    return;
  }
  lastClockKey = clockKey;
  lastSecShown = "";

  tft.fillScreen(COL_EINK_PAPER);

  // Soft round frame (like an e-reader bezel)
  tft.drawCircle(120, 120, 118, COL_EINK_LINE);
  tft.drawCircle(120, 120, 117, COL_EINK_LINE);

  tft.setTextDatum(MC_DATUM);

  tft.setTextColor(COL_EINK_GRAY, COL_EINK_PAPER);
  tft.drawString(dateBuf, 120, CLOCK_WEEKDAY_Y, 2);

  tft.setTextColor(COL_EINK_INK, COL_EINK_PAPER);
  tft.drawString(dayBuf, 120, CLOCK_DATE_Y, 4);

  if (!timeReady) {
    tft.setTextColor(COL_EINK_GRAY, COL_EINK_PAPER);
    tft.drawString("syncing time", 120, CLOCK_TIME_Y, 2);
  } else {
    char secLine[8];
    snprintf(secLine, sizeof(secLine), ":%02d", timeinfo.tm_sec);
    drawClockTimeRow(timeBuf, secLine, true);
    lastSecShown = secLine;
  }

  drawScreenDots();
}

void drawClockSeconds(const struct tm &timeinfo) {
  if (!timeReady) {
    return;
  }

  char timeBuf[16];
  strftime(timeBuf, sizeof(timeBuf), "%H:%M", &timeinfo);

  char secLine[8];
  snprintf(secLine, sizeof(secLine), ":%02d", timeinfo.tm_sec);
  if (String(secLine) == lastSecShown) {
    return;
  }
  lastSecShown = secLine;

  drawClockTimeRow(timeBuf, secLine, false);
}

// --- Weather icons (e-ink style) ---
void drawSun(int cx, int cy, int r) {
  tft.drawCircle(cx, cy, r, COL_EINK_INK);
  tft.fillCircle(cx, cy, r - 2, COL_EINK_GRAY);
  for (int i = 0; i < 8; i++) {
    const float a = i * 45.0f * DEG_TO_RAD;
    const int x0 = cx + cos(a) * (r + 6);
    const int y0 = cy + sin(a) * (r + 6);
    const int x1 = cx + cos(a) * (r + 14);
    const int y1 = cy + sin(a) * (r + 14);
    tft.drawLine(x0, y0, x1, y1, COL_EINK_INK);
  }
}

void drawCloud(int cx, int cy, int scale, uint16_t color) {
  const int s = scale;
  tft.fillCircle(cx - s, cy, s, color);
  tft.fillCircle(cx + s, cy, s, color);
  tft.fillCircle(cx, cy - s / 2, s + 2, color);
  tft.fillRect(cx - s * 2, cy, s * 4 + 2, s + 2, color);
}

void drawWeatherIcon(int code, int cx, int cy) {
  const WeatherIcon type = weatherIconType(code);
  switch (type) {
    case ICON_SUN:
      drawSun(cx, cy, 20);
      break;
    case ICON_CLOUD:
      drawCloud(cx, cy, 16, COL_EINK_GRAY);
      break;
    case ICON_FOG:
      for (int i = 0; i < 4; i++) {
        tft.drawLine(cx - 34, cy - 6 + i * 9, cx + 34, cy - 6 + i * 9, COL_EINK_GRAY);
      }
      break;
    case ICON_RAIN:
      drawCloud(cx, cy - 16, 14, COL_EINK_GRAY);
      for (int i = -2; i <= 2; i++) {
        tft.drawLine(cx + i * 11 - 5, cy + 6, cx + i * 11 - 8, cy + 24, COL_EINK_INK);
      }
      break;
    case ICON_SNOW:
      drawCloud(cx, cy - 16, 14, COL_EINK_GRAY);
      for (int i = -2; i <= 2; i++) {
        const int sx = cx + i * 12;
        const int sy = cy + 18;
        tft.drawLine(sx, sy - 4, sx, sy + 4, COL_EINK_INK);
        tft.drawLine(sx - 4, sy, sx + 4, sy, COL_EINK_INK);
      }
      break;
    case ICON_STORM:
      drawCloud(cx, cy - 18, 15, COL_EINK_GRAY);
      tft.drawLine(cx + 2, cy + 4, cx - 6, cy + 22, COL_EINK_INK);
      tft.drawLine(cx - 6, cy + 22, cx + 10, cy + 22, COL_EINK_INK);
      tft.drawLine(cx + 10, cy + 22, cx + 2, cy + 4, COL_EINK_INK);
      break;
    default:
      drawCloud(cx, cy, 16, COL_EINK_GRAY);
      break;
  }
}

void drawWeatherScreen() {
  String key;
  if (!wifiReady) {
    key = "nowifi";
  } else if (fetchingWeather) {
    key = "loading";
  } else if (!weather.valid) {
    key = "nodata";
  } else {
    key = String(weather.tempC, 1) + weather.weatherCode + weather.windKmh;
  }

  if (key == lastWeatherKey) {
    return;
  }
  lastWeatherKey = key;

  tft.fillScreen(COL_EINK_PAPER);
  tft.drawCircle(120, 120, 118, COL_EINK_LINE);
  tft.drawCircle(120, 120, 117, COL_EINK_LINE);

  tft.setTextDatum(MC_DATUM);

  if (weather.valid) {
    drawWeatherIcon(weather.weatherCode, 120, 82);

    char tempBuf[16];
    snprintf(tempBuf, sizeof(tempBuf), "%.0f C", weather.tempC);
    tft.setTextColor(COL_EINK_INK, COL_EINK_PAPER);
    tft.drawString(tempBuf, 120, 132, 7);

    tft.setTextColor(COL_EINK_GRAY, COL_EINK_PAPER);
    tft.drawString(weatherDescription(weather.weatherCode), 120, 162, 2);

    char windBuf[24];
    snprintf(windBuf, sizeof(windBuf), "%.0f km/h wind", weather.windKmh);
    tft.setTextColor(COL_EINK_GRAY, COL_EINK_PAPER);
    tft.drawString(windBuf, 120, 182, 2);
  } else {
    tft.setTextColor(COL_EINK_GRAY, COL_EINK_PAPER);
    const char *msg = !wifiReady ? "no wi-fi" : fetchingWeather ? "updating" : "no data";
    tft.drawString(msg, 120, 120, 4);
  }

  drawScreenDots();
}

// --- Network (page 4) ---
int wifiBarsFromRssi(int rssi) {
  if (rssi >= -50) return 5;
  if (rssi >= -60) return 4;
  if (rssi >= -70) return 3;
  if (rssi >= -80) return 2;
  if (rssi >= -90) return 1;
  return 0;
}

void drawWifiBars(int cx, int y, int bars, int rssi) {
  const int spacing = 12;
  const int startX = cx - (5 * spacing) / 2 + 4;

  for (int i = 0; i < 5; i++) {
    const int h = 8 + i * 7;
    const int bx = startX + i * spacing;
    const int by = y + 28 - h;
    if (i < bars) {
      tft.fillRoundRect(bx, by, 9, h, 2, COL_EINK_INK);
    } else {
      tft.fillRoundRect(bx, by, 9, h, 2, COL_EINK_PAPER);
      tft.drawRoundRect(bx, by, 9, h, 2, COL_EINK_GRAY);
    }
  }

  char rssiBuf[16];
  snprintf(rssiBuf, sizeof(rssiBuf), "%d dBm", rssi);
  tft.setTextDatum(MC_DATUM);
  tft.setTextColor(COL_EINK_GRAY, COL_EINK_PAPER);
  tft.drawString(rssiBuf, cx, y + 40, 2);
}

void drawNetworkScreen() {
  const int rssi = wifiReady ? WiFi.RSSI() : -100;
  const int bars = wifiBarsFromRssi(rssi);
  const String lanIp = wifiReady ? WiFi.localIP().toString() : String("--");
  const String wanIp =
      network.publicIp.length() > 0 ? network.publicIp
                                    : (network.fetchingPublic ? "..." : "--");

  const String staticKey = lanIp + "|" + wanIp + "|" + (wifiReady ? "1" : "0");
  const bool fullRedraw = staticKey != lastNetworkStaticKey;
  if (fullRedraw) {
    lastNetworkStaticKey = staticKey;
    lastNetworkBars = -1;

    tft.fillScreen(COL_EINK_PAPER);
    tft.drawCircle(120, 120, 118, COL_EINK_LINE);
    tft.drawCircle(120, 120, 117, COL_EINK_LINE);

    tft.setTextDatum(MC_DATUM);

    if (wifiReady) {
      tft.setTextColor(COL_EINK_GRAY, COL_EINK_PAPER);
      tft.drawString("LAN", 120, 118, 2);
      tft.setTextColor(COL_EINK_INK, COL_EINK_PAPER);
      tft.drawString(lanIp, 120, 140, 4);

      tft.setTextColor(COL_EINK_GRAY, COL_EINK_PAPER);
      tft.drawString("WAN", 120, 168, 2);
      tft.setTextColor(COL_EINK_INK, COL_EINK_PAPER);
      tft.drawString(wanIp, 120, 190, 2);
    } else {
      tft.setTextColor(COL_EINK_GRAY, COL_EINK_PAPER);
      tft.drawString("offline", 120, 120, 4);
    }

    drawScreenDots();
  }

  if (!wifiReady) {
    return;
  }

  if (fullRedraw || bars != lastNetworkBars) {
    lastNetworkBars = bars;
    tft.fillRect(58, 28, 124, 72, COL_EINK_PAPER);
    drawWifiBars(120, 52, bars, rssi);
  }
}

// --- Spotify (page 3) ---
void drawSpotifyBars(int cx, int cy, bool playing) {
  const int spacing = 14;
  const int startX = cx - (4 * spacing) / 2 + 6;
  const int heights[4] = {10, 18, 14, 22};

  for (int i = 0; i < 4; i++) {
    const int h = playing ? heights[i] : 8;
    const int bx = startX + i * spacing;
    const int by = cy + 20 - h;
    if (playing) {
      tft.fillRoundRect(bx, by, 8, h, 2, COL_EINK_INK);
    } else {
      tft.fillRoundRect(bx, by, 8, h, 2, COL_EINK_PAPER);
      tft.drawRoundRect(bx, by, 8, h, 2, COL_EINK_GRAY);
    }
  }
}

void drawSpotifyScreen() {
  String key;
  if (!wifiReady) {
    key = "nowifi";
  } else if (!SPOTIFY_ENABLED) {
    key = "noconfig";
  } else if (fetchingSpotify) {
    key = "loading";
  } else if (!spotify.valid) {
    key = "nodata";
  } else if (!spotify.hasTrack) {
    key = "idle";
  } else {
    key = String(spotify.artist) + "|" + (spotify.playing ? "1" : "0");
  }

  if (key == lastSpotifyStaticKey) {
    return;
  }
  lastSpotifyStaticKey = key;
  if (spotify.hasTrack) {
    resetMarquee(spotifyTrackMarquee);
    resetMarquee(spotifyArtistMarquee);
  } else {
    spotifyTrackMarquee.lastText[0] = '\0';
    spotifyArtistMarquee.lastText[0] = '\0';
  }

  tft.fillScreen(COL_EINK_PAPER);
  tft.drawCircle(120, 120, 118, COL_EINK_LINE);
  tft.drawCircle(120, 120, 117, COL_EINK_LINE);
  tft.setTextDatum(MC_DATUM);

  if (!wifiReady) {
    tft.setTextColor(COL_EINK_GRAY, COL_EINK_PAPER);
    tft.drawString("no wi-fi", 120, 120, 4);
  } else if (!SPOTIFY_ENABLED) {
    tft.setTextColor(COL_EINK_GRAY, COL_EINK_PAPER);
    tft.drawString("spotify", 120, 100, 2);
    tft.drawString("add keys in", 120, 128, 2);
    tft.drawString("secrets.h", 120, 148, 2);
  } else if (fetchingSpotify) {
    tft.setTextColor(COL_EINK_GRAY, COL_EINK_PAPER);
    tft.drawString("updating", 120, 120, 4);
  } else if (!spotify.valid) {
    tft.setTextColor(COL_EINK_GRAY, COL_EINK_PAPER);
    tft.drawString("no data", 120, 120, 4);
  } else if (!spotify.hasTrack) {
    drawSpotifyBars(120, 72, false);
    tft.setTextColor(COL_EINK_GRAY, COL_EINK_PAPER);
    tft.drawString("spotify", 120, 108, 2);
    tft.setTextColor(COL_EINK_INK, COL_EINK_PAPER);
    tft.drawString("nothing playing", 120, 140, 4);
  } else {
    drawSpotifyBars(120, 58, spotify.playing);

    tft.setTextColor(COL_EINK_GRAY, COL_EINK_PAPER);
    tft.drawString("spotify", 120, 96, 2);

    tft.fillRect(20, 112, 200, 28, COL_EINK_PAPER);
    tft.fillRect(20, 149, 200, 24, COL_EINK_PAPER);

    tft.setTextColor(COL_EINK_INK, COL_EINK_PAPER);
    tft.drawString(spotify.playing ? "playing" : "paused", 120, 198, 2);
  }

  drawScreenDots();
}

void drawMarqueeLine(const char *text, int vx, int vy, int vw, int vh, uint8_t font,
                     uint16_t color, MarqueeState &state, TFT_eSprite &sprite,
                     uint8_t textSize = 1) {
  if (!text || text[0] == '\0') {
    return;
  }

  if (strcmp(state.lastText, text) != 0) {
    state.scrollPx = 0;
    state.lastDrawnPx = -1;
    state.scrollCarry = 0;
    state.pauseUntil = millis() + 800;
    state.lastScrollMs = 0;
    state.lastText[0] = '\0';
  }

  const int textW = marqueeTextWidth(text, font, textSize);
  const bool scroll = textW > vw;

  if (scroll) {
    advanceMarqueeScroll(state, textW, vw);

    if (state.scrollPx == state.lastDrawnPx && state.lastText[0] != '\0') {
      return;
    }
    state.lastDrawnPx = state.scrollPx;

    if (spotifyMarqueeSpritesOk) {
      sprite.fillSprite(COL_EINK_PAPER);
      sprite.setTextColor(color, COL_EINK_PAPER);
      applyMarqueeFont(sprite, font, textSize);
      sprite.setTextDatum(ML_DATUM);
      sprite.drawString(text, vw - state.scrollPx, vh / 2, font);
      sprite.pushSprite(vx, vy);
    } else {
      tft.setViewport(vx, vy, vw, vh);
      tft.fillRect(0, 0, vw, vh, COL_EINK_PAPER);
      tft.setTextColor(color, COL_EINK_PAPER);
      applyMarqueeFont(tft, font, textSize);
      tft.setTextDatum(ML_DATUM);
      tft.drawString(text, vw - state.scrollPx, vh / 2, font);
      tft.resetViewport();
    }
  } else {
    state.scrollPx = 0;
    state.scrollCarry = 0;
    if (state.lastText[0] != '\0' && strcmp(state.lastText, text) == 0) {
      return;
    }
    state.lastDrawnPx = 0;

    if (spotifyMarqueeSpritesOk) {
      sprite.fillSprite(COL_EINK_PAPER);
      sprite.setTextColor(color, COL_EINK_PAPER);
      applyMarqueeFont(sprite, font, textSize);
      sprite.setTextDatum(MC_DATUM);
      sprite.drawString(text, vw / 2, vh / 2, font);
      sprite.pushSprite(vx, vy);
    } else {
      tft.setViewport(vx, vy, vw, vh);
      tft.fillRect(0, 0, vw, vh, COL_EINK_PAPER);
      tft.setTextColor(color, COL_EINK_PAPER);
      applyMarqueeFont(tft, font, textSize);
      tft.setTextDatum(MC_DATUM);
      tft.drawString(text, vw / 2, vh / 2, font);
      tft.resetViewport();
    }
  }

  strncpy(state.lastText, text, sizeof(state.lastText) - 1);
  state.lastText[sizeof(state.lastText) - 1] = '\0';
}

void drawSpotifyMarquees() {
  if (!spotify.hasTrack) {
    return;
  }

  drawMarqueeLine(spotify.track, 20, 112, 200, 28, 4, COL_EINK_INK, spotifyTrackMarquee,
                  spotifyTrackSprite);
  drawMarqueeLine(spotify.artist, 20, 149, 200, 24, 4, COL_EINK_GRAY, spotifyArtistMarquee,
                  spotifyArtistSprite);
}

#if SPOTIFY_ENABLED
bool refreshSpotifyAccessToken() {
  if (spotifyAccessToken.length() > 0 && millis() < spotifyTokenExpiresMs - 60000UL) {
    return true;
  }

  WiFiClientSecure client;
  client.setInsecure();

  HTTPClient http;
  http.setReuse(false);
  http.setTimeout(15000);
  if (!http.begin(client, "https://accounts.spotify.com/api/token")) {
    return false;
  }

  http.setAuthorization(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET);
  http.addHeader("Content-Type", "application/x-www-form-urlencoded");

  String body = String("grant_type=refresh_token&refresh_token=") + SPOTIFY_REFRESH_TOKEN;
  const int code = http.POST(body);
  if (code != HTTP_CODE_OK) {
    http.end();
    spotifyAccessToken = "";
    return false;
  }

  const String payload = http.getString();
  http.end();

  StaticJsonDocument<768> doc;
  if (deserializeJson(doc, payload)) {
    return false;
  }

  const char *token = doc["access_token"] | "";
  if (strlen(token) < 8) {
    return false;
  }

  spotifyAccessToken = token;
  const int expiresIn = doc["expires_in"] | 3600;
  spotifyTokenExpiresMs = millis() + static_cast<uint32_t>(expiresIn) * 1000UL;
  return true;
}

bool fetchSpotifyNowPlaying() {
  if (!wifiReady) {
    return false;
  }
  if (!refreshSpotifyAccessToken()) {
    return false;
  }

  WiFiClientSecure client;
  client.setInsecure();

  HTTPClient http;
  http.setReuse(false);
  http.setTimeout(15000);
  if (!http.begin(client, "https://api.spotify.com/v1/me/player/currently-playing")) {
    return false;
  }

  http.addHeader("Authorization", "Bearer " + spotifyAccessToken);
  const int code = http.GET();
  const String payload = http.getString();
  http.end();

  if (code == 401) {
    spotifyAccessToken = "";
    spotifyTokenExpiresMs = 0;
    return false;
  }

  if (code == 204) {
    const bool changed =
        spotify.hasTrack || spotify.playing || spotify.track[0] != '\0';
    spotify.hasTrack = false;
    spotify.playing = false;
    spotify.track[0] = '\0';
    spotify.artist[0] = '\0';
    spotify.valid = true;
    spotify.updatedMs = millis();
    if (changed) {
      spotifyDisplayChanged();
    }
    return true;
  }

  if (code != HTTP_CODE_OK || payload.length() < 10) {
    return false;
  }

  StaticJsonDocument<3072> doc;
  if (deserializeJson(doc, payload)) {
    return false;
  }

  char nextTrack[56] = "";
  char nextArtist[40] = "";
  bool nextHasTrack = false;
  bool nextPlaying = false;

  JsonObject item = doc["item"];
  if (!item.isNull()) {
    const char *title = item["name"] | "";
    const char *artist = "";
    JsonArray artists = item["artists"];
    if (!artists.isNull() && artists.size() > 0) {
      artist = artists[0]["name"] | "";
    }
    strncpy(nextTrack, title, sizeof(nextTrack) - 1);
    strncpy(nextArtist, artist, sizeof(nextArtist) - 1);
    nextHasTrack = nextTrack[0] != '\0';
    nextPlaying = doc["is_playing"] | false;
  }

  const bool changed = nextHasTrack != spotify.hasTrack || nextPlaying != spotify.playing ||
                       strcmp(nextTrack, spotify.track) != 0 ||
                       strcmp(nextArtist, spotify.artist) != 0;

  strncpy(spotify.track, nextTrack, sizeof(spotify.track) - 1);
  spotify.track[sizeof(spotify.track) - 1] = '\0';
  strncpy(spotify.artist, nextArtist, sizeof(spotify.artist) - 1);
  spotify.artist[sizeof(spotify.artist) - 1] = '\0';
  spotify.hasTrack = nextHasTrack;
  spotify.playing = nextPlaying;
  spotify.valid = true;
  spotify.updatedMs = millis();

  if (changed) {
    spotifyDisplayChanged();
  }
  return true;
}
#else
bool fetchSpotifyNowPlaying() {
  return false;
}
#endif

bool fetchWeather() {
  if (!wifiReady) {
    return false;
  }

  WiFiClientSecure client;
  client.setInsecure();

  char url[280];
  snprintf(url, sizeof(url),
           "https://api.open-meteo.com/v1/forecast?latitude=%.4f&longitude=%.4f"
           "&current=temperature_2m,weather_code,wind_speed_10m&timezone=auto",
           WEATHER_LAT, WEATHER_LON);

  HTTPClient http;
  http.setReuse(false);
  http.setTimeout(20000);
  if (!http.begin(client, url)) {
    return false;
  }

  const int code = http.GET();
  if (code != HTTP_CODE_OK) {
    http.end();
    return false;
  }

  const String payload = http.getString();
  http.end();

  if (payload.length() < 20) {
    return false;
  }

  StaticJsonDocument<2048> doc;
  const DeserializationError err = deserializeJson(doc, payload);
  if (err) {
    return false;
  }

  JsonObject current = doc["current"];
  if (current.isNull()) {
    return false;
  }

  weather.tempC = current["temperature_2m"] | 0.0f;
  weather.weatherCode = current["weather_code"] | 0;
  weather.windKmh = current["wind_speed_10m"] | 0.0f;
  weather.valid = true;
  weather.updatedMs = millis();
  lastWeatherKey = "";
  return true;
}

bool fetchPublicIp() {
  if (!wifiReady) return false;

  WiFiClientSecure client;
  client.setInsecure();

  HTTPClient http;
  http.setTimeout(10000);
  if (!http.begin(client, "https://api.ipify.org")) return false;

  const int code = http.GET();
  if (code != HTTP_CODE_OK) {
    http.end();
    return false;
  }

  String ip = http.getString();
  http.end();
  ip.trim();
  if (ip.length() < 7) return false;

  network.publicIp = ip;
  network.publicIpUpdatedMs = millis();
  lastNetworkStaticKey = "";
  lastNetworkBars = -1;
  return true;
}

bool isWiFiUp() {
  return WiFi.status() == WL_CONNECTED && WiFi.localIP() != IPAddress(static_cast<uint32_t>(0));
}

void configureWiFiStack() {
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.setSleep(false);
}

void onWiFiRestored() {
  configTzTime(TIMEZONE, "pool.ntp.org", "time.nist.gov");
  lastWeatherFetchAttempt = 0;
  lastNetworkFetchAttempt = 0;
  lastSpotifyFetchAttempt = 0;
  network.publicIp = "";
  invalidateAllScreens();
#if SPOTIFY_ENABLED
  spotifyAccessToken = "";
  spotifyTokenExpiresMs = 0;
#endif
  setupPageHttp();
}

void onWiFiLost() {
  wifiReady = false;
  invalidateAllScreens();
#if SPOTIFY_ENABLED
  spotifyAccessToken = "";
  spotifyTokenExpiresMs = 0;
#endif
}

void maintainWiFi() {
  const uint32_t now = millis();
  if (now - lastWifiCheckMs < WIFI_CHECK_MS) {
    return;
  }
  lastWifiCheckMs = now;

  if (isWiFiUp()) {
    if (!wifiReady) {
      wifiReady = true;
      onWiFiRestored();
    }
    return;
  }

  if (wifiReady) {
    onWiFiLost();
    lastWifiReconnectMs = 0;
  }

  if (now - lastWifiReconnectMs < WIFI_RECONNECT_MS) {
    return;
  }
  lastWifiReconnectMs = now;

  if (WiFi.status() == WL_CONNECTED) {
    WiFi.disconnect(false);
  }
  WiFi.begin(WIFI_SSID, WIFI_PASS);
}

void presentFirstScreen() {
  struct tm timeinfo {};
  for (int i = 0; i < 40 && !timeReady; i++) {
    if (getLocalTime(&timeinfo)) {
      timeReady = true;
      break;
    }
    delay(250);
  }

  invalidateAllScreens();
  drawClockScreen(timeinfo);
}

void connectWiFi() {
  configureWiFiStack();
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  const uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - start) < 20000) {
    if (pollSerialCommands()) {
      presentFirstScreen();
    }
    delay(250);
  }

  wifiReady = isWiFiUp();
  if (!wifiReady) {
    drawStatusMessage("Wi-Fi failed", "Check secrets.h");
    return;
  }

  configTzTime(TIMEZONE, "pool.ntp.org", "time.nist.gov");

  struct tm timeinfo {};
  for (int i = 0; i < 20; i++) {
    if (getLocalTime(&timeinfo)) {
      timeReady = true;
      break;
    }
    delay(500);
  }

  fetchingWeather = true;
  fetchWeather();
  fetchingWeather = false;

  network.fetchingPublic = true;
  fetchPublicIp();
  network.fetchingPublic = false;

#if SPOTIFY_ENABLED
  fetchingSpotify = true;
  fetchSpotifyNowPlaying();
  fetchingSpotify = false;
#endif

  invalidateAllScreens();
  setupPageHttp();
}

void drawCurrentScreen(const struct tm &timeinfo) {
  if (notificationIsActive()) {
    drawNotificationScreen();
    return;
  }

  invalidateAllScreens();
  switch (currentScreen) {
    case SCREEN_CLOCK:
      drawClockScreen(timeinfo);
      break;
    case SCREEN_WEATHER:
      drawWeatherScreen();
      break;
    case SCREEN_NETWORK:
      drawNetworkScreen();
      break;
    case SCREEN_SPOTIFY:
      drawSpotifyScreen();
      break;
    default:
      break;
  }
}

void setup() {
#if ARDUINO_USB_CDC_ON_BOOT
  Serial.begin(115200);
  delay(500);
#endif

  initButtonPins();
  pinMode(TFT_BL, OUTPUT);
  digitalWrite(TFT_BL, TFT_BACKLIGHT_ON);

  tft.init();
  loadDisplayRotation();
  tft.setRotation(displayRotation);
  tft.fillScreen(COL_EINK_PAPER);
  initSpotifyMarqueeSprites();

  drawBootSplash();
  connectWiFi();
  if (wifiReady) {
    presentFirstScreen();
  }
  lastAutoRotateMs = millis();
}

void loop() {
  maintainWiFi();
  handlePageHttp();
  notificationTick();

  struct tm timeinfo {};
  if (getLocalTime(&timeinfo)) {
    timeReady = true;
  }

  bool changedPage = false;
  if (buttonPressed()) {
    if (notificationIsActive()) {
      notificationDismiss();
    } else {
      cycleScreen();
    }
    changedPage = true;
  }
  if (pollSerialCommands()) {
    changedPage = true;
  }

#if AUTO_ROTATE_MS > 0
  if (!changedPage && !notificationIsActive() &&
      (millis() - lastAutoRotateMs) >= AUTO_ROTATE_MS) {
    lastAutoRotateMs = millis();
    cycleScreen();
    changedPage = true;
  }
#endif

  if (changedPage) {
    drawCurrentScreen(timeinfo);
  }

  // Fetch weather on boot failure, then refresh periodically
  if (wifiReady && (millis() - lastWeatherFetchAttempt) > 5000) {
    const bool needWeather =
        !weather.valid || ((millis() - weather.updatedMs) > WEATHER_REFRESH_MS);
    if (needWeather) {
      lastWeatherFetchAttempt = millis();
      fetchingWeather = true;
      fetchWeather();
      fetchingWeather = false;
    }
  }

  if (wifiReady &&
      (network.publicIp.length() == 0 ||
       (millis() - network.publicIpUpdatedMs) > NETWORK_REFRESH_MS) &&
      (millis() - lastNetworkFetchAttempt) > 8000 && !network.fetchingPublic) {
    lastNetworkFetchAttempt = millis();
    network.fetchingPublic = true;
    fetchPublicIp();
    network.fetchingPublic = false;
  }

#if SPOTIFY_ENABLED
  if (wifiReady && (millis() - lastSpotifyFetchAttempt) > SPOTIFY_REFRESH_MS) {
    lastSpotifyFetchAttempt = millis();
    fetchingSpotify = true;
    fetchSpotifyNowPlaying();
    fetchingSpotify = false;
  }
#endif

  if (notificationIsActive()) {
    drawNotificationScreen();
  } else {
    switch (currentScreen) {
      case SCREEN_CLOCK:
        if (timeReady) {
          drawClockScreen(timeinfo);
          drawClockSeconds(timeinfo);
        } else if ((millis() - lastClockDraw) > 1000) {
          lastClockDraw = millis();
          drawBootSplash();
        }
        break;
      case SCREEN_WEATHER:
        drawWeatherScreen();
        break;
      case SCREEN_SPOTIFY:
        drawSpotifyScreen();
        if (spotify.hasTrack && spotify.valid) {
          drawSpotifyMarquees();
        }
        break;
      case SCREEN_NETWORK:
        drawNetworkScreen();
        break;
      default:
        break;
    }
  }

  delay(20);
}
