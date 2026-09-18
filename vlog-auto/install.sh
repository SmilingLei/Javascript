#!/usr/bin/env bash
# macOS 一键安装。只需要 ffmpeg 和 numpy，没有重依赖。
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$DIR/.venv"

say() { printf '\n\033[1;36m==> %s\033[0m\n' "$1"; }
die() { printf '\n\033[1;31m[错误] %s\033[0m\n' "$1" >&2; exit 1; }

say "1/3 检查 ffmpeg"
if command -v ffmpeg >/dev/null 2>&1; then
  echo "已存在: $(ffmpeg -version | head -1 | cut -d' ' -f1-3)"
elif command -v brew >/dev/null 2>&1; then
  brew install ffmpeg
elif command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update && sudo apt-get install -y ffmpeg
else
  die "没找到 ffmpeg，也没找到 brew。请先安装 Homebrew: https://brew.sh"
fi

# HDR 素材转 SDR 依赖 zscale，缺了 iPhone 的杜比视界素材会出问题
if ! ffmpeg -hide_banner -filters 2>/dev/null | grep -q zscale; then
  echo "警告: 这个 ffmpeg 不带 zscale，HDR 素材无法转 SDR。"
  echo "      macOS 上用 brew install ffmpeg 装的版本是带的。"
fi

say "2/3 检查 Python"
PY=""
for c in python3.12 python3.11 python3; do
  command -v "$c" >/dev/null 2>&1 || continue
  if "$c" -c 'import sys;sys.exit(0 if sys.version_info[:2]>=(3,9) else 1)' 2>/dev/null; then
    PY="$c"; echo "使用 $c ($($c --version))"; break
  fi
done
[ -n "$PY" ] || die "未找到 Python 3.9+。macOS 请运行: brew install python@3.12"

say "3/3 创建环境并安装 numpy"
if [ ! -x "$VENV/bin/python" ]; then
  "$PY" -m venv "$VENV" || die "创建虚拟环境失败。Ubuntu 请先: sudo apt-get install -y python3-venv"
fi
"$VENV/bin/python" -m pip install --upgrade pip --quiet
"$VENV/bin/pip" install --quiet -r "$DIR/requirements.txt"

mkdir -p "$DIR/raw"

cat <<EOF

安装完成。

  ffmpeg : $(ffmpeg -version | head -1 | cut -d' ' -f3)
  numpy  : $("$VENV/bin/python" -c 'import numpy;print(numpy.__version__)')

用法：把手机素材放进 raw/ 然后

  cd "$DIR"
  .venv/bin/python scripts/analyze.py raw -o shots.csv
  .venv/bin/python scripts/export.py shots.csv raw -o selected

详见 README.md
EOF
