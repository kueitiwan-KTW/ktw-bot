/**
 * 儀表板相關路由
 */

const express = require('express');
const router = express.Router();
const db = require('../config/database');

/**
 * GET /api/dashboard/stats
 * 查詢儀表板統計數據
 */
router.get('/stats', async (req, res) => {
    try {
        const pool = db.getPool();
        const connection = await pool.getConnection();

        try {
            // 今日入住數量
            const checkinResult = await connection.execute(`
                SELECT COUNT(*) 
                FROM GDWUUKT.ORDER_MN om
                WHERE TRUNC(om.CI_DAT) = TRUNC(SYSDATE)
                  AND om.ORDER_STA IN ('O', 'I')
            `);

            // 今日退房數量
            const checkoutResult = await connection.execute(`
                SELECT COUNT(*) 
                FROM GDWUUKT.ORDER_MN om
                WHERE TRUNC(om.CO_DAT) = TRUNC(SYSDATE)
                  AND om.ORDER_STA IN ('I', 'D')
            `);

            // 目前入住中訂單數
            const occupiedResult = await connection.execute(`
                SELECT COUNT(*)
                FROM GDWUUKT.ORDER_MN om
                WHERE om.ORDER_STA = 'I'
            `);

            // 總房間數
            const totalRoomsResult = await connection.execute(`
                SELECT SUM(ROOM_QNT) FROM GDWUUKT.ROOM_RF
            `);

            // 本月營收（已入住和已退房的訂單）
            const revenueResult = await connection.execute(`
                SELECT NVL(SUM(od.RENT_TOT), 0)
                FROM GDWUUKT.ORDER_DT od
                JOIN GDWUUKT.ORDER_MN om ON TRIM(od.IKEY) = TRIM(om.IKEY)
                WHERE om.ORDER_STA IN ('I', 'D')
                  AND TRUNC(om.CI_DAT) >= TRUNC(SYSDATE, 'MM')
            `);

            const todayCheckin = checkinResult.rows[0][0] || 0;
            const todayCheckout = checkoutResult.rows[0][0] || 0;
            const occupiedRooms = occupiedResult.rows[0][0] || 0;
            const totalRooms = totalRoomsResult.rows[0][0] || 50;
            const monthlyRevenue = revenueResult.rows[0][0] || 0;

            res.json({
                success: true,
                data: {
                    todayCheckin,
                    todayCheckout,
                    occupiedRooms,
                    totalRooms,
                    vacantRooms: totalRooms - occupiedRooms,
                    occupancyRate: totalRooms > 0 ? Math.round((occupiedRooms / totalRooms) * 100) : 0,
                    monthlyRevenue,
                    lastUpdate: new Date().toISOString()
                }
            });

        } finally {
            await connection.close();
        }

    } catch (err) {
        console.error('查詢儀表板統計失敗：', err);
        res.status(500).json({
            success: false,
            error: {
                code: 'DATABASE_ERROR',
                message: '查詢儀表板統計時發生錯誤'
            }
        });
    }
});

module.exports = router;
