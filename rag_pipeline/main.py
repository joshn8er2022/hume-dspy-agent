import os
import argparse
import sys
import base64
from pathlib import Path

from drive_watcher import GoogleDriveWatcher

def setup_credentials():
    """
    Setup Google Drive credentials from environment variables (for Railway deployment).
    If running locally, this will skip if files already exist.
    """
    script_dir = Path(__file__).resolve().parent
    credentials_path = script_dir / 'credentials.json'
    token_path = script_dir / 'token.json'
    
    # Check if we have base64-encoded credentials in environment
    creds_base64 = os.getenv('GOOGLE_DRIVE_CREDENTIALS_BASE64')
    token_base64 = os.getenv('GOOGLE_DRIVE_TOKEN_BASE64')
    
    if creds_base64 and not credentials_path.exists():
        print("📝 Setting up credentials.json from environment variable...")
        with open(credentials_path, 'wb') as f:
            f.write(base64.b64decode(creds_base64))
        print("✅ credentials.json created")
    
    if token_base64 and not token_path.exists():
        print("📝 Setting up token.json from environment variable...")
        with open(token_path, 'wb') as f:
            f.write(base64.b64decode(token_base64))
        print("✅ token.json created")

def main():
    """
    Main entry point for the RAG pipeline.
    """
    # Setup credentials from environment (for Railway)
    setup_credentials()
    
    # Get the directory where the script is located
    script_dir = Path(__file__).resolve().parent
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Google Drive RAG Pipeline')
    parser.add_argument('--credentials', type=str, default=str(script_dir / 'credentials.json'), 
                        help='Path to Google Drive API credentials file')
    parser.add_argument('--token', type=str, default=str(script_dir / 'token.json'),
                        help='Path to Google Drive API token file')
    parser.add_argument('--config', type=str, default=str(script_dir / 'config.json'),
                        help='Path to configuration JSON file')
    parser.add_argument('--interval', type=int, default=300,
                        help='Interval in seconds between checks for changes (default: 300 = 5 minutes)')
    parser.add_argument('--folder-id', type=str, default=None,
                        help='ID of the specific Google Drive folder to watch (and its subfolders)')
    parser.add_argument('--scan-once', action='store_true',
                        help='Scan once and exit (useful for initial setup or testing)')
    
    args = parser.parse_args()

    print("=" * 80)
    print("🚀 HUME RAG PIPELINE - GOOGLE DRIVE WATCHER")
    print("=" * 80)
    print(f"Credentials: {args.credentials}")
    print(f"Token: {args.token}")
    print(f"Config: {args.config}")
    print(f"Interval: {args.interval} seconds")
    print(f"Folder ID: {args.folder_id or 'All files (root)'}")
    print(f"Mode: {'One-time scan' if args.scan_once else 'Continuous monitoring'}")
    print("=" * 80)

    # Start the Google Drive watcher
    watcher = GoogleDriveWatcher(
        credentials_path=args.credentials,
        token_path=args.token,
        folder_id=args.folder_id,
        config_path=args.config
    )
    
    if args.scan_once:
        # Run once and exit
        print("\n🔍 Running one-time scan...")
        watcher.authenticate()
        changed_files = watcher.get_changes()
        
        if changed_files:
            print(f"\n✅ Found {len(changed_files)} files to process")
            for file in changed_files:
                watcher.process_file(file)
        else:
            print("\n✅ No new or changed files found")
        
        print("\n✅ One-time scan complete!")
    else:
        # Watch for changes continuously
        watcher.watch_for_changes(interval_seconds=args.interval)

if __name__ == "__main__":
    main()
