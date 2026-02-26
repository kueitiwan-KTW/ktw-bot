<template>
  <div class="guest-card" :class="'card-status-' + guest.status_code">
    <div class="guest-card-header" @click.stop="toggleExpand">
      <div class="header-main">
        <span class="guest-card-name">
          {{ guest.registered_name || guest.guest_name }}
          <span v-if="guest.registered_name && guest.registered_name !== guest.guest_name" class="booking-name-sub">（{{ guest.guest_name }}）</span>
        </span>
        <div class="header-info">
          <span class="room-number">{{ guest.room_numbers?.join(', ') || t('guest_card.no_room') }}</span>
          <span class="booking-id">{{ guest.booking_id }}</span>
        </div>
      </div>
      <div class="header-right">
        <span class="guest-card-status" :class="'status-' + guest.status_code">{{ tApi(guest.status_name) }}</span>
        <span class="expand-icon">{{ isExpanded ? '▲' : '▼' }}</span>
      </div>
    </div>
    <!-- 收折內容 -->
    <div v-if="isExpanded" class="guest-card-details">
      <div class="detail-row">
        <span class="label">{{ t('guest_card.phone') }}</span>
        <span class="value" :class="{ 'from-bot': guest.phone_from_bot }">
          {{ guest.contact_phone || '-' }}
        </span>
      </div>
      <div class="detail-row"><span class="label">{{ t('guest_card.checkin_date') }}</span><span class="value">{{ guest.check_in_date }}{{ guest.nights >= 2 ? ` (${t('guest_card.nights', { n: guest.nights })})` : '' }}</span></div>
      <div class="detail-row"><span class="label">{{ t('guest_card.checkout_date') }}</span><span class="value">{{ guest.check_out_date }}</span></div>
      <div class="detail-row"><span class="label">{{ t('guest_card.booking_source') }}</span><span class="value">{{ guest.booking_source || t('guest_card.unknown') }}</span></div>
      <div class="detail-row"><span class="label">{{ t('guest_card.room_type') }}</span><span class="value">{{ tApi(guest.room_type_name) || t('guest_card.not_assigned') }}</span></div>
      <div class="detail-row"><span class="label">{{ t('guest_card.breakfast') }}</span><span class="value">{{ tApi(guest.breakfast) || t('guest_card.per_order') }}</span></div>
      <div class="detail-row"><span class="label">{{ t('guest_card.deposit') }}</span><span class="value price">NT$ {{ (guest.deposit_paid || 0).toLocaleString() }}</span></div>
      <div class="detail-row"><span class="label">{{ t('guest_card.total') }}</span><span class="value price">NT$ {{ (guest.room_total || 0).toLocaleString() }}</span></div>
      <div class="detail-row"><span class="label">{{ t('guest_card.balance') }}</span><span class="value price balance-due">NT$ {{ (guest.balance_due || 0).toLocaleString() }}</span></div>
      <div class="detail-row">
        <span class="label">{{ t('guest_card.arrival_time') }}</span>
        <span class="value" :class="{ 'from-bot': guest.arrival_time_from_bot }">
          {{ getTranslatedText(guest.arrival_time_from_bot) || t('guest_card.not_provided') }}
        </span>
      </div>
      <div class="detail-row">
        <span class="label">{{ t('guest_card.line_name') }}</span>
        <span class="value" :class="{ 'from-bot': guest.line_name }">
          {{ guest.line_name || t('guest_card.pending_ai') }}
        </span>
      </div>

      <!-- A.I. 需求與櫃檯備註 (延伸功能) -->
      <div class="supplement-section">
        <!-- 左欄：A.I. 提取需求 -->
        <div class="supplement-column">
          <label class="section-label">{{ t('guest_card.ai_requests') }}</label>
          <div class="ai-requests-box">
            {{ getTranslatedText(guest.special_request_from_bot) || t('guest_card.no_special') }}
          </div>
        </div>

        <!-- 右欄：櫃檯備註 -->
        <div class="supplement-column">
          <label class="section-label">{{ t('guest_card.counter_memo') }}</label>
          <textarea 
            class="staff-memo-area" 
            :placeholder="t('guest_card.memo_placeholder')" 
            v-model="localMemo"
            @blur="saveMemo"
          ></textarea>
          <div v-if="saveStatus" class="save-status">{{ saveStatus }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, reactive } from 'vue';
