"""Google Analytics 4 integration for user behavior tracking."""

import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import hashlib

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class GoogleAnalyticsService:
    """Google Analytics 4 integration for comprehensive event tracking."""
    
    def __init__(self):
        self.measurement_id = os.getenv("GA4_MEASUREMENT_ID")
        self.api_secret = os.getenv("GA4_API_SECRET")
        self.endpoint = "https://www.google-analytics.com/mp/collect"
        self.debug_endpoint = "https://www.google-analytics.com/debug/mp/collect"
        self.enabled = bool(self.measurement_id and self.api_secret and REQUESTS_AVAILABLE)
    
    def healthy(self) -> bool:
        """Check if GA4 is configured."""
        return self.enabled
    
    def _generate_client_id(self, user_id: Optional[str] = None) -> str:
        """Generate a client ID for GA4."""
        if user_id:
            return hashlib.sha256(user_id.encode()).hexdigest()[:32]
        return hashlib.sha256(str(datetime.utcnow()).encode()).hexdigest()[:32]
    
    def _send_event(self, client_id: str, events: List[Dict[str, Any]], 
                   debug: bool = False) -> bool:
        """Send event to Google Analytics 4."""
        if not self.enabled:
            return False
        
        try:
            url = self.debug_endpoint if debug else self.endpoint
            params = {
                "measurement_id": self.measurement_id,
                "api_secret": self.api_secret
            }
            
            payload = {
                "client_id": client_id,
                "events": events
            }
            
            response = requests.post(
                url,
                params=params,
                json=payload,
                timeout=5
            )
            
            return response.status_code == 204 or (debug and response.status_code == 200)
        except Exception:
            return False
    
    # ==================== User Events ====================
    
    def track_page_view(self, user_id: Optional[str], page_title: str, 
                       page_location: str) -> bool:
        """Track page view event."""
        client_id = self._generate_client_id(user_id)
        
        events = [{
            "name": "page_view",
            "params": {
                "page_title": page_title,
                "page_location": page_location,
                "engagement_time_msec": "100"
            }
        }]
        
        return self._send_event(client_id, events)
    
    def track_user_login(self, user_id: str, method: str = "email") -> bool:
        """Track user login event."""
        client_id = self._generate_client_id(user_id)
        
        events = [{
            "name": "login",
            "params": {
                "method": method,
                "user_id": user_id
            }
        }]
        
        return self._send_event(client_id, events)
    
    def track_user_signup(self, user_id: str, method: str = "email") -> bool:
        """Track user signup event."""
        client_id = self._generate_client_id(user_id)
        
        events = [{
            "name": "sign_up",
            "params": {
                "method": method,
                "user_id": user_id
            }
        }]
        
        return self._send_event(client_id, events)
    
    # ==================== Game Events ====================
    
    def track_race_start(self, user_id: Optional[str], difficulty: str, 
                        environment: str, track_length: int) -> bool:
        """Track race start event."""
        client_id = self._generate_client_id(user_id)
        
        events = [{
            "name": "race_start",
            "params": {
                "difficulty": difficulty,
                "environment": environment,
                "track_length": track_length,
                "game_name": "AI Bike Racing Simulator"
            }
        }]
        
        return self._send_event(client_id, events)
    
    def track_race_complete(self, user_id: Optional[str], race_data: Dict[str, Any]) -> bool:
        """Track race completion event."""
        client_id = self._generate_client_id(user_id)
        
        events = [{
            "name": "race_complete",
            "params": {
                "difficulty": race_data.get("difficulty", "medium"),
                "environment": race_data.get("environment", "city"),
                "completion_time": race_data.get("time", 0),
                "crashes": race_data.get("crashes", 0),
                "avg_speed": race_data.get("avg_speed", 0),
                "track_length": race_data.get("track_length", 100),
                "score": race_data.get("score", 0),
                "game_name": "AI Bike Racing Simulator"
            }
        }]
        
        return self._send_event(client_id, events)
    
    def track_race_abandon(self, user_id: Optional[str], reason: str, 
                          progress: float) -> bool:
        """Track race abandonment."""
        client_id = self._generate_client_id(user_id)
        
        events = [{
            "name": "race_abandon",
            "params": {
                "reason": reason,
                "progress_percent": int(progress * 100),
                "game_name": "AI Bike Racing Simulator"
            }
        }]
        
        return self._send_event(client_id, events)
    
    def track_level_up(self, user_id: str, level: int, character: str = "player") -> bool:
        """Track level up event."""
        client_id = self._generate_client_id(user_id)
        
        events = [{
            "name": "level_up",
            "params": {
                "level": level,
                "character": character,
                "game_name": "AI Bike Racing Simulator"
            }
        }]
        
        return self._send_event(client_id, events)
    
    # ==================== AI Interaction Events ====================
    
    def track_track_generation(self, user_id: Optional[str], difficulty: str, 
                              environment: str, ai_service: str) -> bool:
        """Track AI track generation."""
        client_id = self._generate_client_id(user_id)
        
        events = [{
            "name": "track_generated",
            "params": {
                "difficulty": difficulty,
                "environment": environment,
                "ai_service": ai_service,
                "feature": "ai_track_generation"
            }
        }]
        
        return self._send_event(client_id, events)
    
    def track_ai_decision(self, user_id: Optional[str], action: str, 
                         segment_type: str, speed: float) -> bool:
        """Track AI decision making."""
        client_id = self._generate_client_id(user_id)
        
        events = [{
            "name": "ai_decision",
            "params": {
                "action": action,
                "segment_type": segment_type,
                "speed": int(speed),
                "feature": "ai_racing_decision"
            }
        }]
        
        return self._send_event(client_id, events)
    
    # ==================== Engagement Events ====================
    
    def track_button_click(self, user_id: Optional[str], button_name: str, 
                          page: str) -> bool:
        """Track button click event."""
        client_id = self._generate_client_id(user_id)
        
        events = [{
            "name": "button_click",
            "params": {
                "button_name": button_name,
                "page": page
            }
        }]
        
        return self._send_event(client_id, events)
    
    def track_feature_usage(self, user_id: Optional[str], feature_name: str, 
                           usage_count: int = 1) -> bool:
        """Track feature usage."""
        client_id = self._generate_client_id(user_id)
        
        events = [{
            "name": "feature_usage",
            "params": {
                "feature_name": feature_name,
                "usage_count": usage_count
            }
        }]
        
        return self._send_event(client_id, events)
    
    def track_error(self, user_id: Optional[str], error_type: str, 
                   error_message: str, page: str) -> bool:
        """Track error event."""
        client_id = self._generate_client_id(user_id)
        
        events = [{
            "name": "error_occurred",
            "params": {
                "error_type": error_type,
                "error_message": error_message[:100],  # Limit length
                "page": page
            }
        }]
        
        return self._send_event(client_id, events)
    
    # ==================== E-commerce Events (for gamification) ====================
    
    def track_achievement_unlock(self, user_id: str, achievement_id: str, 
                                achievement_name: str) -> bool:
        """Track achievement unlock."""
        client_id = self._generate_client_id(user_id)
        
        events = [{
            "name": "unlock_achievement",
            "params": {
                "achievement_id": achievement_id,
                "achievement_name": achievement_name,
                "game_name": "AI Bike Racing Simulator"
            }
        }]
        
        return self._send_event(client_id, events)
    
    def track_leaderboard_view(self, user_id: Optional[str], 
                              leaderboard_type: str) -> bool:
        """Track leaderboard view."""
        client_id = self._generate_client_id(user_id)
        
        events = [{
            "name": "view_leaderboard",
            "params": {
                "leaderboard_type": leaderboard_type,
                "game_name": "AI Bike Racing Simulator"
            }
        }]
        
        return self._send_event(client_id, events)
    
    # ==================== Session Events ====================
    
    def track_session_start(self, user_id: Optional[str], 
                           session_data: Dict[str, Any]) -> bool:
        """Track session start."""
        client_id = self._generate_client_id(user_id)
        
        events = [{
            "name": "session_start",
            "params": {
                "session_id": session_data.get("session_id", ""),
                "platform": session_data.get("platform", "web"),
                "game_name": "AI Bike Racing Simulator"
            }
        }]
        
        return self._send_event(client_id, events)
    
    def track_session_end(self, user_id: Optional[str], duration_seconds: int, 
                         races_completed: int) -> bool:
        """Track session end."""
        client_id = self._generate_client_id(user_id)
        
        events = [{
            "name": "session_end",
            "params": {
                "session_duration": duration_seconds,
                "races_completed": races_completed,
                "game_name": "AI Bike Racing Simulator"
            }
        }]
        
        return self._send_event(client_id, events)
    
    # ==================== Batch Events ====================
    
    def track_multiple_events(self, user_id: Optional[str], 
                            events: List[Dict[str, Any]]) -> bool:
        """Track multiple events in a single request."""
        client_id = self._generate_client_id(user_id)
        return self._send_event(client_id, events)
