"""探测视频信息、判断 HDR、生成 ffmpeg 滤镜链。analyze 和 export 共用。"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import subprocess

VIDEO_SUFFIXES = {".mov", ".mp4", ".m4v", ".avi", ".mkv", ".hevc"}

# iPhone 默认录杜比视界，直接处理会得到灰白的画面，必须做色调映射
HDR_TRANSFERS = {"smpte2084", "arib-std-b67"}

FILENAME_TIME_PATTERNS = [
    re.compile(r"(20\d{2})(\d{2})(\d{2})[_\-]?(\d{2})(\d{2})(\d{2})"),
    re.compile(r"(20\d{2})[-_](\d{2})[-_](\d{2})[ _\-]?(\d{2})[.:-]?(\d{2})[.:-]?(\d{2})"),
]


class ProbeError(RuntimeError):
    pass


def run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise ProbeError(f"命令失败: {' '.join(cmd[:3])}...\n{proc.stderr[-600:]}")
    return proc.stdout


class VideoInfo:
    __slots__ = (
        "path", "duration", "width", "height", "fps",
        "shot_at", "time_source", "is_hdr", "rotation",
    )

    def __init__(self, **kw) -> None:
        for k in self.__slots__:
            setattr(self, k, kw.get(k))

    @property
    def is_portrait(self) -> bool:
        return self.height >= self.width


def _parse_creation_time(raw: str | None) -> dt.datetime | None:
    if not raw:
        return None
    text = raw.strip().replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    # 统一成 naive 本地时间，避免有的素材带时区有的不带导致排序报错
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    # 1970 附近的时间戳是元数据丢失后的默认值，不可信
    return parsed if parsed.year > 2000 else None


def _time_from_filename(name: str) -> dt.datetime | None:
    for pattern in FILENAME_TIME_PATTERNS:
        m = pattern.search(name)
        if not m:
            continue
        try:
            return dt.datetime(*(int(g) for g in m.groups()))
        except ValueError:
            continue
    return None


def probe(path: pathlib.Path) -> VideoInfo:
    raw = run([
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", str(path),
    ])
    data = json.loads(raw)

    stream = next(
        (s for s in data.get("streams", []) if s.get("codec_type") == "video"), None
    )
    if stream is None:
        raise ProbeError(f"{path.name} 里没有视频轨")

    fmt = data.get("format", {})
    duration = float(fmt.get("duration") or stream.get("duration") or 0.0)
    if duration <= 0:
        raise ProbeError(f"{path.name} 时长读不出来")

    width, height = int(stream["width"]), int(stream["height"])

    rotation = 0
    for side in stream.get("side_data_list") or []:
        if "rotation" in side:
            rotation = int(side["rotation"]) % 360
    # 竖屏拍摄常被存成横向 + 旋转标记，宽高要跟着换过来
    if rotation in (90, 270):
        width, height = height, width

    num, _, den = (stream.get("avg_frame_rate") or "0/1").partition("/")
    fps = float(num) / float(den) if den and float(den) else 0.0

    shot_at = _parse_creation_time(
        (fmt.get("tags") or {}).get("creation_time")
        or (stream.get("tags") or {}).get("creation_time")
    )
    time_source = "元数据"
    if shot_at is None:
        shot_at = _time_from_filename(path.name)
        time_source = "文件名"
    if shot_at is None:
        shot_at = dt.datetime.fromtimestamp(path.stat().st_mtime)
        time_source = "修改时间"

    return VideoInfo(
        path=path,
        duration=duration,
        width=width,
        height=height,
        fps=fps or 30.0,
        shot_at=shot_at,
        time_source=time_source,
        is_hdr=(stream.get("color_transfer") in HDR_TRANSFERS),
        rotation=rotation,
    )


def find_videos(folder: pathlib.Path) -> list[pathlib.Path]:
    return sorted(
        p for p in folder.rglob("*")
        if p.is_file() and p.suffix.lower() in VIDEO_SUFFIXES and not p.name.startswith("._")
    )


def build_filter(info: VideoInfo, out_w: int, out_h: int, blur_sigma: int = 20) -> str:
    """竖屏画布滤镜链。横屏素材两侧补模糊背景，避免黑边。"""
    steps = []
    if info.is_hdr:
        steps.append(
            "zscale=t=linear:npl=100,format=gbrpf32le,"
            "zscale=p=bt709,tonemap=hable:desat=0,"
            "zscale=t=bt709:m=bt709:r=tv"
        )

    src_ratio = info.width / info.height
    dst_ratio = out_w / out_h
    # 比例接近就直接裁，差太多（横屏素材进竖屏画布）才补模糊背景
    if abs(src_ratio - dst_ratio) < 0.02:
        steps.append(f"scale={out_w}:{out_h}")
        steps.append("format=yuv420p")
        return ",".join(steps)

    prefix = (",".join(steps) + ",") if steps else ""
    return (
        f"[0:v]{prefix}split=2[bgsrc][fgsrc];"
        f"[bgsrc]scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
        f"crop={out_w}:{out_h},gblur=sigma={blur_sigma}[bg];"
        f"[fgsrc]scale={out_w}:{out_h}:force_original_aspect_ratio=decrease[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p[v]"
    )


def fmt_hms(seconds: float) -> str:
    seconds = max(seconds, 0.0)
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}.{int((seconds % 1) * 100):02d}"
