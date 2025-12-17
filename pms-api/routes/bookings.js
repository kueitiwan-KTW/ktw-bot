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
          CASE 
            WHEN LENGTH(TRIM(om.GALT_NAM)) > 0 THEN TRIM(om.GALT_NAM)
            WHEN LENGTH(TRIM(om.GLAST_NAM)) > 0 OR LENGTH(TRIM(om.GFIRST_NAM)) > 0 
              THEN TRIM(NVL(om.GLAST_NAM,'') || NVL(om.GFIRST_NAM,''))
            ELSE om.CUST_NAM
          END as guest_name,
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
                    CASE 
                      WHEN LENGTH(TRIM(om.GALT_NAM)) > 0 THEN TRIM(om.GALT_NAM)
                      WHEN LENGTH(TRIM(om.GLAST_NAM)) > 0 OR LENGTH(TRIM(om.GFIRST_NAM)) > 0 
                        THEN TRIM(NVL(om.GLAST_NAM,'') || NVL(om.GFIRST_NAM,''))
                      ELSE om.CUST_NAM
                    END as guest_name,
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
 * GET /api/bookings/test-write-permission
 * 測試 PMS 資料庫寫入權限（開發用）
 * 
 * 注意：此端點必須放在 /:booking_id 之前，否則會被通用路由攔截
 */
router.get('/test-write-permission', async (req, res) => {
    try {
        const pool = db.getPool();
        const connection = await pool.getConnection();
        const results = {
            timestamp: new Date().toISOString(),
            tests: []
        };

        try {
            // 測試 1: 查詢最大訂單號
            const maxKeyResult = await connection.execute(`
                SELECT MAX(TRIM(IKEY)) as max_ikey FROM GDWUUKT.ORDER_MN
            `);
            results.tests.push({
                name: '查詢最大訂單號',
                success: true,
                result: maxKeyResult.rows[0]?.[0] || 'N/A'
            });

            // 測試 2: 查詢 ORDER_MN 必填欄位
            const colsResult = await connection.execute(`
                SELECT COLUMN_NAME, DATA_TYPE, NULLABLE
                FROM ALL_TAB_COLUMNS 
                WHERE OWNER = 'GDWUUKT' AND TABLE_NAME = 'ORDER_MN' AND NULLABLE = 'N'
                ORDER BY COLUMN_ID
            `);
            results.tests.push({
                name: 'ORDER_MN 必填欄位',
                success: true,
                result: colsResult.rows.map(r => `${r[0]} (${r[1]})`)
            });

            // 測試 3: 嘗試 INSERT (會立即 ROLLBACK)
            try {
                const testOrderId = 'TEST99999';
                await connection.execute(`
                    INSERT INTO GDWUUKT.ORDER_MN (IKEY, CI_DAT, CO_DAT, ORDER_STA, CUST_NAM)
                    VALUES (:ikey, SYSDATE, SYSDATE+1, 'N', 'TEST_WRITE_BOT')
                `, { ikey: testOrderId });

                await connection.rollback();
                results.tests.push({
                    name: 'INSERT 測試',
                    success: true,
                    result: '✅ 有寫入權限！(已 ROLLBACK)'
                });
                results.has_write_permission = true;
            } catch (insertErr) {
                results.tests.push({
                    name: 'INSERT 測試',
                    success: false,
                    error: insertErr.message
                });
                results.has_write_permission = false;
            }

            res.json({
                success: true,
                data: results
            });

        } finally {
            await connection.close();
        }

    } catch (err) {
        console.error('測試寫入權限失敗：', err);
        res.status(500).json({
            success: false,
            error: {
                code: 'TEST_ERROR',
                message: err.message
            }
        });
    }
});


/**
 * GET /api/bookings/same-day-list
 * 查詢當日暫存訂單列表（供 Admin Dashboard 使用）
 * 自動比對 PMS 今日入住：如果同名同電話則不顯示（表示已 KEY 進 PMS）
 * 
 * 注意：此端點必須放在 /:booking_id 之前，否則會被通用路由攔截
 */
