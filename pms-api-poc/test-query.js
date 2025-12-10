/**
 * Oracle PMS 訂單查詢測試
 * 
 * 此程式用於驗證能否正確查詢訂單資料
 */

require('dotenv').config();
const oracledb = require('oracledb');

const dbConfig = {
    user: process.env.DB_USER || 'pms_api',
    password: process.env.DB_PASSWORD,
    connectString: process.env.DB_CONNECT_STRING || 'localhost:1521/gdwuukt'
};

async function testOrderQuery() {
    let connection;
    const testOrderId = process.env.TEST_ORDER_ID || '00150501';

    try {
        console.log('🔌 連接資料庫...');
        connection = await oracledb.getConnection(dbConfig);
        console.log('✅ 連線成功');
        console.log('');

        // 測試查詢訂單主檔
        console.log(`📋 查詢訂單編號: ${testOrderId}`);
        console.log('');

        const result = await connection.execute(
            `SELECT 
         om.IKEY as order_id,
         om.CUST_NAM as guest_name,
         om.CONTACT1_RMK as contact_phone,
         TO_CHAR(om.CI_DAT, 'YYYY-MM-DD') as check_in_date,
         TO_CHAR(om.CO_DAT, 'YYYY-MM-DD') as check_out_date,
         om.DAYS as nights,
         om.ORDER_STA as status,
         om.ORDER_RMK as remarks
       FROM GDWUUKT.ORDER_MN om
       WHERE om.IKEY = :order_id`,
            { order_id: testOrderId }
        );

        if (result.rows && result.rows.length > 0) {
            console.log('✅ 找到訂單資料：');
            console.log('');

            const [order] = result.rows;
            const [orderId, guestName, phone, checkIn, checkOut, nights, status, remarks] = order;

            console.log(`   訂單編號: ${orderId}`);
            console.log(`   訂房人: ${guestName || '（未填寫）'}`);
            console.log(`   聯絡電話: ${phone || '（未填寫）'}`);
            console.log(`   入住日期: ${checkIn}`);
            console.log(`   退房日期: ${checkOut}`);
            console.log(`   住宿天數: ${nights} 晚`);
            console.log(`   訂單狀態: ${status}`);
            console.log(`   備註: ${remarks || '（無）'}`);
            console.log('');

            // 查詢訂單明細（房型）
            console.log('📦 查詢房型資料...');
            const detailResult = await connection.execute(
                `SELECT 
           od.ROOM_COD as room_type_code,
           rf.ROOM_NAM as room_type_name,
           od.ORDER_QNT as room_count,
           od.ADULT_QNT as adult_count,
           od.CHILD_QNT as child_count
         FROM GDWUUKT.ORDER_DT od
         LEFT JOIN GDWUUKT.ROOM_RF rf ON od.ROOM_COD = rf.ROOM_TYP
         WHERE od.IKEY = :order_id
         ORDER BY od.IKEY_SEQ_NOS`,
                { order_id: testOrderId }
            );

            if (detailResult.rows && detailResult.rows.length > 0) {
                console.log('');
                detailResult.rows.forEach((room, index) => {
                    const [roomCode, roomName, roomCount, adultCount, childCount] = room;
                    console.log(`   房型 ${index + 1}:  ${roomName || roomCode}`);
                    console.log(`   房間數: ${roomCount} 間`);
                    console.log(`   成人數: ${adultCount} 人`);
                    console.log(`   兒童數: ${childCount} 人`);
                    if (index < detailResult.rows.length - 1) console.log('');
                });
            }

            console.log('');
            console.log('🎉 POC 驗證成功！');
            console.log('');
            console.log('✅ 驗證結果：');
            console.log('   1. ✓ 可以查詢訂單主檔資料');
            console.log('   2. ✓ 可以取得訂房人姓名');
            console.log('   3. ✓ 可以取得入住/退房日期');
            console.log('   4. ✓ 可以查詢房型資料');
            console.log('');
            console.log('📝 下一步：開發完整的 REST API');

        } else {
            console.log(`❌ 找不到訂單編號 ${testOrderId}`);
            console.log('');
            console.log('💡 請檢查：');
            console.log('   1. 訂單編號是否正確');
            console.log('   2. 資料表名稱是否為 TEST.ORDER_MN');
            console.log('   3. 嘗試修改 .env 中的 TEST_ORDER_ID');
        }

    } catch (err) {
        console.error('❌ 查詢失敗：', err.message);
        console.error('');
        console.error('詳細錯誤：');
        console.error(err);

    } finally {
        if (connection) {
            await connection.close();
            console.log('');
            console.log('🔒 已關閉資料庫連線');
        }
    }
}

// 執行測試
testOrderQuery();
