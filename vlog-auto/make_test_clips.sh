#!/usr/bin/env bash
# 生成一批模拟 iPhone vlog 的测试素材，用来验证整条流水线。
# 覆盖：清晰 / 模糊 / 过暗 / 过曝 / 静止 / 抖动 / 横屏 / HDR
#
#   ./make_test_clips.sh testraw
set -euo pipefail

OUT="${1:-testraw}"
mkdir -p "$OUT"
rm -f "$OUT"/*.mp4 "$OUT"/*.png

W=720; H=1280            # 竖屏，模拟手机
V="-c:v libx264 -preset ultrafast -pix_fmt yuv420p"

mk() {  # mk <文件名> <拍摄时间> <时长> <滤镜>
  local name=$1 when=$2 dur=$3 vf=$4
  ffmpeg -y -v error -f lavfi -i "testsrc2=s=${W}x${H}:r=30:d=${dur}" \
    -vf "$vf" $V -metadata creation_time="$when" "$OUT/$name" </dev/null
  echo "  $name  ($when)"
}

echo "生成测试素材到 $OUT/"

# ---- 段落一：上午 ----
mk VID_20260918_091500.mp4 "2026-09-18T09:15:00Z" 12 "hue=s=1.2"
mk VID_20260918_091800.mp4 "2026-09-18T09:18:00Z" 10 "boxblur=12:2"
mk VID_20260918_092200.mp4 "2026-09-18T09:22:00Z" 10 "eq=brightness=-0.42"
mk VID_20260918_092600.mp4 "2026-09-18T09:26:00Z" 10 "eq=brightness=0.46"
mk VID_20260918_093000.mp4 "2026-09-18T09:30:00Z" 14 "hue=h=40"

# 静止：抽一帧循环，画面清晰但完全不动，应当被判为废片
ffmpeg -y -v error -f lavfi -i "testsrc2=s=${W}x${H}:r=30:d=1" -frames:v 1 "$OUT/still.png" </dev/null
ffmpeg -y -v error -loop 1 -i "$OUT/still.png" -t 10 -r 30 $V \
  -metadata creation_time="2026-09-18T09:34:00Z" "$OUT/VID_20260918_093400.mp4" </dev/null
echo "  VID_20260918_093400.mp4  (静止)"
rm -f "$OUT/still.png"

# 剧烈晃动：每帧大幅位移
mk VID_20260918_093800.mp4 "2026-09-18T09:38:00Z" 10 \
  "crop=${W}-80:${H}-80:40+38*sin(n*2.3):40+38*cos(n*3.1),scale=${W}:${H}"

# ---- 段落二：下午（间隔 >30 分钟，应被判为新段落）----
mk VID_20260918_143000.mp4 "2026-09-18T14:30:00Z" 12 "hue=h=120"
mk VID_20260918_143500.mp4 "2026-09-18T14:35:00Z" 10 "hue=h=200,eq=contrast=1.15"

# 横屏素材：应当被自动补模糊背景填进竖屏画布
ffmpeg -y -v error -f lavfi -i "testsrc2=s=1280x720:r=30:d=10" $V \
  -metadata creation_time="2026-09-18T14:40:00Z" "$OUT/VID_20260918_144000.mp4" </dev/null
echo "  VID_20260918_144000.mp4  (横屏)"

# HDR 素材：应当被自动转成 SDR
ffmpeg -y -v error -f lavfi -i "testsrc2=s=${W}x${H}:r=30:d=10" \
  -c:v libx264 -preset ultrafast -pix_fmt yuv420p10le \
  -color_trc smpte2084 -colorspace bt2020nc -color_primaries bt2020 \
  -metadata creation_time="2026-09-18T14:45:00Z" "$OUT/VID_20260918_144500.mp4" </dev/null
echo "  VID_20260918_144500.mp4  (HDR)"

# 没有元数据、文件名也没时间：应当退回用文件修改时间
ffmpeg -y -v error -f lavfi -i "testsrc2=s=${W}x${H}:r=30:d=8" $V "$OUT/nometa.mp4" </dev/null
echo "  nometa.mp4  (无拍摄时间)"

echo
echo "共 $(ls -1 "$OUT"/*.mp4 | wc -l | tr -d ' ') 个文件"
