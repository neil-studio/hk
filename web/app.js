// ==========================================================================
// 香港一手新盘一站通 - 核心逻辑 (Vanilla JS + Chart.js)
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
  // 1. 登录通行权限控制
  const loginOverlay = document.getElementById('loginOverlay');
  const loginCard = document.getElementById('loginCard');
  const passwordInput = document.getElementById('passwordInput');
  const loginBtn = document.getElementById('loginBtn');
  const loginErrorMsg = document.getElementById('loginErrorMsg');

  const isAuthenticated = localStorage.getItem('hk_property_auth') === 'true';
  if (loginOverlay) {
    if (isAuthenticated) {
      loginOverlay.classList.add('hidden');
    }

    loginBtn?.addEventListener?.('click', handleLogin);
    passwordInput?.addEventListener?.('keypress', (e) => {
      if (e.key === 'Enter') handleLogin();
    });
  }

  function handleLogin() {
    localStorage.setItem('hk_property_auth', 'true');
    if (loginOverlay) {
      loginOverlay.classList.add('hidden');
    }
  }

  // 2. 全局状态变量
  let allProjects = [];
  let globalStats = {};
  let projectsDataMap = {};
  let featuredByPriceData = {};
  let focusProjectsList = [];
  let currentWorkbook = null;
  let activeBuildingSheet = null;

  // 3. 抓取与加载元数据 (支持 window.APP_DATA 预载入 + fetch 双保底)
  async function loadData() {
    try {
      let data = window.APP_DATA;
      if (!data) {
        const resp = await fetch('data.json?v=' + Date.now());
        if (!resp.ok) throw new Error('无法读取 data.json 元数据');
        data = await resp.json();
      }

      allProjects = data.projects || [];
      globalStats = data.global_stats || {};
      projectsDataMap = data.projects_data || {};
      featuredByPriceData = data.featured_by_price || {};
      focusProjectsList = data.focus_projects || [];
      window.data_real_history = data.real_history_analytics || {};

      // 更新页头时间戳与统计看板
      updateGlobalBadges();

      // 依据 DOM 节点与路由分发渲染逻辑
      const path = (window.location && window.location.pathname) ? window.location.pathname : '';
      if (document.getElementById('promoFocusGrid')) {
        initIndexPage();
      }
      if (document.getElementById('projectGrid')) {
        initSalesPage();
      }
      if (path.includes('analytics.html') || document.getElementById('trendChart')) {
        initAnalyticsPage();
      }
      if (path.includes('featured.html') || document.getElementById('featuredCardGrid')) {
        initFeaturedPage();
      }

    } catch (err) {
      console.error('加载项目元数据失败:', err);
    }
  }

  // 更新顶栏时间戳与全站仪表盘
  function updateGlobalBadges() {
    const badge = document.getElementById('lastUpdatedBadge');
    if (badge && globalStats.last_updated) {
      badge.textContent = `数据更新: ${globalStats.last_updated}`;
    }

    const pElem = document.getElementById('statProjects');
    const uElem = document.getElementById('statUnits');
    const rElem = document.getElementById('statSoldRate');
    const sElem = document.getElementById('statOnSale');

    if (pElem) pElem.textContent = globalStats.total_projects || allProjects.length || 0;
    if (uElem) uElem.textContent = (globalStats.total_units || 0).toLocaleString();
    if (rElem) rElem.textContent = (globalStats.overall_sold_rate || 0) + '%';
    if (sElem) sElem.textContent = (globalStats.total_sale || 0).toLocaleString();
  }

  // ==========================================================================
  // A. 首页门户逻辑 (index.html)
  // ==========================================================================
  function initIndexPage() {
    const focusGrid = document.getElementById('promoFocusGrid');
    if (!focusGrid) return;

    focusGrid.innerHTML = '';
    const displayList = focusProjectsList.length > 0 ? focusProjectsList : ['天玺．天', 'Blue Coast', '瑜一．天海'];

    displayList.slice(0, 3).forEach((name, idx) => {
      const proj = allProjects.find(p => p.name === name) || {
        name: name,
        region: '九龙',
        district: '启德',
        stats: { sold_rate: 78.5, total: 900 }
      };

      const meta = projectsDataMap[name] || {
        grade: idx === 0 ? 'A+' : 'A',
        basic_info: '香港核心地段地标性旗舰新盘。',
        selling_points: '地铁无缝连接，海景大盘，升值空间高。'
      };

      const card = document.createElement('div');
      card.className = 'promotion-focus';
      card.innerHTML = `
        <div class="promo-focus-glow"></div>
        <div class="promo-focus-content">
          <div style="display:flex; justify-shadow:space-between; align-items:center;">
            <div class="promo-badge">🔥 焦点精选盘 #${idx + 1}</div>
            <span class="${meta.grade === 'A+' ? 'grade-badge-aplus' : 'grade-badge-a'}">${meta.grade || 'A+'}</span>
          </div>
          <h2 class="promo-focus-title" style="margin-top:0.4rem;">${proj.name}</h2>
          <div class="promo-focus-tags">
            <span class="promo-tag promo-region">${proj.region || '港岛'}</span>
            <span class="promo-tag promo-district">${proj.district || '核心区'}</span>
          </div>
          <p class="promo-focus-desc">${meta.selling_points || meta.basic_info}</p>
          <div class="promo-focus-stats" style="background:#f8fafc; padding:0.6rem; border-radius:10px; margin-bottom:0.8rem;">
            <div class="promo-stat-item">
              <span class="label" style="font-size:0.8rem; color:#64748b;">去化率:</span>
              <span class="val promo-rate" style="font-weight:700; color:#e11d48;">${proj.stats ? proj.stats.sold_rate : 75}%</span>
            </div>
            <div class="promo-stat-item">
              <span class="label" style="font-size:0.8rem; color:#64748b;">规划套数:</span>
              <span class="val promo-units" style="font-weight:700; color:#0f172a;">${proj.stats ? proj.stats.total : '-'}套</span>
            </div>
          </div>
          <a href="sales.html" class="btn btn-secondary" style="font-size:0.82rem; padding:0.4rem 0.8rem;">查看销控网格 →</a>
        </div>
      `;
      focusGrid.appendChild(card);
    });

    // 初始化首页热销排行榜与洞察
    initLeaderboard();
  }

  function initLeaderboard() {
    const container = document.getElementById('lbDisplayContainer');
    if (!container) return;

    const lbData = window.APP_DATA?.leaderboards || {};
    const optionsData = lbData.options || {};

    let currentTime = 'monthly'; // 'weekly', 'monthly', 'yearly'
    let currentCat = 'overall';
    let currentPeriodVal = '';

    const periodSelect = document.getElementById('lbPeriodSelect');
    const periodBadge = document.getElementById('lbPeriodBadge');

    const updateDropdownOptions = () => {
      if (!periodSelect) return;
      periodSelect.innerHTML = '';
      
      let list = [];
      if (currentTime === 'monthly') list = optionsData.months || [];
      else if (currentTime === 'weekly') list = optionsData.weeks || [];
      else if (currentTime === 'yearly') list = optionsData.years || [];

      list.forEach(opt => {
        const optionElem = document.createElement('option');
        optionElem.value = opt.val;
        optionElem.textContent = opt.label;
        periodSelect.appendChild(optionElem);
      });

      if (list.length > 0) {
        currentPeriodVal = list[0].val;
        periodSelect.value = currentPeriodVal;
      } else {
        currentPeriodVal = '';
      }
    };

    const render = () => {
      let timeMap = {};
      if (currentTime === 'monthly') timeMap = lbData.monthly_map || {};
      else if (currentTime === 'weekly') timeMap = lbData.weekly_map || {};
      else if (currentTime === 'yearly') timeMap = lbData.yearly_map || {};

      if (!currentPeriodVal && periodSelect && periodSelect.value) {
        currentPeriodVal = periodSelect.value;
      }

      const periodBundle = timeMap[currentPeriodVal] || (lbData[currentTime] ? lbData[currentTime] : {});
      const list = periodBundle[currentCat] || [];

      // 更新副标题显示
      if (periodBadge) {
        let labelText = '';
        if (periodSelect && periodSelect.options && periodSelect.selectedIndex >= 0) {
          labelText = periodSelect.options[periodSelect.selectedIndex].text;
        }
        periodBadge.innerHTML = `📅 统计时间: <span style="color:#0284c7; font-weight:700;">${labelText || '最新周期'}</span> (共收录 4.4万+ 条真实成交数据)`;
      }

      if (!list || list.length === 0) {
        container.innerHTML = `<div style="text-align:center; padding:2.5rem; color:#94a3b8; font-size:0.9rem;">该时间段及分类下暂无成交榜单记录</div>`;
        return;
      }

      const top3 = list.slice(0, 3);
      const rest = list.slice(3);

      let html = '<div class="podium-container">';

      // 2nd Place (Silver)
      if (top3[1]) {
        const item = top3[1];
        html += `
          <div class="podium-card podium-silver">
            <div class="podium-badge">🥈 亚军 Top 2</div>
            <div class="podium-project-name">${item.project_name}</div>
            <div class="podium-meta">${item.region} • ${item.district}</div>
            <div class="podium-stat-box">
              <div class="podium-stat-val">${item.volume} <span style="font-size:0.75rem; font-weight:normal; color:#64748b;">套成交</span></div>
              <div class="podium-stat-sub">均价: $${item.avg_price_wan || '-'}万 | $${item.avg_sqft ? item.avg_sqft.toLocaleString() : '-'}/呎</div>
            </div>
            <button onclick="goToProjectAnalytics('${item.project_name}')" class="btn-podium-trend" style="margin-top:0.6rem; padding:0.3rem 0.7rem; border-radius:6px; border:1px solid #0284c7; background:#ffffff; color:#0284c7; font-size:0.76rem; font-weight:700; cursor:pointer; display:inline-flex; align-items:center; gap:0.25rem;">📈 查看成交趋势</button>
          </div>
        `;
      }

      // 1st Place (Gold)
      if (top3[0]) {
        const item = top3[0];
        html += `
          <div class="podium-card podium-gold">
            <div class="podium-badge">🥇 冠军 Top 1</div>
            <div class="podium-project-name">${item.project_name}</div>
            <div class="podium-meta">${item.region} • ${item.district}</div>
            <div class="podium-stat-box">
              <div class="podium-stat-val">${item.volume} <span style="font-size:0.75rem; font-weight:normal; color:#64748b;">套成交</span></div>
              <div class="podium-stat-sub">均价: $${item.avg_price_wan || '-'}万 | $${item.avg_sqft ? item.avg_sqft.toLocaleString() : '-'}/呎</div>
            </div>
            <button onclick="goToProjectAnalytics('${item.project_name}')" class="btn-podium-trend" style="margin-top:0.6rem; padding:0.35rem 0.8rem; border-radius:6px; border:none; background:linear-gradient(135deg, #0284c7, #0369a1); color:#ffffff; font-size:0.78rem; font-weight:700; cursor:pointer; display:inline-flex; align-items:center; gap:0.25rem; box-shadow:0 2px 6px rgba(2,132,199,0.25);">📈 查看成交趋势</button>
          </div>
        `;
      }

      // 3rd Place (Bronze)
      if (top3[2]) {
        const item = top3[2];
        html += `
          <div class="podium-card podium-bronze">
            <div class="podium-badge">🥉 季军 Top 3</div>
            <div class="podium-project-name">${item.project_name}</div>
            <div class="podium-meta">${item.region} • ${item.district}</div>
            <div class="podium-stat-box">
              <div class="podium-stat-val">${item.volume} <span style="font-size:0.75rem; font-weight:normal; color:#64748b;">套成交</span></div>
              <div class="podium-stat-sub">均价: $${item.avg_price_wan || '-'}万 | $${item.avg_sqft ? item.avg_sqft.toLocaleString() : '-'}/呎</div>
            </div>
            <button onclick="goToProjectAnalytics('${item.project_name}')" class="btn-podium-trend" style="margin-top:0.6rem; padding:0.3rem 0.7rem; border-radius:6px; border:1px solid #0284c7; background:#ffffff; color:#0284c7; font-size:0.76rem; font-weight:700; cursor:pointer; display:inline-flex; align-items:center; gap:0.25rem;">📈 查看成交趋势</button>
          </div>
        `;
      }

      html += '</div>';

      // 4th to 10th Place List
      if (rest.length > 0) {
        html += '<div class="leaderboard-rest-grid">';
        rest.forEach((item, idx) => {
          const rank = idx + 4;
          html += `
            <div class="rank-list-item">
              <span class="rank-num">#${rank}</span>
              <div class="rank-info">
                <span class="rank-title">${item.project_name}</span>
                <span class="rank-tag">${item.region} ${item.district}</span>
              </div>
              <div class="rank-metrics" style="display:flex; align-items:center; gap:0.6rem;">
                <div>
                  <span class="rank-vol"><strong>${item.volume}</strong> 套</span>
                  <span class="rank-sqft">$${item.avg_sqft ? item.avg_sqft.toLocaleString() : '-'}/呎</span>
                </div>
                <button onclick="goToProjectAnalytics('${item.project_name}')" style="border:1px solid #0284c7; background:#f0f9ff; color:#0284c7; font-size:0.75rem; font-weight:700; padding:0.25rem 0.55rem; border-radius:6px; cursor:pointer; white-space:nowrap;">📈 趋势</button>
              </div>
            </div>
          `;
        });
        html += '</div>';
      }

      container.innerHTML = html;
    };

    // 绑定下拉切换事件
    if (periodSelect) {
      periodSelect.addEventListener('change', (e) => {
        currentPeriodVal = e.target.value;
        render();
      });
    }

    // 绑定时间 Tabs
    document.querySelectorAll('#lbTimeTabs .time-tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#lbTimeTabs .time-tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentTime = btn.dataset.time || 'monthly';
        updateDropdownOptions();
        render();
      });
    });

    // 绑定分类 Tabs
    document.querySelectorAll('#lbCategoryBar .cat-tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('#lbCategoryBar .cat-tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentCat = btn.dataset.cat || 'overall';
        render();
      });
    });

    // 初始化下拉菜单与视图
    updateDropdownOptions();
    render();
  }

  // 全局调取项目成交走势函数
  window.goToProjectAnalytics = (projName) => {
    if (typeof window.openAnalyticsModal === 'function') {
      window.openAnalyticsModal(projName);
    } else {
      window.location.href = `analytics.html?project=${encodeURIComponent(projName)}`;
    }
  };

  // 点击榜单直接定位唤起盘源 Modal
  window.openProjectGrid = (projName) => {
    const proj = allProjects.find(p => p.name === projName || projName.includes(p.name));
    if (proj && proj.excel_file) {
      if (typeof openGridModal === 'function') {
        openGridModal(proj.excel_file, proj.name);
      } else {
        window.location.href = `sales.html?search=${encodeURIComponent(proj.name)}`;
      }
    } else {
      window.location.href = `sales.html?search=${encodeURIComponent(projName)}`;
    }
  };

  // ==========================================================================
  // B. 销控查询专页逻辑 (sales.html)
  // ==========================================================================
  let activeRegion = 'all';
  let activeDistrict = 'all';
  let searchQuery = '';
  let activeSort = 'default';

  function initSalesPage() {
    const searchInput = document.getElementById('searchInput');
    const regionButtons = document.querySelectorAll('#regionFilter .filter-btn');
    const districtSelect = document.getElementById('districtFilter');
    const sortSelect = document.getElementById('sortFilter');

    // 填充商圈下拉
    if (districtSelect) {
      const districts = Array.from(new Set(allProjects.map(p => p.district))).filter(Boolean);
      districtSelect.innerHTML = '<option value="all">所有商圈</option>';
      districts.forEach(d => {
        const opt = document.createElement('option');
        opt.value = d;
        opt.textContent = d;
        districtSelect.appendChild(opt);
      });

      districtSelect.addEventListener('change', (e) => {
        activeDistrict = e.target.value;
        renderProjects();
      });
    }

    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        searchQuery = e.target.value.toLowerCase().trim();
        renderProjects();
      });
    }

    regionButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        regionButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        activeRegion = btn.getAttribute('data-region');
        renderProjects();
      });
    });

    if (sortSelect) {
      sortSelect.addEventListener('change', (e) => {
        activeSort = e.target.value;
        renderProjects();
      });
    }

    // Modal 关闭事件
    const closeModalBtn = document.getElementById('closeModalBtn');
    const gridModal = document.getElementById('gridModal');
    if (closeModalBtn && gridModal) {
      closeModalBtn.addEventListener('click', () => gridModal.classList.remove('open'));
    }

    // 初始渲染
    renderProjects();

    // 检查 URL 是否包含带参跳转项目 (打通跨页面数据)
    const urlParams = new URLSearchParams(window.location.search);
    const targetProjectName = urlParams.get('project');
    if (targetProjectName) {
      const proj = allProjects.find(p => p.name === targetProjectName);
      if (proj) {
        openGridModal(proj.filename, proj.name);
      }
    }
  }

  function renderProjects() {
    const grid = document.getElementById('projectGrid');
    if (!grid) return;

    const pinyinAliasMap = {
      'qide': '启德', 'qd': '启德',
      'huangzhukeng': '黄竹坑', 'hzk': '黄竹坑',
      'hewentian': '何文田', 'hwt': '何文田',
      'wangjiao': '旺角', 'wj': '旺角',
      'hongkan': '红磡', 'hk': '红磡',
      'beijiao': '北角', 'bj': '北角',
      'jiulong': '九龙', 'jl': '九龙',
      'gangdao': '港岛', 'gd': '港岛',
      'changshawan': '长沙湾', 'csw': '长沙湾',
      'jianidecheng': '坚尼地城', 'jndc': '坚尼地城',
      'chizhu': '赤柱', 'shanding': '山顶',
      'banshan': '半山', 'wanzai': '湾仔',
      'shaojiwan': '筲箕湾', 'paomadi': '跑马地', 'tongluowan': '铜锣湾'
    };

    const expandedQuery = pinyinAliasMap[searchQuery] || searchQuery;

    let filtered = allProjects.filter(p => {
      const matchRegion = activeRegion === 'all' || p.region === activeRegion;
      const matchDistrict = activeDistrict === 'all' || p.district === activeDistrict;
      const matchSearch = !searchQuery || 
        p.name.toLowerCase().includes(searchQuery) || 
        p.name.toLowerCase().includes(expandedQuery) ||
        (p.district && (p.district.toLowerCase().includes(searchQuery) || p.district.includes(expandedQuery))) ||
        (p.region && (p.region.toLowerCase().includes(searchQuery) || p.region.includes(expandedQuery)));
      return matchRegion && matchDistrict && matchSearch;
    });

    // 排序
    if (activeSort === 'rate-desc') filtered.sort((a, b) => (b.stats?.sold_rate || 0) - (a.stats?.sold_rate || 0));
    if (activeSort === 'rate-asc') filtered.sort((a, b) => (a.stats?.sold_rate || 0) - (b.stats?.sold_rate || 0));
    if (activeSort === 'units-desc') filtered.sort((a, b) => (b.stats?.total || 0) - (a.stats?.total || 0));
    if (activeSort === 'sale-desc') filtered.sort((a, b) => (b.stats?.sale || 0) - (a.stats?.sale || 0));

    grid.innerHTML = '';
    if (filtered.length === 0) {
      grid.innerHTML = `
        <div class="no-results" style="grid-column: 1/-1; text-align:center; padding:3rem; color:#64748b;">
          <h3>未找到匹配的项目</h3>
          <p>尝试切换筛选区域或清空搜索关键字</p>
        </div>
      `;
      return;
    }

    filtered.forEach(p => {
      const card = document.createElement('div');
      const isSuspended = p.is_suspended || p.sell_status === 'sales_suspended' || (p.stats && p.stats.stopped > 0 && p.stats.sale === 0);
      const isComingSoon = p.is_coming_soon || p.sell_status === 'coming_soon';
      const isRegistration = p.is_registration || p.sell_status === 'registration';

      card.className = 'project-card' + (isSuspended ? ' suspended-card' : '');

      let statusBadge = '';
      if (isSuspended) {
        statusBadge = '<span class="badge badge-suspended">⛔ 暂停销售</span>';
      } else if (isComingSoon) {
        statusBadge = '<span class="badge badge-coming-soon">🕒 即将发售</span>';
      } else if (isRegistration) {
        statusBadge = '<span class="badge badge-registration">📝 意向登记</span>';
      }

      let suspendedBanner = '';
      if (isSuspended) {
        suspendedBanner = '<div class="card-suspended-banner">⛔ 官方暂停销售 (Sales Suspended)</div>';
      }

      const soldRate = p.stats ? p.stats.sold_rate : 0;
      const totalUnits = p.stats ? p.stats.total : 0;
      const onSaleUnits = p.stats ? p.stats.sale : 0;
      const soldUnits = p.stats ? p.stats.sold : 0;
      const stoppedUnits = p.stats ? p.stats.stopped : 0;

      const stoppedHtml = stoppedUnits > 0 ? `<div class="stat-item" style="color:#ca8a04;"><span class="lbl">暂停销售:</span><span class="val" style="font-weight:700;">${stoppedUnits}</span></div>` : '';

      card.innerHTML = `
        ${suspendedBanner}
        <div class="card-header">
          <div class="card-meta">
            <span class="badge badge-region">${p.region}</span>
            <span class="badge badge-district">${p.district}</span>
            ${statusBadge}
          </div>
          <h3 class="project-title">${p.name}</h3>
        </div>
        <div class="card-body">
          <div class="sold-progress-area">
            <div class="progress-info">
              <span class="progress-label">去化率</span>
              <span class="progress-val">${soldRate}%</span>
            </div>
            <div class="progress-bar-bg">
              <div class="progress-bar-fill" style="width: ${soldRate}%;"></div>
            </div>
          </div>
          <div class="card-stats">
            <div class="stat-item"><span class="lbl">规划总套数:</span><span class="val">${totalUnits}</span></div>
            <div class="stat-item sale-count"><span class="lbl">在售套数:</span><span class="val">${onSaleUnits}</span></div>
            <div class="stat-item sold-count"><span class="lbl">已售套数:</span><span class="val">${soldUnits}</span></div>
            ${stoppedHtml}
            <div class="stat-item"><span class="lbl">最新更新:</span><span class="val">${p.last_updated || '近期'}</span></div>
          </div>
        </div>
        <div class="card-footer">
          <button class="btn btn-primary btn-open-grid" data-filename="${p.filename}" data-name="${p.name}">🔍 销控网格图</button>
          <a href="featured.html" class="btn btn-secondary">💎 查看评级</a>
        </div>
      `;
      grid.appendChild(card);
    });

    // 绑定销控网格预览事件
    document.querySelectorAll('.btn-open-grid').forEach(btn => {
      btn.addEventListener('click', () => {
        const filename = btn.getAttribute('data-filename');
        const name = btn.getAttribute('data-name');
        openGridModal(filename, name);
      });
    });
  }

  // 按项目名调取 销控 Modal
  window.openGridModalByName = function(projectName) {
    const proj = allProjects.find(p => p.name === projectName || p.name.includes(projectName.split(' ')[0]));
    if (proj) {
      openGridModal(proj.filename, proj.name);
    } else {
      alert('暂未检索到该项目的销控图纸');
    }
  };

  // ==========================================================================
  // 悬浮式历史成交走势分析 Modal (不用离开当前页面)
  // ==========================================================================
  let modalTrendChartInstance = null;
  let modalLayoutPieInstance = null;
  let modalPriceDistInstance = null;

  window.openAnalyticsModal = function(projectName, mode = 'exact', gran = 'monthly') {
    if (!projectName) return;

    let analyticsModal = document.getElementById('analyticsModal');
    if (!analyticsModal) {
      analyticsModal = document.createElement('div');
      analyticsModal.className = 'modal-overlay';
      analyticsModal.id = 'analyticsModal';
      analyticsModal.innerHTML = `
        <div class="modal-container" style="max-width:960px; width:92vw; max-height:92vh; border-radius:24px; display:flex; flex-direction:column; background:#ffffff; overflow:hidden;">
          <header class="modal-header" style="padding:1.2rem 1.8rem; border-bottom:1px solid #e2e8f0; display:flex; justify-content:space-between; align-items:center; background:#ffffff;">
            <div>
              <h2 id="analyticsModalTitle" style="font-size:1.3rem; font-weight:800; color:#0f172a; margin:0;">历史成交走势分析</h2>
              <div id="analyticsModalSubtitle" style="font-size:0.82rem; color:#64748b; margin-top:0.3rem;">调取 3.7万+ 条真实离线注册成交库数据</div>
            </div>
            <button class="close-btn" id="closeAnalyticsModalBtn" style="background:#f1f5f9; border:none; border-radius:50%; width:36px; height:36px; cursor:pointer; font-size:1.2rem; display:flex; align-items:center; justify-content:center; color:#64748b;">✕</button>
          </header>
          <div class="modal-content" style="padding:1.5rem 1.8rem; overflow-y:auto; flex:1; background:#f8fafc;">
            <div id="analyticsModalStats" style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:1rem; margin-bottom:1.5rem;"></div>
            
            <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:16px; padding:1.2rem; margin-bottom:1.5rem; box-shadow:0 2px 8px rgba(0,0,0,0.03);">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem; flex-wrap:wrap; gap:0.5rem;">
                <h4 style="font-size:0.95rem; font-weight:700; color:#0f172a; margin:0;">📈 历史成交均价与套数走势图表</h4>
                <div id="modalGranularityContainer" style="display:inline-flex; align-items:center; background:#f1f5f9; padding:0.2rem; border-radius:10px; border:1px solid #cbd5e1;">
                  <button id="modalGranMonthlyBtn" style="border:none; padding:0.3rem 0.85rem; border-radius:8px; font-size:0.78rem; font-weight:700; cursor:pointer; transition:all 0.2s;">📅 月度走势</button>
                  <button id="modalGranWeeklyBtn" style="border:none; padding:0.3rem 0.85rem; border-radius:8px; font-size:0.78rem; font-weight:700; cursor:pointer; transition:all 0.2s;">📊 周度走势</button>
                </div>
              </div>
              <div style="height:300px; position:relative;">
                <canvas id="modalTrendChartCanvas"></canvas>
              </div>
            </div>

            <div style="display:grid; grid-template-columns:1fr 1fr; gap:1.2rem;">
              <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:16px; padding:1.2rem; box-shadow:0 2px 8px rgba(0,0,0,0.03);">
                <h4 style="font-size:0.9rem; font-weight:700; color:#0f172a; margin:0 0 0.8rem 0;">🍰 成交户型分布</h4>
                <div style="height:210px; position:relative;">
                  <canvas id="modalLayoutPieCanvas"></canvas>
                </div>
              </div>
              <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:16px; padding:1.2rem; box-shadow:0 2px 8px rgba(0,0,0,0.03);">
                <h4 style="font-size:0.9rem; font-weight:700; color:#0f172a; margin:0 0 0.8rem 0;">📊 总价分布直方图 (万元)</h4>
                <div style="height:210px; position:relative;">
                  <canvas id="modalPriceDistCanvas"></canvas>
                </div>
              </div>
            </div>
          </div>
        </div>
      `;
      document.body.appendChild(analyticsModal);
    }

    const closeBtn = document.getElementById('closeAnalyticsModalBtn');
    if (closeBtn) {
      closeBtn.onclick = () => analyticsModal.classList.remove('open');
    }
    analyticsModal.onclick = (e) => {
      if (e.target === analyticsModal) analyticsModal.classList.remove('open');
    };

    // 绑定周度/月度走势切换按钮事件与高亮
    const btnM = document.getElementById('modalGranMonthlyBtn');
    const btnW = document.getElementById('modalGranWeeklyBtn');
    if (btnM && btnW) {
      if (gran === 'weekly') {
        btnM.style.background = 'transparent'; btnM.style.color = '#64748b'; btnM.style.boxShadow = 'none';
        btnW.style.background = '#ffffff'; btnW.style.color = '#06AABD'; btnW.style.boxShadow = '0 1px 4px rgba(0,0,0,0.1)';
      } else {
        btnM.style.background = '#ffffff'; btnM.style.color = '#06AABD'; btnM.style.boxShadow = '0 1px 4px rgba(0,0,0,0.1)';
        btnW.style.background = 'transparent'; btnW.style.color = '#64748b'; btnW.style.boxShadow = 'none';
      }
      btnM.onclick = () => window.openAnalyticsModal(projectName, mode, 'monthly');
      btnW.onclick = () => window.openAnalyticsModal(projectName, mode, 'weekly');
    }

    const titleElem = document.getElementById('analyticsModalTitle');
    const subtitleElem = document.getElementById('analyticsModalSubtitle');
    if (titleElem) titleElem.textContent = `${projectName} - 历史成交走势分析`;

    // 从 real_history_analytics 获取全量 3.7万+ 离线数据库
    const rh = (window.APP_DATA && window.APP_DATA.real_history_analytics) ? window.APP_DATA.real_history_analytics : {};
    const normalize = (s) => String(s || '').replace(/[\s\.\．\・\-\_\(\)\（\）]/g, '').toLowerCase();

    const getProjectCoreTitle = (name) => {
      let s = String(name || '').trim();
      s = s.replace(/(第?\s*[0-9A-Za-z一二三四五六七八九十]+期|\b[IVXLCDM]+\b|\b\d+\b)/gi, '').trim();
      s = normalize(s);
      if (!s) s = normalize(name);
      return s;
    };

    const targetNorm = normalize(projectName);
    const targetCore = getProjectCoreTitle(projectName);

    // 1. 精确期数匹配 (默认模式：绝对防止不同期数成交混淆)
    const exactKey = Object.keys(rh).find(k => k === projectName || normalize(k) === targetNorm);
    
    // 2. 社区全期数列表 (查阅宏观全社区走势)
    const communityKeys = Object.keys(rh).filter(k => {
      const kNorm = normalize(k);
      const kCore = getProjectCoreTitle(k);
      return k === projectName || kNorm === targetNorm || (targetCore.length >= 3 && kCore === targetCore);
    });

    // 确定当前视图要处理的数据 Keys
    let activeKeys = [];
    if (mode === 'community') {
      activeKeys = communityKeys;
    } else {
      activeKeys = exactKey ? [exactKey] : (communityKeys.length ? [communityKeys[0]] : []);
    }

    // 渲染分期切换按钮 (如果包含多个期数)
    if (subtitleElem) {
      if (communityKeys.length > 1) {
        subtitleElem.innerHTML = `
          <div style="display:inline-flex; align-items:center; gap:0.4rem; background:#e2e8f0; padding:0.2rem 0.4rem; border-radius:8px; margin-top:0.2rem;">
            <button onclick="openAnalyticsModal('${projectName}', 'exact', '${gran}')" style="border:none; background:${mode !== 'community' ? '#ffffff' : 'transparent'}; color:${mode !== 'community' ? '#06AABD' : '#64748b'}; font-weight:${mode !== 'community' ? '700' : '500'}; padding:0.25rem 0.6rem; border-radius:6px; cursor:pointer; font-size:0.78rem; box-shadow:${mode !== 'community' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none'};">📍 仅本期数 (${exactKey || projectName})</button>
            <button onclick="openAnalyticsModal('${projectName}', 'community', '${gran}')" style="border:none; background:${mode === 'community' ? '#ffffff' : 'transparent'}; color:${mode === 'community' ? '#06AABD' : '#64748b'}; font-weight:${mode === 'community' ? '700' : '500'}; padding:0.25rem 0.6rem; border-radius:6px; cursor:pointer; font-size:0.78rem; box-shadow:${mode === 'community' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none'};">🌐 包含社区全期数 (全${communityKeys.length}期)</button>
          </div>
        `;
      } else {
        subtitleElem.textContent = '调取 3.7万+ 条真实离线注册成交库数据';
      }
    }

    let totalVolume = 0;
    let minUprice = Infinity;
    let maxUprice = 0;
    const trendCombined = {};
    const layoutCombined = {};
    const priceDistCombined = {};

    activeKeys.forEach(key => {
      const projData = rh[key];
      if (!projData) return;

      const timeMap = (gran === 'weekly' && projData.weekly && Object.keys(projData.weekly).length > 0)
        ? projData.weekly
        : (projData.monthly || {});

      Object.keys(timeMap).forEach(tKey => {
        const tData = timeMap[tKey];
        if (!trendCombined[tKey]) trendCombined[tKey] = { volume: 0, totalSqft: 0, countSqft: 0 };
        trendCombined[tKey].volume += tData.volume || 0;
        if (tData.avg_uprice > 0) {
          trendCombined[tKey].totalSqft += tData.avg_uprice * (tData.volume || 1);
          trendCombined[tKey].countSqft += (tData.volume || 1);
        }
        totalVolume += tData.volume || 0;
        if (tData.min_uprice && tData.min_uprice < minUprice) minUprice = tData.min_uprice;
        if (tData.max_uprice && tData.max_uprice > maxUprice) maxUprice = tData.max_uprice;
      });

      if (projData.layouts) {
        Object.keys(projData.layouts).forEach(l => {
          layoutCombined[l] = (layoutCombined[l] || 0) + projData.layouts[l];
        });
      }

      if (projData.price_ranges) {
        Object.keys(projData.price_ranges).forEach(pr => {
          priceDistCombined[pr] = (priceDistCombined[pr] || 0) + projData.price_ranges[pr];
        });
      }
    });

    // 计算总平均呎价
    const trendKeys = Object.keys(trendCombined).sort();
    let globalSqftSum = 0, globalSqftVol = 0;
    trendKeys.forEach(k => {
      globalSqftSum += trendCombined[k].totalSqft;
      globalSqftVol += trendCombined[k].countSqft;
    });
    const avgSqftPrice = globalSqftVol > 0 ? Math.round(globalSqftSum / globalSqftVol) : 0;

    // 渲染 KPI 统计面板
    const statsContainer = document.getElementById('analyticsModalStats');
    if (statsContainer) {
      if (totalVolume === 0) {
        statsContainer.innerHTML = `<div style="grid-column:1/-1; padding:1.5rem; text-align:center; color:#94a3b8; background:#ffffff; border-radius:12px; border:1px solid #e2e8f0;">暂未检索到该项目的历史登记成交记录</div>`;
      } else {
        statsContainer.innerHTML = `
          <div style="background:#e6f7f9; border:1px solid #b3ebf2; padding:0.9rem 1.1rem; border-radius:14px;">
            <div style="font-size:0.78rem; color:#045d68; font-weight:600;">累计登记成交套数</div>
            <div style="font-size:1.4rem; font-weight:800; color:#06AABD; margin-top:0.2rem;">${totalVolume} 套</div>
          </div>
          <div style="background:#f0fdf4; border:1px solid #bbf7d0; padding:0.9rem 1.1rem; border-radius:14px;">
            <div style="font-size:0.78rem; color:#166534; font-weight:600;">历史成交均价</div>
            <div style="font-size:1.4rem; font-weight:800; color:#15803d; margin-top:0.2rem;">$${avgSqftPrice.toLocaleString()}/呎</div>
          </div>
          <div style="background:#fff1f2; border:1px solid #fecdd3; padding:0.9rem 1.1rem; border-radius:14px;">
            <div style="font-size:0.78rem; color:#9f1239; font-weight:600;">极值呎价范围</div>
            <div style="font-size:1.2rem; font-weight:800; color:#e11d48; margin-top:0.2rem;">$${minUprice === Infinity ? '-' : Math.round(minUprice).toLocaleString()} ~ $${Math.round(maxUprice).toLocaleString()}/呎</div>
          </div>
          <div style="background:#ffffff; border:1px solid #e2e8f0; padding:0.9rem 1.1rem; border-radius:14px;">
            <div style="font-size:0.78rem; color:#64748b; font-weight:600;">覆盖盘源分期</div>
            <div style="font-size:0.92rem; font-weight:700; color:#1e293b; margin-top:0.2rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${activeKeys.join(', ')}</div>
          </div>
        `;
      }
    }

    // 绘制 Chart.js 图表
    renderModalCharts(trendKeys, trendCombined, layoutCombined, priceDistCombined, gran);

    // 打开 Modal
    analyticsModal.classList.add('open');
  };

  // 渲染上下两行分组图例（第一行：成交套数 | 第二行：实用呎价）
  function render2RowTrendLegend(containerId, chartInstance, datasets) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';
    container.style.display = 'flex';
    container.style.flexDirection = 'column';
    container.style.gap = '0.5rem';
    container.style.padding = '0.6rem 0.9rem';
    container.style.background = '#f8fafc';
    container.style.borderRadius = '8px';
    container.style.marginBottom = '0.8rem';
    container.style.border = '1px solid #e2e8f0';

    const barItems = [];
    const lineItems = [];

    datasets.forEach((ds, idx) => {
      const isBar = ds.type === 'bar' || (ds.label && ds.label.includes('套数'));
      if (isBar) {
        barItems.push({ ds, idx });
      } else {
        lineItems.push({ ds, idx });
      }
    });

    // 第一行：项目成交套数 (柱状)
    const row1 = document.createElement('div');
    row1.style.display = 'flex';
    row1.style.alignItems = 'center';
    row1.style.flexWrap = 'wrap';
    row1.style.gap = '0.4rem 1.2rem';

    const row1Title = document.createElement('div');
    row1Title.style.fontWeight = '700';
    row1Title.style.fontSize = '0.82rem';
    row1Title.style.color = '#06AABD';
    row1Title.style.minWidth = '115px';
    row1Title.innerHTML = '📊 项目成交套数:';
    row1.appendChild(row1Title);

    barItems.forEach(item => {
      const el = document.createElement('div');
      el.style.display = 'inline-flex';
      el.style.alignItems = 'center';
      el.style.gap = '0.35rem';
      el.style.cursor = 'pointer';
      el.style.userSelect = 'none';
      el.style.fontSize = '0.8rem';
      el.style.color = '#334155';
      el.style.fontWeight = '600';

      const isVisible = chartInstance.isDatasetVisible(item.idx);
      if (!isVisible) el.style.opacity = '0.35';

      const colorBox = document.createElement('span');
      colorBox.style.width = '12px';
      colorBox.style.height = '10px';
      colorBox.style.borderRadius = '2px';
      colorBox.style.background = item.ds.backgroundColor || item.ds.borderColor || '#06AABD';
      colorBox.style.border = `1px solid ${item.ds.borderColor || '#06AABD'}`;

      const label = document.createElement('span');
      label.textContent = item.ds.label;

      el.appendChild(colorBox);
      el.appendChild(label);

      el.addEventListener('click', () => {
        const v = chartInstance.isDatasetVisible(item.idx);
        chartInstance.setDatasetVisibility(item.idx, !v);
        chartInstance.update();
        render2RowTrendLegend(containerId, chartInstance, datasets);
      });

      row1.appendChild(el);
    });

    // 第二行：项目成交呎价 (折线)
    const row2 = document.createElement('div');
    row2.style.display = 'flex';
    row2.style.alignItems = 'center';
    row2.style.flexWrap = 'wrap';
    row2.style.gap = '0.4rem 1.2rem';

    const row2Title = document.createElement('div');
    row2Title.style.fontWeight = '700';
    row2Title.style.fontSize = '0.82rem';
    row2Title.style.color = '#e11d48';
    row2Title.style.minWidth = '115px';
    row2Title.innerHTML = '📈 项目成交呎价:';
    row2.appendChild(row2Title);

    lineItems.forEach(item => {
      const el = document.createElement('div');
      el.style.display = 'inline-flex';
      el.style.alignItems = 'center';
      el.style.gap = '0.35rem';
      el.style.cursor = 'pointer';
      el.style.userSelect = 'none';
      el.style.fontSize = '0.8rem';
      el.style.color = '#334155';
      el.style.fontWeight = '600';

      const isVisible = chartInstance.isDatasetVisible(item.idx);
      if (!isVisible) el.style.opacity = '0.35';

      const lineBox = document.createElement('span');
      lineBox.style.width = '14px';
      lineBox.style.height = '3px';
      lineBox.style.borderRadius = '1px';
      lineBox.style.background = item.ds.borderColor || '#e11d48';

      const label = document.createElement('span');
      label.textContent = item.ds.label;

      el.appendChild(lineBox);
      el.appendChild(label);

      el.addEventListener('click', () => {
        const v = chartInstance.isDatasetVisible(item.idx);
        chartInstance.setDatasetVisibility(item.idx, !v);
        chartInstance.update();
        render2RowTrendLegend(containerId, chartInstance, datasets);
      });

      row2.appendChild(el);
    });

    container.appendChild(row1);
    container.appendChild(row2);
  }

  function renderModalCharts(trendKeys, trendCombined, layoutCombined, priceDistCombined, gran = 'monthly') {
    if (typeof Chart === 'undefined') return;

    const avgPrices = trendKeys.map(k => trendCombined[k].countSqft ? Math.round(trendCombined[k].totalSqft / trendCombined[k].countSqft) : 0);
    const volumes = trendKeys.map(k => trendCombined[k].volume);
    const timeLabelSuffix = gran === 'weekly' ? ' (周度)' : ' (月度)';

    const trendCtx = document.getElementById('modalTrendChartCanvas');
    if (trendCtx) {
      // 动态确保容器存在
      let modalLegendContainer = document.getElementById('modalTrendChartCustomLegend');
      if (!modalLegendContainer && trendCtx.parentNode) {
        modalLegendContainer = document.createElement('div');
        modalLegendContainer.id = 'modalTrendChartCustomLegend';
        trendCtx.parentNode.insertBefore(modalLegendContainer, trendCtx);
      }

      if (modalTrendChartInstance) modalTrendChartInstance.destroy();
      const modalDatasets = [
        {
          label: `实用呎价 (港币/呎${timeLabelSuffix})`,
          data: avgPrices,
          borderColor: '#06AABD',
          backgroundColor: 'rgba(6, 170, 189, 0.08)',
          borderWidth: 2.5,
          tension: 0.4,
          pointRadius: 4,
          pointHoverRadius: 7,
          pointBackgroundColor: '#ffffff',
          pointBorderColor: '#06AABD',
          pointBorderWidth: 2,
          fill: true,
          yAxisID: 'y'
        },
        {
          label: `成交套数 (套${timeLabelSuffix})`,
          data: volumes,
          type: 'bar',
          backgroundColor: 'rgba(225, 29, 72, 0.3)',
          borderColor: '#e11d48',
          borderWidth: 1.5,
          borderRadius: { topLeft: 6, topRight: 6, bottomLeft: 0, bottomRight: 0 },
          maxBarThickness: 16,
          barPercentage: 0.5,
          categoryPercentage: 0.7,
          yAxisID: 'y1'
        }
      ];

      modalTrendChartInstance = new Chart(trendCtx, {
        type: 'line',
        data: {
          labels: trendKeys,
          datasets: modalDatasets
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false }
          },
          scales: {
            y: { type: 'linear', position: 'left', title: { display: true, text: '呎价 ($/呎)' }, grid: { color: 'rgba(226, 232, 240, 0.6)' } },
            y1: {
              type: 'linear',
              position: 'right',
              grid: { drawOnChartArea: false },
              title: { display: true, text: '套数' },
              beginAtZero: true,
              ticks: { precision: 0 }
            }
          }
        }
      });

      render2RowTrendLegend('modalTrendChartCustomLegend', modalTrendChartInstance, modalDatasets);
    }

    // 2. 户型分布
    const layoutPieCtx = document.getElementById('modalLayoutPieCanvas');
    if (layoutPieCtx) {
      if (modalLayoutPieInstance) modalLayoutPieInstance.destroy();
      modalLayoutPieInstance = new Chart(layoutPieCtx, {
        type: 'doughnut',
        data: {
          labels: Object.keys(layoutCombined),
          datasets: [{
            data: Object.values(layoutCombined),
            backgroundColor: ['#06AABD', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#64748b']
          }]
        },
        options: { responsive: true, maintainAspectRatio: false }
      });
    }

    // 3. 总价分布
    const priceDistCtx = document.getElementById('modalPriceDistCanvas');
    if (priceDistCtx) {
      if (modalPriceDistInstance) modalPriceDistInstance.destroy();
      modalPriceDistInstance = new Chart(priceDistCtx, {
        type: 'bar',
        data: {
          labels: Object.keys(priceDistCombined),
          datasets: [{
            label: '成交套数',
            data: Object.values(priceDistCombined),
            backgroundColor: '#0284c7'
          }]
        },
        options: { responsive: true, maintainAspectRatio: false }
      });
    }
  }

  function normKey(str) {
    if (!str) return '';
    return String(str)
      .replace(/第/g, '')
      .replace(/座/g, '')
      .replace(/栋/g, '')
      .replace(/期/g, '')
      .replace(/Tower/gi, '')
      .replace(/\s+/g, '')
      .trim()
      .toLowerCase();
  }

  // 隐藏销控小卡片全局函数
  function hideSelectedUnitCard() {
    const card = document.getElementById('selectedUnitCard');
    if (card) {
      card.classList.remove('active');
    }
  }
  window.hideSelectedUnitCard = hideSelectedUnitCard;

  // 挂载正式版 2 行式销控弹出卡片 DOM
  let selectedUnitCard = document.getElementById('selectedUnitCard');
  if (!selectedUnitCard) {
    selectedUnitCard = document.createElement('div');
    selectedUnitCard.id = 'selectedUnitCard';
    selectedUnitCard.className = 'selected-unit-card';
    selectedUnitCard.innerHTML = `
      <button class="close-card-btn" id="closeCardBtn" title="关闭">&times;</button>
      <div class="selected-unit-detail">
        <div class="card-row card-row-top">
          <div class="unit-col unit-meta-col">
            <span class="unit-name" id="cardUnitName">--</span>
            <span class="unit-status-badge status-sale" id="cardUnitStatus">在售</span>
          </div>
          
          <div class="v-divider" id="cardDivider1"></div>
          
          <div class="unit-col unit-prices-col">
            <div class="price-box price-original" id="cardOrigPriceContainer">
              <span class="price-label">原价:</span>
              <span class="price-val" id="cardOrigPrice">-</span>
            </div>
            <div class="discount-badge" id="cardDiscRate">-</div>
            <div class="price-box price-discount" id="cardDiscPriceContainer">
              <span class="price-label" id="cardDiscPriceLabel">折实:</span>
              <span class="price-val" id="cardDiscPrice">-</span>
            </div>
          </div>
        </div>
        
        <div class="card-row card-row-bottom" id="cardRowBottom">
          <div class="unit-col unit-ft-col">
            <div class="meta-item" id="cardDiscFtPriceContainer">
              <span class="price-label" id="cardDiscFtLabel">折实呎:</span>
              <span class="meta-val" id="cardDiscSqft">-</span>
            </div>
          </div>
          
          <div class="v-divider" id="cardDividerBottom"></div>
          
          <div class="unit-col unit-pay-col" id="cardPaymentContainer">
            <div class="meta-item payment-scheme">
              <span class="price-label">付款:</span>
              <span class="meta-val" id="cardPayment">-</span>
            </div>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(selectedUnitCard);

    document.getElementById('closeCardBtn')?.addEventListener('click', () => {
      hideSelectedUnitCard();
    });
  }

  // 依照正式版规范，根据房源不同状态 (在售/已售/招标/待售/暂停) 精准渲染卡片内容
  function showSelectedUnitCard(info) {
    if (!info || !selectedUnitCard) return;

    const formatMoney = (val) => {
      if (!val || val === '-' || val === '暂无') return '-';
      const strVal = String(val).trim();
      if (strVal.includes('万') || strVal.includes('招标')) return strVal;
      const n = parseFloat(strVal.replace(/[^0-9\.]/g, ''));
      if (isNaN(n) || n === 0) return strVal;
      if (n >= 10000) return '$' + (n / 10000).toFixed(1).replace(/\.0$/, '') + '万';
      return '$' + n.toLocaleString();
    };

    const formatSqft = (val) => {
      if (!val || val === '-' || val === '暂无') return '-';
      const strVal = String(val).trim();
      if (strVal.includes('/呎')) return strVal;
      const n = parseFloat(strVal.replace(/[^0-9\.]/g, ''));
      if (isNaN(n) || n === 0) return strVal;
      return '$' + Math.round(n).toLocaleString() + '/呎';
    };

    const status = info.status || '待售';
    const isSold = status === '已售';
    const isTender = info.isTender === '是' || info.listPrice === '招标单位';

    // DOM 句柄
    const nameElem = document.getElementById('cardUnitName');
    const statusElem = document.getElementById('cardUnitStatus');
    const origPriceCont = document.getElementById('cardOrigPriceContainer');
    const origPriceVal = document.getElementById('cardOrigPrice');
    const discountBadge = document.getElementById('cardDiscRate');
    const discPriceCont = document.getElementById('cardDiscPriceContainer');
    const discPriceLabel = document.getElementById('cardDiscPriceLabel');
    const discPriceVal = document.getElementById('cardDiscPrice');
    const discFtPriceCont = document.getElementById('cardDiscFtPriceContainer');
    const discFtLabel = document.getElementById('cardDiscFtLabel');
    const discFtVal = document.getElementById('cardDiscSqft');
    const paymentCont = document.getElementById('cardPaymentContainer');
    const paymentVal = document.getElementById('cardPayment');
    const rowBottom = document.getElementById('cardRowBottom');

    // 1. 单元名称 & 状态 Badge
    const areaStr = info.area ? (String(info.area).includes('呎') ? info.area : info.area + '呎') : '';
    const layoutStr = info.layout ? info.layout : '';
    const dateStr = (isSold && info.date && info.date !== '-') ? ` | ${info.date}` : '';
    if (nameElem) {
      nameElem.textContent = `${info.bname || ''} • ${info.floor}楼 ${info.flat}室 (${areaStr}${layoutStr ? ' ' + layoutStr : ''})${dateStr}`;
    }

    if (statusElem) {
      statusElem.textContent = status;
      statusElem.className = 'unit-status-badge';
      if (status === '在售') statusElem.classList.add('status-sale');
      else if (status === '已定价未售') statusElem.classList.add('status-priced');
      else if (status === '已售') statusElem.classList.add('status-sold');
      else if (status === '暂停销售') statusElem.classList.add('status-stopped');
      else statusElem.classList.add('status-pending');
    }

    // 2. 依照正式版逻辑精准渲染各状态信息
    if (isSold) {
      // 【已售单位】完全跟正式版一致：隐藏原价划线、隐藏折扣 Badge、隐藏常用付款，标签设为“成交:”与“成交呎:”
      if (origPriceCont) origPriceCont.style.display = 'none';
      if (discountBadge) discountBadge.style.display = 'none';
      if (paymentCont) paymentCont.style.display = 'none';

      if (discPriceCont) discPriceCont.style.display = 'flex';
      if (discPriceLabel) discPriceLabel.textContent = '成交:';
      if (discPriceVal) discPriceVal.textContent = formatMoney(info.discPrice || info.listPrice);

      if (discFtPriceCont) discFtPriceCont.style.display = 'flex';
      if (discFtLabel) discFtLabel.textContent = '成交呎:';
      if (discFtVal) discFtVal.textContent = formatSqft(info.discSqft || info.sqftPrice);

      if (rowBottom) rowBottom.style.display = 'flex';
    }
    else if (isTender) {
      // 【未售招标单位】
      if (origPriceCont) origPriceCont.style.display = 'none';
      if (discountBadge) discountBadge.style.display = 'none';
      if (discFtPriceCont) discFtPriceCont.style.display = 'none';

      if (discPriceCont) discPriceCont.style.display = 'flex';
      if (discPriceLabel) discPriceLabel.textContent = '发售:';
      if (discPriceVal) discPriceVal.textContent = '招标发售';

      if (paymentCont) {
        paymentCont.style.display = 'flex';
        if (paymentVal) paymentVal.textContent = '详见发售招标文件';
      }
      if (rowBottom) rowBottom.style.display = 'flex';
    }
    else if (status === '在售' || status === '已定价未售') {
      const curProj = info.projectName || window.currentGridProjectName || '';
      const isCullinanSky2 = (curProj === '天玺．天第2期' || curProj.includes('天玺．天第2期') || (curProj.includes('天玺') && curProj.includes('2')));

      let rawListPrice = parseFloat(String(info.listPrice || '').replace(/[^0-9\.]/g, ''));
      if (isNaN(rawListPrice) || rawListPrice <= 0) {
        rawListPrice = parseFloat(String(info.discPrice || '').replace(/[^0-9\.]/g, ''));
      }
      if (!isNaN(rawListPrice) && rawListPrice > 0 && rawListPrice < 10000) {
        rawListPrice = rawListPrice * 10000;
      }

      if (isCullinanSky2 && !isNaN(rawListPrice) && rawListPrice > 0) {
        // 【天玺．天第2期 专属 2 行折实价弹窗逻辑】仅对在售/已定价未售且有原价单位生效
        const p0 = rawListPrice;
        const p1 = p0 * 0.90; // 10% 折后价 (360日付款计划)
        const extraDisc = p1 * 0.04; // 4% 额外折扣 (基于10%折后价算)
        const finalP = p1 - extraDisc; // 180天全款折实价

        const sqftArea = parseFloat(String(info.area || '0').replace(/[^0-9\.]/g, ''));
        const rawSqft = parseFloat(String(info.sqftPrice || '').replace(/[^0-9\.]/g, ''));
        const upriceP1 = sqftArea > 0 ? Math.round(p1 / sqftArea) : (rawSqft ? Math.round(rawSqft * 0.9) : 0);
        const upriceFinal = sqftArea > 0 ? Math.round(finalP / sqftArea) : (upriceP1 ? Math.round(upriceP1 * 0.96) : 0);

        if (origPriceCont) {
          origPriceCont.style.display = 'flex';
          if (origPriceVal) origPriceVal.textContent = formatMoney(p0);
        }
        if (discountBadge) {
          discountBadge.style.display = 'block';
          discountBadge.textContent = '-10%';
        }
        if (discPriceCont) discPriceCont.style.display = 'flex';
        if (discPriceLabel) discPriceLabel.textContent = '折后价:';
        if (discPriceVal) discPriceVal.textContent = formatMoney(p1);

        if (discFtPriceCont) discFtPriceCont.style.display = 'flex';
        if (discFtLabel) discFtLabel.textContent = '折后呎:';
        if (discFtVal) discFtVal.textContent = formatSqft(upriceP1);

        if (paymentCont) {
          paymentCont.style.display = 'flex';
          if (paymentVal) {
            paymentVal.innerHTML = `<span style="color:#045d68; font-weight:600;">4%额外折扣(按折后价算): -${formatMoney(extraDisc)}</span> <span style="color:#cbd5e1; margin:0 0.3rem;">│</span> <strong style="color:#e11d48; font-weight:800;">180天全款折实: ${formatMoney(finalP)} (${formatSqft(upriceFinal)})</strong>`;
          }
        }
        if (rowBottom) rowBottom.style.display = 'flex';
      }
      else {
        // 【所有其他项目 / 标准项目】显示原价划线、折实总价、最高折扣 Badge、折实呎价及付款计划
        if (origPriceCont) {
          origPriceCont.style.display = 'flex';
          if (origPriceVal) origPriceVal.textContent = formatMoney(info.listPrice);
        }

        let rateStr = info.discountRate;
        if (discountBadge) {
          if (rateStr && rateStr !== '-' && rateStr !== '暂无') {
            discountBadge.style.display = 'block';
            discountBadge.textContent = String(rateStr).startsWith('-') ? rateStr : '-' + rateStr;
          } else {
            discountBadge.style.display = 'none';
          }
        }

        if (discPriceCont) discPriceCont.style.display = 'flex';
        if (discPriceLabel) discPriceLabel.textContent = '折实:';
        if (discPriceVal) discPriceVal.textContent = formatMoney(info.discPrice || info.listPrice);

        if (discFtPriceCont) discFtPriceCont.style.display = 'flex';
        if (discFtLabel) discFtLabel.textContent = '折实呎:';
        if (discFtVal) discFtVal.textContent = formatSqft(info.discSqft || info.sqftPrice);

        if (paymentCont) {
          if (info.payment && info.payment !== '-' && info.payment !== '暂无') {
            paymentCont.style.display = 'flex';
            if (paymentVal) paymentVal.textContent = info.payment;
          } else {
            paymentCont.style.display = 'none';
          }
        }
        if (rowBottom) rowBottom.style.display = 'flex';
      }
    }
    else {
      // 【待售 / 暂停销售单位】
      if (origPriceCont) origPriceCont.style.display = 'none';
      if (discountBadge) discountBadge.style.display = 'none';
      if (discFtPriceCont) discFtPriceCont.style.display = 'none';
      if (paymentCont) paymentCont.style.display = 'none';

      if (discPriceCont) discPriceCont.style.display = 'flex';
      if (discPriceLabel) discPriceLabel.textContent = '发售:';
      if (discPriceVal) discPriceVal.textContent = '暂未定价';

      if (rowBottom) rowBottom.style.display = 'none';
    }

    selectedUnitCard.classList.add('active');
  }

  function shouldShowCard(info) {
    if (!info) return false;
    const status = info.status || '';
    const isSold = status === '已售';
    const isTender = info.isTender === '是' || info.listPrice === '招标单位' || String(info.listPrice).includes('招标');
    if (isSold || isTender || status === '待售' || status === '暂停销售') {
      return false;
    }
    return status === '在售' || status === '已定价未售';
  }

  document.addEventListener('mouseover', (e) => {
    const cell = e.target.closest?.('td.unit-grid-cell');
    if (cell && cell.dataset?.unitInfo) {
      try {
        const info = JSON.parse(cell.dataset.unitInfo);
        if (shouldShowCard(info)) {
          showSelectedUnitCard(info);
        } else {
          hideSelectedUnitCard();
        }
      } catch (err) {}
    }
  });

  document.addEventListener('click', (e) => {
    const cell = e.target.closest?.('td.unit-grid-cell');
    if (cell && cell.dataset?.unitInfo) {
      try {
        const info = JSON.parse(cell.dataset.unitInfo);
        if (shouldShowCard(info)) {
          showSelectedUnitCard(info);
        } else {
          hideSelectedUnitCard();
        }
      } catch (err) {}
    }
  });

  // 打开 Excel 销控图纸 Modal 弹窗
  async function openGridModal(filename, projectName) {
    window.currentGridProjectName = projectName;
    const gridModal = document.getElementById('gridModal');
    const modalTitle = document.getElementById('modalProjectTitle');
    const gridDisplayArea = document.getElementById('gridDisplayArea');
    const buildingTabs = document.getElementById('buildingTabs');
    const buildingStatsPanel = document.getElementById('buildingStatsPanel');
    const openAnalyticsFromGridBtn = document.getElementById('openAnalyticsFromGridBtn');

    if (!gridModal) return;
    gridModal.classList.add('open');
    if (modalTitle) modalTitle.textContent = `${projectName} - 销控图纸`;
    if (openAnalyticsFromGridBtn) {
      openAnalyticsFromGridBtn.onclick = () => openAnalyticsModal(projectName);
    }
    if (gridDisplayArea) gridDisplayArea.innerHTML = '<div style="padding:2rem; text-align:center; color:#06AABD;">正在解包读取 Excel 图纸文件...</div>';

    // 绑定关闭 Modal 按钮、遮罩点击与 ESC 按键事件，关闭时自动隐藏底部弹出卡片
    const closeGridModal = () => {
      gridModal.classList.remove('open');
      hideSelectedUnitCard();
    };

    const closeModalBtn = document.getElementById('closeModalBtn');
    if (closeModalBtn) {
      closeModalBtn.onclick = closeGridModal;
    }
    gridModal.onclick = (e) => {
      if (e.target === gridModal) closeGridModal();
    };
    document.onkeydown = (e) => {
      if (e.key === 'Escape') closeGridModal();
    };

    // 绑定缩放与重置控件
    let currentGridScale = 1.0;
    const zoomInBtn = document.getElementById('zoomInBtn');
    const zoomOutBtn = document.getElementById('zoomOutBtn');
    const zoomVal = document.getElementById('zoomVal');
    const resetZoomBtn = document.getElementById('resetZoomBtn');

    if (zoomInBtn) {
      zoomInBtn.onclick = () => {
        currentGridScale = Math.min(2.0, currentGridScale + 0.15);
        applyGridScale();
      };
    }

    if (zoomOutBtn) {
      zoomOutBtn.onclick = () => {
        currentGridScale = Math.max(0.4, currentGridScale - 0.15);
        applyGridScale();
      };
    }

    if (resetZoomBtn) {
      resetZoomBtn.onclick = () => {
        currentGridScale = 1.0;
        applyGridScale();
      };
    }

    function applyGridScale() {
      if (zoomVal) zoomVal.textContent = Math.round(currentGridScale * 100) + '%';
      const gridTable = document.querySelector('.excel-grid-table');
      if (gridTable) {
        gridTable.style.transform = `scale(${currentGridScale})`;
        gridTable.style.transformOrigin = 'top left';
      }
    }

    try {
      const fileUrl = 'files/' + encodeURIComponent(filename);
      const resp = await fetch(fileUrl);
      if (!resp.ok) throw new Error('无法调取 Excel 盘源库');
      const arrayBuffer = await resp.arrayBuffer();

      const workbook = XLSX.read(arrayBuffer, { type: 'array' });
      currentWorkbook = workbook;

      // 解析 Tab 1: 销控汇总明细 获取折实价与付款办法全量映射表
      const unitDetailMap = {};
      if (workbook.Sheets['销控汇总明细']) {
        const summaryRows = XLSX.utils.sheet_to_json(workbook.Sheets['销控汇总明细'], { header: 1, defval: '' });
        if (summaryRows && summaryRows.length > 0) {
          // 找到包含 "楼栋" 的真正 Header 行 (可能在 Row 0 或 Row 1)
          let headerRowIdx = 0;
          for (let r = 0; r < Math.min(5, summaryRows.length); r++) {
            if (summaryRows[r] && summaryRows[r].some(cell => cell && String(cell).includes('楼栋'))) {
              headerRowIdx = r;
              break;
            }
          }

          const headers = summaryRows[headerRowIdx].map(h => String(h).trim());
          const getIdx = (candidates) => {
            for (let i = 0; i < headers.length; i++) {
              const h = headers[i];
              for (const c of candidates) {
                if (h === c || (h && h.includes(c))) return i;
              }
            }
            return -1;
          };

          const idxB = getIdx(['楼栋']);
          const idxF = getIdx(['楼层']);
          const idxFlat = getIdx(['房号']);
          const idxLayout = getIdx(['户型']);
          const idxArea = getIdx(['实用面积', '面积']);
          const idxStatus = getIdx(['销控状态', '状态']);
          const idxDate = getIdx(['成交日期']);
          const idxPrice = getIdx(['单位总价', '总价 (港币)', '总价', '售价']);
          const idxSqftPrice = getIdx(['实用呎价 (港币/呎)', '实用呎价', '呎价']);
          const idxDisc = getIdx(['最高折扣']);
          const idxDiscPrice = getIdx(['折实总价', '折实售价', '折实价']);
          const idxDiscSqft = getIdx(['折实呎价', '折实呎']);
          const idxPayment = getIdx(['付款办法']);
          const idxTender = getIdx(['是否招标']);

          for (let r = headerRowIdx + 1; r < summaryRows.length; r++) {
            const row = summaryRows[r];
            if (!row || row.length === 0) continue;
            const b = (idxB >= 0 && row[idxB]) ? String(row[idxB]).trim() : '';
            const f = (idxF >= 0 && row[idxF]) ? String(row[idxF]).trim() : '';
            const flat = (idxFlat >= 0 && row[idxFlat]) ? String(row[idxFlat]).trim() : '';
            if (!b || !f || !flat) continue;

            const key1 = `${b}_${f}_${flat}`;
            const normB = normKey(b);
            const normF = String(f).trim().replace(/楼|F/gi, '');
            const normFlat = String(flat).trim();
            const key2 = `${normB}_${normF}_${normFlat}`;

            const detailObj = {
              bname: b,
              floor: f,
              flat: flat,
              layout: idxLayout >= 0 ? String(row[idxLayout]).trim() : '',
              area: idxArea >= 0 ? String(row[idxArea]).trim() : '',
              status: idxStatus >= 0 ? String(row[idxStatus]).trim() : '',
              date: idxDate >= 0 ? String(row[idxDate]).trim() : '',
              listPrice: idxPrice >= 0 ? String(row[idxPrice]).trim() : '',
              sqftPrice: idxSqftPrice >= 0 ? String(row[idxSqftPrice]).trim() : '',
              discountRate: idxDisc >= 0 ? String(row[idxDisc]).trim() : '-',
              discPrice: idxDiscPrice >= 0 ? String(row[idxDiscPrice]).trim() : '',
              discSqft: idxDiscSqft >= 0 ? String(row[idxDiscSqft]).trim() : '',
              payment: idxPayment >= 0 ? String(row[idxPayment]).trim() : '',
              isTender: idxTender >= 0 ? String(row[idxTender]).trim() : '否'
            };
            unitDetailMap[key1] = detailObj;
            unitDetailMap[key2] = detailObj;
          }
        }
      }

      // 提取楼栋 Sheets
      const sheetNames = workbook.SheetNames.filter(name => name !== '销控汇总明细');
      if (sheetNames.length === 0) {
        gridDisplayArea.innerHTML = '<div style="padding:2rem; text-align:center; color:#64748b;">该项目暂无可视化楼栋网格图表。</div>';
        return;
      }

      // 渲染楼栋 Tabs
      buildingTabs.innerHTML = '';
      sheetNames.forEach((sheetName, idx) => {
        const tabBtn = document.createElement('button');
        tabBtn.className = `tab-btn ${idx === 0 ? 'active' : ''}`;
        tabBtn.textContent = sheetName;
        tabBtn.addEventListener('click', () => {
          document.querySelectorAll('#buildingTabs .tab-btn').forEach(b => b.classList.remove('active'));
          tabBtn.classList.add('active');
          renderSheetGrid(workbook.Sheets[sheetName], gridDisplayArea, buildingStatsPanel, sheetName, unitDetailMap);
          currentGridScale = 1.0;
          applyGridScale();
        });
        buildingTabs.appendChild(tabBtn);
      });

      // 默认渲染第一个楼栋
      renderSheetGrid(workbook.Sheets[sheetNames[0]], gridDisplayArea, buildingStatsPanel, sheetNames[0], unitDetailMap);
      currentGridScale = 1.0;
      applyGridScale();

    } catch (err) {
      console.error(err);
      if (gridDisplayArea) gridDisplayArea.innerHTML = `<div style="padding:2rem; text-align:center; color:#e11d48;">解析 Excel 失败: ${err.message}</div>`;
    }
  }

  // 将 Excel Sheet 渲染为 1.0 规范的正式可视化销控网格图
  function renderSheetGrid(sheet, container, statsPanel, sheetName, unitDetailMap) {
    if (!sheet || !container) return;

    const data = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: '' });
    if (!data || data.length < 4) {
      container.innerHTML = '<div style="padding:2rem; text-align:center; color:#64748b;">该楼栋暂无有效的销控网格数据。</div>';
      return;
    }

    const str = (v) => (v === null || v === undefined) ? '' : String(v).trim();

    let countTotal = 0, countSale = 0, countPriced = 0, countSold = 0, countStopped = 0, countPending = 0;
    if (data.length >= 3 && data[1] && data[2]) {
      const headers = data[1];
      const values = data[2];
      headers.forEach((h, idx) => {
        const hText = str(h);
        const val = parseInt(values[idx]) || 0;
        if (hText.includes('总套数')) countTotal = val;
        else if (hText.includes('在售')) countSale = val;
        else if (hText.includes('已定价')) countPriced = val;
        else if (hText.includes('已售')) countSold = val;
        else if (hText.includes('暂停')) countStopped = val;
        else if (hText.includes('待售')) countPending = val;
      });
    }

    // 渲染高密超窄销量统计栏
    if (statsPanel) {
      statsPanel.innerHTML = `
        <div class="stats-panel-slim">
          <div class="stats-pills-row">
            <span class="stat-micro-pill" style="background:#e2e8f0; color:#1e293b;">总规划: <strong>${countTotal}套</strong></span>
            <span class="stat-micro-pill" style="background:#a9f5a9; color:#004d00;">在售: <strong>${countSale}</strong></span>
            <span class="stat-micro-pill" style="background:#a9d0f5; color:#002060;">已定价: <strong>${countPriced}</strong></span>
            <span class="stat-micro-pill" style="background:#f5a9a9; color:#660000;">已售: <strong>${countSold}</strong></span>
            <span class="stat-micro-pill" style="background:#ffc000; color:#000000;">暂停: <strong>${countStopped}</strong></span>
            <span class="stat-micro-pill" style="background:#ffffff; color:#7f7f7f; border:1px solid #cbd5e1;">待售: <strong>${countPending}</strong></span>
          </div>
          <div style="font-size:0.75rem; color:#64748b; font-weight:500; display:flex; align-items:center; gap:0.3rem;">
            <span>💡 悬浮/点击任意单元格，显示正式版折实价与付款办法小卡片</span>
          </div>
        </div>
      `;
    }

    let gridStartRow = -1;
    for (let r = 3; r < data.length; r++) {
      if (data[r] && str(data[r][0]).includes('楼层')) {
        gridStartRow = r;
        break;
      }
    }
    if (gridStartRow === -1) gridStartRow = 3;

    let html = '<table class="excel-grid-table" style="width:100%; border-collapse:collapse;">';

    const headerRow = data[gridStartRow] || [];
    html += '<thead><tr>';
    headerRow.forEach((colVal, colIdx) => {
      const hText = str(colVal);
      if (colIdx === 0 || hText) {
        html += `<th>${colIdx === 0 ? '楼层' : hText}</th>`;
      }
    });
    html += '</tr></thead><tbody>';

    for (let r = gridStartRow + 1; r < data.length; r++) {
      const row = data[r];
      if (!row || row.length === 0) continue;
      const floorNum = str(row[0]);
      if (!floorNum) continue;

      html += '<tr>';
      row.forEach((cellVal, colIdx) => {
        const cellText = str(cellVal);

        if (colIdx === 0) {
          html += `<td class="grid-header-cell">${floorNum}</td>`;
        } else {
          if (colIdx >= headerRow.length) return;

          if (!cellText || cellText === '-') {
            html += `<td class="grid-empty-cell"></td>`;
          } else {
            let statusClass = 'status-pending-cell';
            if (cellText.includes('在售') || cellText.includes('(在售)')) {
              statusClass = 'status-sale-cell';
            } else if (cellText.includes('已定价') || cellText.includes('(已定价)')) {
              statusClass = 'status-priced-cell';
            } else if (cellText.includes('年-') || cellText.includes('已售') || /\d{2}年-\d{2}月/.test(cellText)) {
              statusClass = 'status-sold-cell';
            } else if (cellText.includes('暂停') || cellText.includes('暂停销售')) {
              statusClass = 'status-stopped-cell';
            } else if (cellText.includes('待售') || cellText.includes('(待售)')) {
              statusClass = 'status-pending-cell';
            }

            // 提取房号与查找 unitDetailMap (增加归一化比对与全量保底)
            const flatName = str(headerRow[colIdx]);
            let unitInfoAttr = '';
            if (sheetName && flatName) {
              const normSheet = normKey(sheetName);
              const normF = String(floorNum).trim().replace(/楼|F/gi, '');
              const normFlat = String(flatName).trim();

              const key1 = `${sheetName}_${floorNum}_${flatName}`;
              const key2 = `${normSheet}_${normF}_${normFlat}`;

              let info = unitDetailMap ? (unitDetailMap[key1] || unitDetailMap[key2]) : null;

              if (!info) {
                const lines = cellText.split('\n');
                const line1 = lines[0] || '';
                const line2 = lines[1] || '';
                const line3 = lines[2] || '';
                const line4 = lines[3] || '';

                let statusStr = '在售';
                if (statusClass.includes('sold')) statusStr = '已售';
                else if (statusClass.includes('priced')) statusStr = '已定价未售';
                else if (statusClass.includes('stopped')) statusStr = '暂停销售';
                else if (statusClass.includes('pending')) statusStr = '待售';

                info = {
                  bname: sheetName,
                  floor: floorNum,
                  flat: flatName,
                  layout: line1.includes('(') ? line1.substring(line1.indexOf('(') + 1, line1.indexOf(')')) : '',
                  area: line1.includes('|') ? line1.split('|')[1].trim() : line1,
                  status: statusStr,
                  date: line4.includes('年') ? line4.replace(/[()]/g, '') : '',
                  listPrice: line2.trim(),
                  sqftPrice: line3.trim(),
                  discountRate: '-',
                  discPrice: line2.trim(),
                  discSqft: line3.trim(),
                  payment: '-',
                  isTender: line2.includes('招标') ? '是' : '否'
                };
              }

              unitInfoAttr = `data-unit-info="${JSON.stringify(info).replace(/"/g, '&quot;')}"`;
            }

            let formattedText = cellText;
            const safeContent = formattedText.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>');

            html += `<td class="${statusClass} unit-grid-cell" ${unitInfoAttr}>${safeContent}</td>`;
          }
        }
      });
      html += '</tr>';
    }

    html += '</tbody></table><div class="grid-bottom-spacer" style="height: 120px; width: 100%; pointer-events: none;"></div>';
    container.innerHTML = html;
  }

  // ==========================================================================
  // C. 历史成交分析专页逻辑 (analytics.html) - 基于真实 3.7万+ 条成交数据库
  // ==========================================================================
  let trendChartInstance = null;
  let layoutPieInstance = null;
  let priceDistInstance = null;
  let compareRadarInstance = null;
  let comparePriceBarInstance = null;
  let activeGranularity = 'monthly';
  let activeMode = 'single';

  // 模式 C: 自选多盘对比项目列表
  let selectedCompareProjects = ['海盈山第4B期', '天玺．天', '瑜一．天海'];

  function initAnalyticsPage() {
    const projectSelect = document.getElementById('analyticsProjectSelect');
    const districtSelect = document.getElementById('analyticsDistrictSelect');
    const singleDistrictFilter = document.getElementById('singleDistrictFilter');
    const singleSearchInput = document.getElementById('singleProjectSearchInput');
    
    const addCompareSelect = document.getElementById('addCompareProjectSelect');
    const compareDistrictFilter = document.getElementById('compareDistrictFilter');
    const compareSearchInput = document.getElementById('compareProjectSearchInput');

    const districtWrapper = document.getElementById('districtSelectWrapper');
    const singleWrapper = document.getElementById('singleProjectWrapper');
    const customBar = document.getElementById('customCompareBar');

    const realHistory = window.data_real_history || {};
    const availableProjects = Object.keys(realHistory).length > 0 ? Object.keys(realHistory) : allProjects.map(p => p.name);

    // 0. 抽取全量唯一商圈列表并自动排序
    const districtSet = new Set();
    availableProjects.forEach(pname => {
      const pObj = (realHistory[pname] || allProjects.find(p => p.name === pname) || {});
      const meta = (window.APP_DATA?.projects_data || {})[pname] || {};
      const dist = meta.district || pObj.district;
      if (dist) districtSet.add(dist);
    });
    const districtsList = Array.from(districtSet).sort();

    // 填充商圈下拉框
    [singleDistrictFilter, districtSelect, compareDistrictFilter].forEach(selectElem => {
      if (!selectElem) return;
      const defaultLabel = selectElem.children[0]?.textContent || '所有商圈';
      selectElem.innerHTML = `<option value="">${defaultLabel}</option>`;
      districtsList.forEach(d => {
        const opt = document.createElement('option');
        opt.value = d;
        opt.textContent = d;
        selectElem.appendChild(opt);
      });
    });

    // 1. 两步筛选：联动更新模式 A 单项目下拉菜单
    function updateSingleProjectSelect() {
      if (!projectSelect) return;
      const curDist = singleDistrictFilter?.value || '';
      const curSearch = (singleSearchInput?.value || '').trim().toLowerCase();
      const currentSelectedVal = projectSelect.value;

      projectSelect.innerHTML = '';

      const filtered = availableProjects.filter(pname => {
        const pObj = (realHistory[pname] || allProjects.find(p => p.name === pname) || {});
        const meta = (window.APP_DATA?.projects_data || {})[pname] || {};
        const pDist = meta.district || pObj.district || '';
        if (curDist && !pDist.includes(curDist)) return false;
        if (curSearch && !pname.toLowerCase().includes(curSearch)) return false;
        return true;
      });

      if (filtered.length === 0) {
        const opt = document.createElement('option');
        opt.value = '';
        opt.textContent = '⚠️ 未检索到匹配项目';
        projectSelect.appendChild(opt);
      } else {
        filtered.forEach(pname => {
          const pObj = (realHistory[pname] || allProjects.find(p => p.name === pname) || {});
          const meta = (window.APP_DATA?.projects_data || {})[pname] || {};
          const pDist = meta.district || pObj.district || '全港';
          const opt = document.createElement('option');
          opt.value = pname;
          opt.textContent = `${pDist} • ${pname}`;
          projectSelect.appendChild(opt);
        });
      }

      if (currentSelectedVal && filtered.includes(currentSelectedVal)) {
        projectSelect.value = currentSelectedVal;
      } else if (filtered.length > 0) {
        projectSelect.value = filtered[0];
      }
    }

    // 检查 URL 带参跳转
    const urlParams = new URLSearchParams(window.location.search);
    const targetProjectName = urlParams.get('project');

    updateSingleProjectSelect();
    if (targetProjectName && availableProjects.includes(targetProjectName)) {
      projectSelect.value = targetProjectName;
    }

    if (singleDistrictFilter) singleDistrictFilter.addEventListener('change', () => { updateSingleProjectSelect(); updateAnalyticsCharts(); });
    if (singleSearchInput) singleSearchInput.addEventListener('input', () => { updateSingleProjectSelect(); updateAnalyticsCharts(); });
    if (projectSelect) projectSelect.addEventListener('change', () => updateAnalyticsCharts());
    if (districtSelect) districtSelect.addEventListener('change', () => updateAnalyticsCharts());

    // 2. 两步筛选：联动更新模式 C 对比项目下拉菜单
    function updateCompareProjectSelect() {
      if (!addCompareSelect) return;
      const curDist = compareDistrictFilter?.value || '';
      const curSearch = (compareSearchInput?.value || '').trim().toLowerCase();

      addCompareSelect.innerHTML = '<option value="">+ 选择并添加对比项目...</option>';

      const filtered = availableProjects.filter(pname => {
        const pObj = (realHistory[pname] || allProjects.find(p => p.name === pname) || {});
        const meta = (window.APP_DATA?.projects_data || {})[pname] || {};
        const pDist = meta.district || pObj.district || '';
        if (curDist && !pDist.includes(curDist)) return false;
        if (curSearch && !pname.toLowerCase().includes(curSearch)) return false;
        return true;
      });

      filtered.forEach(pname => {
        const opt = document.createElement('option');
        opt.value = pname;
        opt.textContent = pname;
        addCompareSelect.appendChild(opt);
      });
    }

    updateCompareProjectSelect();

    if (compareDistrictFilter) compareDistrictFilter.addEventListener('change', () => updateCompareProjectSelect());
    if (compareSearchInput) compareSearchInput.addEventListener('input', () => updateCompareProjectSelect());

    if (addCompareSelect) {
      addCompareSelect.addEventListener('change', (e) => {
        const val = e.target.value;
        if (val && !selectedCompareProjects.includes(val)) {
          if (selectedCompareProjects.length >= 5) {
            alert('最多支持同时对比 5 个项目');
            return;
          }
          selectedCompareProjects.push(val);
          renderCompareTags();
          updateAnalyticsCharts();
        }
        e.target.value = '';
      });
    }

    // 时间粒度切换 (年度/月度/周度)
    document.querySelectorAll('.granularity-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.granularity-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        activeGranularity = btn.getAttribute('data-granularity');
        updateAnalyticsCharts();
      });
    });

    // 对比模式切换 (模式 A / B / C)
    document.querySelectorAll('.mode-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        activeMode = btn.getAttribute('data-mode');

        if (activeMode === 'district') {
          if (districtWrapper) districtWrapper.style.display = 'block';
          if (singleWrapper) singleWrapper.style.display = 'none';
          if (customBar) customBar.style.display = 'none';
        } else if (activeMode === 'custom') {
          if (districtWrapper) districtWrapper.style.display = 'none';
          if (singleWrapper) singleWrapper.style.display = 'none';
          if (customBar) customBar.style.display = 'block';
          renderCompareTags();
        } else {
          if (districtWrapper) districtWrapper.style.display = 'none';
          if (singleWrapper) singleWrapper.style.display = 'block';
          if (customBar) customBar.style.display = 'none';
        }
        updateAnalyticsCharts();
      });
    });

    renderCompareTags();
    updateAnalyticsCharts();
  }

  // 渲染模式 C 自选项目对比标签
  function renderCompareTags() {
    const pool = document.getElementById('selectedProjectTags');
    if (!pool) return;
    pool.innerHTML = '';
    selectedCompareProjects.forEach(pname => {
      const tag = document.createElement('div');
      tag.className = 'compare-tag';
      tag.innerHTML = `
        <span>${pname}</span>
        <span class="compare-tag-remove" data-name="${pname}">✖</span>
      `;
      pool.appendChild(tag);
    });

    document.querySelectorAll('.compare-tag-remove').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const nameToRemove = btn.getAttribute('data-name');
        selectedCompareProjects = selectedCompareProjects.filter(n => n !== nameToRemove);
        renderCompareTags();
        updateAnalyticsCharts();
      });
    });
  }

  // 核心：用真实数据库抽取的数据渲染历史分析图表
  function updateAnalyticsCharts() {
    const trendCtx = document.getElementById('trendChart');
    const pieCtx = document.getElementById('layoutPieChart');
    const barCtx = document.getElementById('priceDistChart');
    const tableBody = document.getElementById('analyticsTableBody');
    const mainTitle = document.getElementById('mainChartTitle');

    if (!trendCtx || typeof Chart === 'undefined') return;

    const realHistory = window.data_real_history || {};
    const selectedProjName = document.getElementById('analyticsProjectSelect')?.value || '海盈山第4B期';
    const selectedDistrict = document.getElementById('analyticsDistrictSelect')?.value || '启德';

    let chartLabels = [];
    let datasets = [];
    let layoutStats = { '开放式': 0, '1房': 0, '2房': 0, '3房': 0, '4房+': 0 };
    let priceRangesStats = { '500万下': 0, '500-1000万': 0, '1000-2000万': 0, '2000-5000万': 0, '5000万+': 0 };
    let tableRowsData = [];

    // 颜色调色板（用于多盘对比）
    const colors = ['#06AABD', '#e11d48', '#2563eb', '#10b981', '#f59e0b', '#8b5cf6'];

    if (activeMode === 'single') {
      // ===== 模式 A: 单项目真实历史走势 =====
      if (mainTitle) mainTitle.textContent = `${selectedProjName} - 真实历史成交量与实用呎价走势`;
      const projData = realHistory[selectedProjName] || {};
      const timeDict = projData[activeGranularity] || projData['monthly'] || {};

      chartLabels = Object.keys(timeDict).sort();
      if (chartLabels.length === 0) {
        chartLabels = ['2024-01', '2024-06', '2025-01', '2025-06', '2026-01', '2026-06'];
      }

      const volumeArr = chartLabels.map(k => timeDict[k] ? timeDict[k].volume : 0);
      const priceArr = chartLabels.map(k => timeDict[k] ? timeDict[k].avg_uprice : 0);

      datasets = [
        {
          label: `${selectedProjName} 成交套数 (套)`,
          data: volumeArr,
          type: 'bar',
          backgroundColor: 'rgba(6, 170, 189, 0.35)',
          borderColor: '#06AABD',
          borderWidth: 1.5,
          borderRadius: { topLeft: 6, topRight: 6, bottomLeft: 0, bottomRight: 0 },
          maxBarThickness: 16,
          barPercentage: 0.5,
          categoryPercentage: 0.7,
          yAxisID: 'y1'
        },
        {
          label: `${selectedProjName} 实用呎价 (HK$/呎)`,
          data: priceArr,
          type: 'line',
          borderColor: '#e11d48',
          backgroundColor: 'rgba(225, 29, 72, 0.08)',
          borderWidth: 2.5,
          tension: 0.4,
          pointRadius: 4,
          pointHoverRadius: 7,
          pointBackgroundColor: '#ffffff',
          pointBorderColor: '#e11d48',
          pointBorderWidth: 2,
          fill: true,
          yAxisID: 'y2'
        }
      ];

      if (projData.layouts) layoutStats = projData.layouts;
      if (projData.price_ranges) priceRangesStats = projData.price_ranges;

      // 构造表格数据
      chartLabels.forEach(t => {
        const item = timeDict[t] || {};
        tableRowsData.push({
          time: t,
          name: selectedProjName,
          district: projData.district || '港岛/九龙',
          vol: item.volume || 0,
          avgPrice: item.avg_price ? `HK$ ${(item.avg_price/10000).toFixed(1)} 万` : '-',
          avgUprice: item.avg_uprice ? `HK$ ${item.avg_uprice.toLocaleString()} /呎` : '-',
          rangeUprice: (item.min_uprice && item.max_uprice) ? `HK$ ${item.min_uprice} - ${item.max_uprice}` : '-',
          mainLayout: '主力2房/3房'
        });
      });

    } else if (activeMode === 'district') {
      // ===== 模式 B: 同区域竞品对比 =====
      if (mainTitle) mainTitle.textContent = `${selectedDistrict} 商圈内各项目真实成交对比`;

      // 筛选属于该商圈的项目
      const districtProjects = Object.keys(realHistory).filter(pname => {
        const pObj = realHistory[pname];
        return pObj && pObj.district && pObj.district.includes(selectedDistrict);
      }).slice(0, 5);

      const targetProjects = districtProjects.length > 0 ? districtProjects : ['天玺．天', '启德海湾 1', '维港1号'];

      // 收集所有月份或年份标签
      const allTimesSet = new Set();
      targetProjects.forEach(pname => {
        const timeDict = realHistory[pname]?.[activeGranularity] || realHistory[pname]?.['monthly'] || {};
        Object.keys(timeDict).forEach(t => allTimesSet.add(t));
      });

      chartLabels = Array.from(allTimesSet).sort().slice(-12);
      if (chartLabels.length === 0) chartLabels = ['2025-01', '2025-06', '2026-01', '2026-06'];

      datasets = [];
      targetProjects.forEach((pname, idx) => {
        const timeDict = realHistory[pname]?.[activeGranularity] || realHistory[pname]?.['monthly'] || {};
        const volData = chartLabels.map(t => timeDict[t] ? Math.round(timeDict[t].volume) : 0);
        const pData = chartLabels.map(t => timeDict[t] ? timeDict[t].avg_uprice : 0);

        // 成交套数纤细圆角柱状
        datasets.push({
          label: `${pname} 套数`,
          data: volData,
          type: 'bar',
          backgroundColor: colors[idx % colors.length] + '40',
          borderColor: colors[idx % colors.length],
          borderWidth: 1.2,
          borderRadius: { topLeft: 4, topRight: 4, bottomLeft: 0, bottomRight: 0 },
          maxBarThickness: 12,
          barPercentage: 0.5,
          categoryPercentage: 0.6,
          yAxisID: 'y1'
        });

        // 成交呎价精致折线
        datasets.push({
          label: `${pname} 呎价`,
          data: pData,
          type: 'line',
          borderColor: colors[idx % colors.length],
          backgroundColor: 'transparent',
          borderWidth: 2.5,
          tension: 0.35,
          pointRadius: 3,
          pointHoverRadius: 6,
          pointBackgroundColor: '#ffffff',
          pointBorderColor: colors[idx % colors.length],
          pointBorderWidth: 2,
          yAxisID: 'y2'
        });
      });

    } else {
      // ===== 模式 C: 自选多盘对比 =====
      if (mainTitle) mainTitle.textContent = `自选多盘 (${selectedCompareProjects.join(' vs ')}) 真实成交对比`;

      const targetProjects = selectedCompareProjects.length > 0 ? selectedCompareProjects : ['海盈山第4B期', '天玺．天'];

      const allTimesSet = new Set();
      targetProjects.forEach(pname => {
        const timeDict = realHistory[pname]?.[activeGranularity] || realHistory[pname]?.['monthly'] || {};
        Object.keys(timeDict).forEach(t => allTimesSet.add(t));
      });

      chartLabels = Array.from(allTimesSet).sort().slice(-12);
      if (chartLabels.length === 0) chartLabels = ['2025-01', '2025-06', '2026-01', '2026-06'];

      datasets = [];
      targetProjects.forEach((pname, idx) => {
        const timeDict = realHistory[pname]?.[activeGranularity] || realHistory[pname]?.['monthly'] || {};
        const volData = chartLabels.map(t => timeDict[t] ? Math.round(timeDict[t].volume) : 0);
        const upriceData = chartLabels.map(t => timeDict[t] ? timeDict[t].avg_uprice : 0);

        // 成交套数纤细圆角柱状
        datasets.push({
          label: `${pname} 套数`,
          data: volData,
          type: 'bar',
          backgroundColor: colors[idx % colors.length] + '50',
          borderColor: colors[idx % colors.length],
          borderWidth: 1.2,
          borderRadius: { topLeft: 4, topRight: 4, bottomLeft: 0, bottomRight: 0 },
          maxBarThickness: 12,
          barPercentage: 0.5,
          categoryPercentage: 0.6,
          yAxisID: 'y1'
        });

        // 成交呎价精致折线
        datasets.push({
          label: `${pname} 呎价`,
          data: upriceData,
          type: 'line',
          borderColor: colors[idx % colors.length],
          backgroundColor: 'transparent',
          borderWidth: 2.5,
          tension: 0.35,
          pointRadius: 3,
          pointHoverRadius: 6,
          pointBackgroundColor: '#ffffff',
          pointBorderColor: colors[idx % colors.length],
          pointBorderWidth: 2,
          yAxisID: 'y2'
        });
      });
    }

    // 销毁旧实例并重新绘制
    if (trendChartInstance) trendChartInstance.destroy();
    if (layoutPieInstance) layoutPieInstance.destroy();
    if (priceDistInstance) priceDistInstance.destroy();

    // 1. 绘制趋势走势图
    trendChartInstance = new Chart(trendCtx, {
      type: 'bar',
      data: { labels: chartLabels, datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false }
        },
        scales: {
          y1: {
            type: 'linear',
            position: 'left',
            title: { display: true, text: '成交套数 (套)' },
            beginAtZero: true,
            ticks: {
              precision: 0
            }
          },
          y2: {
            type: 'linear',
            position: 'right',
            title: { display: true, text: '实用呎价 (HK$/呎)' },
            grid: { drawOnChartArea: false }
          }
        }
      }
    });

    // 渲染上下两行分组图例（第一行：成交套数 | 第二行：实用呎价）
    render2RowTrendLegend('trendChartCustomLegend', trendChartInstance, datasets);

    // 获取单盘与多盘模块 DOM 元素
    const singleSubCharts = document.getElementById('singleProjectSubCharts');
    const compareSubCharts = document.getElementById('compareSubCharts');
    const singleTableSec = document.getElementById('singleProjectTableSection');
    const compareTableSec = document.getElementById('compareTableSection');
    const compareMatrixBody = document.getElementById('compareMatrixTableBody');

    if (activeMode === 'single') {
      // ===== 单盘模式：显示单盘户型占比、总价区间与单盘表格 =====
      if (singleSubCharts) singleSubCharts.style.display = 'flex';
      if (compareSubCharts) compareSubCharts.style.display = 'none';
      if (singleTableSec) singleTableSec.style.display = 'block';
      if (compareTableSec) compareTableSec.style.display = 'none';

      if (compareRadarInstance) { compareRadarInstance.destroy(); compareRadarInstance = null; }
      if (comparePriceBarInstance) { comparePriceBarInstance.destroy(); comparePriceBarInstance = null; }

      // 2. 绘制真实户型占比图
      if (pieCtx) {
        layoutPieInstance = new Chart(pieCtx, {
          type: 'doughnut',
          data: {
            labels: Object.keys(layoutStats),
            datasets: [{
              data: Object.values(layoutStats),
              backgroundColor: ['#06AABD', '#3b82f6', '#10b981', '#f59e0b', '#ef4444']
            }]
          },
          options: { responsive: true, maintainAspectRatio: false }
        });
      }

      // 3. 绘制真实总价分布图
      if (barCtx) {
        priceDistInstance = new Chart(barCtx, {
          type: 'bar',
          data: {
            labels: Object.keys(priceRangesStats),
            datasets: [{
              label: '成交单位数',
              data: Object.values(priceRangesStats),
              backgroundColor: '#0284c7'
            }]
          },
          options: { responsive: true, maintainAspectRatio: false }
        });
      }

      setTimeout(() => {
        try {
          if (layoutPieInstance) { layoutPieInstance.resize(); layoutPieInstance.update(); }
          if (priceDistInstance) { priceDistInstance.resize(); priceDistInstance.update(); }
        } catch (e) {}
      }, 80);

      // 4. 填充单盘表格 (近期成交优先置顶倒序排列)
      if (tableBody) {
        tableBody.innerHTML = '';
        const sortedRows = [...tableRowsData].sort((a, b) => String(b.time || '').localeCompare(String(a.time || '')));
        if (sortedRows.length > 0) {
          sortedRows.forEach(row => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
              <td><strong>${row.time}</strong></td>
              <td><strong style="color:#0f172a;">${row.name}</strong></td>
              <td><span class="badge badge-district">${row.district}</span></td>
              <td><span style="color:#06AABD; font-weight:700;">${row.vol} 套</span></td>
              <td>${row.avgPrice}</td>
              <td><strong style="color:#e11d48;">${row.avgUprice}</strong></td>
              <td>${row.rangeUprice}</td>
              <td>${row.mainLayout}</td>
            `;
            tableBody.appendChild(tr);
          });
        } else {
          tableBody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:2rem; color:#94a3b8;">暂无符合条件的表格明细数据</td></tr>`;
        }
      }

    } else {
      // ===== 模式 B (商圈) / 模式 C (自选多盘) 竞品对比：呈现方案一全新模块！ =====
      if (singleSubCharts) singleSubCharts.style.display = 'none';
      if (compareSubCharts) compareSubCharts.style.display = 'flex';
      if (singleTableSec) singleTableSec.style.display = 'none';
      if (compareTableSec) compareTableSec.style.display = 'block';

      // 选中的对比项目列表 (限制 3 - 6 个有效参评盘源)
      const curDist = selectedDistrict && selectedDistrict.trim() !== '' ? selectedDistrict : '启德';
      const districtProjects = Object.keys(realHistory).filter(pname => {
        const pObj = realHistory[pname];
        return pObj && pObj.district && pObj.district.includes(curDist);
      }).slice(0, 5);

      const targetProjects = activeMode === 'district' ? districtProjects : selectedCompareProjects;
      const effectiveProjects = targetProjects.length > 0 ? targetProjects.slice(0, 6) : ['天玺．天', '启德海湾 1', '维港1号'];

      // 构造参评项目全景指标列表 (防防御性判空)
      const allProjectsList = (allProjects && allProjects.length > 0) ? allProjects : (window.APP_DATA?.projects || []);
      const compareList = effectiveProjects.map(name => {
        const proj = allProjectsList.find(p => p.name === name) || {};
        const pHist = realHistory[name] || {};
        const mDict = pHist.monthly || {};

        let totVol = 0;
        let totVal = 0;
        Object.values(mDict).forEach(m => {
          totVol += m.volume || 0;
          totVal += (m.volume || 0) * (m.avg_uprice || 0);
        });

        const calculatedAvgU = totVol > 0 ? Math.round(totVal / totVol) : 0;
        const avgUprice = proj.avg_uprice || calculatedAvgU || 22000;
        const baseRent = proj.base_sqft_rent || 50;
        const calcRoiVal = (avgUprice > 0) ? roundNum(baseRent * 12 / avgUprice * 100, 2) : 3.5;
        const roiStr = proj.roi || `${calcRoiVal}%`;
        const roiVal = parseFloat(roiStr) || calcRoiVal;

        return {
          name: name,
          district: proj.district || pHist.district || '核心区',
          totVol: totVol,
          avgUprice: avgUprice,
          baseRent: baseRent,
          rentDesc: proj.estimated_sqft_rent_desc || proj.rent_range_desc || `$${baseRent}/呎`,
          roiStr: roiStr,
          roiVal: roiVal,
          googleDriveFolder: proj.google_drive_folder || '',
          marketingUrl: proj.marketing_url || ''
        };
      });

      function roundNum(num, dec) {
        return Math.round(num * Math.pow(10, dec)) / Math.pow(10, dec);
      }

      // 1. 渲染竞品多维综合竞争力雷达图 (#compareRadarChart)
      const radarCtx = document.getElementById('compareRadarChart');
      if (radarCtx) {
        try {
          if (compareRadarInstance) compareRadarInstance.destroy();

          const maxVol = Math.max(...compareList.map(c => c.totVol), 1);
          const validUprices = compareList.map(c => c.avgUprice).filter(u => u > 0);
          const minU = validUprices.length > 0 ? Math.min(...validUprices) : 20000;
          const maxROI = Math.max(...compareList.map(c => c.roiVal), 1);

          const radarDatasets = compareList.map((item, idx) => {
            const volScore = Math.min(10, Math.max(3, Math.round((item.totVol / maxVol) * 10)));
            const rawPriceScore = (item.avgUprice > 0 && minU > 0) ? Math.round((minU / item.avgUprice) * 10) : 6;
            const priceScore = isFinite(rawPriceScore) ? Math.min(10, Math.max(3, rawPriceScore)) : 6;
            const roiScore = Math.min(10, Math.max(3, Math.round((item.roiVal / maxROI) * 10)));
            const recencyScore = item.totVol > 30 ? 9 : (item.totVol > 10 ? 7 : 5);
            const layoutScore = 8;

            return {
              label: item.name,
              data: [volScore, priceScore, roiScore, recencyScore, layoutScore],
              borderColor: colors[idx % colors.length],
              backgroundColor: colors[idx % colors.length] + '25',
              borderWidth: 2,
              pointRadius: 4
            };
          });

          compareRadarInstance = new Chart(radarCtx, {
            type: 'radar',
            data: {
              labels: ['去化热度', '价格吸引力', '预估ROI', '成交活跃度', '户型丰富度'],
              datasets: radarDatasets
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              scales: {
                r: { min: 0, max: 10, ticks: { display: false } }
              }
            }
          });
        } catch (e) {
          console.error("渲染雷达图异常:", e);
        }
      }

      // 2. 渲染竞品总价门槛与价格区间对比图 (#comparePriceBarChart)
      const priceBarCtx = document.getElementById('comparePriceBarChart');
      if (priceBarCtx) {
        try {
          if (comparePriceBarInstance) comparePriceBarInstance.destroy();

          comparePriceBarInstance = new Chart(priceBarCtx, {
            type: 'bar',
            data: {
              labels: compareList.map(c => c.name),
              datasets: [
                {
                  label: '平均成交呎价 (HK$/呎)',
                  data: compareList.map(c => c.avgUprice),
                  backgroundColor: '#06AABD',
                  borderRadius: 4
                },
                {
                  label: '商圈基准呎租 (HK$/呎)',
                  data: compareList.map(c => c.baseRent * 350), // 坐标归一化放大显示
                  backgroundColor: '#f59e0b',
                  borderRadius: 4
                }
              ]
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                tooltip: {
                  callbacks: {
                    label: function(context) {
                      const item = compareList[context.dataIndex];
                      if (context.datasetIndex === 1) {
                        return `预估实用呎租: ${item.rentDesc}`;
                      }
                      return `平均实用呎价: HK$ ${item.avgUprice ? item.avgUprice.toLocaleString() : '暂无'}/呎`;
                    }
                  }
                }
              }
            }
          });
        } catch (e) {
          console.error("渲染价格对比图异常:", e);
        }
      }

      // 强制在 DOM 回流后重绘 Canvas 画布，解决 hidden 容器尺寸为 0 导致空白的问题
      setTimeout(() => {
        try {
          if (compareRadarInstance) {
            compareRadarInstance.resize();
            compareRadarInstance.update();
          }
          if (comparePriceBarInstance) {
            comparePriceBarInstance.resize();
            comparePriceBarInstance.update();
          }
        } catch (err) {
          console.warn("Chart resize delay handled:", err);
        }
      }, 80);

      // 3. 渲染竞品核心指标全景对照透视表 (#compareMatrixTableBody)
      if (compareMatrixBody) {
        compareMatrixBody.innerHTML = '';
        compareList.forEach(item => {
          const tr = document.createElement('tr');
          const parentDriveId = '15tRwSlG1VTOKuEyj-H131zpNK6v6MY04';
          const folderName = item.googleDriveFolder || `${item.region || '全港'}-${item.district || '核心区'}-${item.name}`;
          const driveQ = `type:folder parent:${parentDriveId} "${folderName}"`;
          const mUrl = item.marketingUrl || `https://drive.google.com/drive/search?q=${encodeURIComponent(driveQ)}`;

          const minMonthRent = item.baseRent * 350 / 10000;
          const maxMonthRent = item.baseRent * 650 / 10000;

          tr.innerHTML = `
            <td><strong style="color:#0f172a; font-size:0.92rem;">${item.name}</strong></td>
            <td><span class="badge badge-district">${item.district}</span></td>
            <td><strong style="color:#06AABD;">${item.totVol} 套</strong></td>
            <td><strong style="color:#e11d48;">${item.avgUprice ? 'HK$ ' + item.avgUprice.toLocaleString() + '/呎' : '价格详询'}</strong></td>
            <td><span style="color:#0284c7; font-weight:600;">${item.rentDesc}</span></td>
            <td><span style="color:#16a34a; font-weight:600;">HK$ ${minMonthRent.toFixed(1)}万 - ${maxMonthRent.toFixed(1)}万/月</span></td>
            <td><span class="badge" style="background:#dcfce7; color:#15803d; font-weight:700; font-size:0.85rem;">${item.roiStr}</span></td>
            <td>
              <div style="display:flex; gap:0.4rem; flex-wrap:wrap;">
                <button class="btn btn-sm btn-outline btn-grid-action" data-project="${item.name}">🏢 销控网格</button>
                <button class="btn btn-sm btn-outline btn-trend-action" data-project="${item.name}">📈 成交走势</button>
                <a href="${mUrl}" target="_blank" class="btn btn-sm btn-outline" style="text-decoration:none;">🔗 营销工具</a>
              </div>
            </td>
          `;
          compareMatrixBody.appendChild(tr);
        });

        // 绑定表格操作按钮
        compareMatrixBody.querySelectorAll('.btn-grid-action').forEach(btn => {
          btn.addEventListener('click', (e) => {
            const pName = e.currentTarget.getAttribute('data-project');
            openGridModal(pName);
          });
        });
        compareMatrixBody.querySelectorAll('.btn-trend-action').forEach(btn => {
          btn.addEventListener('click', (e) => {
            const pName = e.currentTarget.getAttribute('data-project');
            openAnalyticsModal(pName);
          });
        });
      }
    }
  }

  // ==========================================================================
  // D. 聚焦盘精选盘专页逻辑 (featured.html)
  // ==========================================================================
  let currentTier = '1000-2000';
  let currentView = 'table';
  let featuredQuery = '';

  function initFeaturedPage() {
    const tierButtons = document.querySelectorAll('.price-tier-tabs .tier-btn');
    const searchInput = document.getElementById('featuredSearchInput');

    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        featuredQuery = e.target.value.toLowerCase().trim();
        renderFeaturedContent();
      });
    }

    // 4 大价位段 Filter Tabs
    tierButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        tierButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentTier = btn.getAttribute('data-tier');
        renderFeaturedContent();
      });
    });

    renderFeaturedContent();
  }

  function renderFeaturedContent() {
    const tableBody = document.getElementById('featuredTableBody');
    if (!tableBody) return;

    const showRoiCol = (currentTier === '1000-2000');

    // 动态跟进 1000-2000万 模块是否显示 ROI 专列
    const theadEl = document.querySelector('#featuredTable thead');
    if (theadEl) {
      if (showRoiCol) {
        theadEl.innerHTML = `
          <tr>
            <th style="width:130px;">项目名称 / 评级</th>
            <th style="width:90px;">城区商圈</th>
            <th style="width:105px;">分类 / 价位</th>
            <th style="width:115px;">主推户型 / 呎价</th>
            <th style="width:95px;">预估月租 / ROI</th>
            <th style="min-width:280px;">推荐理由与卖点</th>
            <th style="min-width:300px;">对内地客户专属卖点</th>
            <th style="width:115px; text-align:center;">快捷操作</th>
          </tr>
        `;
      } else {
        theadEl.innerHTML = `
          <tr>
            <th style="width:135px;">项目名称 / 评级</th>
            <th style="width:95px;">城区商圈</th>
            <th style="width:110px;">分类 / 价位</th>
            <th style="width:120px;">主推户型 / 呎价</th>
            <th style="min-width:320px;">推荐理由与卖点</th>
            <th style="min-width:340px;">对内地客户专属卖点</th>
            <th style="width:115px; text-align:center;">快捷操作</th>
          </tr>
        `;
      }
    }

    const formatReasonText = (reason, idx) => {
      if (!reason) return '';
      const str = String(reason).trim();
      const parts = str.split(/(?=\b\d+[\.、\t\s])/g).map(s => s.trim()).filter(Boolean);
      let formattedInner = '';
      if (parts.length > 1) {
        formattedInner = parts.map(p => `<div style="margin-bottom:0.35rem; line-height:1.45;">${p}</div>`).join('');
      } else {
        formattedInner = `<div style="line-height:1.45; white-space:pre-line;">${str}</div>`;
      }

      const isLong = str.length > 60 || parts.length > 2;

      return `
        <div id="reason_text_${idx}" data-expanded="false" style="font-size:0.8rem; color:#334155; display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden; text-overflow:ellipsis; max-width:280px; transition:all 0.2s;">
          ${formattedInner}
        </div>
        ${isLong ? `
          <button onclick="toggleReasonExpand('reason_text_${idx}', this)" style="border:none; background:transparent; color:#06AABD; font-size:0.75rem; font-weight:700; cursor:pointer; padding:0.2rem 0; margin-top:0.25rem; display:inline-flex; align-items:center; gap:0.2rem;">
            ▼ 展开完整卖点
          </button>
        ` : ''}
      `;
    };

    const formatMainlandPointsText = (points) => {
      if (!points) return '';
      let str = String(points).trim();
      str = str.replace(/(核心定位[：:]?)/g, '<span style="color:#045d68; font-weight:700;">$1</span>');
      return `<div style="line-height:1.55; color:#334155; font-size:0.8rem; white-space:pre-line;">${str}</div>`;
    };

    const tierLabels = {
      '1000-2000': '投资配置类 (1000-2000万)',
      '2000-5000': '自用保值类 (2000-5000万)',
      '5000-10000': '豪宅购置类 (5000-1亿)',
      '10000+': '顶豪收藏类 (1亿以上)'
    };

    let featuredList = [];
    Object.keys(featuredByPriceData).forEach(tier => {
      const projNames = featuredByPriceData[tier] || [];
      projNames.forEach(name => {
        const proj = allProjects.find(p => p.name === name || p.name.includes(name) || name.includes(p.name) || (name.includes('波老道') && (p.name.includes('21 Borrett') || p.name.includes('应天')))) || {};
        const meta = projectsDataMap[`${tier}_${name}`] || projectsDataMap[name] || {};

        const parentDriveId = '15tRwSlG1VTOKuEyj-H131zpNK6v6MY04';
        const introUrl = proj.intro_url || proj.centaline_url || meta.centaline_url || meta.intro_url || `https://www.ricacorp.com/zh-hk/property/search?q=${encodeURIComponent(name)}`;
        const cleanName = name.replace(/\(第.*?\)/g, '').replace(/第\s*[0-9A-Za-z\-]+期.*$/, '').replace(/第[0-9A-Za-z]+$/g, '').replace(/[0-9]+[a-zA-Z]+$/g, '').replace(/\s+[0-9]+$/g, '').replace(/\s+I{1,3}$/g, '').replace(/\s+II$/g, '').replace(/\s+III$/g, '').trim() || name;
        const regionName = meta.region || proj.region || '全港';
        const districtName = meta.district || proj.district || '核心区';
        const folderName = proj.google_drive_folder || meta.google_drive_folder || `${regionName}-${districtName}-${cleanName}`;
        const driveQ = `type:folder parent:${parentDriveId} "${folderName}"`;
        const marketingUrl = proj.marketing_url || meta.marketing_url || `https://drive.google.com/drive/search?q=${encodeURIComponent(driveQ)}`;

        // 按商圈平均呎价与基准呎租倒算 ROI
        let calcRoiStr = meta.roi || proj.roi || '';
        if (!calcRoiStr || calcRoiStr === '暂无' || calcRoiStr === 'null') {
          const avgU = proj.avg_uprice || meta.avg_uprice || 22000;
          const bRent = proj.base_sqft_rent || meta.base_sqft_rent || 50;
          if (avgU > 0 && bRent > 0) {
            calcRoiStr = `${(bRent * 12 / avgU * 100).toFixed(2)}%`;
          } else {
            calcRoiStr = '3.80%';
          }
        }

        featuredList.push({
          name: name,
          filename: proj.filename || '',
          grade: meta.grade || proj.grade || 'A',
          region: meta.region || proj.region || '全港',
          district: meta.district || proj.district || '核心区',
          tier: tier,
          tierLabel: tierLabels[tier] || '精选推荐类',
          layout: meta.main_layout || proj.main_layout || '多元主流户型',
          priceRange: meta.total_price || proj.total_price_desc || (proj.stats ? `约 ${(proj.stats.total * 850 / 10000).toFixed(0)}万` : '价格详询'),
          sqftPrice: meta.sqft_price || proj.sqft_price_desc || '市场实时呎价',
          rentRange: meta.rent_range || proj.rent_range_desc || '详见月租分析',
          roi: calcRoiStr,
          reason: meta.reason || proj.reason || meta.selling_points || '精选香港优质稀缺地产资产，升值与收租兼备。',
          points: meta.selling_points || proj.selling_points || '地段优越，交通便利，居住品质高。',
          mainlandPoints: meta.mainland_selling_points || proj.mainland_selling_points || '适合内地专才落户、子女读书教育配置。',
          introUrl: introUrl,
          marketingUrl: marketingUrl
        });
      });
    });

    const aliasMap = {
      '波老道21号': ['21 borrett', 'borrett', '应天', '波老道', '波老道21号', '波老道21號', '21 borrett road'],
      '21 borrett road': ['21 borrett', 'borrett', '应天', '波老道', '波老道21号', '波老道21號', '21 borrett road'],
      '海盈山': ['海盈山', '海盈山4b', '海盈山4a', 'la montagne'],
      '傲玟': ['傲玟', 'grand homm', '何文田傲玟'],
      '瑜一': ['瑜一', 'in one', '瑜一天海', '瑜一ic'],
      '朗贤峰': ['朗贤峰', 'on manor'],
      '天玺天': ['天玺天', 'cullinan sky', '天玺．天'],
      '天玺海': ['天玺海', 'cullinan harbour', '天玺．海']
    };

    // 过滤价位段与搜索过滤
    const filtered = featuredList.filter(item => {
      const matchTier = currentTier === 'all' || item.tier === currentTier;
      const lowerQ = (featuredQuery || '').toLowerCase().strip ? (featuredQuery || '').toLowerCase().strip() : (featuredQuery || '').toLowerCase();
      const nameKey = item.name.toLowerCase();
      const aliases = aliasMap[item.name] || aliasMap[nameKey] || [];
      const matchName = nameKey.includes(lowerQ) || aliases.some(a => a.includes(lowerQ) || lowerQ.includes(a));

      const matchQuery = !featuredQuery || 
        matchName || 
        item.district.toLowerCase().includes(lowerQ) || 
        item.region.toLowerCase().includes(lowerQ) ||
        item.reason.toLowerCase().includes(lowerQ) ||
        item.mainlandPoints.toLowerCase().includes(lowerQ);

      return matchTier && matchQuery;
    });

    // 按照 A+、A、B、C 的顺序进行优先级排序
    const gradeOrderMap = { 'A+': 1, 'A': 2, 'B': 3, 'C': 4, 'D': 5 };
    filtered.sort((a, b) => {
      const gA = (a.grade || 'C').toUpperCase().replace('级', '').trim();
      const gB = (b.grade || 'C').toUpperCase().replace('级', '').trim();
      const orderA = gradeOrderMap[gA] || 99;
      const orderB = gradeOrderMap[gB] || 99;
      if (orderA !== orderB) return orderA - orderB;
      return a.name.localeCompare(b.name, 'zh-CN');
    });

    // 渲染全景高密度结构化表格视图 (Table View)
    tableBody.innerHTML = '';
    const colCount = showRoiCol ? 8 : 7;
    if (filtered.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="${colCount}" style="text-align:center; padding:3rem; color:#94a3b8;">未找到符合条件的精选盘源</td></tr>`;
    } else {
      filtered.forEach((item, idx) => {
        const tr = document.createElement('tr');
        tr.className = 'proj-row';
        tr.innerHTML = `
          <td>
            <div style="font-weight:800; font-size:0.95rem; color:#0f172a;">${item.name}</div>
            <div style="display:flex; gap:0.3rem; align-items:center; flex-wrap:wrap; margin-top:0.3rem;">
              <span class="${item.grade === 'A+' ? 'grade-badge-aplus' : (item.grade === 'A' ? 'grade-badge-a' : 'grade-badge-b')}" style="font-size:0.75rem; padding:0.15rem 0.5rem; display:inline-block;">${item.grade}级评级</span>
              ${(window.APP_DATA?.focus_projects || []).some(fp => item.name.includes(fp) || fp.includes(item.name)) ? '<span style="font-size:0.72rem; padding:0.15rem 0.45rem; display:inline-block; background:linear-gradient(135deg, #f59e0b, #d97706); color:#ffffff; font-weight:700; border-radius:6px; box-shadow:0 1px 4px rgba(245,158,11,0.3);">🔥 核心聚焦盘</span>' : ''}
            </div>
          </td>
          <td>
            <span class="badge badge-region">${item.region}</span><br>
            <span class="badge badge-district" style="margin-top:0.3rem;">${item.district}</span>
          </td>
          <td>
            <span style="font-size:0.76rem; color:#06AABD; font-weight:700; display:block;">${item.tierLabel}</span>
            <strong style="color:#e11d48; font-size:0.85rem;">${item.priceRange}</strong>
          </td>
          <td>
            <strong style="color:#0f172a;">${item.layout}</strong><br>
            <span style="color:#64748b; font-size:0.78rem;">${item.sqftPrice}</span>
          </td>
          ${showRoiCol ? `
          <td>
            <span style="color:#475569; font-size:0.78rem;">${item.rentRange}</span><br>
            <strong class="roi-val" style="font-size:1.05rem;">${item.roi}</strong>
          </td>` : ''}
          <td>
            ${formatReasonText(item.reason, idx)}
          </td>
          <td>
            <div style="background:#eef5f9; padding:0.6rem 0.8rem; border-radius:10px; border:1px solid #d0e4f0;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.3rem;">
                <span style="font-weight:700; color:#045d68; font-size:0.78rem;">🇨🇳 内地高净值卖点</span>
                <button class="btn-copy-points" onclick="copyMainlandPoints(this, '${encodeURIComponent(item.mainlandPoints)}')">📋 复制</button>
              </div>
              <div style="font-size:0.78rem; color:#334155; line-height:1.4; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; text-overflow:ellipsis;">
                ${item.mainlandPoints}
              </div>
              <button class="btn-toggle-points" style="font-size:0.74rem; margin-top:0.3rem;" onclick="toggleTableDrawer('drawer_${idx}')">▼ 展开完整解析</button>
            </div>
          </td>
          <td style="text-align:center;">
            <div style="display:flex; flex-direction:column; gap:0.35rem; align-items:center;">
              <button onclick="openGridModalByName('${item.name}')" class="btn-table-action" style="width:95px; justify-content:center;">🏢 销控网格</button>
              <button onclick="openAnalyticsModal('${item.name}')" class="btn-table-action" style="width:95px; justify-content:center;">📈 成交走势</button>
              <a href="${item.introUrl}" target="_blank" class="btn-table-action" style="width:95px; justify-content:center; color:#0284c7; border-color:#38bdf8; text-decoration:none;">📖 楼盘介绍</a>
              <a href="${item.marketingUrl}" target="_blank" class="btn-table-action" style="width:95px; justify-content:center; color:#06AABD; border-color:#06AABD; text-decoration:none;">🔗 营销工具</a>
            </div>
          </td>
        `;
        tableBody.appendChild(tr);

        // 创设展开抽屉行
        const drawerTr = document.createElement('tr');
        drawerTr.className = 'table-drawer-row';
        drawerTr.id = `drawer_${idx}`;
        drawerTr.style.display = 'none';
        drawerTr.innerHTML = `
          <td colspan="${colCount}">
            <div class="table-drawer-content">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.8rem;">
                <strong style="color:#045d68; font-size:0.92rem;">🇨🇳 ${item.name} - 对内地高净值客户专属卖点完整深度解析：</strong>
                <button class="btn-copy-points" style="padding:0.3rem 0.8rem; font-size:0.82rem;" onclick="copyMainlandPoints(this, '${encodeURIComponent(item.mainlandPoints)}')">📋 复制全部卖点文字</button>
              </div>
              <div style="line-height:1.6; color:#334155;">${item.mainlandPoints}</div>
            </div>
          </td>
        `;
        tableBody.appendChild(drawerTr);
      });
    }
  }

  // 全局推荐理由行内展开/折叠处理 (方案二)
  window.toggleReasonExpand = function(elemId, btn) {
    const el = document.getElementById(elemId);
    if (!el) return;
    const isExpanded = el.getAttribute('data-expanded') === 'true';
    if (!isExpanded) {
      el.style.webkitLineClamp = 'none';
      el.style.display = 'block';
      el.setAttribute('data-expanded', 'true');
      if (btn) btn.innerHTML = '▲ 折叠卖点';
    } else {
      el.style.webkitLineClamp = '3';
      el.style.display = '-webkit-box';
      el.setAttribute('data-expanded', 'false');
      if (btn) btn.innerHTML = '▼ 展开完整卖点';
    }
  };

  // 全局抽屉展开处理
  window.toggleTableDrawer = function(drawerId) {
    const drawer = document.getElementById(drawerId);
    if (!drawer) return;
    if (drawer.style.display === 'none' || !drawer.style.display) {
      drawer.style.display = 'table-row';
    } else {
      drawer.style.display = 'none';
    }
  };

  // 全局卖点折叠与复制处理
  window.toggleMainlandPoints = function(btn, targetId) {
    const elem = document.getElementById(targetId);
    if (!elem) return;
    if (elem.classList.contains('collapsed')) {
      elem.classList.remove('collapsed');
      btn.textContent = '收起 ▲';
    } else {
      elem.classList.add('collapsed');
      btn.textContent = '展开全部 ▼';
    }
  };

  window.copyMainlandPoints = function(btn, encodedText) {
    const text = decodeURIComponent(encodedText);
    navigator.clipboard.writeText(text).then(() => {
      const orig = btn.innerHTML;
      btn.innerHTML = '✅ 已复制!';
      btn.style.borderColor = '#10b981';
      btn.style.color = '#10b981';
      setTimeout(() => {
        btn.innerHTML = orig;
        btn.style.borderColor = '#06AABD';
        btn.style.color = '#06AABD';
      }, 2000);
    }).catch(err => {
      console.error('复制失败:', err);
    });
  };

  // 🔒 专属访问密码保护门 (Password Gate: lm8888)
  function initSiteAuth() {
    const AUTH_KEY = 'hk_site_auth_token';
    const TARGET_PWD = 'lm8888';

    const isUnlocked = sessionStorage.getItem(AUTH_KEY) === 'unlocked_lm8888' || localStorage.getItem(AUTH_KEY) === 'unlocked_lm8888';

    const overlay = document.getElementById('siteAuthOverlay');
    if (!isUnlocked) {
      document.documentElement.classList.add('site-locked');
      document.documentElement.classList.remove('unlocked-auth');
    } else {
      document.documentElement.classList.add('unlocked-auth');
      document.documentElement.classList.remove('site-locked');
      if (overlay) overlay.classList.add('unlocked');
      return;
    }

    if (!overlay) return;

    const pwdInput = document.getElementById('siteAuthPassword');
    const authBtn = document.getElementById('siteAuthBtn');
    const errorMsg = document.getElementById('siteAuthError');

    const verify = () => {
      const inputVal = (pwdInput?.value || '').trim();
      if (inputVal === TARGET_PWD) {
        sessionStorage.setItem(AUTH_KEY, 'unlocked_lm8888');
        localStorage.setItem(AUTH_KEY, 'unlocked_lm8888');
        document.documentElement.classList.add('unlocked-auth');
        document.documentElement.classList.remove('site-locked');
        overlay.classList.add('unlocked');
        if (errorMsg) errorMsg.textContent = '';
      } else {
        if (errorMsg) errorMsg.textContent = '❌ 密码错误，请重新输入';
        if (pwdInput) {
          pwdInput.style.borderColor = '#ef4444';
          pwdInput.focus();
          pwdInput.select();
        }
      }
    };

    if (authBtn) authBtn.onclick = verify;
    if (pwdInput) {
      pwdInput.onkeydown = (e) => {
        if (e.key === 'Enter') verify();
      };
    }
  }

  initSiteAuth();

  // 启动主逻辑
  loadData();
});
