"""Fix Implementation System (Phase 0.6)

Applies approved fixes to the codebase safely with rollback capability.

Pattern:
1. User approves fix via Slack
2. System validates approval
3. Creates backup of affected files
4. Applies changes
5. Runs validation tests
6. Commits to git
7. Deploys to Railway

If anything fails, automatic rollback.

Phase 0.6 - October 20, 2025
"""

import os
import logging
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import dspy

logger = logging.getLogger(__name__)


@dataclass
class FileBackup:
    """Backup of a file before modification."""
    original_path: str
    backup_path: str
    timestamp: datetime


@dataclass
class ImplementationResult:
    """Result of fix implementation."""
    success: bool
    fix_id: str
    files_modified: List[str]
    backups: List[FileBackup]
    commit_hash: Optional[str]
    error: Optional[str]
    rollback_performed: bool


class FixImplementor:
    """Implements approved fixes with safety and rollback."""
    
    def __init__(self, repo_path: str = "/Users/joshisrael/hume-dspy-agent"):
        """Initialize fix implementor.
        
        Args:
            repo_path: Path to git repository
        """
        self.repo_path = Path(repo_path)
        self.backups: Dict[str, List[FileBackup]] = {}
        
        logger.info("✅ Fix Implementor initialized")
        logger.info(f"   Repository: {self.repo_path}")
    
    def create_backup(self, file_path: str, fix_id: str) -> FileBackup:
        """Create backup of file before modification.
        
        Args:
            file_path: Path to file to backup
            fix_id: ID of the fix being applied
        
        Returns:
            FileBackup object
        """
        timestamp = datetime.utcnow()
        backup_dir = self.repo_path / ".backups" / fix_id
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        original = Path(file_path)
        backup_name = f"{original.stem}_{timestamp.strftime('%Y%m%d_%H%M%S')}{original.suffix}"
        backup_path = backup_dir / backup_name
        
        # Copy file
        shutil.copy2(file_path, backup_path)
        
        backup = FileBackup(
            original_path=file_path,
            backup_path=str(backup_path),
            timestamp=timestamp
        )
        
        if fix_id not in self.backups:
            self.backups[fix_id] = []
        self.backups[fix_id].append(backup)
        
        logger.info(f"📦 Backed up {file_path} → {backup_path}")
        return backup
    
    def apply_file_change(
        self,
        file_path: str,
        old_content: str,
        new_content: str,
        fix_id: str
    ) -> bool:
        """Apply a change to a file.
        
        Args:
            file_path: Path to file to modify
            old_content: Content to replace
            new_content: New content
            fix_id: ID of the fix
        
        Returns:
            True if successful
        """
        try:
            # Create backup first
            self.create_backup(file_path, fix_id)
            
            # Read current content
            with open(file_path, 'r') as f:
                current = f.read()
            
            # Verify old_content exists
            if old_content not in current:
                logger.error(f"❌ Old content not found in {file_path}")
                return False
            
            # Apply change
            updated = current.replace(old_content, new_content, 1)
            
            # Write back
            with open(file_path, 'w') as f:
                f.write(updated)
            
            logger.info(f"✅ Applied change to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to apply change to {file_path}: {e}")
            return False
    
    def rollback_fix(self, fix_id: str) -> bool:
        """Rollback all changes for a fix.
        
        Args:
            fix_id: ID of fix to rollback
        
        Returns:
            True if rollback successful
        """
        if fix_id not in self.backups:
            logger.error(f"No backups found for fix {fix_id}")
            return False
        
        logger.warning(f"🔄 Rolling back fix {fix_id}...")
        
        try:
            for backup in self.backups[fix_id]:
                # Restore from backup
                shutil.copy2(backup.backup_path, backup.original_path)
                logger.info(f"↩️ Restored {backup.original_path}")
            
            logger.info(f"✅ Rollback complete for {fix_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            return False
    
    def run_validation_tests(self) -> Tuple[bool, str]:
        """Run validation tests to verify system still works.
        
        Returns:
            Tuple of (success, output)
        """
        logger.info("🧪 Running validation tests...")
        
        try:
            # Test 1: Python syntax check
            result = subprocess.run(
                ["python", "-m", "py_compile"] + [
                    str(f) for f in self.repo_path.rglob("*.py")
                    if ".venv" not in str(f) and "node_modules" not in str(f)
                ],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.repo_path
            )
            
            if result.returncode != 0:
                return False, f"Syntax check failed: {result.stderr}"
            
            logger.info("✅ Python syntax check passed")
            
            # Test 2: Import check (try importing main modules)
            test_imports = [
                "from agents.strategy_agent import StrategyAgent",
                "from core.mcp_orchestrator import get_mcp_orchestrator",
                "from monitoring.proactive_monitor import ProactiveMonitor"
            ]
            
            for imp in test_imports:
                result = subprocess.run(
                    ["python", "-c", imp],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=self.repo_path
                )
                if result.returncode != 0:
                    return False, f"Import check failed: {imp}\n{result.stderr}"
            
            logger.info("✅ Import checks passed")
            
            return True, "All validation tests passed"
            
        except Exception as e:
            return False, f"Validation failed: {e}"
    
    def commit_changes(self, fix_id: str, description: str) -> Optional[str]:
        """Commit changes to git.
        
        Args:
            fix_id: ID of the fix
            description: Commit message
        
        Returns:
            Commit hash or None if failed
        """
        try:
            # Add all changes
            subprocess.run(
                ["git", "add", "-A"],
                cwd=self.repo_path,
                check=True
            )
            
            # Commit
            commit_msg = f"fix(auto): {description}\n\nFix ID: {fix_id}\nApplied by: Proactive Monitor (Phase 0.6)"
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=self.repo_path,
                check=True,
                capture_output=True
            )
            
            # Get commit hash
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            commit_hash = result.stdout.strip()
            logger.info(f"✅ Committed changes: {commit_hash[:8]}")
            return commit_hash
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Git commit failed: {e}")
            return None
    
    def deploy_to_railway(self) -> bool:
        """Deploy changes to Railway.
        
        Returns:
            True if deployment successful
        """
        try:
            logger.info("🚀 Deploying to Railway...")
            
            # Push to git (Railway auto-deploys)
            result = subprocess.run(
                ["git", "push"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                logger.info("✅ Pushed to git - Railway will auto-deploy")
                return True
            else:
                logger.error(f"❌ Git push failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Deployment failed: {e}")
            return False
    
    async def implement_fix(
        self,
        fix_id: str,
        changes: List[Dict[str, str]],
        description: str
    ) -> ImplementationResult:
        """Implement an approved fix with full safety workflow.
        
        Args:
            fix_id: ID of the fix to implement
            changes: List of changes to apply (file, old_content, new_content)
            description: Description of the fix
        
        Returns:
            ImplementationResult with success status
        """
        logger.info(f"🔧 Implementing fix: {fix_id}")
        
        files_modified = []
        rollback_performed = False
        
        try:
            # Step 1: Apply all changes
            for change in changes:
                success = self.apply_file_change(
                    file_path=change["file"],
                    old_content=change["old_content"],
                    new_content=change["new_content"],
                    fix_id=fix_id
                )
                
                if not success:
                    raise Exception(f"Failed to apply change to {change['file']}")
                
                files_modified.append(change["file"])
            
            # Step 2: Validate changes
            logger.info("🧪 Validating changes...")
            validation_ok, validation_msg = self.run_validation_tests()
            
            if not validation_ok:
                raise Exception(f"Validation failed: {validation_msg}")
            
            # Step 3: Commit changes
            logger.info("📝 Committing changes...")
            commit_hash = self.commit_changes(fix_id, description)
            
            if not commit_hash:
                raise Exception("Failed to commit changes")
            
            # Step 4: Deploy
            logger.info("🚀 Deploying to production...")
            deploy_ok = self.deploy_to_railway()
            
            if not deploy_ok:
                raise Exception("Deployment failed")
            
            logger.info(f"✅ Fix {fix_id} implemented successfully!")
            
            return ImplementationResult(
                success=True,
                fix_id=fix_id,
                files_modified=files_modified,
                backups=self.backups.get(fix_id, []),
                commit_hash=commit_hash,
                error=None,
                rollback_performed=False
            )
            
        except Exception as e:
            logger.error(f"❌ Implementation failed: {e}")
            
            # Attempt rollback
            logger.warning("🔄 Attempting rollback...")
            rollback_ok = self.rollback_fix(fix_id)
            rollback_performed = rollback_ok
            
            return ImplementationResult(
                success=False,
                fix_id=fix_id,
                files_modified=files_modified,
                backups=self.backups.get(fix_id, []),
                commit_hash=None,
                error=str(e),
                rollback_performed=rollback_performed
            )


# ===== Convenience Functions =====

_implementor_instance: Optional[FixImplementor] = None

def get_fix_implementor() -> FixImplementor:
    """Get or create the global fix implementor instance."""
    global _implementor_instance
    if _implementor_instance is None:
        _implementor_instance = FixImplementor()
    return _implementor_instance
