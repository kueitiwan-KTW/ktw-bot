"""
可視化報表
顯示房況比對結果與差異分析。
"""

from datetime import date, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

from .room_config import RoomConfigManager
from .platforms.base import RoomAvailability
from .utils.logger import logger


@dataclass
class ComparisonResult:
    """比對結果"""
    room_id: str
    room_name: str
    target_date: date
    platform: str
    base_inventory: int
    actual_inventory: int
    base_price: float
    actual_price: Optional[float]
    inventory_diff: int     # 正數 = 超賣，負數 = 還有空房
    price_diff: float       # 正數 = OTA 比基準高，負數 = OTA 比基準低


class ReportGenerator:
    """報表產生器"""
    
    def __init__(self, room_config: RoomConfigManager):
        self.room_config = room_config
    
    def compare_availability(
        self,
        platform: str,
        availability: List[RoomAvailability]
    ) -> List[ComparisonResult]:
        """比對 OTA 房況與基準設定"""
        results = []
        
        for avail in availability:
            # 反查房型 ID
            room_id = self.room_config.find_room_by_platform_name(platform, avail.room_type)
            if not room_id:
                logger.warning(f"未知房型: {avail.room_type} (平台: {platform})")
                continue
            
            room = self.room_config.room_types[room_id]
            base_inventory = room.base_inventory
            base_price = self.room_config.get_base_price(room_id, avail.date)
            
            results.append(ComparisonResult(
                room_id=room_id,
                room_name=room.name,
                target_date=avail.date,
                platform=platform,
                base_inventory=base_inventory,
                actual_inventory=avail.available,
                base_price=base_price or 0,
                actual_price=avail.price,
                inventory_diff=base_inventory - avail.available,
                price_diff=(avail.price or 0) - (base_price or 0)
            ))
        
        return results
    
    def print_comparison_report(
        self,
        platform: str,
        results: List[ComparisonResult],
        show_all: bool = False
    ) -> None:
        """印出比對報表"""
        print("\n" + "=" * 80)
        print(f"📊 {platform.upper()} 房況比對報表")
        print("=" * 80)
        
        if not results:
            print("  (無資料)")
            return
        
        # 依房型分組
        by_room: Dict[str, List[ComparisonResult]] = {}
        for r in results:
            if r.room_id not in by_room:
                by_room[r.room_id] = []
            by_room[r.room_id].append(r)
        
        for room_id, room_results in by_room.items():
            room_name = room_results[0].room_name
            print(f"\n🏨 {room_name}")
            print("-" * 70)
            print(f"{'日期':<12} {'庫存(基準→實際)':<18} {'價格(基準→實際)':<22} {'狀態'}")
            print("-" * 70)
            
            for r in sorted(room_results, key=lambda x: x.target_date):
                # 庫存狀態
                if r.inventory_diff > 0:
                    inv_status = f"⚠️ 已售 {r.inventory_diff} 間"
                elif r.inventory_diff < 0:
                    inv_status = f"❓ 多出 {abs(r.inventory_diff)} 間"
                else:
                    inv_status = "✅"
                
                # 價格狀態
                if r.actual_price is None:
                    price_status = "❓ 無價格"
                elif r.price_diff > 100:
                    price_status = f"📈 +${r.price_diff:,.0f}"
                elif r.price_diff < -100:
                    price_status = f"📉 ${r.price_diff:,.0f}"
                else:
                    price_status = "✅"
                
                # 決定是否顯示
                has_issue = r.inventory_diff != 0 or abs(r.price_diff) > 100
                if show_all or has_issue:
                    inv_str = f"{r.base_inventory} → {r.actual_inventory}"
                    price_str = f"${r.base_price:,.0f} → ${r.actual_price:,.0f}" if r.actual_price else f"${r.base_price:,.0f} → ?"
                    
                    print(f"{str(r.target_date):<12} {inv_str:<18} {price_str:<22} {inv_status} {price_status}")
        
        print("\n" + "=" * 80)
        print("📌 圖例: ⚠️=需關注  ✅=正常  📈=價格偏高  📉=價格偏低  ❓=異常")
        print("=" * 80 + "\n")
    
    def print_summary(self, all_results: Dict[str, List[ComparisonResult]]) -> None:
        """印出總覽摘要"""
        print("\n" + "🌟" * 30)
        print("📋 整體摘要")
        print("🌟" * 30)
        
        total_issues = 0
        
        for platform, results in all_results.items():
            inventory_issues = sum(1 for r in results if r.inventory_diff > 0)
            price_issues = sum(1 for r in results if abs(r.price_diff) > 500)
            
            total_issues += inventory_issues + price_issues
            
            print(f"\n📱 {platform.upper()}")
            print(f"   - 庫存差異: {inventory_issues} 筆")
            print(f"   - 價格差異: {price_issues} 筆 (差距 > $500)")
        
        print(f"\n🔔 需要關注的項目: {total_issues} 筆")
        
        if total_issues == 0:
            print("✅ 所有房況與基準一致！")
        else:
            print("⚠️ 請檢視上方詳細報表")
        
        print("\n")


# CLI 入口
if __name__ == "__main__":
    from datetime import date
    
    # 測試用
    room_config = RoomConfigManager()
    reporter = ReportGenerator(room_config)
    
    # 模擬 OTA 資料
    mock_availability = [
        RoomAvailability("Standard Double Room", date.today(), 8, 2800),
        RoomAvailability("Standard Double Room", date.today() + timedelta(days=1), 10, 3000),
        RoomAvailability("Deluxe Double Room", date.today(), 5, 3800),
    ]
    
    results = reporter.compare_availability("agoda", mock_availability)
    reporter.print_comparison_report("agoda", results, show_all=True)
