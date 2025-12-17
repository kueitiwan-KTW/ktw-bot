# Helpers 模組

> LINE Bot 外部服務整合

## 📋 模組說明

此資料夾包含所有外部 API 整合和輔助功能。

## 📂 檔案結構

| 檔案 | 說明 |
|:---|:---|
| `google_services.py` | Google API 服務（認證、驅動） |
| `gmail_helper.py` | Gmail 訂單郵件查詢 |
| `pms_client.py` | PMS REST API 客戶端 |
| `weather_helper.py` | 天氣查詢（中央氣象署） |

## 🔗 服務對照

| Helper | 外部 API | 用途 |
|:---|:---|:---|
| `GoogleServices` | Google OAuth | 服務認證 |
| `GmailHelper` | Gmail API | 搜尋訂單郵件 |
| `PMSClient` | PMS REST API | 訂單查詢、房況查詢 |
| `WeatherHelper` | 中央氣象署 API | 天氣預報 |

## 🔧 使用方式

```python
from helpers import (
    GoogleServices,
    GmailHelper,
    PMSClient,
    WeatherHelper
)

# 初始化
google_services = GoogleServices()
gmail_helper = GmailHelper(google_services)
pms_client = PMSClient()
weather_helper = WeatherHelper()
```

## ⚙️ 環境變數

```env
# PMS API
PMS_API_BASE_URL=http://192.168.8.3:3000/api
PMS_API_TIMEOUT=5
PMS_API_ENABLED=True
```

---

*最後更新：2025-12-17*
