# 如何將 PMS 整合套件加入 KTW-bot Repository

## 📦 準備工作

**您需要複製的所有文件**（共 11 個）：

所有文件目前位於：
```
/Users/ktw/.gemini/antigravity/brain/4673da49-130a-4d10-bbd1-466a008cfa73/
```

---

## 📋 檔案清單與用途

| 檔案名稱 | 用途 | 目標位置 |
|---------|------|---------|
| `PMS_INTEGRATION_SUMMARY.md` | **總覽文件**（最重要） | `KTW-bot/docs/` |
| `pms_api_specification.md` | REST API 完整規格 | `KTW-bot/docs/` |
| `pms_database_structure.md` | 資料庫結構分析 | `KTW-bot/docs/` |
| `bot_pms_integration_plan.md` | BOT 整合方案 | `KTW-bot/docs/` |
| `task.md` | 任務清單 | `KTW-bot/docs/` |
| `implementation_plan.md` | 實作計畫 | `KTW-bot/docs/` |
| `oracle_access_guide.md` | Oracle 連線指南 | `KTW-bot/docs/oracle/` |
| `oracle_connection_steps.md` | 連線步驟 | `KTW-bot/docs/oracle/` |
| `oracle_sql_commands.md` | SQL 指令集 | `KTW-bot/docs/oracle/` |
| `pms_data_access_plan.md` | 資料存取計畫 | `KTW-bot/docs/` |
| `oracle_info_collector.bat` | 資訊收集工具 | `KTW-bot/tools/` |

---

## 🚀 整合步驟

### 方法 A：在 KTW-bot 建立新分支（建議）

#### 1. Clone KTW-bot repository（如果還沒 clone）

```bash
cd ~/Projects  # 或您習慣的專案目錄
git clone https://github.com/kueitiwan-KTW/KTW-bot.git
cd KTW-bot
```

#### 2. 建立新分支 `pms-integration`

```bash
git checkout main
git pull origin main
git checkout -b pms-integration
```

#### 3. 建立目錄結構

```bash
# 建立文件目錄
mkdir -p docs/oracle
mkdir -p tools

# 將來會用到的目錄
mkdir -p pms-api
mkdir -p admin-dashboard
```

#### 4. 複製所有文件

**在 macOS 上執行**：

```bash
# 複製主要文件到 docs/
cp /Users/ktw/.gemini/antigravity/brain/4673da49-130a-4d10-bbd1-466a008cfa73/PMS_INTEGRATION_SUMMARY.md docs/
cp /Users/ktw/.gemini/antigravity/brain/4673da49-130a-4d10-bbd1-466a008cfa73/pms_api_specification.md docs/
cp /Users/ktw/.gemini/antigravity/brain/4673da49-130a-4d10-bbd1-466a008cfa73/pms_database_structure.md docs/
cp /Users/ktw/.gemini/antigravity/brain/4673da49-130a-4d10-bbd1-466a008cfa73/bot_pms_integration_plan.md docs/
cp /Users/ktw/.gemini/antigravity/brain/4673da49-130a-4d10-bbd1-466a008cfa73/task.md docs/
cp /Users/ktw/.gemini/antigravity/brain/4673da49-130a-4d10-bbd1-466a008cfa73/implementation_plan.md docs/
cp /Users/ktw/.gemini/antigravity/brain/4673da49-130a-4d10-bbd1-466a008cfa73/pms_data_access_plan.md docs/

# 複製 Oracle 相關文件到 docs/oracle/
cp /Users/ktw/.gemini/antigravity/brain/4673da49-130a-4d10-bbd1-466a008cfa73/oracle_access_guide.md docs/oracle/
cp /Users/ktw/.gemini/antigravity/brain/4673da49-130a-4d10-bbd1-466a008cfa73/oracle_connection_steps.md docs/oracle/
cp /Users/ktw/.gemini/antigravity/brain/4673da49-130a-4d10-bbd1-466a008cfa73/oracle_sql_commands.md docs/oracle/

# 複製工具到 tools/
cp /Users/ktw/.gemini/antigravity/brain/4673da49-130a-4d10-bbd1-466a008cfa73/oracle_info_collector.bat tools/
```

