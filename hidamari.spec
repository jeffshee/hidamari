%global tag 2.0
%global debug_package %{nil}
%global project hidamari
%undefine _disable_source_fetch

Name:           hidamari
Version:        %{tag}
Release:        1%{?dist}
Summary:        Video wallpaper for Linux

License:        Apache-2.0
URL:            https://github.com/jeffshee/hidamari
Source0:        https://github.com/jeffshee/hidamari/archive/refs/tags/v%{tag}.tar.gz

Requires:       python3-gobject python3-pillow python3-pydbus python3-vlc youtube-dl gtk3 ffmpeg vlc libX11

%description
Video wallpaper for Linux. Minimal and written in Python.

%prep
%autosetup -n %{project}-%{tag}

%build

%install
%{__mkdir_p} %{buildroot}%{_datadir}/hidamari
%{__mkdir_p} %{buildroot}%{_bindir}
%{__install} -m 0755 src/* %{buildroot}%{_datadir}/hidamari
%{__ln_s} -r %{buildroot}%{_datadir}/hidamari/hidamari %{buildroot}%{_bindir}/hidamari

%{__mkdir_p} %{buildroot}%{_datarootdir}/icons/hicolor/scalable/apps
%{__mkdir_p} %{buildroot}%{_datarootdir}/applications
%{__install} -m 0644 res/hidamari.svg %{buildroot}%{_datarootdir}/icons/hicolor/scalable/apps/hidamari.svg
%{__cat} <<EOT > %{buildroot}%{_datarootdir}/applications/hidamari.desktop
[Desktop Entry]
Type=Application
Name=Hidamari
Exec=hidamari
StartupNotify=false
Terminal=false
Icon=hidamari
Categories=System;Monitor;
EOT

%files
%license LICENSE
%doc README.md
%{_datadir}/hidamari/*
%{_bindir}/hidamari
%{_datarootdir}/icons/hicolor/scalable/apps/hidamari.svg
%{_datarootdir}/applications/hidamari.desktop

%changelog
* Fri May 7 2021 jeffshee <jeffshee8969@gmail.com>
Initial release
