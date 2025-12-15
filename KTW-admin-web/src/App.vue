<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { GridStack } from 'gridstack'
import 'gridstack/dist/gridstack.min.css'
import GuestCard from './components/GuestCard.vue'

// API 基礎 URL（動態取得主機名）
const API_BASE = `http://${window.location.hostname}:3000`

// GridStack 實例
let grid = null

// 面板配置（可拖曳、可縮放、可隱藏、可收折）
const widgets = ref([
  { id: 'checkin', title: '今日入住', x: 0, y: 0, w: 3, h: 2, visible: true, collapsed: false },
  { id: 'checkout', title: '今日退房', x: 3, y: 0, w: 3, h: 2, visible: true, collapsed: false },
  { id: 'occupancy', title: '住房率', x: 6, y: 0, w: 3, h: 2, visible: true, collapsed: false },
  { id: 'vacant', title: '空房數', x: 9, y: 0, w: 3, h: 2, visible: true, collapsed: false },
  { id: 'rooms', title: '即時房況', x: 0, y: 2, w: 12, h: 5, visible: true, collapsed: false },
  { id: 'guests', title: '昨今明入住資訊', x: 0, y: 7, w: 12, h: 4, visible: true, collapsed: false },
])

// 切換面板收折狀態
function toggleCollapse(index) {
  widgets.value[index].collapsed = !widgets.value[index].collapsed
}

// 入住資訊 Tab 切換
const activeGuestTab = ref('today') // today, yesterday, tomorrow

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
// 狀態排序邏輯 (DRY 原則)：N/R 優先，I 次之，其他依序
const STATUS_PRIORITY = { 'N': 0, 'R': 1, 'I': 2, 'O': 3, 'D': 4, 'C': 5, 'S': 6, 'CO': 7 };
function sortGuestsByStatus(guests) {
  return [...guests].sort((a, b) => {
    const priorityA = STATUS_PRIORITY[a.status_code] ?? 99;
    const priorityB = STATUS_PRIORITY[b.status_code] ?? 99;
    return priorityA - priorityB;
  });
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
        // 依狀態排序
        todayGuests.value = sortGuestsByStatus(result.data || [])
      }
    }
  } catch (error) {
    console.error('Fetch today checkin error:', error)
  } finally {
    guestsLoading.value = false
  }
}

// 昨日入住客人清單
const yesterdayGuests = ref([])
const yesterdayLoading = ref(true)

async function fetchYesterdayCheckin() {
  yesterdayLoading.value = true
  try {
    const res = await fetch(`${API_BASE}/api/pms/yesterday-checkin`, {
      signal: AbortSignal.timeout(5000)
    })
    if (res.ok) {
      const result = await res.json()
      if (result.success) {
        // 依狀態排序
        yesterdayGuests.value = sortGuestsByStatus(result.data || [])
      }
    }
  } catch (error) {
    console.error('Fetch yesterday checkin error:', error)
  } finally {
    yesterdayLoading.value = false
  }
}

// 明日入住客人清單
const tomorrowGuests = ref([])
const tomorrowLoading = ref(true)

async function fetchTomorrowCheckin() {
  tomorrowLoading.value = true
  try {
    const res = await fetch(`${API_BASE}/api/pms/tomorrow-checkin`, {
      signal: AbortSignal.timeout(5000)
    })
    if (res.ok) {
      const result = await res.json()
      if (result.success) {
        // 依狀態排序
        tomorrowGuests.value = sortGuestsByStatus(result.data || [])
      }
    }
  } catch (error) {
    console.error('Fetch tomorrow checkin error:', error)
  } finally {
    tomorrowLoading.value = false
  }
}

