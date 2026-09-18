#!/usr/bin/env python3
"""第二步：按清单导出编号好的竖屏片段，拖进剪映用。

    python scripts/export.py shots.csv raw/ -o selected/

导出的片段前后各留一点余量，方便在剪映里拉伸对齐节拍点。
"""

from __future__ import annotations

import argparse
import csv
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import vlogkit  # noqa: E402


def build_command(
    info: vlogkit.VideoInfo,
    start: float,
    duration: float,
    dst: pathlib.Path,
    args,
) -> list[str]:
    chain = vlogkit.build_filter(info, args.width, args.height, args.blur)
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-ss", f"{start:.3f}", "-i", str(info.path),
        "-t", f"{duration:.3f}",
    ]
    if chain.startswith("["):
        cmd += ["-filter_complex", chain, "-map", "[v]"]
    else:
        cmd += ["-vf", chain, "-map", "0:v:0"]
    cmd += [
        "-r", str(args.fps),
        "-c:v", "libx264", "-preset", args.preset, "-crf", str(args.crf),
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
    ]
    # 原声是无意义的环境噪音，成片音轨在剪映里重做
    cmd += ["-an"] if args.mute else ["-map", "0:a:0?", "-c:a", "aac", "-b:a", "128k"]
    cmd.append(str(dst))
    return cmd


def write_outline(path: pathlib.Path, entries: list[dict], margin: float) -> None:
    """导出一张镜头清单，方便照着写旁白，也可以直接丢给 AI 起草。"""
    by_group: dict[str, list[dict]] = {}
    for item in entries:
        by_group.setdefault(item["group"], []).append(item)

    lines = [
        "# 剪辑清单",
        "",
        f"共 {len(entries)} 个镜头，"
        f"合计 {vlogkit.fmt_hms(sum(e['duration'] for e in entries))}"
        f"（含前后各 {margin}s 余量）。",
        "",
        "## 镜头一览",
        "",
    ]
    for group in sorted(by_group):
        shots = by_group[group]
        span = f"{shots[0]['shot_at'][11:16]} - {shots[-1]['shot_at'][11:16]}"
        lines += [
            f"### 段落 {group}（{span}，{len(shots)} 个镜头）",
            "",
            "| 序号 | 文件 | 时长 | 拍摄时间 | 旁白（自己填） |",
            "| --- | --- | --- | --- | --- |",
        ]
        for shot in shots:
            lines.append(
                f"| {shot['index']:03d} | {shot['name']} | {shot['duration']:.1f}s "
                f"| {shot['shot_at'][11:16]} | |"
            )
        lines.append("")

    lines += [
        "## 让 AI 起草旁白时可以这样问",
        "",
        "> 这是我一条生活 vlog 的镜头清单，按拍摄时间排序，分成几个段落。",
        "> 请写一段第一人称旁白，语气轻松自然，不要煽情也不要文艺腔。",
        "> 每个段落 2-3 句话，每句控制在 15 字以内，方便配音断句。",
        "> 输出时标明每句话对应哪几个镜头序号。",
        "",
        "写好之后在剪映里用「文本 → 文本朗读」生成配音。",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", help="analyze.py 生成的清单")
    ap.add_argument("raw", help="原始素材文件夹（和 analyze.py 用的同一个）")
    ap.add_argument("-o", "--output", default="selected")
    ap.add_argument("--margin", type=float, default=1.0, help="每段前后留的余量秒数")
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1920)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--preset", default="medium")
    ap.add_argument("--blur", type=int, default=20, help="横屏素材补背景的模糊强度")
    ap.add_argument("--keep-audio", dest="mute", action="store_false", help="保留原声")
    ap.set_defaults(mute=True)
    args = ap.parse_args()

    raw_dir = pathlib.Path(args.raw).expanduser()
    out_dir = pathlib.Path(args.output).expanduser()
    csv_path = pathlib.Path(args.csv).expanduser()
    if not csv_path.is_file():
        print(f"找不到清单: {csv_path}", file=sys.stderr)
        return 1

    with csv_path.open(encoding="utf-8-sig") as fh:
        rows = [r for r in csv.DictReader(fh) if r.get("keep", "").strip() == "1"]
    if not rows:
        print("清单里没有 keep=1 的片段", file=sys.stderr)
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    cache: dict[pathlib.Path, vlogkit.VideoInfo] = {}
    done, failed, total_len = 0, [], 0.0
    exported: list[dict] = []

    for index, row in enumerate(rows, 1):
        src = raw_dir / row["file"]
        if not src.is_file():
            failed.append(f"{row['file']} 找不到")
            continue
        try:
            info = cache.get(src) or cache.setdefault(src, vlogkit.probe(src))
        except vlogkit.ProbeError as exc:
            failed.append(str(exc))
            continue

        # 留余量是为了在剪映里能把片段拉长对齐节拍，不能超出素材本身
        start = max(0.0, float(row["start"]) - args.margin)
        end = min(info.duration, float(row["end"]) + args.margin)
        duration = end - start
        if duration <= 0.1:
            failed.append(f"{row['file']} 区间无效")
            continue

        stem = pathlib.Path(row["file"]).stem[:28]
        dst = out_dir / f"{index:03d}_g{row.get('group', '1')}_{stem}.mp4"
        cmd = build_command(info, start, duration, dst, args)
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0 or not dst.exists():
            failed.append(f"{row['file']} 导出失败: {proc.stderr[-300:]}")
            continue

        done += 1
        total_len += duration
        exported.append({
            "index": index,
            "name": dst.name,
            "duration": duration,
            "group": str(row.get("group", "1")),
            "shot_at": row.get("shot_at", ""),
        })
        print(f"[{index}/{len(rows)}] {dst.name}  {duration:.1f}s")

    if exported:
        outline = out_dir / "剪辑清单.md"
        write_outline(outline, exported, args.margin)
        print(f"\n镜头清单 -> {outline}")

    print(f"\n导出 {done} 段，合计 {vlogkit.fmt_hms(total_len)} -> {out_dir}")
    print(f"（含前后各 {args.margin}s 余量，在剪映里裁掉即可对齐节拍）")
    if failed:
        print(f"\n{len(failed)} 段失败：")
        for line in failed[:10]:
            print("  -", line)
    return 0 if done else 1


if __name__ == "__main__":
    raise SystemExit(main())
