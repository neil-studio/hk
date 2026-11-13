#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "1️⃣ 检查 Cloudflare 登录状态..."
npx wrangler whoami || {
  echo "请先在浏览器完成 Cloudflare 授权登录："
  npx wrangler login
}

echo "2️⃣ 创建 D1 数据库 (如已存在可忽略错误)..."
npx wrangler d1 create hk_property_auth_db || true

echo "⚠️ 请确认 wrangler.toml 中的 database_id 已填入上方输出的 UUID！"
echo "3️⃣ 初始化 D1 数据表结构..."
npx wrangler d1 execute hk_property_auth_db --config ./wrangler.toml --remote --yes --file=./schema.sql

echo "4️⃣ 部署 Cloudflare Worker..."
npx wrangler deploy --config ./wrangler.toml

echo "✅ 部署完成！请将上方输出的 https://hk-property-auth.<你的子域>.workers.dev 地址更新到 ../auth.js 的 apiBase 中。"
