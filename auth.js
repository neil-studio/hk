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

      /* 右上角用户状态栏 */
      #hkUserBadge {
        position: fixed;
        top: 12px;
        right: 14px;
        z-index: 99990;
        display: flex;
        align-items: center;
        gap: 8px;
        background: rgba(15, 23, 42, 0.88);
        backdrop-filter: blur(8px);
        color: #f8fafc;
        padding: 6px 12px;
        border-radius: 999px;
        font-size: 12px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.22);
        border: 1px solid rgba(255, 255, 255, 0.14);
        font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif;
      }
      #hkUserBadge .hk-role-pill {
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 11px;
        font-weight: 600;
      }
      #hkUserBadge a, #hkUserBadge button {
        color: #e2e8f0;
        background: rgba(255, 255, 255, 0.1);
        border: none;
        border-radius: 6px;
        padding: 3px 8px;
        font-size: 11px;
        cursor: pointer;
        text-decoration: none;
        transition: background 0.15s;
      }
      #hkUserBadge a:hover, #hkUserBadge button:hover {
        background: rgba(255, 255, 255, 0.22);
      }
      #hkUserBadge .hk-btn-admin {
        background: #7c3aed;
        color: #fff;
        font-weight: 600;
      }
      #hkUserBadge .hk-btn-admin:hover {
        background: #6d28d9;
      }
      @media (max-width: 640px) {
        #hkUserBadge {
          top: auto;
          bottom: 12px;
          right: 10px;
          padding: 5px 10px;
        }
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

  function mountUserBadge() {
    if (!currentUser || !document.body) return;
    const old = document.getElementById('hkUserBadge');
    if (old) old.remove();

    const badge = document.createElement('div');
    badge.id = 'hkUserBadge';
    const roleMeta = ROLE_LABELS[currentUser.role] || ROLE_LABELS.viewer;
    const prefix = getRootPrefix();

    const adminLink = currentUser.role === 'admin'
      ? `<a class="hk-btn-admin" href="${prefix}admin.html">👥 用户管理</a>`
      : '';

    badge.innerHTML = `
      <span class="hk-role-pill" style="background:${roleMeta.bg};color:${roleMeta.color}">${roleMeta.text}</span>
      <span style="font-weight:600;max-width:90px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${currentUser.username}">${currentUser.display_name || currentUser.username}</span>
      ${adminLink}
      <button type="button" id="hkChangePwdBtn">改密</button>
      <button type="button" id="hkLogoutBtn">退出</button>
    `;
    document.body.appendChild(badge);

    document.getElementById('hkLogoutBtn').addEventListener('click', logout);
    document.getElementById('hkChangePwdBtn').addEventListener('click', showChangePasswordModal);
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

  async function showLoginOverlay(mode = 'login') {
    injectStyles();
    revealPage();
    const old = document.getElementById('hkAuthOverlay');
    if (old) old.remove();

    const overlay = document.createElement('div');
    overlay.id = 'hkAuthOverlay';

    const isBootstrap = mode === 'bootstrap';
    overlay.innerHTML = `
      <div class="hk-auth-card">
        <h2 class="hk-auth-title">${isBootstrap ? '初始化超级管理员' : '香港一手新盘一站通'}</h2>
        <p class="hk-auth-sub">${isBootstrap ? '首次使用，请创建系统首个管理员账号' : '请输入您的授权账号与密码登录'}</p>
        <form id="hkAuthForm">
          <div class="hk-auth-field">
            <label>账号</label>
            <input type="text" id="hkAuthUser" value="${isBootstrap ? 'admin' : ''}" placeholder="请输入账号" autocomplete="username" required />
          </div>
          ${isBootstrap ? `
          <div class="hk-auth-field">
            <label>显示名称</label>
            <input type="text" id="hkAuthDisplayName" value="超级管理员" placeholder="例如：张经理" />
          </div>` : ''}
          <div class="hk-auth-field">
            <label>密码</label>
            <input type="password" id="hkAuthPass" placeholder="${isBootstrap ? '请设置至少 6 位密码' : '请输入密码'}" autocomplete="current-password" required />
          </div>
          ${!isBootstrap ? `
          <div class="hk-auth-row">
            <label style="display:flex;align-items:center;gap:6px;cursor:pointer;">
              <input type="checkbox" id="hkAuthRemember" checked /> 7天内记住登录状态
            </label>
          </div>` : ''}
          <button type="submit" id="hkAuthSubmit" class="hk-auth-btn">${isBootstrap ? '创建管理员并进入' : '登 录'}</button>
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

    // 检查后端是否尚未初始化
    if (!isBootstrap) {
      apiRequest('/api/health').then(health => {
        if (health && health.initialized === false) {
          extraEl.style.display = 'block';
          extraEl.innerHTML = '检测到系统尚未初始化，<button type="button" class="hk-auth-link" id="hkGoBootstrap">点此创建首个超级管理员</button>';
          document.getElementById('hkGoBootstrap').onclick = () => showLoginOverlay('bootstrap');
        }
      }).catch(err => {
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
      btnEl.textContent = isBootstrap ? '正在创建...' : '正在验证...';

      const username = document.getElementById('hkAuthUser').value.trim();
      const password = document.getElementById('hkAuthPass').value;

      try {
        if (isBootstrap) {
          const displayName = document.getElementById('hkAuthDisplayName').value.trim() || '超级管理员';
          await apiRequest('/api/bootstrap', {
            method: 'POST',
            body: JSON.stringify({ username, display_name: displayName, password })
          });
          // 创建后自动登录
          const loginRes = await apiRequest('/api/login', {
            method: 'POST',
            body: JSON.stringify({ username, password })
          });
          saveSession(loginRes.token, loginRes.user, true);
          currentUser = loginRes.user;
        } else {
          const remember = document.getElementById('hkAuthRemember').checked;
          const loginRes = await apiRequest('/api/login', {
            method: 'POST',
            body: JSON.stringify({ username, password })
          });
          saveSession(loginRes.token, loginRes.user, remember);
          currentUser = loginRes.user;
        }

        overlay.remove();
        onAuthenticated();
      } catch (err) {
        errEl.textContent = err.message || '登录失败，请检查网络或账号密码';
        errEl.style.display = 'block';
        btnEl.disabled = false;
        btnEl.textContent = isBootstrap ? '创建管理员并进入' : '登 录';
      }
    });
  }

  function onAuthenticated() {
    revealPage();
    applyPermissions();
    mountUserBadge();
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
    try {
      const res = await apiRequest('/api/me');
      currentUser = res.user;
      localStorage.setItem(AUTH_CONFIG.userKey, JSON.stringify(currentUser));
      onAuthenticated();
    } catch (err) {
      // Token 失效或被管理员踢下线
      clearSession();
      await showLoginOverlay('login');
    }
  }

  async function logout() {
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
    logout,
    ready
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAuth);
  } else {
    initAuth();
  }
})(window, document);
