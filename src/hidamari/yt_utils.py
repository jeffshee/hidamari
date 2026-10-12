import yt_dlp as youtube_dl


def get_formats(raw_url):
    with youtube_dl.YoutubeDL({"noplaylist": True}) as ydl:
        formats = ydl.extract_info(raw_url, download=False)["formats"]
    return formats


def _value(fmt, key, default):
    # Formats may lack a field or set it to None, e.g. direct video URLs from the generic extractor
    value = fmt.get(key)
    return default if value is None else value


def _dimensions(fmt):
    width, height = fmt.get("width"), fmt.get("height")
    if not width or not height:
        # Unknown, callers fall back to detecting the size from the player
        return None, None
    return width, height


def filter_audio(formats):
    return filter(lambda x: x.get("acodec") != "none" and x.get("vcodec") == "none", formats)


def filter_video(formats):
    return filter(lambda x: x.get("acodec") == "none" and x.get("vcodec") != "none", formats)


def filter_audio_video(formats):
    return filter(lambda x: x.get("acodec") != "none" and x.get("vcodec") != "none", formats)


def get_best(formats):
    filtered = list(filter_audio_video(formats))
    best = max(filtered, key=lambda x: _value(x, "quality", -1))
    return best["url"], *_dimensions(best)


def get_best_audio(formats):
    filtered = list(filter_audio(formats))
    if not filtered:
        filtered = list(filter_audio_video(formats))
    best = max(filtered, key=lambda x: _value(x, "quality", -1))
    return best["url"]


def get_best_video(formats):
    filtered = list(filter_video(formats))
    if not filtered:
        filtered = list(filter_audio_video(formats))
    best = max(filtered, key=lambda x: _value(x, "quality", -1))
    return best["url"], *_dimensions(best)


def get_optimal_video(formats, height):
    filtered = list(filter_video(formats))
    if not filtered:
        filtered = list(filter_audio_video(formats))
    best = min(filtered, key=lambda x: abs(_value(x, "height", 0) - height))
    return best["url"], *_dimensions(best)


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