router.get('/same-day-list', async (req, res) => {
    try {
        const dataDir = path.join(__dirname, '..', 'data');
        const filePath = path.join(dataDir, 'same_day_bookings.json');

        let bookings = [];
        if (fs.existsSync(filePath)) {
            try {
                const content = fs.readFileSync(filePath, 'utf8');
                bookings = JSON.parse(content);
            } catch (e) {
                bookings = [];
            }
        }

        // 只回傳今日的訂單
        const today = new Date().toISOString().slice(0, 10);
        let todayBookings = bookings.filter(b => b.check_in_date === today);

        // 嘗試取得 PMS 今日入住名單進行比對
        let pmsCheckins = [];
        try {
            const pool = db.getPool();
            const connection = await pool.getConnection();
            try {
                pmsCheckins = await getCheckinBookings(connection, 0, "'O','I','N'");
            } finally {
                await connection.close();
            }
        } catch (pmsErr) {
            console.log('無法取得 PMS 入住名單，跳過比對：', pmsErr.message);
        }

        // 比對邏輯：如果 PMS 今日入住中有同名同電話的訂單，自動標記為已 KEY
        if (pmsCheckins.length > 0) {
            // 建立 PMS 入住名單的姓名+電話組合集合
            const pmsNamePhoneSet = new Set();
            pmsCheckins.forEach(p => {
                // PMS 資料可能是 LAST_NAM + FIRST_NAM 或 guest_name
                const pmsName = (p.GLAST_NAM || '') + (p.GFIRST_NAM || '') || p.guest_name || '';
                const pmsPhone = (p.PHONE || p.phone || '').replace(/[-\s]/g, '');
                if (pmsName && pmsPhone) {
                    pmsNamePhoneSet.add(`${pmsName.toLowerCase()}|${pmsPhone}`);
                }
            });

            // 過濾暫存訂單：如果 PMS 中有同名同電話，自動標記為 checked_in
            todayBookings = todayBookings.map(b => {
                if (b.status === 'pending' || b.status === 'interrupted') {
                    const bookingName = (b.guest_name || '').toLowerCase();
                    const bookingPhone = (b.phone || '').replace(/[-\s]/g, '');
                    const key = `${bookingName}|${bookingPhone}`;

                    if (pmsNamePhoneSet.has(key)) {
                        // 自動標記為已 KEY，不顯示在待處理列表
                        return { ...b, status: 'checked_in', auto_matched: true };
                    }
                }
                return b;
            });

            // 更新檔案中的狀態（自動標記的訂單）
            const autoMatchedIds = todayBookings
                .filter(b => b.auto_matched)
                .map(b => b.item_id || b.temp_order_id);

            if (autoMatchedIds.length > 0) {
                const updatedBookings = bookings.map(b => {
                    const id = b.item_id || b.temp_order_id;
                    if (autoMatchedIds.includes(id)) {
                        return { ...b, status: 'checked_in', auto_matched: true };
                    }
                    return b;
                });
                fs.writeFileSync(filePath, JSON.stringify(updatedBookings, null, 2), 'utf8');
                console.log(`✅ 自動比對 PMS：${autoMatchedIds.length} 筆訂單已標記為已 KEY`);
            }
        }

        // 過濾掉已入住的，只顯示待處理的
        const pendingBookings = todayBookings.filter(b => b.status !== 'checked_in');

        res.json({
            success: true,
            data: {
                date: today,
                total: pendingBookings.length,
                bookings: pendingBookings.map(b => ({
                    order_id: b.order_id || b.temp_order_id,
                    item_id: b.item_id || b.temp_order_id,
                    room_type_code: b.room_type_code,
                    room_type_name: b.room_type_name,
                    room_count: b.room_count,
                    bed_type: b.bed_type,
                    special_requests: b.special_requests,
                    nights: b.nights,
                    guest_name: b.guest_name,
                    phone: b.phone,
                    arrival_time: b.arrival_time,
                    check_in_date: b.check_in_date,
                    check_out_date: b.check_out_date,
                    status: b.status,
                    created_at: b.created_at,
                    line_display_name: b.line_display_name
                }))
            }
        });

    } catch (err) {
        console.error('查詢暫存訂單失敗：', err);
        res.status(500).json({
            success: false,
            error: {
                code: 'READ_ERROR',
                message: '讀取暫存訂單時發生錯誤'
            }
        });
    }
});

/**
 * PATCH /api/bookings/same-day/:order_id/checkin
 * 標記暫存訂單為已 KEY（已入住）
 * 
 * 注意：此端點必須放在 /:booking_id 之前
 */
router.patch('/same-day/:order_id/checkin', async (req, res) => {
    try {
        const { order_id } = req.params;
        const dataDir = path.join(__dirname, '..', 'data');
        const filePath = path.join(dataDir, 'same_day_bookings.json');

        if (!fs.existsSync(filePath)) {
            return res.status(404).json({
                success: false,
                error: {
                    code: 'NOT_FOUND',
                    message: '找不到暫存訂單檔案'
                }
            });
        }

        let bookings = [];
        try {
            const content = fs.readFileSync(filePath, 'utf8');
            bookings = JSON.parse(content);
        } catch (e) {
            return res.status(500).json({
                success: false,
                error: {
                    code: 'READ_ERROR',
                    message: '讀取暫存訂單失敗'
                }
            });
        }

        const orderIndex = bookings.findIndex(b => b.temp_order_id === order_id || b.order_id === order_id);
        if (orderIndex === -1) {
            return res.status(404).json({
                success: false,
                error: {
                    code: 'NOT_FOUND',
                    message: `找不到訂單編號 ${order_id}`
                }
            });
        }

        bookings[orderIndex].status = 'checked_in';
        bookings[orderIndex].checked_in_at = new Date().toISOString();
        fs.writeFileSync(filePath, JSON.stringify(bookings, null, 2), 'utf8');

        console.log(`✅ 暫存訂單已標記為 KEY：${order_id}`);

        res.json({
            success: true,
            data: {
                order_id: order_id,
                status: 'checked_in',
                message: '已標記為已 KEY 單'
            }
        });

    } catch (err) {
        console.error('標記訂單失敗：', err);
        res.status(500).json({
            success: false,
            error: {
                code: 'UPDATE_ERROR',
                message: '更新訂單狀態時發生錯誤'
            }
        });
    }
});


