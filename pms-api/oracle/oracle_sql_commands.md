# Oracle 資料庫連線與探索指令

## 第一步：連接資料庫

開啟**命令提示字元**，執行：

```cmd
d:\app\product\12.2.0\dbhome_1\bin\sqlplus.exe / as sysdba
```

成功後會看到：
```
Connected to:
Oracle Database 12c ...

SQL>
```

---

## 第二步：探索資料庫結構

連接成功後，在 `SQL>` 提示符下依序執行以下指令：

### 1. 列出所有資料表
```sql
SELECT table_name FROM dba_tables WHERE owner NOT IN ('SYS','SYSTEM','OUTLN','DBSNMP','APPQOSSYS','ORDDATA','ORDSYS','MDSYS','CTXSYS','XDB','WMSYS') ORDER BY table_name;
```

### 2. 查找訂房相關資料表
```sql
SELECT table_name FROM dba_tables WHERE table_name LIKE '%BOOK%' OR table_name LIKE '%RESERV%' OR table_name LIKE '%ROOM%' OR table_name LIKE '%GUEST%';
```

### 3. 查看資料表結構（替換 TABLE_NAME）
```sql
DESC owner_name.table_name;
```

### 4. 查看資料表內容範例（前 10 筆）
```sql
SELECT * FROM owner_name.table_name WHERE ROWNUM <= 10;
```

---

## 執行步驟

1. 先執行連接指令
2. 成功後執行第二步的 SQL 查詢
3. 將結果複製貼回給我分析
