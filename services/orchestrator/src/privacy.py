"""
Privacy & Data Management
Implements "right to forget" with hard deletion and retention policies
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
import structlog

logger = structlog.get_logger(__name__)

# Privacy configuration
PRIVACY_CONFIG = {
    "session_retention_days": 7,
    "telemetry_retention_days": 30,
    "faiss_retention_days": 7,
    "deletion_verification": True
}

class PrivacyManager:
    """Manages user privacy and data deletion"""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = data_dir
        self.telemetry_dir = os.path.join(data_dir, "telemetry")
        self.sessions_dir = os.path.join(data_dir, "sessions")
        self.faiss_dir = os.path.join(data_dir, "faiss")
        
        # Ensure directories exist
        os.makedirs(self.telemetry_dir, exist_ok=True)
        os.makedirs(self.sessions_dir, exist_ok=True)
        os.makedirs(self.faiss_dir, exist_ok=True)
    
    def hash_user_id(self, user_id: str) -> str:
        """Create a hash of user ID for privacy"""
        return hashlib.sha256(user_id.encode()).hexdigest()[:16]
    
    def forget_user(self, user_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Implement "right to forget" for a user"""
        user_hash = self.hash_user_id(user_id)
        
        deletion_report = {
            "user_id_hash": user_hash,
            "timestamp": datetime.utcnow().isoformat(),
            "deleted_items": [],
            "errors": []
        }
        
        try:
            # Delete session data
            if session_id:
                session_deleted = self._delete_session_data(session_id)
                if session_deleted:
                    deletion_report["deleted_items"].append(f"session:{session_id}")
            
            # Delete user sessions
            user_sessions_deleted = self._delete_user_sessions(user_hash)
            deletion_report["deleted_items"].extend(user_sessions_deleted)
            
            # Delete telemetry data
            telemetry_deleted = self._delete_telemetry_data(user_hash)
            deletion_report["deleted_items"].extend(telemetry_deleted)
            
            # Delete FAISS embeddings
            faiss_deleted = self._delete_faiss_embeddings(user_hash)
            deletion_report["deleted_items"].extend(faiss_deleted)
            
            # Add tombstone record
            self._add_tombstone(user_hash, deletion_report)
            
            logger.info("User data deleted successfully", 
                       user_hash=user_hash, 
                       deleted_count=len(deletion_report["deleted_items"]))
            
            return deletion_report
            
        except Exception as e:
            error_msg = f"Deletion failed: {str(e)}"
            deletion_report["errors"].append(error_msg)
            logger.error("User deletion failed", user_hash=user_hash, error=str(e))
            raise HTTPException(status_code=500, detail=error_msg)
    
    def _delete_session_data(self, session_id: str) -> bool:
        """Delete specific session data"""
        session_file = os.path.join(self.sessions_dir, f"{session_id}.json")
        if os.path.exists(session_file):
            os.remove(session_file)
            logger.debug("Session data deleted", session_id=session_id)
            return True
        return False
    
    def _delete_user_sessions(self, user_hash: str) -> List[str]:
        """Delete all sessions for a user"""
        deleted_sessions = []
        
        try:
            for filename in os.listdir(self.sessions_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.sessions_dir, filename)
                    try:
                        with open(filepath, 'r') as f:
                            session_data = json.load(f)
                        
                        # Check if session belongs to user
                        if session_data.get('user_hash') == user_hash:
                            os.remove(filepath)
                            deleted_sessions.append(f"session:{filename}")
                            logger.debug("User session deleted", session_id=filename)
                    except Exception as e:
                        logger.warning("Failed to process session file", filename=filename, error=str(e))
        except Exception as e:
            logger.error("Failed to scan sessions directory", error=str(e))
        
        return deleted_sessions
    
    def _delete_telemetry_data(self, user_hash: str) -> List[str]:
        """Delete telemetry data for a user"""
        deleted_telemetry = []
        
        try:
            for filename in os.listdir(self.telemetry_dir):
                if filename.endswith('.jsonl'):
                    filepath = os.path.join(self.telemetry_dir, filename)
                    try:
                        # Read and filter out user data
                        filtered_lines = []
                        with open(filepath, 'r') as f:
                            for line in f:
                                try:
                                    data = json.loads(line.strip())
                                    # Remove lines containing user hash
                                    if user_hash not in str(data):
                                        filtered_lines.append(line)
                                    else:
                                        deleted_telemetry.append(f"telemetry:{filename}")
                                except json.JSONDecodeError:
                                    filtered_lines.append(line)  # Keep malformed lines
                        
                        # Write filtered data back
                        with open(filepath, 'w') as f:
                            f.writelines(filtered_lines)
                            
                    except Exception as e:
                        logger.warning("Failed to process telemetry file", filename=filename, error=str(e))
        except Exception as e:
            logger.error("Failed to scan telemetry directory", error=str(e))
        
        return deleted_telemetry
    
    def _delete_faiss_embeddings(self, user_hash: str) -> List[str]:
        """Delete FAISS embeddings for a user"""
        deleted_embeddings = []
        
        try:
            # This is a placeholder - actual FAISS deletion would depend on implementation
            # For now, we'll delete any user-specific embedding files
            for filename in os.listdir(self.faiss_dir):
                if user_hash in filename:
                    filepath = os.path.join(self.faiss_dir, filename)
                    os.remove(filepath)
                    deleted_embeddings.append(f"faiss:{filename}")
                    logger.debug("FAISS embedding deleted", filename=filename)
        except Exception as e:
            logger.error("Failed to delete FAISS embeddings", error=str(e))
        
        return deleted_embeddings
    
    def _add_tombstone(self, user_hash: str, deletion_report: Dict[str, Any]):
        """Add tombstone record for audit trail"""
        tombstone_file = os.path.join(self.data_dir, "tombstones.jsonl")
        
        tombstone_record = {
            "type": "user_deletion",
            "user_hash": user_hash,
            "timestamp": datetime.utcnow().isoformat(),
            "deletion_report": deletion_report
        }
        
        try:
            with open(tombstone_file, 'a') as f:
                f.write(json.dumps(tombstone_record) + '\n')
            logger.info("Tombstone record added", user_hash=user_hash)
        except Exception as e:
            logger.error("Failed to add tombstone record", error=str(e))
    
    def cleanup_expired_data(self):
        """Clean up expired data based on retention policies"""
        cutoff_date = datetime.utcnow() - timedelta(days=PRIVACY_CONFIG["session_retention_days"])
        
        cleaned_items = []
        
        # Clean expired sessions
        try:
            for filename in os.listdir(self.sessions_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.sessions_dir, filename)
                    file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    
                    if file_time < cutoff_date:
                        os.remove(filepath)
                        cleaned_items.append(f"expired_session:{filename}")
        except Exception as e:
            logger.error("Failed to clean expired sessions", error=str(e))
        
        logger.info("Data cleanup completed", cleaned_count=len(cleaned_items))
        return cleaned_items

# Global privacy manager
privacy_manager = PrivacyManager()