// 手動重新整理 - 全部即時更新
async function manualRefresh() {
  // 重設倒數計時器
  countdown.value = 30
  
  await Promise.all([
    fetchPMSDashboard(),
    fetchTodayCheckin(),
    fetchYesterdayCheckin(),
    fetchTomorrowCheckin(),
    fetchRoomStatus(),
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
  console.log('[DEBUG] Checking service status...');
  console.log('[DEBUG] API_BASE:', API_BASE);
  try {
    const res = await fetch(`${API_BASE}/api/status`, { 
      signal: AbortSignal.timeout(3000) 
    });
    console.log('[DEBUG] Response status:', res.status, res.ok);
    if (res.ok) {
      const data = await res.json();
      console.log('[DEBUG] API Response:', data);
      
      // 更新現有的 services 陣列項目，而不是替換整個陣列
      data.services.forEach(apiService => {
        const existing = services.value.find(s => s.id === apiService.id);
        if (existing) {
          existing.status = apiService.status;
          existing.name = apiService.name;
        } else {
          // 如果是新服務，加入到陣列
          services.value.push({
            id: apiService.id,
            name: apiService.name,
            icon: getServiceIcon(apiService.id),
            status: apiService.status
          });
        }
      });
      
      console.log('[DEBUG] Updated services:', services.value.map(s => ({id: s.id, status: s.status})));
    } else {
      console.error('[DEBUG] Response not OK:', res.status);
    }
  } catch (error) {
    console.error('[DEBUG] Fetch error:', error);
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
  // v-if 會自動處理 DOM 的添加/移除
  // 切換後需要重新初始化 GridStack
  nextTick(() => {
    if (grid) {
      grid.destroy(false)
    }
    grid = GridStack.init({
      column: 100,
      cellHeight: 60,
      margin: 15,
      animate: true,
      float: false,
      disableOneColumnMode: true,
      minRow: 1,
      resizable: { handles: 'all' },
      handle: '.widget-handle',
      draggable: { handle: '.widget-handle' }
    }, '.grid-stack')
  })
}

// 定時刷新狀態
let statusInterval = null
let pmsInterval = null
let guestInterval = null
let roomInterval = null
let countdownInterval = null

// 倒數計時器 (30秒為一個週期)
const countdown = ref(30)

// 倒數計時器邏輯
function startCountdown() {
  countdown.value = 30
  if (countdownInterval) clearInterval(countdownInterval)
  countdownInterval = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      countdown.value = 30
    }
  }, 1000)
}

