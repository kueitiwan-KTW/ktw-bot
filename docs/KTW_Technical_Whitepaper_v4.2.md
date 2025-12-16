# KTW 飯店系統轉型技術白皮書 v4.2 (Converted)

> Auto-converted from .docx. Formatting may be simplified.

KTW 飯店系統轉型技術白皮書

v4.2（Consolidated Final）

文件用途

系統轉型架構決策、落地規格、執行路徑與維運 Runbook

核心策略

雙核心驅動（Python AI Core + Node.js IO Core）/ 漸進式遷移 / PostgreSQL 作為數據終局

最新納入

Windows vs Linux 選型、Synology 異地備份、UniFi VPN、LINE 加好友開通 Wi-Fi（Captive Portal）

文件日期

2025-12-13

# 版本與變更記錄

本文件以你提供的 v4.0 原文為基礎，並在不刪除任何原文內容的前提下，合併先前討論的決策與新增需求（備份/DR、作業系統選型、UniFi VPN、LINE 加好友開通 Wi-Fi）。

v4.0：你提供的 Final Technical White Paper 原文（完整保留）。

v4.1：補強基礎設施策略（本地為主 + 異地備份/DR）、NAS 定案 Synology、Windows vs Linux 優劣與遷移路線、UniFi VPN Runbook。

v4.2：新增『客人必須加入官方 LINE 才能開通免費 Wi-Fi』，採 UniFi Hotspot + External Portal + LINE Login + Friendship Status + UniFi Network API 放行。

# 目錄

Part I － v4.0 原文（完整保留）

Part II － v4.1/v4.2 新增章節與建議（不影響原文）

附錄 A － 異地備份 Runbook（Windows + UniFi VPN + Synology）

附錄 B － LINE 加好友開通 Wi-Fi Runbook（UniFi Hotspot + External Portal）

參考資料（References）

# Part I － v4.0 原文（完整保留）

以下內容為你提供之白皮書 v4.0 原文，僅做版面排版與章節結構化呈現；不刪除原文資訊。

## 📖 1. 執行摘要 (Executive Summary)

本白皮書融合了架構演進分析 (v3.0) 與詳細技術規格 (v2.0/2.1)，旨在規劃 KTW 飯店從傳統封閉式系統（德安 Oracle）轉型為 自主可控、數據驅動 的現代化飯店生態系。

核心策略為「雙核心驅動、漸進式遷移」：

## 🏗️ 2. 架構演進與決策分析 (Architectural Evolution)

我們經過多次架構評估，最終確立了「模組化單體 (Modular Monolith) 邁向 微服務 (Microservices)」的演進路線。

2.1 決策歷程深度剖析

最終選擇：改良版微服務架構 (Evolutionary Architecture)

2.2 雙核心戰略 (Dual-Core Strategy)

## 🖥️ 3. 前端生態系詳解 (Frontend Ecosystem)

我們採用 Vue.js 3 作為統一的前端技術棧，針對不同場景封裝為 Web App 與 Desktop App。

3.1 🏨 櫃台管理後台 (Staff Portal)

3.2 🤖 自助入住機 (Guest Kiosk)

## 💾 4. 資料庫詳細設計 (Database Schema)

我們選擇 PostgreSQL 16+ 作為核心，並利用 Schema 進行業務隔離。

4.1 核心表結構 (Core Schema)

customers 表：

CREATE TABLE customers (

    id SERIAL PRIMARY KEY,

    line_user_id VARCHAR(50) UNIQUE,  -- 關聯 LINE Bot

    name VARCHAR(100),

    passport_number VARCHAR(50),      -- 加密儲存

    phone VARCHAR(20),

    email VARCHAR(100),

    vip_level INTEGER DEFAULT 0,      -- VIP 等級

    points INTEGER DEFAULT 0,         -- 會員點數

    tags JSONB,                       -- 標籤 (e.g. ["喜歡高樓層", "素食"])

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);

📅 訂單主檔 (Bookings) —— 初期同步德安，後期接手 GoBooking

CREATE TABLE bookings (

    id SERIAL PRIMARY KEY,

    booking_ref VARCHAR(50) UNIQUE,   -- 訂單編號

    source_system VARCHAR(20),        -- 'ORACLE', 'GOBOOKING', 'KIOSK'

    customer_id INTEGER REFERENCES customers(id),

    room_number VARCHAR(10),

    check_in_date DATE,

    check_out_date DATE,

    status VARCHAR(20),               -- 'CONFIRMED', 'CHECKED_IN', 'CANCELLED'

    total_amount DECIMAL(10,2),

    raw_payload JSONB,                -- 儲存原始訂單 JSON (API 來源)

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);

