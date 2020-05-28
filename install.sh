#!/bin/sh

install() {
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
}

echo "=== Hidamari Installer Script ==="
echo "This script install hidamari to $HOME/.hidamari"
while true; do
  read -r -p "Do you wish to proceed [y/N]?" yn
  case $yn in
  [Yy]*)
    install
    break
    ;;
  *)
    echo "Abort"
    exit ;;
  esac
done
