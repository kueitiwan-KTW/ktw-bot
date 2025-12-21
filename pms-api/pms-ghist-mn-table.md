# PMS GHIST_MN 客戶歷史資料表

> 此表儲存客人的歷史資料，每位客人有唯一的 HFD 編號 (GCUST_COD)。

## 欄位清單 (共 82 個)

### 基本資料
| # | 欄位 | 說明 | 範例 |
|:--:|:-----|:-----|:-----|
| 1 | GCUST_COD | **客戶資料編號 (HFD)** | HFD000000000310001 |
| 2 | SHOW_COD | 顯示代碼 | HFD000000000310001 |
| 3 | LAST_NAM | 姓氏 | 簡 |
| 4 | FIRST_NAM | 名字 | 瑞儀 |
| 5 | ALT_NAM | 別名/中文名 | 簡瑞儀 |
| 6 | GUEST_TYP | 客人類型代碼 | 03 |
| 7 | GUEST_WAY | 客人來源途徑 | - |
| 8 | CONTRY_COD | 國籍代碼 | TWN |
| 9 | LIVE_COD | 居住地代碼 | - |
| 10 | ID_NOS | 身分證/護照號碼 | Q123578523 |
| 11 | BIRTH_DAT | 生日 | 1986-11-30 |
| 12 | SEX_TYP | 性別 (M/F) | M |

### 聯絡資料
| # | 欄位 | 說明 | 範例 |
|:--:|:-----|:-----|:-----|
| 13 | CONTACT1_COD | 聯絡方式1代碼 | - |
| 14 | CONTACT1_RMK | 聯絡方式1內容 | 0989015163 |
| 15 | CONTACT2_COD | 聯絡方式2代碼 | - |
| 16 | CONTACT2_RMK | 聯絡方式2內容 | - |
| 17 | CONTACT3_COD | 聯絡方式3代碼 | - |
| 18 | CONTACT3_RMK | 聯絡方式3內容 | - |
| 19 | CONTACT4_COD | 聯絡方式4代碼 | - |
| 20 | CONTACT4_RMK | 聯絡方式4內容 | - |
| 72 | E_MAIL | 電子郵件 | raintoo@hotmail.com |
| 73 | E_MAIL_COD | 郵件代碼 | - |

### 公司/代理
| # | 欄位 | 說明 |
|:--:|:-----|:-----|
| 21 | UNI_COD | 統一編號 |
| 24 | CCUST_COD | 公司客戶代碼 (CS開頭) |
| 25 | ACUST_COD | 代理代碼 |
| 59 | CCUST_NAM | 公司名稱 |

### 入住歷史
| # | 欄位 | 說明 | 範例 |
|:--:|:-----|:-----|:-----|
| 26 | FIRST_DAT | 首次入住日期 | 2022-07-17 |
| 27 | LAST_DAT | 最後入住日期 | 2022-07-17 |
| 28 | VISIT_NOS | 累計入住次數 | 1 |
| 29 | VISITDAT_NOS | 累計入住天數 | 1 |
| 30 | REQUST_RMK | ⭐ **客戶備註/特殊需求** | - |
| 42 | CHARACTER_RMK | 客戶特徵備註 | - |
| 43 | TRANS_TOT | 累計消費金額 | - |

### VIP / 狀態
| # | 欄位 | 說明 |
|:--:|:-----|:-----|
| 31 | MESSGE_STA | 訊息狀態 |
| 32 | VIP_STA | VIP 狀態 (0=否) |
| 33 | LANG_COD | 語言代碼 |
| 34 | ROLE_COD | 角色代碼 |
| 35 | SALUTE_COD | 稱謂代碼 |
| 36 | STATUS_COD | 狀態代碼 |
| 37 | PREF_ROOM | 偏好房型 |
| 40 | CO_DEL_STA | 刪除狀態 |
| 41 | MCUST_COD | 主客戶代碼 |

### 偏好設定
| # | 欄位 | 說明 |
|:--:|:-----|:-----|
| 61 | FAVER_FOOD | 喜好食物 |
| 62 | FAVER_DRINK | 喜好飲料 |
| 63 | FAVER_SMOKE | 吸煙偏好 |
| 64 | FAVER | 其他偏好 |
| 65 | FAVER_OTHER | 其他偏好2 |
| 66 | FAVER_NEWSPP | 報紙偏好 |
| 67 | FAVER_SPA | SPA偏好 |

### 發票/統編
| # | 欄位 | 說明 |
|:--:|:-----|:-----|
| 22 | CREDIT_NOS | 信用卡號 |
| 23 | EXPIRA_DAT | 信用卡效期 |
| 38 | UNIINV_TITLE | 發票抬頭 |

### 車輛/航空
| # | 欄位 | 說明 |
|:--:|:-----|:-----|
| 70 | CAR_BARND | 車輛品牌 |
| 71 | CAR_COLOR | 車輛顏色 |
| 78 | CAR_NOS | 車牌號碼 |
| 79 | AIRLINE_COD | 航空公司代碼 |
| 80 | AIRMB_NOS | 航空會員號 |

### 分類標籤 (GHIST_TYP)
| # | 欄位 | 說明 |
|:--:|:-----|:-----|
| 44 | INS_CUST_TYP | 建檔客戶類型 |
| 45-54 | GHIST1~10_TYP | 客戶分類標籤1~10 |

### 系統欄位
| # | 欄位 | 說明 |
|:--:|:-----|:-----|
| 39 | HOTEL_COD | 飯店代碼 |
| 55 | DM_FLAG | DM旗標 |
| 56 | ACU_CUST_COD | 累計客戶代碼 |
| 57 | ACU_SHOW_COD | 累計顯示代碼 |
| 58 | WEDDING_DAT | 結婚紀念日 |
| 60 | RS_DISC_COD | 折扣代碼 |
| 68 | ITEM_LIST | 項目清單 |
| 69 | ANAMNESIS | 病歷/過敏史 |
| 74 | INS_DAT | 建檔日期 |
| 75 | INS_USR | 建檔人員 |
| 76 | UPD_DAT | 更新日期 |
| 77 | UPD_USR | 更新人員 |
| 81 | IDENTIFY_COD | 識別代碼 |
| 82 | IDENTIFY_NOS | 識別號碼 |

---

## 關聯說明

```
ORDER_MN (訂單表)
├── IKEY (訂單編號)
├── CCUST_COD → GHIST_MN.CCUST_COD (公司)
└── 透過 GUEST_MN 關聯到 GHIST_MN

GUEST_MN (住客表)
├── IKEY → ORDER_MN.IKEY
├── GCUST_COD → GHIST_MN.GCUST_COD (客人)
└── ID_COD → GHIST_MN.ID_NOS

GHIST_MN (客戶歷史表)
├── GCUST_COD (HFD開頭的客戶唯一識別碼)
└── 儲存客人的歷史資料、偏好、備註
```

---

## OTA 訂單編號前綴對照

| 前綴 | 訂房來源 |
|:-----|:---------|
| RMAG | Agoda |
| RMBK | Booking.com |
| RMEX | Expedia |
| RMCPT | 攜程 |
| RMPGP | 官網 |
| 無OTA編號 | 手KEY |

---

*文件建立日期：2025-12-15*
