# Hidamari　ーひだまりー
Video wallpaper for Linux, like Komorebi. Minimal and written in Python.

Hidamari 日溜まり【ひだまり】(n) sunny spot; exposure to the sun

## Prerequisite
1. PyGObject, refer to [Installation](https://pygobject.readthedocs.io/en/latest/getting_started.html)
2. Pillow, pydbus, Watchdog `pip3 install pillow pydbus watchdog`
3. Multimedia codecs, refer to [Ubuntu](https://itsfoss.com/install-media-codecs-ubuntu/) or [Fedora](https://docs.fedoraproject.org/en-US/quick-docs/assembly_installing-plugins-for-playing-movies-and-music/)

## Usage
0. Prerequisite stated above.
1. Run `bash <(wget -qO- https://raw.githubusercontent.com/jeffshee/hidamari/master/install.sh)`

**OR**
1. Clone the repo, or simply download the `.zip` file from GitHub.
2. Extract or copy everything to `~/bin/` directory.
3. In terminal, use `chmod +x ~/bin/hidamari` to make the script executable.
4. Optional, copy the `.desktop` file to `~/.local/share/applications/` for the application icon.
5. Optional, copy the `.desktop` file to `~/.config/autostart/` to autostart the script after login.

## Known issue
~1. Fedora 32, cannot autostart the script due to a segmentation fault. [Fedora Bugzilla](https://bugzilla.redhat.com/show_bug.cgi?id=1834740)~

## Demo
Please click on the image (link to YouTube)

[![](preview.gif)](http://www.youtube.com/watch?v=EFh4O0xVcFw "")

## Please!! (｡>ｕ<｡)
Collaboration is welcome! Let's make it better together~

Feel free to open an issue if you have any problem/suggestion :heart:

Star my project if you like it! :star2:

Stay tune!!
