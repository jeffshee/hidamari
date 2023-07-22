# Development Note

## Build
### Dependencies
#### PyGObject
Please refer to the [official documentation](https://pygobject.readthedocs.io/en/latest/getting_started.html#gettingstarted). The system-provided PyGObject is recommended.

#### Python packages
- Installing with pip (from `requirements.txt`, recommended)
```bash
pip install -r requirements.txt
```

- Installing from system provided package (Fedora):
```bash
sudo dnf install python3-pillow python3-pydbus python3-requests python3-setproctitle python3-vlc yt-dlp
```

#### Runtime dependencies
Note 1: Packages may have different names among distros. Hint: [pkgs.org](https://pkgs.org/) is very convenient to search packages for your distro.

Note 2: Please don't worry about the `gnome-desktop` package; it's just a library, not the GNOME Desktop Environment. 

- Ubuntu:
```bash
sudo apt install dconf-cli libappindicator3-1 libgnome-desktop-4-1 libwebkit2gtk-4.1-0 libwnck-3-0 mesa-utils vdpauinfo xdg-user-dirs
```

- Fedora:
```bash
sudo dnf install dconf glx-utils gnome-desktop4 libappindicator-gtk3 libwnck3 vdpauinfo webkit2gtk4.1 xdg-user-dirs
```

#### Build dependencies
- Ubuntu:
```bash
sudo apt install git meson gtk-update-icon-cache desktop-file-utils
```

- Fedora:
```bash
sudo dnf install git meson gtk-update-icon-cache desktop-file-utils
```

### Install
```
meson setup build && meson install -C build
```

### Uninstall
Please, check these commands before running. 🙏
```
sudo rm -rf /usr/local/share/hidamari
sudo rm /usr/local/bin/hidamari
sudo rm /usr/local/share/appdata/io.github.jeffshee.Hidamari.appdata.xml
sudo rm /usr/local/share/applications/io.github.jeffshee.Hidamari.desktop
sudo rm /usr/local/share/glib-2.0/schemas/io.github.jeffshee.Hidamari.gschema.xml
sudo rm /usr/local/share/icons/hicolor/scalable/apps/io.github.jeffshee.Hidamari.svg
```

## Flatpak
VSCode + Flatpak extension (`bilelmoussaoui.flatpak-vscode`) is recommended. Alternatively, GNOME Builder also comes in handy when building Flatpak applications.

*TODO: Write steps for building Flatpak*