/**
 * 房間相關路由
 */

const express = require('express');
const router = express.Router();
const db = require('../config/database');

/**
 * GET /api/rooms/availability
 * 查詢可用房間
 */
router.get('/availability', async (req, res) => {
    try {
        const { check_in, check_out } = req.query;

        if (!check_in || !check_out) {
            return res.status(400).json({
                success: false,
                error: {
                    code: 'MISSING_PARAMETER',
                    message: '請提供 check_in 和 check_out 參數'
                }
            });
        }

        const pool = db.getPool();
        const connection = await pool.getConnection();

        try {
            // 查詢所有房型
            const result = await connection.execute(
                `SELECT 
           rm.ROOM_TYP as room_type_code,
           rm.ROOM_NAM as room_type_name,
           rm.ROOM_QNT as total_rooms,
           NVL(
             (SELECT SUM(od.ORDER_QNT)
              FROM GDWUUKT.ORDER_DT od
              JOIN GDWUUKT.ORDER_MN om ON TRIM(od.IKEY) = TRIM(om.IKEY)
              WHERE od.ROOM_COD = rm.ROOM_TYP
                AND om.ORDER_STA IN ('O', 'R', 'I')
                AND om.CO_DAT > TO_DATE(:check_in, 'YYYY-MM-DD')
                AND om.CI_DAT < TO_DATE(:check_out, 'YYYY-MM-DD')
             ), 0
           ) as booked_rooms
         FROM GDWUUKT.ROOM_RF rm
         ORDER BY rm.ROOM_TYP`,
                { check_in, check_out }
            );

            const rooms = result.rows.map(row => ({
                room_type_code: row[0],
                room_type_name: row[1],
                total_rooms: row[2],
                booked_rooms: row[3],
                available_rooms: row[2] - row[3],
                is_available: (row[2] - row[3]) > 0
            }));

            res.json({
                success: true,
                data: {
                    check_in,
                    check_out,
                    rooms
                }
            });

        } finally {
            await connection.close();
        }

    } catch (err) {
        console.error('查詢可用房間失敗：', err);
        res.status(500).json({
            success: false,
            error: {
                code: 'DATABASE_ERROR',
                message: '查詢可用房間時發生錯誤'
            }
        });
    }
});

/**
 * GET /api/rooms/today-availability
 * 查詢今日可預訂房型（當日預訂專用）
 * 使用 WRS_STOCK_DT（網路庫存）和 RMINV_MN（館內庫存）
 * 
 * ⚠️ 僅限「當日可訂房價」查詢，已訂訂單價格必須 100% 依據訂單內容
 * 
 * 房價計算：ratecod_dt 基準價（含早）+ 日類型對應加價
 * - 日類型來源：holiday_rf (BATCH_DAT → DAY_STA)
 * - 加價映射：service_rf (COMMAND_OPTION = 'H' + DAY_STA → ITEM_NOS)
 * - 加價金額：service_dt (KEY + ROOM_COD + SERV_COD → ITEM_AMT)
 */