/**
 * PATCH /api/bookings/same-day/:order_id/mismatch
 * 標記暫存訂單為匹配失敗（KEY 錯）
 */
router.patch('/same-day/:order_id/mismatch', async (req, res) => {
    try {
        const { order_id } = req.params;
        const dataDir = path.join(__dirname, '..', 'data');
        const filePath = path.join(dataDir, 'same_day_bookings.json');

        if (!fs.existsSync(filePath)) {
            return res.status(404).json({
                success: false,
                error: { code: 'NOT_FOUND', message: '找不到暫存訂單檔案' }
            });
        }

        let bookings = [];
        try {
            const content = fs.readFileSync(filePath, 'utf8');
            bookings = JSON.parse(content);
        } catch (e) {
            return res.status(500).json({
                success: false,
                error: { code: 'READ_ERROR', message: '讀取暫存訂單失敗' }
            });
        }

        const orderIndex = bookings.findIndex(b => b.temp_order_id === order_id || b.order_id === order_id || b.item_id === order_id);
        if (orderIndex === -1) {
            return res.status(404).json({
                success: false,
                error: { code: 'NOT_FOUND', message: `找不到訂單編號 ${order_id}` }
            });
        }

        bookings[orderIndex].status = 'mismatch';
        bookings[orderIndex].mismatch_at = new Date().toISOString();
        fs.writeFileSync(filePath, JSON.stringify(bookings, null, 2), 'utf8');

        console.log(`⚠️ 暫存訂單標記為 KEY 錯：${order_id}`);

        res.json({
            success: true,
            data: {
                order_id: order_id,
                status: 'mismatch',
                message: 'PMS 匹配失敗，已標記為 KEY 錯'
            }
        });

    } catch (err) {
        console.error('標記 mismatch 失敗：', err);
        res.status(500).json({
            success: false,
            error: { code: 'UPDATE_ERROR', message: '更新訂單狀態時發生錯誤' }
        });
    }
});

/**
 * PATCH /api/bookings/same-day/:order_id/cancel
 * 取消暫存訂單（標記為取消，保留 LOG）
 */
