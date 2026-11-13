import os
import subprocess

SANDBOX_DIR = "/Users/nb/google/Antigravity/工作/运营/价单/sandbox"
PREVIEW_DIR = os.path.join(SANDBOX_DIR, "preview_shots")
ARTIFACT_DIR = "/Users/nb/.gemini/antigravity/brain/4966922d-20a7-40ee-81fd-975e44311c8a"
os.makedirs(PREVIEW_DIR, exist_ok=True)
os.makedirs(ARTIFACT_DIR, exist_ok=True)

# 基础样式（完全沿用 A4 横版导出规范：1122px x 793px）
COMMON_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@600;700;800;900&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

:root {
  --primary: #00889A;
  --primary-dark: #005A66;
  --gold: #C5A059;
  --slate-900: #0F172A;
  --slate-800: #1E293B;
  --slate-700: #334155;
  --slate-500: #64748B;
  --border: #E2E8F0;
  --bg-page: #F8FAFC;
}

* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
  background: #E2E8F0;
  padding: 20px;
  display: flex;
  justify-content: center;
}

.pdf-page {
  width: 1122px;
  height: 793px;
  background: #FFFFFF;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0,0,0,0.15);
}

.page-header {
  height: 48px;
  padding: 0 36px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 2px solid var(--primary);
  background: #FFFFFF;
}

