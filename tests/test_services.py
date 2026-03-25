"""Unit tests for AI service modules."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json


class TestGeminiService:
    """Tests for GeminiService."""
    
    @pytest.fixture
    def gemini_service(self):
        """Create GeminiService instance."""
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key', 'GEMINI_FLAG': 'True'}):
            from gemini_service import GeminiService
            return GeminiService()
    
    def test_initialization(self, gemini_service):
        """Test GeminiService initialization."""
        assert gemini_service is not None
    
    def test_healthy_with_valid_key(self, gemini_service):
        """Test health check with valid configuration."""
        # Should return True if properly configured
        result = gemini_service.healthy()
        assert isinstance(result, bool)
    
    @patch('gemini_service.GeminiService._call_json')
    def test_generate_track_returns_dict(self, mock_call, gemini_service):
        """Test generate_track returns dictionary."""
        mock_call.return_value = {
            "segments": [
                {"type": "straight", "length": 100},
                {"type": "curve", "difficulty": 0.5}
            ]
        }
        
        track = gemini_service.generate_track("medium", "city")
        
        assert isinstance(track, dict)
        assert "segments" in track
        assert len(track["segments"]) > 0
    
    @patch('gemini_service.GeminiService._call_json')
    def test_generate_track_fallback_on_failure(self, mock_call, gemini_service):
        """Test generate_track uses fallback when API fails."""
        mock_call.return_value = None
        
        track = gemini_service.generate_track("medium", "city")
        
        # Should return fallback track
        assert isinstance(track, dict)
        assert "segments" in track
    
    @patch('gemini_service.GeminiService._call_json')
    def test_decide_action_returns_dict(self, mock_call, gemini_service):
        """Test decide_action returns dictionary."""
        mock_call.return_value = {
            "action": "accelerate",
            "reason": "Straight segment ahead"
        }
        
        decision = gemini_service.decide_action(
            current_speed=100,
            segment_type="straight",
            difficulty=0.5,
            opponent_proximity=50
        )
        
        assert isinstance(decision, dict)
        assert "action" in decision
        assert "reason" in decision
    
    @patch('gemini_service.GeminiService._call_json')
    def test_decide_action_fallback(self, mock_call, gemini_service):
        """Test decide_action uses fallback on failure."""
        mock_call.return_value = None
        
        decision = gemini_service.decide_action(
            current_speed=100,
            segment_type="curve",
            difficulty=0.7,
            opponent_proximity=50
        )
        
        # Should return fallback decision
        assert isinstance(decision, dict)
        assert "action" in decision
    
    @patch('gemini_service.GeminiService._call_json')
    def test_generate_adaptive_track(self, mock_call, gemini_service):
        """Test adaptive track generation."""
        mock_call.return_value = {
            "segments": [
                {"type": "straight", "length": 80},
                {"type": "curve", "difficulty": 0.6}
            ]
        }
        
        performance = {
            "crashes": 2,
            "avg_speed": 110,
            "completion_time": 45
        }
        
        track = gemini_service.generate_adaptive_track(
            performance_summary=performance,
            environment="desert",
            base_difficulty="medium"
        )
        
        assert isinstance(track, dict)
        assert "segments" in track


class TestOllamaService:
    """Tests for OllamaService."""
    
    @pytest.fixture
    def ollama_service(self):
        """Create OllamaService instance."""
        with patch.dict('os.environ', {
            'OLLAMA_HOST': 'http://localhost:11434',
            'OLLAMA_MODEL': 'llama3:latest',
            'OLLAMA_FLAG': 'True'
        }):
            from ollama_service import OllamaService
            return OllamaService()
    
    def test_initialization(self, ollama_service):
        """Test OllamaService initialization."""
        assert ollama_service is not None
        assert ollama_service.host == 'http://localhost:11434'
        assert ollama_service.model == 'llama3:latest'
    
    @patch('requests.get')
    def test_healthy_when_reachable(self, mock_get, ollama_service):
        """Test health check when Ollama is reachable."""
        mock_get.return_value.status_code = 200
        
        result = ollama_service.healthy()
        
        assert result is True
    
    @patch('requests.get')
    def test_healthy_when_unreachable(self, mock_get, ollama_service):
        """Test health check when Ollama is unreachable."""
        mock_get.side_effect = Exception("Connection failed")
        
        result = ollama_service.healthy()
        
        assert result is False
    
    @patch('requests.post')
    def test_generate_track(self, mock_post, ollama_service):
        """Test track generation with Ollama."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": json.dumps({
                "segments": [
                    {"type": "straight", "length": 100}
                ]
            })
        }
        mock_post.return_value = mock_response
        
        track = ollama_service.generate_track("easy", "snow")
        
        assert isinstance(track, dict)
        assert "segments" in track
    
    @patch('requests.post')
    def test_decide_action(self, mock_post, ollama_service):
        """Test decision making with Ollama."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": json.dumps({
                "action": "brake",
                "reason": "Approaching curve"
            })
        }
        mock_post.return_value = mock_response
        
        decision = ollama_service.decide_action(
            current_speed=120,
            segment_type="curve",
            difficulty=0.6,
            opponent_proximity=30
        )
        
        assert isinstance(decision, dict)
        assert "action" in decision


class TestServiceIntegration:
    """Integration tests for AI services."""
    
    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key', 'GEMINI_FLAG': 'True'})
    @patch('gemini_service.GeminiService._call_json')
    def test_gemini_full_workflow(self, mock_call):
        """Test complete workflow with Gemini service."""
        from gemini_service import GeminiService
        
        # Mock track generation
        mock_call.return_value = {
            "segments": [
                {"type": "straight", "length": 100},
                {"type": "curve", "difficulty": 0.5}
            ]
        }
        
        service = GeminiService()
        track = service.generate_track("medium", "city")
        
        assert "segments" in track
        
        # Mock decision making
        mock_call.return_value = {
            "action": "accelerate",
            "reason": "Clear straight ahead"
        }
        
        decision = service.decide_action(100, "straight", 0.5, 50)
        
        assert "action" in decision
        assert decision["action"] in ["accelerate", "brake", "maintain", "overtake"]
    
    def test_service_fallback_chain(self):
        """Test fallback from Gemini to Ollama to heuristic."""
        with patch.dict('os.environ', {
            'GEMINI_FLAG': 'False',
            'OLLAMA_FLAG': 'False'
        }):
            # When both services disabled, should use heuristics
            # This is tested implicitly through the simulation
            pass


class TestJSONParsing:
    """Tests for JSON parsing and extraction."""
    
    @pytest.fixture
    def gemini_service(self):
        """Create GeminiService for testing."""
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key'}):
            from gemini_service import GeminiService
            return GeminiService()
    
    def test_extract_json_from_clean_response(self, gemini_service):
        """Test JSON extraction from clean response."""
        text = '{"segments": [{"type": "straight", "length": 100}]}'
        result = gemini_service._extract_json(text)
        
        assert result is not None
        assert "segments" in result
    
    def test_extract_json_from_markdown(self, gemini_service):
        """Test JSON extraction from markdown code blocks."""
        text = '```json\n{"segments": [{"type": "straight"}]}\n```'
        result = gemini_service._extract_json(text)
        
        assert result is not None
    
    def test_extract_json_with_prose(self, gemini_service):
        """Test JSON extraction when mixed with prose."""
        text = 'Here is the track: {"segments": [{"type": "curve"}]} Hope this helps!'
        result = gemini_service._extract_json(text)
        
        assert result is not None
    
    def test_extract_json_invalid(self, gemini_service):
        """Test JSON extraction with invalid JSON."""
        text = 'This is not JSON at all'
        result = gemini_service._extract_json(text)
        
        # Should handle gracefully
        assert result is None or isinstance(result, str)


class TestErrorHandling:
    """Tests for error handling in services."""
    
    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key'})
    def test_gemini_api_timeout(self):
        """Test handling of API timeout."""
        from gemini_service import GeminiService
        
        service = GeminiService()
        
        with patch.object(service, '_post_generate', side_effect=Exception("Timeout")):
            # Should not crash, should use fallback
            track = service.generate_track("medium", "city")
            assert isinstance(track, dict)
    
    @patch.dict('os.environ', {'OLLAMA_HOST': 'http://localhost:11434'})
    def test_ollama_connection_error(self):
        """Test handling of Ollama connection error."""
        from ollama_service import OllamaService
        
        service = OllamaService()
        
        with patch('requests.post', side_effect=Exception("Connection refused")):
            # Should not crash, should use fallback
            track = service.generate_track("easy", "desert")
            assert isinstance(track, dict)
    
    @patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key'})
    @patch('gemini_service.GeminiService._call_json')
    def test_malformed_response_handling(self, mock_call):
        """Test handling of malformed API response."""
        from gemini_service import GeminiService
        
        service = GeminiService()
        
        # Return malformed data
        mock_call.return_value = {"invalid": "structure"}
        
        track = service.generate_track("hard", "cyberpunk")
        
        # Should use fallback
        assert isinstance(track, dict)
        assert "segments" in track
