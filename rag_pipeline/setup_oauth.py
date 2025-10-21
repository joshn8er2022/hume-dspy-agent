"""
Simple OAuth setup script - no dependencies on OpenAI or Supabase
"""
import os
import json
from pathlib import Path
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly',
          'https://www.googleapis.com/auth/drive.readonly']

def authenticate():
    """Authenticate with Google Drive API and generate token.json"""
    script_dir = Path(__file__).resolve().parent
    credentials_path = str(script_dir / 'credentials.json')
    token_path = str(script_dir / 'token.json')
    
    print("=" * 80)
    print("🔐 GOOGLE DRIVE OAUTH SETUP")
    print("=" * 80)
    print(f"Credentials: {credentials_path}")
    print(f"Token will be saved to: {token_path}")
    print("=" * 80)
    
    creds = None
    
    # Check if token.json exists
    if os.path.exists(token_path):
        print("\n✅ Found existing token.json")
        creds = Credentials.from_authorized_user_info(
            json.loads(open(token_path).read()), SCOPES)
    
    # If there are no valid credentials, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("\n🔄 Refreshing expired token...")
            creds.refresh(Request())
        else:
            print("\n🌐 Opening browser for authentication...")
            print("Please authorize the application in your browser.")
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
        print(f"\n✅ Token saved to: {token_path}")
    
    # Build the Drive API service
    service = build('drive', 'v3', credentials=creds)
    
    # Test the connection
    print("\n🧪 Testing Google Drive connection...")
    results = service.files().list(pageSize=10, fields="files(id, name)").execute()
    files = results.get('files', [])
    
    print(f"\n✅ SUCCESS! Connected to Google Drive")
    print(f"Found {len(files)} files in test query:")
    for file in files[:5]:
        print(f"  - {file['name']}")
    
    if len(files) > 5:
        print(f"  ... and {len(files) - 5} more")
    
    print("\n" + "=" * 80)
    print("✅ OAUTH SETUP COMPLETE!")
    print("=" * 80)
    print("\nYou can now run the RAG pipeline.")
    print("Next step: Setup Supabase tables")

if __name__ == "__main__":
    try:
        authenticate()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure credentials.json exists in this directory")
        print("2. Check that you've enabled Google Drive API in Google Cloud Console")
        print("3. Make sure you added yourself as a test user in OAuth consent screen")
