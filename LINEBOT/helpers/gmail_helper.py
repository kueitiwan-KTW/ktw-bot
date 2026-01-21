import base64
import re


class GmailHelper:
    def __init__(self, google_services):
        self.service = google_services.get_gmail_service()
        self.available = self.service is not None
        if not self.available:
            print("⚠️ GmailHelper 以降級模式運行（Gmail 查詢功能不可用）")

    def search_order(self, order_id):
        """
        Searches for an email containing the order_id.
        Prioritizes messages where the order_id appears in the Subject line.
        
        New Feature: Deep Scan for Substring Matches (e.g. searching "56645" inside "1675664593")
        """
        # 🔧 降級模式檢查
        if not self.available:
            print(f"⚠️ Gmail 查詢略過 (service 不可用)")
            return None
        
        print(f"Searching for Order ID: {order_id}")
        
        # --- 隱私攔截碼 (Privacy Guard) ---
        # 1. 攔截日期格式 (如 12/18, 2025-12-18)
        import re
        if re.search(r'\d{1,2}/\d{1,2}', order_id) or re.search(r'\d{4}-\d{2}-\d{2}', order_id):
            print(f"❌ Privacy Block: Detected date format in search query '{order_id}'. Search aborted.")
            return None
            
        # 2. 攔截過短或無效的純數字 (防止廣泛匹配)
        clean_numeric = re.sub(r'\D', '', order_id)
        if not clean_numeric or len(clean_numeric) < 5:
            print(f"❌ Privacy Block: Search query '{order_id}' is too vague. Search aborted.")
            return None
        # -------------------------------
        
        # 1. Primary Strategy: Direct API Search (Fast, requires word match)
        # If order_id has a prefix (e.g., RMAG1675664593), also search for the numeric part
        import re
        numeric_part = re.sub(r'^[A-Z]+', '', order_id)  # Remove leading letters
        
        # Build query: Search for both full ID and numeric part
        if numeric_part and numeric_part != order_id:
            query = f'("{order_id}" OR "{numeric_part}")'
        else:
            query = f'"{order_id}"'
        
        try:
            results = self.service.users().messages().list(userId='me', q=query, maxResults=10).execute()
            messages = results.get('messages', [])
            
            # If explicit search fails, and ID is short (likely a substring), try Deep Scan
            # 限定最近 14 天的訂單郵件，避免掃描到過舊的歷史資料
            if not messages and len(order_id) >= 5:
                print(f"⚠️ Direct search failed. Initiating Deep Scan for substring match: {order_id}")
                # Search for generic order keywords to get a candidate pool (within last 14 days)
                pool_query = 'subject:(訂單 OR Order OR Booking OR Reservation) newer_than:14d'
                pool_results = self.service.users().messages().list(userId='me', q=pool_query, maxResults=50).execute()
                pool_messages = pool_results.get('messages', [])
                
                print(f"  - Deep Scan: Scanned {len(pool_messages)} recent order emails.")
                
                # Collect ALL matching messages, then prioritize
                matching_messages = []
                
                for msg in pool_messages:
                    m = self.service.users().messages().get(userId='me', id=msg['id']).execute()
                    
                    # 1. Check Subject (Safest)
                    headers = m['payload']['headers']
                    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                    from_addr = next((h['value'] for h in headers if h['name'] == 'From'), '').lower()
                    
                    if order_id in subject:
                        # Check if internal
                        is_internal = '館別' in subject or 'webhotel' in from_addr
                        is_official = any(kw in from_addr or kw in subject.lower() 
                                        for kw in ['agoda', 'booking.com', 'hotels.com'])
                        
                        if is_official and not is_internal:
                            # Official email found! Use immediately
                            print(f"  - ✅ Official email found: {subject}")
                            messages = [m]
                            break
                        else:
                            # Keep as candidate
                            matching_messages.append((m, is_internal))
                            print(f"  - Found match: {subject} (Internal: {is_internal})")

                    # 2. Check Body (With "Anti-Property-ID" Guard)
                    if not matching_messages and order_id not in subject:
                        body = self._extract_body(m['payload'])
                        if order_id in body:
                            # Safety Check: Is this just a Property ID?
                            idx = body.find(order_id)
                            start = max(0, idx - 20)
                            context = body[start:idx].lower()
                            
                            blacklist = ['property id', 'hotel id', '統編', 'job id', '物業編號']
                            is_safe = True
                            for bad_word in blacklist:
                                if bad_word in context:
                                    print(f"  - ⚠️ Ignored (Context: '{bad_word}')")
                                    is_safe = False
                                    break
                            
                            if is_safe:
                                print(f"  - ✅ Found in BODY: {subject}")
                                matching_messages.append((m, False))
                
                # If no official email was found directly, use the best candidate
                if not messages and matching_messages:
                    # Prefer non-internal messages
                    non_internal = [m for m, is_int in matching_messages if not is_int]
                    if non_internal:
                        messages = [non_internal[0]]
                        print(f"  - Using non-internal candidate")
                    else:
                        messages = [matching_messages[0][0]]
                        print(f"  - Using best available candidate")
        
            if not messages:
                print("No messages found via any strategy.")
                return None

            print(f"Found {len(messages)} candidate messages. Analyzing priorities...")
            
            # ... (Rest of the priority logic remains the same, assuming 'messages' is populated)
            
            target_message = None
            
            # Strategy: Prioritize official booking confirmation emails over internal system notifications
            target_message = None
            best_candidate = None
            
            for msg in messages:
                # If we already have the full message (from Deep Scan), use it. Otherwise fetch.
                if 'payload' in msg:
                    full_msg = msg
                else:
                    full_msg = self.service.users().messages().get(userId='me', id=msg['id']).execute()
                
                headers = full_msg['payload']['headers']
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                from_addr = next((h['value'] for h in headers if h['name'] == 'From'), '').lower()
                
                print(f" - Inspecting: {subject}")
                
                # Check if the numeric part of order_id is in subject (more flexible matching)
                import re
                numeric_part = re.sub(r'^[A-Z]+', '', order_id)
                has_match = numeric_part in subject or order_id in subject
                
                if has_match:
                    # Check if this is an official booking email (from Agoda, Booking.com, etc.)
                    is_official = any(keyword in from_addr or keyword in subject.lower() 
                                     for keyword in ['agoda', 'booking.com', 'hotels.com', 'expedia'])
                    
                    # Check if this is an internal system notification
                    is_internal = '館別' in subject or 'webhotel' in from_addr or '系統自動傳送' in subject
                    
                    if is_official and not is_internal:
                        print(f"   -> ✅ Official booking confirmation! Selecting this message.")
                        target_message = full_msg
                        break
                    elif not is_internal:
                        # Not internal, but not clearly official either - keep as backup
                        if not best_candidate:
                            best_candidate = full_msg
                            print(f"   -> Potential match (keeping as backup)")
                    else:
                        print(f"   -> ⚠️ Internal system notification - skipping")
            
            # Fallback: Use best candidate if no official email found
            if not target_message and best_candidate:
                print("   -> Using backup candidate")
                target_message = best_candidate
            elif not target_message and messages:
                print("   -> No subject match found. Defaulting to most recent message.")
                target_message = self.service.users().messages().get(userId='me', id=messages[0]['id']).execute()
            
            if target_message:
                result = self._parse_message(target_message)
                if result:
                    result['order_id'] = order_id # Critical: Inject the ID we searched for
                    return result
                
            return None

        except Exception as e:
            print(f"An error occurred during search: {e}")
            return None

    def _parse_message(self, msg):
        """Parses the message payload to extract relevant info."""
        payload = msg['payload']
        headers = payload.get("headers")
        subject = ""
        for header in headers:
            if header['name'] == 'Subject':
                subject = header['value']
        
        body = self._extract_body(payload)

        # Extract Phone Number (Simple Regex for demo)
        phone_match = re.search(r'09\d{8}', body)
        phone = phone_match.group(0) if phone_match else None

        return {
            "id": msg['id'],
            "subject": subject,
            "snippet": msg.get('snippet', ''),
            "phone": phone,
            "body": body
        }

    def _extract_body(self, payload):
        """Recursively extracts the body from the payload."""
        if 'body' in payload and 'data' in payload['body']:
            raw_content = base64.urlsafe_b64decode(payload['body']['data']).decode()
            return self._strip_html_tags(raw_content)
        
        if 'parts' in payload:
            # Priority: text/plain (避免 HTML 解析問題) -> text/html (去除標籤後使用)
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                     if 'data' in part['body']:
                        return base64.urlsafe_b64decode(part['body']['data']).decode()
            
            for part in payload['parts']:
                if part['mimeType'] == 'text/html':
                     if 'data' in part['body']:
                        raw_html = base64.urlsafe_b64decode(part['body']['data']).decode()
                        return self._strip_html_tags(raw_html)
            
            for part in payload['parts']:
                if 'parts' in part:
                    found = self._extract_body(part)
                    if found: 
                        return found
        return ""
    
    def _strip_html_tags(self, html_content: str) -> str:
        """
        去除 HTML 標籤，保留純文字內容
        
        Args:
            html_content: 原始 HTML 內容
            
        Returns:
            str: 去除標籤後的純文字
        """
        import re
        
        try:
            # 1. 先移除 <style> 和 <script> 區塊（含內容）
            text = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
            
            # 2. 移除 HTML 註解
            text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
            
            # 3. 使用 HTMLParser 去除剩餘標籤
            from html.parser import HTMLParser
            from io import StringIO
            
            class HTMLStripper(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.reset()
                    self.strict = False
                    self.convert_charrefs = True
                    self.text = StringIO()
                    
                def handle_data(self, data):
                    self.text.write(data)
                    
                def get_data(self):
                    return self.text.getvalue()
            
            stripper = HTMLStripper()
            stripper.feed(text)
            text = stripper.get_data()
            
            # 4. 清理多餘空白和換行
            text = re.sub(r'\n\s*\n', '\n\n', text)  # 多個空行變成一個
            text = re.sub(r'[ \t]+', ' ', text)  # 多個空格變成一個
            text = re.sub(r'\n +', '\n', text)  # 行首空格
            
            return text.strip()
        except Exception as e:
            print(f"❌ HTML 解析錯誤: {e}")
            # Fallback: 簡單的正則去除標籤
            return re.sub(r'<[^>]+>', '', html_content)
