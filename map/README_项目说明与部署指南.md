# 🗺️ 香港一手新盘全景地图系统 (HK Map System) 完整源码与数据工程包

欢迎使用 **香港一手新盘全景地图系统**！本包包含了地图网站的完整前端应用、空间与业务数据、媒体切图、后台微服务接口以及数据处理/同步更新脚本。无论是在本地离线运行、内网私有化部署，还是托管在云端静态平台（GitHub Pages、Cloudflare Pages、Vercel、Nginx），均可开箱即用。

---

## ⚡ 3 秒极速上手 (Quick Start)

由于现代浏览器安全策略（CORS）限制直接通过 `file://` 协议加载本地 JSON/GeoJSON 数据，**请务必通过 HTTP 服务运行**：

### 方式一：推荐 - 使用自带后台服务启动 (支持坐标拖拽保存)
```bash
python3 server.py
```
终端将输出 `Starting server at http://localhost:8080`。  
在浏览器中打开：**`http://localhost:8080`**

### 方式二：标准静态 HTTP 服务启动
```bash
python3 -m http.server 8080
```
在浏览器中打开：**`http://localhost:8080`**

### 🔐 默认访问授权密码
- **进入密码**：`lm8888`
- *如需取消密码保护*：打开 `test_layout_floating.html`，搜索并注释掉包含 `TARGET_PWD = 'lm8888'` 的密码拦截逻辑代码块即可。

---

## 📂 源码与数据全景目录结构

```text
hk-map-source-bundle/
├── 🌐 前端展示层
│   ├── index.html                   # 门户重定向入口
│   ├── test_layout_floating.html    # 全景地图核心交互主页（Leaflet 地图、悬浮窗、5D 价值系统）
│   ├── export_presentation.html     # 演示方案与全景排版导出工具页
│   └── landma_logo.png              # 网站系统 Logo 标识
│
├── 📊 核心业务与销控数据
│   ├── data.json                    # 全港一手新盘销控总库（各楼盘户型、在售/已售、最新价单、成交）
│   ├── hk_districts_data.js         # 香港大区、分区、商圈层级与边界配置
│   ├── community_classification.json# 社区商圈归属、梯队与分级分类库
│   ├── 全港一手新盘空间区域与商圈归属重划表.xlsx # 商圈空间重划对照底表
│   ├── 导出方案项目描述库.xlsx      # 楼盘 5D 深度价值分析文案库
│   └── 楼盘卖点.xlsx                # 各楼盘核心亮点与营销卖点表
│
├── 🗺️ GIS 地理空间图层数据
│   ├── hong_kong_micro_districts.geojson # 156 个高精微片区矢量多边形边界 (WGS84)
│   ├── hk_project_coords.json       # 全量新盘项目经纬度坐标、商圈与元数据底表
│   ├── hk_mtr_stations.json         # 全港港铁 (MTR) 站点经纬度及换乘线数据
│   ├── hk_mtr_lines.json            # 全港港铁线路走势 GeoJSON
│   └── hk_landmarks.json            # 核心商圈地标、顶尖名校、医院、配套空间图层
│
├── 🖼️ 楼盘实景与切图资源
│   ├── project_images_manifest.json # 楼盘封面图与切图索引清单
│   └── images/
│       └── projects/
│           ├── hd/                  # 高清楼盘封面图 (WebP 格式，高保真画质)
│           └── thumb/               # 缩略图 (WebP 格式，极速秒开渲染)
│
├── ⚙️ 后台服务与自动化工具链
│   ├── server.py                    # 轻量 HTTP 运行服务（支持 /api/save_coords 坐标调整持久化）
│   ├── sync_from_prod.py            # 数据全自动同步与发布工作流（融合主站最新销控、智能坐标兜底）
│   ├── process_project_images.py    # 图片处理流水线（原图按规格压缩生成 WebP 和缩略图）
│   ├── calibrate_overlapping_coords.py # 密集重叠楼盘坐标智能碰撞避让算法
│   ├── patch_landmarks_meta.py      # 地标空间数据补全与权重注入工具
│   ├── process_mtr_data.py          # 港铁站点数据预处理与提取工具
│   └── optimize_data_files.py       # JSON 数据无损压缩与裁剪工具
│
└── 📐 香港区域划分 (独立 GIS 套件)
    ├── README.md                    # 156 个真实微型规划片区 GIS 数据规范说明
    ├── hong_kong_micro_districts.geojson       # WGS84 坐标系多边形
    ├── hong_kong_micro_districts_gcj02.geojson # GCJ-02 火星坐标系（适配高德/腾讯地图）
    ├── hong_kong_micro_districts.kml           # Google Earth / My Maps 专用 3D 边界
    ├── preview.html                 # 独立片区与楼盘空间漫游测试工具
    └── integration_snippet.js       # 纯前端即插即用片区渲染脚本
```

---

## 🛠️ 数据更新与二次开发说明

### 1. 调整楼盘地图坐标
- 运行 `python3 server.py` 开启本地服务。
- 在前端地图中开启开发者坐标微调模式，可直接拖动地图上的楼盘气泡图钉。
- 前端会调用 `POST /api/save_coords`，自动将新经纬度写入 `hk_project_coords.json`。
- 若存在同一商圈内多盘密集重叠，可运行 `python3 calibrate_overlapping_coords.py` 进行自动几何放射分散。

### 2. 更新一手新盘销控与价格
- 核心销控与房源价格数据存储于 `data.json`。
- 如果配合爬虫系统或主站数据库使用，运行 `python3 sync_from_prod.py`，脚本将自动进行销控对齐、字段清洗、智能坐标补全及版本刷新。

### 3. 添加新楼盘图片
- 将新拍摄或获取的楼盘图片放入工作目录。
- 执行 `python3 process_project_images.py`，程序将自动生成 `images/projects/hd/` 和 `thumb/` 并更新 `project_images_manifest.json`。

---

## 🚀 生产部署建议
1. **GitHub Pages**：直接推送至 GitHub 仓库根目录，在仓库设置中启用 Pages 即可上线。
2. **Nginx / Apache**：将解压后的所有文件部署至 Web 根目录，配置好 MIME 类型（特别是 `.json`, `.geojson`, `.webp`）和 CORS 头。
3. **Cloudflare Pages / Vercel**：选择静态站点部署，无需任何构建命令，输出目录选根目录即可。

祝使用愉快！
