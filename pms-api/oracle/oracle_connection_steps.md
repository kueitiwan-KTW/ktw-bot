# Oracle 資料庫連線指引

## 已確認資訊
- **資料庫名稱（SID）**: gdwuukt
- **主機**: gdwuukt-db01
- **連接埠**: 1521
- **SQL*Plus 路徑**: C:\app\product\12.2.0\client_1\bin\sqlplus.exe

## 下一步：嘗試連接

### 步驟 1：確認主機位置
```cmd
hostname
```
**目的**：確認資料庫是在本機還是遠端伺服器

---

### 步驟 2：嘗試連接資料庫

**方法 A - 使用 SYSTEM 帳號**：
```cmd
cd C:\app\product\12.2.0\client_1\bin
sqlplus system@gdwuukt
```
> 會提示輸入密碼，如果不知道就按 Enter

**方法 B - 使用 OS 驗證**：
```cmd
sqlplus / as sysdba @gdwuukt
```

**方法 C - 使用 SYS 帳號**：
```cmd
sqlplus sys@gdwuukt as sysdba
```

---

## 請回報
1. hostname 的結果
2. 連接時的錯誤訊息或提示
