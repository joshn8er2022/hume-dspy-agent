"""
Google Drive Complete Audit for Knowledge Base

Pulls EVERYTHING from Google Drive:
- Lists all files (no filtering)
- Categorizes by type
- Summarizes each file
- Presents for user approval

Uses existing Zapier/Google Drive integration.
"""

import os
import sys
import json
from datetime import datetime
from typing import List, Dict, Any
import asyncio

# Add parent to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.mcp_orchestrator import MCPOrchestrator
    MCP_AVAILABLE = True
except ImportError:
    print("⚠️  MCP Orchestrator not available")
    MCP_AVAILABLE = False


class GoogleDriveAuditor:
    """Complete Google Drive audit for KB population"""
    
    def __init__(self):
        self.mcp = MCPOrchestrator()
        self.files = []
    
    async def initialize(self):
        """Initialize MCP and load Google tools"""
        print("🔧 Initializing MCP...")
        await self.mcp.initialize()
        
        # Load Google Drive tools
        print("📂 Loading Google Drive tools...")
        google_tools = await self.mcp.get_tools_for_profile("document_analyst")
        
        google_drive_tools = [t for t in google_tools if "google" in t.get("name", "").lower()]
        print(f"   Found {len(google_drive_tools)} Google Drive tools")
        
        return google_drive_tools
    
    async def list_all_files(self) -> List[Dict[str, Any]]:
        """List EVERYTHING in Google Drive"""
        print("\n" + "="*80)
        print("🔍 SCANNING ENTIRE GOOGLE DRIVE")
        print("="*80)
        print("This may take a minute...")
        
        try:
            # Use Zapier Google Drive - CORRECT tool name
            result = await self.mcp.call_tool(
                server_name="zapier",
                tool_name="google_drive_retrieve_files_from_google_drive",
                arguments={
                    "instructions": "Retrieve all files from Google Drive for knowledge base audit",
                    "spaces": "drive",
                    "pageSize": "1000",
                    "orderBy": "modifiedTime desc"
                }
            )
            
            files = result.get("files", [])
            print(f"\n✅ Found {len(files)} total files")
            
            self.files = files
            return files
        
        except Exception as e:
            print(f"❌ Error listing files: {e}")
            print("\nTrying alternative method...")
            
            # Fallback: Try via agent delegation
            print("Delegating to document_analyst...")
            return await self._list_via_agent()
    
    async def _list_via_agent(self) -> List[Dict[str, Any]]:
        """Fallback: Use document_analyst subordinate"""
        from agents.agent_delegation_enhanced import AgentDelegationSystem
        
        delegation = AgentDelegationSystem()
        
        result = await delegation.delegate_task(
            profile="document_analyst",
            task="List ALL files in Google Drive with metadata (name, type, size, modified date, path)",
            context={"full_audit": True, "no_filtering": True}
        )
        
        # Parse result
        files = result.get("files", [])
        self.files = files
        return files
    
    def categorize_files(self) -> Dict[str, List[Dict]]:
        """Categorize files by potential KB category"""
        print("\n" + "="*80)
        print("📊 CATEGORIZING FILES")
        print("="*80)
        
        categories = {
            "business": [],
            "strategy": [],
            "playbooks": [],
            "intelligence": [],
            "marketing": [],
            "sales": [],
            "product": [],
            "operations": [],
            "financial": [],
            "personal": [],
            "temp": [],
            "other": []
        }
        
        # Keywords for categorization
        keywords = {
            "business": ["company", "overview", "unit economics", "capacity", "business model"],
            "strategy": ["icp", "ideal customer", "target", "positioning", "messaging", "strategy"],
            "playbooks": ["playbook", "qualification", "objection", "script", "sequence", "process"],
            "intelligence": ["competitor", "market", "analysis", "research", "trends", "intel"],
            "marketing": ["marketing", "campaign", "content", "brand", "advertising", "seo"],
            "sales": ["sales", "pipeline", "deals", "crm", "outreach", "prospecting"],
            "product": ["product", "roadmap", "features", "specs", "requirements"],
            "operations": ["operations", "ops", "workflow", "process", "sop"],
            "financial": ["financial", "revenue", "expenses", "budget", "pricing", "costs"],
            "personal": ["personal", "private", "draft", "temp", "test"],
            "temp": ["tmp", "backup", "old", "archive", "copy of"]
        }
        
        for file in self.files:
            name = file.get("name", "").lower()
            categorized = False
            
            # Check each category
            for category, terms in keywords.items():
                if any(term in name for term in terms):
                    categories[category].append(file)
                    categorized = True
                    break
            
            # Default to other
            if not categorized:
                categories["other"].append(file)
        
        # Print summary
        print("\nCategory Distribution:")
        for category, files in categories.items():
            if files:
                print(f"  {category.upper()}: {len(files)} files")
        
        return categories
    
    def summarize_file(self, file: Dict[str, Any]) -> str:
        """Generate summary for a file"""
        name = file.get("name", "Unknown")
        file_type = file.get("mimeType", "Unknown")
        size = file.get("size", "Unknown")
        modified = file.get("modifiedTime", "Unknown")
        
        # Simplify mime type
        type_map = {
            "application/vnd.google-apps.document": "Google Doc",
            "application/vnd.google-apps.spreadsheet": "Google Sheet",
            "application/vnd.google-apps.presentation": "Google Slides",
            "application/pdf": "PDF",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "Word Doc",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "Excel",
            "text/plain": "Text File",
            "image/jpeg": "Image (JPEG)",
            "image/png": "Image (PNG)"
        }
        
        simple_type = type_map.get(file_type, file_type)
        
        return f"{name} | {simple_type} | {size} bytes | Modified: {modified}"
    
    def generate_report(self, categories: Dict[str, List[Dict]]) -> str:
        """Generate formatted report for user review"""
        report = []
        report.append("\n" + "="*80)
        report.append("📚 GOOGLE DRIVE KNOWLEDGE BASE AUDIT")
        report.append("="*80)
        report.append(f"\nTotal Files: {len(self.files)}")
        report.append(f"Scan Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("\n" + "="*80)
        
        # Priority order
        priority_categories = [
            "business", "strategy", "playbooks", "intelligence",
            "sales", "marketing", "product", "operations", "financial"
        ]
        
        for category in priority_categories:
            files = categories.get(category, [])
            if not files:
                continue
            
            report.append(f"\n## {category.upper()} ({len(files)} files)")
            report.append("-" * 80)
            
            for i, file in enumerate(files, 1):
                summary = self.summarize_file(file)
                report.append(f"{i}. {summary}")
                
                # Suggest KB location
                if category in ["business", "strategy", "playbooks", "intelligence"]:
                    filename = file.get("name", "").lower().replace(" ", "_")
                    kb_path = f"knowledge_base/{category}/{filename}.md"
                    report.append(f"   → Suggested: {kb_path}")
                    report.append(f"   Relevance: ⭐⭐⭐ HIGH")
                else:
                    report.append(f"   Relevance: ⭐⭐ MEDIUM")
                
                report.append("")
        
        # Low priority categories
        for category in ["personal", "temp", "other"]:
            files = categories.get(category, [])
            if not files:
                continue
            
            report.append(f"\n## {category.upper()} ({len(files)} files)")
            report.append("-" * 80)
            report.append("⚠️  These files are likely NOT relevant for knowledge base")
            
            for i, file in enumerate(files[:10], 1):  # Show first 10
                summary = self.summarize_file(file)
                report.append(f"{i}. {summary}")
            
            if len(files) > 10:
                report.append(f"... and {len(files) - 10} more")
            
            report.append("")
        
        report.append("\n" + "="*80)
        report.append("📋 NEXT STEPS")
        report.append("="*80)
        report.append("\n1. Review the categories above")
        report.append("2. Identify files to include in knowledge base")
        report.append("3. Tell me which files to extract and convert")
        report.append("4. I'll download, convert to markdown, and load into KB")
        
        return "\n".join(report)
    
    async def run_audit(self):
        """Run complete audit"""
        try:
            # Initialize
            await self.initialize()
            
            # List all files
            files = await self.list_all_files()
            
            if not files:
                print("❌ No files found or unable to access Google Drive")
                print("\nTroubleshooting:")
                print("1. Check Google Drive integration in Zapier")
                print("2. Verify OAuth permissions")
                print("3. Try running via Slack: 'List all my Google Drive files'")
                return
            
            # Categorize
            categories = self.categorize_files()
            
            # Generate report
            report = self.generate_report(categories)
            
            # Save report
            report_file = f"google_drive_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(report_file, 'w') as f:
                f.write(report)
            
            print(report)
            print(f"\n📄 Full report saved to: {report_file}")
            
        except Exception as e:
            print(f"❌ Audit failed: {e}")
            import traceback
            traceback.print_exc()
    
    async def cleanup(self):
        """Cleanup"""
        if hasattr(self, 'mcp'):
            await self.mcp.cleanup()


async def main():
    """Run audit"""
    auditor = GoogleDriveAuditor()
    
    try:
        await auditor.run_audit()
    finally:
        await auditor.cleanup()


if __name__ == "__main__":
    if not MCP_AVAILABLE:
        print("❌ MCP not available. Run from project root:")
        print("   cd /Users/joshisrael/hume-dspy-agent")
        print("   python knowledge_base/google_drive_audit.py")
        sys.exit(1)
    
    print("🚀 Starting Google Drive Audit for Knowledge Base")
    print("="*80)
    
    asyncio.run(main())
