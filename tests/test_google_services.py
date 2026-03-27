"""Comprehensive tests for all Google Services integrations."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime


class TestFirebaseService:
    """Tests for Firebase integration."""
    
    @pytest.fixture
    def firebase_service(self):
        """Create Firebase service instance."""
        with patch('firebase_config.FIREBASE_AVAILABLE', True):
            with patch('firebase_config.firebase_admin'):
                from firebase_config import FirebaseService
                service = FirebaseService()
                service.initialized = True
                service.db = Mock()
                service.bucket = Mock()
                return service
    
    def test_initialization(self, firebase_service):
        """Test Firebase service initialization."""
        assert firebase_service.initialized is True
        assert firebase_service.db is not None
    
    def test_healthy_check(self, firebase_service):
        """Test health check."""
        assert firebase_service.healthy() is True
    
    def test_save_race_result(self, firebase_service):
        """Test saving race result."""
        mock_doc_ref = Mock()
        mock_doc_ref.id = "race123"
        firebase_service.db.collection.return_value.add.return_value = (None, mock_doc_ref)
        
        race_data = {
            "difficulty": "hard",
            "time": 45.2,
            "crashes": 1
        }
        
        result = firebase_service.save_race_result("user123", race_data)
        assert result == "race123"
    
    def test_get_user_races(self, firebase_service):
        """Test retrieving user races."""
        mock_doc = Mock()
        mock_doc.id = "race123"
        mock_doc.to_dict.return_value = {"difficulty": "hard", "time": 45.2}
        
        firebase_service.db.collection.return_value.where.return_value.order_by.return_value.limit.return_value.stream.return_value = [mock_doc]
        
        races = firebase_service.get_user_races("user123", limit=10)
        assert len(races) == 1
        assert races[0]["id"] == "race123"
    
    def test_update_leaderboard(self, firebase_service):
        """Test leaderboard update."""
        mock_doc = Mock()
        mock_doc.exists = False
        firebase_service.db.collection.return_value.document.return_value.get.return_value = mock_doc
        
        result = firebase_service.update_leaderboard("user123", "Player1", 8500, "hard", 150)
        assert result is True
    
    def test_get_leaderboard(self, firebase_service):
        """Test retrieving leaderboard."""
        mock_doc = Mock()
        mock_doc.id = "user123"
        mock_doc.to_dict.return_value = {"username": "Player1", "best_score": 8500}
        
        firebase_service.db.collection.return_value.order_by.return_value.limit.return_value.stream.return_value = [mock_doc]
        
        leaders = firebase_service.get_leaderboard(limit=10)
        assert len(leaders) == 1
        assert leaders[0]["username"] == "Player1"


class TestAdvancedGeminiService:
    """Tests for Advanced Gemini features."""
    
    @pytest.fixture
    def gemini_service(self):
        """Create Advanced Gemini service."""
        with patch('gemini_advanced.genai'):
            from gemini_advanced import AdvancedGeminiService
            service = AdvancedGeminiService(api_key="test-key")
            service.model = Mock()
            return service
    
    def test_initialization(self, gemini_service):
        """Test service initialization."""
        assert gemini_service.model is not None
    
    def test_healthy_check(self, gemini_service):
        """Test health check."""
        assert gemini_service.healthy() is True
    
    def test_function_calling_track_generation(self, gemini_service):
        """Test track generation with function calling."""
        mock_response = Mock()
        mock_response.candidates = []
        gemini_service.model.generate_content.return_value = mock_response
        
        track = gemini_service.generate_track_with_functions("hard", "cyberpunk", 15)
        
        assert isinstance(track, dict)
        assert "segments" in track
    
    def test_coaching_session(self, gemini_service):
        """Test multi-turn coaching session."""
        gemini_service.model.start_chat.return_value = Mock()
        
        gemini_service.start_coaching_session({"level": 5, "avg_speed": 120})
        assert gemini_service.chat_session is not None
    
    def test_get_coaching_advice(self, gemini_service):
        """Test getting coaching advice."""
        mock_chat = Mock()
        mock_response = Mock()
        mock_response.text = "Great job! Try braking earlier on curves."
        mock_chat.send_message.return_value = mock_response
        
        gemini_service.chat_session = mock_chat
        
        advice = gemini_service.get_coaching_advice({
            "avg_speed": 120,
            "crashes": 2,
            "time": 45.5
        })
        
        assert isinstance(advice, str)
        assert len(advice) > 0
    
    def test_streaming_commentary(self, gemini_service):
        """Test streaming commentary generation."""
        mock_chunk1 = Mock()
        mock_chunk1.text = "The rider "
        mock_chunk2 = Mock()
        mock_chunk2.text = "accelerates hard!"
        
        gemini_service.model.generate_content.return_value = [mock_chunk1, mock_chunk2]
        
        chunks = gemini_service.generate_commentary_stream("accelerate", "straight", 145.5)
        
        assert isinstance(chunks, list)
        assert len(chunks) > 0
    
    def test_decision_with_reasoning(self, gemini_service):
        """Test decision making with reasoning."""
        mock_response = Mock()
        mock_response.text = json.dumps({
            "action": "brake",
            "reason": "Approaching sharp curve",
            "reasoning_steps": ["Analyze speed", "Check segment", "Choose action"]
        })
        gemini_service.model.generate_content.return_value = mock_response
        
        decision = gemini_service.decide_with_reasoning({
            "speed": 150,
            "segment_type": "curve",
            "difficulty": 0.8
        })
        
        assert decision["action"] == "brake"
        assert "reasoning_steps" in decision
    
    def test_batch_analyze_races(self, gemini_service):
        """Test batch race analysis."""
        mock_response = Mock()
        mock_response.text = json.dumps({"rating": 8, "tip": "Brake earlier"})
        gemini_service.model.generate_content.return_value = mock_response
        
        races = [
            {"avg_speed": 120, "crashes": 1, "time": 45.2},
            {"avg_speed": 110, "crashes": 2, "time": 52.1}
        ]
        
        results = gemini_service.batch_analyze_races(races)
        
        assert len(results) == 2
        assert all("rating" in r for r in results)


class TestGoogleCloudService:
    """Tests for Google Cloud Platform integration."""
    
    @pytest.fixture
    def gcp_service(self):
        """Create GCP service instance."""
        with patch('google_cloud_integration.STORAGE_AVAILABLE', True):
            with patch('google_cloud_integration.storage'):
                from google_cloud_integration import GoogleCloudService
                service = GoogleCloudService()
                service.storage_client = Mock()
                service.logging_client = Mock()
                service.logger = Mock()
                service.bucket_name = "test-bucket"
                return service
    
    def test_initialization(self, gcp_service):
        """Test GCP service initialization."""
        assert gcp_service.storage_client is not None
    
    def test_healthy_check(self, gcp_service):
        """Test health check."""
        assert gcp_service.healthy() is True
    
    def test_upload_track_data(self, gcp_service):
        """Test uploading track data."""
        mock_bucket = Mock()
        mock_blob = Mock()
        mock_bucket.blob.return_value = mock_blob
        gcp_service.storage_client.bucket.return_value = mock_bucket
        
        track_data = {"segments": [{"type": "straight", "length": 100}]}
        result = gcp_service.upload_track_data("track123", track_data)
        
        assert result is not None
        assert "track123" in result
    
    def test_download_track_data(self, gcp_service):
        """Test downloading track data."""
        mock_bucket = Mock()
        mock_blob = Mock()
        mock_blob.exists.return_value = True
        mock_blob.download_as_text.return_value = json.dumps({"segments": []})
        mock_bucket.blob.return_value = mock_blob
        gcp_service.storage_client.bucket.return_value = mock_bucket
        
        track = gcp_service.download_track_data("track123")
        
        assert track is not None
        assert "segments" in track
    
    def test_log_race_event(self, gcp_service):
        """Test logging race event."""
        result = gcp_service.log_race_event("race_completed", {
            "user_id": "user123",
            "time": 45.2
        })
        
        assert result is True
        assert gcp_service.logger.log_struct.called
    
    def test_log_error(self, gcp_service):
        """Test error logging."""
        result = gcp_service.log_error("Track generation failed", {
            "error_code": "500",
            "user_id": "user123"
        })
        
        assert result is True
    
    def test_track_user_session(self, gcp_service):
        """Test user session tracking."""
        result = gcp_service.track_user_session("user123", {
            "duration": 300,
            "races_completed": 3
        })
        
        assert result is True


class TestGoogleAnalyticsService:
    """Tests for Google Analytics 4 integration."""
    
    @pytest.fixture
    def ga_service(self):
        """Create GA4 service instance."""
        with patch.dict('os.environ', {
            'GA4_MEASUREMENT_ID': 'G-TEST123',
            'GA4_API_SECRET': 'test-secret'
        }):
            with patch('google_analytics_integration.REQUESTS_AVAILABLE', True):
                from google_analytics_integration import GoogleAnalyticsService
                service = GoogleAnalyticsService()
                return service
    
    def test_initialization(self, ga_service):
        """Test GA4 service initialization."""
        assert ga_service.measurement_id == 'G-TEST123'
        assert ga_service.enabled is True
    
    def test_healthy_check(self, ga_service):
        """Test health check."""
        assert ga_service.healthy() is True
    
    @patch('google_analytics_integration.requests.post')
    def test_track_race_start(self, mock_post, ga_service):
        """Test tracking race start."""
        mock_post.return_value.status_code = 204
        
        result = ga_service.track_race_start("user123", "hard", "cyberpunk", 150)
        
        assert result is True
        assert mock_post.called
    
    @patch('google_analytics_integration.requests.post')
    def test_track_race_complete(self, mock_post, ga_service):
        """Test tracking race completion."""
        mock_post.return_value.status_code = 204
        
        result = ga_service.track_race_complete("user123", {
            "difficulty": "hard",
            "time": 45.2,
            "crashes": 1,
            "avg_speed": 125.5,
            "score": 8500
        })
        
        assert result is True
    
    @patch('google_analytics_integration.requests.post')
    def test_track_ai_decision(self, mock_post, ga_service):
        """Test tracking AI decision."""
        mock_post.return_value.status_code = 204
        
        result = ga_service.track_ai_decision("user123", "overtake", "curve", 145.5)
        
        assert result is True
    
    @patch('google_analytics_integration.requests.post')
    def test_track_achievement_unlock(self, mock_post, ga_service):
        """Test tracking achievement unlock."""
        mock_post.return_value.status_code = 204
        
        result = ga_service.track_achievement_unlock(
            "user123",
            "first_win",
            "First Race Victory"
        )
        
        assert result is True


class TestIntegration:
    """Integration tests for Google Services."""
    
    def test_complete_race_workflow_with_services(self):
        """Test complete race workflow with all services."""
        with patch('firebase_config.FIREBASE_AVAILABLE', True):
            with patch('google_analytics_integration.REQUESTS_AVAILABLE', True):
                with patch('firebase_config.firebase_admin'):
                    with patch('google_analytics_integration.requests.post') as mock_post:
                        mock_post.return_value.status_code = 204
                        
                        from firebase_config import FirebaseService
                        from google_analytics_integration import GoogleAnalyticsService
                        
                        firebase = FirebaseService()
                        firebase.initialized = True
                        firebase.db = Mock()
                        
                        ga = GoogleAnalyticsService()
                        
                        # Simulate race workflow
                        user_id = "user123"
                        
                        # Track race start
                        ga.track_race_start(user_id, "hard", "cyberpunk", 150)
                        
                        # Simulate race completion
                        race_data = {
                            "difficulty": "hard",
                            "time": 45.2,
                            "crashes": 1,
                            "avg_speed": 125.5
                        }
                        
                        # Save to Firebase
                        mock_doc_ref = Mock()
                        mock_doc_ref.id = "race123"
                        firebase.db.collection.return_value.add.return_value = (None, mock_doc_ref)
                        
                        race_id = firebase.save_race_result(user_id, race_data)
                        assert race_id == "race123"
                        
                        # Track completion
                        ga.track_race_complete(user_id, race_data)
                        
                        # Verify all services called
                        assert firebase.db.collection.called
                        assert mock_post.called
    
    def test_service_fallback_chain(self):
        """Test graceful fallback when services unavailable."""
        with patch('firebase_config.FIREBASE_AVAILABLE', False):
            from firebase_config import FirebaseService
            
            service = FirebaseService()
            assert service.healthy() is False
            
            # Should handle gracefully
            result = service.save_race_result("user123", {})
            assert result is None
    
    def test_error_handling_across_services(self):
        """Test error handling across all services."""
        with patch('gemini_advanced.genai'):
            from gemini_advanced import AdvancedGeminiService
            
            service = AdvancedGeminiService(api_key="test-key")
            service.model = None
            
            # Should use fallback
            track = service.generate_track_with_functions("hard", "city", 15)
            assert isinstance(track, dict)
            assert "segments" in track
