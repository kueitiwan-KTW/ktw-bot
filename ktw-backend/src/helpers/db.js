import sqlite3 from 'sqlite3';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { existsSync, mkdirSync } from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// 確保 data 目錄存在
const DATA_DIR = join(__dirname, '../../data');
if (!existsSync(DATA_DIR)) {
    mkdirSync(DATA_DIR, { recursive: true });
}

const DB_PATH = join(DATA_DIR, 'ktw_supplements.db');

const db = new sqlite3.Database(DB_PATH, (err) => {
    if (err) {
        console.error('❌ 無法開啟 SQLite 資料庫:', err.message);
    } else {
        console.log('✅ 已連線到 SQLite 擴充資料庫');
        initDb();
    }
});

function initDb() {
    // 1. guest_supplements 表
    const supplementsSchema = `
        CREATE TABLE IF NOT EXISTS guest_supplements (
            booking_id TEXT PRIMARY KEY,
            confirmed_phone TEXT,
            arrival_time TEXT,
            staff_memo TEXT,
            ai_extracted_requests TEXT,
            line_name TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    `;

    // 2. 🔧 方案 D：user_order_mapping 表（用戶訂單關聯）
    const mappingSchema = `
        CREATE TABLE IF NOT EXISTS user_order_mapping (
            line_user_id TEXT NOT NULL,
            pms_id TEXT,
            ota_id TEXT,
            check_in_date TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (line_user_id, pms_id)
        );
    `;

    db.run(supplementsSchema, (err) => {
        if (err) {
            console.error('❌ 初始化 guest_supplements 失敗:', err.message);
        } else {
            console.log('✅ guest_supplements 資料表就緒');
            // 檢查是否需要新增 line_name 欄位 (遷移)
            db.all("PRAGMA table_info(guest_supplements)", (err, columns) => {
                if (!err && !columns.find(c => c.name === 'line_name')) {
                    db.run("ALTER TABLE guest_supplements ADD COLUMN line_name TEXT", (err) => {
                        if (!err) console.log('✅ 已升級資料庫：新增 line_name 欄位');
                        else console.error('❌ 升級資料庫失敗:', err.message);
                    });
                }
            });
        }
    });

    db.run(mappingSchema, (err) => {
        if (err) {
            console.error('❌ 初始化 user_order_mapping 失敗:', err.message);
        } else {
            console.log('✅ user_order_mapping 資料表就緒');
        }
    });
}


/**
 * 取得訂單擴充資料
 */
export function getSupplement(bookingId) {
    return new Promise((resolve, reject) => {
        db.get('SELECT * FROM guest_supplements WHERE booking_id = ?', [bookingId], (err, row) => {
            if (err) reject(err);
            else resolve(row);
        });
    });
}

/**
 * 批次取得訂單擴充資料
 */
export function getAllSupplements(bookingIds) {
    if (!bookingIds || bookingIds.length === 0) return Promise.resolve([]);
    const placeholders = bookingIds.map(() => '?').join(',');
    return new Promise((resolve, reject) => {
        db.all(`SELECT * FROM guest_supplements WHERE booking_id IN (${placeholders})`, bookingIds, (err, rows) => {
            if (err) reject(err);
            else resolve(rows);
        });
    });
}

/**
 * 更新或插入擴充資料
 */
export function updateSupplement(bookingId, data) {
    const { confirmed_phone, arrival_time, staff_memo, ai_extracted_requests, line_name } = data;
    const updatedAt = new Date().toISOString();

    return new Promise((resolve, reject) => {
        // 使用 REPLACE INTO (SQLite) 或 INSERT OR REPLACE
        const sql = `
            INSERT INTO guest_supplements (
                booking_id, confirmed_phone, arrival_time, staff_memo, ai_extracted_requests, line_name, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(booking_id) DO UPDATE SET
                confirmed_phone = COALESCE(excluded.confirmed_phone, confirmed_phone),
                arrival_time = COALESCE(excluded.arrival_time, arrival_time),
                staff_memo = COALESCE(excluded.staff_memo, staff_memo),
                ai_extracted_requests = COALESCE(excluded.ai_extracted_requests, ai_extracted_requests),
                line_name = COALESCE(excluded.line_name, line_name),
                updated_at = excluded.updated_at
        `;

        db.run(sql, [bookingId, confirmed_phone, arrival_time, staff_memo, ai_extracted_requests, line_name, updatedAt], function (err) {
            if (err) reject(err);
            else resolve({ changes: this.changes });
        });
    });
}

