#!/bin/sh

TEMP_DIR="$HOME/hidamari_temp"
INSTALL_DIR="$HOME/.hidamari"
BIN_DIR="$HOME/bin"
AUTOSTART_DIR="$HOME/.config/autostart"
APPLICATIONS_DIR="$HOME/.local/share/applications/"
ICONS_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

clear_old() {
  if [ -d "$INSTALL_DIR" ]; then
    rm -rf ~/.hidamari
  fi
  if [ -f "$BIN_DIR/hidamari" ] || [ -L "$BIN_DIR/hidamari" ]; then
    rm ~/bin/hidamari
  fi
}

create_dirs() {
  if [ ! -d "$BIN_DIR" ]; then
    mkdir "$BIN_DIR"
  fi
  if [ ! -d "$AUTOSTART_DIR" ]; then
    mkdir -p "$AUTOSTART_DIR"
  fi
  if [ ! -d "$ICONS_DIR" ]; then
    mkdir -p "$ICONS_DIR"
  fi
}

install() {
  clear_old
  create_dirs
  git clone https://github.com/jeffshee/hidamari.git "$TEMP_DIR"
  cp -r "$TEMP_DIR/src" "$INSTALL_DIR"
  ln -s "$INSTALL_DIR/hidamari" "$BIN_DIR/hidamari"
  cp "$TEMP_DIR/res/hidamari.desktop" "$AUTOSTART_DIR/hidamari.desktop"
  cp "$TEMP_DIR/res/hidamari.desktop" "$APPLICATIONS_DIR/hidamari.desktop"
  cp "$TEMP_DIR/res/hidamari.svg" "$ICONS_DIR/hidamari.svg"
  rm -rf "$TEMP_DIR"
}

echo "=== Hidamari Installer Script ==="
echo "This script install hidamari to $INSTALL_DIR"
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
