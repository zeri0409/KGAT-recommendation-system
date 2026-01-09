# Vue开发服务器启动脚本（适配Node.js 17+）
# 解决 OpenSSL 兼容性问题

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Vue开发服务器启动脚本" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 设置环境变量解决Node.js 17+的OpenSSL兼容性问题
$env:NODE_OPTIONS="--openssl-legacy-provider"

Write-Host "已设置 NODE_OPTIONS=--openssl-legacy-provider" -ForegroundColor Yellow
Write-Host "正在启动开发服务器..." -ForegroundColor Green
Write-Host ""

# 启动开发服务器
npm run serve

