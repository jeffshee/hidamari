<p align="center"><img src="https://raw.githubusercontent.com/jeffshee/hidamari/resource/hidamari.svg" width="256"></p>

<p align="center">Video wallpaper for Linux. Written in Python. 🐍</p>  
<p align="center">Hidamari 日溜まり【ひだまり】(n) sunny spot; exposure to the sun</p>

# Hidamari　ーひだまりー
If you like my project, please consider buying me a coffee!! (⁎˃ ꇴ ˂⁎)ｯ

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/jeffshee)

Also please don't forget to click that star button! 🌟  
Your support is truly appreciated!

## For GNOME user 🐾
Please also check my new project [Hanabi](https://github.com/jeffshee/gnome-ext-hanabi)! While the project is still in its infancy, it has the potential to become more integrated with GNOME Shell.

## Features 🔥

There are several solutions to achieve video as wallpaper on Linux, for example:

1. [Xwinwrap + mpv](https://www.linuxuprising.com/2019/05/livestream-wallpaper-for-your-gnome.html)
2. [Komorebi](https://github.com/cheesecakeufo/komorebi)

Hidamari offers similar feature as above, with additional features listed below:

- [x] Autostart after login
- [x] Apply static wallpaper with blur effect <sup>1</sup>
- [x] Detect maximized window and fullscreen mode <sup>2</sup>
- [x] Volume control
- [x] Mute/Pause the playback anytime with just 2 clicks!
- [x] I'm feeling lucky <sup>3</sup>
- [x] Hardware accelerated video decoding! <sup>4</sup>
- [x] Gnome Wayland support!
- [x] Multi-monitor support!
- [x] Streaming URL support! <sup>5</sup>
- [x] Webpage as wallpaper! <sup>6</sup>
- [ ] You name it! =)

<sup>1</sup> Video frame can be applied as system wallpaper, look great in <i>GNOME</i>  
<sup>2</sup> Automatically pauses playback when maximized window or full screen mode is detected (Limited support for Gnome Wayland, see issue [#40](https://github.com/jeffshee/hidamari/issues/40))  
<sup>3</sup> Randomly select and play a video  
<sup>4</sup> Use <i>vlc</i> as backend  
<sup>5</sup> Use <i>yt-dlp</i> as backend, tested with YouTube videos  
<sup>6</sup> Theoretically it can be anything from a normal webpage to <i>Unity/Godot WebGL games</i>, be creative!

<!-- TODO add flathub link -->
<!-- ## (Un)Installation ⏬
Run the script in terminal to install or uninstall:
```
bash <(wget -qO- https://raw.githubusercontent.com/jeffshee/hidamari/master/install.sh)
```
The script will also check for the dependencies. It will try to install them if possible (only for pip packages).  -->

<!-- ## Installation (Fedora, RPM) ⏬

1. Multimedia codecs, refer
   to [Fedora](https://docs.fedoraproject.org/en-US/quick-docs/assembly_installing-plugins-for-playing-movies-and-music/)
2. Enable Copr `sudo dnf copr enable jeffshee/hidamari`
3. Install `sudo dnf install hidamari`

## Installation (Ubuntu, DEB) ⏬

1. Multimedia codecs, refer to [Ubuntu](https://itsfoss.com/install-media-codecs-ubuntu/)
2. Download the `.deb` file from release section
3. Install `sudo apt install ./path/to/hidamari*.deb`
4. (Recommended) Upgrade `youtube-dl` to the latest version:  
   `sudo pip3 install --upgrade youtube-dl`

## Installation (Other linux) ⏬

### Prerequisite

1. python3, pip3, git, ffmpeg, vlc, libx11
2. Multimedia codecs, please refer to your distribution for installation guide
3. PyGObject, refer to [Installation](https://pygobject.readthedocs.io/en/latest/getting_started.html)
4. Pillow, pydbus, youtube-dl `sudo pip3 install pillow pydbus python-vlc youtube-dl`

### Installation

0. Prerequisite stated above.
1. Run `bash <(wget -qO- https://raw.githubusercontent.com/jeffshee/hidamari/master/install.sh)` -->

## Screenshot 📸

![](https://raw.githubusercontent.com/jeffshee/hidamari/resource/screenshot-1.png)
![](https://raw.githubusercontent.com/jeffshee/hidamari/resource/screenshot-2.png)
![](https://raw.githubusercontent.com/jeffshee/hidamari/resource/screenshot-3.png)

<!-- TODO v3.0 demo -->
<!-- ## Demo 📽️

Please click on the image to view <i>(redirect to YouTube)</i>

[![](https://i3.ytimg.com/vi/GV_kL7g94nY/maxresdefault.jpg)](https://www.youtube.com/watch?v=GV_kL7g94nY) -->

## Please!! 🙏

Collaboration is welcome! Let's make it better together~  
Feel free to open an issue if you have any problem or suggestion 🤗  

## Contributors ✨

<a href="https://github.com/jeffshee/hidamari/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=jeffshee/hidamari" />
</a>

Made with [contributors-img](https://contrib.rocks).  
Icons made by [Freepik](http://www.freepik.com/) from [Flaticon](https://www.flaticon.com)
