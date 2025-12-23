<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, reactive } from "vue";
import { GridStack } from "gridstack";
import "gridstack/dist/gridstack.min.css";
import GuestCard from "./components/GuestCard.vue";

// API 基礎 URL（動態取得主機名）
const API_BASE = `http://${window.location.hostname}:3000`;

// GridStack 實例
let grid = null;

// 面板配置（可拖曳、可縮放、可隱藏、可收折）
const widgets = ref([
  {
    id: "checkin",
    title: "今日入住",
    x: 0,
    y: 0,
    w: 3,
    h: 2,
    visible: true,
    collapsed: false,
  },
  {
    id: "checkout",
    title: "今日退房",
    x: 3,
    y: 0,
    w: 3,
    h: 2,
    visible: true,
    collapsed: false,
  },
  {
    id: "occupancy",
    title: "住房率",
    x: 6,
    y: 0,
    w: 3,
    h: 2,
    visible: true,
    collapsed: false,
  },
  {
    id: "vacant",
    title: "空房數",
    x: 9,
    y: 0,
    w: 3,
    h: 2,
    visible: true,
    collapsed: false,
  },
  {
    id: "rooms",
    title: "即時房況",
    x: 0,
    y: 2,
    w: 12,
    h: 5,
    visible: true,
    collapsed: false,
  },
  {
    id: "sameday",
    title: "LINE 當日預訂",
    x: 0,
    y: 6,
    w: 12,
    h: 4,
    visible: true,
    collapsed: false,
  },
  {
    id: "guests",
    title: "入住資訊 (8日預覽)",
    x: 0,
    y: 10,
    w: 12,
    h: 4,
    visible: true,
    collapsed: false,
  },
]);

// 分頁配置：昨、今、明 + 未來 5 天
const GUEST_TABS_CONFIG = [
  { offset: -1, label: "昨日" },
  { offset: 0, label: "今日" },
  { offset: 1, label: "明日" },
  { offset: 2, label: null }, // 動態日期 1
  { offset: 3, label: null }, // 動態日期 2
  { offset: 4, label: null }, // 動態日期 3
  { offset: 5, label: null }, // 動態日期 4
  { offset: 6, label: null }, // 動態日期 5
];

// 格式化 Tab 標籤文字（含國字星期幾）
const WEEKDAYS = ["日", "一", "二", "三", "四", "五", "六"];

function getTabLabel(config) {
  if (config.label) return config.label;

  const date = new Date();
  date.setDate(date.getDate() + config.offset);
  const month = date.getMonth() + 1;
  const day = date.getDate();
  const weekday = WEEKDAYS[date.getDay()];
  return `${month}/${day} ${weekday}`;
}

// 切換面板收折狀態
function toggleCollapse(index) {
  widgets.value[index].collapsed = !widgets.value[index].collapsed;
}

// 入住資訊 Tab 切換
const activeGuestOffset = ref(0); // 以 offset 作為 key

// 使用 reactive 儲存各天資料，確保深層反應性
const guestTabs = reactive({});

// 初始化各分頁屬性
GUEST_TABS_CONFIG.forEach((cfg) => {
  guestTabs[cfg.offset.toString()] = { data: [], loading: false };
});

// 統計資料 (從 PMS API 取得)
const stats = ref({
  todayCheckin: 0,
  todayCheckout: 0,
  occupiedRooms: 0,
  totalRooms: 50,
  lastUpdate: null,
});

// PMS 資料載入狀態
const pmsLoading = ref(true);
const pmsError = ref(null);

