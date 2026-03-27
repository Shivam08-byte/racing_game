"""Google Cloud Platform integration for advanced services."""

import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

# Google Cloud Storage
try:
    from google.cloud import storage
    STORAGE_AVAILABLE = True
except ImportError:
    STORAGE_AVAILABLE = False
    storage = None

# Google Cloud Logging
try:
    from google.cloud import logging as cloud_logging
    LOGGING_AVAILABLE = True
except ImportError:
    LOGGING_AVAILABLE = False
    cloud_logging = None

# Google Cloud Secret Manager
try:
    from google.cloud import secretmanager
    SECRET_MANAGER_AVAILABLE = True
except ImportError:
    SECRET_MANAGER_AVAILABLE = False
    secretmanager = None

# Vertex AI
try:
    from google.cloud import aiplatform
    VERTEX_AI_AVAILABLE = True
except ImportError:
    VERTEX_AI_AVAILABLE = False
    aiplatform = None


class GoogleCloudService:
    """Comprehensive Google Cloud Platform integration."""
    
    def __init__(self):
        self.project_id = os.getenv("GCP_PROJECT_ID")
        self.storage_client = None
        self.logging_client = None
        self.secret_client = None
        self.bucket_name = os.getenv("GCP_STORAGE_BUCKET")
        
        self._init_services()
    
    def _init_services(self) -> None:
        """Initialize Google Cloud services."""
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        
        # Initialize Storage
        if STORAGE_AVAILABLE and credentials_path:
            try:
                self.storage_client = storage.Client(project=self.project_id)
            except Exception:
                pass
        
        # Initialize Logging
        if LOGGING_AVAILABLE and credentials_path:
            try:
                self.logging_client = cloud_logging.Client(project=self.project_id)
                self.logger = self.logging_client.logger("racing-game")
            except Exception:
                self.logger = None
        
        # Initialize Secret Manager
        if SECRET_MANAGER_AVAILABLE and credentials_path:
            try:
                self.secret_client = secretmanager.SecretManagerServiceClient()
            except Exception:
                pass
    
    def healthy(self) -> bool:
        """Check if any GCP service is available."""
        return any([
            self.storage_client is not None,
            self.logging_client is not None,
            self.secret_client is not None
        ])
    
    # ==================== Cloud Storage ====================
    
    def upload_track_data(self, track_id: str, track_data: Dict[str, Any]) -> Optional[str]:
        """Upload track data to Cloud Storage."""
        if not self.storage_client or not self.bucket_name:
            return None
        
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(f"tracks/{track_id}.json")
            
            blob.upload_from_string(
                json.dumps(track_data),
                content_type="application/json"
            )
            
            return f"gs://{self.bucket_name}/tracks/{track_id}.json"
        except Exception:
            return None
    
    def download_track_data(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Download track data from Cloud Storage."""
        if not self.storage_client or not self.bucket_name:
            return None
        
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(f"tracks/{track_id}.json")
            
            if not blob.exists():
                return None
            
            data = blob.download_as_text()
            return json.loads(data)
        except Exception:
            return None
    
    def list_tracks(self, prefix: str = "tracks/") -> List[str]:
        """List all tracks in Cloud Storage."""
        if not self.storage_client or not self.bucket_name:
            return []
        
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blobs = bucket.list_blobs(prefix=prefix)
            
            return [blob.name for blob in blobs]
        except Exception:
            return []
    
    def upload_race_replay(self, user_id: str, race_id: str, 
                          replay_data: List[Dict[str, Any]]) -> Optional[str]:
        """Upload race replay to Cloud Storage."""
        if not self.storage_client or not self.bucket_name:
            return None
        
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(f"replays/{user_id}/{race_id}.json")
            
            blob.upload_from_string(
                json.dumps(replay_data),
                content_type="application/json"
            )
            
            # Set metadata
            blob.metadata = {
                "user_id": user_id,
                "race_id": race_id,
                "uploaded_at": datetime.utcnow().isoformat()
            }
            blob.patch()
            
            return f"gs://{self.bucket_name}/replays/{user_id}/{race_id}.json"
        except Exception:
            return None
    
    # ==================== Cloud Logging ====================
    
    def log_race_event(self, event_type: str, event_data: Dict[str, Any], 
                      severity: str = "INFO") -> bool:
        """Log race event to Cloud Logging."""
        if not self.logger:
            return False
        
        try:
            self.logger.log_struct(
                {
                    "event_type": event_type,
                    "timestamp": datetime.utcnow().isoformat(),
                    **event_data
                },
                severity=severity
            )
            return True
        except Exception:
            return False
    
    def log_error(self, error_message: str, error_data: Dict[str, Any]) -> bool:
        """Log error to Cloud Logging."""
        if not self.logger:
            return False
        
        try:
            self.logger.log_struct(
                {
                    "error_message": error_message,
                    "timestamp": datetime.utcnow().isoformat(),
                    **error_data
                },
                severity="ERROR"
            )
            return True
        except Exception:
            return False
    
    def log_performance_metric(self, metric_name: str, value: float, 
                              labels: Dict[str, str]) -> bool:
        """Log performance metric to Cloud Logging."""
        if not self.logger:
            return False
        
        try:
            self.logger.log_struct(
                {
                    "metric_name": metric_name,
                    "value": value,
                    "labels": labels,
                    "timestamp": datetime.utcnow().isoformat()
                },
                severity="INFO"
            )
            return True
        except Exception:
            return False
    
    # ==================== Secret Manager ====================
    
    def get_secret(self, secret_id: str, version: str = "latest") -> Optional[str]:
        """Get secret from Secret Manager."""
        if not self.secret_client or not self.project_id:
            return None
        
        try:
            name = f"projects/{self.project_id}/secrets/{secret_id}/versions/{version}"
            response = self.secret_client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception:
            return None
    
    def create_secret(self, secret_id: str, secret_value: str) -> bool:
        """Create a new secret in Secret Manager."""
        if not self.secret_client or not self.project_id:
            return False
        
        try:
            parent = f"projects/{self.project_id}"
            
            # Create secret
            secret = self.secret_client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_id,
                    "secret": {"replication": {"automatic": {}}}
                }
            )
            
            # Add secret version
            self.secret_client.add_secret_version(
                request={
                    "parent": secret.name,
                    "payload": {"data": secret_value.encode("UTF-8")}
                }
            )
            
            return True
        except Exception:
            return False
    
    # ==================== Monitoring & Analytics ====================
    
    def track_user_session(self, user_id: str, session_data: Dict[str, Any]) -> bool:
        """Track user session for analytics."""
        if not self.logger:
            return False
        
        try:
            self.logger.log_struct(
                {
                    "event_type": "user_session",
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    **session_data
                },
                severity="INFO"
            )
            return True
        except Exception:
            return False
    
    def track_race_completion(self, race_data: Dict[str, Any]) -> bool:
        """Track race completion for analytics."""
        if not self.logger:
            return False
        
        try:
            self.logger.log_struct(
                {
                    "event_type": "race_completed",
                    "timestamp": datetime.utcnow().isoformat(),
                    **race_data
                },
                severity="INFO"
            )
            return True
        except Exception:
            return False
    
    def track_ai_decision(self, decision_data: Dict[str, Any]) -> bool:
        """Track AI decision for analysis."""
        if not self.logger:
            return False
        
        try:
            self.logger.log_struct(
                {
                    "event_type": "ai_decision",
                    "timestamp": datetime.utcnow().isoformat(),
                    **decision_data
                },
                severity="DEBUG"
            )
            return True
        except Exception:
            return False


class VertexAIService:
    """Vertex AI integration for advanced ML capabilities."""
    
    def __init__(self):
        self.project_id = os.getenv("GCP_PROJECT_ID")
        self.location = os.getenv("GCP_LOCATION", "us-central1")
        self.initialized = False
        
        self._init_vertex_ai()
    
    def _init_vertex_ai(self) -> None:
        """Initialize Vertex AI."""
        if not VERTEX_AI_AVAILABLE or not self.project_id:
            return
        
        try:
            aiplatform.init(
                project=self.project_id,
                location=self.location
            )
            self.initialized = True
        except Exception:
            pass
    
    def healthy(self) -> bool:
        """Check if Vertex AI is initialized."""
        return self.initialized
    
    def predict_race_outcome(self, race_features: Dict[str, Any]) -> Dict[str, Any]:
        """Predict race outcome using Vertex AI."""
        if not self.initialized:
            return {"predicted_time": 0, "confidence": 0}
        
        try:
            # This would use a trained model endpoint
            # For now, return placeholder
            return {
                "predicted_time": race_features.get("track_length", 100) / 10,
                "predicted_crashes": 0,
                "confidence": 0.85
            }
        except Exception:
            return {"predicted_time": 0, "confidence": 0}
    
    def get_personalized_difficulty(self, user_history: List[Dict[str, Any]]) -> str:
        """Get personalized difficulty recommendation using ML."""
        if not self.initialized or not user_history:
            return "medium"
        
        try:
            # Analyze user performance
            avg_crashes = sum(r.get("crashes", 0) for r in user_history) / len(user_history)
            avg_completion = sum(r.get("completed", 0) for r in user_history) / len(user_history)
            
            if avg_crashes > 3 or avg_completion < 0.5:
                return "easy"
            elif avg_crashes < 1 and avg_completion > 0.9:
                return "hard"
            else:
                return "medium"
        except Exception:
            return "medium"
