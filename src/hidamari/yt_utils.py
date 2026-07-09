import yt_dlp as youtube_dl


def get_formats(raw_url):
    with youtube_dl.YoutubeDL({"noplaylist": True}) as ydl:
        formats = ydl.extract_info(raw_url, download=False)["formats"]
    return formats


def filter_audio(formats):
    return filter(lambda x: x.get("acodec") != "none" and x.get("vcodec") == "none", formats)


def filter_video(formats):
    return filter(lambda x: x.get("acodec") == "none" and x.get("vcodec") != "none", formats)


def filter_audio_video(formats):
    return filter(lambda x: x.get("acodec") != "none" and x.get("vcodec") != "none", formats)


def get_best(formats):
    filtered = list(filter_audio_video(formats))
    best = max(filtered, key=lambda x: x.get("quality", -1))
    return best["url"], best["width"], best["height"]


def get_best_audio(formats):
    filtered = list(filter_audio(formats))
    if not filtered:
        filtered = list(filter_audio_video(formats))
    best = max(filtered, key=lambda x: x.get("quality", -1))
    return best["url"]


def get_best_video(formats):
    filtered = list(filter_video(formats))
    if not filtered:
        filtered = list(filter_audio_video(formats))
    best = max(filtered, key=lambda x: x.get("quality", -1))
    return best["url"], best["width"], best["height"]


def get_optimal_video(formats, height):
    filtered = list(filter_video(formats))
    if not filtered:
        filtered = list(filter_audio_video(formats))
    best = min(filtered, key=lambda x: abs(x.get("height", 0) - height))
    return best["url"], best["width"], best["height"]


if __name__ == "__main__":
    import vlc

    test_url = "https://www.youtube.com/watch?v=hdf9-E0Rt8Q"
    formats = get_formats(test_url)
    instance = vlc.Instance()
    player = instance.media_player_new()
    Media = instance.media_new(get_optimal_video(formats, 1080))
    player.set_media(Media)
    player.add_slave(vlc.MediaSlaveType(1), get_best_audio(formats), True)
    player.play()

    while True:
        pass
