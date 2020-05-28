#!/bin/sh
if [ -d "$HOME/.hidamari" ]; then
  rm -rf ~/.hidamari
fi
git clone https://github.com/jeffshee/hidamari.git ~/.hidamari
if [ ! -d "$HOME/bin" ]; then
  mkdir ~/bin
fi
if [ -f "$HOME/bin/hidamari" ]; then
  rm ~/bin/hidamari
fi
ln -s ~/.hidamari/hidamari ~/bin/hidamari
cp ~/.hidamari/hidamari.desktop ~/.config/autostart/hidamari.desktop
cp ~/.hidamari/hidamari.desktop ~/.local/share/applications/hidamari.desktop
cp ~/.hidamari/hidamari.svg ~/.local/share/icons/hicolor/scalable/apps/hidamari.svg
