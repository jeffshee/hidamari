import youtube_dl


def get_formats(raw_url):
    with youtube_dl.YoutubeDL({"noplaylist": True}) as ydl:
        formats = ydl.extract_info(raw_url, download=False)["formats"]
    return formats


def filter_audio(formats):
    return filter(lambda x: x["acodec"] != "none" and x["vcodec"] == "none", formats)


def filter_video(formats):
    return filter(lambda x: x["acodec"] == "none" and x["vcodec"] != "none", formats)


def filter_audio_video(formats):
    return filter(lambda x: x["acodec"] != "none" and x["vcodec"] != "none", formats)


def get_best(formats):
    filtered = list(filter_audio_video(formats))
    best = max(filtered, key=lambda x: x["quality"])
    return best["url"]


def get_best_audio(formats):
    filtered = list(filter_audio(formats))
    best = max(filtered, key=lambda x: x["quality"])
    return best["url"]


def get_best_video(formats):
    filtered = list(filter_video(formats))
    best = max(filtered, key=lambda x: x["quality"])
    return best["url"]


def get_optimal_video(formats, height):
    filtered = list(filter_video(formats))
    best = min(filtered, key=lambda x: abs(x["height"] - height))
    return best["url"]


if __name__ == "__main__":
    import vlc

    test_url = "https://www.youtube.com/watch?v=H2QFIQsIOdI&list=LL&index=2"
    # test_url = "https://www.youtube.com/watch?v=Y-lYuGIWqu0&list=LL&index=6"
    formats = get_formats(test_url)
    instance = vlc.Instance()
    player = instance.media_player_new()
    Media = instance.media_new(get_optimal_video(formats, 1080))
    player.set_media(Media)
    player.add_slave(vlc.MediaSlaveType(1), get_best_audio(formats), True)
    player.play()

    while True:
        pass
