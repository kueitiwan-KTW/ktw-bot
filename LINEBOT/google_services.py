import os.path
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Define the scopes for all services
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/spreadsheets.readonly'
]

class GoogleServices:
    def __init__(self):
        self.creds = None
        self.authenticate()
        
    def authenticate(self):
        """Handles OAuth2 authentication and token management."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(base_dir, '..', 'data')
        token_path = os.path.join(data_dir, 'token.json')
        creds_path = os.path.join(data_dir, 'credentials.json')

        if os.path.exists(token_path):
            try:
                self.creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            except Exception:
                self.creds = None

        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception:
                    self.creds = None
            
            if not self.creds:
                if not os.path.exists(creds_path):
                    print(f"❌ Error: credentials.json not found at {creds_path}!")
                    return

                flow = InstalledAppFlow.from_client_secrets_file(
                    creds_path, SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(token_path, 'w') as token:
                token.write(self.creds.to_json())
        
        print("✅ Google Services Authenticated Successfully!")

    def get_gmail_service(self):
        return build('gmail', 'v1', credentials=self.creds)

    def get_drive_service(self):
        return build('drive', 'v3', credentials=self.creds)

    def get_sheets_service(self):
        return build('sheets', 'v4', credentials=self.creds)

if __name__ == "__main__":
    # Run this script directly to trigger authentication
    print("Initializing Google Services...")
    services = GoogleServices()
    
    # Test services
    try:
        gmail = services.get_gmail_service()
        profile = gmail.users().getProfile(userId='me').execute()
        print(f"📧 Gmail Connected: {profile['emailAddress']}")
        
        drive = services.get_drive_service()
        print("📂 Drive Connected")
        
        sheets = services.get_sheets_service()
        print("📊 Sheets Connected")
        
    except Exception as e:
        print(f"❌ Service Test Failed: {e}")