.page-header-left {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.page-header-title {
  font-family: 'Noto Serif SC', serif;
  font-size: 1.05rem;
  font-weight: 800;
  color: var(--slate-900);
}

.page-header-badge {
  font-size: 0.65rem;
  font-weight: 700;
  color: var(--primary);
  background: #E0F2FE;
  padding: 2px 8px;
  border-radius: 12px;
  letter-spacing: 0.5px;
}

.page-header-logo {
  height: 24px;
}

.page-footer {
  height: 32px;
  padding: 0 36px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-top: 1px solid var(--border);
  font-size: 0.62rem;
  color: var(--slate-500);
  background: #FFFFFF;
}

.page-body {
  flex: 1;
  padding: 10px 36px 8px 36px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
  overflow: hidden;
}

.verdict-sec-title {
  font-size: 0.84rem;
  font-weight: 800;
  color: var(--slate-900);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.verdict-sec-subtitle {
  font-size: 0.66rem;
  color: var(--slate-500);
  font-weight: normal;
}

/* 标签通用 */
.tag-pill {
  font-size: 0.60rem;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 2px;
}
"""

# 数据定义
projs_4 = {
    "owner": [
        {
            "idx": 3,
            "name": "愽峰",
            "price": "约 $4883 万起",
            "district": "九龙塘",
            "school": "41名校网",
            "meta": "🏛️ 3座大厦 46伙 · 🔑 现楼 · 🚇 近九龙塘站",
            "sqft": "📐 主力3-4房大宅 (1,400-3,000呎)",
            "highlight": "九龙塘广播道半山珍稀向南大宅，圈层高度纯粹",
            "img": f"file://{SANDBOX_DIR}/images/projects/thumb/博峰.webp",
            "tags": ["九龙塘半山", "41校网天花板", "现楼即住"]
        },
        {
            "idx": 4,
            "name": "The Monet 第2期",
            "price": "约 $1500 万起",
            "district": "九龙塘",
            "school": "41名校网",
            "meta": "🏛️ 独栋 14伙 · 🔑 现楼 · 🚇 近九龙塘站",
            "sqft": "📐 主打2-3房精品 (800-1,500呎)",
            "highlight": "九龙塘广播道8号超级豪宅巅峰之作，极度稀缺",
            "img": f"file://{SANDBOX_DIR}/images/projects/thumb/The Monet 第2期.webp",
            "tags": ["低密独栋", "喇沙名校圈", "私密花园"]
        }
    ],
    "balanced": [
        {
            "idx": 1,
            "name": "傲玟",
            "price": "约 $1503 万起",
            "district": "何文田",
            "school": "34名校网",
            "meta": "🏛️ 6座大厦 401伙 · 🔑 现楼 · 🚇 近土瓜湾站",
            "sqft": "📐 主力2-3房家庭大宅 (848-1,440呎)",
            "highlight": "何文田核心传统豪宅区现楼大宅，私密园林会所",
            "img": f"file://{SANDBOX_DIR}/images/projects/thumb/傲玟.webp",
            "tags": ["传统豪宅", "34名校网", "现楼交付"]
        },
        {
            "idx": 2,
            "name": "瑜一．天海",
            "price": "约 $711 万起",
            "district": "何文田",
            "school": "34名校网",
            "meta": "🏛️ 4座大厦 447伙 · 🔑 现楼 · 🚇 近何文田站",
            "sqft": "📐 1房至3房港铁上盖 (311-934呎)",
            "highlight": "纯正港铁上盖双线枢纽极速通达，流动性极强底仓",
            "img": f"file://{SANDBOX_DIR}/images/projects/thumb/瑜一．天海.webp",
            "tags": ["港铁上盖", "双线换乘", "流动性底仓"]
        }
    ]
}

# 8个项目数据扩充
projs_8 = {
    "owner": projs_4["owner"] + [
        {
            "idx": 5,
            "name": "维港汇 I",
            "price": "约 $1200 万起",
            "district": "西南九龙",
            "school": "一线海景",
            "meta": "🏛️ 4座大厦 524伙 · 🔑 现楼 · 🚇 近南昌站",
            "sqft": "📐 2-4房临海地标 (488-2,189呎)",
            "highlight": "维港一线临海地标大盘，双铁交汇顶级会所",
            "img": f"file://{SANDBOX_DIR}/images/projects/thumb/维港汇 I.webp",
            "tags": ["一线维港", "港铁南昌站", "临海豪宅"]
        },
        {
            "idx": 6,
            "name": "朗贤峰第IIA期",
            "price": "约 $950 万起",
            "district": "何文田",
            "school": "34名校网",
            "meta": "🏛️ 5座大厦 418伙 · 🔑 2025年 · 🚇 近何文田站",
            "sqft": "📐 1-4房铁路枢纽 (377-1,433呎)",
            "highlight": "鹰君与港铁倾力打造，直通何文田站出入口",
            "img": f"file://{SANDBOX_DIR}/images/projects/thumb/朗贤峰第IIA期.webp",
            "tags": ["港铁上盖", "34名校网", "品牌发展商"]
        }
    ],
    "balanced": projs_4["balanced"] + [
        {
            "idx": 7,
            "name": "柏蔚森 I",
            "price": "约 $420 万起",
            "district": "启德跑道区",
            "school": "34名校网",
            "meta": "🏛️ 2座大厦 291伙 · 🔑 2025年 · 🚇 近启德站",
            "sqft": "📐 1-3房轻奢亲海 (234-560呎)",
            "highlight": "新世界森林森呼吸美学，启德跑道区高租售比标杆",
            "img": f"file://{SANDBOX_DIR}/images/projects/thumb/柏蔚森 I.webp",
            "tags": ["启德跑道", "高租金回报", "低总价门槛"]
        },
        {
            "idx": 8,
            "name": "启德海湾 第1期",
            "price": "约 $580 万起",
            "district": "启德跑道区",
            "school": "34名校网",
            "meta": "🏛️ 3座大厦 1017伙 · 🔑 现楼 · 🚇 近启德站",
            "sqft": "📐 1-3房都会海景 (288-771呎)",
            "highlight": "嘉华/会德丰/中国海外联手巨构，成熟大盘生活圈",
            "img": f"file://{SANDBOX_DIR}/images/projects/thumb/启德海湾第1期.webp",
            "tags": ["千伙大盘", "34名校网", "现楼即住"]
        }
    ]
}


# =========================================================================
# 生成方案一：【图文微缩实景 + 标签化精装卡片】
# =========================================================================
def build_option1_html(projs_data, title_suffix="4盘效果"):
    num_projs = len(projs_data["owner"]) + len(projs_data["balanced"])
    
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
{COMMON_CSS}

.verdict-rows-container {{
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
  min-height: 0;
}}

.decision-category-row {{
  background: #FFFFFF;
  border: 1px solid var(--border);
  border-radius: 8px;
  display: flex;
  flex-direction: row;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0,0,0,0.02);
  flex: 1;
  min-height: 0;
}}

.decision-category-row.cat-owner {{ border-left: 5px solid #0284C7; }}
.decision-category-row.cat-balanced {{ border-left: 5px solid #16A34A; }}

/* 左侧策略看板 */
.decision-row-strategy-box {{
  width: 250px;
  flex-shrink: 0;
  padding: 10px 14px;
  background: rgba(248, 250, 252, 0.95);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 6px;
}}

.decision-row-title {{
  font-size: 0.86rem;
  font-weight: 800;
  color: var(--slate-900);
  font-family: 'Noto Serif SC', serif;
  display: flex;
  align-items: center;
  gap: 5px;
}}

.decision-row-count-pill {{
  font-size: 0.62rem;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 10px;
}}

.decision-row-strategy-text {{
  font-size: 0.64rem;
  line-height: 1.45;
  color: var(--slate-700);
  display: flex;
  flex-direction: column;
  gap: 4px;
}}

.decision-row-strategy-text strong {{ color: var(--slate-900); }}

.decision-row-profile-tag {{
  background: #F1F5F9;
  border: 1px solid #E2E8F0;
  padding: 4px 6px;
  border-radius: 4px;
  font-size: 0.60rem;
  color: var(--slate-700);
  line-height: 1.35;
}}

/* 右侧图文卡片流 */
.decision-row-projects-flow {{
  flex: 1;
  min-width: 0;
  padding: 8px 10px;
  display: grid;
  grid-template-columns: repeat({2 if num_projs <= 4 else 3 if num_projs <= 6 else 4}, 1fr);
  gap: 8px;
  align-items: stretch;
  background: #FAFCFF;
}}
.cat-balanced .decision-row-projects-flow {{ background: #FAFEFA; }}

/* 建议一核心：图文结合卡片 */
.proj-rich-card {{
  background: #FFFFFF;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  gap: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.03);
  border-top: 3px solid #CBD5E1;
}}
.border-owner {{ border-top-color: #0284C7; }}
.border-balanced {{ border-top-color: #16A34A; }}

.card-top-row {{
  display: flex;
  gap: 10px;
  align-items: center;
}}

.card-img-wrap {{
  width: 96px;
  height: 70px;
  flex-shrink: 0;
  border-radius: 6px;
  overflow: hidden;
  position: relative;
  background: #E2E8F0;
  border: 1px solid #CBD5E1;
}}

.card-img {{
  width: 100%;
  height: 100%;
  object-fit: cover;
}}

.card-img-badge {{
  position: absolute;
  bottom: 2px;
  right: 2px;
  background: rgba(15, 23, 42, 0.80);
  color: #FFFFFF;
  font-size: 0.52rem;
  padding: 1px 4px;
  border-radius: 2px;
  font-weight: 600;
}}

.card-top-info {{
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}}

.card-name-price {{
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}}

.card-name {{
  font-size: 0.82rem;
  font-weight: 800;
  color: var(--slate-900);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}

.card-price {{
  font-size: 0.76rem;
  font-weight: 800;
  white-space: nowrap;
}}

.card-tag-row {{
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
  margin: 1px 0;
}}

.card-meta-line {{
  font-size: 0.61rem;
  color: #64748B;
  display: flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}

.card-sqft-line {{
  font-size: 0.62rem;
  font-weight: 600;
  color: var(--slate-700);
  background: #F8FAFC;
  padding: 4px 6px;
  border-radius: 4px;
  border: 1px solid #F1F5F9;
}}

.card-highlight-line {{
  font-size: 0.62rem;
  color: var(--slate-700);
  background: #F1F5F9;
  padding: 6px 8px;
  border-radius: 4px;
  line-height: 1.4;
  border-left: 3px solid var(--primary);
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 2px;
}}
</style>
</head>
<body>

<div class="pdf-page">
  <div class="page-header">
    <div class="page-header-left">
      <span class="page-header-title">全案综合置业决策建议与终极选房指南</span>
      <span class="page-header-badge">建议一预览 · 图文微缩实景与标签化精装卡片 ({title_suffix})</span>
    </div>
    <span style="font-size:0.75rem; font-weight:700; color:var(--primary);">LANDMA GLOBAL</span>
  </div>

  <div class="page-body">
    <div class="verdict-sec-title">
      <span>💡 蓝玛置业专家终极选房分类矩阵 (2大核心置业客群维度深度匹配)</span>
      <span class="verdict-sec-subtitle">全案入选 {num_projs} 个重点新盘 · 图文一体化呈现 · 消除空旷感与视觉撕裂</span>
    </div>

    <div class="verdict-rows-container">
      <!-- 怡居大宅 -->
      <div class="decision-category-row cat-owner">
        <div class="decision-row-strategy-box">
          <div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
              <div class="decision-row-title">🏡 怡居大宅（自住）</div>
              <span class="decision-row-count-pill" style="background:#E0F2FE; color:#0369A1;">{len(projs_data['owner'])} 盘入选</span>
            </div>
            <div class="decision-row-strategy-text">
              <div><strong>【核心逻辑】</strong>聚焦低密纯粹圈层、名校网生态或稀缺景观，追求高隐私度与品质，长线保值抗跌。</div>
              <div><strong>【置业指引】</strong>首选中高楼层主力及特色单位，重点关注开阔景观、梯户比与会所圈层。</div>
            </div>
          </div>
          <div class="decision-row-profile-tag">
            🎯 <strong>客群画像：</strong>追求子女高阶教育与家族资产传承的顶净值家庭<br>
            💰 <strong>建议预算：</strong>约 $1,500万 - $8,000万 港币
          </div>
        </div>

        <div class="decision-row-projects-flow">
          {"".join([f'''
          <div class="proj-rich-card border-owner">
            <div class="card-top-row">
              <div class="card-img-wrap">
                <img src="{p['img']}" class="card-img" alt="{p['name']}" onerror="this.style.display='none'">
                <span class="card-img-badge">实景效果</span>
              </div>
              <div class="card-top-info">
                <div class="card-name-price">
                  <div class="card-name"><span style="color:#00889A;">#{p['idx']}</span> {p['name']}</div>
                  <div class="card-price" style="color:#0284C7;">{p['price']}</div>
                </div>
                <div class="card-tag-row">
                  {''.join([f'<span class="tag-pill" style="background:#E0F2FE; color:#0369A1;">{t}</span>' for t in p['tags']])}
                </div>
                <div class="card-meta-line">{p['meta']}</div>
              </div>
            </div>
            <div class="card-sqft-line">{p['sqft']}</div>
            <div class="card-highlight-line"><strong>【核心特质】</strong>{p['highlight']}</div>
          </div>
          ''' for p in projs_data['owner']])}
        </div>
      </div>

      <!-- 兼得平衡 -->
      <div class="decision-category-row cat-balanced">
        <div class="decision-row-strategy-box">
          <div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
              <div class="decision-row-title">⚖️ 兼得平衡（投资自住）</div>
              <span class="decision-row-count-pill" style="background:#DCFCE7; color:#15803D;">{len(projs_data['balanced'])} 盘入选</span>
            </div>
            <div class="decision-row-strategy-text">
              <div><strong>【核心逻辑】</strong>自住品质与资产流动性兼备的稳健底仓。紧邻核心轨交枢纽或综合体，进可攻退可守。</div>
              <div><strong>【置业指引】</strong>优先锁定主流 2-3 房主力户型，兼得便捷成熟配套与庞大承接流动性。</div>
            </div>
          </div>
          <div class="decision-row-profile-tag">
            🎯 <strong>客群画像：</strong>看重便利通勤自住、兼顾抗周期流动性保值的稳健买家<br>
            💰 <strong>建议预算：</strong>约 $700万 - $2,500万 港币
          </div>
        </div>

        <div class="decision-row-projects-flow">
          {"".join([f'''
          <div class="proj-rich-card border-balanced">
            <div class="card-top-row">
              <div class="card-img-wrap">
                <img src="{p['img']}" class="card-img" alt="{p['name']}" onerror="this.style.display='none'">
                <span class="card-img-badge">实景效果</span>
              </div>
              <div class="card-top-info">
                <div class="card-name-price">
                  <div class="card-name"><span style="color:#00889A;">#{p['idx']}</span> {p['name']}</div>
                  <div class="card-price" style="color:#16A34A;">{p['price']}</div>
                </div>
                <div class="card-tag-row">
                  {''.join([f'<span class="tag-pill" style="background:#DCFCE7; color:#15803D;">{t}</span>' for t in p['tags']])}
                </div>
                <div class="card-meta-line">{p['meta']}</div>
              </div>
            </div>
            <div class="card-sqft-line">{p['sqft']}</div>
            <div class="card-highlight-line"><strong>【核心特质】</strong>{p['highlight']}</div>
          </div>
          ''' for p in projs_data['balanced']])}
        </div>
      </div>
    </div>
  </div>

  <div class="page-footer">
    <span>蓝玛国际 LANDMA GLOBAL · 客户定制方案</span>
    <span>第 8 页 / 共 10 页</span>
  </div>
</div>

</body>
</html>
"""
    return html


# =========================================================================
# 生成方案二：【通栏策略横幅 + 宽幅自适应网格池（纯文字高密度）】
# =========================================================================
def build_option2_html(projs_data, title_suffix="4盘效果"):
    num_projs = len(projs_data["owner"]) + len(projs_data["balanced"])
    
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
{COMMON_CSS}

.verdict-sections-container {{
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
  min-height: 0;
}}

.cat-section-block {{
  background: #FFFFFF;
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0,0,0,0.02);
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}}

/* 方案二核心：通栏横幅 Banner */
.cat-section-banner {{
  padding: 6px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border);
}}