// ============================================
// Bot Session 持久化 (對話狀態儲存)
// ============================================

/**
 * 初始化 bot_sessions 資料表
 */
function initBotSessionsTable() {
    const schema = `
        CREATE TABLE IF NOT EXISTS bot_sessions (
            user_id TEXT PRIMARY KEY,
            handler_type TEXT,
            state TEXT,
            data TEXT,
            pending_intent TEXT,
            pending_intent_message TEXT,
            created_at DATETIME,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    `;
    db.run(schema, (err) => {
        if (err) {
            console.error('❌ 初始化 bot_sessions 資料表失敗:', err.message);
        } else {
            console.log('✅ bot_sessions 資料表就緒');
        }
    });
}

// 在資料庫連線後初始化
setTimeout(initBotSessionsTable, 500);

// ============================================
// VIP 用戶管理 (雙層架構: guest + internal)
// ============================================

/**
 * 初始化 vip_users 資料表
 */
function initVipUsersTable() {
    const schema = `
        CREATE TABLE IF NOT EXISTS vip_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            line_user_id TEXT UNIQUE NOT NULL,
            display_name TEXT,
            vip_type TEXT NOT NULL DEFAULT 'guest',
            vip_level INTEGER DEFAULT 1,
            role TEXT,
            permissions TEXT,
            note TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    `;
    db.run(schema, (err) => {
        if (err) {
            console.error('❌ 初始化 vip_users 資料表失敗:', err.message);
        } else {
            console.log('✅ vip_users 資料表就緒');
        }
    });
}

// 延遲初始化 VIP 表
setTimeout(initVipUsersTable, 600);

/**
 * 取得所有 VIP 用戶
 * @returns {Promise<Array>}
 */
export function getAllVipUsers() {
    return new Promise((resolve, reject) => {
        db.all('SELECT * FROM vip_users ORDER BY vip_type, vip_level DESC', (err, rows) => {
            if (err) reject(err);
            else resolve(rows || []);
        });
    });
}

/**
 * 查詢用戶 VIP 狀態
 * @param {string} userId - LINE User ID
 * @returns {Promise<Object|null>}
 */
export function getVipUser(userId) {
    return new Promise((resolve, reject) => {
        db.get('SELECT * FROM vip_users WHERE line_user_id = ?', [userId], (err, row) => {
            if (err) reject(err);
            else if (row) {
                // 解析 permissions JSON
                try {
                    row.permissions = row.permissions ? JSON.parse(row.permissions) : [];
                } catch {
                    row.permissions = [];
                }
                resolve(row);
            } else {
                resolve(null);
            }
        });
    });
}

/**
 * 新增 VIP 用戶
 * @param {Object} data - VIP 資料
 */
export function addVipUser(data) {
    const { line_user_id, display_name, vip_type, vip_level, role, permissions, note } = data;
    const now = new Date().toISOString();
    const permissionsJson = permissions ? JSON.stringify(permissions) : null;

    return new Promise((resolve, reject) => {
        const sql = `
            INSERT INTO vip_users (
                line_user_id, display_name, vip_type, vip_level, role, permissions, note, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(line_user_id) DO UPDATE SET
                display_name = COALESCE(excluded.display_name, display_name),
                vip_type = excluded.vip_type,
                vip_level = excluded.vip_level,
                role = excluded.role,
                permissions = excluded.permissions,
                note = COALESCE(excluded.note, note),
                updated_at = excluded.updated_at
        `;

        db.run(sql, [
            line_user_id, display_name, vip_type || 'guest', vip_level || 1,
            role, permissionsJson, note, now, now
        ], function (err) {
            if (err) reject(err);
            else resolve({ id: this.lastID, changes: this.changes });
        });
    });
}

/**
 * 刪除 VIP 用戶
 * @param {string} userId - LINE User ID
 */
export function deleteVipUser(userId) {
    return new Promise((resolve, reject) => {
        db.run('DELETE FROM vip_users WHERE line_user_id = ?', [userId], function (err) {
            if (err) reject(err);
            else resolve({ changes: this.changes });
        });
    });
}

/**
 * 取得 Bot Session
 * @param {string} userId - LINE 用戶 ID
 * @returns {Promise<Object|null>} session 資料
 */
