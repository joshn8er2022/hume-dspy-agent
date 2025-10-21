# Google Drive MCP Tools - Correct Names

**Issue Identified**: Oct 20, 2025 - Agent was calling non-existent tool names

## ❌ INCORRECT TOOL NAMES (Don't Use)
- `google_drive_list_files` ❌ (doesn't exist)
- `google_drive_search` ❌ (doesn't exist)

## ✅ CORRECT TOOL NAMES (Use These)

### **Primary Tools for KB Audit**

#### `google_drive_retrieve_files_from_google_drive`
**Description**: Retrieve a list of files based on specific query parameters  
**Parameters**:
- `spaces`: "drive" (default)
- `pageSize`: 1000 (max)
- `orderBy`: "modifiedTime desc"
- `driveId`: (optional) specific drive
- `q`: (optional) query string

**Example Usage**:
```python
result = await mcp_client.call_tool(
    "google_drive_retrieve_files_from_google_drive",
    {
        "spaces": "drive",
        "pageSize": 1000,
        "orderBy": "modifiedTime desc"
    }
)
```

---

### **Search Tools**

#### `google_drive_find_a_file`
**Description**: Search for a specific file by name  
**Parameters**:
- `title`: File name to search
- `drive`: (optional) Specific drive
- `folder`: (optional) Search within folder

#### `google_drive_find_a_folder`
**Description**: Search for a specific folder by name  
**Parameters**:
- `title`: Folder name to search
- `drive`: (optional) Specific drive
- `folder`: (optional) Search within folder

---

### **File Management Tools**

#### `google_drive_create_folder`
**Description**: Create a new, empty folder  
**Parameters**:
- `title`: Folder name
- `drive`: (optional) Drive location
- `folder`: (optional) Parent folder

#### `google_drive_copy_file`
**Description**: Create a copy of the specified file  
**Parameters**:
- `file`: File ID to copy
- `drive`: (optional) Drive location
- `folder`: (optional) Destination folder

#### `google_drive_delete_file`
**Description**: Delete a file by ID  
**Parameters**:
- `fileId`: ID of file to delete

#### `google_drive_delete_file_permanent`
**Description**: Permanently delete a file (cannot be undone)  
**Parameters**:
- `file`: File ID
- `drive`: (optional)
- `folder`: (optional)

#### `google_drive_move_file`
**Description**: Move a file from one folder to another  
**Parameters**:
- `file`: File ID
- `drive`: (optional)
- `folder`: Destination folder

#### `google_drive_upload_file`
**Description**: Upload an existing file to Google Drive  
**Parameters**:
- `file`: File content
- `drive`: (optional)
- `folder`: (optional)

#### `google_drive_create_file_from_text`
**Description**: Create a new file from plain text  
**Parameters**:
- `file`: Text content
- `drive`: (optional)
- `title`: File name
- `folder`: (optional)

#### `google_drive_replace_file`
**Description**: Upload a file that replaces an existing file  
**Parameters**:
- `file`: New file content
- `drive`: (optional)
- `folder`: (optional)

---

### **Metadata & Permissions Tools**

#### `google_drive_get_file_permissions`
**Description**: List all users who have access to a file  
**Parameters**:
- `file_id`: File ID
- `drive`: (optional)
- `folder`: (optional)

#### `google_drive_retrieve_file_or_folder_by_id`
**Description**: Get a file or folder by its ID  
**Parameters**:
- `id`: File/folder ID
- `drive`: (optional)

#### `google_drive_update_file_or_folder_metadata`
**Description**: Update file/folder metadata (name, description, starred, color)  
**Parameters**:
- `name`: (optional) New name
- `drive`: (optional)
- `folder`: (optional)
- Custom properties

#### `google_drive_update_file_folder_name`
**Description**: Update the name of a file or folder  
**Parameters**:
- `file`: File ID
- `drive`: (optional)
- `folder`: (optional)

---

### **Sharing & Permissions Tools**

#### `google_drive_add_file_sharing_preference`
**Description**: Add sharing scope to file (provides sharing URL)  
**Parameters**:
- `file_id`: File ID
- `drive`: (optional)
- `domain`: (optional) Domain to share with

#### `google_drive_remove_file_permission`
**Description**: Remove specific user access to a file  
**Parameters**:
- `file`: File ID
- `drive`: (optional)
- `email`: User email to remove

#### `google_drive_create_shortcut`
**Description**: Create a shortcut to a file  
**Parameters**:
- `file`: Target file ID
- `drive`: (optional)
- `folder`: (optional) Location for shortcut

#### `google_drive_create_shared_drive`
**Description**: Create a new shared drive (Team Drive)  
**Parameters**:
- `name`: Drive name
- `themeId`: (optional)
- `colorRgb`: (optional)

---

### **Export Tool**

#### `google_drive_export_file`
**Description**: Export Google Workspace files to different formats (PDF, Word, Excel)  
**Parameters**:
- `file`: File ID
- `drive`: (optional)
- `folder`: (optional)
- Format options

---

### **Advanced Tool**

#### `google_drive_api_request_beta`
**Description**: Make raw HTTP request to Google Drive API with auth  
**Parameters**:
- `url`: API endpoint
- `method`: HTTP method
- `body`: Request body

---

## 🎯 FOR KNOWLEDGE BASE AUDIT

**Use this tool**: `google_drive_retrieve_files_from_google_drive`

**Parameters for full scan**:
```json
{
  "spaces": "drive",
  "pageSize": 1000,
  "orderBy": "modifiedTime desc"
}
```

**To paginate** (if more than 1000 files):
```json
{
  "spaces": "drive",
  "pageSize": 1000,
  "pageToken": "<token_from_previous_response>"
}
```

---

## 🔧 AGENT CODE FIX

**File**: `/core/agent_delegation_enhanced.py` or `/agents/strategy_agent.py`

**Issue**: Agent references `google_drive_list_files` which doesn't exist

**Fix**: Update tool name references to `google_drive_retrieve_files_from_google_drive`

---

## 📊 RESPONSE FORMAT

The `google_drive_retrieve_files_from_google_drive` tool returns:

```json
{
  "files": [
    {
      "id": "file_id_here",
      "name": "filename.ext",
      "mimeType": "application/vnd.google-apps.document",
      "size": "12345",
      "modifiedTime": "2025-10-20T12:00:00Z",
      "webViewLink": "https://drive.google.com/...",
      "parents": ["folder_id"]
    }
  ],
  "nextPageToken": "token_if_more_results"
}
```

---

**Last Updated**: Oct 20, 2025, 10:40 PM PST  
**Issue**: Tool name mismatch causing "Tool not found" errors  
**Status**: ✅ Documented, ready to implement
