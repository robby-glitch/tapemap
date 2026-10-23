#!/bin/bash
# usage: shot.sh <frameIndex> <out.png> [sel]
F=$1; OUT=$2; SEL=${3:-}
URL="file:///C:/Users/kaam/Desktop/operator%20mode/tapemap/docs/fresh-take/mockup.html#f=$F&s=$SEL"
"/c/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --disable-gpu --hide-scrollbars --window-size=1245,720 --force-device-scale-factor=1 --virtual-time-budget=2000 --screenshot="C:/Users/kaam/Desktop/operator mode/tapemap/docs/fresh-take/scratch/$OUT" "$URL" 2>&1 | tail -2