router.patch('/same-day/:order_id/cancel', async (req, res) => {
    try {
        const { order_id } = req.params;
        const dataDir = path.join(__dirname, '..', 'data');
        const filePath = path.join(dataDir, 'same_day_bookings.json');

        if (!fs.existsSync(filePath)) {
            return res.status(404).json({
                success: false,
                error: {
                    code: 'NOT_FOUND',
                    message: '找不到暫存訂單檔案'
                }
            });
        }

        let bookings = [];
        try {
            const content = fs.readFileSync(filePath, 'utf8');
            bookings = JSON.parse(content);
        } catch (e) {
            return res.status(500).json({
                success: false,
                error: {
                    code: 'READ_ERROR',
                    message: '讀取暫存訂單失敗'
                }
            });
        }

        const orderIndex = bookings.findIndex(b => b.temp_order_id === order_id || b.order_id === order_id);
        if (orderIndex === -1) {
            return res.status(404).json({
                success: false,
                error: {
                    code: 'NOT_FOUND',
                    message: `找不到訂單編號 ${order_id}`
                }
            });
        }

        // 標記為取消，保留記錄
        bookings[orderIndex].status = 'cancelled';
        bookings[orderIndex].cancelled_at = new Date().toISOString();
        fs.writeFileSync(filePath, JSON.stringify(bookings, null, 2), 'utf8');

        console.log(`❌ 暫存訂單已取消：${order_id}`);

        res.json({
            success: true,
            data: {
                order_id: order_id,
                status: 'cancelled',
                message: '已標記為取消'
            }
        });

    } catch (err) {
        console.error('取消訂單失敗：', err);
        res.status(500).json({
            success: false,
            error: {
                code: 'CANCEL_ERROR',
                message: '取消訂單時發生錯誤'
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
           CASE 
             WHEN LENGTH(TRIM(om.GALT_NAM)) > 0 THEN TRIM(om.GALT_NAM)
             WHEN LENGTH(TRIM(om.GLAST_NAM)) > 0 OR LENGTH(TRIM(om.GFIRST_NAM)) > 0 
               THEN TRIM(NVL(om.GLAST_NAM,'') || NVL(om.GFIRST_NAM,''))
             ELSE om.CUST_NAM
           END as guest_name,
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

const fs = require('fs');
const path = require('path');

/**
 * POST /api/bookings/same-day
 * 建立當日預訂訂單（暫存方案）
 * 由於 PMS 資料庫寫入權限尚未確認，先暫存至本地 JSON 檔案
 * 生成臨時訂單編號供追蹤
 */
router.post('/same-day', async (req, res) => {
    try {
        const {
            room_type_code,
            room_type_name,
            room_count,
            nights,
            guest_name,
            phone,
            arrival_time,
            line_user_id,
            line_display_name
        } = req.body;

        // 驗證必填欄位
        if (!room_type_code || !room_count || !guest_name || !phone || !arrival_time) {
            return res.status(400).json({
                success: false,
                error: {
                    code: 'MISSING_PARAMETER',
                    message: '請提供房型、間數、姓名、電話、抵達時間'
                }
            });
        }

        // 生成臨時訂單編號：SD + 日期 + 序號
        const today = new Date();
        const dateStr = today.toISOString().slice(0, 10).replace(/-/g, '');
        const timeStr = today.toTimeString().slice(0, 8).replace(/:/g, '');

        // 支援客戶端傳送 order_id（多房型訂單共用）和 item_id（每房型獨立）
        // 預設格式：WI+月日時分
        const orderId = req.body.order_id || `WI${dateStr.slice(4)}${timeStr.slice(0, 4)}`;
        const itemId = req.body.item_id || orderId;  // 如果沒有 item_id，則使用 order_id（單房型訂單）

        // 計算入住與退房日期
        const checkInDate = today.toISOString().slice(0, 10);
        const checkOutDate = new Date(today.getTime() + (nights || 1) * 24 * 60 * 60 * 1000)
            .toISOString().slice(0, 10);

        // 建立訂單資料
        const orderData = {
            order_id: orderId,              // 大訂單 ID（多房型共用）
            item_id: itemId,                // 小項目 ID（每房型獨立，用於取消/操作）
            temp_order_id: itemId,          // 保留向後相容
            room_type_code,
            room_type_name: room_type_name || room_type_code,
            room_count: parseInt(room_count) || 1,
            bed_type: req.body.bed_type || null,      // 床型
            special_requests: req.body.special_requests || null,  // 客人特殊需求
            nights: parseInt(nights) || 1,
            guest_name,
            phone,
            arrival_time,
            check_in_date: checkInDate,
            check_out_date: checkOutDate,
            line_user_id: line_user_id || null,
            line_display_name: line_display_name || null,
            status: req.body.status || 'pending',  // 支援 pending/interrupted
            created_at: today.toISOString(),
            notes: req.body.status === 'interrupted' ? '💔 預約中斷' : '⚠️ 當日預訂 - 免訂金 - 需客人準時抵達'
        };

        // 暫存至 JSON 檔案（PMS 整合後可改為直接寫入資料庫）
        const dataDir = path.join(__dirname, '..', 'data');
        const filePath = path.join(dataDir, 'same_day_bookings.json');

        // 確保目錄存在
        if (!fs.existsSync(dataDir)) {
            fs.mkdirSync(dataDir, { recursive: true });
        }

        // 讀取現有資料
        let bookings = [];
        if (fs.existsSync(filePath)) {
            try {
                const content = fs.readFileSync(filePath, 'utf8');
                bookings = JSON.parse(content);
            } catch (e) {
                bookings = [];
            }
        }

        // 新增訂單
        bookings.push(orderData);
        fs.writeFileSync(filePath, JSON.stringify(bookings, null, 2), 'utf8');

        console.log(`📝 當日預訂已建立：${itemId} - ${guest_name} - ${room_type_name} x${room_count}`);

        res.json({
            success: true,
            data: {
                order_id: orderId,
                guest_name,
                room_type_name: orderData.room_type_name,
                room_count: orderData.room_count,
                nights: orderData.nights,
                check_in_date: checkInDate,
                check_out_date: checkOutDate,
                arrival_time,
                status: 'pending',
                message: '訂單已成立，請準時抵達辦理入住'
            }
        });

    } catch (err) {
        console.error('建立當日預訂失敗：', err);
        res.status(500).json({
            success: false,
            error: {
                code: 'CREATE_ERROR',
                message: '建立訂單時發生錯誤，請稍後再試或聯繫櫃檯'
            }
        });
    }
});

module.exports = router;


