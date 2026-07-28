#!/bin/bash
# ==========================================
# 香港一手新盘销控中心 - 一键同步与自动重试工具 (macOS .command 脚本)
# 双击即可运行：自动全量抓取、同步网页端、推送云端，并在 1 小时后自动对失败项目进行重试与更新。
# ==========================================

# 切换到脚本所在目录
cd "$(dirname "$0")"

clear
echo "=========================================="
echo "      香港一手新盘销控中心 - 一键同步工具      "
echo "=========================================="
echo ""

# 1. 运行本地全量抓取脚本（香港置业数据源）
echo "[1/5] 正在执行全量抓取新盘销控数据（HKP 数据源）..."
python3 scrape_hkp_sales_control.py
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ 错误: 抓取新盘数据失败，请检查网络。"
    echo ""
    read -p "按回车键退出..."
    exit 1
fi

# 1.5 补充抓取美联独有的新盘项目
echo ""
echo "[2/5] 正在补充抓取美联独有新盘（美联数据源）..."
python3 scrape_midland_supplement.py
if [ $? -ne 0 ]; then
    echo "⚠️ 警告: 美联补充抓取出现错误，但不影响主流程，继续执行..."
fi

# 3. 整理网页数据并第一次推送到 GitHub
echo ""
echo "[3/5] 正在整理网页端文件并推送到 GitHub (全量更新)..."
python3 build_web.py
if [ $? -eq 0 ]; then
    cd web
    if [ -n "$(git status --porcelain)" ]; then
        git add .
        git commit -m "自动同步新盘数据(全量): $(date +'%Y-%m-%d %H:%M:%S')"
        git push
        echo "👍 第一次数据已同步至 GitHub Pages。"
    else
        echo "ℹ️ 提示: 本地数据无任何变动，无需上传。"
    fi
    cd ..
else
    echo "⚠️ 警告: 网页生成失败，跳过本次推送。"
fi

# 最终完成
echo ""
echo "=========================================="
echo "🎉 恭喜！一键更新与同步流程已全部结束！"
echo "网页将在 1-2 分钟内自动部署更新。"
echo "您的访问网址: https://neil-studio.github.io/hk-properties/"
echo "=========================================="
echo ""
read -p "按回车键关闭此窗口..."
