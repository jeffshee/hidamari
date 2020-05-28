#!/bin/sh

clear_old() {
  if [ -d "$HOME/.hidamari" ]; then
    rm -rf ~/.hidamari
  fi
  if [ -f "$HOME/bin/hidamari" ] || [ -L "$HOME/bin/hidamari" ]; then
    rm ~/bin/hidamari
  fi
}

create_dirs() {
  if [ ! -d "$HOME/bin" ]; then
    mkdir ~/bin
  fi
  if [ ! -d "$HOME/.config/autostart/" ]; then
    mkdir -p ~/.config/autostart
  fi
  if [ ! -d "$HOME/.local/share/icons/hicolor/scalable/apps/" ]; then
    mkdir -p ~/.local/share/icons/hicolor/scalable/apps
  fi
}

install() {
  clear_old
  create_dirs
  git clone https://github.com/jeffshee/hidamari.git ~/.hidamari
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
    exit
    ;;
  esac
done