import { useI18n } from 'vue-i18n';
import { translateApiValue, translateText } from '../utils/translate.js';

// i18n 翻譯函數
const { t, locale } = useI18n();

// 自由文字翻譯快取（reactive）
const freeTextTranslations = reactive({});

function getTranslatedText(text) {
  if (!text || locale.value === 'zh-TW') return text;
  const cacheKey = `${locale.value}:${text}`;
  if (freeTextTranslations[cacheKey]) return freeTextTranslations[cacheKey];
  freeTextTranslations[cacheKey] = text;
  translateText(text, locale.value === 'id' ? 'id' : 'zh-TW').then(translated => {
    freeTextTranslations[cacheKey] = translated;
  });
  return freeTextTranslations[cacheKey];
}

function tApi(value) {
  return translateApiValue(value, t);
}

// 共用房客卡片元件 (GuestCard)
const props = defineProps({
  guest: {
    type: Object,
    required: true
  },
  isExpanded: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['toggle', 'update-guest']);

const localMemo = ref(props.guest.staff_memo || '');
const saveStatus = ref('');
let timer = null;

// 當 guest 資料更新時同步本地 memo
watch(() => props.guest.staff_memo, (newVal) => {
  localMemo.value = newVal || '';
});

function toggleExpand() {
  emit('toggle');
}

// 自動儲存邏輯
async function saveMemo() {
  if (localMemo.value === props.guest.staff_memo) return;
  
  saveStatus.value = t('guest_card.saving');
  try {
    const API_BASE = `http://${window.location.hostname}:3000`;
    const res = await fetch(`${API_BASE}/api/pms/supplements/${props.guest.pms_id || props.guest.booking_id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ staff_memo: localMemo.value })
    });
    
    if (res.ok) {
      saveStatus.value = t('guest_card.saved');
      // 通知父組件更新資料 (可選，通常 WebSocket 會處理)
      // emit('update-guest', { ...props.guest, staff_memo: localMemo.value });
      setTimeout(() => { saveStatus.value = ''; }, 2000);
    } else {
      saveStatus.value = t('guest_card.save_fail');
    }
  } catch (err) {
    console.error('儲存備註失敗:', err);
    saveStatus.value = t('guest_card.network_error');
  }
}
</script>

<style scoped>
.supplement-section {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px dashed rgba(255, 255, 255, 0.1);
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  grid-column: 1 / -1; /* 橫跨整個父容器 */
}

.supplement-column {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.supplement-column .ai-requests-box,
.supplement-column .staff-memo-area {
  flex: 1;
  min-height: 60px;
}

.section-label {
  font-size: 0.85rem;
  font-weight: bold;
  opacity: 0.8;
  color: #a0aec0;
}

.ai-requests-box {
  padding: 10px;
  background: rgba(49, 130, 206, 0.1);
  border-radius: 6px;
  font-size: 0.9rem;
  color: #90cdf4;
  min-height: 40px;
}

.staff-memo-area {
  width: 100%;
  min-height: 80px;
  padding: 10px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  color: #fff;
  font-size: 0.9rem;
  resize: vertical;
  transition: all 0.3s ease;
}

.staff-memo-area:focus {
  outline: none;
  border-color: #63b3ed;
  background: rgba(0, 0, 0, 0.3);
}

.save-status {
  font-size: 0.75rem;
  text-align: right;
  height: 15px;
  opacity: 0.8;
}

.from-bot {
  color: #63b3ed;
  font-weight: bold;
}

.bot-tag {
  font-size: 0.7rem;
  background: #3182ce;
  color: #fff;
  padding: 1px 4px;
  border-radius: 3px;
  margin-left: 5px;
}
</style>
