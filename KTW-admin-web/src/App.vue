<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { GridStack } from 'gridstack'
import 'gridstack/dist/gridstack.min.css'

// API 基礎 URL（動態取得主機名）
const API_BASE = `http://${window.location.hostname}:3000`

// GridStack 實例
let grid = null

// 面板配置（可拖曳、可縮放、可隱藏）
const widgets = ref([
  { id: 'checkin', title: '今日入住', x: 0, y: 0, w: 3, h: 2, visible: true },
  { id: 'checkout', title: '今日退房', x: 3, y: 0, w: 3, h: 2, visible: true },
  { id: 'occupancy', title: '住房率', x: 6, y: 0, w: 3, h: 2, visible: true },
  { id: 'vacant', title: '空房數', x: 9, y: 0, w: 3, h: 2, visible: true },
  { id: 'rooms', title: '即時房況', x: 0, y: 2, w: 12, h: 5, visible: true },
  { id: 'guests', title: '今日入住客人', x: 0, y: 7, w: 12, h: 4, visible: true },
])

// 統計資料 (從 PMS API 取得)
const stats = ref({
  todayCheckin: 0,
  todayCheckout: 0,
  occupiedRooms: 0,
  totalRooms: 50,
  lastUpdate: null
})

// PMS 資料載入狀態
const pmsLoading = ref(true)
const pmsError = ref(null)

// 從 Node.js Core 取得 PMS 統計資料
async function fetchPMSDashboard() {
  pmsLoading.value = true
  pmsError.value = null
  try {
    const res = await fetch(`${API_BASE}/api/pms/dashboard`, {
      signal: AbortSignal.timeout(5000)
    })
    if (res.ok) {
      const result = await res.json()
      if (result.success) {
        stats.value = result.data
      } else {
        pmsError.value = result.error || 'PMS API 回傳失敗'
      }
    } else {
      pmsError.value = `HTTP ${res.status}`
    }
  } catch (error) {
    pmsError.value = error.message
  } finally {
    pmsLoading.value = false
  }
}

// 今日入住客人清單
const todayGuests = ref([])
const guestsLoading = ref(true)

// 從 Node.js Core 取得今日入住客人
async function fetchTodayCheckin() {
  guestsLoading.value = true
  try {
    const res = await fetch(`${API_BASE}/api/pms/today-checkin`, {
      signal: AbortSignal.timeout(5000)
    })
    if (res.ok) {
      const result = await res.json()
      if (result.success) {
        todayGuests.value = result.data || []
      }
    }
  } catch (error) {
    console.error('Fetch today checkin error:', error)
  } finally {
    guestsLoading.value = false
  }
}

// 手動重新整理
async function manualRefresh() {
  await Promise.all([
    fetchPMSDashboard(),
    fetchTodayCheckin(),
    checkServiceStatus()
  ])
}


// 服務狀態監控
const services = ref([
  { id: 'bot', name: 'AI 助手', icon: '🤖', status: 'checking', port: 5001 },
  { id: 'pms', name: 'PMS API', icon: '🔌', status: 'checking', port: 3000 },
  { id: 'gmail', name: 'Gmail', icon: '📧', status: 'checking', port: null },
  { id: 'ngrok', name: 'Ngrok', icon: '🌐', status: 'checking', port: null },
])

// 檢查服務狀態 (透過 Node.js Core API)
async function checkServiceStatus() {
  try {
    const res = await fetch(`${API_BASE}/api/status`, { 
      signal: AbortSignal.timeout(3000) 
    });
    if (res.ok) {
      const data = await res.json();
      services.value = data.services.map(s => ({
        id: s.id,
        name: s.name,
        icon: getServiceIcon(s.id),
        status: s.status
      }));
    }
  } catch (error) {
    services.value.forEach(s => s.status = 'offline');
  }
}

function getServiceIcon(id) {
  const icons = { 
    bot: '🤖', 
    core: '⚙️', 
    ngrok: '🌐', 
    gmail: '📧', 
    pms: '🔌',
    admin: '🖥️'  // Vue.js Admin
  };
  return icons[id] || '📦';
}

// 格式化時間顯示
function formatTime(timestamp) {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now - date;
  
  if (diff < 60000) return '剛剛';
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分鐘前`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小時前`;
  return date.toLocaleString('zh-TW');
}

