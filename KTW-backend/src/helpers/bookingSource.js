/**
 * 訂房來源輔助函數 (DRY 原則)
 * 共用的 OTA 編號前綴對照邏輯
 */

// OTA 編號前綴對照表
const OTA_PREFIX_MAP = {
    'RMAG': 'Agoda',
    'RMBK': 'Booking.com',
    'RMEX': 'Expedia',
    'RMCPT': '攜程',
    'RMPGP': '官網'
};

/**
 * 依據 OTA 訂單編號判斷訂房來源
 * @param {string} otaId - OTA 訂單編號
 * @returns {string} 訂房來源名稱
 */
function getBookingSource(otaId) {
    // 沒有 OTA 編號 → 手KEY
    if (!otaId) {
        return '手KEY';
    }

    // 依前綴判斷
    for (const [prefix, source] of Object.entries(OTA_PREFIX_MAP)) {
        if (otaId.startsWith(prefix)) {
            return source;
        }
    }

    // 有 OTA 編號但無法識別前綴
    return 'OTA';
}

export { OTA_PREFIX_MAP, getBookingSource };