#### 5. 提交變更

```bash
git add .
git commit -m "feat: 新增 PMS 整合套件文件

- 新增 Oracle 資料庫連線與探索文件
- 新增 REST API 完整規格
- 新增 BOT 整合方案與架構設計
- 新增專案任務清單與實作計畫"

git push origin pms-integration
```

#### 6. 在 GitHub 建立 Pull Request

1. 開啟 https://github.com/kueitiwan-KTW/KTW-bot
2. 點選 "Pull requests" → "New pull request"
3. Base: `main` ← Compare: `pms-integration`
4. 建立 PR，標題：`[Feature] PMS 整合套件 - Oracle 資料庫與 REST API 規格`

---

### 方法 B：直接在 main 分支操作（不建議）

```bash
cd KTW-bot
git checkout main
git pull origin main

# 建立目錄與複製文件（同方法 A 的步驟 3-4）
# ...

git add .
git commit -m "feat: 新增 PMS 整合套件文件"
git push origin main
```

---

## 📁 最終的 KTW-bot 目錄結構

```
KTW-bot/
├── docs/                                    ← 新增
│   ├── PMS_INTEGRATION_SUMMARY.md          ← 從這份開始看
│   ├── pms_api_specification.md
│   ├── pms_database_structure.md
│   ├── bot_pms_integration_plan.md
│   ├── task.md
│   ├── implementation_plan.md
│   ├── pms_data_access_plan.md
│   └── oracle/
│       ├── oracle_access_guide.md
│       ├── oracle_connection_steps.md
│       └── oracle_sql_commands.md
├── tools/                                   ← 新增
│   └── oracle_info_collector.bat
├── pms-api/                                 ← 未來建立（Node.js API）
├── admin-dashboard/                         ← 未來建立（Next.js 後台）
├── bot.py                                   ← 現有（將修改）
├── app.py                                   ← 現有
└── README.md                                ← 建議更新
```

---

## 📝 更新 README.md（建議）

在 `KTW-bot/README.md` 加入：

```markdown
## 📦 PMS 整合功能（開發中）

本專案正在整合德安資訊 PMS 系統，將訂房資料直接從 Oracle 資料庫查詢。

### 相關文件
- [PMS 整合總覽](docs/PMS_INTEGRATION_SUMMARY.md) - **從這裡開始**
- [REST API 規格](docs/pms_api_specification.md)
- [資料庫結構](docs/pms_database_structure.md)
- [整合方案](docs/bot_pms_integration_plan.md)

### 專案結構
```
pms-api/           # PMS REST API（Node.js + Express + Oracle）
admin-dashboard/   # 管理後台（Next.js + React + TypeScript）
docs/              # 完整技術文件
```
```

---

## ✅ 檢查清單

完成後請確認：

- [ ] 所有 11 個文件已複製到 KTW-bot
- [ ] 目錄結構正確（docs/, docs/oracle/, tools/）
- [ ] 已建立 Git 分支 `pms-integration`
- [ ] 已提交變更並 push 到 GitHub
- [ ] 已建立 Pull Request（如果使用分支）
- [ ] README.md 已更新（建議）

---

## 🎯 下一步行動

文件整合完成後，即可開始：

1. **建立 PMS API 專案**（參考 `docs/pms_api_specification.md`）
2. **調整 LINE BOT**（參考 `docs/bot_pms_integration_plan.md`）
3. **建立 Next.js 後台**（參考 `docs/PMS_INTEGRATION_SUMMARY.md`）

---

**完成時間**：約 10-15 分鐘  
**建議閱讀順序**：
1. `PMS_INTEGRATION_SUMMARY.md`（總覽）
2. `pms_api_specification.md`（API 規格）
3. `bot_pms_integration_plan.md`（整合方案）
