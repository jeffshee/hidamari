<p align="center"><img src="https://raw.githubusercontent.com/jeffshee/hidamari/v2/res/hidamari.svg" width="256"></p>

<p align="center">Video wallpaper for Linux. Minimal and written in Python.</p>  
<p align="center">Hidamari 日溜まり【ひだまり】(n) sunny spot; exposure to the sun</p>

# Hidamari　ーひだまりー

## Features 🔥

There are several solutions to achieve video as wallpaper on Linux, for example:

1. [Xwinwrap + mpv](https://www.linuxuprising.com/2019/05/livestream-wallpaper-for-your-gnome.html)
2. [Komorebi](https://github.com/cheesecakeufo/komorebi)

Hidamari offers similar feature as above, with additional features listed below:

- [x] Autostart after login
- [x] Apply static wallpaper with blur effect <sup>1</sup>
- [x] Detect maximized window and fullscreen mode <sup>2</sup>
- [x] Volume control
- [x] Mute the playback anytime with just 2 clicks!
- [x] Pause the playback anytime with just 2 clicks!
- [x] I'm feeling lucky <sup>3</sup>
- [x] GPU video decoding!
- [x] Gnome Wayland support!
- [x] Multi-monitor support!
- [x] Streaming URL support! <sup>4</sup>
- [x] Webpage as wallpaper! <sup>5</sup>
- [ ] You name it! =)

<sup>1</sup> Video frame can be applied as system wallpaper, look great in <i>GNOME</i>  
<sup>2</sup> Automatically pauses playback when maximized window or full screen mode is detected    
<sup>3</sup> Randomly select and play a video  
<sup>4</sup> Use <i>youtube-dl</i> as backend, tested with YouTube videos  
<sup>5</sup> Theoretically it can be anything from a normal webpage to <i>Unity/Godot WebGL games</i>, be creative!

## Installation (Fedora) ⏬

1. Multimedia codecs, refer
   to [Fedora](https://docs.fedoraproject.org/en-US/quick-docs/assembly_installing-plugins-for-playing-movies-and-music/)
2. Enable Copr `sudo dnf copr enable jeffshee/hidamari`
3. Install `sudo dnf install hidamari`

## Installation (Other linux) ⏬

### Prerequisite

1. PyGObject, refer to [Installation](https://pygobject.readthedocs.io/en/latest/getting_started.html)
2. Pillow, pydbus, youtube-dl `pip3 install pillow pydbus python-vlc youtube-dl`
3. Multimedia codecs, refer to [Ubuntu](https://itsfoss.com/install-media-codecs-ubuntu/)
4. FFmpeg, VLC player (For Ubuntu `sudo apt-get install ffmpeg vlc`)

### Installation

0. Prerequisite stated above.
1. Run `bash <(wget -qO- https://raw.githubusercontent.com/jeffshee/hidamari/master/install.sh)`

## Screenshot 📸

![](screenshot/01_video.png)
![](screenshot/02_streaming.png)
![](screenshot/03_webpage.png)

## Demo 📽️

Please click on the image to view <i>(redirect to YouTube)</i>

[![](http://i3.ytimg.com/vi/GV_kL7g94nY/maxresdefault.jpg)](https://www.youtube.com/watch?v=GV_kL7g94nY)

## Please!! (｡>ｕ<｡)

Collaboration is welcome! Let's make it better together~  
Feel free to open an issue if you have any problem or suggestion 🤗  
Star my project if you like it! 🌟  
Stay tune!!

## Contributors ✨

<a href="https://github.com/jeffshee/hidamari/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=jeffshee/hidamari" />
</a>

Made with [contributors-img](https://contrib.rocks).  
Icons made by [Freepik](http://www.freepik.com/) from [Flaticon](https://www.flaticon.com)

