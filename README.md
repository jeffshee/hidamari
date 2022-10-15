<p align="center"><img src="https://raw.githubusercontent.com/jeffshee/hidamari/resource/hidamari.svg" width="256"></p>

<p align="center">Video wallpaper for Linux. Written in Python. 🐍</p>  
<p align="center">Hidamari 日溜まり【ひだまり】(n) sunny spot; exposure to the sun</p>

# Hidamari　ーひだまりー
If you like my project, please consider buying me a coffee!! (⁎˃ ꇴ ˂⁎)ｯ

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/jeffshee)

Also please don't forget to click that star button! 🌟  
Your support is truly appreciated!

## For GNOME user 🐾
Please also check my new project [Hanabi](https://github.com/jeffshee/gnome-ext-hanabi)! While the project is still in its infancy, it has the potential to become more integrated with GNOME Shell

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

<sup>1</sup> Video frame can be applied as system wallpaper, look great in <i>GNOME</i> (currently GNOME exclusive, support for other DE might be added if requested...)  
<sup>2</sup> Automatically pauses playback when maximized window or full screen mode is detected (currently X11 only...)  
<sup>3</sup> Randomly select and play a video  
<sup>4</sup> Use <i>vlc</i> as backend (currently HW acceleration doesn't work with Nvidia+Wayland combination...)     
<sup>5</sup> Use <i>yt-dlp</i> as backend, tested with YouTube videos  
<sup>6</sup> Theoretically it can be anything from a normal webpage to <i>Unity/Godot WebGL games</i>, be creative!

## Installation ⏬
### Flatpak 📦
It is available on Flathub!

<a href='https://flathub.org/apps/details/io.github.jeffshee.Hidamari'><img width='240' alt='Download Hidamari on Flathub' src='https://flathub.org/assets/badges/flathub-badge-en.png'/></a>

#### Command line instructions
Install:  
Make sure to follow the [setup guide](https://flatpak.org/setup/) before installing
```
flatpak install flathub io.github.jeffshee.Hidamari
```
Run:  
```
flatpak run io.github.jeffshee.Hidamari
```

### Unofficial package
These are maintained by the community!
| Distro     | URL                                     | Maintainer                            |
|------------|-----------------------------------------|---------------------------------------|
| Arch Linux | [![AUR](https://img.shields.io/aur/version/hidamari?style=for-the-badge)](https://aur.archlinux.org/packages/hidamari) | [laymoth](https://github.com/laymoth) |

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
