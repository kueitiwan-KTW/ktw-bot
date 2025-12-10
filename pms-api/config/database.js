/**
 * Oracle 資料庫連線配置
 */

require('dotenv').config();
const oracledb = require('oracledb');

// 初始化 Oracle Client（Thick 模式以支持中文字符集）
if (process.env.ORACLE_CLIENT_LIB_DIR) {
    try {
        oracledb.initOracleClient({ libDir: process.env.ORACLE_CLIENT_LIB_DIR });
        console.log('✅ Oracle Client 初始化成功（Thick 模式）');
    } catch (err) {
        console.error('❌ Oracle Client 初始化失敗：', err.message);
    }
}

// 資料庫連線配置
const dbConfig = {
    user: process.env.DB_USER,
    password: process.env.DB_PASSWORD,
    connectString: process.env.DB_CONNECT_STRING,
    poolMin: 2,
    poolMax: 10,
    poolIncrement: 1
};

// 創建連線池
let pool;

async function initialize() {
    try {
        pool = await oracledb.createPool(dbConfig);
        console.log('✅ Oracle 連線池建立成功');
    } catch (err) {
        console.error('❌ 連線池建立失敗：', err.message);
        throw err;
    }
}

async function close() {
    if (pool) {
        try {
            await pool.close(10);
            console.log('✅ 連線池已關閉');
        } catch (err) {
            console.error('❌ 關閉連線池時發生錯誤：', err.message);
        }
    }
}

function getPool() {
    return pool;
}

module.exports = {
    initialize,
    close,
    getPool
};
