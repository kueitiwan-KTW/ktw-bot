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
