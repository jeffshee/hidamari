#!/bin/python

import argparse
import fcntl
import sys

import gi

gi.require_version('Gtk', '3.0')
gi.require_version('GtkClutter', '1.0')
gi.require_version('ClutterGst', '3.0')
from gi.repository import Gtk, Gdk, GtkClutter, Clutter, ClutterGst
from singleton import SingleInstance


def monitor_detect():
    display = Gdk.Display.get_default()
    monitor = display.get_primary_monitor()
    geometry = monitor.get_geometry()
    scale_factor = monitor.get_scale_factor()
    width = scale_factor * geometry.width
    height = scale_factor * geometry.height
    return width, height


def quit_application():
    Gtk.main_quit()


def single_instance_check():
    pid_file = 'program.pid'
    fp = open(pid_file, 'w')
    try:
        fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        print('There is another instance still running!')
        sys.exit(0)


class VideoWallpaper:
    def __init__(self, video_path, audio_volume=0.0):
        # Settings
        self.video_path = video_path
        self.audio_volume = audio_volume
        bg_color = Clutter.Color.get_static(Clutter.StaticColor.BLACK)

        # Monitor Detect
        self.width, self.height = monitor_detect()

        # Actors initialize
        GtkClutter.init()
        self.embed = GtkClutter.Embed()
        self.main_actor = self.embed.get_stage()
        self.wallpaper_actor = Clutter.Actor()
        self.wallpaper_actor.set_size(self.width, self.height)
        self.main_actor.add_child(self.wallpaper_actor)
        self.main_actor.set_background_color(bg_color)

        # Video initialize
        ClutterGst.init()
        self.video_playback = ClutterGst.Playback()
        self.video_content = ClutterGst.Content()
        self.video_content.set_player(self.video_playback)

        # Playback settings
        self.video_playback.set_filename(video_path)
        self.video_playback.set_audio_volume(audio_volume)
        self.video_playback.set_playing(True)
        self.video_playback.connect('eos', self.loop_playback)
        self.wallpaper_actor.set_content(self.video_content)

        # Window settings
        self.window = Gtk.Window(title='Desktop')
        self.window.add(self.embed)
        self.window.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
        self.window.set_size_request(self.width, self.height)
        self.window.show_all()

        Gtk.main()

    def loop_playback(self, playback):
        playback.set_progress(0.0)
        playback.set_audio_volume(self.audio_volume)
        playback.set_playing(True)


if __name__ == '__main__':
    # # Dummy for testing
    # root = '/home/jeffshee/Developer/komorebi/video/'
    # file_name = ['anone.mp4', 'azusa.mp4', 'bakuretsu.mp4', 'marisa.mp4', 'megumi.mp4', 'miko_fox.mp4', 'miku.mp4',
    #              'starry.mp4']
    # VideoWallpaper(video_path=root + file_name[4])

    # Single Instance Check
    SingleInstance()
    parser = argparse.ArgumentParser()
    parser.add_argument('path', help='path to video')
    parser.add_argument('-v', '--volume', help='audio volume ranged from 0.0 (default) to 1.0', type=float, default=0.0)
    args = parser.parse_args()
    VideoWallpaper(video_path=args.path, audio_volume=args.volume)
