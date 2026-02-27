<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, reactive, watch } from "vue";
import { useI18n } from "vue-i18n";
import { setLocale } from "./i18n/index.js";
import { GridStack } from "gridstack";
import "gridstack/dist/gridstack.min.css";
import GuestCard from "./components/GuestCard.vue";
import { translateApiValue, translateText, clearTranslationCache } from "./utils/translate.js";

// i18n 翻譯函數（tm 用於取得陣列/物件型翻譯值）
const { t, tm, locale } = useI18n();

// 語言切換
// 自由文字翻譯快取（reactive，翻譯完成後自動更新 UI）
const freeTextCache = reactive({});

/**
 * 取得自由文字的翻譯結果
 * 先顯示原文，背景呼叫 Google Translate API 翻譯完成後自動更新
 */
function getTranslatedText(text) {
  if (!text || locale.value === 'zh-TW') return text;
  const cacheKey = `${locale.value}:${text}`;
  if (freeTextCache[cacheKey]) return freeTextCache[cacheKey];
  // 先設定載入中，背景翻譯
  freeTextCache[cacheKey] = text; // 先顯示原文
  translateText(text, locale.value === 'id' ? 'id' : 'zh-TW').then(translated => {
    freeTextCache[cacheKey] = translated;
  });
  return freeTextCache[cacheKey];
}

/**
 * 翻譯 API 固定值（對照表翻譯）
 */
function tApi(value) {
  return translateApiValue(value, t);
}

function switchLanguage(lang) {
  setLocale(lang);
}

// API 基礎 URL（動態取得主機名）
const API_BASE = `http://${window.location.hostname}:3000`;

// GridStack 實例
let grid = null;

// 面板配置（可拖曳、可縮放、可隱藏、可收折）
// Widget 標題的 i18n 對照表
const widgetTitleKeys = {
  checkin: 'dashboard.today_checkin',
  checkout: 'dashboard.today_checkout',
  occupancy: 'dashboard.occupancy',
  vacant: 'dashboard.vacant',
  rooms: 'dashboard.rooms',
  sameday: 'dashboard.sameday',
  guests: 'dashboard.guest_info',
  'ai-needs': 'dashboard.ai_needs',
};

const widgets = ref([
  { id: "checkin", x: 0, y: 0, w: 25, h: 2, visible: true, collapsed: false },
  { id: "checkout", x: 25, y: 0, w: 25, h: 2, visible: true, collapsed: false },
  { id: "occupancy", x: 50, y: 0, w: 25, h: 2, visible: true, collapsed: false },
  { id: "vacant", x: 75, y: 0, w: 25, h: 2, visible: true, collapsed: false },
  { id: "rooms", x: 0, y: 2, w: 100, h: 5, visible: true, collapsed: false },
  { id: "sameday", x: 0, y: 6, w: 100, h: 4, visible: true, collapsed: false },
  { id: "guests", x: 0, y: 10, w: 100, h: 4, visible: true, collapsed: false },
  { id: "ai-needs", x: 0, y: 14, w: 100, h: 4, visible: true, collapsed: false },
]);

// 取得 widget 翻譯標題
function getWidgetTitle(id) {
  return t(widgetTitleKeys[id] || id);
}

// 分頁配置：昨、今、明 + 未來 5 天
const GUEST_TABS_CONFIG = [
  { offset: -1, labelKey: "guests.tab_yesterday" },
  { offset: 0, labelKey: "guests.tab_today" },
  { offset: 1, labelKey: "guests.tab_tomorrow" },
  { offset: 2, labelKey: null },
  { offset: 3, labelKey: null },
  { offset: 4, labelKey: null },
  { offset: 5, labelKey: null },
  { offset: 6, labelKey: null },
];