// 切換面板顯示/隱藏
function toggleWidget(widgetId) {
  const widget = widgets.value.find(w => w.id === widgetId)
  if (widget) {
    widget.visible = !widget.visible
    nextTick(() => {
      if (grid) {
        if (widget.visible) {
          // 重新添加到 grid
        } else {
          // 從 grid 移除
          const el = document.querySelector(`[gs-id="${widgetId}"]`)
          if (el) grid.removeWidget(el, false)
        }
      }
    })
  }
}

// 定時刷新狀態
let statusInterval = null
let pmsInterval = null

onMounted(() => {
  // 服務狀態檢測
  checkServiceStatus()
  statusInterval = setInterval(checkServiceStatus, 10000)
  
  // PMS 統計資料
  fetchPMSDashboard()
  pmsInterval = setInterval(fetchPMSDashboard, 15000) // 每15秒刷新
  
  // 今日入住客人
  fetchTodayCheckin()
  
  // WebSocket 即時通知連線
  connectWebSocket()
  
  // 初始化 GridStack
  nextTick(() => {
    grid = GridStack.init({
      column: 24,
      cellHeight: 60,
      margin: 8,
      animate: true,
      float: true,
      disableOneColumnMode: true,
      minRow: 1,
      resizable: { handles: 'all' }
    }, '.grid-stack')
  })
})

// WebSocket 連線
let ws = null
const notifications = ref([])

function connectWebSocket() {
  ws = new WebSocket('ws://localhost:3001')
  
  ws.onopen = () => {
    console.log('🔗 WebSocket 已連線')
  }
  
  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)
      console.log('📩 收到通知:', msg)
      
      if (msg.type === 'new_message') {
        // 新增到即時訊息列表
        notifications.value.unshift(msg.data)
        if (notifications.value.length > 20) notifications.value.pop()
      }
      
      // Bot 更新客戶資訊（電話、抵達時間、特殊需求）
      if (msg.type === 'update_guest') {
        const { booking_id, guest_name, phone, arrival_time, special_request } = msg.data
        // 在今日入住列表中找到對應的客人
        const guest = todayGuests.value.find(g => 
          g.booking_id === booking_id || 
          g.guest_name?.includes(guest_name) ||
          guest_name?.includes(g.guest_name)
        )
        if (guest) {
          if (phone) guest.phone_from_bot = phone
          if (arrival_time) guest.arrival_time_from_bot = arrival_time
          if (special_request) guest.special_request_from_bot = special_request
          console.log('✅ 已更新客戶資料:', guest_name)
        }
      }
    } catch (e) {
      console.error('解析通知失敗:', e)
    }
  }
  
  ws.onclose = () => {
    console.log('🔌 WebSocket 斷開，5秒後重連...')
    setTimeout(connectWebSocket, 5000)
  }
  
  ws.onerror = (err) => {
    console.error('WebSocket 錯誤:', err)
  }
}

onUnmounted(() => {
  if (statusInterval) clearInterval(statusInterval)
  if (pmsInterval) clearInterval(pmsInterval)
  if (ws) ws.close()
  if (grid) grid.destroy()
})

// 模擬房間資料
const rooms = ref([
  { number: '101', status: 'occupied' },
  { number: '102', status: 'vacant' },
  { number: '103', status: 'cleaning' },
  { number: '104', status: 'dnd' },
  { number: '105', status: 'occupied' },
  { number: '106', status: 'vacant' },
  { number: '201', status: 'occupied' },
  { number: '202', status: 'occupied' },
  { number: '203', status: 'vacant' },
  { number: '204', status: 'cleaning' },
  { number: '205', status: 'occupied' },
  { number: '206', status: 'dnd' },
  { number: '301', status: 'vacant' },
  { number: '302', status: 'occupied' },
  { number: '303', status: 'occupied' },
  { number: '304', status: 'vacant' },
])

const activeMenu = ref('dashboard')

const menuItems = [
  { id: 'dashboard', icon: '📊', label: '儀表板' },
  { id: 'rooms', icon: '🏨', label: '房況監控' },
  { id: 'bookings', icon: '📅', label: '訂單管理' },
  { id: 'guests', icon: '👥', label: '旅客資料' },
  { id: 'pos', icon: '💰', label: 'POS 收銀' },
  { id: 'reports', icon: '📈', label: '報表中心' },
  { id: 'settings', icon: '⚙️', label: '系統設定' },
]

const statusIcons = { vacant: '✓', occupied: '🛏️', cleaning: '🧹', dnd: '🔴' }
</script>

