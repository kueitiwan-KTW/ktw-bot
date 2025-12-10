/**
 * Oracle 資料庫連線測試
 * 
 * 此程式用於驗證能否成功連接到 PMS Oracle 資料庫
 */

require('dotenv').config();
const oracledb = require('oracledb');

// 初始化 Thick 模式以支持中文字符集
if (process.env.ORACLE_CLIENT_LIB_DIR) {
    try {
        oracledb.initOracleClient({ libDir: process.env.ORACLE_CLIENT_LIB_DIR });
    } catch (err) {
        // 已初始化或不需要初始化
    }
}

const dbConfig = {
    user: process.env.DB_USER || 'pms_api',
    password: process.env.DB_PASSWORD,
    connectString: process.env.DB_CONNECT_STRING || 'localhost:1521/gdwuukt'
};

async function testConnection() {
    let connection;

    try {
        console.log('🔌 正在連接 Oracle 資料庫...');
        console.log(`   帳號: ${dbConfig.user}`);
        console.log(`   連線字串: ${dbConfig.connectString}`);
        console.log('');

        // 嘗試連接
        connection = await oracledb.getConnection(dbConfig);

        console.log('✅ 連線成功！');
        console.log('');

        // 測試簡單查詢
        console.log('📊 測試查詢資料庫版本...');
        const result = await connection.execute(
            `SELECT BANNER FROM V$VERSION WHERE BANNER LIKE 'Oracle%'`
        );

        if (result.rows && result.rows.length > 0) {
            console.log(`   版本: ${result.rows[0][0]}`);
        }

        console.log('');
        console.log('🎉 POC 測試成功！資料庫連線沒問題。');
        console.log('');
        console.log('📝 下一步：');
        console.log('   1. 執行 npm run test-query 測試查詢訂單資料');
        console.log('   2. 執行 npm run test-api 測試完整 API 功能');

    } catch (err) {
        console.error('❌ 連線失敗：', err.message);
        console.error('');
        console.error('💡 可能的原因：');
        console.error('   1. 密碼錯誤 - 請檢查 .env 檔案中的 DB_PASSWORD');
        console.error('   2. 主機無法連線 - 請確認 gdwuukt-db01 是否可連線');
        console.error('   3. SID 錯誤 - 請確認 SID 是否為 gdwuukt');
        console.error('   4. 權限不足 - 請確認帳號有存取權限');
        console.error('');
        console.error('詳細錯誤：');
        console.error(err);

    } finally {
        // 關閉連線
        if (connection) {
            try {
                await connection.close();
                console.log('🔒 已關閉資料庫連線');
            } catch (err) {
                console.error('關閉連線時發生錯誤：', err.message);
            }
        }
    }
}

// 執行測試
testConnection();
