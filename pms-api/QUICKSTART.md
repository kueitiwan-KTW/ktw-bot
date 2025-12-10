# PMS API 快速部署指南

## 🎯 目标
在 Windows Server (192.168.8.3) 上部署 PMS REST API

## ✅ 前置条件
- Node.js v20.10.0 已安装
- Oracle Database 正在运行
- pms_api 账号已创建并授权

## 📦 部署步骤

### 1. 复制档案到 Windows Server
将 `pms-api` 资料夹复制到 `C:\KTW-bot\pms-api`

### 2. 执行部署脚本
```powershell
cd C:\KTW-bot\pms-api
.\deploy-windows.bat
```

脚本会自动:
- ✓ 检查 Node.js
- ✓ 安装 npm 套件
- ✓ 配置环境变数
- ✓ 启动测试

### 3. 验证部署
开启浏览器测试:
```
http://localhost:3000/api/health
```

应该看到:
```json
{
  "status": "ok",
  "timestamp": "...",
  "service": "PMS API"
}
```

## 🧪 测试 API

### 从 Mac 测试
```bash
# 健康检查
curl http://192.168.8.3:3000/api/health

# 查询订单
curl "http://192.168.8.3:3000/api/bookings/search?name=booking"

# 订单详情
curl http://192.168.8.3:3000/api/bookings/00039201
```

### 从 Windows 测试
```powershell
# 使用 PowerShell
Invoke-WebRequest http://localhost:3000/api/health
```

## 🔧 常见问题

### 问题 1：端口被占用
```
Error: listen EADDRINUSE: address already in use :::3000
```

**解决**: 修改 `.env` 中的 `PORT=3001`

### 问题 2：Oracle Client 初始化失败
```
Oracle Client 初始化失敗
```

**解决**: 检查 `.env` 中的路径:
```
ORACLE_CLIENT_LIB_DIR=D:\\app\\product\\12.2.0\\dbhome_1\\bin
```

### 问题 3：连接被拒绝（从 Mac 测试时）
**解决**: 确认防火牆已開放 Port 3000

## 📝 下一步
部署成功后即可整合到 LINE Bot！
