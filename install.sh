#!/bin/sh

OLD_INSTALL_DIR="$HOME/.hidamari"
OLD_BIN_DIR="$HOME/bin"
# Follow XDG Specs
BIN_DIR="$HOME/.local/bin"
INSTALL_DIR="$HOME/.local/share/hidamari"
APPLICATIONS_DIR="$HOME/.local/share/applications"
ICONS_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
# Set PATH for shell
ENV_D_DIR="$HOME/.config/environment.d"
BRANCH="master"

clear_old() {
  for name in $OLD_INSTALL_DIR $INSTALL_DIR; do
    if [[ -d $name ]]; then
      rm -rf $name
    fi
  done

  for name in $APPLICATIONS_DIR/hidamari.desktop $ICONS_DIR/hidamari.svg $ENV_D_DIR/60-local-bin.conf; do
    if [[ -f $name ]]; then
      rm $name
    fi
  done

  for name in $OLD_BIN_DIR $BIN_DIR; do
    if [[ -L $name/hidamari ]]; then
      rm $name/hidamari
      rmdir $name --ignore-fail-on-non-empty
    fi
  done
}

create_dirs() {
  for name in $BIN_DIR $INSTALL_DIR $APPLICATIONS_DIR $ICONS_DIR $ENV_D_DIR; do
    if [[ ! -d $name ]]; then
      mkdir -p $name
    fi
  done
}

check_deps() {
  error=0

  for name in python3 pip3 git ffmpeg vlc; do
    if [[ -z $(which $name 2>/dev/null) ]]; then
      echo "$name needs to be installed"
      error=1
    fi
  done

  if [[ -z $(ldconfig -p | grep libX11) ]]; then
    echo "libX11 needs to be installed"
    error=1
  fi

  # Arch-based OS doesn't ship with libwnck3 by default
    if [[ -z $(ldconfig -p | grep libwnck) ]]; then
    echo "libwnck3 needs to be installed"
    error=1
  fi

  if [[ $error -ne 1 ]]; then
    echo "Dependencies check OK"
  else
    echo "Install the above and rerun this script"
    exit 1
  fi
}

check_path() {
  if [[ $(systemctl --user show-environment | grep PATH) == *$BIN_DIR* ]]; then
    echo "PATH check OK"
  else
    echo "$BIN_DIR not found in \$PATH"
    echo "Append \`PATH=\"\$PATH:\$HOME/.local/bin\"\` to $ENV_D_DIR/60-local-bin.conf"
    touch $ENV_D_DIR/60-local-bin.conf
    echo "PATH=\"\$PATH:\$HOME/.local/bin\"" >>$ENV_D_DIR/60-local-bin.conf
    echo "Reboot is required to display the app icon"
  fi

  ## (Archived) Not using this because it doesn't set the $PATH for shell
  # if [[ $(echo $PATH) == *$BIN_DIR* ]]; then
  #   echo "PATH check OK"
  # else
  #   echo "$BIN_DIR not found in \$PATH"
  #   for name in ".bashrc" ".zshrc"; do
  #     echo "Append \`export PATH=\"\$PATH:\$HOME/.local/bin\"\` to $name"
  #     echo "export PATH=\"\$PATH:\$HOME/.local/bin\"" >>$HOME/$name
  #     source $HOME/$name
  #   done
  # fi
}

install_pip_deps() {
  # Replaced youtube-dl to yt-dlp
  pip3 install -U pycairo PyGObject pillow pydbus python-vlc yt-dlp
}

install() {
  check_deps
  install_pip_deps
  clear_old
  create_dirs
  check_path
  git clone --depth=1 --branch=$BRANCH https://github.com/jeffshee/hidamari.git $INSTALL_DIR
  ln -s $INSTALL_DIR/src/hidamari $BIN_DIR/hidamari
  cp $INSTALL_DIR/res/hidamari.desktop $APPLICATIONS_DIR/hidamari.desktop
  cp $INSTALL_DIR/res/hidamari.svg $ICONS_DIR/hidamari.svg
}

uninstall() {
  clear_old
}

prompt_install() {
  echo "This will install Hidamari to $INSTALL_DIR"
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
}

prompt_uninstall() {
  echo "This will uninstall Hidamari"
  while true; do
    read -r -p "Do you wish to proceed [y/N]?" yn
    case $yn in
    [Yy]*)
      uninstall
      break
      ;;
    *)
      echo "Abort"
      exit
      ;;
    esac
  done
}

echo "=== Hidamari (Un)Installer Script ==="
echo "0 for uninstall"
echo "1 for install"
while true; do
  read -r -p "Choose [0/1]?" action
  case $action in
  0)
    prompt_uninstall
    break
    ;;
  1)
    prompt_install
    break
    ;;
  *)
    echo "Abort"
    exit
    ;;
  esac
done
