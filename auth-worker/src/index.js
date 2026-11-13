/**
 * 香港一手新盘一站通 — 用户管理与权限控制 Worker (Cloudflare Workers + D1)
 */

const ROLE_PERMISSIONS = {
  admin: ['marketing_tools', 'map_export', 'map_admin', 'user_admin', 'secondhand'],
  agent: ['marketing_tools', 'map_export', 'secondhand'],
  viewer: []
};

const VALID_ROLES = new Set(['admin', 'agent', 'viewer']);
const SESSION_TTL_HOURS = 24 * 7; // 7 天有效期

// ==================== 工具函数 ====================

function getCorsHeaders(request, env) {
  const origin = request.headers.get('Origin') || '';
  const allowed = (env.ALLOWED_ORIGINS || '')
    .split(',')
    .map(s => s.trim())
    .filter(Boolean);

  let allowOrigin = allowed[0] || '*';
  if (origin && (allowed.includes(origin) || origin.startsWith('http://localhost:') || origin.startsWith('http://127.0.0.1:'))) {
    allowOrigin = origin;
  }

  return {
    'Access-Control-Allow-Origin': allowOrigin,
    'Access-Control-Allow-Methods': 'GET, POST, PATCH, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Max-Age': '86400',
    'Vary': 'Origin'
  };
}

function jsonResponse(data, status = 200, corsHeaders = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      ...corsHeaders
    }
  });
}

function toHex(buffer) {
  return Array.from(new Uint8Array(buffer))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');
}

function fromHex(hex) {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) {
    bytes[i / 2] = parseInt(hex.slice(i, i + 2), 16);
  }
  return bytes;
}

async function hashPassword(password, saltHex = null) {
  const salt = saltHex ? fromHex(saltHex) : crypto.getRandomValues(new Uint8Array(16));
  const enc = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey(
    'raw',
    enc.encode(password),
    { name: 'PBKDF2' },
    false,
    ['deriveBits']
  );
  const derived = await crypto.subtle.deriveBits(
    {
      name: 'PBKDF2',
      salt,
      iterations: 100000,
      hash: 'SHA-256'
    },
    keyMaterial,
    256
  );
  return `pbkdf2$${toHex(salt)}$${toHex(derived)}`;
}

async function verifyPassword(password, storedHash) {
  if (!storedHash || !storedHash.startsWith('pbkdf2$')) return false;
  const parts = storedHash.split('$');
  if (parts.length !== 3) return false;
  const [, saltHex] = parts;
  const candidate = await hashPassword(password, saltHex);
  // 常时间比较
  if (candidate.length !== storedHash.length) return false;
  let diff = 0;
  for (let i = 0; i < candidate.length; i++) {
    diff |= candidate.charCodeAt(i) ^ storedHash.charCodeAt(i);
  }
  return diff === 0;
}

function generateToken() {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  return toHex(bytes);
}

function getClientMeta(request) {
  return {
    ip: request.headers.get('CF-Connecting-IP') || request.headers.get('X-Forwarded-For') || '',
    ua: (request.headers.get('User-Agent') || '').slice(0, 200)
  };
}

function isExpired(expiresAt) {
  if (!expiresAt) return false;
  const ts = Date.parse(expiresAt.includes('T') ? expiresAt : expiresAt.replace(' ', 'T') + 'Z');
  return !Number.isNaN(ts) && ts <= Date.now();
}

function formatUserPublic(user) {
  return {
    id: user.id,
    username: user.username,
    display_name: user.display_name || user.username,
    role: user.role,
    permissions: ROLE_PERMISSIONS[user.role] || [],
    is_active: Boolean(user.is_active),
    expires_at: user.expires_at,
    single_session: Boolean(user.single_session),
    last_login_at: user.last_login_at,
    created_at: user.created_at
  };
}

async function writeAuditLog(env, { username, userId = null, role = '', action, success = true, detail = '', ip = '', ua = '' }) {
  try {
    await env.DB.prepare(
      `INSERT INTO audit_logs (username, user_id, role, action, success, detail, ip, user_agent)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`
    )
      .bind(username, userId, role, action, success ? 1 : 0, detail, ip, ua)
      .run();
  } catch (e) {
    console.error('Audit log error:', e);
  }
}

async function authenticateRequest(request, env) {
  const authHeader = request.headers.get('Authorization') || '';
  const token = authHeader.startsWith('Bearer ') ? authHeader.slice(7).trim() : '';
  if (!token) return null;

  const row = await env.DB.prepare(
    `SELECT s.token, s.expires_at AS session_expires_at, u.*
     FROM sessions s
     JOIN users u ON u.id = s.user_id
     WHERE s.token = ?`
  )
    .bind(token)
    .first();

  if (!row) return null;
  if (isExpired(row.session_expires_at)) {
    await env.DB.prepare('DELETE FROM sessions WHERE token = ?').bind(token).run();
    return null;
  }
  if (!row.is_active || isExpired(row.expires_at)) {
    return null;
  }
  return { token, user: row };
}

