/**
 * 訂單查詢輔助函數
 * 提供共用的資料庫查詢邏輯
 */

/**
 * 訂單狀態碼對照表（共用定義）
 */
const STATUS_MAP = {
    'O': '已確認',
    'I': '已入住',
    'N': '新訂單',
    'R': '預約中',
    'D': '已取消',
    'C': '已取消',
    'S': 'NO-SHOW',
    'CO': '已退房'
};

/**
 * 取得狀態名稱
 * @param {string} statusCode - 狀態碼
 * @returns {string} 狀態名稱
 */
function getStatusName(statusCode) {
    return STATUS_MAP[statusCode] || '未知';
}

/**
 * 查詢訂單的房價總額（從 ORDER_DT.RENT_AMT 加總）
 * @param {Object} connection - 資料庫連線
 * @param {string} bookingId - 訂單編號
 * @returns {Promise<number>} 房價總額
 */
async function getRoomTotal(connection, bookingId) {
    try {
        const result = await connection.execute(
            `SELECT NVL(SUM(RENT_AMT), 0) as total
             FROM GDWUUKT.ORDER_DT
             WHERE TRIM(IKEY) = :booking_id`,
            { booking_id: bookingId }
        );
        return result.rows[0] ? result.rows[0][0] : 0;
    } catch (err) {
        console.log(`查詢房價總額失敗 (${bookingId}):`, err.message);
        return 0;
    }
}

/**
 * 查詢訂單的已付訂金（從 DEPOSIT_DT.USE_AMT 加總正數金額）
 * @param {Object} connection - 資料庫連線
 * @param {string} bookingId - 訂單編號
 * @returns {Promise<number>} 已付訂金
 */
async function getDepositPaid(connection, bookingId) {
    try {
        // 先取得訂金單號
        const depositNosResult = await connection.execute(
            `SELECT DEPOSIT_NOS FROM GDWUUKT.ORDER_MN WHERE TRIM(IKEY) = :booking_id`,
            { booking_id: bookingId }
        );

        if (!depositNosResult.rows[0] || !depositNosResult.rows[0][0]) {
            return 0;
        }

        const depositNos = depositNosResult.rows[0][0];

        // 查詢訂金明細（只取正數，負數是沖銷）
        const result = await connection.execute(
            `SELECT NVL(SUM(USE_AMT), 0) as total
             FROM GDWUUKT.DEPOSIT_DT
             WHERE DEPOSIT_NOS = :deposit_nos
               AND USE_AMT > 0`,
            { deposit_nos: depositNos }
        );

        return result.rows[0] ? result.rows[0][0] : 0;
    } catch (err) {
        console.log(`查詢已付訂金失敗 (${bookingId}):`, err.message);
        return 0;
    }
}

/**
 * 查詢訂單的房型明細
 * @param {Object} connection - 資料庫連線
 * @param {string} bookingId - 訂單編號
 * @returns {Promise<Array>} 房型列表
 */
async function getRoomDetails(connection, bookingId) {
    try {
        const result = await connection.execute(
            `SELECT 
                od.ROOM_COD as room_type_code,
                rf.ROOM_NAM as room_type_name,
                od.ORDER_QNT as room_count,
                od.ADULT_QNT as adult_count,
                od.CHILD_QNT as child_count,
                od.RENT_AMT as rent_amount
             FROM GDWUUKT.ORDER_DT od
             LEFT JOIN GDWUUKT.ROOM_RF rf ON od.ROOM_COD = rf.ROOM_TYP
             WHERE TRIM(od.IKEY) = :booking_id`,
            { booking_id: bookingId }
        );

        return result.rows.map(r => ({
            room_type_code: r[0],
            room_type_name: r[1],
            room_count: r[2],
            adult_count: r[3],
            child_count: r[4],
            rent_amount: r[5] || 0
        }));
    } catch (err) {
        console.log(`查詢房型明細失敗 (${bookingId}):`, err.message);
        return [];
    }
}

/**
 * 查詢訂單的已分配房號
 * @param {Object} connection - 資料庫連線
 * @param {string} bookingId - 訂單編號
 * @returns {Promise<Array>} 房號列表
 */
async function getRoomNumbers(connection, bookingId) {
    try {
        const result = await connection.execute(
            `SELECT DISTINCT TRIM(ROOM_NOS) as room_number
             FROM GDWUUKT.ASSIGN_DT
             WHERE TRIM(IKEY) = :booking_id
               AND ROOM_NOS IS NOT NULL`,
            { booking_id: bookingId }
        );
        return result.rows.map(r => r[0]).filter(Boolean);
    } catch (err) {
        console.log(`查詢房號失敗 (${bookingId}):`, err.message);
        return [];
    }
}

/**
 * 查詢訂單的房間狀態 (取第一間房)
 * @param {Object} connection - 資料庫連線
 * @param {string} bookingId - 訂單編號
 * @returns {Promise<string>} 房間狀態代碼 (V, R, O...)
 */
async function getRoomStatus(connection, bookingId) {
    try {
        // 先找分配的房號，再找該房號的狀態
        // 注意：可能會有多間房，這裡只取第一間的狀態作為代表
        const result = await connection.execute(
            `SELECT rm.ROOM_STA 
             FROM GDWUUKT.ASSIGN_DT ad
             JOIN GDWUUKT.ROOM_MN rm ON TRIM(ad.ROOM_NOS) = TRIM(rm.ROOM_NOS)
             WHERE TRIM(ad.IKEY) = :booking_id
               AND ROWNUM = 1`,
            { booking_id: bookingId }
        );
        return result.rows[0] ? result.rows[0][0] : null;
    } catch (err) {
        console.log(`查詢房間狀態失敗 (${bookingId}):`, err.message);
        return null;
    }
}

