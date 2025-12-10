/**
 * PMS API 主程式
 */

const express = require('express');
const cors = require('cors');
const db = require('./config/database');

const app = express();
const PORT = process.env.PORT || 3000;

// 中介軟體
app.use(cors());
app.use(express.json());

// 路由
const bookingsRouter = require('./routes/bookings');
const roomsRouter = require('./routes/rooms');

// API v1 路由
app.use('/api/v1/bookings', bookingsRouter);
app.use('/api/v1/rooms', roomsRouter);

// 向后兼容：保留无版本号的路由（重定向到 v1）
app.use('/api/bookings', bookingsRouter);
app.use('/api/rooms', roomsRouter);

// 健康檢查端點
app.get('/api/health', (req, res) => {
    res.json({
        status: 'ok',
        timestamp: new Date().toISOString(),
        service: 'PMS API'
    });
});

// 根路徑
app.get('/', (req, res) => {
    res.json({
        message: 'PMS REST API',
        version: '1.0.0',
        apiVersion: 'v1',
        endpoints: {
            health: 'GET /api/health',
            // v1 端點
            searchBookings: 'GET /api/v1/bookings/search?name=XXX&phone=XXX',
            getBooking: 'GET /api/v1/bookings/:booking_id',
            checkAvailability: 'GET /api/v1/rooms/availability?check_in=YYYY-MM-DD&check_out=YYYY-MM-DD',
            createBooking: 'POST /api/v1/bookings',
            cancelBooking: 'DELETE /api/v1/bookings/:booking_id',
            // 兼容端點（無版本號，映射到 v1）
            searchBookingsCompat: 'GET /api/bookings/search',
            getBookingCompat: 'GET /api/bookings/:booking_id',
            createBookingCompat: 'POST /api/bookings',
            cancelBookingCompat: 'DELETE /api/bookings/:booking_id'
        },
        note: '建議使用 /api/v1/ 端點以確保未來兼容性'
    });
});

// 錯誤處理
app.use((err, req, res, next) => {
    console.error('錯誤：', err);
    res.status(500).json({
        success: false,
        error: {
            code: 'INTERNAL_SERVER_ERROR',
            message: err.message || '伺服器內部錯誤'
        }
    });
});

// 404 處理
app.use((req, res) => {
    res.status(404).json({
        success: false,
        error: {
            code: 'NOT_FOUND',
            message: '找不到請求的資源'
        }
    });
});

// 啟動伺服器
async function startServer() {
    try {
        // 初始化資料庫連線池
        await db.initialize();

        // 啟動 HTTP 伺服器
        app.listen(PORT, () => {
            console.log('');
            console.log('🚀 PMS API 伺服器已啟動');
            console.log(`📡 監聽端口: ${PORT}`);
            console.log(`🌐 API 位址: http://localhost:${PORT}`);
            console.log(`💚 健康檢查: http://localhost:${PORT}/api/health`);
            console.log('');
        });
    } catch (err) {
        console.error('❌ 伺服器啟動失敗：', err.message);
        process.exit(1);
    }
}

// 優雅關閉
process.on('SIGINT', async () => {
    console.log('\n正在關閉伺服器...');
    await db.close();
    process.exit(0);
});

process.on('SIGTERM', async () => {
    console.log('\n正在關閉伺服器...');
    await db.close();
    process.exit(0);
});

// 啟動
startServer();
