<template>
  <div class="guest-card" :class="'card-status-' + guest.status_code">
    <div class="guest-card-header" @click="toggleExpand">
      <div class="header-main">
        <span class="guest-card-name">
          {{ guest.registered_name || guest.guest_name }}
          <span v-if="guest.registered_name && guest.registered_name !== guest.guest_name" class="booking-name-sub">（{{ guest.guest_name }}）</span>
        </span>
        <div class="header-info">
          <span class="room-number">{{ guest.room_numbers?.join(', ') || '尚未排房' }}</span>
          <span class="booking-id">{{ guest.booking_id }}</span>
        </div>
      </div>
      <div class="header-right">
        <span class="guest-card-status" :class="'status-' + guest.status_code">{{ guest.status_name }}</span>
        <span class="expand-icon">{{ expanded ? '▲' : '▼' }}</span>
      </div>
    </div>
    <!-- 收折內容 -->
    <div v-show="expanded" class="guest-card-details">
      <div class="detail-row"><span class="label">聯絡電話</span><span class="value">{{ guest.contact_phone || '-' }}</span></div>
      <div class="detail-row"><span class="label">入住日期</span><span class="value">{{ guest.check_in_date }}{{ guest.nights >= 2 ? ` (${guest.nights}晚)` : '' }}</span></div>
      <div class="detail-row"><span class="label">退房日期</span><span class="value">{{ guest.check_out_date }}</span></div>
      <div class="detail-row"><span class="label">訂房來源</span><span class="value">{{ guest.booking_source || '未知' }}</span></div>
      <div class="detail-row"><span class="label">房型</span><span class="value">{{ guest.room_type_name || '尚未分配' }}</span></div>
      <div class="detail-row"><span class="label">早餐</span><span class="value">{{ guest.breakfast || '依訂單' }}</span></div>
      <div class="detail-row"><span class="label">已付訂金</span><span class="value price">NT$ {{ (guest.deposit_paid || 0).toLocaleString() }}</span></div>
      <div class="detail-row"><span class="label">房價總額</span><span class="value price">NT$ {{ (guest.room_total || 0).toLocaleString() }}</span></div>
      <div class="detail-row"><span class="label">應收尾款</span><span class="value price balance-due">NT$ {{ (guest.balance_due || 0).toLocaleString() }}</span></div>
      <div class="detail-row">
        <span class="label">預計抵達</span>
        <span class="value" :class="{ 'from-bot': guest.arrival_time_from_bot }">
          {{ guest.arrival_time_from_bot || '未提供' }}
          <span v-if="guest.arrival_time_from_bot" class="bot-tag">Bot</span>
        </span>
      </div>
      <div class="detail-row"><span class="label">LINE 姓名</span><span class="value">{{ guest.line_name || '待 AI 處理' }}</span></div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

// 共用房客卡片元件 (GuestCard)
// 用於今日、昨日、明日入住清單
defineProps({
  guest: {
    type: Object,
    required: true
  }
});

// 收折狀態
const expanded = ref(false);

function toggleExpand() {
  expanded.value = !expanded.value;
}
</script>
