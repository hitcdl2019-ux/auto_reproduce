#!/bin/bash
# lab4ai-auto-reproduct 安装脚本
# 为 vendor/ 下的第三方 skill 创建软链接到 ~/.openclaw/skills/ 一级目录

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="$(dirname "$SCRIPT_DIR")"
VENDOR_DIR="$SCRIPT_DIR/vendor"

echo "🔧 lab4ai-auto-reproduct 安装脚本"
echo "   Skill 目录: $SKILLS_DIR"
echo "   Vendor 目录: $VENDOR_DIR"
echo ""

if [ ! -d "$VENDOR_DIR" ]; then
    echo "❌ vendor/ 目录不存在: $VENDOR_DIR"
    exit 1
fi

for skill_dir in "$VENDOR_DIR"/*/; do
    skill_name=$(basename "$skill_dir")
    target="$SKILLS_DIR/$skill_name"
    
    if [ -L "$target" ]; then
        echo "🔄 更新软链接: $skill_name"
        rm "$target"
    elif [ -d "$target" ]; then
        echo "⚠️  跳过 $skill_name（已存在同名目录，非软链接）"
        continue
    else
        echo "✅ 创建软链接: $skill_name"
    fi
    
    ln -sf "$skill_dir" "$target"
done

echo ""
echo "✅ 安装完成！以下 vendor skill 已链接:"
for skill_dir in "$VENDOR_DIR"/*/; do
    skill_name=$(basename "$skill_dir")
    target="$SKILLS_DIR/$skill_name"
    if [ -L "$target" ]; then
        echo "   $skill_name -> $(readlink "$target")"
    fi
done