// ==================== 路由处理 ====================

export default {
  async fetch(request, env) {
    const cors = getCorsHeaders(request, env);

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: cors });
    }

    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, '') || '/';
    const meta = getClientMeta(request);

    try {
      // 1. 健康检查
      if (path === '/api/health' && request.method === 'GET') {
        const countRow = await env.DB.prepare('SELECT COUNT(*) AS cnt FROM users').first();
        return jsonResponse({ ok: true, initialized: (countRow?.cnt || 0) > 0 }, 200, cors);
      }

      // 2. 首次初始化超级管理员（仅当 users 表为空时可用）
      if (path === '/api/bootstrap' && request.method === 'POST') {
        const countRow = await env.DB.prepare('SELECT COUNT(*) AS cnt FROM users').first();
        if ((countRow?.cnt || 0) > 0) {
          return jsonResponse({ error: '系统已初始化，禁止重复创建初始管理员' }, 403, cors);
        }
        const body = await request.json().catch(() => ({}));
        const username = String(body.username || 'admin').trim();
        const password = String(body.password || '').trim();
        const displayName = String(body.display_name || '超级管理员').trim();
        if (!username || password.length < 6) {
          return jsonResponse({ error: '管理员账号不能为空且密码至少 6 位' }, 400, cors);
        }
        const pwHash = await hashPassword(password);
        await env.DB.prepare(
          `INSERT INTO users (username, display_name, password_hash, role, is_active)
           VALUES (?, ?, ?, 'admin', 1)`
        )
          .bind(username, displayName, pwHash)
          .run();
        await writeAuditLog(env, {
          username,
          role: 'admin',
          action: 'bootstrap',
          success: true,
          detail: '初始化系统超级管理员',
          ...meta
        });
        return jsonResponse({ ok: true, message: `初始管理员 ${username} 创建成功` }, 201, cors);
      }

      // 3. 登录
      if (path === '/api/login' && request.method === 'POST') {
        const body = await request.json().catch(() => ({}));
        const username = String(body.username || '').trim();
        const password = String(body.password || '');

        if (!username || !password) {
          return jsonResponse({ error: '请输入账号和密码' }, 400, cors);
        }

        const user = await env.DB.prepare('SELECT * FROM users WHERE username = ?').bind(username).first();
        if (!user) {
          await writeAuditLog(env, { username, action: 'login', success: false, detail: '账号不存在', ...meta });
          return jsonResponse({ error: '账号或密码错误' }, 401, cors);
        }

        const ok = await verifyPassword(password, user.password_hash);
        if (!ok) {
          await writeAuditLog(env, {
            username,
            userId: user.id,
            role: user.role,
            action: 'login',
            success: false,
            detail: '密码错误',
            ...meta
          });
          return jsonResponse({ error: '账号或密码错误' }, 401, cors);
        }

        if (!user.is_active) {
          await writeAuditLog(env, {
            username,
            userId: user.id,
            role: user.role,
            action: 'login',
            success: false,
            detail: '账号已被停用',
            ...meta
          });
          return jsonResponse({ error: '该账号已被停用，请联系管理员' }, 403, cors);
        }

        if (isExpired(user.expires_at)) {
          await writeAuditLog(env, {
            username,
            userId: user.id,
            role: user.role,
            action: 'login',
            success: false,
            detail: '账号已过有效期',
            ...meta
          });
          return jsonResponse({ error: '该账号已过期，请联系管理员续期' }, 403, cors);
        }

        if (user.single_session) {
          await env.DB.prepare('DELETE FROM sessions WHERE user_id = ?').bind(user.id).run();
        }

        const token = generateToken();
        const sessionExpires = new Date(Date.now() + SESSION_TTL_HOURS * 3600 * 1000).toISOString();

        await env.DB.prepare(
          `INSERT INTO sessions (token, user_id, expires_at, ip, user_agent) VALUES (?, ?, ?, ?, ?)`
        )
          .bind(token, user.id, sessionExpires, meta.ip, meta.ua)
          .run();

        await env.DB.prepare(`UPDATE users SET last_login_at = datetime('now') WHERE id = ?`)
          .bind(user.id)
          .run();

        await writeAuditLog(env, {
          username: user.username,
          userId: user.id,
          role: user.role,
          action: 'login',
          success: true,
          detail: '登录成功',
          ...meta
        });

        return jsonResponse(
          {
            token,
            expires_at: sessionExpires,
            user: formatUserPublic(user)
          },
          200,
          cors
        );
      }

      // 以下接口均需先校验 Token
      const auth = await authenticateRequest(request, env);

      // 4. 获取当前登录态
      if (path === '/api/me' && request.method === 'GET') {
        if (!auth) {
          return jsonResponse({ error: '未登录或会话已失效' }, 401, cors);
        }
        return jsonResponse({ user: formatUserPublic(auth.user) }, 200, cors);
      }

      // 5. 退出登录
      if (path === '/api/logout' && request.method === 'POST') {
        if (auth) {
          await env.DB.prepare('DELETE FROM sessions WHERE token = ?').bind(auth.token).run();
          await writeAuditLog(env, {
            username: auth.user.username,
            userId: auth.user.id,
            role: auth.user.role,
            action: 'logout',
            success: true,
            detail: '主动退出登录',
            ...meta
          });
        }
        return jsonResponse({ ok: true }, 200, cors);
      }

      // 6. 用户自助修改密码
      if (path === '/api/change-password' && request.method === 'POST') {
        if (!auth) return jsonResponse({ error: '未登录' }, 401, cors);
        const body = await request.json().catch(() => ({}));
        const oldPassword = String(body.old_password || '');
        const newPassword = String(body.new_password || '');
        if (newPassword.length < 6) {
          return jsonResponse({ error: '新密码长度至少 6 位' }, 400, cors);
        }
        const ok = await verifyPassword(oldPassword, auth.user.password_hash);
        if (!ok) {
          return jsonResponse({ error: '原密码不正确' }, 400, cors);
        }
        const newHash = await hashPassword(newPassword);
        await env.DB.prepare(`UPDATE users SET password_hash = ?, updated_at = datetime('now') WHERE id = ?`)
          .bind(newHash, auth.user.id)
          .run();
        await writeAuditLog(env, {
          username: auth.user.username,
          userId: auth.user.id,
          role: auth.user.role,
          action: 'change_password',
          success: true,
          detail: '用户自助修改密码',
          ...meta
        });
        return jsonResponse({ ok: true }, 200, cors);
      }

      // ==================== 管理员专属接口 ====================
      if (path.startsWith('/api/admin/')) {
        if (!auth) return jsonResponse({ error: '未登录或会话已失效' }, 401, cors);
        if (auth.user.role !== 'admin') {
          return jsonResponse({ error: '无管理员权限' }, 403, cors);
        }

        // 7. 用户列表
        if (path === '/api/admin/users' && request.method === 'GET') {
          const rows = await env.DB.prepare(
            `SELECT u.*, (SELECT COUNT(*) FROM sessions s WHERE s.user_id = u.id) AS active_sessions
             FROM users u ORDER BY u.id ASC`
          ).all();
          const users = (rows.results || []).map(u => ({
            ...formatUserPublic(u),
            active_sessions: u.active_sessions || 0
          }));
          return jsonResponse({ users }, 200, cors);
        }

        // 8. 新增用户
        if (path === '/api/admin/users' && request.method === 'POST') {
          const body = await request.json().catch(() => ({}));
          const username = String(body.username || '').trim();
          const displayName = String(body.display_name || username).trim();
          const password = String(body.password || '');
          const role = String(body.role || 'viewer');
          const isActive = body.is_active === false ? 0 : 1;
          const singleSession = body.single_session ? 1 : 0;
          const expiresAt = body.expires_at ? String(body.expires_at).trim() : null;

          if (!username || !/^[a-zA-Z0-9_.-]{2,32}$/.test(username)) {
            return jsonResponse({ error: '账号需为 2~32 位字母/数字/下划线' }, 400, cors);
          }
          if (password.length < 6) {
            return jsonResponse({ error: '密码长度至少 6 位' }, 400, cors);
          }
          if (!VALID_ROLES.has(role)) {
            return jsonResponse({ error: '无效的角色类型' }, 400, cors);
          }

          const exists = await env.DB.prepare('SELECT id FROM users WHERE username = ?').bind(username).first();
          if (exists) {
            return jsonResponse({ error: '该账号已存在' }, 409, cors);
          }

          const pwHash = await hashPassword(password);
          const res = await env.DB.prepare(
            `INSERT INTO users (username, display_name, password_hash, role, is_active, expires_at, single_session)
             VALUES (?, ?, ?, ?, ?, ?, ?)`
          )
            .bind(username, displayName, pwHash, role, isActive, expiresAt, singleSession)
            .run();

          await writeAuditLog(env, {
            username: auth.user.username,
            userId: auth.user.id,
            role: auth.user.role,
            action: 'admin_create_user',
            success: true,
            detail: `创建账号 ${username} (${role})`,
            ...meta
          });

          return jsonResponse({ ok: true, id: res.meta?.last_row_id }, 201, cors);
        }

        // 9. 编辑用户 / 踢下线 / 删除用户
        const userMatch = path.match(/^\/api\/admin\/users\/(\d+)(\/revoke)?$/);
        if (userMatch) {
          const targetId = Number(userMatch[1]);
          const isRevoke = Boolean(userMatch[2]);
          const target = await env.DB.prepare('SELECT * FROM users WHERE id = ?').bind(targetId).first();
          if (!target) return jsonResponse({ error: '用户不存在' }, 404, cors);

          if (isRevoke && request.method === 'POST') {
            await env.DB.prepare('DELETE FROM sessions WHERE user_id = ?').bind(targetId).run();
            await writeAuditLog(env, {
              username: auth.user.username,
              userId: auth.user.id,
              role: auth.user.role,
              action: 'admin_revoke_sessions',
              success: true,
              detail: `强制踢下线 ${target.username}`,
              ...meta
            });
            return jsonResponse({ ok: true }, 200, cors);
          }

          if (request.method === 'PATCH') {
            const body = await request.json().catch(() => ({}));
            const displayName = body.display_name !== undefined ? String(body.display_name).trim() : target.display_name;
            const role = body.role !== undefined ? String(body.role) : target.role;
            const isActive = body.is_active !== undefined ? (body.is_active ? 1 : 0) : target.is_active;
            const singleSession = body.single_session !== undefined ? (body.single_session ? 1 : 0) : target.single_session;
            const expiresAt = body.expires_at !== undefined ? (body.expires_at ? String(body.expires_at).trim() : null) : target.expires_at;

            if (!VALID_ROLES.has(role)) {
              return jsonResponse({ error: '无效的角色类型' }, 400, cors);
            }
            if (targetId === auth.user.id && (!isActive || role !== 'admin')) {
              return jsonResponse({ error: '不能禁用或降级当前正在使用的管理员账号' }, 400, cors);
            }

            let pwHash = target.password_hash;
            if (body.password && String(body.password).length > 0) {
              if (String(body.password).length < 6) {
                return jsonResponse({ error: '新密码长度至少 6 位' }, 400, cors);
              }
              pwHash = await hashPassword(String(body.password));
            }

            await env.DB.prepare(
              `UPDATE users
               SET display_name = ?, password_hash = ?, role = ?, is_active = ?, expires_at = ?, single_session = ?, updated_at = datetime('now')
               WHERE id = ?`
            )
              .bind(displayName, pwHash, role, isActive, expiresAt, singleSession, targetId)
              .run();

            if (!isActive) {
              await env.DB.prepare('DELETE FROM sessions WHERE user_id = ?').bind(targetId).run();
            }

            await writeAuditLog(env, {
              username: auth.user.username,
              userId: auth.user.id,
              role: auth.user.role,
              action: 'admin_update_user',
              success: true,
              detail: `更新账号 ${target.username}`,
              ...meta
            });

            return jsonResponse({ ok: true }, 200, cors);
          }

          if (request.method === 'DELETE') {
            if (targetId === auth.user.id) {
              return jsonResponse({ error: '不能删除当前正在登录的管理员账号' }, 400, cors);
            }
            await env.DB.prepare('DELETE FROM sessions WHERE user_id = ?').bind(targetId).run();
            await env.DB.prepare('DELETE FROM users WHERE id = ?').bind(targetId).run();
            await writeAuditLog(env, {
              username: auth.user.username,
              userId: auth.user.id,
              role: auth.user.role,
              action: 'admin_delete_user',
              success: true,
              detail: `删除账号 ${target.username}`,
              ...meta
            });
            return jsonResponse({ ok: true }, 200, cors);
          }
        }

        // 10. 登录审计日志
        if (path === '/api/admin/logs' && request.method === 'GET') {
          const limit = Math.min(Number(url.searchParams.get('limit') || 100), 300);
          const rows = await env.DB.prepare(
            `SELECT id, username, role, action, success, detail, ip, user_agent, created_at
             FROM audit_logs ORDER BY id DESC LIMIT ?`
          )
            .bind(limit)
            .all();
          return jsonResponse({ logs: rows.results || [] }, 200, cors);
        }
      }

      return jsonResponse({ error: 'Not Found' }, 404, cors);
    } catch (err) {
      console.error('Worker unhandled error:', err);
      return jsonResponse({ error: '服务器内部错误', detail: err.message }, 500, cors);
    }
  }
};
