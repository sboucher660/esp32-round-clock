#pragma once

#include "config.h"

struct tm;

// Live alert overlay (not in BOOT page cycle). Shows 15s then returns to prior page.
void notificationShow(const char *app, const char *title, const char *body);
void notificationTick();
bool notificationIsActive();
void notificationDismiss();

void drawNotificationScreen();
