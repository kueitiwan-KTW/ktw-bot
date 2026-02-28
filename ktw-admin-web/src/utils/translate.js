/**
 * 前端翻譯工具模組
 * - 對照表翻譯：固定的 API 值（狀態、房型、早餐）
 * - Google Cloud Translation API：自由文字即時翻譯
 */

// Google Cloud Translation API Key（從環境變數讀取，不進 Git）
const GOOGLE_TRANSLATE_API_KEY = import.meta.env.VITE_GOOGLE_TRANSLATE_KEY || '';
const TRANSLATE_API_URL = 'https://translation.googleapis.com/language/translate/v2';

// ============================================================
// 對照表翻譯（固定值）
// ============================================================

// API 回傳的中文固定值 → i18n key 對照
const API_VALUE_MAP = {
  // 訂單狀態（status_name）
  '新訂單': 'api.status_new',
  '已確認': 'api.status_confirmed',
  '已入住': 'api.status_checked_in',
  '續住中': 'api.status_staying',
  '預計退房': 'api.status_expected_checkout',
  '已取消': 'api.status_cancelled',
  '已退房': 'api.status_checked_out',
  'No Show': 'api.status_no_show',

  // 早餐（breakfast）
  '有早餐': 'api.breakfast_included',
  '不含早餐': 'api.breakfast_excluded',
  '含早餐': 'api.breakfast_included',

  // 房型（room_type_name）
  '標準雙人房': 'api.room_standard_double',
  '標準三人房': 'api.room_standard_triple',
  '標準四人房': 'api.room_standard_quad',
  '無障礙雙人房': 'api.room_accessible_double',
  '豪華雙人房': 'api.room_deluxe_double',
  '豪華四人房': 'api.room_deluxe_quad',
};

/**
 * 翻譯 API 回傳的固定值
 * 如果在對照表中找到，使用 i18n 翻譯；否則返回原值
 * @param {string} value - API 回傳的中文值
 * @param {Function} t - vue-i18n 的 t 函數
 * @returns {string} 翻譯後的文字
 */
export function translateApiValue(value, t) {
  if (!value) return value;
  const key = API_VALUE_MAP[value];
  if (key) {
    const translated = t(key);
    // 如果 i18n 找不到 key（回傳 key 本身），就用原值
    return translated === key ? value : translated;
  }
  return value;
}

// ============================================================
// Google Cloud Translation API（自由文字）
// ============================================================

// 翻譯快取（避免重複 API 呼叫）
const translationCache = new Map();

/**
 * 使用 Google Cloud Translation API 翻譯自由文字
 * 帶有快取機制，相同文字不重複呼叫
 * @param {string} text - 要翻譯的文字
 * @param {string} targetLang - 目標語言代碼（如 'id'）
 * @param {string} sourceLang - 來源語言代碼（預設 'zh-TW'）
 * @returns {Promise<string>} 翻譯後的文字
 */
export async function translateText(text, targetLang = 'id', sourceLang = 'zh-TW') {
  if (!text || !text.trim()) return text;

  // 中文介面不需要翻譯
  if (targetLang === 'zh-TW' || targetLang === 'zh') return text;

  // 檢查快取
  const cacheKey = `${sourceLang}:${targetLang}:${text}`;
  if (translationCache.has(cacheKey)) {
    return translationCache.get(cacheKey);
  }

  try {
    const res = await fetch(`${TRANSLATE_API_URL}?key=${GOOGLE_TRANSLATE_API_KEY}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        q: text,
        source: sourceLang,
        target: targetLang,
        format: 'text',
      }),
    });

    if (!res.ok) {
      console.warn('[Translate] API 回傳錯誤:', res.status);
      return text; // 翻譯失敗時返回原文
    }

    const data = await res.json();
    const translated = data.data?.translations?.[0]?.translatedText || text;

    // 存入快取
    translationCache.set(cacheKey, translated);
    return translated;
  } catch (err) {
    console.warn('[Translate] API 呼叫失敗:', err.message);
    return text; // 網路錯誤時返回原文
  }
}

/**
 * 批次翻譯多段文字（減少 API 呼叫次數）
 * @param {string[]} texts - 要翻譯的文字陣列
 * @param {string} targetLang - 目標語言代碼
 * @param {string} sourceLang - 來源語言代碼
 * @returns {Promise<string[]>} 翻譯後的文字陣列
 */
export async function translateBatch(texts, targetLang = 'id', sourceLang = 'zh-TW') {
  if (!texts || texts.length === 0) return texts;
  if (targetLang === 'zh-TW' || targetLang === 'zh') return texts;

  // 找出需要翻譯的（不在快取中的）
  const toTranslate = [];
  const results = new Array(texts.length);

  texts.forEach((text, i) => {
    if (!text || !text.trim()) {
      results[i] = text;
      return;
    }
    const cacheKey = `${sourceLang}:${targetLang}:${text}`;
    if (translationCache.has(cacheKey)) {
      results[i] = translationCache.get(cacheKey);
    } else {
      toTranslate.push({ index: i, text });
    }
  });

  // 如果都在快取中，直接返回
  if (toTranslate.length === 0) return results;

  try {
    const res = await fetch(`${TRANSLATE_API_URL}?key=${GOOGLE_TRANSLATE_API_KEY}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        q: toTranslate.map(item => item.text),
        source: sourceLang,
        target: targetLang,
        format: 'text',
      }),
    });

    if (!res.ok) {
      // 翻譯失敗，用原文填充
      toTranslate.forEach(item => { results[item.index] = item.text; });
      return results;
    }

    const data = await res.json();
    const translations = data.data?.translations || [];

    toTranslate.forEach((item, i) => {
      const translated = translations[i]?.translatedText || item.text;
      results[item.index] = translated;
      // 存入快取
      const cacheKey = `${sourceLang}:${targetLang}:${item.text}`;
      translationCache.set(cacheKey, translated);
    });

    return results;
  } catch (err) {
    console.warn('[Translate] 批次翻譯失敗:', err.message);
    toTranslate.forEach(item => { results[item.index] = item.text; });
    return results;
  }
}

/**
 * 清除翻譯快取
 */
export function clearTranslationCache() {
  translationCache.clear();
}
