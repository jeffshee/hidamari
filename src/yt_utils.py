import yt_dlp as youtube_dl
import logging

logger = logging.getLogger("hidamari")


def get_formats(raw_url):
    with youtube_dl.YoutubeDL({"noplaylist": True}) as ydl:
        info = ydl.extract_info(raw_url, download=False)
        formats = info["formats"]
        # Extract HTTP headers from info or formats
        # Headers might be in info or in individual formats
        http_headers = info.get("http_headers", {})
        
        # If no headers in info, try to get them from the first format that has them
        if not http_headers:
            for fmt in formats:
                fmt_headers = fmt.get("http_headers", {})
                if fmt_headers:
                    http_headers = fmt_headers
                    break
        
        # Ensure User-Agent is set (important for YouTube streams)
        if "User-Agent" not in http_headers:
            http_headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        # Ensure Referer is set (YouTube checks this)
        if "Referer" not in http_headers:
            http_headers["Referer"] = raw_url
        
        # Ensure each format has http_headers (use format-specific or fallback to common)
        for fmt in formats:
            if "http_headers" not in fmt or not fmt.get("http_headers"):
                fmt["http_headers"] = http_headers
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
    if not filtered:
        raise ValueError("No audio format found")
    best = max(filtered, key=lambda x: x.get("quality", -1))
    return best["url"], best.get("http_headers", {})


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
    if not filtered:
        raise ValueError("No video format found")
    best = min(filtered, key=lambda x: abs(x.get("height", 0) - height))
    return best["url"], best["width"], best["height"], best.get("http_headers", {})


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