router.get('/today-availability', async (req, res) => {
    try {
        const pool = db.getPool();
        const connection = await pool.getConnection();

        try {
            // 使用 Oracle SYSDATE 取得今日日期（自動校正時區）
            const dateResult = await connection.execute(`
                SELECT TO_CHAR(SYSDATE, 'YYYY-MM-DD') as today FROM DUAL
            `);
            const today = dateResult.rows[0][0];

            // 步驟 1：查詢今日日類型
            const dayTypeResult = await connection.execute(`
                SELECT TRIM(DAY_STA) as day_sta
                FROM GDWUUKT.HOLIDAY_RF
                WHERE TRUNC(BATCH_DAT) = TO_DATE(:today, 'YYYY-MM-DD')
            `, { today });
            
            const dayType = dayTypeResult.rows.length > 0 ? dayTypeResult.rows[0][0] : 'N';

            // 日類型名稱對照
            const dayTypeNames = {
                'N': '平日', 'D': '旺日', 'H': '假日',
                'S': '旺季', 'T': '緊迫日', 'W': '旺季假日'
            };
            const dayTypeName = dayTypeNames[dayType] || '平日';

            // 步驟 2：查詢庫存 + 基準價 + 加價金額（單一 SQL）
            // 基準價：ratecod_dt (web001)
            // 加價：service_dt 透過 service_rf.COMMAND_OPTION 映射日類型
            const result = await connection.execute(`
                SELECT 
                    TRIM(w.ROOM_COD) as room_type_code,
                    rf.ROOM_NAM as room_type_name,
                    w.STOCK_QNT as web_stock,
                    w.USE_QNT as web_used,
                    (w.STOCK_QNT - w.USE_QNT) as web_available,
                    NVL(r.LEFT_QNT, 0) as local_stock,
                    NVL(r.ROOM_QNT, 0) as total_rooms,
                    NVL(p2.RENT_AMT, 0) as base_price,
                    NVL(sd.ITEM_AMT, 0) as surcharge,
                    NVL((
                        SELECT COUNT(*)
                        FROM GDWUUKT.ROOM_MN rm2
                        WHERE TRIM(rm2.ROOM_COD) = TRIM(w.ROOM_COD)
                    ), 0) as total_rooms_count,
                    NVL((
                        SELECT COUNT(*)
                        FROM GDWUUKT.ROOM_MN rm
                        WHERE TRIM(rm.ROOM_COD) = TRIM(w.ROOM_COD)
                          AND TRIM(rm.ROOM_STA) = 'V'
                          AND TRIM(rm.CLEAN_STA) = 'C'
                          AND NVL(TRIM(rm.OOS_STA), 'N') != 'Y'
                    ), 0) as clean_vacant_count
                FROM GDWUUKT.WRS_STOCK_DT w
                LEFT JOIN GDWUUKT.RMINV_MN r 
                    ON TRIM(w.ROOM_COD) = TRIM(r.ROOM_COD) 
                    AND TRUNC(w.BATCH_DAT) = TRUNC(r.BATCH_DAT)
                LEFT JOIN GDWUUKT.ROOM_RF rf 
                    ON TRIM(w.ROOM_COD) = TRIM(rf.ROOM_TYP)
                LEFT JOIN GDWUUKT.RATECOD_DT p2
                    ON TRIM(w.ROOM_COD) = TRIM(p2.ROOM_COD)
                    AND p2.KEY IN (SELECT KEY FROM GDWUUKT.RATECOD_MN WHERE TRIM(RATE_COD) = 'web001')
                LEFT JOIN GDWUUKT.SERVICE_DT sd
                    ON TRIM(w.ROOM_COD) = TRIM(sd.ROOM_COD)
                    AND sd.KEY IN (SELECT KEY FROM GDWUUKT.RATECOD_MN WHERE TRIM(RATE_COD) = 'web001')
                    AND TRIM(sd.SERV_COD) IN (
                        SELECT TRIM(ITEM_NOS) FROM GDWUUKT.SERVICE_RF 
                        WHERE TRIM(COMMAND_OPTION) = :cmd_option
                    )
                WHERE TRUNC(w.BATCH_DAT) = TO_DATE(:today, 'YYYY-MM-DD')
                ORDER BY w.ROOM_COD
            `, { 
                today,
                cmd_option: dayType === 'N' ? 'NONE' : ('H' + dayType)
            });

            // 取得伺服器當前小時（用 Oracle SYSDATE 校正時區）
            const hourResult = await connection.execute(`
                SELECT TO_NUMBER(TO_CHAR(SYSDATE, 'HH24')) as current_hour FROM DUAL
            `);
            const currentHour = hourResult.rows[0][0];
            const useCleanFilter = currentHour >= 14;  // 14:00 後才啟用清潔過濾

            // 過濾出有庫存的房型（14:00 後額外檢查乾淨空房）
            const availableRoomTypes = result.rows
                .filter(row => {
                    const webAvailable = row[4] || 0;  // web_available
                    const localStock = row[5] || 0;    // local_stock
                    const cleanVacant = row[10] || 0;  // clean_vacant_count
                    const hasInventory = webAvailable > 0 || localStock > 0;
                    if (!hasInventory) return false;
                    // 14:00 後需至少有一間乾淨空房
                    if (useCleanFilter && cleanVacant <= 0) return false;
                    return true;
                })
                .map(row => {
                    const basePrice = row[7] || 0;
                    const surcharge = row[8] || 0;
                    const inventoryCount = (row[4] || 0) + (row[5] || 0);
                    const cleanVacant = row[10] || 0;  // 因為新增了 total_rooms_rf，index 往後移 1
                    const totalRooms = row[9] || 0;    // ROOM_RF.ROOM_QNT 總房數
                    // 14:00 後：可用數 = MIN(庫存, 乾淨空房)；14:00 前：可用數 = 庫存
                    let effectiveCount = useCleanFilter
                        ? Math.min(inventoryCount, cleanVacant)
                        : inventoryCount;
                    // 不得超過該房型的總房間數
                    if (totalRooms > 0) {
                        effectiveCount = Math.min(effectiveCount, totalRooms);
                    }
                    return {
                        room_type_code: row[0],
                        room_type_name: row[1] || row[0],
                        web_available: row[4] || 0,
                        local_stock: row[5] || 0,
                        available_count: effectiveCount,
                        total_rooms: totalRooms,
                        clean_vacant: cleanVacant,
                        clean_filter_active: useCleanFilter,
                        price: basePrice + surcharge,       // 總價（基準 + 加價）
                        base_price: basePrice,              // 基準價（含早）
                        surcharge: surcharge,               // 日類型加價
                        day_type: dayType,                  // 日類型代碼
                        day_type_name: dayTypeName           // 日類型名稱
                    };
                });

            // 計算總數
            const totalWebAvailable = availableRoomTypes.reduce((sum, r) => sum + r.web_available, 0);
            const totalLocalStock = availableRoomTypes.reduce((sum, r) => sum + r.local_stock, 0);

            res.json({
                success: true,
                data: {
                    date: today,
                    day_type: dayType,
                    day_type_name: dayTypeName,
                    available_room_types: availableRoomTypes,
                    summary: {
                        web_available: totalWebAvailable,
                        local_stock: totalLocalStock,
                        total_available: totalWebAvailable + totalLocalStock
                    },
                    has_availability: availableRoomTypes.length > 0
                }
            });

        } finally {
            await connection.close();
        }

    } catch (err) {
        console.error('查詢今日可用房型失敗：', err);
        res.status(500).json({
            success: false,
            error: {
                code: 'DATABASE_ERROR',
                message: '查詢今日可用房型時發生錯誤'
            }
        });
    }
});

