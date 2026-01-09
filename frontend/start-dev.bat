@echo off
REM Vue开发服务器启动脚本（适配Node.js 17+）
REM 解决 OpenSSL 兼容性问题

echo ========================================
echo Vue开发服务器启动脚本
echo ========================================
echo.

REM 设置环境变量解决Node.js 17+的OpenSSL兼容性问题
set NODE_OPTIONS=--openssl-legacy-provider

echo 已设置 NODE_OPTIONS=--openssl-legacy-provider
echo 正在启动开发服务器...
echo.

REM 启动开发服务器
npm run serve

