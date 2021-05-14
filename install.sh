#!/bin/sh

TEMP_DIR="$HOME/hidamari_temp"
INSTALL_DIR="$HOME/.hidamari"
BIN_DIR="$HOME/bin"
APPLICATIONS_DIR="$HOME/.local/share/applications"
ICONS_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
BRANCH="master"

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
  if [ ! -d "$ICONS_DIR" ]; then
    mkdir -p "$ICONS_DIR"
  fi
}

install() {
  clear_old
  create_dirs
  git clone --depth=1 --branch="$BRANCH" https://github.com/jeffshee/hidamari.git "$TEMP_DIR"
  cp -r "$TEMP_DIR/src" "$INSTALL_DIR"
  ln -s "$INSTALL_DIR/hidamari" "$BIN_DIR/hidamari"
  cp "$TEMP_DIR/res/hidamari.desktop" "$APPLICATIONS_DIR/hidamari.desktop"
  cp "$TEMP_DIR/res/hidamari.svg" "$ICONS_DIR/hidamari.svg"
  rm -rf "$TEMP_DIR"
}

echo "=== Hidamari Installer Script ==="
echo "This script will install Hidamari to $INSTALL_DIR"
echo "Please make sure that $BIN_DIR is listed in the \`PATH\` environment variable"
echo "Otherwise please append \`export PATH=\"\$PATH:$BIN_DIR\"\` to \`.bashrc\` (or \`.zshrc\` accordingly)"
echo "Current \`PATH\` environment variable: $PATH"
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