/**
 * 查詢訂單的入住/退房狀態 (來自 ASSIGN_DT.STATUS_COD)
 * 換房邏輯：如果有任何一間房是 C/I 或 CHGROOMC/I，表示客人仍在住
 * @param {Object} connection - 資料庫連線
 * @param {string} bookingId - 訂單編號
 * @returns {Promise<string>} 狀態代碼 ('C/I' = 已入住, 'C/O' = 已退房, 'CHGROOMC/I' = 換房入住中)
 */
async function getAssignStatus(connection, bookingId) {
    try {
        // 查詢所有房間狀態，優先判斷是否有仍在入住的房間
        const result = await connection.execute(
            `SELECT TRIM(STATUS_COD) 
             FROM GDWUUKT.ASSIGN_DT 
             WHERE TRIM(IKEY) = :booking_id
             ORDER BY BEGIN_DAT DESC`,
            { booking_id: bookingId }
        );
        
        if (!result.rows || result.rows.length === 0) {
            return null;
        }
        
        // 收集所有狀態
        const statuses = result.rows.map(r => r[0]);
        
        // 優先級：如果有任何入住中狀態（C/I 或 CHGROOMC/I），表示仍在住
        const hasCheckedIn = statuses.some(s => s && (s.includes('C/I') && !s.startsWith('C/O')));
        if (hasCheckedIn) {
            // 返回換房入住狀態（如果有 CHGROOMC/I）或普通入住狀態
            const roomChangeStatus = statuses.find(s => s && s.includes('CHGROOM'));
            return roomChangeStatus || 'C/I';
        }
        
        // 如果所有房間都是 C/O，則已退房
        const allCheckedOut = statuses.every(s => s && s === 'C/O');
        if (allCheckedOut) {
            return 'C/O';
        }
        
        // 返回最新狀態
        return statuses[0];
    } catch (err) {
        console.log(`查詢入住退房狀態失敗 (${bookingId}):`, err.message);
        return null;
    }
}

/**
 * 取得有效的訂單狀態碼 (DRY 原則：統一判斷退房邏輯)
 * 換房處理：CHGROOMC/I 表示換房後仍在入住，不應標記為已退房
 * @param {Object} connection - 資料庫連線
 * @param {string} bookingId - 訂單編號
 * @param {string} originalStatusCode - 原始訂單狀態碼
 * @returns {Promise<{statusCode: string, statusName: string}>} 有效狀態碼及名稱
 */
async function getEffectiveStatus(connection, bookingId, originalStatusCode) {
    const assignStatus = await getAssignStatus(connection, bookingId);

    let statusCode = originalStatusCode;
    
    if (assignStatus) {
        // 換房入住中或普通入住中：保持「已入住」狀態
        if (assignStatus.includes('C/I') && !assignStatus.startsWith('C/O')) {
            statusCode = 'I';  // 已入住
        }
        // 純 C/O（所有房間都退出）：覆蓋為「已退房」
        else if (assignStatus === 'C/O') {
            statusCode = 'CO';  // 已退房
        }
    }

    return {
        statusCode: statusCode,
        statusName: getStatusName(statusCode)
    };
}
/**
 * 查詢入住訂單清單（共用函數 - DRY 原則）
 * @param {Object} connection - 資料庫連線
 * @param {number} dateOffset - 日期偏移量（0=今日, -1=昨日, 1=明日）
 * @param {string} statusFilter - 狀態篩選（如 "'O','I','N'" ）
 * @returns {Promise<Array>} 訂單清單
 */
async function getCheckinBookings(connection, dateOffset, statusFilter) {
    // 主查詢 - 只查 ORDER_MN 避免重複，guest 資料用子查詢取第一筆
    const sql = `
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
            (SELECT TRIM(ALT_NAM) FROM GDWUUKT.GUEST_MN WHERE TRIM(IKEY) = TRIM(om.IKEY) AND ROWNUM = 1) as registered_name,
            (SELECT TRIM(ID_COD) FROM GDWUUKT.GUEST_MN WHERE TRIM(IKEY) = TRIM(om.IKEY) AND ROWNUM = 1) as id_number
        FROM GDWUUKT.ORDER_MN om
        WHERE TRUNC(om.CI_DAT) = TRUNC(SYSDATE + :dateOffset)
          AND om.ORDER_STA IN (${statusFilter})
        ORDER BY om.CI_DAT
    `;

    const result = await connection.execute(sql, { dateOffset });

    // 為每筆訂單查詢房型、房號、金額（使用共用輔助函數）
    const bookings = await Promise.all(result.rows.map(async row => {
        const bookingId = row[0];

        // 使用輔助函數查詢相關資料
        const [rooms, roomNumbers, roomTotal, depositPaid] = await Promise.all([
            getRoomDetails(connection, bookingId),
            getRoomNumbers(connection, bookingId),
            getRoomTotal(connection, bookingId),
            getDepositPaid(connection, bookingId)
        ]);

        // 使用統一的狀態判斷函數 (DRY)
        const { statusCode, statusName } = await getEffectiveStatus(connection, bookingId, row[9]);

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
            status_code: statusCode,
            status_name: statusName,
            remarks: row[10],
            room_total: roomTotal,
            registered_name: row[11] || '',
            id_number: row[12] || '',
            deposit_paid: depositPaid,
            rooms: rooms,
            room_numbers: roomNumbers
        };
    }));

    return bookings;
}

module.exports = {
    STATUS_MAP,
    getStatusName,
    getRoomTotal,
    getDepositPaid,
    getRoomDetails,
    getRoomNumbers,
    getRoomStatus,
    getAssignStatus,
    getEffectiveStatus,
    getCheckinBookings
};