onMounted(() => {
  // 服務狀態檢測 (每5秒)
  checkServiceStatus()
  statusInterval = setInterval(checkServiceStatus, 5000)
  
  // PMS 統計資料 (每15秒)
  fetchPMSDashboard()
  pmsInterval = setInterval(fetchPMSDashboard, 15000)
  
  // 入住客人清單 (每30秒)
  fetchTodayCheckin()
  fetchYesterdayCheckin()
  fetchTomorrowCheckin()
  guestInterval = setInterval(() => {
    fetchTodayCheckin()
    fetchYesterdayCheckin()
    fetchTomorrowCheckin()
  }, 30000)
  
  // 房間狀態 (每15秒)
  fetchRoomStatus()
  roomInterval = setInterval(fetchRoomStatus, 15000)
  
  // 啟動倒數計時器
  startCountdown()
  
  // WebSocket 即時通知連線
  connectWebSocket()
  
  // 初始化 GridStack
  nextTick(() => {
    grid = GridStack.init({
      column: 100,
      cellHeight: 60,
      margin: 15,
      animate: true,
      float: false,
      disableOneColumnMode: true,
      minRow: 1,
      resizable: { handles: 'all' },
      handle: '.widget-handle',  // 只有拖曳手柄可拖動
      draggable: { handle: '.widget-handle' }  // 明確指定拖曳區域
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

// 房間狀態資料（從 PMS API 獲取）
const rooms = ref([])
const roomsLoading = ref(false)

// 只顯示需要處理的房間（髒房、待檢查）
const dirtyRooms = computed(() => {
  return rooms.value.filter(r => 
    r.clean_status?.code === 'D' || 
    r.clean_status?.code === 'I'
  )
})

// 獲取房間狀態
async function fetchRoomStatus() {
  roomsLoading.value = true
  try {
    const res = await fetch('/api/pms/rooms/status')
    const data = await res.json()
    if (data.success && data.data?.rooms) {
      rooms.value = data.data.rooms.map(r => ({
        number: r.room_number,
        floor: r.floor,
        room_type: r.room_type_code,
        status: r.oos_status ? 'oos' : (r.clean_status?.code === 'D' ? 'dirty' : (r.clean_status?.code === 'I' ? 'inspecting' : 'clean')),
        clean_status: r.clean_status,
        oos_status: r.oos_status,
        oos_reason: r.oos_reason,
        room_status: r.room_status
      }))
    }
  } catch (e) {
    console.error('獲取房間狀態失敗:', e)
  } finally {
    roomsLoading.value = false
  }
}

// Tooltip 狀態
const hoveredRoom = ref(null)
const tooltipPos = ref({ x: 0, y: 0 })

function showTooltip(room, e) {
  if (!room.oos_reason) return
  hoveredRoom.value = room
  tooltipPos.value = { x: e.clientX, y: e.clientY }
}

function moveTooltip(e) {
  if (hoveredRoom.value) {
    tooltipPos.value = { x: e.clientX, y: e.clientY }
  }
}

function hideTooltip() {
  hoveredRoom.value = null
}

const activeMenu = ref('dashboard')

// 處理 menu 切換，切回 dashboard 時重新佈局 GridStack
function switchMenu(menuId) {
  activeMenu.value = menuId
  
  // 切回 dashboard 時，完全重新初始化 GridStack
  if (menuId === 'dashboard') {
    nextTick(() => {
      // 先銷毀舊的 grid
      if (grid) {
        grid.destroy(false)  // false = 不移除 DOM 元素
      }
      
      // 重新初始化 GridStack
      grid = GridStack.init({
        column: 100,
        cellHeight: 60,
        margin: 15,
        animate: true,
        float: false,
        disableOneColumnMode: true,
        minRow: 1,
        resizable: { handles: 'all' },
        handle: '.widget-handle',
        draggable: { handle: '.widget-handle' }
      }, '.grid-stack')
    })
  }
}

const menuItems = [
  { id: 'dashboard', icon: '📊', label: '儀表板' },
  { id: 'rooms', icon: '🏨', label: '房況監控' },
  { id: 'bookings', icon: '📅', label: '訂單管理' },
  { id: 'guests', icon: '👥', label: '旅客資料' },
  { id: 'pos', icon: '💰', label: 'POS 收銀' },
  { id: 'reports', icon: '📈', label: '報表中心' },
  { id: 'settings', icon: '⚙️', label: '系統設定' },
]

// 狀態圖示對照
const statusIcons = { 
  clean: '✓', 
  dirty: '🧹', 
  inspecting: '🔍', 
  oos: '🔧',
  occupied: '🛏️'
}
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
          @click="switchMenu(item.id)"
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
          <div v-if="activeMenu === 'dashboard'" class="refresh-group">
            <div class="countdown-timer" :class="{ warning: countdown <= 5 }">
              <span class="countdown-value">{{ countdown }}</span>
              <span class="countdown-unit">秒</span>
            </div>
            <button @click="manualRefresh" class="refresh-btn" title="重新整理全部資料">
              更新
            </button>
          </div>
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
        <div v-if="widgets[0].visible" class="grid-stack-item" gs-id="checkin" gs-x="0" gs-y="0" gs-w="25" gs-h="2" gs-min-w="15" gs-min-h="2">
          <div class="grid-stack-item-content stat-card">
            <div class="widget-handle"></div>
            <h3>今日入住</h3>
            <div class="stat-row">
              <span class="stat-value">{{ stats.todayCheckin }}</span>
              <span class="stat-unit">組</span>
            </div>
          </div>
        </div>

        <!-- 今日退房 -->
        <div v-if="widgets[1].visible" class="grid-stack-item" gs-id="checkout" gs-x="25" gs-y="0" gs-w="25" gs-h="2" gs-min-w="15" gs-min-h="2">
          <div class="grid-stack-item-content stat-card">
            <div class="widget-handle"></div>
            <h3>今日退房</h3>
            <div class="stat-row">
              <span class="stat-value">{{ stats.todayCheckout }}</span>
              <span class="stat-unit">組</span>
            </div>
          </div>
        </div>

        <!-- 住房率 -->
        <div v-if="widgets[2].visible" class="grid-stack-item" gs-id="occupancy" gs-x="50" gs-y="0" gs-w="25" gs-h="2" gs-min-w="15" gs-min-h="2">
          <div class="grid-stack-item-content stat-card">
            <div class="widget-handle"></div>
            <h3>住房率</h3>
            <div class="stat-row">
              <span class="stat-value">{{ stats.totalRooms > 0 ? Math.round(stats.occupiedRooms / stats.totalRooms * 100) : 0 }}</span>
              <span class="stat-unit">%</span>
            </div>
          </div>
        </div>

        <!-- 空房數 -->
        <div v-if="widgets[3].visible" class="grid-stack-item" gs-id="vacant" gs-x="75" gs-y="0" gs-w="25" gs-h="2" gs-min-w="15" gs-min-h="2">
          <div class="grid-stack-item-content stat-card">
            <div class="widget-handle"></div>
            <h3>空房數</h3>
            <div class="stat-row">
              <span class="stat-value">{{ stats.totalRooms - stats.occupiedRooms }}</span>
              <span class="stat-unit">間</span>
            </div>
          </div>
        </div>

        <!-- 房況面板（只顯示需處理的房間） -->
        <div v-if="widgets[4].visible" class="grid-stack-item" gs-id="rooms" gs-x="0" gs-y="2" gs-w="100" gs-h="4" gs-min-w="12" gs-min-h="3">
          <div class="grid-stack-item-content room-status-panel">
            <div class="widget-handle"></div>
            <h3>
              🧹 待處理房間 <span class="room-count">({{ dirtyRooms.length }})</span>
              <div class="status-legend">
                <span class="legend-item"><span class="dot dirty"></span>髒房</span>
                <span class="legend-item"><span class="dot inspecting"></span>待檢查</span>
              </div>
            </h3>
            <div v-if="roomsLoading" class="loading-text">載入中...</div>
            <div v-else-if="dirtyRooms.length === 0" class="empty-text">✅ 所有房間皆已清掃完成</div>
            <div v-else class="room-grid" @mouseleave="hideTooltip">
              <div v-for="room in dirtyRooms" 
                   :key="room.number" 
                   class="room-card" 
                   :class="room.status" 
                   @mouseenter="showTooltip(room, $event)" 
                   @mousemove="moveTooltip"
                   @mouseleave="hideTooltip">
                <span class="room-number">{{ room.number }}</span>
              </div>
            </div>
            <!-- 自定義 Tooltip -->
            <div v-if="hoveredRoom" class="custom-tooltip" :style="{ top: (tooltipPos.y + 15) + 'px', left: (tooltipPos.x + 15) + 'px' }">
              <span class="tooltip-title">🔧 房間瑕疵紀錄</span>
              <div class="tooltip-content">{{ hoveredRoom.oos_reason }}</div>
            </div>
          </div>
        </div>



        <!-- 入住資訊（Tab 切換：今日/昨日/明日） -->
        <div v-if="widgets[5].visible" class="grid-stack-item" :class="{ collapsed: widgets[5].collapsed }" gs-id="guests" gs-x="0" gs-y="6" gs-w="100" gs-h="10" gs-min-w="12" gs-min-h="4">
          <div class="grid-stack-item-content guest-cards-panel">
            <div class="panel-header">
              <div class="widget-handle"></div>
              <h3>🏨 入住資訊</h3>
              <div class="guest-tabs">
                <button :class="{ active: activeGuestTab === 'today' }" @click="activeGuestTab = 'today'">
                  今日 <span class="tab-count">({{ todayGuests.length }})</span>
                </button>
                <button :class="{ active: activeGuestTab === 'yesterday' }" @click="activeGuestTab = 'yesterday'">
                  昨日 <span class="tab-count">({{ yesterdayGuests.length }})</span>
                </button>
                <button :class="{ active: activeGuestTab === 'tomorrow' }" @click="activeGuestTab = 'tomorrow'">
                  明日 <span class="tab-count">({{ tomorrowGuests.length }})</span>
                </button>
              </div>
              <button class="collapse-btn" @click="toggleCollapse(5)">{{ widgets[5].collapsed ? '▼' : '▲' }}</button>
            </div>
            <div v-show="!widgets[5].collapsed" class="panel-body">
              <!-- 今日入住 -->
              <div v-show="activeGuestTab === 'today'">
                <div v-if="guestsLoading" class="loading-text">載入中...</div>
                <div v-else-if="todayGuests.length === 0" class="empty-text">今日無入住</div>
                <div v-else class="guest-cards-list">
                  <GuestCard v-for="g in todayGuests" :key="g.booking_id" :guest="g" />
                </div>
              </div>
              <!-- 昨日入住 -->
              <div v-show="activeGuestTab === 'yesterday'">
                <div v-if="yesterdayLoading" class="loading-text">載入中...</div>
                <div v-else-if="yesterdayGuests.length === 0" class="empty-text">昨日無入住</div>
                <div v-else class="guest-cards-list">
                  <GuestCard v-for="g in yesterdayGuests" :key="g.booking_id" :guest="g" />
                </div>
              </div>
              <!-- 明日入住 -->
              <div v-show="activeGuestTab === 'tomorrow'">
                <div v-if="tomorrowLoading" class="loading-text">載入中...</div>
                <div v-else-if="tomorrowGuests.length === 0" class="empty-text">明日無入住</div>
                <div v-else class="guest-cards-list">
                  <GuestCard v-for="g in tomorrowGuests" :key="g.booking_id" :guest="g" />
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
