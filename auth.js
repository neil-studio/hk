/**
 * 香港一手新盘一站通 — 全站统一鉴权与权限控制模块 (auth.js)
 * 对接 Cloudflare Workers + D1 云端鉴权服务
 */
(function (window, document) {
  'use strict';

  const AUTH_CONFIG = {
    // Cloudflare Worker 云端鉴权服务地址
    apiBase: localStorage.getItem('hk_auth_api_base') || 'https://hk-property-auth.enjoylife630.workers.dev',
    tokenKey: 'hk_auth_token',
    userKey: 'hk_auth_user'
  };

  // 支持通过 URL 参数 ?auth_api=http://127.0.0.1:8787 临时切换后端地址以便本地联调
  try {
    const params = new URLSearchParams(window.location.search);
    const overrideApi = params.get('auth_api');
    if (overrideApi) {
      localStorage.setItem('hk_auth_api_base', overrideApi.replace(/\/+$/, ''));
      AUTH_CONFIG.apiBase = overrideApi.replace(/\/+$/, '');
    }
  } catch (_) {}

  const ROLE_LABELS = {
    admin: { text: '超级管理员', bg: '#7c3aed', color: '#ffffff' },
    agent: { text: '内部顾问', bg: '#0284c7', color: '#ffffff' },
    viewer: { text: 'VIP 访客', bg: '#475569', color: '#ffffff' }
  };

  let currentUser = null;
  let authReadyResolvers = [];

  function getRootPrefix() {
    return window.location.pathname.includes('/map/') ? '../' : '';
  }

  function getToken() {
    return sessionStorage.getItem(AUTH_CONFIG.tokenKey) || localStorage.getItem(AUTH_CONFIG.tokenKey) || '';
  }

  function saveSession(token, user, remember = true) {
    sessionStorage.setItem(AUTH_CONFIG.tokenKey, token);
    sessionStorage.setItem(AUTH_CONFIG.userKey, JSON.stringify(user));
    localStorage.setItem('hk_last_active_at', String(Date.now()));
    if (remember) {
      localStorage.setItem(AUTH_CONFIG.tokenKey, token);
      localStorage.setItem(AUTH_CONFIG.userKey, JSON.stringify(user));
    } else {
      localStorage.removeItem(AUTH_CONFIG.tokenKey);
      localStorage.removeItem(AUTH_CONFIG.userKey);
    }
  }

  function clearSession() {
    sessionStorage.removeItem(AUTH_CONFIG.tokenKey);
    sessionStorage.removeItem(AUTH_CONFIG.userKey);
    localStorage.removeItem(AUTH_CONFIG.tokenKey);
    localStorage.removeItem(AUTH_CONFIG.userKey);
    localStorage.removeItem('hk_last_active_at');
    currentUser = null;
  }

  async function apiRequest(path, options = {}) {
    const token = getToken();
    const headers = {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {})
    };
    const res = await fetch(`${AUTH_CONFIG.apiBase}${path}`, {
      ...options,
      headers
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const err = new Error(data.error || `请求失败 (${res.status})`);
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  }

  function injectStyles() {
    if (document.getElementById('hk-auth-styles')) return;
    const style = document.createElement('style');
    style.id = 'hk-auth-styles';
    style.textContent = `
      /* 按角色控制功能可见性 */
      body.hk-role-viewer [data-auth-perm="marketing_tools"],
      body.hk-role-viewer [data-auth-perm="map_export"],
      body.hk-role-viewer [data-auth-perm="map_admin"],
      body.hk-role-viewer [data-auth-perm="user_admin"],
      body.hk-role-viewer .btn-marketing-action,
      body.hk-role-viewer .btn-marketing-disabled,
      body.hk-role-viewer .btn-export-main,
      body.hk-role-viewer .btn-selected-export {
        display: none !important;
      }
      body.hk-role-agent [data-auth-perm="map_admin"],
      body.hk-role-agent [data-auth-perm="user_admin"] {
        display: none !important;
      }

      #hkAuthOverlay {
        position: fixed;
        inset: 0;
        z-index: 999999;
        background: radial-gradient(circle at top, #1e293b 0%, #0f172a 70%);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 20px;
        font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
      }
      .hk-auth-card {
        width: 100%;
        max-width: 400px;
        background: rgba(255, 255, 255, 0.98);
        border-radius: 16px;
        padding: 32px 28px;
        box-shadow: 0 24px 60px rgba(0, 0, 0, 0.45);
        color: #0f172a;
      }
      .hk-auth-title {
        font-size: 20px;
        font-weight: 700;
        margin: 0 0 6px;
        text-align: center;
        color: #0f172a;
      }
      .hk-auth-sub {
        font-size: 13px;
        color: #64748b;
        margin: 0 0 22px;
        text-align: center;
      }
      .hk-auth-field {
        margin-bottom: 14px;
      }
      .hk-auth-field label {
        display: block;
        font-size: 13px;
        font-weight: 600;
        color: #334155;
        margin-bottom: 6px;
      }
      .hk-auth-field input {
        width: 100%;
        box-sizing: border-box;
        padding: 11px 13px;
        border: 1.5px solid #cbd5e1;
        border-radius: 10px;
        font-size: 14px;
        outline: none;
        transition: border-color 0.2s;
      }
      .hk-auth-field input:focus {
        border-color: #2563eb;
      }
      .hk-auth-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 16px;
        font-size: 13px;
        color: #475569;
      }
      .hk-auth-btn {
        width: 100%;
        padding: 12px;
        border: none;
        border-radius: 10px;
        background: linear-gradient(135deg, #2563eb, #1d4ed8);
        color: #fff;
        font-size: 15px;
        font-weight: 600;
        cursor: pointer;
        transition: opacity 0.2s;
      }
      .hk-auth-btn:disabled {
        opacity: 0.6;
        cursor: not-allowed;
      }
      .hk-auth-err {
        margin-top: 12px;
        padding: 10px 12px;
        border-radius: 8px;
        background: #fef2f2;
        border: 1px solid #fecaca;
        color: #dc2626;
        font-size: 13px;
        display: none;
      }
      .hk-auth-bootstrap-tip {
        margin-top: 14px;
        padding-top: 12px;
        border-top: 1px dashed #e2e8f0;
        text-align: center;
        font-size: 12px;
        color: #64748b;
      }
      .hk-auth-link {
        color: #2563eb;
        cursor: pointer;
        text-decoration: underline;
        background: none;
        border: none;
        padding: 0;
        font-size: 12px;
      }

      /* 首页页头内嵌用户菜单（浅色融入原风格，零遮挡） */
      .header-actions {
        display: flex;
        align-items: center;
        gap: 10px;
        flex-wrap: wrap;
        justify-content: flex-end;
      }
      #hkUserBadge {
        position: relative;
        display: inline-flex;
        align-items: center;
        font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif;
      }
      #hkUserTrigger {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(255, 255, 255, 0.92);
        color: #1e293b;
        border: 1px solid #cbd5e1;
        border-radius: 999px;
        padding: 5px 12px;
        font-size: 12px;
        font-weight: 600;
        cursor: pointer;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
        transition: all 0.15s;
      }
      #hkUserTrigger:hover {
        background: #ffffff;
        border-color: #94a3b8;
      }
      #hkUserTrigger .hk-role-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        display: inline-block;
      }
      #hkUserTrigger .hk-role-tag {
        font-size: 11px;
        font-weight: 600;
        color: #64748b;
      }
      #hkUserMenu {
        position: absolute;
        top: calc(100% + 6px);
        right: 0;
        min-width: 170px;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        box-shadow: 0 12px 30px rgba(15, 23, 42, 0.14);
        padding: 6px;
        z-index: 99990;
        display: none;
      }
      #hkUserMenu.open {
        display: block;
      }
      .hk-menu-head {
        padding: 6px 10px 8px;
        border-bottom: 1px solid #f1f5f9;
        margin-bottom: 4px;
        font-size: 12px;
        color: #64748b;
      }
      .hk-menu-head strong {
        display: block;
        color: #0f172a;
        font-size: 13px;
      }
      #hkUserMenu a, #hkUserMenu button {
        width: 100%;
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 10px;
        border: none;
        background: transparent;
        color: #334155;
        font-size: 13px;
        font-weight: 500;
        border-radius: 8px;
        cursor: pointer;
        text-decoration: none;
        text-align: left;
      }
      #hkUserMenu a:hover, #hkUserMenu button:hover {
        background: #f1f5f9;
        color: #0f172a;
      }
      #hkUserMenu .hk-menu-admin {
        color: #6d28d9;
        font-weight: 600;
      }
      #hkUserMenu .hk-menu-logout {
        color: #dc2626;
      }
    `;
    document.head.appendChild(style);
  }

  function revealPage() {
    document.documentElement.style.visibility = 'visible';
  }

  function applyPermissions() {
    if (!currentUser || !document.body) return;
    document.body.classList.remove('hk-role-admin', 'hk-role-agent', 'hk-role-viewer');
    document.body.classList.add(`hk-role-${currentUser.role}`);

    document.querySelectorAll('[data-auth-perm]').forEach(el => {
      const perm = el.getAttribute('data-auth-perm');
      if (!hasPermission(perm)) {
        el.style.display = 'none';
      }
    });

    document.querySelectorAll('[data-auth-role]').forEach(el => {
      const allowed = (el.getAttribute('data-auth-role') || '').split(',').map(s => s.trim());
      if (!allowed.includes(currentUser.role)) {
        el.style.display = 'none';
      }
    });
  }

  function isHomePage() {
    const p = window.location.pathname;
    if (p.includes('/map/')) return false;
    return p === '/' || p.endsWith('/index.html') || p.endsWith('/hk') || p.endsWith('/hk/');
  }

  function mountUserBadge() {
    if (!currentUser || !document.body) return;
    const old = document.getElementById('hkUserBadge');
    if (old) old.remove();

    // 仅在首页页头文档流内展示，不遮挡其他页面（如地图导出按钮）
    if (!isHomePage()) return;
    const headerActions = document.querySelector('.header-actions');
    if (!headerActions) return;

    const badge = document.createElement('div');
    badge.id = 'hkUserBadge';
    const roleMeta = ROLE_LABELS[currentUser.role] || ROLE_LABELS.viewer;
    const prefix = getRootPrefix();
    const displayName = currentUser.display_name || currentUser.username;

    const adminLink = currentUser.role === 'admin'
      ? `<a class="hk-menu-admin" href="${prefix}admin.html">👥 用户管理后台</a>`
      : '';

    badge.innerHTML = `
      <button type="button" id="hkUserTrigger" title="账号与权限菜单">
        <span class="hk-role-dot" style="background:${roleMeta.bg};"></span>
        <span>${displayName}</span>
        <span class="hk-role-tag">(${roleMeta.text})</span>
        <span style="font-size:10px;color:#94a3b8;">▾</span>
      </button>
      <div id="hkUserMenu">
        <div class="hk-menu-head">
          <strong>${displayName}</strong>
          <span>账号：${currentUser.username} · ${roleMeta.text}</span>
        </div>
        ${adminLink}
        <button type="button" id="hkChangePwdBtn">🔑 修改密码</button>
        <button type="button" id="hkLogoutBtn" class="hk-menu-logout">🚪 退出登录</button>
      </div>
    `;
    headerActions.appendChild(badge);

    const trigger = document.getElementById('hkUserTrigger');
    const menu = document.getElementById('hkUserMenu');
    trigger.addEventListener('click', (e) => {
      e.stopPropagation();
      menu.classList.toggle('open');
    });
    document.addEventListener('click', (e) => {
      if (!badge.contains(e.target)) {
        menu.classList.remove('open');
      }
    });

    document.getElementById('hkLogoutBtn').addEventListener('click', logout);
    document.getElementById('hkChangePwdBtn').addEventListener('click', () => {
      menu.classList.remove('open');
      showChangePasswordModal();
    });
  }

  function showChangePasswordModal() {
    const old = document.getElementById('hkPwdModal');
    if (old) old.remove();

    const modal = document.createElement('div');
    modal.id = 'hkPwdModal';
    modal.style.cssText = 'position:fixed;inset:0;z-index:999999;background:rgba(15,23,42,0.65);display:flex;align-items:center;justify-content:center;padding:20px;';
    modal.innerHTML = `
      <div class="hk-auth-card" style="max-width:360px;">
        <h3 class="hk-auth-title" style="font-size:18px;">修改登录密码</h3>
        <p class="hk-auth-sub">当前账号：${currentUser.username}</p>
        <div class="hk-auth-field">
          <label>原密码</label>
          <input type="password" id="hkOldPwd" placeholder="请输入原密码" />
        </div>
        <div class="hk-auth-field">
          <label>新密码（至少 6 位）</label>
          <input type="password" id="hkNewPwd" placeholder="请输入新密码" />
        </div>
        <div style="display:flex;gap:10px;margin-top:16px;">
          <button type="button" id="hkPwdCancel" class="hk-auth-btn" style="background:#e2e8f0;color:#334155;">取消</button>
          <button type="button" id="hkPwdSubmit" class="hk-auth-btn">确认修改</button>
        </div>
        <div id="hkPwdErr" class="hk-auth-err"></div>
      </div>
    `;
    document.body.appendChild(modal);

    document.getElementById('hkPwdCancel').onclick = () => modal.remove();
    document.getElementById('hkPwdSubmit').onclick = async () => {
      const oldPassword = document.getElementById('hkOldPwd').value;
      const newPassword = document.getElementById('hkNewPwd').value;
      const errEl = document.getElementById('hkPwdErr');
      errEl.style.display = 'none';
      try {
        await apiRequest('/api/change-password', {
          method: 'POST',
          body: JSON.stringify({ old_password: oldPassword, new_password: newPassword })
        });
        alert('密码修改成功！');
        modal.remove();
      } catch (err) {
        errEl.textContent = err.message;
        errEl.style.display = 'block';
      }
    };
  }

  async function showLoginOverlay(mode = 'login', setupInfo = null) {
    injectStyles();
    revealPage();
    const old = document.getElementById('hkAuthOverlay');
    if (old) old.remove();

    const overlay = document.createElement('div');
    overlay.id = 'hkAuthOverlay';

    const isBootstrap = mode === 'bootstrap';
    const isSetup = mode === 'setup';
    const titleText = isBootstrap
      ? '初始化超级管理员'
      : isSetup
        ? '首次登录 · 设置专属密码'
        : '香港一手新盘一站通';
    const subText = isBootstrap
      ? '首次使用，请创建系统首个管理员账号'
      : isSetup
        ? `欢迎 ${setupInfo?.display_name || setupInfo?.username || ''}，请设置密码激活账号`
        : '请输入您的授权账号与密码登录（首次登录密码可留空）';

    overlay.innerHTML = `
      <div class="hk-auth-card">
        <h2 class="hk-auth-title">${titleText}</h2>
        <p class="hk-auth-sub">${subText}</p>
        <form id="hkAuthForm">
          <div class="hk-auth-field">
            <label>账号</label>
            <input type="text" id="hkAuthUser" value="${isBootstrap ? 'admin' : isSetup ? (setupInfo?.username || '') : ''}" ${isSetup ? 'readonly style="background:#f1f5f9;color:#475569;"' : ''} placeholder="请输入账号" autocomplete="username" required />
          </div>
          ${isBootstrap ? `
          <div class="hk-auth-field">
            <label>显示名称</label>
            <input type="text" id="hkAuthDisplayName" value="超级管理员" placeholder="例如：张经理" />
          </div>` : ''}
          <div class="hk-auth-field">
            <label>${isSetup ? '设置新密码（至少 6 位）' : '密码'}</label>
            <input type="password" id="hkAuthPass" placeholder="${isBootstrap || isSetup ? '请设置至少 6 位密码' : '请输入密码（首次登录可留空）'}" autocomplete="${isSetup ? 'new-password' : 'current-password'}" ${isBootstrap || isSetup ? 'required' : ''} />
          </div>
          ${isSetup ? `
          <div class="hk-auth-field">
            <label>确认新密码</label>
            <input type="password" id="hkAuthPassConfirm" placeholder="请再次输入新密码" autocomplete="new-password" required />
          </div>` : ''}
          ${!isBootstrap ? `
          <div class="hk-auth-row">
            <label style="display:flex;align-items:center;gap:6px;cursor:pointer;">
              <input type="checkbox" id="hkAuthRemember" checked /> 7天内记住登录状态
            </label>
          </div>` : ''}
          <button type="submit" id="hkAuthSubmit" class="hk-auth-btn">${isBootstrap ? '创建管理员并进入' : isSetup ? '设置密码并进入' : '登 录'}</button>
          <div id="hkAuthErr" class="hk-auth-err"></div>
        </form>
        <div id="hkAuthExtra" class="hk-auth-bootstrap-tip" style="display:none;"></div>
      </div>
    `;
    document.body.appendChild(overlay);

    const form = document.getElementById('hkAuthForm');
    const errEl = document.getElementById('hkAuthErr');
    const btnEl = document.getElementById('hkAuthSubmit');
    const extraEl = document.getElementById('hkAuthExtra');

    if (mode === 'login') {
      apiRequest('/api/health').then(health => {
        if (health && health.initialized === false) {
          extraEl.style.display = 'block';
          extraEl.innerHTML = '检测到系统尚未初始化，<button type="button" class="hk-auth-link" id="hkGoBootstrap">点此创建首个超级管理员</button>';
          document.getElementById('hkGoBootstrap').onclick = () => showLoginOverlay('bootstrap');
        }
      }).catch(() => {
        extraEl.style.display = 'block';
        extraEl.innerHTML = `<span style="color:#b45309;">⚠️ 暂未连接到鉴权服务 (${AUTH_CONFIG.apiBase})，请确认 Worker 已部署</span>`;
      });
    } else {
      extraEl.style.display = 'block';
      extraEl.innerHTML = '<button type="button" class="hk-auth-link" id="hkBackLogin">返回账号登录</button>';
      document.getElementById('hkBackLogin').onclick = () => showLoginOverlay('login');
    }

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      errEl.style.display = 'none';
      btnEl.disabled = true;
      btnEl.textContent = isBootstrap ? '正在创建...' : isSetup ? '正在激活...' : '正在验证...';

      const username = document.getElementById('hkAuthUser').value.trim();
      const password = document.getElementById('hkAuthPass').value;

      try {
        if (isBootstrap) {
          const displayName = document.getElementById('hkAuthDisplayName').value.trim() || '超级管理员';
          await apiRequest('/api/bootstrap', {
            method: 'POST',
            body: JSON.stringify({ username, display_name: displayName, password })
          });
          const loginRes = await apiRequest('/api/login', {
            method: 'POST',
            body: JSON.stringify({ username, password })
          });
          saveSession(loginRes.token, loginRes.user, true);
          currentUser = loginRes.user;
        } else if (isSetup) {
          const confirmPwd = document.getElementById('hkAuthPassConfirm').value;
          if (password.length < 6) {
            throw new Error('新密码长度至少 6 位');
          }
          if (password !== confirmPwd) {
            throw new Error('两次输入的密码不一致');
          }
          const remember = document.getElementById('hkAuthRemember').checked;
          const setupRes = await apiRequest('/api/setup-password', {
            method: 'POST',
            body: JSON.stringify({ username, new_password: password })
          });
          saveSession(setupRes.token, setupRes.user, remember);
          currentUser = setupRes.user;
        } else {
          const remember = document.getElementById('hkAuthRemember').checked;
          const loginRes = await apiRequest('/api/login', {
            method: 'POST',
            body: JSON.stringify({ username, password })
          });
          if (loginRes.requires_password_setup) {
            await showLoginOverlay('setup', {
              username: loginRes.username,
              display_name: loginRes.display_name
            });
            return;
          }
          saveSession(loginRes.token, loginRes.user, remember);
          currentUser = loginRes.user;
        }

        overlay.remove();
        onAuthenticated();
      } catch (err) {
        errEl.textContent = err.message || '登录失败，请检查网络或账号密码';
        errEl.style.display = 'block';
        btnEl.disabled = false;
        btnEl.textContent = isBootstrap ? '创建管理员并进入' : isSetup ? '设置密码并进入' : '登 录';
      }
    });
  }

  // ==================== 活动量低频采集与无操作超时控制 ====================
  const IDLE_PAUSE_MS = 10 * 60 * 1000;        // 10 分钟无操作暂停计入有效时长
  const IDLE_LOGOUT_MS = 12 * 60 * 60 * 1000;  // 12 小时无操作强制退出登录
  const SYNC_INTERVAL_MS = 12 * 60 * 60 * 1000; // 12 小时汇总上报周期
  const BUFFER_KEY = 'hk_activity_buffer';
  const LAST_SYNC_KEY = 'hk_activity_last_sync';
  const LAST_ACTIVE_KEY = 'hk_last_active_at';
  let trackerStarted = false;

  function detectModule() {
    const p = window.location.pathname;
    if (p.includes('/map/')) return 'map';
    if (p.includes('sales.html')) return 'sales';
    if (p.includes('analytics.html')) return 'analytics';
    if (p.includes('featured.html')) return 'featured';
    if (p.includes('secondhand.html')) return 'secondhand';
    if (p.includes('admin.html')) return 'admin';
    return 'home';
  }

  function getTodayStr() {
    const d = new Date(Date.now() + 8 * 3600 * 1000); // 北京/香港时间 YYYY-MM-DD
    return d.toISOString().slice(0, 10);
  }

  function readActivityBuffer() {
    try {
      return JSON.parse(localStorage.getItem(BUFFER_KEY) || '{}') || {};
    } catch (_) {
      return {};
    }
  }

  function writeActivityBuffer(buf) {
    try {
      localStorage.setItem(BUFFER_KEY, JSON.stringify(buf));
    } catch (_) {}
  }

  function recordActivityDelta(moduleName, { visits = 0, clicks = 0, exports = 0, active_seconds = 0 }) {
    if (!currentUser) return;
    const date = getTodayStr();
    const key = `${currentUser.id}|${date}|${moduleName}`;
    const buf = readActivityBuffer();
    if (!buf[key]) {
      buf[key] = { user_id: currentUser.id, date, module: moduleName, visits: 0, clicks: 0, exports: 0, active_seconds: 0 };
    }
    buf[key].visits += visits;
    buf[key].clicks += clicks;
    buf[key].exports = (buf[key].exports || 0) + exports;
    buf[key].active_seconds += active_seconds;
    writeActivityBuffer(buf);
  }

  function trackExport(moduleName = null) {
    recordActivityDelta(moduleName || detectModule(), { exports: 1 });
  }

  async function flushActivity(useBeacon = false) {
    const token = getToken();
    if (!token) return;
    const buf = readActivityBuffer();
    const allEntries = Object.entries(buf);
    if (allEntries.length === 0) return;

    const uid = currentUser ? currentUser.id : null;
    const items = [];
    const remaining = {};
    for (const [k, v] of allEntries) {
      if (!uid || v.user_id === uid) {
        items.push({
          date: v.date,
          module: v.module,
          visits: v.visits || 0,
          clicks: v.clicks || 0,
          exports: v.exports || 0,
          active_seconds: v.active_seconds || 0
        });
      } else {
        remaining[k] = v;
      }
    }
    if (items.length === 0) return;

    writeActivityBuffer(remaining);
    localStorage.setItem(LAST_SYNC_KEY, String(Date.now()));

    const url = `${AUTH_CONFIG.apiBase}/api/activity/sync`;
    if (useBeacon && navigator.sendBeacon) {
      try {
        // 使用纯文本字符串避免触发跨域 OPTIONS 预检，确保关闭页面时 100% 送达
        const sent = navigator.sendBeacon(url, JSON.stringify({ token, items }));
        if (sent) return;
      } catch (_) {}
    }

    try {
      await apiRequest('/api/activity/sync', {
        method: 'POST',
        body: JSON.stringify({ items })
      });
    } catch (_) {
      // 网络失败时放回本地账本，下次补报
      const cur = readActivityBuffer();
      for (const it of items) {
        const key = `${uid || 'x'}|${it.date}|${it.module}`;
        if (!cur[key]) cur[key] = { user_id: uid, ...it };
        else {
          cur[key].visits += it.visits;
          cur[key].clicks += it.clicks;
          cur[key].exports = (cur[key].exports || 0) + (it.exports || 0);
          cur[key].active_seconds += it.active_seconds;
        }
      }
      writeActivityBuffer(cur);
    }
  }

  function isIdleTimedOut() {
    const last = Number(localStorage.getItem(LAST_ACTIVE_KEY) || 0);
    return last > 0 && Date.now() - last >= IDLE_LOGOUT_MS;
  }

  function startActivityTracker() {
    if (trackerStarted || !currentUser) return;
    trackerStarted = true;

    const mod = detectModule();
    if (!localStorage.getItem(LAST_ACTIVE_KEY)) {
      localStorage.setItem(LAST_ACTIVE_KEY, String(Date.now()));
    }

    // 记录本次进入板块访问 +1
    recordActivityDelta(mod, { visits: 1 });

    // 若本地有积压超过 12 小时的未同步数据，顺手补报一次
    const lastSync = Number(localStorage.getItem(LAST_SYNC_KEY) || 0);
    if (!lastSync || Date.now() - lastSync >= SYNC_INTERVAL_MS) {
      flushActivity(false);
    }

    let lastTouchWrite = 0;
    const touchActive = () => {
      const now = Date.now();
      if (now - lastTouchWrite > 5000) {
        lastTouchWrite = now;
        localStorage.setItem(LAST_ACTIVE_KEY, String(now));
      }
    };

    ['mousemove', 'mousedown', 'keydown', 'scroll', 'touchstart'].forEach(evt => {
      window.addEventListener(evt, touchActive, { passive: true });
    });

    // 记录有效点击次数（仅记录真实按钮/链接/交互元素或页面点击）
    document.addEventListener('click', (e) => {
      touchActive();
      if (e.target && e.target.closest && e.target.closest('#hkAuthOverlay')) return;
      recordActivityDelta(mod, { clicks: 1 });
    }, true);

    // 每 30 秒检测一次：10分钟无操作暂停时长，12小时无操作强制登出
    setInterval(async () => {
      if (!currentUser) return;
      const now = Date.now();
      const lastActive = Number(localStorage.getItem(LAST_ACTIVE_KEY) || now);
      const idleMs = now - lastActive;

      if (idleMs >= IDLE_LOGOUT_MS) {
        await flushActivity(false);
        await logout();
        return;
      }

      if (idleMs < IDLE_PAUSE_MS && !document.hidden) {
        recordActivityDelta(mod, { active_seconds: 30 });
      }

      const ls = Number(localStorage.getItem(LAST_SYNC_KEY) || 0);
      if (ls && now - ls >= SYNC_INTERVAL_MS) {
        flushActivity(false);
      }
    }, 30000);

    // 页面隐藏或关闭时通过 sendBeacon 低频打包上报（防丢数）
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        flushActivity(true);
      }
    });
    window.addEventListener('pagehide', () => {
      flushActivity(true);
    });
  }

  function onAuthenticated() {
    revealPage();
    applyPermissions();
    mountUserBadge();
    startActivityTracker();
    if (currentUser.role === 'admin') {
      try { localStorage.setItem('sandbox_admin_mode', 'true'); } catch (_) {}
    } else {
      try { localStorage.removeItem('sandbox_admin_mode'); } catch (_) {}
    }
    if (typeof window.map !== 'undefined' && window.map && window.map.invalidateSize) {
      setTimeout(() => window.map.invalidateSize(), 200);
    }
    window.dispatchEvent(new CustomEvent('hk-auth-ready', { detail: currentUser }));
    authReadyResolvers.forEach(r => r(currentUser));
    authReadyResolvers = [];
  }

  async function initAuth() {
    injectStyles();
    const token = getToken();
    if (!token) {
      await showLoginOverlay('login');
      return;
    }
    if (isIdleTimedOut()) {
      await flushActivity(false);
      try { await apiRequest('/api/logout', { method: 'POST' }); } catch (_) {}
      clearSession();
      await showLoginOverlay('login');
      return;
    }

    // 优先读取本地缓存用户信息实现 0ms 秒开，同时后台异步向云端核验有效性
    let cachedUser = null;
    try {
      const raw = sessionStorage.getItem(AUTH_CONFIG.userKey) || localStorage.getItem(AUTH_CONFIG.userKey);
      if (raw) cachedUser = JSON.parse(raw);
    } catch (_) {}

    if (cachedUser && cachedUser.username) {
      currentUser = cachedUser;
      onAuthenticated();
      apiRequest('/api/me')
        .then(res => {
          if (res && res.user) {
            currentUser = res.user;
            localStorage.setItem(AUTH_CONFIG.userKey, JSON.stringify(currentUser));
            applyPermissions();
          }
        })
        .catch(async (err) => {
          if (err && (err.status === 401 || err.status === 403)) {
            clearSession();
            await showLoginOverlay('login');
          }
        });
      return;
    }

    try {
      const res = await apiRequest('/api/me');
      currentUser = res.user;
      localStorage.setItem(AUTH_CONFIG.userKey, JSON.stringify(currentUser));
      onAuthenticated();
    } catch (err) {
      clearSession();
      await showLoginOverlay('login');
    }
  }

  async function logout() {
    await flushActivity(false);
    try {
      await apiRequest('/api/logout', { method: 'POST' });
    } catch (_) {}
    clearSession();
    window.location.reload();
  }

  function hasPermission(perm) {
    if (!currentUser) return false;
    if (currentUser.role === 'admin') return true;
    return Array.isArray(currentUser.permissions) && currentUser.permissions.includes(perm);
  }

  function getUser() {
    return currentUser;
  }

  function getRole() {
    return currentUser ? currentUser.role : null;
  }

  function ready() {
    if (currentUser) return Promise.resolve(currentUser);
    return new Promise(resolve => authReadyResolvers.push(resolve));
  }

  window.HKAuth = {
    config: AUTH_CONFIG,
    apiRequest,
    getUser,
    getRole,
    hasPermission,
    applyPermissions,
    trackExport,
    flushActivity,
    logout,
    ready
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAuth);
  } else {
    initAuth();
  }
})(window, document);
