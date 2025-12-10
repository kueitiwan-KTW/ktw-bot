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

module.exports = router;