export function getBotSession(userId) {
    return new Promise((resolve, reject) => {
        db.get('SELECT * FROM bot_sessions WHERE user_id = ?', [userId], (err, row) => {
            if (err) reject(err);
            else if (row) {
                // 解析 JSON 欄位
                try {
                    row.data = row.data ? JSON.parse(row.data) : {};
                } catch {
                    row.data = {};
                }
                resolve(row);
            } else {
                resolve(null);
            }
        });
    });
}

/**
 * 更新或建立 Bot Session
 * @param {string} userId - LINE 用戶 ID
 * @param {Object} sessionData - session 資料
 */
export function updateBotSession(userId, sessionData) {
    const { handler_type, state, data, pending_intent, pending_intent_message } = sessionData;
    const now = new Date().toISOString();
    const dataJson = JSON.stringify(data || {});

    return new Promise((resolve, reject) => {
        const sql = `
            INSERT INTO bot_sessions (
                user_id, handler_type, state, data, pending_intent, pending_intent_message, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                handler_type = excluded.handler_type,
                state = excluded.state,
                data = excluded.data,
                pending_intent = excluded.pending_intent,
                pending_intent_message = excluded.pending_intent_message,
                updated_at = excluded.updated_at
        `;

        db.run(sql, [userId, handler_type, state, dataJson, pending_intent, pending_intent_message, now, now], function (err) {
            if (err) reject(err);
            else resolve({ changes: this.changes });
        });
    });
}

/**
 * 刪除 Bot Session
 * @param {string} userId - LINE 用戶 ID
 */
export function deleteBotSession(userId) {
    return new Promise((resolve, reject) => {
        db.run('DELETE FROM bot_sessions WHERE user_id = ?', [userId], function (err) {
            if (err) reject(err);
            else resolve({ changes: this.changes });
        });
    });
}

/**
 * 取得所有進行中的 Bot Sessions（用於 Admin-Web 合併顯示）
 * @returns {Promise<Array>} 所有進行中的 sessions
 */
export function getAllActiveSessions() {
    return new Promise((resolve, reject) => {
        db.all(
            'SELECT * FROM bot_sessions WHERE state != ? AND state IS NOT NULL',
            ['idle'],
            (err, rows) => {
                if (err) reject(err);
                else {
                    // 解析 JSON data 欄位
                    const parsed = (rows || []).map(row => {
                        try {
                            row.data = row.data ? JSON.parse(row.data) : {};
                        } catch {
                            row.data = {};
                        }
                        return row;
                    });
                    resolve(parsed);
                }
            }
        );
    });
}

// ============================================
// 🔧 方案 D：用戶訂單關聯 (User Order Mapping)
// ============================================

/**
 * 儲存用戶與訂單的關聯
 * @param {string} lineUserId - LINE 用戶 ID
 * @param {string} pmsId - PMS 訂單 ID
 * @param {string} otaId - OTA 訂單 ID
 * @param {string} checkInDate - 入住日期
 */
export function saveUserOrderLink(lineUserId, pmsId, otaId, checkInDate) {
    const updatedAt = new Date().toISOString();

    return new Promise((resolve, reject) => {
        const sql = `
            INSERT INTO user_order_mapping (line_user_id, pms_id, ota_id, check_in_date, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(line_user_id, pms_id) DO UPDATE SET
                ota_id = excluded.ota_id,
                check_in_date = excluded.check_in_date,
                updated_at = excluded.updated_at
        `;

        db.run(sql, [lineUserId, pmsId, otaId, checkInDate, updatedAt], function (err) {
            if (err) reject(err);
            else resolve({ changes: this.changes });
        });
    });
}

/**
 * 取得用戶關聯的訂單列表
 * @param {string} lineUserId - LINE 用戶 ID
 * @returns {Promise<Array>} 關聯的訂單列表
 */
export function getUserOrders(lineUserId) {
    return new Promise((resolve, reject) => {
        db.all(
            'SELECT * FROM user_order_mapping WHERE line_user_id = ? ORDER BY updated_at DESC',
            [lineUserId],
            (err, rows) => {
                if (err) reject(err);
                else resolve(rows || []);
            }
        );
    });
}

/**
 * 取得用戶最近的訂單
 * @param {string} lineUserId - LINE 用戶 ID
 * @returns {Promise<Object|null>} 最近的訂單關聯
 */
