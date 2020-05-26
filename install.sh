#!/bin/sh
git clone https://github.com/jeffshee/hidamari.git ~/.hidamari
mkdir ~/bin
ln -s ~/.hidamari/hidamari ~/bin/hidamari
cp ~/.hidamari/hidamari.desktop ~/.config/autostart/hidamari.desktop
cp ~/.hidamari/hidamari.desktop ~/.local/share/applications/hidamari.desktop
cp ~/.hidamari/hidamari.svg ~/.local/share/icons/hicolor/scalable/apps/hidamari.svg