<template>
  <div id="app">
    <!-- 側邊欄 -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <h1>🏨 KTW Admin</h1>
        <p>飯店管理系統 v2.0</p>
      </div>
      <ul class="nav-menu">
        <li 
          v-for="item in menuItems" 
          :key="item.id"
          class="nav-item"
          :class="{ active: activeMenu === item.id }"
          @click="activeMenu = item.id"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
        </li>
      </ul>
      
      <!-- 面板控制 -->
      <div v-if="activeMenu === 'dashboard'" class="widget-controls">
        <h4>📦 面板控制</h4>
        <label v-for="w in widgets" :key="w.id" class="widget-toggle">
          <input type="checkbox" v-model="w.visible" @change="toggleWidget(w.id)">
          <span>{{ w.title }}</span>
        </label>
      </div>
    </aside>

    <!-- 主內容區 -->
    <main class="main-content">
      <header class="header">
        <h2>{{ menuItems.find(m => m.id === activeMenu)?.label }}</h2>
        <div class="header-right">
          <button v-if="activeMenu === 'dashboard'" @click="manualRefresh" class="refresh-btn" title="重新整理">
            更新
          </button>
          <div class="header-services">
            <div v-for="service in services" :key="service.id" class="header-service-item">
              <span class="service-name-small">{{ service.name }}</span>
              <span class="service-status-dot" :class="service.status"></span>
            </div>
          </div>
        </div>
      </header>

      <!-- 儀表板視圖 -->
      <div v-if="activeMenu === 'dashboard'" class="grid-stack">
        <!-- 今日入住 -->
        <div v-if="widgets[0].visible" class="grid-stack-item" gs-id="checkin" gs-x="0" gs-y="0" gs-w="6" gs-h="2" gs-min-w="4" gs-min-h="2">
          <div class="grid-stack-item-content stat-card">
            <div class="widget-handle">⋮⋮</div>
            <h3>今日入住</h3>
            <span class="stat-value">{{ stats.todayCheckin }}</span>
            <span class="stat-unit">組</span>
          </div>
        </div>

        <!-- 今日退房 -->
        <div v-if="widgets[1].visible" class="grid-stack-item" gs-id="checkout" gs-x="6" gs-y="0" gs-w="6" gs-h="2" gs-min-w="4" gs-min-h="2">
          <div class="grid-stack-item-content stat-card">
            <div class="widget-handle">⋮⋮</div>
            <h3>今日退房</h3>
            <span class="stat-value">{{ stats.todayCheckout }}</span>
            <span class="stat-unit">組</span>
          </div>
        </div>

        <!-- 住房率 -->
        <div v-if="widgets[2].visible" class="grid-stack-item" gs-id="occupancy" gs-x="12" gs-y="0" gs-w="6" gs-h="2" gs-min-w="4" gs-min-h="2">
          <div class="grid-stack-item-content stat-card">
            <div class="widget-handle">⋮⋮</div>
            <h3>住房率</h3>
            <span class="stat-value">{{ Math.round(stats.occupiedRooms / stats.totalRooms * 100) }}</span>
            <span class="stat-unit">%</span>
          </div>
        </div>

        <!-- 空房數 -->
        <div v-if="widgets[3].visible" class="grid-stack-item" gs-id="vacant" gs-x="18" gs-y="0" gs-w="6" gs-h="2" gs-min-w="4" gs-min-h="2">
          <div class="grid-stack-item-content stat-card">
            <div class="widget-handle">⋮⋮</div>
            <h3>空房數</h3>
            <span class="stat-value">{{ stats.totalRooms - stats.occupiedRooms }}</span>
            <span class="stat-unit">間</span>
          </div>
        </div>

        <!-- 房況面板 -->
        <div v-if="widgets[4].visible" class="grid-stack-item" gs-id="rooms" gs-x="0" gs-y="2" gs-w="24" gs-h="4" gs-min-w="12" gs-min-h="3">
          <div class="grid-stack-item-content room-status-panel">
            <div class="widget-handle">⋮⋮</div>
            <h3>🏨 即時房況</h3>
            <div class="room-grid">
              <div v-for="room in rooms" :key="room.number" class="room-card" :class="room.status">
                <span class="room-number">{{ room.number }}</span>
                <span class="room-status-icon">{{ statusIcons[room.status] }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 今日入住客戶資料卡 -->
        <div v-if="widgets[5].visible" class="grid-stack-item" gs-id="guests" gs-x="0" gs-y="6" gs-w="24" gs-h="8" gs-min-w="12" gs-min-h="4">
          <div class="grid-stack-item-content guest-cards-panel">
            <div class="widget-handle">⋮⋮</div>
            <h3>👥 今日入住客戶 <span v-if="todayGuests.length" class="guest-count">({{ todayGuests.length }})</span></h3>
            <div v-if="guestsLoading" class="loading-text">載入中...</div>
            <div v-else-if="todayGuests.length === 0" class="empty-text">今日無預定入住</div>
            <div v-else class="guest-cards-list">
              <div v-for="g in todayGuests" :key="g.booking_id" class="guest-card">
                <!-- 客戶資料卡標題 -->
                <div class="guest-card-header">
                  <span class="guest-card-name">{{ g.guest_name }}</span>
                  <span class="guest-card-status" :class="'status-' + g.status_code">{{ g.status_name }}</span>
                </div>
                <!-- 訂單詳情 -->
                <div class="guest-card-details">
                  <div class="detail-row">
                    <span class="label">房號</span>
                    <span class="value">{{ g.room_numbers?.length ? g.room_numbers.join(', ') : '尚未排房' }}</span>
                  </div>
                  <div class="detail-row">
                    <span class="label">訂單編號</span>
                    <span class="value">{{ g.booking_id }}</span>
                  </div>
                  <div class="detail-row">
                    <span class="label">LINE 姓名</span>
                    <span class="value" :class="{ 'from-bot': g.line_name }">
                      {{ g.line_name || '-' }}
                      <span v-if="g.line_name" class="bot-tag">AI</span>
                    </span>
                  </div>
                  <div class="detail-row">
                    <span class="label">聯絡電話</span>
                    <span class="value" :class="{ 'from-bot': g.phone_from_bot }">
                      {{ g.phone_from_bot || g.contact_phone || '-' }}
                      <span v-if="g.phone_from_bot" class="bot-tag">AI</span>
                    </span>
                  </div>
                  <div class="detail-row">
                    <span class="label">入住日期</span>
                    <span class="value">{{ g.check_in_date }}{{ g.nights >= 2 ? ` (${g.nights}晚)` : '' }}</span>
                  </div>
                  <div class="detail-row">
                    <span class="label">退房日期</span>
                    <span class="value">{{ g.check_out_date }}</span>
                  </div>
                  <div class="detail-row">
                    <span class="label">訂房來源</span>
                    <span class="value booking-source">{{ g.booking_source || '未知' }}</span>
                  </div>
                  <div class="detail-row">
                    <span class="label">房型</span>
                    <span class="value">{{ g.room_type_name || g.room_types || g.room_type }}</span>
                  </div>
                  <div class="detail-row">
                    <span class="label">早餐</span>
                    <span class="value">{{ g.breakfast || '依訂單' }}</span>
                  </div>
                  <div class="detail-row">
                    <span class="label">已付訂金</span>
                    <span class="value price">NT$ {{ (g.deposit_paid || 0).toLocaleString() }}</span>
                  </div>
                  <div class="detail-row">
                    <span class="label">房價總額</span>
                    <span class="value price">NT$ {{ (g.room_total || 0).toLocaleString() }}</span>
                  </div>
                  <div class="detail-row">
                    <span class="label">預計抵達</span>
                    <span class="value" :class="{ 'from-bot': g.arrival_time_from_bot }">
                      {{ g.arrival_time_from_bot || '未提供' }}
                      <span v-if="g.arrival_time_from_bot" class="bot-tag">Bot</span>
                    </span>
                  </div>
                  <div class="detail-row special-request">
                    <span class="label">特殊需求</span>
                    <span class="value" :class="{ 'from-bot': g.special_request_from_bot }">
                      {{ g.special_request_from_bot || '無' }}
                      <span v-if="g.special_request_from_bot" class="bot-tag">Bot</span>
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 即時通知客戶資料卡 -->
        <div class="grid-stack-item" gs-id="notifications" gs-x="0" gs-y="10" gs-w="24" gs-h="6" gs-min-w="12" gs-min-h="4">
          <div class="grid-stack-item-content notification-panel">
            <div class="widget-handle">⋮⋮</div>
            <h3>📩 即時客戶訊息 <span class="notification-count" v-if="notifications.length">({{ notifications.length }})</span></h3>
            <div v-if="notifications.length === 0" class="empty-text">等待客戶訊息...</div>
            <div v-else class="notification-list">
              <div 
                v-for="(n, idx) in notifications" 
                :key="idx" 
                class="customer-card"
                :class="{ vip: n.is_vip }"
              >
                <!-- 客戶基本資訊 -->
                <div class="customer-header">
                  <img :src="n.profile_picture || 'https://via.placeholder.com/50'" class="avatar" />
                  <div class="customer-info">
                    <div class="customer-name">
                      {{ n.display_name }}
                      <span v-if="n.is_vip" class="vip-badge">⭐ VIP</span>
                    </div>
                    <div class="customer-message">💬 {{ n.message }}</div>
                  </div>
                  <span class="notification-time">{{ formatTime(n.timestamp) }}</span>
                </div>
                
                <!-- 訂單詳細資訊 -->
                <div v-if="n.booking" class="booking-details">
                  <div class="booking-row">
                    <span class="label">訂單狀況</span>
                    <span class="value" :class="'status-' + n.booking.status_code">{{ n.booking.status_name }}</span>
                  </div>
                  <div class="booking-row">
                    <span class="label">房號</span>
                    <span class="value">{{ n.booking.room_numbers?.length ? n.booking.room_numbers.join(', ') : '尚未排房' }}</span>
                  </div>
                  <div class="booking-row">
                    <span class="label">訂單編號</span>
                    <span class="value">{{ n.booking.booking_id }}</span>
                  </div>
                  <div class="booking-row">
                    <span class="label">訂房姓名</span>
                    <span class="value">{{ n.booking.guest_name }}</span>
                  </div>
                  <div class="booking-row">
                    <span class="label">聯絡電話</span>
                    <span class="value" :class="{ 'from-bot': n.phone_from_bot }">
                      {{ n.phone_from_bot || n.booking.contact_phone || '-' }}
                      <span v-if="n.phone_from_bot" class="bot-tag">Bot更新</span>
                    </span>
                  </div>
                  <div class="booking-row">
                    <span class="label">入住日期</span>
                    <span class="value">{{ n.booking.check_in_date }}</span>
                  </div>
                  <div class="booking-row">
                    <span class="label">退房日期</span>
                    <span class="value">{{ n.booking.check_out_date }}</span>
                  </div>
                  <div class="booking-row">
                    <span class="label">訂房來源</span>
                    <span class="value booking-source">{{ n.booking.source }}</span>
                  </div>
                  <div class="booking-row">
                    <span class="label">房型</span>
                    <span class="value">{{ n.booking.room_type_name || n.booking.room_type_code }}</span>
                  </div>
                  <div class="booking-row">
                    <span class="label">早餐</span>
                    <span class="value">{{ n.booking.breakfast || '無' }}</span>
                  </div>
                  <div class="booking-row">
                    <span class="label">已付訂金</span>
                    <span class="value price">NT$ {{ n.booking.deposit_paid?.toLocaleString() || 0 }}</span>
                  </div>
                  <div class="booking-row">
                    <span class="label">房價總額</span>
                    <span class="value price">NT$ {{ n.booking.room_total?.toLocaleString() || 0 }}</span>
                  </div>
                  <div class="booking-row">
                    <span class="label">預計抵達</span>
                    <span class="value" :class="{ 'from-bot': n.arrival_time_from_bot }">
                      {{ n.arrival_time_from_bot || n.booking.arrival_time || '未提供' }}
                      <span v-if="n.arrival_time_from_bot" class="bot-tag">Bot更新</span>
                    </span>
                  </div>
                  <div class="booking-row special-request">
                    <span class="label">特殊需求</span>
                    <span class="value" :class="{ 'from-bot': n.special_request_from_bot }">
                      {{ n.special_request_from_bot || n.booking.special_request || '無' }}
                      <span v-if="n.special_request_from_bot" class="bot-tag">Bot更新</span>
                    </span>
                  </div>
                </div>
                
                <!-- 尚無訂單資訊 -->
                <div v-else class="no-booking">
                  <span class="hint">💡 正在查詢訂單資訊...</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 其他頁面佔位 -->
      <div v-else class="placeholder">
        <p style="text-align: center; color: #888; padding: 100px;">
          📦 {{ menuItems.find(m => m.id === activeMenu)?.label }} 功能開發中...
        </p>
      </div>
    </main>
  </div>
</template>
