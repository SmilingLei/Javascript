#!/usr/bin/env python3
"""第一步：扫描素材，按拍摄时间排序，逐段打分，挑出候选镜头。

    python scripts/analyze.py raw/ -o shots.csv

输出一张 CSV 清单，keep 列是机器的建议（1 保留 / 0 丢弃）。
你可以用表格软件打开直接改这一列，再交给 export.py。
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import pathlib
import subprocess
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import vlogkit  # noqa: E402

SAMPLE_FPS = 2.5
ANALYZE_LONG_EDGE = 480

# 权重：清晰度最重要，其次曝光，再次运动是否合适
W_SHARP, W_EXPOSURE, W_MOTION = 0.5, 0.3, 0.2

# 硬性淘汰线
MIN_BRIGHTNESS, MAX_BRIGHTNESS = 28.0, 226.0
MAX_CLIPPED = 0.35          # 过暗+过曝像素占比上限
FROZEN_MOTION = 0.45        # 低于此值视为画面冻结（忘了关录像）
SHAKE_MOTION = 14.0         # 高于此值视为剧烈晃动


def even(value: float) -> int:
    return max(2, int(round(value / 2)) * 2)


def batch_metrics(frames: np.ndarray, previous: np.ndarray | None) -> dict[str, np.ndarray]:
    """算一批帧的清晰度、亮度、过曝欠曝比例，以及与前一帧的运动量。"""
    f = frames.astype(np.float32)

    # 四邻域拉普拉斯，方差越大越锐利；糊片的高频成分很少
    lap = (
        4.0 * f[:, 1:-1, 1:-1]
        - f[:, :-2, 1:-1] - f[:, 2:, 1:-1]
        - f[:, 1:-1, :-2] - f[:, 1:-1, 2:]
    )

    prior = previous.astype(np.float32) if previous is not None else f[0]
    chain = np.concatenate([prior[None, ...], f], axis=0)
    motion = np.abs(chain[1:] - chain[:-1]).reshape(len(f), -1).mean(axis=1)

    return {
        "sharpness": lap.reshape(len(f), -1).var(axis=1),
        "brightness": f.reshape(len(f), -1).mean(axis=1),
        "clipped": ((frames < 16) | (frames > 240)).reshape(len(frames), -1).mean(axis=1),
        "motion": motion,
    }


def measure(info: vlogkit.VideoInfo, batch: int = 64) -> dict[str, np.ndarray]:
    """解码一遍抽成小尺寸灰度帧，边读边算。

    长录像一次性读进内存会吃掉好几个 G，所以按批消费，只留下逐帧指标。
    """
    if info.width >= info.height:
        ow, oh = ANALYZE_LONG_EDGE, even(ANALYZE_LONG_EDGE * info.height / info.width)
    else:
        oh, ow = ANALYZE_LONG_EDGE, even(ANALYZE_LONG_EDGE * info.width / info.height)
    frame_bytes = ow * oh

    cmd = [
        "ffmpeg", "-v", "error", "-i", str(info.path),
        "-vf", f"fps={SAMPLE_FPS},scale={ow}:{oh}",
        "-f", "rawvideo", "-pix_fmt", "gray", "-",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    collected: dict[str, list[np.ndarray]] = {
        "sharpness": [], "brightness": [], "clipped": [], "motion": [],
    }
    previous: np.ndarray | None = None
    leftover = b""
    try:
        assert proc.stdout is not None
        while True:
            chunk = proc.stdout.read(frame_bytes * batch)
            if not chunk:
                break
            buf = leftover + chunk
            count = len(buf) // frame_bytes
            leftover = buf[count * frame_bytes:]
            if count == 0:
                continue
            frames = np.frombuffer(buf[: count * frame_bytes], dtype=np.uint8)
            frames = frames.reshape(count, oh, ow)
            for key, values in batch_metrics(frames, previous).items():
                collected[key].append(values)
            previous = frames[-1]
    finally:
        if proc.stdout:
            proc.stdout.close()
        stderr = proc.stderr.read() if proc.stderr else b""
        if proc.stderr:
            proc.stderr.close()
        proc.wait()

    if proc.returncode != 0:
        raise vlogkit.ProbeError(
            f"{info.path.name} 解码失败\n{stderr.decode('utf-8', 'replace')[-600:]}"
        )
    if not collected["sharpness"]:
        raise vlogkit.ProbeError(f"{info.path.name} 太短，抽不出足够的帧")

    metrics = {k: np.concatenate(v) for k, v in collected.items()}
    if len(metrics["sharpness"]) < 2:
        raise vlogkit.ProbeError(f"{info.path.name} 太短，抽不出足够的帧")
    return metrics


def motion_score(mean_motion: float) -> float:
    """运动量打分：冻结和剧烈晃动都不要，中间有个舒服的区间。"""
    if mean_motion < FROZEN_MOTION or mean_motion > SHAKE_MOTION:
        return 0.0
    # 2-6 之间是手持轻微移动，观感最好
    if mean_motion < 2.0:
        return 0.55 + 0.45 * (mean_motion - FROZEN_MOTION) / (2.0 - FROZEN_MOTION)
    if mean_motion <= 6.0:
        return 1.0
    return max(0.0, 1.0 - (mean_motion - 6.0) / (SHAKE_MOTION - 6.0))


def exposure_score(brightness: float, clipped: float) -> float:
    if not (MIN_BRIGHTNESS <= brightness <= MAX_BRIGHTNESS) or clipped > MAX_CLIPPED:
        return 0.0
    # 以中灰 118 为最佳，越偏离越扣分
    deviation = abs(brightness - 118.0) / 118.0
    return max(0.0, (1.0 - deviation)) * (1.0 - clipped / MAX_CLIPPED * 0.5)


def scan_windows(info: vlogkit.VideoInfo, metrics: dict, args) -> list[dict]:
    """滑动窗口找出这条素材里值得用的几段。"""
    n = len(metrics["sharpness"])
    win = max(2, int(round(args.shot_len * SAMPLE_FPS)))
    stride = max(1, int(round(args.stride * SAMPLE_FPS)))
    if n < win:
        return []

    # 手机按下/松开录制键时的抖动，掐掉头尾
    guard = int(round(args.edge_trim * SAMPLE_FPS))
    lo, hi = guard, n - guard - win
    if hi < lo:
        lo, hi = 0, n - win

    out = []
    for start in range(lo, hi + 1, stride):
        end = start + win
        sl = slice(start, end)
        brightness = float(metrics["brightness"][sl].mean())
        clipped = float(metrics["clipped"][sl].max())
        motion = float(metrics["motion"][sl].mean())

        exposure = exposure_score(brightness, clipped)
        motion_q = motion_score(motion)
        if exposure == 0.0 or motion_q == 0.0:
            continue

        out.append({
            "file": info.path,
            "start": start / SAMPLE_FPS,
            "end": end / SAMPLE_FPS,
            "sharp_raw": float(metrics["sharpness"][sl].mean()),
            "brightness": brightness,
            "clipped": clipped,
            "motion": motion,
            "exposure_q": exposure,
            "motion_q": motion_q,
        })
    return out


def suppress_overlaps(windows: list[dict], min_gap: float) -> list[dict]:
    """同一条素材里相邻窗口内容几乎一样，只留分最高的那个。"""
    picked: list[dict] = []
    for cand in sorted(windows, key=lambda w: w["score"], reverse=True):
        if all(
            cand["start"] >= p["end"] + min_gap or cand["end"] <= p["start"] - min_gap
            for p in picked
        ):
            picked.append(cand)
    return sorted(picked, key=lambda w: w["start"])


def percentile_rank(values: np.ndarray) -> np.ndarray:
    """清晰度的绝对值随内容变化很大，用批次内的相对排名更稳。"""
    if len(values) == 0:
        return values
    order = values.argsort().argsort().astype(np.float64)
    return order / max(len(values) - 1, 1)


def group_by_time(infos: list[vlogkit.VideoInfo], gap_minutes: float) -> dict[pathlib.Path, int]:
    """拍摄时间断档超过阈值就算换了一个段落，方便在剪映里安排快慢节奏。"""
    groups: dict[pathlib.Path, int] = {}
    index = 0
    previous: dt.datetime | None = None
    for info in infos:
        if previous is not None and (info.shot_at - previous).total_seconds() > gap_minutes * 60:
            index += 1
        groups[info.path] = index
        previous = info.shot_at
    return groups


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", help="放原始素材的文件夹")
    ap.add_argument("-o", "--output", default="shots.csv")
    ap.add_argument("--target", type=float, default=300.0, help="成片目标秒数（默认 5 分钟）")
    ap.add_argument("--overshoot", type=float, default=1.5, help="多挑几个给你手动删")
    ap.add_argument("--shot-len", type=float, default=3.0, help="单个镜头时长")
    ap.add_argument("--stride", type=float, default=0.8, help="滑窗步长")
    ap.add_argument("--edge-trim", type=float, default=0.4, help="每条素材掐掉的头尾秒数")
    ap.add_argument("--min-gap", type=float, default=2.0, help="同一素材内两个镜头的最小间隔")
    ap.add_argument("--group-gap", type=float, default=30.0, help="超过几分钟算新段落")
    args = ap.parse_args()

    folder = pathlib.Path(args.folder).expanduser()
    if not folder.is_dir():
        print(f"找不到文件夹: {folder}", file=sys.stderr)
        return 1

    files = vlogkit.find_videos(folder)
    if not files:
        print(f"{folder} 里没有视频文件", file=sys.stderr)
        return 1
    print(f"找到 {len(files)} 个文件\n")

    infos, failures = [], []
    for path in files:
        try:
            infos.append(vlogkit.probe(path))
        except vlogkit.ProbeError as exc:
            failures.append(f"{path.name}: {exc}")
    if not infos:
        print("没有一个文件能读取", file=sys.stderr)
        return 1

    infos.sort(key=lambda i: i.shot_at)
    groups = group_by_time(infos, args.group_gap)

    guessed = sum(1 for i in infos if i.time_source != "元数据")
    total_raw = sum(i.duration for i in infos)
    print(f"素材总时长 {vlogkit.fmt_hms(total_raw)}，分成 {max(groups.values()) + 1} 个段落")
    if guessed:
        print(f"提示：{guessed} 个文件读不到拍摄时间，已退回文件名或修改时间排序")
    if any(i.is_hdr for i in infos):
        print(f"提示：{sum(1 for i in infos if i.is_hdr)} 个 HDR 文件，导出时会自动转 SDR")
    print()

    candidates: list[dict] = []
    for idx, info in enumerate(infos, 1):
        label = f"[{idx}/{len(infos)}] {info.path.name}"
        try:
            metrics = measure(info)
        except vlogkit.ProbeError as exc:
            failures.append(str(exc))
            print(f"{label} 跳过")
            continue

        windows = scan_windows(info, metrics, args)
        for w in windows:
            w["group"] = groups[info.path]
            w["shot_at"] = info.shot_at
        candidates.extend(windows)
        print(f"{label}  {vlogkit.fmt_hms(info.duration)}  可用片段 {len(windows)}")

    if not candidates:
        print("\n没有任何片段通过筛选。素材可能过暗、太糊或者全程静止。", file=sys.stderr)
        return 1

    sharp_q = percentile_rank(np.array([c["sharp_raw"] for c in candidates]))
    for cand, sq in zip(candidates, sharp_q):
        cand["sharp_q"] = float(sq)
        cand["score"] = (
            W_SHARP * float(sq)
            + W_EXPOSURE * cand["exposure_q"]
            + W_MOTION * cand["motion_q"]
        )

    by_file: dict[pathlib.Path, list[dict]] = {}
    for cand in candidates:
        by_file.setdefault(cand["file"], []).append(cand)
    shots = []
    for file_windows in by_file.values():
        shots.extend(suppress_overlaps(file_windows, args.min_gap))

    # 按段落的素材量分配名额，避免某一段把整条片子占满
    budget = args.target * args.overshoot
    per_group: dict[int, list[dict]] = {}
    for shot in shots:
        per_group.setdefault(shot["group"], []).append(shot)
    group_weight = {g: sum(s["end"] - s["start"] for s in v) for g, v in per_group.items()}
    weight_total = sum(group_weight.values()) or 1.0

    chosen: set[int] = set()
    for gid, group_shots in per_group.items():
        quota = budget * group_weight[gid] / weight_total
        used = 0.0
        for shot in sorted(group_shots, key=lambda s: s["score"], reverse=True):
            if used >= quota:
                break
            chosen.add(id(shot))
            used += shot["end"] - shot["start"]

    shots.sort(key=lambda s: (s["shot_at"], s["start"]))

    out_path = pathlib.Path(args.output)
    with out_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "seq", "keep", "group", "file", "start", "end", "duration",
            "score", "sharpness", "exposure", "motion", "shot_at",
        ])
        for seq, shot in enumerate(shots, 1):
            writer.writerow([
                seq,
                1 if id(shot) in chosen else 0,
                shot["group"] + 1,
                shot["file"].relative_to(folder).as_posix(),
                f"{shot['start']:.2f}",
                f"{shot['end']:.2f}",
                f"{shot['end'] - shot['start']:.2f}",
                f"{shot['score']:.3f}",
                f"{shot['sharp_q']:.3f}",
                f"{shot['exposure_q']:.3f}",
                f"{shot['motion']:.2f}",
                shot["shot_at"].strftime("%Y-%m-%d %H:%M:%S"),
            ])

    kept = sum(1 for s in shots if id(s) in chosen)
    kept_len = sum(s["end"] - s["start"] for s in shots if id(s) in chosen)
    print(f"\n候选 {len(shots)} 段，建议保留 {kept} 段，合计 {vlogkit.fmt_hms(kept_len)}")
    print(f"清单已写出 -> {out_path}")
    print("用表格软件打开，改 keep 列（1 保留 / 0 丢弃），然后跑 export.py")
    if failures:
        print(f"\n{len(failures)} 个文件有问题：")
        for line in failures[:10]:
            print("  -", line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
