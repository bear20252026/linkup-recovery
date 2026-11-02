#!/bin/sh
# LinkUp APK 反编译一键脚本（macOS / Linux 通用）
# 用法：终端进入本目录，执行：  sh mac_run.sh com.youloft.watcher1.5.6.apk
# 前提：安装了 Java（没有的话执行：brew install --cask temurin@17）
set -e
APK="${1:-com.youloft.watcher1.5.6.apk}"
[ -f "$APK" ] || APK="$(ls ../*.apk 2>/dev/null | head -1)"
[ -f "$APK" ] || { echo "找不到 APK，用法: sh mac_run.sh /路径/com.youloft.watcher1.5.6.apk"; exit 1; }
echo "使用 APK: $APK"
command -v java >/dev/null 2>&1 || { echo "未检测到 Java，请先执行: brew install --cask temurin@17"; exit 1; }
if [ ! -d jadx-1.5.6 ]; then echo "解压 jadx..."; unzip -q jadx-1.5.6.zip; fi
chmod +x jadx-1.5.6/bin/jadx 2>/dev/null || true
echo "== [1/2] jadx 反编译 Java 源码（5-20 分钟）=="
jadx-1.5.6/bin/jadx -d out_jadx --show-bad-code --deobf-min 3 "$APK" || true
echo "== [2/2] apktool 还原布局/清单为文本 XML =="
java -jar apktool_3.0.3.jar d "$APK" -o out_apktool || true
echo ""
echo "全部完成！重点阅读顺序："
echo "  out_jadx/sources/com/youloft/yftracker/    <- 网络层+签名算法（核心，先重写这个）"
echo "  out_jadx/sources/com/youloft/watcher/manager/  <- 业务管理器"
echo "  out_jadx/sources/com/youloft/watcher/pages/    <- 页面逻辑"
echo "  out_apktool/res/layout/                        <- 布局 XML"
echo "完成后把 out_jadx 和 out_apktool 两个文件夹拷回手机发我，我继续帮你搭重建工程。"
