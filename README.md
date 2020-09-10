# Hidamari　ーひだまりー
Video wallpaper for Linux, like Komorebi. Minimal and written in Python.

Hidamari 日溜まり【ひだまり】(n) sunny spot; exposure to the sun

## Feature
There are several solutions to achieve video as wallpaper on Linux, for example:
1. [Xwinwrap + mpv](https://www.linuxuprising.com/2019/05/livestream-wallpaper-for-your-gnome.html)
2. [Komorebi](https://github.com/cheesecakeufo/komorebi)

Hidamari offers similar feature as above, with additional features listed below:
- [x] Autostart after login
- [x] Apply static wallpaper. Apply the first frame of the video as wallpaper underneath. Blur radius is adjustable too!
- [x] Detect maximized window. Automatically pause the video playback if any maximized window is detected.
- [x] Mute audio
- [x] Volume level
- [x] Pause the video playback manually at anytime
- [x] I'm feeling lucky. Randomly select and play the video
- [ ] You name it! =)

## Prerequisite
1. PyGObject, refer to [Installation](https://pygobject.readthedocs.io/en/latest/getting_started.html)
2. Pillow, pydbus, Watchdog `pip3 install pillow pydbus watchdog`
3. Multimedia codecs, refer to [Ubuntu](https://itsfoss.com/install-media-codecs-ubuntu/) or [Fedora](https://docs.fedoraproject.org/en-US/quick-docs/assembly_installing-plugins-for-playing-movies-and-music/)
4. FFmpeg

## Installation
0. Prerequisite stated above.
1. Run `bash <(wget -qO- https://raw.githubusercontent.com/jeffshee/hidamari/master/install.sh)`

## Demo
Please click on the image (link to YouTube)

[![](res/demo.gif)](http://www.youtube.com/watch?v=EFh4O0xVcFw "")

## Please!! (｡>ｕ<｡)
Collaboration is welcome! Let's make it better together~

Feel free to open an issue if you have any problem/suggestion :heart:

Star my project if you like it! :star2:

Stay tune!!

## Special Thanks
Icons made by [Freepik](http://www.freepik.com/) from [Flaticon](https://www.flaticon.com/)!