/**
 * GET /api/rooms/explore
 * 探索房間相關資料表結構（開發用）
 */
router.get('/explore', async (req, res) => {
    try {
        const pool = db.getPool();
        const connection = await pool.getConnection();

        try {
            const results = {};

            // 1. 查詢所有包含 ROOM 的資料表
            const roomTables = await connection.execute(`
                SELECT TABLE_NAME 
                FROM ALL_TABLES 
                WHERE OWNER = 'GDWUUKT' 
                AND (TABLE_NAME LIKE '%ROOM%' OR TABLE_NAME LIKE '%HOUSE%' OR TABLE_NAME LIKE '%HK%')
                ORDER BY TABLE_NAME
            `);
            results.roomTables = roomTables.rows.map(r => r[0]);

            // 2. 查詢 ROOM_MN 欄位結構
            const roomMnCols = await connection.execute(`
                SELECT COLUMN_NAME, DATA_TYPE, NULLABLE
                FROM ALL_TAB_COLUMNS 
                WHERE OWNER = 'GDWUUKT' AND TABLE_NAME = 'ROOM_MN'
                ORDER BY COLUMN_ID
            `);
            results.roomMnColumns = roomMnCols.rows.map(r => ({
                name: r[0],
                type: r[1],
                nullable: r[2]
            }));

            // 3. 查詢 ROOM_MN 樣本資料
            try {
                const sample = await connection.execute(`
                    SELECT * FROM GDWUUKT.ROOM_MN WHERE ROWNUM <= 5
                `);
                results.roomMnSample = sample.rows.map(row => {
                    const obj = {};
                    sample.metaData.forEach((col, i) => {
                        obj[col.name] = row[i];
                    });
                    return obj;
                });
            } catch (e) {
                results.roomMnSample = { error: e.message };
            }

            // 4. 查詢包含 STATUS/STA/CLEAN 的欄位
            const statusCols = await connection.execute(`
                SELECT t.TABLE_NAME, c.COLUMN_NAME, c.DATA_TYPE
                FROM ALL_TABLES t
                JOIN ALL_TAB_COLUMNS c ON t.TABLE_NAME = c.TABLE_NAME AND t.OWNER = c.OWNER
                WHERE t.OWNER = 'GDWUUKT' 
                AND (t.TABLE_NAME LIKE '%ROOM%' OR t.TABLE_NAME LIKE '%HOUSE%')
                AND (c.COLUMN_NAME LIKE '%STATUS%' OR c.COLUMN_NAME LIKE '%STA%' OR c.COLUMN_NAME LIKE '%CLEAN%')
                ORDER BY t.TABLE_NAME, c.COLUMN_NAME
            `);
            results.statusColumns = statusCols.rows.map(r => ({
                table: r[0],
                column: r[1],
                type: r[2]
            }));

            res.json({
                success: true,
                data: results
            });

        } finally {
            await connection.close();
        }

    } catch (err) {
        console.error('探索房間資料表失敗：', err);
        res.status(500).json({
            success: false,
            error: {
                code: 'DATABASE_ERROR',
                message: err.message
            }
        });
    }
});

