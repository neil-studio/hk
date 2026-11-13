#!/bin/bash
# ==========================================
# 香港一手新盘销控中心 - 一键同步与风控熔断工具 (macOS .command 脚本)
# 升级特性：全链路报错即停 + 失败项目一键局部重试 + 数量骤减熔断 + 地图联动同步
# ==========================================

cd "$(dirname "$0")"

clear
echo "=================================================="
echo "   香港一手新盘销控中心 - 一键安全同步工具 (风控版)"
echo "=================================================="
echo ""

# 记录更新前的项目总数，供推送前熔断对比
PREV_COUNT=$(python3 -c "
import json, os
if os.path.exists('data.json'):
    try:
        with open('data.json', 'r', encoding='utf-8') as f:
            print(len(json.load(f).get('projects', [])))
    except:
        print(0)
else:
    print(0)
")
echo "📌 当前线上基准项目数: ${PREV_COUNT} 个"
echo ""

# 辅助函数：报错暂停确认
confirm_on_error() {
    local step_name="$1"
    echo ""
    echo "❌ 错误: [${step_name}] 执行出现异常！"
    read -p "⚠️ 是否仍要忽略此报错并强行继续下一步？(输入 y 继续 / 直接回车立即中止): " choice
    if [[ "$choice" != "y" && "$choice" != "Y" ]]; then
        echo "🛑 已按安全策略中止流程，未改动线上数据。"
        read -p "按回车键退出..."
        exit 1
    fi
}

# ==========================================
# [1/6] 更新楼盘基础信息数据库
# ==========================================
echo "[1/6] 正在更新楼盘基础信息数据库 (开发商/校网/GPS/关键日期等)..."
python3 scrape_hkp_project_details.py
if [ $? -ne 0 ]; then
    confirm_on_error "1/6 楼盘基础信息抓取"
fi

# ==========================================
# [2/6] 全量抓取新盘销控数据 (HKP 主数据源)
# ==========================================
echo ""
echo "[2/6] 正在执行全量抓取新盘销控数据（HKP 主数据源）..."
python3 scrape_hkp_sales_control.py
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ 错误: HKP 主抓取脚本运行崩溃，已安全中止。"
    read -p "按回车键退出..."
    exit 1
fi

# 第二道安全门：检查 failed_projects.json 是否有部分项目因 IP 抖动/超时抓取失败
while true; do
    FAILED_INFO=$(python3 -c "
import json, os
f = 'failed_projects.json'
if os.path.exists(f):
    try:
        with open(f, 'r', encoding='utf-8') as fp:
            items = json.load(fp)
        if items:
            names = [str(x.get('name', x)) if isinstance(x, dict) else str(x) for x in items]
            print(f'{len(items)}|' + ', '.join(names))
        else:
            print('0|')
    except Exception as e:
        print(f'-1|{e}')
else:
    print('0|')
")
    FAILED_COUNT="${FAILED_INFO%%|*}"
    FAILED_NAMES="${FAILED_INFO#*|}"

    if [ "$FAILED_COUNT" -gt 0 ] 2>/dev/null; then
        echo ""
        echo "=================================================="
        echo "⚠️  安全门拦截: HKP 有 ${FAILED_COUNT} 个项目抓取失败！"
        echo "📋 失败清单: ${FAILED_NAMES}"
        echo "=================================================="
        echo "请选择操作:"
        echo "  [r] 一键仅重试以上 ${FAILED_COUNT} 个失败项目 (推荐)"
        echo "  [y] 人工确认忽略以上失败项，继续往下执行"
        echo "  [n] 立即中止退出 (默认)"
        read -p "请输入选项 [r/y/N]: " retry_choice
        if [[ "$retry_choice" == "r" || "$retry_choice" == "R" ]]; then
            echo ""
            echo "🔄 正在启动局部重试模式 (--retry)..."
            python3 scrape_hkp_sales_control.py --retry
            if [ $? -ne 0 ]; then
                confirm_on_error "HKP 失败项目局部重试"
            fi
            continue
        elif [[ "$retry_choice" == "y" || "$retry_choice" == "Y" ]]; then
            echo "👍 已人工确认放行，继续下一步..."
            break
        else
            echo "🛑 已安全中止流程，保护线上数据不被污染。"
            read -p "按回车键退出..."
            exit 1
        fi
    elif [ "$FAILED_COUNT" == "-1" ]; then
        confirm_on_error "读取 failed_projects.json 失败 (${FAILED_NAMES})"
        break
    else
        echo "✅ HKP 抓取 100% 全量成功，无任何失败项目！"
        break
    fi
done

# ==========================================
# [3/6] 补充抓取美联独有新盘
# ==========================================
echo ""
echo "[3/6] 正在补充抓取美联独有新盘（美联数据源）..."
python3 scrape_midland_supplement.py
if [ $? -ne 0 ]; then
    confirm_on_error "3/6 美联补充抓取"
fi

# ==========================================
# [4/6] 生成正式版网页数据库 (data.json / files)
# ==========================================
echo ""
echo "[4/6] 正在生成正式版网页数据库 (build_web.py)..."
python3 build_web.py
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ 错误: 正式版网页打包失败，已安全中止推送。"
    read -p "按回车键退出..."
    exit 1
fi

# ==========================================
# [5/6] 提取地图导出方案最近成交与在售汇总
# ==========================================
echo ""
echo "[5/6] 正在同步地图导出方案成交与销控汇总 (map/build_export_data.py)..."
python3 map/build_export_data.py
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ 错误: 地图导出数据提取失败，已安全中止推送。"
    read -p "按回车键退出..."
    exit 1
fi

# ==========================================
# [6/6] 数量骤减熔断检查 & 全量推送 GitHub
# ==========================================
NEW_COUNT=$(python3 -c "
import json, os
if os.path.exists('data.json'):
    try:
        with open('data.json', 'r', encoding='utf-8') as f:
            print(len(json.load(f).get('projects', [])))
    except:
        print(0)
else:
    print(0)
")
echo ""
echo "📊 打包后最新项目总数: ${NEW_COUNT} 个 (更新前基准: ${PREV_COUNT} 个)"

if [ "$PREV_COUNT" -gt 0 ] 2>/dev/null; then
    DROP=$((PREV_COUNT - NEW_COUNT))
    if [ "$DROP" -gt 3 ]; then
        echo ""
        echo "🚨 熔断警报: 本次项目数量较上次骤减了 ${DROP} 个！"
        echo "   可能存在大面积误判售罄或网络异常，已强制拦截推送！"
        read -p "⚠️ 确认这是真实变化并强行推送上线吗？(输入 y 确认 / 回车中止): " drop_choice
        if [[ "$drop_choice" != "y" && "$drop_choice" != "Y" ]]; then
            echo "🛑 已熔断中止推送，线上数据完好无损！"
            read -p "按回车键退出..."
            exit 1
        fi
    fi
fi

CURRENT_BRANCH=$(git branch --show-current)
echo ""
echo "[6/6] 正在全量暂存并推送至 GitHub 分支 (${CURRENT_BRANCH})..."
if [ -n "$(git status --porcelain)" ]; then
    git add .
    git commit -m "自动同步新盘与地图数据(全量): $(date +'%Y-%m-%d %H:%M:%S')"
    git push origin "${CURRENT_BRANCH}"
    if [ $? -eq 0 ]; then
        echo "👍 数据已全量同步至 GitHub (${CURRENT_BRANCH})。"
    else
        echo "❌ 错误: git push 推送失败，请检查网络或 Git 权限。"
        read -p "按回车键退出..."
        exit 1
    fi
else
    echo "ℹ️ 提示: 本地数据无任何变动，无需上传。"
fi

# 最终完成
echo ""
echo "=================================================="
echo "🎉 恭喜！全站与地图一键安全同步流程已全部结束！"
echo "正式版发布地址: https://neil-studio.github.io/hk/"
echo "全景地图子系统: https://neil-studio.github.io/hk/map/"
echo "=================================================="
echo ""
read -p "按回车键关闭此窗口..."
