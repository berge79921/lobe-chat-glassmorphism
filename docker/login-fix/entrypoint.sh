#!/bin/sh
set -e

cd /app

if [ ! -f node_modules/imapflow/package.json ] || [ ! -f node_modules/nodemailer/package.json ] || [ ! -f node_modules/mailparser/package.json ]; then
  echo "[entrypoint] Installing login-proxy npm dependencies..."
  npm install --omit=dev --prefer-offline 2>&1
  echo "[entrypoint] npm install complete."
else
  echo "[entrypoint] node_modules up to date, skipping install."
fi

exec node server.js