.cat-section-banner.banner-owner {{
  background: linear-gradient(90deg, #F0F9FF 0%, #E0F2FE 100%);
  border-left: 5px solid #0284C7;
}}
.cat-section-banner.banner-balanced {{
  background: linear-gradient(90deg, #F0FDF4 0%, #DCFCE7 100%);
  border-left: 5px solid #16A34A;
}}

.cat-banner-left {{
  display: flex;
  align-items: center;
  gap: 8px;
}}

.cat-banner-title {{
  font-family: 'Noto Serif SC', serif;
  font-size: 0.88rem;
  font-weight: 800;
  color: var(--slate-900);
}}

.cat-banner-count {{
  font-size: 0.62rem;
  font-weight: 700;
  padding: 1px 7px;
  border-radius: 10px;
}}

.cat-banner-strategy {{
  font-size: 0.63rem;
  color: var(--slate-700);
  display: flex;
  gap: 14px;
}}
.cat-banner-strategy strong {{ color: var(--slate-900); }}

/* 通栏卡片网格池 */
.cat-cards-grid-pool {{
  padding: 8px 12px;
  flex: 1;
  display: grid;
  grid-template-columns: repeat({2 if num_projs <= 4 else 3 if num_projs <= 6 else 4}, 1fr);
  gap: 10px;
  align-items: stretch;
  background: #FAFAFA;
}}

.opt2-pure-card {{
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  gap: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.03);
  border-top: 3px solid #CBD5E1;
}}
.opt2-border-owner {{ border-top-color: #0284C7; }}
.opt2-border-balanced {{ border-top-color: #16A34A; }}

.opt2-head-row {{
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}}
.opt2-name {{
  font-size: 0.86rem;
  font-weight: 800;
  color: var(--slate-900);
}}
.opt2-price {{
  font-size: 0.78rem;
  font-weight: 800;
}}

.opt2-tags-row {{
  display: flex;
  gap: 4px;
}}

.opt2-meta-grid {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px 10px;
  font-size: 0.63rem;
  color: #475569;
  background: #F8FAFC;
  padding: 6px 8px;
  border-radius: 4px;
  border: 1px solid #F1F5F9;
}}

.opt2-highlight-box {{
  font-size: 0.63rem;
  color: var(--slate-700);
  background: #F1F5F9;
  padding: 6px 10px;
  border-radius: 4px;
  line-height: 1.4;
  border-left: 3px solid var(--primary);
  flex: 1;
  display: flex;
  align-items: center;
}}
</style>
</head>
<body>

<div class="pdf-page">
  <div class="page-header">
    <div class="page-header-left">
      <span class="page-header-title">全案综合置业决策建议与终极选房指南</span>
      <span class="page-header-badge">建议二预览 · 通栏策略横幅与宽幅自适应网格池 ({title_suffix})</span>
    </div>
    <span style="font-size:0.75rem; font-weight:700; color:var(--primary);">LANDMA GLOBAL</span>
  </div>

  <div class="page-body">
    <div class="verdict-sec-title">
      <span>💡 蓝玛置业专家终极选房分类矩阵 (2大核心置业客群维度深度匹配)</span>
      <span class="verdict-sec-subtitle">全案入选 {num_projs} 个重点新盘 · 100% 宽幅满格展开 · 高度收敛不拉裂</span>
    </div>

    <div class="verdict-sections-container">
      <!-- 怡居大宅 -->
      <div class="cat-section-block">
        <div class="cat-section-banner banner-owner">
          <div class="cat-banner-left">
            <span class="cat-banner-title">🏡 怡居大宅（自住）</span>
            <span class="cat-banner-count" style="background:#E0F2FE; color:#0369A1;">{len(projs_data['owner'])} 盘入选</span>
          </div>
          <div class="cat-banner-strategy">
            <span><strong>【核心逻辑】</strong>聚焦低密纯粹圈层、名校网生态或稀缺自然景观，长线保值抗跌</span>
            <span><strong>【置业指引】</strong>首选中高楼层 3-4 房主力及特色单位，重点关注梯户比与圈层</span>
          </div>
        </div>

        <div class="cat-cards-grid-pool">
          {"".join([f'''
          <div class="opt2-pure-card opt2-border-owner">
            <div class="opt2-head-row">
              <div class="opt2-name"><span style="color:#00889A;">#{p['idx']}</span> {p['name']}</div>
              <div class="opt2-price" style="color:#0284C7;">{p['price']}</div>
            </div>
            <div class="opt2-tags-row">
              {''.join([f'<span class="tag-pill" style="background:#E0F2FE; color:#0369A1;">{t}</span>' for t in p['tags']])}
            </div>
            <div class="opt2-meta-grid">
              <div>{p['meta'].split(' · ')[0]}</div>
              <div>{p['meta'].split(' · ')[1]} · {p['meta'].split(' · ')[2]}</div>
              <div style="grid-column:span 2;">{p['sqft']}</div>
            </div>
            <div class="opt2-highlight-box">
              <strong>【核心特质】</strong>{p['highlight']}
            </div>
          </div>
          ''' for p in projs_data['owner']])}
        </div>
      </div>

      <!-- 兼得平衡 -->
      <div class="cat-section-block">
        <div class="cat-section-banner banner-balanced">
          <div class="cat-banner-left">
            <span class="cat-banner-title">⚖️ 兼得平衡（投资自住）</span>
            <span class="cat-banner-count" style="background:#DCFCE7; color:#15803D;">{len(projs_data['balanced'])} 盘入选</span>
          </div>
          <div class="cat-banner-strategy">
            <span><strong>【核心逻辑】</strong>自住品质与资产流动性兼备的稳健底仓，紧邻核心轨交枢纽，进退自如</span>
            <span><strong>【置业指引】</strong>优先锁定主流 2-3 房家庭主力户型，兼得成熟配套与庞大二手承接力</span>
          </div>
        </div>

        <div class="cat-cards-grid-pool">
          {"".join([f'''
          <div class="opt2-pure-card opt2-border-balanced">
            <div class="opt2-head-row">
              <div class="opt2-name"><span style="color:#00889A;">#{p['idx']}</span> {p['name']}</div>
              <div class="opt2-price" style="color:#16A34A;">{p['price']}</div>
            </div>
            <div class="opt2-tags-row">
              {''.join([f'<span class="tag-pill" style="background:#DCFCE7; color:#15803D;">{t}</span>' for t in p['tags']])}
            </div>
            <div class="opt2-meta-grid">
              <div>{p['meta'].split(' · ')[0]}</div>
              <div>{p['meta'].split(' · ')[1]} · {p['meta'].split(' · ')[2]}</div>
              <div style="grid-column:span 2;">{p['sqft']}</div>
            </div>
            <div class="opt2-highlight-box">
              <strong>【核心特质】</strong>{p['highlight']}
            </div>
          </div>
          ''' for p in projs_data['balanced']])}
        </div>
      </div>
    </div>
  </div>

  <div class="page-footer">
    <span>蓝玛国际 LANDMA GLOBAL · 客户定制方案</span>
    <span>第 8 页 / 共 10 页</span>
  </div>
</div>

</body>
</html>
"""
    return html


# 写入 4 个独立的 HTML 文件
files_to_render = [
    ("preview_opt1_4projs.html", build_option1_html(projs_4, "4盘效果"), "preview_opt1_4projs.png"),
    ("preview_opt1_8projs.html", build_option1_html(projs_8, "8盘效果"), "preview_opt1_8projs.png"),
    ("preview_opt2_4projs.html", build_option2_html(projs_4, "4盘效果"), "preview_opt2_4projs.png"),
    ("preview_opt2_8projs.html", build_option2_html(projs_8, "8盘效果"), "preview_opt2_8projs.png"),
]

for html_name, html_content, png_name in files_to_render:
    html_path = os.path.join(PREVIEW_DIR, html_name)
    png_path = os.path.join(PREVIEW_DIR, png_name)
    artifact_png_path = os.path.join(ARTIFACT_DIR, png_name)
    
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Written: {html_path}")
    
    # 使用 Chrome Headless 进行截图
    cmd = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless",
        "--disable-gpu",
        "--window-size=1200,850",
        f"--screenshot={png_path}",
        f"file://{html_path}"
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(f"Captured: {png_path}")
    
    # 拷贝一份到 artifact 目录供聊天内引用
    if os.path.exists(png_path):
        import shutil
        shutil.copyfile(png_path, artifact_png_path)
        print(f"Copied to artifact: {artifact_png_path}")

print("All previews generated successfully!")
