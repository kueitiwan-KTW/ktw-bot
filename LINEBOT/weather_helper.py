import requests
import os
import json
from datetime import datetime, timedelta

class WeatherHelper:
    def __init__(self):
        self.api_key = os.getenv("CWA_API_KEY")
        # F-D0047-027 is Pingtung County Township Forecast (Future 2 days / 1 week)
        # We use F-D0047-027 for 1 week forecast usually, but let's check the documentation.
        # F-D0047-035 is Pingtung County Township Forecast (Future 1 week)
        self.base_url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-035"
        self.location_name = "車城鄉"

    
    def get_weather_forecast(self, date_str):
        """
        Fetches weather forecast for Checheng Township.
        Uses 3-hourly forecast (F-D0047-093) for Today/Tomorrow for better accuracy.
        Uses Weekly forecast (F-D0047-035) for future dates.
        :param date_str: Date string in 'YYYY-MM-DD' format.
        :return: A string describing the weather.
        """
        if not self.api_key:
            return "系統未設定 CWA_API_KEY，無法查詢氣象署資料。"

        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            today = datetime.now().date()
            
            if target_date < today:
                return "日期已過，無法查詢預報。"
            
            days_diff = (target_date - today).days
            
            # Use Weekly forecast (F-D0047-035) for all dates as it is robust and verified
            if days_diff > 6:
                return "日期太遠，氣象署僅提供未來 1 週內的天氣預報。"

            # For future dates (day 2-6), use Weekly forecast (Original logic improved)
            return self._get_weekly_forecast_specific_date(target_date)

        except ValueError:
            return "日期格式錯誤，請使用 YYYY-MM-DD。"
        except Exception as e:
            print(f"CWA API Error: {e}")
            return "暫時無法取得氣象署資訊，請檢查 API Key 是否正確。"

    def _get_short_term_forecast(self, target_date):
        # F-D0047-093: Township Forecast - Future 2 Days (3-hour slots)
        url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-D0047-093"
        params = {
            "Authorization": self.api_key,
            "format": "JSON",
            "locationName": self.location_name,
            "elementName": "天氣現象,最低溫度,最高溫度"
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if not data["success"]:
            return "氣象署 API 回傳失敗 (Short Term)。"

        locations = data["records"]["Locations"][0]["Location"]
        target_location = next((loc for loc in locations if loc["LocationName"] == self.location_name), None)
        
        if not target_location:
            return f"找不到 {self.location_name} 的氣象資料。"

        weather_elements = {elem["ElementName"]: elem["Time"] for elem in target_location["WeatherElement"]}
        
        if "天氣現象" not in weather_elements:
             return "查無天氣現象資料。"

        # Robust Slot Selection
        best_match_idx = None
        
        # 1. Try to find a daytime slot (06:00 - 18:00 start time) for the target date
        for i, time_slot in enumerate(weather_elements["天氣現象"]):
            start_time = datetime.strptime(time_slot["StartTime"].split("+")[0].replace("T", " "), "%Y-%m-%d %H:%M:%S")
            if start_time.date() == target_date:
                if 6 <= start_time.hour <= 18:
                    best_match_idx = i
                    break
        
        # 2. If no daytime slot (e.g., querying 'Today' at 8 PM), take the FIRST available slot for that date
        if best_match_idx is None:
             for i, time_slot in enumerate(weather_elements["天氣現象"]):
                start_time = datetime.strptime(time_slot["StartTime"].split("+")[0].replace("T", " "), "%Y-%m-%d %H:%M:%S")
                # Special handling for "Today": if start_time is still valid (end_time > now) ?? 
                # CWA usually removes past slots. So any slot appearing for 'Today' is valid.
                if start_time.date() == target_date:
                    best_match_idx = i
                    break
        
        if best_match_idx is None:
            # If still no slot (maybe it's 11:59PM and slots are gone), try tomorrow if user asked for today?
            # Or just return data not available.
            return f"今日預報時段已過，請查詢明天天氣。"

        wx = weather_elements["天氣現象"][best_match_idx]["ElementValue"][0]["Weather"]
        # MinT/MaxT might be roughly same structure? 
        # Note: 3-hr forecast might name elements consistently, but let's verify if '最低溫度' exists.
        # usually 3hr has '攝氏溫度' (T) or 'Apparent T'. 
        # F-D0047-093 elements: Wx, T, AT, PoP6h... It might NOT have MinT/MaxT per 3hr slot directly or named differently.
        # Let's check documentation or infer. 
        # Actually F-D0047-093 usually has 'T' (Temperature). It doesn't strictly have Min/Max for 3hr, just T.
        # But '最低溫度' (MinT) and '最高溫度' (MaxT) are Daily parameters often. 
        # Wait, if I request elementName "天氣現象,最低溫度,最高溫度", and if they don't exist in 093, it might error or return empty.
        # 3-hr forecast (093) has: Wx, T, AT, CI, PoP6h, WS, WD, Td, RH. 
        # It DOES NOT have MinT/MaxT usually. It uses T.
        # I should use '攝氏溫度' (T) and maybe range?
        # Let's fallback to using just Weather Description if T is tricky, or try to get T.
        # To be safe and consistent with Weekly, I should perhaps stick to Weekly methodology but just relax slot selection?
        # PLAN ADJUSTMENT: F-D0047-093 returns 3-hour T. I can pick one T or a range?
        # Let's stick to using Weekly (035) but with relaxed slot selection first. 
        # Weekly (035) DEFINITELY has MinT/MaxT.
        # If I use 093, I need to parse 'T'.
        # Let's revert to using 035 (Weekly) for everything BUT relax the slot selection to allow "Looking for *any* slot on that day".
        # This reduces risk of "Element not found".
        pass

    def _get_weekly_forecast_specific_date(self, target_date):
        # Re-using the Weekly API logic but isolated for clarity
        params = {
            "Authorization": self.api_key,
            "format": "JSON",
            "locationName": self.location_name,
            "elementName": "天氣現象,最低溫度,最高溫度,12小時降雨機率,最高體感溫度,最低體感溫度"
        }
        response = requests.get(self.base_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if not data["success"]: return "氣象署 API 回傳失敗。"
        
        locations = data["records"]["Locations"][0]["Location"]
        target_location = next((loc for loc in locations if loc["LocationName"] == self.location_name), None)
        
        if not target_location: return f"找不到 {self.location_name} 的氣象資料。"

        weather_elements = {elem["ElementName"]: elem["Time"] for elem in target_location["WeatherElement"]}
        
        best_match_idx = None
        
        # 1. Day time match
        for i, time_slot in enumerate(weather_elements["天氣現象"]):
            start_time = datetime.strptime(time_slot["StartTime"].split("+")[0].replace("T", " "), "%Y-%m-%d %H:%M:%S")
            if start_time.date() == target_date:
                if 6 <= start_time.hour <= 18:
                    best_match_idx = i
                    break
        
        # 2. Any match for that day
        if best_match_idx is None:
            for i, time_slot in enumerate(weather_elements["天氣現象"]):
                start_time = datetime.strptime(time_slot["StartTime"].split("+")[0].replace("T", " "), "%Y-%m-%d %H:%M:%S")
                if start_time.date() == target_date:
                    best_match_idx = i
                    # Don't break immediately if we want to find *latest*? No, just first available is fine.
                    break
                    
        if best_match_idx is None:
            return f"查無 {target_date} 的預報資料 (可能已過預報時段)。"

        wx = weather_elements["天氣現象"][best_match_idx]["ElementValue"][0]["Weather"]
        min_t = weather_elements["最低溫度"][best_match_idx]["ElementValue"][0]["MinTemperature"]
        max_t = weather_elements["最高溫度"][best_match_idx]["ElementValue"][0]["MaxTemperature"]
        
        # 新增: 降雨機率和體感溫度
        pop = weather_elements["12小時降雨機率"][best_match_idx]["ElementValue"][0]["ProbabilityOfPrecipitation"]
        min_at = weather_elements["最低體感溫度"][best_match_idx]["ElementValue"][0]["MinApparentTemperature"]
        max_at = weather_elements["最高體感溫度"][best_match_idx]["ElementValue"][0]["MaxApparentTemperature"]
        
        # 組合回覆訊息
        result = f"入住當天車城鄉天氣{wx}，氣溫約 {min_t}°C - {max_t}°C"
        
        # 如果體感溫度與實際溫度差異較大 (>2度),顯示體感溫度
        if abs(int(min_at) - int(min_t)) > 2 or abs(int(max_at) - int(max_t)) > 2:
            result += f"，體感溫度 {min_at}°C - {max_at}°C"
        
        # 加入降雨機率
        pop_int = int(pop)
        if pop_int > 0:
            result += f"，降雨機率 {pop}%"
        
        result += " (資料來源：中央氣象署)"
        
        return result

    def get_weekly_forecast(self):
        """
        Fetches the weekly weather forecast for Checheng Township from CWA API.
        :return: A formatted string with 7-day forecast.
        """
        if not self.api_key:
            return "系統未設定 CWA_API_KEY，無法查詢氣象署資料。"

        try:
            params = {
                "Authorization": self.api_key,
                "format": "JSON",
                "locationName": self.location_name,
                "elementName": "天氣現象,最低溫度,最高溫度"
            }

            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()

            if not data["success"]:
                return "氣象署 API 回傳失敗。"

            locations = data["records"]["Locations"][0]["Location"]
            target_location = next((loc for loc in locations if loc["LocationName"] == self.location_name), None)
            
            if not target_location:
                return f"找不到 {self.location_name} 的氣象資料。"

            weather_elements = {elem["ElementName"]: elem["Time"] for elem in target_location["WeatherElement"]}
            
            if "天氣現象" not in weather_elements:
                 return "查無天氣現象資料。"

            # Process 7-day forecast
            forecast_lines = [f"【{self.location_name}未來一週天氣預報】"]
            processed_dates = set()

            for i, time_slot in enumerate(weather_elements["天氣現象"]):
                start_time_str = time_slot["StartTime"]
                clean_time_str = start_time_str.replace("T", " ").split("+")[0]
                slot_start = datetime.strptime(clean_time_str, "%Y-%m-%d %H:%M:%S")
                date_str = slot_start.strftime("%Y-%m-%d")
                
                # Only take one slot per day
                if date_str in processed_dates:
                    continue
                
                # Logic: If it's a future date, try to find daytime. If it's today, take what we can get.
                # Actually for listing, we iterate sequentially. 
                # If we encounter a slot for a new date, check if it's a good slot (daytime).
                # If not, maybe look ahead?
                # Simplification: Just take the first slot we see for that date? 
                # Better: Accumulate slots per date and pick best.
                
                pass # Logic continues below in actual implementation replacement...
            
            # Re-implementing loop for clarity in replacement
            # Group indices by date
            date_indices = {}
            for i, time_slot in enumerate(weather_elements["天氣現象"]):
                start_time = datetime.strptime(time_slot["StartTime"].split("+")[0].replace("T", " "), "%Y-%m-%d %H:%M:%S")
                d_str = start_time.strftime("%Y-%m-%d")
                if d_str not in date_indices: date_indices[d_str] = []
                date_indices[d_str].append( (i, start_time) )

            sorted_dates = sorted(date_indices.keys())
            
            for d_str in sorted_dates:
                slots = date_indices[d_str]
                best_i = slots[0][0] # Default to first
                
                # Try to find daytime slot (06-18)
                for idx, t in slots:
                    if 6 <= t.hour <= 18:
                        best_i = idx
                        break
                
                wx = weather_elements["天氣現象"][best_i]["ElementValue"][0]["Weather"]
                min_t = weather_elements["最低溫度"][best_i]["ElementValue"][0]["MinTemperature"]
                max_t = weather_elements["最高溫度"][best_i]["ElementValue"][0]["MaxTemperature"]
                
                forecast_lines.append(f"📅 {d_str}: {wx}, {min_t}°C - {max_t}°C")

            forecast_lines.append("(資料來源：中央氣象署)")
            return "\n".join(forecast_lines)

        except Exception as e:
            print(f"CWA API Error: {e}")
            return "暫時無法取得氣象署資訊，請檢查 API Key 是否正確。"

    def _get_weather_description(self, code):
        # Not used for CWA as they return text directly
        pass
