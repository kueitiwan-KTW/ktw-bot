import express from 'express';
import cors from 'cors';
import { createServer } from 'http';
import { WebSocketServer } from 'ws';
import { readFileSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import { beautifyBookings } from './services/ai-beautify.js';
import { getBookingSource } from './helpers/bookingSource.js';
import dotenv from 'dotenv';
import path from 'path'; // Added missing import

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// 載入 KTW-backend 專用 .env
dotenv.config({ path: join(__dirname, '../.env') });

const app = express();
const PORT = 3000;
const WS_PORT = 3001;

// Bot 的 guest_orders.json 路徑
const GUEST_ORDERS_PATH = join(__dirname, '../../chat_logs/guest_orders.json');

// 讀取 Bot 收集的訂單資訊
function getGuestOrders() {
    try {
        if (existsSync(GUEST_ORDERS_PATH)) {
            const data = readFileSync(GUEST_ORDERS_PATH, 'utf-8');
            return JSON.parse(data);
        }
    } catch (err) {
        console.error('讀取 guest_orders.json 失敗:', err.message);
    }
    return {};
}

// 智慧匹配：從 guest_orders.json 找出對應的 Bot 收集資訊
function matchGuestOrder(booking, guestOrders) {
    // 1. 優先用訂單編號精確匹配
    if (guestOrders[booking.booking_id]) {
        return guestOrders[booking.booking_id];
    }

    // 2. 用姓名+入住日期模糊匹配
    const bookingName = booking.guest_name?.toLowerCase().replace(/\s+/g, '');
    const bookingDate = booking.check_in_date;

    for (const [orderId, order] of Object.entries(guestOrders)) {
        const orderName = order.guest_name?.toLowerCase().replace(/\s+/g, '');
        const orderDate = order.check_in;

        // 姓名部分匹配 + 日期匹配
        if (orderDate === bookingDate) {
            if (bookingName?.includes(orderName) || orderName?.includes(bookingName)) {
                console.log(`🔗 智慧匹配成功: ${booking.guest_name} → ${order.guest_name} (訂單 ${orderId})`);
                return order;
            }
        }
    }

    return null;
}

// 🔄 共用的訂單資料處理函數（供今日/昨日/明日 API 使用）
function processBookings(bookings, guestOrders) {
    // 使用全域的 roomTypeMap（DRY 原則 - 避免重複定義）

    return bookings.map(booking => {
        // 1. OTA 訂單號
        const otaId = booking.ota_booking_id || '';
        const displayOrderId = otaId || booking.booking_id;

        // 2. 訂房來源判斷 (使用共用函數 - DRY)
        const bookingSource = getBookingSource(otaId);

        const remarks = booking.remarks || '';
        const guestName = booking.guest_name || '';
        const lastName = (booking.guest_last_name || '').trim();
        const firstName = (booking.guest_first_name || '').trim();

        // 3. 組合姓名 (使用已宣告的 lastName, firstName)
        let fullName = lastName && firstName ? `${lastName}${firstName}` : guestName;
        if (!fullName || fullName === guestName) {
            const match = remarks.match(/Guest Name:\s*([A-Za-z\s]+?)(?:\s+benefit|\s+request|$)/i);
            if (match) fullName = match[1].trim();
        }

        // 4. 早餐判斷
        let breakfast = remarks.includes('不含早') ? "不含早餐" : "有早餐";

        // 5. 電話格式化
        let formattedPhone = booking.contact_phone || '';
        if (formattedPhone) {
            const digitsOnly = formattedPhone.replace(/\D/g, '');
            if (digitsOnly.length >= 9) formattedPhone = '0' + digitsOnly.slice(-9);
        }

        // 6. 整合 Bot 資料
        const botInfo = matchGuestOrder(booking, guestOrders);

        // 7. 處理房型
        let roomTypeName = '未知房型';
        if (booking.rooms && booking.rooms.length > 0) {
            const roomCounts = {};
            booking.rooms.forEach(room => {
                const roomCode = (room.ROOM_TYPE_CODE || room.room_type_code || '').trim();
                const count = room.ROOM_COUNT || room.room_count || 1;
                if (roomCode) roomCounts[roomCode] = (roomCounts[roomCode] || 0) + count;
            });
            const roomParts = Object.entries(roomCounts).map(([code, count]) => {
                const name = roomTypeMap[code] || code;
                return count > 1 ? `${name} x${count}` : name;
            });
            roomTypeName = roomParts.join(', ') || '未知房型';
        }

        // 8. 計算應收尾款（只有官網、手KEY、Booking.com 才計算）
        const needsPayment = ['官網', '手KEY', 'Booking.com'].includes(bookingSource);
        const depositPaid = booking.deposit_paid || 0;
        const roomTotal = booking.room_total || 0;
        const balanceDue = needsPayment ? Math.max(0, roomTotal - depositPaid) : 0;

        // 9. 回傳結果
        const result = {
            booking_id: displayOrderId,
            pms_id: booking.booking_id,
            booking_source: bookingSource,
            guest_name: fullName,
            registered_name: booking.registered_name || null,
            customer_remarks: booking.customer_remarks || null,
            contact_phone: formattedPhone,
            check_in_date: booking.check_in_date,
            check_out_date: booking.check_out_date,
            nights: booking.nights,
            status_code: booking.status_code,
            status_name: booking.status_name,
            breakfast: breakfast,
            remarks: remarks,
            deposit_paid: depositPaid,
            room_total: roomTotal,
            balance_due: balanceDue,
            room_type_name: roomTypeName,
            room_numbers: booking.room_numbers || (booking.rooms && booking.rooms.length > 0 ? booking.rooms.map(r => r.room_number).filter(Boolean) : []),
            line_name: botInfo?.display_name || null,
            arrival_time_from_bot: botInfo?.arrival_time || null,
            special_request_from_bot: null
        };

        // 提取特殊需求
        if (botInfo?.special_requests?.length) {
            const lastRequest = botInfo.special_requests[botInfo.special_requests.length - 1];
            if (lastRequest.includes('special_need:')) {
                result.special_request_from_bot = lastRequest.split('special_need:')[1].trim();
            }
        }

        return result;
    });
}

// WebSocket 客戶端管理
const wsClients = new Set();

// 中介軟體
app.use(cors());  // 允許跨域 (Vue.js 可以呼叫)
app.use(express.json());

// ============================================
// API 路由
// ============================================

// 健康檢查（Vue.js 燈號用）
app.get('/api/health', (req, res) => {
    res.json({
        status: 'online',
        service: 'KTW-Core',
        timestamp: new Date().toISOString()
    });
});

// 系統狀態 API（給前端燈號用）
app.get('/api/status', async (req, res) => {
    const services = [];

    // 1. 檢查 Bot (Port 5001)
    try {
        const response = await fetch('http://localhost:5001/', { signal: AbortSignal.timeout(2000) });
        services.push({ id: 'bot', name: 'LINE Bot', status: 'online' });
    } catch {
        services.push({ id: 'bot', name: 'LINE Bot', status: 'offline' });
    }

    // 2. Node.js Core 自己一定在線
    services.push({ id: 'core', name: 'Node.js Core', status: 'online' });

    // 3. 檢查 Ngrok (Port 4040)
    try {
        const response = await fetch('http://127.0.0.1:4040/api/tunnels', { signal: AbortSignal.timeout(2000) });
        if (response.ok) {
            services.push({ id: 'ngrok', name: 'Ngrok', status: 'online' });
        } else {
            services.push({ id: 'ngrok', name: 'Ngrok', status: 'offline' });
        }
    } catch {
        services.push({ id: 'ngrok', name: 'Ngrok', status: 'offline' });
    }

    // 4. 檢查 PMS API (192.168.8.3:3000)
    try {
        const response = await fetch('http://192.168.8.3:3000/api/health', { signal: AbortSignal.timeout(3000) });
        if (response.ok) {
            services.push({ id: 'pms', name: 'PMS API', status: 'online' });
        } else {
            services.push({ id: 'pms', name: 'PMS API', status: 'offline' });
        }
    } catch {
        services.push({ id: 'pms', name: 'PMS API', status: 'offline' });
    }

    // 5. 檢查 Vue.js Admin (Port 5002)
    try {
        const response = await fetch('http://localhost:5002/', { signal: AbortSignal.timeout(2000) });
        if (response.ok) {
            services.push({ id: 'admin', name: 'Vue.js Admin', status: 'online' });
        } else {
            services.push({ id: 'admin', name: 'Vue.js Admin', status: 'offline' });
        }
    } catch {
        services.push({ id: 'admin', name: 'Vue.js Admin', status: 'offline' });
    }

    // 6. Gmail 暫時模擬（之後可接 Python API）
    services.push({ id: 'gmail', name: 'Gmail', status: 'online' });

    res.json({ services });
});

// ============================================
// PMS API 代理 (轉發請求到德安 PMS)
// ============================================// PMS API 基礎 URL
const PMS_API_BASE = 'http://192.168.8.3:3000/api/v1';


// 讀取房型對照表
const roomTypeMap = JSON.parse(
    readFileSync(join(__dirname, '../room_type_mapping.json'), 'utf-8')
);

function translateRoomType(code) {
    return roomTypeMap[code?.trim()] || code?.trim() || '未知房型';
}

function translateSource(otaId) {
    if (!otaId) return '官網';
    const prefix = otaId.substring(0, 4);
    const sourceMap = {
        'RMBK': 'Booking.com',
        'RMAG': 'Agoda',
        'RMEX': 'Expedia',
        'RMCT': 'Ctrip 攜程',
        'RMHT': 'Hotels.com',
    };
    return sourceMap[prefix] || (otaId.startsWith('RM') ? 'OTA' : '官網');
}

function translateStatus(code) {
    const statusMap = {
        'O': '已確認',
        'R': '預約中',
        'I': '已入住',
        'D': '已退房',
        'C': '已取消',
    };
    return statusMap[code] || '未知';
}

// 轉換 PMS 訂單資料為前端格式
function transformBookingData(booking) {
    if (!booking) return null;

    const room = booking.rooms?.[0] || {};
    return {
        booking_id: booking.ota_booking_id || booking.booking_id,  // 優先顯示 OTA 編號
        pms_id: booking.booking_id,  // 保留 PMS 編號供內部使用
        guest_name: [booking.guest_last_name, booking.guest_first_name].filter(Boolean).join(' ') || booking.guest_name,
        contact_phone: booking.contact_phone,
        check_in_date: booking.check_in_date,
        check_out_date: booking.check_out_date,
        room_type_code: room.ROOM_TYPE_CODE?.trim(),
        room_type_name: translateRoomType(room.ROOM_TYPE_CODE),
        room_numbers: booking.room_numbers || [],
        source: translateSource(booking.ota_booking_id),
        status_code: booking.status_code,
        status_name: translateStatus(booking.status_code),
        deposit_paid: booking.deposit_paid || 0,
        room_total: room.ROOM_TOTAL || 0,
        breakfast: translateBreakfast(booking.remarks),
        arrival_time: null, // 由 Bot 更新
    };
}

// 早餐判斷
function translateBreakfast(remarks) {
    if (!remarks) return '依訂單';
    // web001:官網優惠價 = 含早餐
    if (remarks.includes('官網優惠價') || remarks.includes('含早')) return '有早餐';
    // OTAnfb:OTA定價不含早 = 無早餐
    if (remarks.includes('OTA定價不含早') || remarks.includes('不含早')) return '無早餐';
    return '依訂單';
}

// 取得今日統計摘要
app.get('/api/pms/dashboard', async (req, res) => {
    try {
        // 從 PMS API 取得真實資料
        const PMS_API = 'http://192.168.8.3:3000/api';

        const [checkinRes, checkoutRes, roomsRes] = await Promise.allSettled([
            fetch(`${PMS_API}/bookings/today-checkin`, { signal: AbortSignal.timeout(5000) }),
            fetch(`${PMS_API}/bookings/today-checkout`, { signal: AbortSignal.timeout(5000) }),
            fetch(`${PMS_API}/rooms/status`, { signal: AbortSignal.timeout(5000) })  // 使用 /status 端點
        ]);

        let todayCheckin = 0;
        let todayCheckout = 0;
        let occupiedRooms = 0;
        let totalRooms = 0;

        // 今日入住數量
        if (checkinRes.status === 'fulfilled' && checkinRes.value.ok) {
            const data = await checkinRes.value.json();
            todayCheckin = data.count || 0;
        }

        // 今日退房數量
        if (checkoutRes.status === 'fulfilled' && checkoutRes.value.ok) {
            const data = await checkoutRes.value.json();
            todayCheckout = data.count || 0;
        }

        // 房況統計 - 從 /rooms/status 取得
        if (roomsRes.status === 'fulfilled' && roomsRes.value.ok) {
            const data = await roomsRes.value.json();
            const stats = data.data?.stats || {};
            totalRooms = stats.total || 0;
            occupiedRooms = stats.occupied || 0;  // 直接使用 API 計算好的 occupied 數量
        }

        res.json({
            success: true,
            data: {
                todayCheckin,
                todayCheckout,
                occupiedRooms,
                totalRooms,
                lastUpdate: new Date().toISOString()
            }
        });
    } catch (error) {
        console.error('PMS Dashboard Error:', error.message);
        res.json({
            success: false,
            error: error.message,
            data: {
                todayCheckin: 0,
                todayCheckout: 0,
                occupiedRooms: 0,
                totalRooms: 0,
                lastUpdate: new Date().toISOString()
            }
        });
    }
});

// 取得今日入住客人清單
app.get('/api/pms/today-checkin', async (req, res) => {
    try {
        const today = new Date().toISOString().split('T')[0];

        // 使用 PMS API 的 check_in 日期查詢
        // 注意：PMS API 可能需要使用 Oracle 直接查詢
        // 暫時使用模擬資料，之後可串接 Oracle
        const response = await fetch(`http://192.168.8.3:3000/api/bookings/today-checkin`, {
            signal: AbortSignal.timeout(5000)
        });

        if (response.ok) {
            const data = await response.json();

            if (data.success && data.data) {
                // 使用共用的資料處理函數
                const guestOrders = getGuestOrders();
                data.data = processBookings(data.data, guestOrders);
            }
            res.json(data);
        } else {
            // PMS API 沒有此端點時，回傳模擬資料供前端開發
            const today = new Date().toISOString().split('T')[0];
            res.json({
                success: true,
                data: [
                    {
                        booking_id: "00605201",
                        guest_name: "王小明",
                        contact_phone: "0912345678",
                        check_in_date: today,
                        check_out_date: new Date(Date.now() + 86400000).toISOString().split('T')[0],
                        room_type_code: "SD",
                        room_type_name: "標準雙人房",
                        room_numbers: ["301"],
                        source: "Booking.com",
                        status_code: "O",
                        status_name: "待入住",
                        breakfast: "有早餐",
                        deposit_paid: 1500,
                        room_total: 3000
                    },
                    {
                        booking_id: "00605202",
                        guest_name: "陳大華",
                        contact_phone: "0987654321",
                        check_in_date: today,
                        check_out_date: new Date(Date.now() + 172800000).toISOString().split('T')[0],
                        room_type_code: "SQ",
                        room_type_name: "標準四人房",
                        room_numbers: [],
                        source: "官網",
                        status_code: "O",
                        status_name: "待入住",
                        breakfast: "無早餐",
                        deposit_paid: 2000,
                        room_total: 5000
                    }
                ],
                count: 2,
                note: "模擬資料 - 待接入 PMS API /api/bookings/today-checkin"
            });
        }
    } catch (error) {
        console.error('Today Checkin Error:', error.message);
        res.json({
            success: false,
            error: error.message,
            data: [],
            count: 0
        });
    }
});

// 取得昨日入住客人清單
app.get('/api/pms/yesterday-checkin', async (req, res) => {
    try {
        const response = await fetch('http://192.168.8.3:3000/api/bookings/yesterday-checkin', {
            signal: AbortSignal.timeout(5000)
        });

        if (response.ok) {
            const data = await response.json();
            if (data.success && data.data) {
                // 使用共用的資料處理函數
                const guestOrders = getGuestOrders();
                data.data = processBookings(data.data, guestOrders);
            }
            res.json(data);
        } else {
            res.status(response.status).json({ success: false, error: 'PMS API error' });
        }
    } catch (error) {
        console.error('昨日入住API錯誤:', error);
        res.status(500).json({ success: false, error: error.message, data: [] });
    }
});

// 取得明日入住客人清單
app.get('/api/pms/tomorrow-checkin', async (req, res) => {
    try {
        const response = await fetch('http://192.168.8.3:3000/api/bookings/tomorrow-checkin', {
            signal: AbortSignal.timeout(5000)
        });

        if (response.ok) {
            const data = await response.json();
            if (data.success && data.data) {
                // 使用共用的資料處理函數
                const guestOrders = getGuestOrders();
                data.data = processBookings(data.data, guestOrders);
            }
            res.json(data);
        } else {
            res.status(response.status).json({ success: false, error: 'PMS API error' });
        }
    } catch (error) {
        console.error('明日入住API錯誤:', error);
        res.status(500).json({ success: false, error: error.message, data: [] });
    }
});

// 取得房間狀態（清潔/停用）
app.get('/api/pms/rooms/status', async (req, res) => {
    try {
        const response = await fetch('http://192.168.8.3:3000/api/rooms/status', {
            signal: AbortSignal.timeout(5000)
        });

        if (response.ok) {
            const data = await response.json();
            res.json(data);
        } else {
            res.status(response.status).json({ success: false, error: 'PMS API error' });
        }
    } catch (error) {
        console.error('房間狀態 API 錯誤:', error);
        res.status(500).json({ success: false, error: error.message, data: { stats: {}, rooms: [] } });
    }
});

// ============================================
// LINE 當日預訂 (暫存訂單 API)
// ============================================

// 取得當日暫存訂單列表
app.get('/api/pms/same-day-bookings', async (req, res) => {
    try {
        const response = await fetch('http://192.168.8.3:3000/api/v1/bookings/same-day-list', {
            signal: AbortSignal.timeout(5000)
        });

        if (response.ok) {
            const data = await response.json();
            res.json(data);
        } else {
            res.status(response.status).json({ success: false, error: 'PMS API error' });
        }
    } catch (error) {
        console.error('暫存訂單 API 錯誤:', error);
        res.status(500).json({ success: false, error: error.message, data: { bookings: [] } });
    }
});

// 標記暫存訂單為已 KEY
app.patch('/api/pms/same-day-bookings/:order_id/checkin', async (req, res) => {
    try {
        const { order_id } = req.params;
        const response = await fetch(`http://192.168.8.3:3000/api/v1/bookings/same-day/${order_id}/checkin`, {
            method: 'PATCH',
            signal: AbortSignal.timeout(5000)
        });

        if (response.ok) {
            const data = await response.json();
            res.json(data);
        } else {
            res.status(response.status).json({ success: false, error: 'PMS API error' });
        }
    } catch (error) {
        console.error('標記訂單 API 錯誤:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// 搜尋訂單
app.get('/api/pms/bookings/search', async (req, res) => {
    try {
        const { name, phone, booking_id } = req.query;
        const params = new URLSearchParams();
        if (name) params.append('name', name);
        if (phone) params.append('phone', phone);
        if (booking_id) params.append('booking_id', booking_id);

        const response = await fetch(`${PMS_API_BASE} /bookings/search ? ${params} `, {
            signal: AbortSignal.timeout(5000)
        });

        if (response.ok) {
            const data = await response.json();
            res.json(data);
        } else {
            res.status(response.status).json({ success: false, error: 'PMS API Error' });
        }
    } catch (error) {
        console.error('PMS Search Error:', error.message);
        res.status(500).json({ success: false, error: error.message });
    }
});

// 取得訂單詳情
app.get('/api/pms/bookings/:id', async (req, res) => {
    try {
        const { id } = req.params;
        const response = await fetch(`${PMS_API_BASE} /bookings/${id} `, {
            signal: AbortSignal.timeout(5000)
        });

        if (response.ok) {
            const data = await response.json();
            res.json(data);
        } else {
            res.status(response.status).json({ success: false, error: 'Booking not found' });
        }
    } catch (error) {
        console.error('PMS Booking Detail Error:', error.message);
        res.status(500).json({ success: false, error: error.message });
    }
});

// 根路由
app.get('/', (req, res) => {
    res.json({
        message: '🏨 KTW Core API',
        version: '1.0.0',
        endpoints: [
            'GET /api/health',
            'GET /api/status',
            'GET /api/pms/dashboard',
            'GET /api/pms/bookings/search',
            'GET /api/pms/bookings/:id'
        ]
    });
});

// ============================================
// 即時推送 API (給 Bot 呼叫)
// ============================================

// Bot 推送新訊息到前台
app.post('/api/notify', (req, res) => {
    const { type, data } = req.body;

    const message = JSON.stringify({
        type: type || 'notification',
        data,
        timestamp: new Date().toISOString()
    });

    // 廣播到所有 WebSocket 客戶端
    let sentCount = 0;
    wsClients.forEach(client => {
        if (client.readyState === 1) { // OPEN
            client.send(message);
            sentCount++;
        }
    });

    console.log(`📢 推送通知到 ${sentCount} 個客戶端: ${type} `);

    res.json({
        success: true,
        sentTo: sentCount,
        message: '通知已推送'
    });
});

// ============================================
// 啟動伺服器
// ============================================
const server = createServer(app);

// WebSocket 伺服器 (在單獨端口運行)
const wss = new WebSocketServer({ port: WS_PORT });

wss.on('connection', (ws, req) => {
    console.log('🔗 新的 WebSocket 連線');
    wsClients.add(ws);

    ws.on('close', () => {
        console.log('🔌 WebSocket 斷開連線');
        wsClients.delete(ws);
    });

    ws.on('error', (err) => {
        console.error('WebSocket 錯誤:', err);
        wsClients.delete(ws);
    });

    // 發送歡迎訊息
    ws.send(JSON.stringify({
        type: 'welcome',
        data: { message: '已連線到 KTW-Core' },
        timestamp: new Date().toISOString()
    }));
});

server.listen(PORT, () => {
    console.log(`🚀 KTW - Core 運行中: http://localhost:${PORT}`);
    console.log(`📡 WebSocket 運行中: ws://localhost:${WS_PORT}`);
    console.log('📡 API 端點:');
    console.log('   GET  /api/health - 健康檢查');
    console.log('   GET  /api/status - 系統狀態');
    console.log('   POST /api/notify - 推送通知');
});
