## 📦 PMS 整合功能（開發中）

本專案正在整合德安資訊 PMS 系統，將訂房資料直接從 Oracle 資料庫查詢。

### � 開發規範

- [標準作業程序 (SOP)](docs/DEVELOPMENT_SOP.md) - **開發前必讀**
- [PMS 整合總覽](docs/PMS_INTEGRATION_SUMMARY.md)
- [REST API 規格](pms-api/pms_api_specification.md)
- [資料庫結構參考](pms-api/PMS-DATABASE-REFERENCE.md)
- [整合方案](docs/bot_pms_integration_plan.md)

### 專案結構
```
pms-api/           # PMS REST API（Node.js + Express + Oracle）
admin-dashboard/   # 管理後台（Next.js + React + TypeScript）
docs/              # 完整技術文件
```