/**
 * GET /api/rooms/status
 * 查詢所有房間的清潔/停用狀態
 */
router.get('/status', async (req, res) => {
    try {
        const pool = db.getPool();
        const connection = await pool.getConnection();

        try {
            // 查詢房間狀態 + 房型名稱
            const result = await connection.execute(`
                SELECT 
                    TRIM(rm.ROOM_NOS) as room_number,
                    TRIM(rm.FLOOR_NOS) as floor,
                    TRIM(rm.ROOM_COD) as room_type_code,
                    rf.ROOM_NAM as room_type_name,
                    TRIM(rm.ROOM_STA) as room_status,
                    TRIM(rm.CLEAN_STA) as clean_status,
                    TRIM(rm.OOS_STA) as oos_status,
                    TRIM(rm.OSRESON_RMK) as oos_reason,
                    rm.UPD_DAT as last_update
                FROM GDWUUKT.ROOM_MN rm
                LEFT JOIN GDWUUKT.ROOM_RF rf ON rm.ROOM_COD = rf.ROOM_TYP
                ORDER BY rm.FLOOR_NOS, rm.ROOM_NOS
            `);

            // 清潔狀態對照表
            const cleanStatusMap = {
                'C': { code: 'C', name: '乾淨', color: 'green' },
                'D': { code: 'D', name: '髒（待清掃）', color: 'red' },
                'I': { code: 'I', name: '待檢查', color: 'yellow' }
            };

            // 房間狀態對照表
            const roomStatusMap = {
                'V': { code: 'V', name: '空房' },
                'O': { code: 'O', name: '入住中' }
            };

            const rooms = result.rows.map(row => ({
                room_number: row[0],
                floor: row[1],
                room_type_code: row[2],
                room_type_name: row[3],
                room_status: roomStatusMap[row[4]] || { code: row[4], name: row[4] },
                clean_status: cleanStatusMap[row[5]] || { code: row[5], name: row[5], color: 'gray' },
                oos_status: row[6] === 'Y',
                oos_reason: row[7],
                last_update: row[8]
            }));

            // 統計數據
            const stats = {
                total: rooms.length,
                clean: rooms.filter(r => r.clean_status.code === 'C' && !r.oos_status).length,
                dirty: rooms.filter(r => r.clean_status.code === 'D' && !r.oos_status).length,
                inspecting: rooms.filter(r => r.clean_status.code === 'I' && !r.oos_status).length,
                oos: rooms.filter(r => r.oos_status).length,
                occupied: rooms.filter(r => r.room_status.code === 'O').length,
                vacant: rooms.filter(r => r.room_status.code === 'V').length
            };

            res.json({
                success: true,
                data: {
                    stats,
                    rooms
                }
            });

        } finally {
            await connection.close();
        }

    } catch (err) {
        console.error('查詢房間狀態失敗：', err);
        res.status(500).json({
            success: false,
            error: {
                code: 'DATABASE_ERROR',
                message: err.message
            }
        });
    }
});

module.exports = router;
