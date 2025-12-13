/**
 * 訂單相關路由
 */

const express = require('express');
const router = express.Router();
const db = require('../config/database');

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
            const statusMap = { 'O': '已確認', 'R': '預約中', 'C': '已取消', 'I': '已入住', 'D': '已取消', 'N': '新訂單' };

            const bookings = result.rows.map(row => ({
                booking_id: row[0],
                guest_name: row[1],
                contact_phone: row[2],
                check_in_date: row[3],
                check_out_date: row[4],
                nights: row[5],
                status_code: row[6],
                status_name: statusMap[row[6]] || '未知'
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
            const newLocal = `
                SELECT 
                    TRIM(om.IKEY) as booking_id,
                    TRIM(om.RVRESERVE_NOS) as ota_booking_id,
                    om.CUST_NAM as guest_name,
                    TRIM(om.GLAST_NAM) as guest_last_name,
                    TRIM(om.GFIRST_NAM) as guest_first_name,
                    om.CONTACT1_RMK as contact_phone,
                    TO_CHAR(om.CI_DAT, 'YYYY-MM-DD') as check_in_date,
                    TO_CHAR(om.CO_DAT, 'YYYY-MM-DD') as check_out_date,
                    om.DAYS as nights,
                    om.ORDER_STA as status_code,
                    om.ORDER_RMK as remarks,
                    om.ORDER_DEPOSIT as room_total
                FROM GDWUUKT.ORDER_MN om
                WHERE TRUNC(om.CI_DAT) = TRUNC(SYSDATE)
                  AND om.ORDER_STA IN ('O', 'I', 'N')
                ORDER BY om.CI_DAT
            `;
            const result = await connection.execute(newLocal);

            // 狀態碼轉換
            const statusMap = { 'O': '已確認', 'I': '已入住', 'N': '新訂單' };

            // 為每筆訂單查詢房型和房號
            const bookings = await Promise.all(result.rows.map(async row => {
                const bookingId = row[0];

                // 查詢房型明細
                const roomResult = await connection.execute(
                    `SELECT 
                        od.ROOM_COD as room_type_code,
                        rf.ROOM_NAM as room_type_name,
                        od.ORDER_QNT as room_count,
                        od.ADULT_QNT as adult_count,
                        od.CHILD_QNT as child_count
                     FROM GDWUUKT.ORDER_DT od
                     LEFT JOIN GDWUUKT.ROOM_RF rf ON od.ROOM_COD = rf.ROOM_TYP
                     WHERE TRIM(od.IKEY) = :booking_id`,
                    { booking_id: bookingId }
                );

                const rooms = roomResult.rows.map(r => ({
                    room_type_code: r[0],
                    room_type_name: r[1],
                    room_count: r[2],
                    adult_count: r[3],
                    child_count: r[4]
                }));

                // 查詢已分配的房號（從 ASSIGN_DT 表）
                let roomNumbers = [];
                try {
                    const roomNoResult = await connection.execute(
                        `SELECT DISTINCT TRIM(ROOM_NOS) as room_number
                         FROM GDWUUKT.ASSIGN_DT
                         WHERE TRIM(IKEY) = :booking_id
                           AND ROOM_NOS IS NOT NULL`,
                        { booking_id: bookingId }
                    );
                    roomNumbers = roomNoResult.rows.map(r => r[0]).filter(Boolean);
                } catch (err) {
                    console.log(`查詢房號失敗 (${bookingId}):`, err.message);
                }

                return {
                    booking_id: bookingId,
                    ota_booking_id: row[1] || '',
                    guest_name: row[2],
                    guest_last_name: row[3] || '',
                    guest_first_name: row[4] || '',
                    contact_phone: row[5],
                    check_in_date: row[6],
                    check_out_date: row[7],
                    nights: row[8],
                    status_code: row[9],
                    status_name: statusMap[row[9]] || '其他',
                    remarks: row[10],
                    room_total: row[11] || 0,
                    deposit_paid: 0,
                    rooms: rooms,
                    room_numbers: roomNumbers
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
            const statusMap = { 'I': '待退房', 'D': '已退房' };

            const bookings = result.rows.map(row => ({
                booking_id: row[0],
                guest_name: row[1],
                contact_phone: row[2],
                check_in_date: row[3],
                check_out_date: row[4],
                nights: row[5],
                status_code: row[6],
                status_name: statusMap[row[6]] || '其他'
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

            // 狀態碼轉換
            const statusMap = { 'O': '已確認', 'R': '預約中', 'C': '已取消', 'I': '已入住', 'D': '已取消', 'N': '新訂單' };

            res.json({
                success: true,
                data: {
                    booking_id: order[0],
                    guest_name: order[1],
                    contact_phone: order[2],
                    check_in_date: order[3],
                    check_out_date: order[4],
                    nights: order[5],
                    status_code: order[6],
                    remarks: order[7],
                    status_name: statusMap[order[6]] || '未知',
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