// 從 Node.js Core 取得 PMS 統計資料
async function fetchPMSDashboard() {
  pmsLoading.value = true;
  pmsError.value = null;
  try {
    const res = await fetch(`${API_BASE}/api/pms/dashboard`, {
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) {
      const result = await res.json();
      if (result.success) {
        stats.value = result.data;
      } else {
        pmsError.value = result.error || "PMS API 回傳失敗";
      }
    } else {
      pmsError.value = `HTTP ${res.status}`;
    }
  } catch (error) {
    pmsError.value = error.message;
  } finally {
    pmsLoading.value = false;
  }
}
// 狀態排序邏輯 (DRY 原則)：N/R 優先，I 次之，其他依序
const STATUS_PRIORITY = { N: 0, R: 1, I: 2, O: 3, D: 4, C: 5, S: 6, CO: 7 };
function sortGuestsByStatus(guests) {
  return [...guests].sort((a, b) => {
    const priorityA = STATUS_PRIORITY[a.status_code] ?? 99;
    const priorityB = STATUS_PRIORITY[b.status_code] ?? 99;
    return priorityA - priorityB;
  });
}

// 展開狀態管理（使用數組儲存已展開的卡片 ID）
const expandedCards = ref([]);

function toggleCardExpand(cardKey) {
  const index = expandedCards.value.indexOf(cardKey);
  if (index > -1) {
    expandedCards.value = expandedCards.value.filter((id) => id !== cardKey);
  } else {
    expandedCards.value = [...expandedCards.value, cardKey];
  }
}

function isCardExpanded(cardKey) {
  return expandedCards.value.includes(cardKey);
}

// 智慧抓取各天入住資料
async function fetchGuestData(offset) {
  const tab = guestTabs[offset.toString()];
  if (!tab) return;

  tab.loading = true;
  try {
    const res = await fetch(`${API_BASE}/api/pms/checkin-by-offset/${offset}`, {
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) {
      const result = await res.json();
      if (result.success) {
        tab.data = sortGuestsByStatus(result.data || []);
      }
    }
  } catch (error) {
    console.error(`Fetch guests (offset ${offset}) error:`, error);
  } finally {
    tab.loading = false;
  }
}

// 供手動刷新與初始化使用
async function fetchAllGuestTabs() {
  await Promise.all(GUEST_TABS_CONFIG.map((cfg) => fetchGuestData(cfg.offset)));
}

// ============================================
// LINE 當日預訂（暫存訂單）
// ============================================
const sameDayBookings = ref([]);
const sameDayLoading = ref(false);
const sameDayError = ref(null);
const expandedOrders = ref([]); // 展開的大訂單 ID

// 按 order_id 分組訂單（用於收折顯示）
const groupedBookings = computed(() => {
  const groups = {};
  sameDayBookings.value.forEach((b) => {
    const orderId = b.order_id;
    if (!groups[orderId]) {
      groups[orderId] = {
        order_id: orderId,
        guest_name: b.guest_name,
        phone: b.phone,
        arrival_time: b.arrival_time,
        line_display_name: b.line_display_name,
        created_at: b.created_at,
        items: [],
      };
    }
    groups[orderId].items.push(b);
  });

  // 計算每個大訂單的整體狀態
  const groupList = Object.values(groups).map((group) => {
    const allCancelled = group.items.every((i) => i.status === "cancelled");
    const allCheckedIn = group.items.every((i) => i.status === "checked_in");
    const hasMismatch = group.items.some((i) => i.status === "mismatch");
    const hasPending = group.items.some(
      (i) => i.status === "pending" || i.status === "interrupted"
    );

    // 整體狀態優先順序：mismatch > pending > checked_in > cancelled
    let groupStatus = "pending";
    if (allCancelled) groupStatus = "cancelled";
    else if (allCheckedIn) groupStatus = "checked_in";
    else if (hasMismatch) groupStatus = "mismatch";
    else if (hasPending) groupStatus = "pending";

    return { ...group, groupStatus };
  });

  // 排序：KEY 錯在最上，接著待入住，最後已取消
  groupList.sort((a, b) => {
    const statusOrder = {
      mismatch: 0,
      pending: 1,
      checked_in: 2,
      cancelled: 3,
    };
    return (
      (statusOrder[a.groupStatus] || 1) - (statusOrder[b.groupStatus] || 1)
    );
  });

  // 過濾：已 KEY 的訂單不顯示
  return groupList.filter((g) => g.groupStatus !== "checked_in");
});

// 切換大訂單展開狀態
function toggleOrderExpand(orderId) {
  const idx = expandedOrders.value.indexOf(orderId);
  if (idx > -1) {
    expandedOrders.value = expandedOrders.value.filter((id) => id !== orderId);
  } else {
    expandedOrders.value = [...expandedOrders.value, orderId];
  }
}

function isOrderExpanded(orderId) {
  return expandedOrders.value.includes(orderId);
}

// 取得當日暫存訂單
async function fetchSameDayBookings() {
  sameDayLoading.value = true;
  sameDayError.value = null;
  try {
    const res = await fetch(`${API_BASE}/api/pms/same-day-bookings`, {
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) {
      const result = await res.json();
      if (result.success) {
        sameDayBookings.value = result.data?.bookings || [];
      } else {
        sameDayError.value = result.error || "取得暫存訂單失敗";
      }
    } else {
      sameDayError.value = `HTTP ${res.status}`;
    }
  } catch (error) {
    sameDayError.value = error.message;
  } finally {
    sameDayLoading.value = false;
  }
}

// 標記暫存訂單為已 KEY（含 PMS 匹配驗證）
async function markAsKeyed(orderId) {
  try {
    const res = await fetch(
      `${API_BASE}/api/pms/same-day-bookings/${orderId}/checkin`,
      {
        method: "PATCH",
        signal: AbortSignal.timeout(10000), // 加長超時，因為需要查詢 PMS
      }
    );
    if (res.ok) {
      const result = await res.json();
      if (result.success) {
        // 匹配成功，刷新列表
        await fetchSameDayBookings();
      } else if (result.mismatch) {
        // 匹配失敗，刷新列表顯示 KEY 錯狀態
        console.log("⚠️ PMS 匹配失敗:", result.error);
        await fetchSameDayBookings();
      }
    }
  } catch (error) {
    console.error("標記訂單失敗:", error);
  }
}

// 取消暫存訂單（標記而非刪除）
async function cancelBooking(orderId) {
  if (!confirm("確定要取消此訂單嗎？")) return;

  try {
    const res = await fetch(
      `${API_BASE}/api/pms/same-day-bookings/${orderId}/cancel`,
      {
        method: "PATCH",
        signal: AbortSignal.timeout(5000),
      }
    );
    if (res.ok) {
      const result = await res.json();
      if (result.success) {
        alert("✅ 訂單已取消");
        // 刷新列表
        await fetchSameDayBookings();
      } else {
        alert("❌ 取消失敗：" + (result.error?.message || "未知錯誤"));
      }
    } else {
      alert("❌ API 請求失敗：HTTP " + res.status);
    }
  } catch (error) {
    console.error("取消訂單失敗:", error);
    alert("❌ 取消失敗：" + error.message);
  }
}

// 批次標記所有房型為已 KEY
async function markAllAsKeyed(group) {
  // 包含 pending、interrupted、mismatch 狀態的項目都要處理
  const pendingItems = group.items.filter(
    (i) =>
      i.status === "pending" ||
      i.status === "interrupted" ||
      i.status === "mismatch"
  );
  if (pendingItems.length === 0) return;

  for (const item of pendingItems) {
    await markAsKeyed(item.item_id || item.order_id);
  }
}

// 批次取消所有房型
async function cancelAllBookings(group) {
  const pendingItems = group.items.filter(
    (i) =>
      i.status === "pending" ||
      i.status === "interrupted" ||
      i.status === "mismatch"
  );
  if (pendingItems.length === 0) return;

  if (!confirm(`確定要取消此訂單的所有 ${pendingItems.length} 間房嗎？`))
    return;

  for (const item of pendingItems) {
    try {
      const res = await fetch(
        `${API_BASE}/api/pms/same-day-bookings/${
          item.item_id || item.order_id
        }/cancel`,
        {
          method: "PATCH",
          signal: AbortSignal.timeout(5000),
        }
      );
    } catch (error) {
      console.error("批次取消失敗:", error);
    }
  }
  alert("✅ 已取消所有房型");
  await fetchSameDayBookings();
}

// 格式化日期時間（顯示時間部分）
function formatDateTime(isoString) {
  if (!isoString) return "-";
  const date = new Date(isoString);
  return date.toLocaleTimeString("zh-TW", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

// 手動重新整理 - 全部即時更新
async function manualRefresh() {
  // 重設倒數計時器
  countdown.value = 30;

  await Promise.all([
    fetchPMSDashboard(),
    fetchAllGuestTabs(),
    fetchRoomStatus(),
    fetchSameDayBookings(),
    checkServiceStatus(),
  ]);
}

// 服務狀態監控
const services = ref([
  { id: "bot", name: "AI 助手", icon: "🤖", status: "checking", port: 5001 },
  { id: "pms", name: "PMS API", icon: "🔌", status: "checking", port: 3000 },
  { id: "gmail", name: "Gmail", icon: "📧", status: "checking", port: null },
  { id: "ngrok", name: "Ngrok", icon: "🌐", status: "checking", port: null },
]);

// 檢查服務狀態 (透過 Node.js Core API)
async function checkServiceStatus() {
  console.log("[DEBUG] Checking service status...");
  console.log("[DEBUG] API_BASE:", API_BASE);
  try {
    const res = await fetch(`${API_BASE}/api/status`, {
      signal: AbortSignal.timeout(3000),
    });
    console.log("[DEBUG] Response status:", res.status, res.ok);
    if (res.ok) {
      const data = await res.json();
      console.log("[DEBUG] API Response:", data);

      // 更新現有的 services 陣列項目，而不是替換整個陣列
      data.services.forEach((apiService) => {
        const existing = services.value.find((s) => s.id === apiService.id);
        if (existing) {
          existing.status = apiService.status;
          existing.name = apiService.name;
        } else {
          // 如果是新服務，加入到陣列
          services.value.push({
            id: apiService.id,
            name: apiService.name,
            icon: getServiceIcon(apiService.id),
            status: apiService.status,
          });
        }
      });

      console.log(
        "[DEBUG] Updated services:",
        services.value.map((s) => ({ id: s.id, status: s.status }))
      );
    } else {
      console.error("[DEBUG] Response not OK:", res.status);
    }
  } catch (error) {
    console.error("[DEBUG] Fetch error:", error);
    services.value.forEach((s) => (s.status = "offline"));
  }
}

function getServiceIcon(id) {
  const icons = {
    bot: "🤖",
    core: "⚙️",
    ngrok: "🌐",
    gmail: "📧",
    pms: "🔌",
    admin: "🖥️", // Vue.js Admin
  };
  return icons[id] || "📦";
}

// 格式化時間顯示
function formatTime(timestamp) {
  if (!timestamp) return "";
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now - date;

  if (diff < 60000) return "剛剛";
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分鐘前`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小時前`;
  return date.toLocaleString("zh-TW");
}

// 切換面板顯示/隱藏
function toggleWidget(widgetId) {
  // v-if 會自動處理 DOM 的添加/移除
  // 切換後需要重新初始化 GridStack
  nextTick(() => {
    if (grid) {
      grid.destroy(false);
    }
    grid = GridStack.init(
      {
        column: 100,
        cellHeight: 60,
        margin: 15,
        animate: true,
        float: false,
        disableOneColumnMode: true,
        minRow: 1,
        resizable: { handles: "all" },
        handle: ".widget-handle",
        draggable: { handle: ".widget-handle" },
      },
      ".grid-stack"
    );
  });
}

// 定時刷新狀態
let statusInterval = null;
let pmsInterval = null;
let guestInterval = null;
let roomInterval = null;
let countdownInterval = null;

// 倒數計時器 (30秒為一個週期)
const countdown = ref(30);

// 倒數計時器邏輯
function startCountdown() {
  countdown.value = 30;
  if (countdownInterval) clearInterval(countdownInterval);
  countdownInterval = setInterval(() => {
    countdown.value--;
    if (countdown.value <= 0) {
      countdown.value = 30;
    }
  }, 1000);
}

onMounted(() => {
  // 服務狀態檢測 (每5秒)
  checkServiceStatus();
  statusInterval = setInterval(checkServiceStatus, 5000);

  // PMS 統計資料 (每15秒)
  fetchPMSDashboard();
  pmsInterval = setInterval(fetchPMSDashboard, 15000);

  // 入住客人清單 (每30秒)
  fetchAllGuestTabs();
  guestInterval = setInterval(fetchAllGuestTabs, 30000);

  // 房間狀態 (每15秒)
  fetchRoomStatus();
  roomInterval = setInterval(fetchRoomStatus, 15000);

  // LINE 當日預訂 (每30秒)
  fetchSameDayBookings();
  setInterval(fetchSameDayBookings, 30000);

  // 啟動倒數計時器
  startCountdown();

  // WebSocket 即時通知連線
  connectWebSocket();

  // 初始化 GridStack
  nextTick(() => {
    grid = GridStack.init(
      {
        column: 100,
        cellHeight: 60,
        margin: 15,
        animate: true,
        float: false,
        disableOneColumnMode: true,
        minRow: 1,
        resizable: { handles: "all" },
        handle: ".widget-handle", // 只有拖曳手柄可拖動
        draggable: { handle: ".widget-handle" }, // 明確指定拖曳區域
      },
      ".grid-stack"
    );
  });
});

// WebSocket 連線
let ws = null;
const notifications = ref([]);

function connectWebSocket() {
  ws = new WebSocket("ws://localhost:3001");

  ws.onopen = () => {
    console.log("🔗 WebSocket 已連線");
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      console.log("📩 收到通知:", msg);

      if (msg.type === "new_message") {
        // 新增到即時訊息列表
        notifications.value.unshift(msg.data);
        if (notifications.value.length > 20) notifications.value.pop();
      }

      // Bot 或櫃檯更新客戶擴充資訊（電話、抵達時間、特殊需求、櫃檯備註）
      if (msg.type === "update_guest" || msg.type === "supplement_update") {
        const payload = msg.data;
        const booking_id = payload.booking_id;

        // 更新所有列表中的對應訂單
        GUEST_TABS_CONFIG.forEach((cfg) => {
          const list = guestTabs[cfg.offset.toString()].data;
          const item = list.find(
            (g) => g.pms_id === booking_id || g.booking_id === booking_id
          );
          if (item) {
            if (payload.confirmed_phone)
              item.contact_phone = payload.confirmed_phone;
            if (payload.arrival_time)
              item.arrival_time_from_bot = payload.arrival_time;
            if (payload.ai_extracted_requests)
              item.special_request_from_bot = payload.ai_extracted_requests;
            if (payload.staff_memo !== undefined)
              item.staff_memo = payload.staff_memo;
            if (payload.line_name) item.line_name = payload.line_name;
            console.log(`✅ 已同步訂單 ${booking_id} 的擴充資料`);
          }
        });
      }
    } catch (e) {
      console.error("解析通知失敗:", e);
    }
  };

  ws.onclose = () => {
    console.log("🔌 WebSocket 斷開，5秒後重連...");
    setTimeout(connectWebSocket, 5000);
  };

  ws.onerror = (err) => {
    console.error("WebSocket 錯誤:", err);
  };
}

onUnmounted(() => {
  if (statusInterval) clearInterval(statusInterval);
  if (pmsInterval) clearInterval(pmsInterval);
  if (ws) ws.close();
  if (grid) grid.destroy();
});

// 房間狀態資料（從 PMS API 獲取）
const rooms = ref([]);
const roomsLoading = ref(false);

// 只顯示需要處理的房間（髒房、待檢查）
const dirtyRooms = computed(() => {
  return rooms.value.filter(
    (r) => r.clean_status?.code === "D" || r.clean_status?.code === "I"
  );
});

// 獲取房間狀態
async function fetchRoomStatus() {
  roomsLoading.value = true;
  try {
    const res = await fetch("/api/pms/rooms/status");
    const data = await res.json();
    if (data.success && data.data?.rooms) {
      rooms.value = data.data.rooms.map((r) => ({
        number: r.room_number,
        floor: r.floor,
        room_type: r.room_type_code,
        status: r.oos_status
          ? "oos"
          : r.clean_status?.code === "D"
          ? "dirty"
          : r.clean_status?.code === "I"
          ? "inspecting"
          : "clean",
        clean_status: r.clean_status,
        oos_status: r.oos_status,
        oos_reason: r.oos_reason,
        room_status: r.room_status,
      }));
    }
  } catch (e) {
    console.error("獲取房間狀態失敗:", e);
  } finally {
    roomsLoading.value = false;
  }
}

// Tooltip 狀態
const hoveredRoom = ref(null);
const tooltipPos = ref({ x: 0, y: 0 });

function showTooltip(room, e) {
  if (!room.oos_reason) return;
  hoveredRoom.value = room;
  tooltipPos.value = { x: e.clientX, y: e.clientY };
}

function moveTooltip(e) {
  if (hoveredRoom.value) {
    tooltipPos.value = { x: e.clientX, y: e.clientY };
  }
}

function hideTooltip() {
  hoveredRoom.value = null;
}

const activeMenu = ref("dashboard");

// 處理 menu 切換，切回 dashboard 時重新佈局 GridStack
function switchMenu(menuId) {
  activeMenu.value = menuId;

  // 切回 dashboard 時，完全重新初始化 GridStack
  if (menuId === "dashboard") {
    nextTick(() => {
      // 先銷毀舊的 grid
      if (grid) {
        grid.destroy(false); // false = 不移除 DOM 元素
      }

      // 重新初始化 GridStack
      grid = GridStack.init(
        {
          column: 100,
          cellHeight: 60,
          margin: 15,
          animate: true,
          float: false,
          disableOneColumnMode: true,
          minRow: 1,
          resizable: { handles: "all" },
          handle: ".widget-handle",
          draggable: { handle: ".widget-handle" },
        },
        ".grid-stack"
      );
    });
  }
}

const menuItems = [
  { id: "dashboard", icon: "📊", label: "儀表板" },
  { id: "rooms", icon: "🏨", label: "房況監控" },
  { id: "bookings", icon: "📅", label: "訂單管理" },
  { id: "guests", icon: "👥", label: "旅客資料" },
  { id: "pos", icon: "💰", label: "POS 收銀" },
  { id: "reports", icon: "📈", label: "報表中心" },
  { id: "settings", icon: "⚙️", label: "系統設定" },
];

// 狀態圖示對照
const statusIcons = {
  clean: "✓",
  dirty: "🧹",
  inspecting: "🔍",
  oos: "🔧",
  occupied: "🛏️",
};
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
          <input
            type="checkbox"
            v-model="w.visible"
            @change="toggleWidget(w.id)"
          />
          <span>{{ w.title }}</span>
        </label>
      </div>
    </aside>

    <!-- 主內容區 -->
    <main class="main-content">
      <header class="header">
        <h2>{{ menuItems.find((m) => m.id === activeMenu)?.label }}</h2>
        <div class="header-right">
          <div v-if="activeMenu === 'dashboard'" class="refresh-group">
            <div class="countdown-timer" :class="{ warning: countdown <= 5 }">
              <span class="countdown-value">{{ countdown }}</span>
              <span class="countdown-unit">秒</span>
            </div>
            <button
              @click="manualRefresh"
              class="refresh-btn"
              title="重新整理全部資料"
            >
              更新
            </button>
          </div>
          <div class="header-services">
            <div
              v-for="service in services"
              :key="service.id"
              class="header-service-item"
            >
              <span class="service-name-small">{{ service.name }}</span>
              <span class="service-status-dot" :class="service.status"></span>
            </div>
          </div>
        </div>
      </header>

      <!-- 儀表板視圖 -->
      <div v-if="activeMenu === 'dashboard'" class="grid-stack">
        <!-- 今日入住 -->
        <div
          v-if="widgets[0].visible"
          class="grid-stack-item"
          gs-id="checkin"
          gs-x="0"
          gs-y="0"
          gs-w="25"
          gs-h="2"
          gs-min-w="15"
          gs-min-h="2"
        >
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
        <div
          v-if="widgets[1].visible"
          class="grid-stack-item"
          gs-id="checkout"
          gs-x="25"
          gs-y="0"
          gs-w="25"
          gs-h="2"
          gs-min-w="15"
          gs-min-h="2"
        >
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
        <div
          v-if="widgets[2].visible"
          class="grid-stack-item"
          gs-id="occupancy"
          gs-x="50"
          gs-y="0"
          gs-w="25"
          gs-h="2"
          gs-min-w="15"
          gs-min-h="2"
        >
          <div class="grid-stack-item-content stat-card">
            <div class="widget-handle"></div>
            <h3>住房率</h3>
            <div class="stat-row">
              <span class="stat-value">{{
                stats.totalRooms > 0
                  ? Math.round((stats.occupiedRooms / stats.totalRooms) * 100)
                  : 0
              }}</span>
              <span class="stat-unit">%</span>
            </div>
          </div>
        </div>

        <!-- 空房數 -->
        <div
          v-if="widgets[3].visible"
          class="grid-stack-item"
          gs-id="vacant"
          gs-x="75"
          gs-y="0"
          gs-w="25"
          gs-h="2"
          gs-min-w="15"
          gs-min-h="2"
        >
          <div class="grid-stack-item-content stat-card">
            <div class="widget-handle"></div>
            <h3>空房數</h3>
            <div class="stat-row">
              <span class="stat-value">{{
                stats.totalRooms - stats.occupiedRooms
              }}</span>
              <span class="stat-unit">間</span>
            </div>
          </div>
        </div>

        <!-- 房況面板（只顯示需處理的房間） -->
        <div
          v-if="widgets[4].visible"
          class="grid-stack-item"
          gs-id="rooms"
          gs-x="0"
          gs-y="2"
          gs-w="100"
          gs-h="4"
          gs-min-w="12"
          gs-min-h="3"
        >
          <div class="grid-stack-item-content room-status-panel">
            <div class="widget-handle"></div>
            <h3>
              🧹 待處理房間
              <span class="room-count">({{ dirtyRooms.length }})</span>
              <div class="status-legend">
                <span class="legend-item"
                  ><span class="dot dirty"></span>髒房</span
                >
                <span class="legend-item"
                  ><span class="dot inspecting"></span>待檢查</span
                >
              </div>
            </h3>
            <div v-if="roomsLoading" class="loading-text">載入中...</div>
            <div v-else-if="dirtyRooms.length === 0" class="empty-text">
              ✅ 所有房間皆已清掃完成
            </div>
            <div v-else class="room-grid" @mouseleave="hideTooltip">
              <div
                v-for="room in dirtyRooms"
                :key="room.number"
                class="room-card"
                :class="room.status"
                @mouseenter="showTooltip(room, $event)"
                @mousemove="moveTooltip"
                @mouseleave="hideTooltip"
              >
                <span class="room-number">{{ room.number }}</span>
              </div>
            </div>
            <!-- 自定義 Tooltip -->
            <div
              v-if="hoveredRoom"
              class="custom-tooltip"
              :style="{
                top: tooltipPos.y + 15 + 'px',
                left: tooltipPos.x + 15 + 'px',
              }"
            >
              <span class="tooltip-title">🔧 房間瑕疵紀錄</span>
              <div class="tooltip-content">{{ hoveredRoom.oos_reason }}</div>
            </div>
          </div>
        </div>

        <!-- LINE 當日預訂 (暫存訂單) -->
        <div
          v-if="widgets[5].visible"
          class="grid-stack-item"
          :class="{ collapsed: widgets[5].collapsed }"
          gs-id="sameday"
          gs-x="0"
          gs-y="6"
          gs-w="100"
          gs-h="4"
          gs-min-w="12"
          gs-min-h="3"
        >
          <div class="grid-stack-item-content same-day-panel">
            <div class="panel-header">
              <div class="widget-handle"></div>
              <h3>
                📱 LINE 當日預訂
                <span class="panel-count">({{ sameDayBookings.length }})</span>
              </h3>
              <button class="collapse-btn" @click="toggleCollapse(5)">
                {{ widgets[5].collapsed ? "▼" : "▲" }}
              </button>
            </div>
            <div v-show="!widgets[5].collapsed" class="panel-body">
              <div v-if="sameDayLoading" class="loading-text">載入中...</div>
              <div v-else-if="sameDayError" class="error-text">
                {{ sameDayError }}
              </div>
              <div v-else-if="groupedBookings.length === 0" class="empty-text">
                📋 目前無 LINE 當日預訂
              </div>
              <div v-else class="same-day-table-wrapper">
                <!-- 使用收折顯示：大訂單 > 小訂單 -->
                <div
                  v-for="group in groupedBookings"
                  :key="group.order_id"
                  class="order-group"
                >
                  <!-- 大訂單標題列（可點擊展開/收折） -->
                  <div class="order-group-header">
                    <span
                      class="expand-icon"
                      @click="toggleOrderExpand(group.order_id)"
                      >{{ isOrderExpanded(group.order_id) ? "▼" : "▶" }}</span
                    >
                    <span
                      class="order-id"
                      @click="toggleOrderExpand(group.order_id)"
                      >{{ group.order_id }}</span
                    >
                    <span
                      class="guest-info"
                      @click="toggleOrderExpand(group.order_id)"
                    >
                      👤 {{ group.guest_name || "-" }}
                      <span v-if="group.line_display_name" class="line-name"
                        >({{ group.line_display_name }})</span
                      >
                      | 📞 {{ group.phone || "-" }} | 🕐
                      {{ group.arrival_time || "-" }}
                    </span>
                    <span class="room-count-badge"
                      >{{ group.items.length }} 間</span
                    >
                    <!-- 大訂單狀態顯示 -->
                    <span
                      v-if="group.groupStatus === 'cancelled'"
                      class="group-status-cancelled"
                      >✕ 已取消</span
                    >
                    <span
                      v-else-if="group.groupStatus === 'checked_in'"
                      class="group-status-done"
                      >✓ 已 KEY</span
                    >
                    <span
                      v-else-if="group.groupStatus === 'mismatch'"
                      class="group-status-mismatch"
                      >⚠ KEY 錯</span
                    >
                    <span
                      class="special-requests"
                      v-if="group.items[0]?.special_requests"
                      >📝 {{ group.items[0].special_requests }}</span
                    >
                    <!-- 批次操作按鈕 -->
                    <div class="group-actions" @click.stop>
                      <!-- 正常狀態：已 KEY 按鈕 -->
                      <button
                        class="key-btn-sm"
                        @click="markAllAsKeyed(group)"
                        v-if="group.groupStatus === 'pending'"
                      >
                        已 KEY
                      </button>
                      <!-- KEY 錯狀態：重新匹配按鈕 -->
                      <button
                        class="mismatch-btn-sm"
                        @click="markAllAsKeyed(group)"
                        v-if="group.groupStatus === 'mismatch'"
                      >
                        重新匹配
                      </button>
                      <button
                        class="cancel-btn-sm"
                        @click="cancelAllBookings(group)"
                        v-if="
                          group.groupStatus === 'pending' ||
                          group.groupStatus === 'mismatch'
                        "
                      >
                        全部取消
                      </button>
                    </div>
                  </div>

                  <!-- 小訂單列表（展開時顯示） -->
                  <div
                    v-show="isOrderExpanded(group.order_id)"
                    class="order-items"
                  >
                    <div
                      v-for="item in group.items"
                      :key="item.item_id || item.order_id"
                      class="order-item-row"
                      :class="{
                        'checked-in': item.status === 'checked_in',
                        cancelled: item.status === 'cancelled',
                      }"
                    >
                      <span class="item-room">
                        {{ item.room_type_name || item.room_type_code }} x{{
                          item.room_count
                        }}
                        <span class="bed-type" v-if="item.bed_type">{{
                          item.bed_type
                        }}</span>
                      </span>
                      <span class="item-status">
                        <span
                          v-if="item.status === 'checked_in'"
                          class="done-text"
                          >✓ 已 KEY</span
                        >
                        <span
                          v-else-if="item.status === 'cancelled'"
                          class="cancelled-text"
                          >✕ 已取消</span
                        >
                        <!-- pending 狀態不顯示文字 -->
                      </span>
                      <span
                        class="item-actions"
                        v-if="
                          item.status === 'pending' ||
                          item.status === 'interrupted'
                        "
                      >
                        <button
                          class="cancel-btn-sm"
                          @click.stop="
                            cancelBooking(item.item_id || item.order_id)
                          "
                        >
                          取消
                        </button>
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 入住資訊（Tab 切換：今日/昨日/明日） -->
        <div
          v-if="widgets[6].visible"
          class="grid-stack-item"
          :class="{ collapsed: widgets[6].collapsed }"
          gs-id="guests"
          gs-x="0"
          gs-y="10"
          gs-w="100"
          gs-h="10"
          gs-min-w="12"
          gs-min-h="4"
        >
          <div class="grid-stack-item-content guest-cards-panel">
            <div class="panel-header">
              <div class="widget-handle"></div>
              <h3>🏨 入住資訊</h3>
              <div class="guest-tabs">
                <button
                  v-for="cfg in GUEST_TABS_CONFIG"
                  :key="'tab-' + cfg.offset"
                  :class="{ active: activeGuestOffset === cfg.offset }"
                  @click="activeGuestOffset = cfg.offset"
                  class="guest-tab-btn"
                >
                  {{ getTabLabel(cfg) }}
                  <span class="tab-count"
                    >({{
                      guestTabs[cfg.offset.toString()]?.data.length || 0
                    }})</span
                  >
                </button>
              </div>
              <button class="collapse-btn" @click="toggleCollapse(6)">
                {{ widgets[6].collapsed ? "▼" : "▲" }}
              </button>
            </div>
            <div v-show="!widgets[6].collapsed" class="panel-body">
              <template
                v-for="cfg in GUEST_TABS_CONFIG"
                :key="'content-' + cfg.offset"
              >
                <div v-if="activeGuestOffset === cfg.offset">
                  <div
                    v-if="guestTabs[cfg.offset.toString()]?.loading"
                    class="loading-text"
                  >
                    載入中...
                  </div>
                  <div
                    v-else-if="
                      guestTabs[cfg.offset.toString()]?.data.length === 0
                    "
                    class="empty-text"
                  >
                    {{ getTabLabel(cfg) }}無入住
                  </div>
                  <div v-else class="guest-cards-list">
                    <GuestCard
                      v-for="g in guestTabs[cfg.offset.toString()].data"
                      :key="cfg.offset + '-' + g.booking_id"
                      :guest="g"
                      :isExpanded="
                        isCardExpanded(cfg.offset + '-' + g.booking_id)
                      "
                      @toggle="
                        toggleCardExpand(cfg.offset + '-' + g.booking_id)
                      "
                    />
                  </div>
                </div>
              </template>
            </div>
          </div>
        </div>
      </div>

      <!-- 其他頁面佔位 -->
      <div v-else class="placeholder">
        <p style="text-align: center; color: #888; padding: 100px">
          📦
          {{ menuItems.find((m) => m.id === activeMenu)?.label }} 功能開發中...
        </p>
      </div>
    </main>
  </div>
</template>