// 格式化 Tab 標籤文字（含在地化星期幾）
function getTabLabel(config) {
  if (config.labelKey) return t(config.labelKey);

  const weekdays = tm('guests.weekdays');
  const date = new Date();
  date.setDate(date.getDate() + config.offset);
  const month = date.getMonth() + 1;
  const day = date.getDate();
  const weekday = weekdays[date.getDay()];
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
        pmsError.value = result.error || t('common.pms_fail');
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

// ============================================
// AI 需求速覽（複用 guestTabs 資料）
// ============================================
const activeAiNeedsOffset = ref(0); // 獨立 Tab 狀態

// 從既有 guestTabs 過濾有 AI 需求的訂單
function getAiNeedsGuests(offset) {
  const tab = guestTabs[offset.toString()];
  if (!tab) return [];
  return tab.data.filter(g =>
    g.special_request_from_bot || g.customer_remarks || g.staff_memo
  );
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
// 同步回覆（手動回覆記錄）
// ============================================
const chatUsers = ref([]);
const chatUsersLoading = ref(false);
const todayCheckinUsers = ref([]);
const todayCheckinLoading = ref(false);
const selectedUserId = ref(null);
const syncReplyMessage = ref('');
const syncReplyStatus = ref(null); // null | 'sending' | 'success' | 'error'

// 取得當日入住客人的 LINE 資訊
async function fetchTodayCheckinUsers() {
  todayCheckinLoading.value = true;
  try {
    const res = await fetch(`${API_BASE}/api/chat/today-checkin-users`, {
      signal: AbortSignal.timeout(8000),
    });
    if (res.ok) {
      const result = await res.json();
      if (result.success) {
        todayCheckinUsers.value = result.data || [];
      }
    }
  } catch (error) {
    console.error('取得當日入住客人失敗:', error);
  } finally {
    todayCheckinLoading.value = false;
  }
}

async function fetchChatUsers() {
  chatUsersLoading.value = true;
  // 同時載入當日入住客人
  fetchTodayCheckinUsers();
  try {
    const res = await fetch(`${API_BASE}/api/chat/users`, {
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) {
      const result = await res.json();
      if (result.success) {
        chatUsers.value = result.data || [];
      }
    }
  } catch (error) {
    console.error('取得客人列表失敗:', error);
  } finally {
    chatUsersLoading.value = false;
  }
}

async function syncReply() {
  if (!selectedUserId.value || !syncReplyMessage.value.trim()) return;

  syncReplyStatus.value = 'sending';
  try {
    const res = await fetch(`${API_BASE}/api/chat/sync-reply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: selectedUserId.value,
        message: syncReplyMessage.value.trim(),
        send_line: true,
      }),
    });
    if (res.ok) {
      const result = await res.json();
      if (result.success) {
        syncReplyStatus.value = 'success';
        syncReplyMessage.value = '';
        // 重新載入歷史紀錄
        fetchSyncHistory(selectedUserId.value);
        // 3 秒後清除成功狀態
        setTimeout(() => { syncReplyStatus.value = null; }, 3000);
      } else {
        syncReplyStatus.value = 'error';
      }
    }
  } catch (error) {
    console.error('同步回覆失敗:', error);
    syncReplyStatus.value = 'error';
  }
}

// 格式化最後對話時間
function formatLastActivity(isoString) {
  if (!isoString) return '';
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now - date;
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return t('time.just_now');
  if (diffMin < 60) return t('time.minutes_ago', { n: diffMin });
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return t('time.hours_ago', { n: diffHour });
  const diffDay = Math.floor(diffHour / 24);
  return t('time.days_ago', { n: diffDay });
}

// 取得選中客人的顯示名
const selectedUserName = computed(() => {
  const user = chatUsers.value.find(u => u.user_id === selectedUserId.value);
  return user?.display_name || '';
});

// 同步回覆歷史紀錄
const syncHistory = ref([]);
const syncHistoryLoading = ref(false);

async function fetchSyncHistory(userId) {
  if (!userId) { syncHistory.value = []; return; }
  syncHistoryLoading.value = true;
  try {
    const res = await fetch(`${API_BASE}/api/chat/sync-history/${userId}`, {
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) {
      const result = await res.json();
      if (result.success) {
        syncHistory.value = result.data || [];
      }
    }
  } catch (error) {
    console.error('取得同步歷史失敗:', error);
  } finally {
    syncHistoryLoading.value = false;
  }
}

// 最後 3 段對話（所有角色）
const recentMessages = ref([]);
const recentMessagesLoading = ref(false);

async function fetchRecentMessages(userId) {
  if (!userId) { recentMessages.value = []; return; }
  recentMessagesLoading.value = true;
  try {
    const res = await fetch(`${API_BASE}/api/chat/recent/${userId}?count=5`, {
      signal: AbortSignal.timeout(5000),
    });
    if (res.ok) {
      const result = await res.json();
      if (result.success) {
        recentMessages.value = result.data || [];
      }
    }
  } catch (error) {
    console.error('取得最近對話失敗:', error);
  } finally {
    recentMessagesLoading.value = false;
  }
}

// 選中客人時自動載入歷史和最近對話
watch(selectedUserId, (newId) => {
  fetchSyncHistory(newId);
  fetchRecentMessages(newId);
});

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
        sameDayError.value = result.error || t('booking.fetch_fail');
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
  if (!confirm(t('booking.confirm_cancel'))) return;

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
        alert(t('booking.cancel_success'));
        // 刷新列表
        await fetchSameDayBookings();
      } else {
        alert(t('booking.cancel_fail', { error: result.error?.message || '未知錯誤' }));
      }
    } else {
      alert(t('booking.cancel_api_fail', { status: res.status }));
    }
  } catch (error) {
    console.error("取消訂單失敗:", error);
    alert(t('booking.cancel_fail', { error: error.message }));
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

  if (!confirm(t('booking.confirm_cancel_all', { count: pendingItems.length })))
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
  alert(t('booking.cancel_all_done'));
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
  { id: "bot", nameKey: "services.ai_assistant", icon: "🤖", status: "checking", port: 5001 },
  { id: "pms", nameKey: "services.pms_api", icon: "🔌", status: "checking", port: 3000 },
  { id: "gmail", nameKey: "services.gmail", icon: "📧", status: "checking", port: null },
  { id: "ngrok", nameKey: "services.ngrok", icon: "🌐", status: "checking", port: null },
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
          // 如果是新服務，加入到陣列（必須包含 nameKey 供 i18n 使用）
          services.value.push({
            id: apiService.id,
            name: apiService.name,
            nameKey: `services.${apiService.id}`,
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

  if (diff < 60000) return t('time.just_now');
  if (diff < 3600000) return t('time.minutes_ago', { n: Math.floor(diff / 60000) });
  if (diff < 86400000) return t('time.hours_ago', { n: Math.floor(diff / 3600000) });
  return date.toLocaleString(locale.value === 'id' ? 'id-ID' : 'zh-TW');
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
  // 載入已確認的今日入住房間
  loadAcknowledgedRooms();

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

  // 同步回覆面板：載入客人列表
  fetchChatUsers();

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

// 已確認的今日入住房間（點擊後停止閃爍，後端資料庫同步）
const acknowledgedRooms = ref(new Set());

// 從後端 API 載入已確認房間（跨電腦同步）
async function loadAcknowledgedRooms() {
  try {
    const res = await fetch("/api/room-acknowledgments");
    const data = await res.json();
    if (data.success && data.rooms) {
      acknowledgedRooms.value = new Set(data.rooms);
      console.log(`✅ 已載入 ${data.rooms.length} 間確認房間（${data.date}）`);
    }
  } catch (e) {
    console.error("載入已確認房間失敗:", e);
  }
}

// 確認房間（呼叫後端 API）
async function acknowledgeRoom(roomNumber) {
  // 立即更新 UI
  acknowledgedRooms.value.add(roomNumber);
  acknowledgedRooms.value = new Set(acknowledgedRooms.value);
  
  // 呼叫後端 API（跨電腦同步）
  try {
    await fetch("/api/room-acknowledgments", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ room_number: roomNumber }),
    });
  } catch (e) {
    console.error("儲存確認狀態失敗:", e);
  }
}

// 清除所有已確認（僅清除本地 UI，後端資料保留）
function clearAcknowledgedRooms() {
  acknowledgedRooms.value = new Set();
}

// 計算今日入住的房號列表
const todayCheckinRoomNumbers = computed(() => {
  const todayGuests = guestTabs["0"]?.data || [];
  const roomNumbers = new Set();
  todayGuests.forEach((guest) => {
    // 從 room_numbers 陣列取得房號
    if (guest.room_numbers && Array.isArray(guest.room_numbers)) {
      guest.room_numbers.forEach((num) => roomNumbers.add(num));
    }
    // 也可能是 room_number 單一欄位
    if (guest.room_number) {
      roomNumbers.add(guest.room_number);
    }
  });
  return roomNumbers;
});

// 只顯示需要處理的房間
// 邏輯：
// 1. 排除 OOS（維修中）的房間
// 2. 今日入住房號（不管清潔狀態）+ 尚未確認 → 顯示並閃爍
// 3. 點擊確認後 → 恢復原本邏輯（只顯示髒房/待檢查）
const dirtyRooms = computed(() => {
  return rooms.value
    .filter((r) => {
      // 排除維修房（ROOM_STA = R）
      if (r.room_status?.code === "R") {
        return false;
      }
      
      const isDirtyOrInspecting = r.clean_status?.code === "D" || r.clean_status?.code === "I";
      const isTodayCheckin = todayCheckinRoomNumbers.value.has(r.number);
      const isAcknowledged = acknowledgedRooms.value.has(r.number);
      
      // 今日入住 + 尚未確認 → 強制顯示（不管清潔狀態）
      if (isTodayCheckin && !isAcknowledged) {
        return true;
      }
      
      // 已確認 或 非今日入住 → 恢復原本邏輯（只顯示髒房/待檢查）
      return isDirtyOrInspecting;
    })
    .map((r) => {
      const isTodayCheckin = todayCheckinRoomNumbers.value.has(r.number);
      const isAcknowledged = acknowledgedRooms.value.has(r.number);
      return {
        ...r,
        isTodayCheckin,
        isAcknowledged,
        // 閃爍條件：今日入住 且 尚未確認
        shouldBlink: isTodayCheckin && !isAcknowledged,
      };
    });
});

// 今日入住且尚未確認的待處理房間數量（閃爍中）
const urgentRoomCount = computed(() => {
  return dirtyRooms.value.filter((r) => r.shouldBlink).length;
});

// 已確認的今日入住房間數量（已停止閃爍）
const acknowledgedCount = computed(() => {
  return dirtyRooms.value.filter((r) => r.isTodayCheckin && r.isAcknowledged).length;
});

// 待處理房間按樓層分組（2F, 3F, 5F, 6F）
const floors = ["2", "3", "5", "6"];
const dirtyRoomsByFloor = computed(() => {
  const grouped = {};
  floors.forEach((floor) => {
    grouped[floor] = dirtyRooms.value
      .filter((r) => r.number && r.number.startsWith(floor))
      .sort((a, b) => parseInt(a.number) - parseInt(b.number));
  });
  return grouped;
});

// 點擊房間：今日入住房間停止閃爍，恢復原本邏輯
function handleRoomClick(room) {
  if (room.shouldBlink) {
    // 閃爍中的今日入住房間：確認後停止閃爍，恢復原本邏輯
    acknowledgeRoom(room.number);
  }
  // 非閃爍房間：不做額外動作，保持原本行為（hover tooltip）
}

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
const sidebarOpen = ref(false);
function toggleSidebar() { sidebarOpen.value = !sidebarOpen.value; }
function closeSidebar() { sidebarOpen.value = false; }

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
  { id: "dashboard", icon: "📊", labelKey: "nav.dashboard" },
  { id: "sync-reply", icon: "📝", labelKey: "nav.sync_reply" },
  { id: "rooms", icon: "🏨", labelKey: "nav.rooms" },
  { id: "bookings", icon: "📅", labelKey: "nav.bookings" },
  { id: "guests", icon: "👥", labelKey: "nav.guests" },
  { id: "pos", icon: "💰", labelKey: "nav.pos" },
  { id: "reports", icon: "📈", labelKey: "nav.reports" },
  { id: "settings", icon: "⚙️", labelKey: "nav.settings" },
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
    <!-- 漢堡選單按鈕（手機用） -->
    <button class="hamburger-btn" @click="toggleSidebar" aria-label="Menu">
      <span></span><span></span><span></span>
    </button>

    <!-- Sidebar overlay（手機時點擊關閉） -->
    <div class="sidebar-overlay" :class="{ active: sidebarOpen }" @click="closeSidebar"></div>

    <!-- 側邊欄 -->
    <aside class="sidebar" :class="{ open: sidebarOpen }">
      <div class="sidebar-header">
        <h1>{{ $t('header.title') }}</h1>
        <p>{{ $t('header.subtitle') }}</p>
      </div>

      <!-- 語言切換 -->
      <div class="language-switcher">
        <div class="lang-buttons">
          <button :class="{ active: locale === 'zh-TW' }" @click="switchLanguage('zh-TW')">{{ $t('language.zh_tw') }}</button>
          <button :class="{ active: locale === 'id' }" @click="switchLanguage('id')">{{ $t('language.id') }}</button>
        </div>
      </div>

      <ul class="nav-menu">
        <li
          v-for="item in menuItems"
          :key="item.id"
          class="nav-item"
          :class="{ active: activeMenu === item.id }"
          @click="switchMenu(item.id); closeSidebar()"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span>{{ $t(item.labelKey) }}</span>
        </li>
      </ul>

      <!-- 面板控制 -->
      <div v-if="activeMenu === 'dashboard'" class="widget-controls">
        <h4>{{ $t('nav.panel_control') }}</h4>
        <label v-for="w in widgets" :key="w.id" class="widget-toggle">
          <input
            type="checkbox"
            v-model="w.visible"
            @change="toggleWidget(w.id)"
          />
          <span>{{ getWidgetTitle(w.id) }}</span>
        </label>
      </div>


    </aside>

    <!-- 主內容區 -->
    <main class="main-content">
      <header class="header">
        <h2>{{ $t(menuItems.find((m) => m.id === activeMenu)?.labelKey || 'nav.dashboard') }}</h2>
        <div class="header-right">
          <div v-if="activeMenu === 'dashboard'" class="refresh-group">
            <div class="countdown-timer" :class="{ warning: countdown <= 5 }">
              <span class="countdown-value">{{ countdown }}</span>
              <span class="countdown-unit">{{ $t('header.second') }}</span>
            </div>
            <button
              @click="manualRefresh"
              class="refresh-btn"
              :title="$t('header.refresh_title')"
            >
              {{ $t('header.refresh') }}
            </button>
          </div>
          <div class="header-services">
            <div
              v-for="service in services"
              :key="service.id"
              class="header-service-item"
            >
              <span class="service-name-small">{{ service.nameKey ? $t(service.nameKey) : service.name }}</span>
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
            <h3>{{ $t('dashboard.today_checkin') }}</h3>
            <div class="stat-row">
              <span class="stat-value">{{ stats.todayCheckin }}</span>
              <span class="stat-unit">{{ $t('dashboard.unit_group') }}</span>
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
            <h3>{{ $t('dashboard.today_checkout') }}</h3>
            <div class="stat-row">
              <span class="stat-value">{{ stats.todayCheckout }}</span>
              <span class="stat-unit">{{ $t('dashboard.unit_group') }}</span>
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
            <h3>{{ $t('dashboard.occupancy') }}</h3>
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
            <h3>{{ $t('dashboard.vacant') }}</h3>
            <div class="stat-row">
              <span class="stat-value">{{
                stats.totalRooms - stats.occupiedRooms
              }}</span>
              <span class="stat-unit">{{ $t('dashboard.unit_room') }}</span>
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
              {{ $t('rooms.pending_title') }}
              <span class="room-count">({{ dirtyRooms.length }})</span>
              <span v-if="urgentRoomCount > 0" class="urgent-count">
                {{ $t('rooms.urgent_count', { count: urgentRoomCount }) }}
              </span>
              <span v-if="acknowledgedCount > 0" class="acknowledged-count" @click="clearAcknowledgedRooms" title="點擊恢復顯示">
                {{ $t('rooms.acknowledged_count', { count: acknowledgedCount }) }}
              </span>
              <div class="status-legend">
                <span class="legend-item"
                  ><span class="dot dirty"></span>{{ $t('rooms.legend_dirty') }}</span
                >
                <span class="legend-item"
                  ><span class="dot inspecting"></span>{{ $t('rooms.legend_inspecting') }}</span
                >
                <span class="legend-item"
                  ><span class="dot urgent"></span>{{ $t('rooms.legend_urgent') }}</span
                >
              </div>
            </h3>
            <div v-if="roomsLoading" class="loading-text">{{ $t('common.loading') }}</div>
            <div v-else-if="dirtyRooms.length === 0" class="empty-text">
              {{ $t('rooms.all_clean') }}
            </div>
            <div v-else class="floor-grid" @mouseleave="hideTooltip">
              <!-- 按樓層分組顯示 -->
              <div
                v-for="floor in floors"
                :key="floor"
                v-show="dirtyRoomsByFloor[floor]?.length > 0"
                class="floor-row"
              >
                <span class="floor-label">{{ floor }}F</span>
                <div class="floor-rooms">
                  <div
                    v-for="room in dirtyRoomsByFloor[floor]"
                    :key="room.number"
                    class="room-card clickable"
                    :class="[room.status, { urgent: room.shouldBlink }]"
                    :title="room.shouldBlink ? $t('rooms.click_confirm', { room: room.number }) : $t('rooms.click_view', { room: room.number })"
                    @click="handleRoomClick(room)"
                    @mouseenter="showTooltip(room, $event)"
                    @mousemove="moveTooltip"
                    @mouseleave="hideTooltip"
                  >
                    <span class="room-number">{{ room.number }}</span>
                  </div>
                </div>
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
              <span class="tooltip-title">{{ $t('rooms.tooltip_title') }}</span>
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
                {{ $t('booking.title') }}
                <span class="panel-count">({{ sameDayBookings.length }})</span>
              </h3>
              <button class="collapse-btn" @click="toggleCollapse(5)">
                {{ widgets[5].collapsed ? "▼" : "▲" }}
              </button>
            </div>
            <div v-show="!widgets[5].collapsed" class="panel-body">
              <div v-if="sameDayLoading" class="loading-text">{{ $t('common.loading') }}</div>
              <div v-else-if="sameDayError" class="error-text">
                {{ sameDayError }}
              </div>
              <div v-else-if="groupedBookings.length === 0" class="empty-text">
                {{ $t('booking.empty') }}
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
                      >{{ $t('booking.room_count', { count: group.items.length }) }}</span
                    >
                    <!-- 大訂單狀態顯示 -->
                    <span
                      v-if="group.groupStatus === 'cancelled'"
                      class="group-status-cancelled"
                      >{{ $t('booking.cancelled') }}</span
                    >
                    <span
                      v-else-if="group.groupStatus === 'checked_in'"
                      class="group-status-done"
                      >{{ $t('booking.checked_in') }}</span
                    >
                    <span
                      v-else-if="group.groupStatus === 'mismatch'"
                      class="group-status-mismatch"
                      >{{ $t('booking.mismatch') }}</span
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
                        {{ $t('booking.btn_keyed') }}
                      </button>
                      <!-- KEY 錯狀態：重新匹配按鈕 -->
                      <button
                        class="mismatch-btn-sm"
                        @click="markAllAsKeyed(group)"
                        v-if="group.groupStatus === 'mismatch'"
                      >
                        {{ $t('booking.btn_rematch') }}
                      </button>
                      <button
                        class="cancel-btn-sm"
                        @click="cancelAllBookings(group)"
                        v-if="
                          group.groupStatus === 'pending' ||
                          group.groupStatus === 'mismatch'
                        "
                      >
                        {{ $t('booking.btn_cancel_all') }}
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
                          >{{ $t('booking.checked_in') }}</span
                        >
                        <span
                          v-else-if="item.status === 'cancelled'"
                          class="cancelled-text"
                          >{{ $t('booking.cancelled') }}</span
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
                          {{ $t('booking.btn_cancel') }}
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
              <h3>{{ $t('guests.title') }}</h3>
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
                    {{ $t('common.loading') }}
                  </div>
                  <div
                    v-else-if="
                      guestTabs[cfg.offset.toString()]?.data.length === 0
                    "
                    class="empty-text"
                  >
                    {{ $t('guests.no_checkin', { day: getTabLabel(cfg) }) }}
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

        <!-- AI 需求速覽 -->
        <div
          v-if="widgets[7].visible"
          class="grid-stack-item"
          :class="{ collapsed: widgets[7].collapsed }"
          gs-id="ai-needs"
          gs-x="0"
          gs-y="14"
          gs-w="100"
          gs-h="5"
          gs-min-w="12"
          gs-min-h="3"
        >
          <div class="grid-stack-item-content ai-needs-panel">
            <div class="panel-header">
              <div class="widget-handle"></div>
              <h3>{{ $t('ai.title') }}</h3>
              <div class="guest-tabs">
                <button
                  v-for="cfg in GUEST_TABS_CONFIG"
                  :key="'ai-tab-' + cfg.offset"
                  :class="{ active: activeAiNeedsOffset === cfg.offset }"
                  @click="activeAiNeedsOffset = cfg.offset"
                  class="guest-tab-btn"
                >
                  {{ getTabLabel(cfg) }}
                  <span class="tab-count">({{ getAiNeedsGuests(cfg.offset).length }})</span>
                </button>
              </div>
              <button class="collapse-btn" @click="toggleCollapse(7)">
                {{ widgets[7].collapsed ? "▼" : "▲" }}
              </button>
            </div>
            <div v-show="!widgets[7].collapsed" class="panel-body">
              <template
                v-for="cfg in GUEST_TABS_CONFIG"
                :key="'ai-content-' + cfg.offset"
              >
                <div v-if="activeAiNeedsOffset === cfg.offset">
                  <div
                    v-if="guestTabs[cfg.offset.toString()]?.loading"
                    class="loading-text"
                  >
                    {{ $t('common.loading') }}
                  </div>
                  <div
                    v-else-if="getAiNeedsGuests(cfg.offset).length === 0"
                    class="empty-text"
                  >
                    ✅ {{ $t('ai.no_needs', { day: getTabLabel(cfg) }) }}
                  </div>
                  <div v-else class="ai-needs-list">
                    <div
                      v-for="g in getAiNeedsGuests(cfg.offset)"
                      :key="'ai-' + cfg.offset + '-' + g.booking_id"
                      class="ai-needs-item"
                    >
                      <div class="ai-needs-room">
                        <span class="ai-room-tag">{{ g.room_numbers?.join(', ') || $t('ai.not_assigned') }}</span>
                        <span class="ai-guest-name">{{ g.guest_name }}</span>
                        <span v-if="g.line_name" class="ai-line-name">({{ g.line_name }})</span>
                        <span class="ai-status-badge" :class="'status-' + g.status_code">{{ tApi(g.status_name) }}</span>
                      </div>
                      <div class="ai-needs-details">
                        <div v-if="g.special_request_from_bot" class="ai-need-row">
                          <span class="ai-need-tag bot">{{ $t('ai.tag_ai') }}</span>
                          <span class="ai-need-text">{{ getTranslatedText(g.special_request_from_bot) }}</span>
                        </div>
                        <div v-if="g.customer_remarks" class="ai-need-row">
                          <span class="ai-need-tag pms">{{ $t('ai.tag_pms') }}</span>
                          <span class="ai-need-text">{{ getTranslatedText(g.customer_remarks) }}</span>
                        </div>
                        <div v-if="g.staff_memo" class="ai-need-row">
                          <span class="ai-need-tag memo">{{ $t('ai.tag_counter') }}</span>
                          <span class="ai-need-text">{{ g.staff_memo }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </template>
            </div>
          </div>
        </div>
      </div>

      <!-- 📝 同步回覆專區 -->
      <div v-else-if="activeMenu === 'sync-reply'" class="sync-reply-page">
        <div class="sync-reply-panel">
          <div class="sync-page-header">
            <h3>{{ $t('sync.title') }}</h3>
            <p class="sync-page-desc">{{ $t('sync.desc') }}</p>
            <button class="sync-refresh-btn" @click="fetchChatUsers">{{ $t('sync.refresh') }}</button>
          </div>
          <div class="sync-reply-container">
            <!-- 客人選擇列表 -->
            <div class="sync-reply-users">
              <!-- 當日入住客人區塊 -->
              <div class="sync-reply-label today-checkin-label">{{ $t('sync.today_checkin_label') }}</div>
              <div v-if="todayCheckinLoading" class="empty-text">{{ $t('common.loading') }}</div>
              <div v-else-if="todayCheckinUsers.length === 0" class="empty-text today-checkin-empty">{{ $t('sync.today_no_match') }}</div>
              <div v-else class="sync-user-list today-checkin-list">
                <div
                  v-for="u in todayCheckinUsers"
                  :key="'checkin-' + u.user_id"
                  class="sync-user-item today-checkin-item"
                  :class="{ active: selectedUserId === u.user_id }"
                  @click="selectedUserId = u.user_id"
                >
                  <span class="sync-user-name">{{ u.display_name }}</span>
                  <span class="sync-user-badge" v-if="u.room_info">{{ u.room_info }}</span>
                  <span class="sync-user-badge" v-else-if="u.room_type">{{ u.room_type }}</span>
                </div>
              </div>
              <!-- 原有客人列表 -->
              <div class="sync-reply-label">{{ $t('sync.select_label') }}</div>
              <div v-if="chatUsersLoading" class="empty-text">{{ $t('common.loading') }}</div>
              <div v-else-if="chatUsers.length === 0" class="empty-text">
                {{ $t('sync.no_records') }}
                <button class="sync-load-btn" @click="fetchChatUsers">{{ $t('sync.load_list') }}</button>
              </div>
              <div v-else class="sync-user-list">
                <div
                  v-for="u in chatUsers"
                  :key="u.user_id"
                  class="sync-user-item"
                  :class="{ active: selectedUserId === u.user_id }"
                  @click="selectedUserId = u.user_id"
                >
                  <span class="sync-user-name">{{ u.display_name }}</span>
                  <span class="sync-user-time">{{ formatLastActivity(u.last_activity) }}</span>
                </div>
              </div>
            </div>
            <!-- 回覆輸入 -->
            <div class="sync-reply-input" v-if="selectedUserId">
              <div class="sync-reply-target">{{ $t('sync.reply_to') }}<strong>{{ selectedUserName }}</strong></div>
              <!-- 最近對話 -->
              <div class="recent-messages" v-if="recentMessages.length > 0 || recentMessagesLoading">
                <div class="recent-messages-title">{{ $t('sync.recent_chat') }}</div>
                <div v-if="recentMessagesLoading" class="empty-text">{{ $t('common.loading') }}</div>
                <div v-else class="recent-messages-list">
                  <div v-for="(m, i) in recentMessages" :key="i" class="recent-msg-item" :class="{ 'msg-guest': m.role.includes('客人'), 'msg-ai': m.role.includes('AI') || m.role.includes('助理'), 'msg-admin': m.role.includes('管理員') }">
                    <div class="recent-msg-role">{{ m.role }} <span class="recent-msg-time">{{ m.timestamp }}</span></div>
                    <div class="recent-msg-content">{{ m.message.slice(0, 200) }}{{ m.message.length > 200 ? '...' : '' }}</div>
                  </div>
                </div>
              </div>
              <textarea
                v-model="syncReplyMessage"
                :placeholder="$t('sync.textarea_placeholder')"
                rows="5"
                class="sync-textarea"
              ></textarea>
              <div class="sync-reply-actions">
                <button
                  class="sync-submit-btn"
                  :disabled="!syncReplyMessage.trim() || syncReplyStatus === 'sending'"
                  @click="syncReply"
                >
                  {{ syncReplyStatus === 'sending' ? $t('sync.sending') : $t('sync.send_record') }}
                </button>
                <span v-if="syncReplyStatus === 'success'" class="sync-success">{{ $t('sync.send_success') }}</span>
                <span v-if="syncReplyStatus === 'error'" class="sync-error">{{ $t('sync.send_fail') }}</span>
              </div>
              <!-- 歷史紀錄 -->
              <div class="sync-history">
                <div class="sync-history-title">{{ $t('sync.history_title') }}</div>
                <div v-if="syncHistoryLoading" class="empty-text">{{ $t('common.loading') }}</div>
                <div v-else-if="syncHistory.length === 0" class="sync-history-empty">{{ $t('sync.history_empty') }}</div>
                <div v-else class="sync-history-list">
                  <div v-for="(h, i) in syncHistory" :key="i" class="sync-history-item">
                    <div class="sync-history-time">{{ h.timestamp }}</div>
                    <div class="sync-history-msg">{{ h.message }}</div>
                  </div>
                </div>
              </div>
            </div>
            <div class="sync-reply-hint" v-else>
              {{ $t('sync.select_hint') }}
            </div>
          </div>
        </div>
      </div>

      <!-- 其他頁面佔位 -->
      <div v-else class="placeholder">
        <p style="text-align: center; color: #888; padding: 100px">
          {{ $t('common.developing', { page: $t(menuItems.find((m) => m.id === activeMenu)?.labelKey) }) }}
        </p>
      </div>
    </main>
  </div>
</template>
