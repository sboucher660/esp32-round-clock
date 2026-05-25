#!/bin/zsh
# Karabiner shell_command target (survives reboot; uses auto port detect).
DIR="${0:A:h}"
exec "$DIR/send-page.sh" next
