import os
import gi
import os
from typing import Optional, Tuple, Dict

gi.require_version('Gst', '1.0')

from gi.repository import Gst, GdkPixbuf
from concurrent.futures import ThreadPoolExecutor, as_completed

Gst.init(None)

from src.config.paths_config import GALLERY_DIR, THUMBNAILS_DIR
from src.utils.hash import hash_file_content


def ensure_directories_exist() -> None:
    """Create gallery and thumbnails directories if they don't exist."""
    os.makedirs(GALLERY_DIR, exist_ok=True)
    os.makedirs(THUMBNAILS_DIR, exist_ok=True)


def extract_video_thumbnail(video_path: str, output_path: str) -> bool:
    """Extract a single thumbnail image from a video file and save it as PNG."""
    pipeline_str = (
        f'filesrc location="{video_path}" ! decodebin ! videoconvert ! videoscale ! '
        f'video/x-raw,format=RGB,width=320,height=180 ! appsink name=sink max-buffers=1 drop=true emit-signals=false'
    )
    pipeline = Gst.parse_launch(pipeline_str)
    appsink = pipeline.get_by_name('sink')

    pipeline.set_state(Gst.State.PAUSED)
    pipeline.get_state(Gst.CLOCK_TIME_NONE)

    pipeline.seek_simple(
        Gst.Format.TIME,
        Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
        int(1 * Gst.SECOND),
    )

    pipeline.set_state(Gst.State.PLAYING)

    sample = appsink.emit("pull-sample")
    if not sample:
        pipeline.set_state(Gst.State.NULL)
        return False

    buf = sample.get_buffer()
    caps = sample.get_caps()

    result, mapinfo = buf.map(Gst.MapFlags.READ)
    if not result:
        pipeline.set_state(Gst.State.NULL)
        return False

    structure = caps.get_structure(0)
    width = structure.get_value('width')
    height = structure.get_value('height')

    pixbuf = GdkPixbuf.Pixbuf.new_from_data(
        mapinfo.data,
        GdkPixbuf.Colorspace.RGB,
        False,
        8,
        width,
        height,
        width * 3,
    )
    pixbuf.savev(output_path, "png", [], [])
    buf.unmap(mapinfo)

    pipeline.set_state(Gst.State.NULL)
    return True


def process_video_to_thumbnail(video_path: str) -> Optional[Tuple[str, str]]:
    """
    Generate a thumbnail for a given video file if it doesn't exist.
    Returns a tuple of (video_path, thumbnail_path) on success, or None on failure.
    """
    file_hash = hash_file_content(video_path)
    thumbnail_filename = f"{file_hash}.png"
    thumbnail_path = os.path.join(THUMBNAILS_DIR, thumbnail_filename)

    if not os.path.exists(thumbnail_path):
        success = extract_video_thumbnail(video_path, thumbnail_path)
        if not success:
            return None

    return (video_path, thumbnail_path)


def generate_all_video_thumbnails() -> Dict[str, str]:
    """
    Scan the gallery directory for supported video files and generate thumbnails for each,
    returning a dictionary mapping video paths to their thumbnail paths.
    """
    ensure_directories_exist()
    supported_exts = {".mp4", ".mkv", ".avi", ".mov"}
    video_to_thumbnail: Dict[str, str] = {}

    video_paths = [
        entry.path for entry in os.scandir(GALLERY_DIR)
        if entry.is_file() and entry.name.lower().endswith(tuple(supported_exts))
    ]

    max_workers = max(1, os.cpu_count() - 1)  # leave 1 CPU free at minimum 1 worker

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_video_to_thumbnail, path): path for path in video_paths}
        for future in as_completed(futures):
            result = future.result()
            if result:
                video_path, thumbnail_path = result
                video_to_thumbnail[video_path] = thumbnail_path

    return video_to_thumbnail