export function getUserLatestOrder(lineUserId) {
    return new Promise((resolve, reject) => {
        db.get(
            'SELECT * FROM user_order_mapping WHERE line_user_id = ? ORDER BY updated_at DESC LIMIT 1',
            [lineUserId],
            (err, row) => {
                if (err) reject(err);
                else resolve(row || null);
            }
        );
    });
}

// ============================================
// 房間確認狀態 (Room Acknowledgments)
// 用於 Admin-Web 跨電腦同步
// ============================================

/**
 * 初始化 room_acknowledgments 資料表
 */
function initRoomAcknowledgmentsTable() {
    const schema = `
        CREATE TABLE IF NOT EXISTS room_acknowledgments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_number TEXT NOT NULL,
            date TEXT NOT NULL,
            acknowledged_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(room_number, date)
        );
    `;
    db.run(schema, (err) => {
        if (err) {
            console.error('❌ 初始化 room_acknowledgments 資料表失敗:', err.message);
        } else {
            console.log('✅ room_acknowledgments 資料表就緒');
            // 清除過期記錄（只保留當日）
            clearExpiredAcknowledgments();
        }
    });
}

// 延遲初始化
setTimeout(initRoomAcknowledgmentsTable, 700);

/**
 * 取得當日已確認的房間列表
 * @param {string} date - 日期 (YYYY-MM-DD)
 * @returns {Promise<Array>} 已確認房間號碼列表
 */
export function getRoomAcknowledgments(date) {
    return new Promise((resolve, reject) => {
        db.all(
            'SELECT room_number FROM room_acknowledgments WHERE date = ?',
            [date],
            (err, rows) => {
                if (err) reject(err);
                else resolve((rows || []).map(r => r.room_number));
            }
        );
    });
}

/**
 * 新增房間確認記錄
 * @param {string} roomNumber - 房號
 * @param {string} date - 日期 (YYYY-MM-DD)
 */
export function addRoomAcknowledgment(roomNumber, date) {
    return new Promise((resolve, reject) => {
        const sql = `
            INSERT OR IGNORE INTO room_acknowledgments (room_number, date)
            VALUES (?, ?)
        `;
        db.run(sql, [roomNumber, date], function (err) {
            if (err) reject(err);
            else resolve({ id: this.lastID, changes: this.changes });
        });
    });
}

/**
 * 清除過期的確認記錄（只保留當日）
 */
export function clearExpiredAcknowledgments() {
    const today = new Date().toISOString().split('T')[0];
    return new Promise((resolve, reject) => {
        db.run(
            'DELETE FROM room_acknowledgments WHERE date < ?',
            [today],
            function (err) {
                if (err) reject(err);
                else {
                    if (this.changes > 0) {
                        console.log(`✅ 已清除 ${this.changes} 筆過期房間確認記錄`);
                    }
                    resolve({ changes: this.changes });
                }
            }
        );
    });
}

/**
 * 清除所有確認記錄（每天 23:00 執行）
 */
export function clearAllAcknowledgments() {
    return new Promise((resolve, reject) => {
        db.run('DELETE FROM room_acknowledgments', function (err) {
            if (err) reject(err);
            else {
                console.log(`🕐 每日 23:00 定時清除：已清除 ${this.changes} 筆房間確認記錄`);
                resolve({ changes: this.changes });
            }
        });
    });
}

/**
 * 設定每天 23:00 自動清除確認記錄
 */
function scheduleNightlyClear() {
    const now = new Date();
    const target = new Date();
    target.setHours(23, 0, 0, 0); // 今天 23:00
    
    // 如果已經過了今天 23:00，設定明天 23:00
    if (now >= target) {
        target.setDate(target.getDate() + 1);
    }
    
    const msUntilTarget = target.getTime() - now.getTime();
    
    console.log(`⏰ 已設定每日 23:00 自動清除房間確認記錄（下次執行：${target.toLocaleString('zh-TW')}）`);
    
    // 第一次執行
    setTimeout(() => {
        clearAllAcknowledgments();
        // 之後每 24 小時執行一次
        setInterval(clearAllAcknowledgments, 24 * 60 * 60 * 1000);
    }, msUntilTarget);
}

// 啟動定時任務
setTimeout(scheduleNightlyClear, 1000);

export default db;
