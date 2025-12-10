# PMS API 測試客戶端使用說明

## 🎯 用途

此腳本用於在 Mac 本機測試 Windows Server (192.168.8.3) 上部署的 PMS API。

## 📋 前置條件

1. Windows Server 上的 PMS API 已部署並運行
2. 防火牆已開放 Port 3000
3. Mac 可以連線到內網 192.168.8.3

## 🚀 使用方式

### 方式一：直接執行

```bash
cd /Users/ktw/KTW-bot/pms-api-poc
python3 test-api-client.py
```

### 方式二：使用執行權限

```bash
./test-api-client.py
```

## 🧪 測試項目

腳本會自動執行以下測試：

1. **API 連線測試**
   - 檢查 Windows Server 上的 API 是否可連線
   - 驗證網路暢通

2. **訂單查詢測試**
   - 測試查詢特定訂單（預設：00150501）
   - 驗證資料格式
   - 確認無幻覺問題

3. **訂單搜尋測試** (選填)
   - 測試依姓名或電話搜尋
   - 驗證搜尋功能

4. **BOT 整合測試**
   - 模擬 LINE BOT 的查詢流程
   - 生成 BOT 回應預覽
   - 驗證整合可行性

## 📊 預期結果

```
====================================================
測試總結
====================================================
API 連線: ✅ 通過
查詢訂單: ✅ 通過
BOT 整合: ✅ 通過

總計: 3/3 項測試通過

🎉 所有測試通過！PMS API 運作正常。
```

## ⚙️ 設定選項

### 修改 API 位址

編輯 `test-api-client.py`，修改第 13 行：

```python
# 預設
PMS_API_URL = "http://192.168.8.3:3000/api"

# 如果使用不同 IP 或 Port
PMS_API_URL = "http://your-ip:your-port/api"
```

### 修改測試訂單號

編輯 main() 函數中的訂單號：

```python
# 第 224 行
results.append(("查詢訂單", test_query_booking("your-order-id")))
```

## ❌ 常見問題

### 問題 1：無法連線到 API

```
❌ 無法連線到 API
   請確認:
   1. Windows Server (192.168.8.3) 上的 API 是否正在運行
   2. 防火牆是否開放 Port 3000
   3. 網路是否可連通
```

**解決方法**：

1. 確認 Windows Server 上 API 正在運行：
   ```powershell
   # 在 Windows Server 上執行
   netstat -ano | findstr :3000
   ```

2. 測試網路連通性：
   ```bash
   # 在 Mac 上執行
   ping 192.168.8.3
   telnet 192.168.8.3 3000
   ```

3. 檢查防火牆：
   ```powershell
   # 在 Windows Server 上執行
   Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*PMS*"}
   ```

### 問題 2：找不到訂單

```
❌ 找不到訂單 00150501
```

**解決方法**：
- 修改測試腳本使用實際存在的訂單號
- 或在 Oracle 資料庫中確認訂單是否存在

### 問題 3：API 回應格式錯誤

**解決方法**：
- 確認 Windows Server 上的 API 實作符合規格
- 參考 `docs/pms_api_specification.md`

## 📝 下一步

**測試成功後**：

1. **整合到 LINE BOT**
   ```python
   # 修改 bot.py
   def check_order_status(self, order_id):
       response = requests.get(
           f"http://192.168.8.3:3000/api/bookings/{order_id}"
       )
       return response.json()
   ```

2. **移除 Gmail API**
   - 刪除 `gmail_helper.py`
   - 更新 `requirements.txt`

3. **完整測試**
   - 測試 LINE BOT 訂單查詢
   - 驗證資料準確性
   - 確認無幻覺問題

## 🔗 相關文件

- [PMS API 規格](../docs/pms_api_specification.md)
- [Windows Server 部署指南](DEPLOY_WINDOWS.md)
- [安全設定指南](WINDOWS_SECURITY.md)