🛍️ 商品與庫存 (Products & Inventory) —— POS 系統核心

CREATE TABLE products (

    id SERIAL PRIMARY KEY,

    barcode VARCHAR(50) UNIQUE,

    name VARCHAR(100),

    price DECIMAL(10,2),

    cost DECIMAL(10,2),

    stock_quantity INTEGER,           -- 當前庫存

    category_id INTEGER,

    is_active BOOLEAN DEFAULT TRUE

);

💰 交易與發票 (Transactions) —— 帳務系統核心

CREATE TABLE transactions (

    id SERIAL PRIMARY KEY,

    booking_id INTEGER REFERENCES bookings(id),

    amount DECIMAL(10,2),

    type VARCHAR(20),       -- 'PAYMENT', 'REFUND', 'DEPOSIT'

    method VARCHAR(20),     -- 'CASH', 'CREDIT_CARD', 'LINE_PAY'

    invoice_number VARCHAR(20), -- 發票號碼

    carrier_id VARCHAR(50),     -- 手機載具

    raw_response JSONB,         -- 刷卡機回傳原始資料

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);

4.2 日誌表結構 (Log Schema)

📟 硬體操作日誌 (Hardware Logs) —— 完整的安全審計軌跡

CREATE TABLE hardware_logs (

    id SERIAL PRIMARY KEY,

    device_type VARCHAR(20),          -- 'LOCK', 'ROOM_SIGNAL', 'POS', 'KIOSK'

    device_id VARCHAR(50),            -- 設備編號/房號

    action_type VARCHAR(50),          -- 'ISSUE_CARD', 'DOOR_OPEN', 'SOS_ALERT'

    payload JSONB,                    -- 詳細數據 (卡號、錯誤碼)

    performed_by VARCHAR(50),         -- 操作者 (System / Staff ID)

    ip_address VARCHAR(45),

    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);

### 4.3 PostgreSQL vs Oracle 深度技術評估

特性

Oracle (舊德安)

PostgreSQL (新核心)

獲勝關鍵

並發模型

Process-based

Process-based

平手 (皆具備高穩定性)

JSON 支援

支援 (BLOB)

JSONB (Binary)

PG 勝 (可建立索引，適合 API 資料)

地理資訊

Oracle Spatial (付費)

PostGIS (免費)

PG 勝 (未來可做周邊景點地圖)

擴充性

封閉 Plugin

FDW (Foreign Data Wrapper)

PG 勝 (可直接 Mount Oracle 資料表)

持有成本

極高 (授權+維護)

極低 (開源)

PG 勝

## 🔌 5. 硬體驅動與協定 (Hardware Protocols)

### 5.1 Waferlock 門鎖

介面：USB / DLL SDK

控制層：Node.js ffi-napi

關鍵函數：

int IssueCard(int room, char* expire): 發卡

int ReadCard(char* outBuffer): 讀卡

int EraseCard(): 清除卡片

### 5.2 MINXON 房況訊號

介面：RS-485 / Modbus RTU (模擬)

控制層：Node.js serialport

協議範例：

查詢指令: [0x01] [0x03] [0x00] [0x64] [CRC] (讀取 100號房)

狀態回傳: [0x01] [0x03] [0x02] [STATUS_BYTE] [CRC]

STATUS_BYTE Bitmask:

Bit 0: 插卡 (Power)

Bit 1: 勿擾 (DND)

Bit 2: 打掃 (Clean)

Bit 3: SOS

### 5.4 NEC SL2100 交換機 (PBX)

介面：Ethernet (LAN) / CTI (TAPI 2.1) / SIP Trunk

控制層：Node.js net 模組 (TCP Socket) 或 3rd party TAPI wrapper。

整合功能：

計費 (Call Accounting)：接收 SMDR 字串，解析通話時間與費用，自動寫入訂單帳務。

晨喚 (Wake-up Call)：由 Bot 設定時間，系統自動透過 CTI 指令設定房間分機 Morning Call。

[NEW] AI 語音智能客服 (Voice AI)：

架構：NEC SL2100 (SIP Trunk) <--> VoIP Gateway (Asterisk/FreeSWITCH) <--> Node.js Media Server <--> Python AI Core

