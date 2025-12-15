/**
 * 訂單相關路由
 */

const express = require('express');
const router = express.Router();
const db = require('../config/database');
const { STATUS_MAP, getStatusName, getRoomTotal, getDepositPaid, getRoomDetails, getRoomNumbers, getEffectiveStatus, getCheckinBookings } = require('../helpers/bookingHelpers');



/**
 * GET /api/bookings/search
 * 查詢訂單（依姓名或電話）
 */
router.get('/search', async (req, res) => {
    try {
        const { name, phone } = req.query;

        if (!name && !phone) {
            return res.status(400).json({
                success: false,
                error: {
                    code: 'MISSING_PARAMETER',
                    message: '請提供姓名或電話至少一項'
                }
            });
        }

        const pool = db.getPool();
        const connection = await pool.getConnection();

        try {
            let sql = `
        SELECT 
          TRIM(om.IKEY) as booking_id,
          om.CUST_NAM as guest_name,
          om.CONTACT1_RMK as contact_phone,
          TO_CHAR(om.CI_DAT, 'YYYY-MM-DD') as check_in_date,
          TO_CHAR(om.CO_DAT, 'YYYY-MM-DD') as check_out_date,
          om.DAYS as nights,
          om.ORDER_STA as status_code
        FROM GDWUUKT.ORDER_MN om
        WHERE 1=1
      `;

            const binds = {};

            if (name) {
                sql += ` AND om.CUST_NAM LIKE '%' || :name || '%'`;
                binds.name = name;
            }

            if (phone) {
                sql += ` AND om.CONTACT1_RMK LIKE '%' || :phone || '%'`;
                binds.phone = phone;
            }

            sql += ` ORDER BY om.CI_DAT DESC FETCH FIRST 50 ROWS ONLY`;

            const result = await connection.execute(sql, binds);

            // 狀態碼轉換函數
            // const statusMap = { 'O': '已確認', 'R': '預約中', 'C': '已取消', 'I': '已入住', 'D': '已取消', 'N': '新訂單' };

            const bookings = await Promise.all(result.rows.map(async row => {
                const bookingId = row[0];

                // 使用統一的狀態判斷函數 (DRY)
                const { statusCode, statusName } = await getEffectiveStatus(connection, bookingId, row[6]);

                return {
                    booking_id: bookingId,
                    guest_name: row[1],
                    contact_phone: row[2],
                    check_in_date: row[3],
                    check_out_date: row[4],
                    nights: row[5],
                    status_code: statusCode,
                    status_name: statusName
                };
            }));

            res.json({
                success: true,
                data: bookings,
                count: bookings.length
            });

        } finally {
            await connection.close();
        }

    } catch (err) {
        console.error('查詢訂單失敗：', err);
        res.status(500).json({
            success: false,
            error: {
                code: 'DATABASE_ERROR',
                message: '查詢訂單時發生錯誤'
            }
        });
    }
});

/**
 * GET /api/bookings/today-checkin
 * 查詢今日入住訂單清單
 */
router.get('/today-checkin', async (req, res) => {
    try {
        const pool = db.getPool();
        const connection = await pool.getConnection();

        try {
            // 使用共用函數查詢 (DRY)
            const bookings = await getCheckinBookings(connection, 0, "'O','I','N'");

            res.json({
                success: true,
                data: bookings,
                count: bookings.length,
                date: new Date().toISOString().split('T')[0]
            });

        } finally {
            await connection.close();
        }

    } catch (err) {
        console.error('查詢今日入住失敗：', err);
        res.status(500).json({
            success: false,
            error: {
                code: 'DATABASE_ERROR',
                message: '查詢今日入住時發生錯誤'
            }
        });
    }
});

/**
 * GET /api/bookings/yesterday-checkin
 * 查詢昨日入住訂單清單（用於開發測試）
 */
router.get('/yesterday-checkin', async (req, res) => {
    try {
        const pool = db.getPool();
        const connection = await pool.getConnection();

        try {
            // 使用共用函數查詢 (DRY)
            const bookings = await getCheckinBookings(connection, -1, "'O','I','N','D','C','S'");

            res.json({
                success: true,
                data: bookings,
                count: bookings.length,
                date: new Date(Date.now() - 86400000).toISOString().split('T')[0]  // 昨天
            });

        } finally {
            await connection.close();
        }

    } catch (err) {
        console.error('查詢昨日入住失敗：', err);
        res.status(500).json({
            success: false,
            error: {
                code: 'DATABASE_ERROR',
                message: '查詢昨日入住時發生錯誤'
            }
        });
    }
});

/**
 * GET /api/bookings/today-checkout
 * 查詢今日退房訂單清單
 */
