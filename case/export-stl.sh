#!/bin/bash
set -e
cd "$(dirname "$0")"
mkdir -p stl
for p in body back; do
  echo "Exporting mini-mac-$p.stl ..."
  openscad -D "part=\"$p\"" -o "stl/mini-mac-$p.stl" mini-mac.scad
done
echo "Done: stl/mini-mac-body.stl + stl/mini-mac-back.stl"
