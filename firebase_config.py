"""Firebase integration for AI Bike Racing Simulator."""

import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

try:
    import firebase_admin
    from firebase_admin import credentials, firestore, auth, storage
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    firestore = None
    auth = None
    storage = None


class FirebaseService:
    """Firebase service for authentication, database, and storage."""
    
    def __init__(self):
        self.initialized = False
        self.db = None
        self.bucket = None
        self._init_firebase()
    
    def _init_firebase(self) -> None:
        """Initialize Firebase Admin SDK."""
        if not FIREBASE_AVAILABLE:
            return
        
        try:
            # Check if already initialized
            firebase_admin.get_app()
            self.initialized = True
        except ValueError:
            # Initialize Firebase
            cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
            
            if cred_path and os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred, {
                    'storageBucket': os.getenv("FIREBASE_STORAGE_BUCKET")
                })
                self.initialized = True
            elif os.getenv("FIREBASE_CREDENTIALS_JSON"):
                # Load from environment variable (for deployment)
                cred_dict = json.loads(os.getenv("FIREBASE_CREDENTIALS_JSON"))
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred, {
                    'storageBucket': os.getenv("FIREBASE_STORAGE_BUCKET")
                })
                self.initialized = True
        
        if self.initialized:
            self.db = firestore.client()
            self.bucket = storage.bucket()
    
    def healthy(self) -> bool:
        """Check if Firebase is initialized."""
        return self.initialized
    
    # ==================== User Management ====================
    
    def create_user(self, email: str, display_name: str) -> Optional[str]:
        """Create a new user in Firebase Auth."""
        if not self.initialized:
            return None
        
        try:
            user = auth.create_user(
                email=email,
                display_name=display_name
            )
            return user.uid
        except Exception:
            return None
    
    def get_user(self, uid: str) -> Optional[Dict[str, Any]]:
        """Get user information."""
        if not self.initialized:
            return None
        
        try:
            user = auth.get_user(uid)
            return {
                "uid": user.uid,
                "email": user.email,
                "display_name": user.display_name,
                "created_at": user.user_metadata.creation_timestamp
            }
        except Exception:
            return None
    
    # ==================== Race History ====================
    
    def save_race_result(self, user_id: str, race_data: Dict[str, Any]) -> Optional[str]:
        """Save race result to Firestore."""
        if not self.initialized or not self.db:
            return None
        
        try:
            race_data["user_id"] = user_id
            race_data["timestamp"] = firestore.SERVER_TIMESTAMP
            race_data["created_at"] = datetime.utcnow().isoformat()
            
            doc_ref = self.db.collection("races").add(race_data)
            return doc_ref[1].id
        except Exception:
            return None
    
    def get_user_races(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's race history."""
        if not self.initialized or not self.db:
            return []
        
        try:
            races_ref = self.db.collection("races")
            query = races_ref.where("user_id", "==", user_id).order_by(
                "timestamp", direction=firestore.Query.DESCENDING
            ).limit(limit)
            
            races = []
            for doc in query.stream():
                race = doc.to_dict()
                race["id"] = doc.id
                races.append(race)
            
            return races
        except Exception:
            return []
    
    # ==================== Leaderboard ====================
    
    def update_leaderboard(self, user_id: str, username: str, score: float, 
                          difficulty: str, track_length: int) -> bool:
        """Update global leaderboard."""
        if not self.initialized or not self.db:
            return False
        
        try:
            leaderboard_ref = self.db.collection("leaderboard").document(user_id)
            
            # Get current best score
            doc = leaderboard_ref.get()
            if doc.exists:
                current_best = doc.to_dict().get("best_score", 0)
                if score <= current_best:
                    return True  # Don't update if not better
            
            leaderboard_ref.set({
                "user_id": user_id,
                "username": username,
                "best_score": score,
                "difficulty": difficulty,
                "track_length": track_length,
                "updated_at": firestore.SERVER_TIMESTAMP,
                "timestamp": datetime.utcnow().isoformat()
            }, merge=True)
            
            return True
        except Exception:
            return False
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top scores from leaderboard."""
        if not self.initialized or not self.db:
            return []
        
        try:
            leaderboard_ref = self.db.collection("leaderboard")
            query = leaderboard_ref.order_by(
                "best_score", direction=firestore.Query.DESCENDING
            ).limit(limit)
            
            leaders = []
            for doc in query.stream():
                leader = doc.to_dict()
                leader["id"] = doc.id
                leaders.append(leader)
            
            return leaders
        except Exception:
            return []
    
    # ==================== Track Storage ====================
    
    def save_track_template(self, track_name: str, track_data: Dict[str, Any]) -> bool:
        """Save track template to Firestore."""
        if not self.initialized or not self.db:
            return False
        
        try:
            track_ref = self.db.collection("track_templates").document(track_name)
            track_data["created_at"] = firestore.SERVER_TIMESTAMP
            track_data["timestamp"] = datetime.utcnow().isoformat()
            track_ref.set(track_data)
            return True
        except Exception:
            return False
    
    def get_track_templates(self) -> List[Dict[str, Any]]:
        """Get all track templates."""
        if not self.initialized or not self.db:
            return []
        
        try:
            tracks_ref = self.db.collection("track_templates")
            tracks = []
            for doc in tracks_ref.stream():
                track = doc.to_dict()
                track["id"] = doc.id
                tracks.append(track)
            return tracks
        except Exception:
            return []
    
    # ==================== Analytics ====================
    
    def log_event(self, event_name: str, event_data: Dict[str, Any]) -> bool:
        """Log analytics event to Firestore."""
        if not self.initialized or not self.db:
            return False
        
        try:
            event_data["event_name"] = event_name
            event_data["timestamp"] = firestore.SERVER_TIMESTAMP
            event_data["created_at"] = datetime.utcnow().isoformat()
            
            self.db.collection("analytics_events").add(event_data)
            return True
        except Exception:
            return False
    
    def get_analytics_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get analytics summary for last N days."""
        if not self.initialized or not self.db:
            return {}
        
        try:
            from datetime import timedelta
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            events_ref = self.db.collection("analytics_events")
            query = events_ref.where("created_at", ">=", cutoff.isoformat())
            
            total_events = 0
            event_counts = {}
            
            for doc in query.stream():
                total_events += 1
                event = doc.to_dict()
                event_name = event.get("event_name", "unknown")
                event_counts[event_name] = event_counts.get(event_name, 0) + 1
            
            return {
                "total_events": total_events,
                "event_counts": event_counts,
                "period_days": days
            }
        except Exception:
            return {}
    
    # ==================== Cloud Storage ====================
    
    def upload_race_replay(self, user_id: str, race_id: str, 
                          replay_data: str) -> Optional[str]:
        """Upload race replay to Cloud Storage."""
        if not self.initialized or not self.bucket:
            return None
        
        try:
            blob_name = f"replays/{user_id}/{race_id}.json"
            blob = self.bucket.blob(blob_name)
            blob.upload_from_string(replay_data, content_type="application/json")
            
            # Make publicly accessible (optional)
            # blob.make_public()
            
            return blob.public_url
        except Exception:
            return None
    
    def download_race_replay(self, user_id: str, race_id: str) -> Optional[str]:
        """Download race replay from Cloud Storage."""
        if not self.initialized or not self.bucket:
            return None
        
        try:
            blob_name = f"replays/{user_id}/{race_id}.json"
            blob = self.bucket.blob(blob_name)
            
            if not blob.exists():
                return None
            
            return blob.download_as_text()
        except Exception:
            return None
