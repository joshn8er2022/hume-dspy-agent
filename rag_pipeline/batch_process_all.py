"""
Batch process ALL files in Google Drive for initial knowledge base setup.
This ignores timestamps and processes everything from scratch.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from drive_watcher import GoogleDriveWatcher

def main():
    """Batch process all files in Google Drive"""
    print("=" * 80)
    print("🚀 BATCH PROCESSING ALL FILES IN GOOGLE DRIVE")
    print("=" * 80)
    print("\nThis will process ALL files, not just recent changes.")
    print("Perfect for initial knowledge base setup!\n")
    
    # Load environment
    load_dotenv()
    
    # Initialize watcher
    script_dir = Path(__file__).parent
    watcher = GoogleDriveWatcher(
        credentials_path=str(script_dir / 'credentials.json'),
        token_path=str(script_dir / 'token.json'),
        config_path=str(script_dir / 'config.json')
    )
    
    # Authenticate
    print("📡 Connecting to Google Drive...")
    watcher.authenticate()
    print("✅ Connected!\n")
    
    # Get ALL files (no time filter)
    print("📂 Fetching complete file list...")
    results = watcher.service.files().list(
        pageSize=1000,
        fields="files(id, name, mimeType, webViewLink, modifiedTime, trashed)"
    ).execute()
    
    all_files = results.get('files', [])
    
    # Filter out trashed files
    files_to_process = [f for f in all_files if not f.get('trashed', False)]
    
    print(f"✅ Found {len(files_to_process)} files to process")
    print(f"   (Excluded {len(all_files) - len(files_to_process)} trashed files)\n")
    
    # Process each file
    print("🔄 Starting batch processing...\n")
    processed = 0
    skipped = 0
    errors = 0
    
    for i, file in enumerate(files_to_process, 1):
        file_name = file['name']
        mime_type = file.get('mimeType', '')
        
        print(f"[{i}/{len(files_to_process)}] Processing: {file_name}")
        
        # Check if supported
        supported_types = watcher.config.get('supported_mime_types', [])
        if not any(mime_type.startswith(t) for t in supported_types):
            print(f"   ⏭️  Skipped (unsupported type: {mime_type})")
            skipped += 1
            continue
        
        try:
            watcher.process_file(file)
            processed += 1
            print(f"   ✅ Success!")
        except Exception as e:
            errors += 1
            print(f"   ❌ Error: {str(e)}")
        
        print()  # Blank line for readability
    
    # Summary
    print("=" * 80)
    print("📊 BATCH PROCESSING COMPLETE!")
    print("=" * 80)
    print(f"✅ Processed: {processed} files")
    print(f"⏭️  Skipped: {skipped} files (unsupported types)")
    print(f"❌ Errors: {errors} files")
    print(f"📁 Total: {len(files_to_process)} files scanned")
    print("\n🎉 Knowledge base is ready!\n")

if __name__ == "__main__":
    main()
