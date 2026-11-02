#!/bin/sh
# LinkUp 双版本反编译一键脚本（macOS/Linux）
set -e
BASE="https://github.com/bear20252026/linkup-recovery/releases/download/v1.0"
echo "== [0/5] 依赖检查 =="
command -v java >/dev/null || { echo "缺少 Java，请先执行: brew install --cask temurin@17"; exit 1; }
echo "Java OK: $(java -version 2>&1 | head -1)"
echo "== [1/5] 下载大文件（可断点续传，已存在则跳过）=="
for f in apk156.part_aa apk156.part_ab apk166.part_aa apk166.part_ab jadx-1.5.6.zip apktool_3.0.3.jar; do
  [ -f "$f" ] || curl -L --retry 3 -o "$f" "$BASE/$f"
done
echo "== [2/5] 拼合 APK 并校验 =="
cat apk156.part_aa apk156.part_ab > com.youloft.watcher1.5.6.apk
cat apk166.part_aa apk166.part_ab > LinkUp.apk
chk() { if command -v md5sum >/dev/null 2>&1; then [ "$(md5sum "$2" | cut -d' ' -f1)" = "$1" ] && echo "校验OK $2" || echo "!! 校验不一致 $2"; else [ "$(md5 -q "$2")" = "$1" ] && echo "校验OK $2" || echo "!! 校验不一致 $2"; fi; }
chk 8d8e19b9f7435e2f5b33355c9cc897d4 com.youloft.watcher1.5.6.apk
chk 5ddd548a8b01b3b85fa1f9153c75d393 LinkUp.apk
echo "== [3/5] 解压 jadx =="
[ -d jadx-1.5.6 ] || unzip -q jadx-1.5.6.zip
chmod +x jadx-1.5.6/bin/jadx 2>/dev/null || true
echo "== [4/5] 反编译两个版本（各约 5-20 分钟）=="
jadx-1.5.6/bin/jadx -d out_jadx_156 --show-bad-code --deobf-min 3 com.youloft.watcher1.5.6.apk || true
jadx-1.5.6/bin/jadx -d out_jadx_166 --show-bad-code --deobf-min 3 LinkUp.apk || true
java -jar apktool_3.0.3.jar d com.youloft.watcher1.5.6.apk -o out_apktool_156 || true
java -jar apktool_3.0.3.jar d LinkUp.apk -o out_apktool_166 || true
echo "== [5/5] 打包产物 =="
zip -rq linkup_decompiled.zip out_jadx_156 out_jadx_166 out_apktool_156 out_apktool_166 2>/dev/null || tar czf linkup_decompiled.tar.gz out_jadx_156 out_jadx_166 out_apktool_156 out_apktool_166
echo "全部完成！产物: $(pwd)/linkup_decompiled.zip（或 .tar.gz）"
echo "请把该压缩包发回手机上的 DSH 助手，我将继续做差异分析和重建工程。"
