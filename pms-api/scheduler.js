/**
 * 自動清除過期暫存訂單
 * 每天凌晨 3:00 執行，清除未入住的過期訂單
 */

const cron = require('node-cron');
const fs = require('fs');
const path = require('path');

const DATA_DIR = path.join(__dirname, 'data');
const BOOKINGS_FILE = path.join(DATA_DIR, 'same_day_bookings.json');
const LOG_FILE = path.join(DATA_DIR, 'cleanup_log.json');

/**
 * 清除過期未入住的暫存訂單
 */
function cleanupExpiredBookings() {
    const now = new Date();
    const today = now.toISOString().slice(0, 10);

    console.log(`\n🧹 [${now.toISOString()}] 開始清除過期暫存訂單...`);

    if (!fs.existsSync(BOOKINGS_FILE)) {
        console.log('   沒有暫存訂單檔案，跳過清除');
        return;
    }

    let bookings = [];
    try {
        const content = fs.readFileSync(BOOKINGS_FILE, 'utf8');
        bookings = JSON.parse(content);
    } catch (e) {
        console.error('   讀取暫存訂單失敗：', e.message);
        return;
    }

    const originalCount = bookings.length;

    // 保留今日和已入住的訂單，清除其他
    const keepBookings = bookings.filter(b => {
        // 保留已入住的
        if (b.status === 'checked_in') return true;
        // 保留今日的未入住訂單
        if (b.check_in_date === today && b.status === 'pending') return true;
        // 其他都清除
        return false;
    });

    const removedCount = originalCount - keepBookings.length;

    // 記錄被清除的訂單
    const removedBookings = bookings.filter(b => {
        if (b.status === 'checked_in') return false;
        if (b.check_in_date === today && b.status === 'pending') return false;
        return true;
    });

    if (removedCount > 0) {
        // 儲存清除後的訂單
        fs.writeFileSync(BOOKINGS_FILE, JSON.stringify(keepBookings, null, 2), 'utf8');

        // 記錄清除日誌
        const logEntry = {
            timestamp: now.toISOString(),
            removed_count: removedCount,
            removed_orders: removedBookings.map(b => ({
                order_id: b.temp_order_id,
                guest_name: b.guest_name,
                check_in_date: b.check_in_date
            }))
        };

        // 讀取現有日誌
        let logs = [];
        if (fs.existsSync(LOG_FILE)) {
            try {
                logs = JSON.parse(fs.readFileSync(LOG_FILE, 'utf8'));
            } catch (e) {
                logs = [];
            }
        }
        logs.push(logEntry);

        // 只保留最近 30 天的日誌
        const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString();
        logs = logs.filter(l => l.timestamp > thirtyDaysAgo);

        fs.writeFileSync(LOG_FILE, JSON.stringify(logs, null, 2), 'utf8');

        console.log(`   ✅ 清除了 ${removedCount} 筆過期訂單`);
        removedBookings.forEach(b => {
            console.log(`      - ${b.temp_order_id}: ${b.guest_name} (${b.check_in_date})`);
        });
    } else {
        console.log('   沒有需要清除的過期訂單');
    }

    console.log(`   保留 ${keepBookings.length} 筆訂單`);
}

/**
 * 啟動排程任務
 */
function startScheduler() {
    // 每天凌晨 3:00 執行清除
    cron.schedule('0 3 * * *', () => {
        cleanupExpiredBookings();
    }, {
        timezone: 'Asia/Taipei'
    });

    console.log('📅 暫存訂單自動清除排程已啟動 (每天 03:00)');
}

// 導出函數供其他模組使用
module.exports = {
    cleanupExpiredBookings,
    startScheduler
};

// 如果直接執行此檔案，執行一次清除（用於測試）
if (require.main === module) {
    cleanupExpiredBookings();
}