流程：

進線：外部來電 -> NEC -> 轉接 SIP 分機 (AI Gateway)。

聽 (STT)：Node.js 接收 RTP 音訊流 -> Python (Whisper) 轉文字。

想 (LLM)：文字 -> Gemini Agent 生成回應。

說 (TTS)：回應文字 -> Python (Google TTS) 轉語音 -> Node.js 串流回傳 -> NEC -> 客人聽到聲音。

場景：房客撥打 "9" (總機) 時，若忙線中自動轉接 AI，處理 "請問早餐時間"、"幫我多送兩瓶水" 等語音需求。

房務碼 (Housekeeping Codes)：清潔人員透過話機輸入代碼 (如 *123#)，系統即時更新房況為「已打掃」。

### 5.5 Unifi 全館網路與監控

介面：Unifi Controller API (REST/Websocket)

整合功能：

Wi-Fi 密碼：Check-in 時自動生成專屬 Wi-Fi 密碼 (Voucher)，Check-out 自動失效。

監視器快照：當房況訊號觸發「SOS」或「門鎖異常開啟」時，後台自動彈出該樓層走道監視器畫面 (UniFi Protect)。

### 5.6 錄音監控系統

介面：Audio Stream / File Access

整合策略：背景服務定期將錄音檔 (依時間/櫃台分機號) 歸檔至 PostgreSQL (透過 Blob 或 檔案路徑)。

爭議查詢：在後台訂單頁面，可直接調閱該時段的櫃台通話錄音。

## 📂 6. 專案目錄結構 (Project Structure)

kueitiwan-KTW/

├── KTW-bot/                  # [Python] LINE Bot (AI Core)

│   ├── app.py

│   └── bot.py

│

├── KTW-backend/              # [Node.js] IO Core & API Gateway

│   ├── src/

│   │   ├── drivers/          # 硬體驅動 (HAL)

│   │   │   ├── waferlock.js  # 門卡 DLL 封裝

│   │   │   ├── minxon.js     # RS-485 協議解析

│   │   │   ├── castles.js    # 刷卡機 ECR 協議

│   │   │   ├── nec_pbx.js    # [NEW] SMDR 計費解析

│   │   │   └── unifi.js      # [NEW] Network/Protect API

│   │   ├── database/         # PostgreSQL 連線

│   │   ├── api/              # REST API Endpoints

│   │   └── jobs/             # Oracle Sync Jobs

│   └── package.json

│

├── KTW-admin-web/            # [Vue.js] 櫃台管理後台

│   ├── src/

│   │   ├── components/       # UI (RoomCard, BookingGrid)

│   │   └── stores/           # Pinia

│   └── package.json

│

├── KTW-guest-kiosk/          # [Electron] 自助入住機 APP

│   ├── src/

│   │   ├── main.js           # 主進程

│   │   └── renderer/         # 前端畫面

│   └── package.json

│

└── docker-compose.yml        # 服務編排

## 🗓️ 7. 遷移執行路徑 (Execution Roadmap) - Updated

因應「優先看到後台框架」的需求，我們調整了執行順序：

### Phase 1: 基礎建設與後台雛形 (Foundation & Prototype) - [第 1-2 個月]

目標：讓您看到東西、摸到介面，同時建立資料庫地基。

環境地基：安裝 Docker, PostgreSQL 16, Node.js 20 環境；建立 kueitiwan-KTW 專案目錄結構。

後台框架 (Vue.js)：初始化 KTW-admin-web (Vite + Vue3)；架設 UI 骨架：登入頁、側邊選單(導覽列)、儀表板空殼。

效果：可以打開瀏覽器看到後台畫面（即使數據是假的）。

資料庫 (PostgreSQL)：建立 customers 與 bookings 資料表。

### Phase 2: 連接神經網絡 (Connectivity) - [第 3-5 個月]

目標：讓後台不再是空殼，而是能動的。

Node.js API 開發：寫出第一支 API，讓後台能讀取真實的資料庫數據。

硬體接駁 (RS-485/USB)：寫出 Minxon 解碼器，讓後台的房況燈號能跟著真實硬體跳動；測試 Waferlock 發卡功能。

### Phase 3: 應用深化 (Deep Dive) - [第 5-8 個月]

自助機 (Kiosk) 原型：開發 Electron App。

NEC 電話整合：實作 CTI/SIP 串接。

### Phase 4: 生態切換 (Switch) - [第 8-12 個月]

全面介接：GoBooking/SiteMinder 上線。

Oracle 退役。

# Part II － v4.1/v4.2 新增章節與建議（不影響原文）

## 8. 運行環境與基礎設施策略（新增）

### 8.1 現況與容量假設（依現場資訊）

櫃檯同時使用者：2–3 個櫃檯畫面。

業務量：每日約 50 筆入住/訂單；尖峰最多連續 2–3 天。

網路：一般網路（非專線），並規劃使用 UniFi VPN 做遠端維運與異地備份通道。

### 8.2 本地為主 vs 雲託管資料庫：決策結論

在 2–3 櫃檯 + 50 筆/日的工作量下，建議採「本地為主（Primary On-Prem）」以降低對外網的依賴與避免斷網造成前台停擺；同時以「異地 NAS 備份」滿足災難復原需求。雲端資料庫可作為第二階段選項，但非必需。

本地為主（建議）：櫃檯與房控等關鍵路徑不受外網品質影響；延遲最低；現場故障排除更直覺。

雲託管 DB（可選）：異地可用性與平台代管便利性提升，但對外網可用性高度敏感，且 VPN/零信任與資安管控成本上升。

結論：本案優先本地；以備份/快照/異地複寫補足風險。

### 8.3 RAID 與備份的邊界

RAID 主要用於降低單顆硬碟故障造成的中斷風險，但無法處理誤刪、勒索、應用邏輯錯誤、或整機毀損等情境；因此仍必須有獨立的備份與保留策略。

### 8.4 Windows vs Linux：選型對照（新增）

本案現場既有伺服器為 Windows Server 2016 64-bit；若要最小化導入風險，Phase 1–2 建議先沿用 Windows 生態。

注意：Microsoft 已公告 Windows Server 2016 支援將於 2027 年 1 月終止，建議評估升級至較新版本（例如 Server 2022/2025）以維持安全更新。 [R10]

面向

Windows（推薦做為 Phase 1–2 起跑）

Linux（推薦做為 Phase 3+ 優化或新環境）

現場維運/人才

多數飯店/中小企業 IT 熟悉；AD、RDP、事件檢視器等工具完整。

需具備 Linux 維運能力；需要標準化（Ansible、systemd、journald）。

硬體驅動/周邊

部分 SDK/DLL（例如票據、掃描器、部分設備）較常見於 Windows。

硬體驅動彈性高，但遇到 Windows-only SDK 時需要替代方案或額外封裝。

Docker/服務治理

可行，但需控管更新與權限模型；建議以 WS2022+ 搭配 Docker Desktop/WSL2 或原生引擎規劃。

容器生態成熟、資源利用率高，CI/CD 友善，適合長期擴展。

安全性基線

需建立 Patch/AV/權限/稽核；建議分層帳號與服務帳號。

最小化安裝、SELinux/AppArmor、iptables/nftables 等可精細化。

成本

OS 授權與 CAL 成本較高。

OS 本體成本低；主要成本在人才與維運。

### 8.5 既有伺服器規格與升級建議（新增）

你目前伺服器：Windows Server 2016 / Intel Xeon E3-1240 v6 / RAM 8GB。

短期（不換機）最低建議：RAM 升級到 32GB（建議 ECC）、系統碟與資料碟改用 SSD（至少資料碟 SSD），並確保有獨立備份。

中期（建議換機）：選擇入門塔式伺服器（含遠端管理功能更佳），並以 64–128GB RAM 規劃三年成長空間。

推薦機型（範例，供採購比對；實際以當地供貨/維保為準）：

Dell PowerEdge T350：支援 Intel Xeon E-2300，最高可到 128GB DDR4（32GB UDIMM x4）。 [R11]

HPE ProLiant ML30 Gen11：最高可到 128GB DDR5 ECC UDIMM。 [R12]

Lenovo ThinkSystem ST50 V3：支援 Xeon E-2400/6300，最高可到 128GB，並具 XClarity 管理能力。 [R13]

### 8.6 NAS 定案：Synology（異地備份目的地）

本案 NAS 定案使用 Synology。備份策略建議採：每日備份檔落地 + NAS 快照（含不可變快照/WORM）+ 異地放置。Synology 不可變快照以 WORM 技術確保在保護期內不可刪改，官方並建議保護期 7–14 天。 [R8]

## 9. 網路與遠端維運（新增）

### 9.1 UniFi VPN：站點對站點（Site Magic SD-WAN）

你規劃以 UniFi 做 VPN，建議優先採 Site Magic 以降低手動設定成本並提升可維護性（支援 Hub-and-Spoke 與 Mesh）。 [R3]

關鍵前提：至少一台 UniFi Gateway 需具公網 IP；站點網段不可重疊；USG 不支援。 [R3]

### 9.2 流量規則（Traffic Rules）做最小權限

UniFi 的 Traffic & Policy 管理可用於允許/阻擋/限速特定流量，並由系統自動決定透過防火牆或 ACL 落地。 [R14]

跨站只允許：備份主機 -> NAS（SMB/HTTPS 等必要服務），避免 Any-Any。

Guest 網路與內網隔離：訪客 VLAN 與 Staff/IoT VLAN 嚴格分段。

## 10. [新增] 客人必須加入官方 LINE 才能開通免費 Wi-Fi

### 10.1 設計目標與原則

旅客連上 SSID 後，必須完成『LINE 登入 + 加好友驗證』才授權上網。

採 UniFi Hotspot / Captive Portal，並使用 External Portal Server 由 KTW 自建 Portal 負責驗證與授權。 [R1][R2]

授權前只放行 Portal 與 LINE 必要網域；避免額外放行 captive.apple.com 或 connectivitycheck.gstatic.com 以免破壞重導流程。 [R4]

### 10.2 高層架構（Logical Architecture）

Guest Device

  │ (connect SSID: KTW-Guest)

  ▼

UniFi AP / Gateway (Hotspot: authorized=false)  ──redirect──►  KTW External Portal

                                                        │

                                                        ├─ LINE Login (OAuth2)

                                                        ├─ Friendship Status API (friendFlag)

                                                        └─ UniFi Network API (AUTHORIZE_GUEST_ACCESS)

                                                                │

                                                                ▼

                                                        Guest Internet Access (authorized=true)

### 10.3 UniFi 端設定（Network Console）

建立 SSID：KTW-Guest，啟用 Hotspot Portal / Captive Portal。Hotspot 會隔離訪客與其他網路，確保分段安全。 [R1]

Authentication：選擇 External Portal Server（Advanced），Portal URL 指向你的 Portal 網域（HTTPS）。 [R1]

Pre-Authorization Allowances（授權前允許清單）：僅加入 Portal 網域與 LINE Login/驗證所需網域。

重要注意：不要額外允許 captive.apple.com (iOS) 或 connectivitycheck.gstatic.com (Android)，否則會破壞重導與 Portal 認證。 [R4]

### 10.4 External Portal Server：參數解析與授權流程

UniFi 會將 Client MAC、SSID 等資訊以 query string 帶給 Portal；Portal 可用這些資訊查詢 clientId 並進一步授權。 [R2]

範例 Redirect URL（UniFi -> External Portal）

http://PORTAL/guest/s/default/?ap=<AP_MAC>&id=<CLIENT_MAC>&t=<TS>&url=<ORIGINAL>&ssid=<SSID>

### 10.5 LINE 驗證：強制加好友的可機器判斷流程

採 LINE Login（建議啟用 add friend option），讓旅客登入後可引導加好友。 [R5]

Portal 取得 access token 後，呼叫 LINE Login v2.1 API：GET /friendship/v1/status，讀取 friendFlag。 [R6]

friendFlag = true：代表已加好友且未封鎖，允許下一步授權上網。 [R6]

friendFlag = false：顯示『請先加入官方 LINE』，並提供加好友按鈕/QR，再次檢查友誼狀態。

### 10.6 UniFi Network API：授權 client 上網

Portal 依 client MAC 取得 clientId（/v1/sites/{siteId}/clients?filter=macAddress.eq(...)），再呼叫 actions 授權。 [R2]

授權動作：AUTHORIZE_GUEST_ACCESS，可帶 time/data/rate 限制（例如 24 小時、每設備速率上限）。 [R2]

### 10.7 資料落地：Wi-Fi 授權稽核表（新增 Schema）

CREATE SCHEMA IF NOT EXISTS wifi;

CREATE TABLE wifi.access_logs (

  id BIGSERIAL PRIMARY KEY,

  line_user_id VARCHAR(64),

  client_mac VARCHAR(17) NOT NULL,

  ap_mac VARCHAR(17),

  ssid VARCHAR(64),

  authorized BOOLEAN DEFAULT FALSE,

  authorized_at TIMESTAMP,

  expires_at TIMESTAMP,

  unifi_client_id VARCHAR(64),

  ip_address VARCHAR(45),

  user_agent TEXT,

  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);

CREATE INDEX idx_wifi_access_mac ON wifi.access_logs(client_mac);

CREATE INDEX idx_wifi_access_line ON wifi.access_logs(line_user_id);

### 10.8 與既有程式碼結構的整合點

KTW-backend/src/drivers/unifi.js：延伸為『UniFi Network API client』，包含 sites/clients/actions 封裝。 [R2]

新增模組：KTW-backend/src/modules/wifi_portal/（Portal Landing、LINE callback、friendship status check）。

KTW-bot（AI Core）：可在旅客完成 Wi-Fi 認證後推送歡迎訊息/導流（非必需）。

# 附錄 A － 異地備份 Runbook（Windows + UniFi VPN + Synology）

## A.1 備份策略（建議）

資料庫：每日 1 次 pg_dump（custom 格式），保留 30 天；每週 1 次 full dump + 每日增量（如後續導入 PITR 再補 WAL）。pg_dump custom 格式可供 pg_restore 使用且預設壓縮，並具備較高還原彈性。 [R7][R15]

檔案：Kiosk 掃描暫存、報表、錄音檔等，以檔案層級備份至 NAS。

目的地：Synology NAS（異地放置），並啟用 Snapshot Replication 與不可變快照（WORM，建議保護期 7–14 天）。 [R8]

通道：透過 UniFi VPN（Site Magic）或既有 VPN，確保備份流量走加密通道。 [R3]

## A.2 PostgreSQL 備份命令（Windows 版本範例）

建議使用 pg_dump -F c 產生 custom 格式，並以時間戳命名。 [R7]

set PGPASSWORD=***

set BACKUP_DIR=D:\pg_backups

set DB=ktw_core

for /f "tokens=1-3 delims=/- " %%a in ("%date%") do set TODAY=%%a%%b%%c

"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe" -h 127.0.0.1 -U ktw -F c -f "%BACKUP_DIR%\%DB%_%TODAY%.dump" %DB%

若需免密碼執行，可使用 pgpass.conf。Windows 路徑為 %APPDATA%\postgresql\pgpass.conf。 [R9]

## A.3 備份檔複製到 Synology（Robocopy）

Robocopy 支援 restartable mode（/Z），中斷可續傳；適合 VPN 或不穩定鏈路。 [R16]

set SRC=D:\pg_backups

set DST=\\SYNOLOGY-NAS\ktw-backup\pg

robocopy "%SRC%" "%DST%" *.dump /MIR /Z /J /R:3 /W:10 /NP /LOG+:D:\logs\robocopy_pg.log

## A.4 Synology 端：快照/不可變快照

在 Snapshot Replication 建立共享資料夾快照排程。

針對備份共享資料夾啟用不可變快照（WORM），保護期建議 7–14 天，以抵禦勒索/誤刪。 [R8]

## A.5 還原演練（至少每季 1 次）

從 NAS 取回最近一份 dump。

在測試環境使用 pg_restore 還原，驗證 Booking/Room/Transactions 等核心表與索引。

演練紀錄寫入維運日誌（hardware_logs 同樣可加擴充維運 schema）。

# 附錄 B － LINE 加好友開通 Wi-Fi Runbook（UniFi Hotspot + External Portal）

## B.1 事前準備清單

UniFi Network Controller 常駐（自架或 Cloud Key/UDM），以確保 Portal 與 Hotspot 功能 24/7 可用。 [R1]

KTW External Portal 網域（建議獨立子網域，例如 portal.xxx.com），必須使用 HTTPS 憑證。

LINE Developers：建立 LINE Login Channel 並與 Official Account 連結（bot link），啟用 add friend option。 [R5]

KTW-backend 取得 UniFi Network API 存取權杖（依你採用的 UniFi 部署方式設定）。 [R2]

## B.2 UniFi 設定步驟（摘要）

Settings > WiFi：建立 SSID「KTW-Guest」，啟用 Hotspot Portal。 [R1]

Hotspot Manager / Landing Page：選 External Portal Server，填入 Portal URL。 [R1]

Pre-Authorization Allowances：只放行 Portal 與 LINE 必要網域；不要放行 captive.apple.com / connectivitycheck.gstatic.com。 [R4]

Client Isolation / VLAN Segmentation：啟用訪客隔離，避免 Guest 互相或存取內網。 [R17]

## B.3 Portal 行為與錯誤排除

Portal 沒跳轉：檢查 Hotspot 是否啟用、Controller 是否在線、以及是否誤放行 iOS/Android 連線檢測網域造成 redirect 失效。 [R4]

LINE Login callback 失敗：檢查 Channel callback URL、HTTPS 憑證、以及 state/nonce 驗證。 [R5][R6]

friendFlag 一直 false：確認 OA 與 LINE Login channel 已正確連結；使用 friendship status API 以 access token 查詢。 [R6]

授權成功但無法上網：檢查 Gateway DNS/NAT、Traffic Rules 是否阻擋，以及 Guest VLAN 是否有正確出網路由。 [R14]

# 參考資料（References）

[R1] Ubiquiti Help Center, “UniFi Hotspots and Captive Portals.” https://help.ui.com/hc/en-us/articles/115000166827-UniFi-Hotspots-and-Captive-Portals

[R2] Ubiquiti Help Center, “External Hotspot API for Authorization Clients.” https://help.ui.com/hc/en-us/articles/31228198640023-External-Hotspot-API-for-Authorization-Clients

[R3] Ubiquiti Help Center, “UniFi Gateway - Setting Up SD-WAN with UniFi Site Magic.” https://help.ui.com/hc/en-us/articles/16750417515159-UniFi-Gateway-Setting-Up-SD-WAN-with-UniFi-Site-Magic

[R4] Ubiquiti Help Center (TW), “UniFi 熱點門戶和訪客 WiFi” 注意事項（勿放行 captive.apple.com 等）。 https://help.tw.ui.com/articles/115000166827/

[R5] LINE Developers, “Add a LINE Official Account as a friend when logged in (add friend option).” https://developers.line.biz/en/docs/line-login/link-a-bot/

[R6] LINE Developers, “LINE Login v2.1 API reference” (Friendship status). https://developers.line.biz/en/reference/line-login/

[R7] PostgreSQL Documentation, “pg_dump” (custom format archive suitable for pg_restore). https://www.postgresql.org/docs/current/app-pgdump.html

[R8] Synology Knowledge Center, “不可變快照是什麼？該如何使用？”（WORM，不可變快照，保護期建議 7–14 天）。 https://kb.synology.com/zh-tw/DSM/tutorial/what_is_an_immutable_snapshot

[R9] PostgreSQL Documentation, “The Password File (pgpass.conf)”（Windows 路徑 %APPDATA%\postgresql\pgpass.conf）。 https://www.postgresql.org/docs/current/libpq-pgpass.html

[R10] Microsoft Support, “針對 Windows Server 2016 的支援即將在 2027 年 1 月終止。” https://support.microsoft.com/zh-tw/topic/%E9%87%9D%E5%B0%8D-windows-server-2016-%E7%9A%84%E6%94%AF%E6%8F%B4%E5%8D%B3%E5%B0%87%E5%9C%A8-2027-%E5%B9%B4-1-%E6%9C%88%E7%B5%82%E6%AD%A2-ffd9e92c-5027-4201-b6e1-ed46f8486b43

[R11] Dell, “Dell PowerEdge T350 Spec Sheet.” https://i.dell.com/sites/csdocuments/Product_Docs/en/dell-emc-poweredge-t350-spec-sheet.pdf

[R12] HPE, “HPE ProLiant ML30 Gen11 data sheet.” https://www.hpe.com/psnow/generateDDS/HPE%20ProLiant%20ML30%20Gen11%20data%20sheet-PSN1014788890COEN.pdf

[R13] Lenovo Docs, “ThinkSystem ST50 V3 技術規格.” https://pubs.lenovo.com/st50-v3/zh-TW/server_specifications_technical

[R14] Ubiquiti Help Center, “Traffic & Policy Management in UniFi.” https://help.ui.com/hc/en-us/articles/5546542486551-Traffic-Policy-Management-in-UniFi

[R15] PostgreSQL Documentation, “Chapter 25. Backup and Restore.” https://www.postgresql.org/docs/current/backup.html

[R16] Microsoft Learn, “Robocopy.” https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/robocopy

[R17] Ubiquiti Help Center, “Implementing Network and Client Isolation in UniFi.” https://help.ui.com/hc/en-us/articles/18965560820247-Implementing-Network-and-Client-Isolation-in-UniFi