router.get('/today-checkout', async (req, res) => {
    try {
        const pool = db.getPool();
        const connection = await pool.getConnection();

        try {
            const result = await connection.execute(`
                SELECT 
                    TRIM(om.IKEY) as booking_id,
                    om.CUST_NAM as guest_name,
                    om.CONTACT1_RMK as contact_phone,
                    TO_CHAR(om.CI_DAT, 'YYYY-MM-DD') as check_in_date,
                    TO_CHAR(om.CO_DAT, 'YYYY-MM-DD') as check_out_date,
                    om.DAYS as nights,
                    om.ORDER_STA as status_code
                FROM GDWUUKT.ORDER_MN om
                WHERE TRUNC(om.CO_DAT) = TRUNC(SYSDATE)
                  AND om.ORDER_STA IN ('I', 'D')
                ORDER BY om.CO_DAT
            `);

            // 狀態碼轉換
            // 使用共用狀態碼對照

            const bookings = await Promise.all(result.rows.map(async row => {
                const bookingId = row[0];

                // 使用統一的狀態判斷函數 (DRY)
                let { statusCode, statusName } = await getEffectiveStatus(connection, bookingId, row[6]);

                // 特殊處理：今日退房清單中，如果還是 I (已入住)，顯示為 "待退房"
                if (statusCode === 'I') statusName = '待退房';

                return {
                    booking_id: bookingId,
                    guest_name: row[1],
                    contact_phone: row[2],
                    check_in_date: row[3],
                    check_out_date: row[4],
                    nights: row[5],
                    status_code: statusCode,
                    status_name: statusName
                };
            }));

            res.json({
                success: true,
                data: bookings,
                count: bookings.length,
                date: new Date().toISOString().split('T')[0]
            });

        } finally {
            await connection.close();
        }

    } catch (err) {
        console.error('查詢今日退房失敗：', err);
        res.status(500).json({
            success: false,
            error: {
                code: 'DATABASE_ERROR',
                message: '查詢今日退房時發生錯誤'
            }
        });
    }
});
/**
 * GET /api/bookings/tomorrow-checkin
 * 查詢明日入住訂單清單
 */
router.get('/tomorrow-checkin', async (req, res) => {
    try {
        const pool = db.getPool();
        const connection = await pool.getConnection();

        try {
            // 使用共用函數查詢 (DRY)
            const bookings = await getCheckinBookings(connection, 1, "'O','N','R'");

            // 計算明天日期
            const tomorrow = new Date(Date.now() + 86400000).toISOString().split('T')[0];

            res.json({
                success: true,
                data: bookings,
                count: bookings.length,
                date: tomorrow
            });

        } finally {
            await connection.close();
        }

    } catch (err) {
        console.error('查詢明日入住失敗：', err);
        res.status(500).json({
            success: false,
            error: {
                code: 'DATABASE_ERROR',
                message: '查詢明日入住時發生錯誤'
            }
        });
    }
});


/**
 * GET /api/bookings/:booking_id
 * 查詢單一訂單詳細資訊
 */
router.get('/:booking_id', async (req, res) => {
    try {
        const { booking_id } = req.params;

        const pool = db.getPool();
        const connection = await pool.getConnection();

        try {
            // 查詢訂單主檔
            const orderResult = await connection.execute(
                `SELECT 
           TRIM(om.IKEY) as booking_id,
           om.CUST_NAM as guest_name,
           om.CONTACT1_RMK as contact_phone,
           TO_CHAR(om.CI_DAT, 'YYYY-MM-DD') as check_in_date,
           TO_CHAR(om.CO_DAT, 'YYYY-MM-DD') as check_out_date,
           om.DAYS as nights,
           om.ORDER_STA as status_code,
           om.ORDER_RMK as remarks
         FROM GDWUUKT.ORDER_MN om
         WHERE TRIM(om.IKEY) = :booking_id`,
                { booking_id }
            );

            if (orderResult.rows.length === 0) {
                return res.status(404).json({
                    success: false,
                    error: {
                        code: 'NOT_FOUND',
                        message: `找不到訂單編號 ${booking_id}`
                    }
                });
            }

            const order = orderResult.rows[0];

            // 查詢訂單明細（房型）
            const roomResult = await connection.execute(
                `SELECT 
           od.ROOM_COD as room_type_code,
           rf.ROOM_NAM as room_type_name,
           od.ORDER_QNT as room_count,
           od.ADULT_QNT as adult_count,
           od.CHILD_QNT as child_count
         FROM GDWUUKT.ORDER_DT od
         LEFT JOIN GDWUUKT.ROOM_RF rf ON od.ROOM_COD = rf.ROOM_TYP
         WHERE TRIM(od.IKEY) = :booking_id
         ORDER BY od.IKEY_SEQ_NOS`,
                { booking_id }
            );

            const rooms = roomResult.rows.map(row => ({
                room_type_code: row[0],
                room_type_name: row[1],
                room_count: row[2],
                adult_count: row[3],
                child_count: row[4]
            }));

            // 使用統一的狀態判斷函數 (DRY)
            const { statusCode, statusName } = await getEffectiveStatus(connection, booking_id, order[6]);

            res.json({
                success: true,
                data: {
                    booking_id: order[0],
                    guest_name: order[1],
                    contact_phone: order[2],
                    check_in_date: order[3],
                    check_out_date: order[4],
                    nights: order[5],
                    status_code: statusCode,
                    remarks: order[7],
                    status_name: statusName,
                    rooms: rooms
                }
            });

        } finally {
            await connection.close();
        }

    } catch (err) {
        console.error('查詢訂單詳情失敗：', err);
        res.status(500).json({
            success: false,
            error: {
                code: 'DATABASE_ERROR',
                message: '查詢訂單詳情時發生錯誤'
            }
        });
    }
});


module.exports = router;
