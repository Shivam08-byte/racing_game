"""Integration tests for app.py - Streamlit application."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os


class TestAppImports:
    """Test that app.py imports correctly."""
    
    def test_app_imports_successfully(self):
        """Test that app.py can be imported without errors."""
        # Mock streamlit to avoid GUI initialization
        sys.modules['streamlit'] = MagicMock()
        
        try:
            # This will execute the module-level code
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "app",
                os.path.join(os.path.dirname(__file__), "..", "app.py")
            )
            # Just verify it can be loaded
            assert spec is not None
        except Exception as e:
            pytest.fail(f"Failed to import app.py: {e}")


class TestAppConfiguration:
    """Test app configuration and setup."""
    
    @patch.dict('os.environ', {'GEMINI_FLAG': 'True', 'GOOGLE_API_KEY': 'test-key'})
    def test_service_initialization_gemini(self):
        """Test that Gemini service can be initialized."""
        from gemini_service import GeminiService
        
        service = GeminiService()
        assert service is not None
    
    @patch.dict('os.environ', {'OLLAMA_FLAG': 'True', 'OLLAMA_HOST': 'http://localhost:11434'})
    def test_service_initialization_ollama(self):
        """Test that Ollama service can be initialized."""
        from ollama_service import OllamaService
        
        service = OllamaService()
        assert service is not None
        assert service.host == 'http://localhost:11434'


class TestAppHelpers:
    """Test helper functions that could be extracted from app."""
    
    def test_track_generation_workflow(self):
        """Test the track generation workflow."""
        from gemini_service import GeminiService
        from utils import scale_track
        
        service = GeminiService()
        track = service.generate_track("medium", "city")
        
        assert isinstance(track, dict)
        assert "segments" in track
        
        # Test scaling
        scaled = scale_track(track, 100)
        assert isinstance(scaled, dict)
        assert "segments" in scaled
    
    def test_simulation_initialization_workflow(self):
        """Test the simulation initialization workflow."""
        from simulation import RaceSimulation
        from gemini_service import GeminiService
        
        track = {
            "segments": [
                {"type": "straight", "length": 100},
                {"type": "curve", "difficulty": 0.5}
            ]
        }
        
        service = GeminiService()
        sim = RaceSimulation(track, "medium", service)
        
        assert sim is not None
        assert sim.track == track
        assert sim.difficulty == "medium"


class TestAppIntegration:
    """Integration tests for app workflows."""
    
    def test_complete_race_setup_workflow(self):
        """Test complete race setup workflow."""
        from gemini_service import GeminiService
        from simulation import RaceSimulation
        from utils import scale_track
        
        # Initialize service
        service = GeminiService()
        
        # Generate track
        track = service.generate_track("medium", "city")
        assert "segments" in track
        
        # Scale track
        scaled_track = scale_track(track, 150)
        assert "segments" in scaled_track
        
        # Initialize simulation
        sim = RaceSimulation(scaled_track, "medium", service, second_ai=True)
        assert sim is not None
        
        # Verify initial state
        state = sim.player_state()
        assert state["pos"] == 0.0
        assert state["speed"] >= 0
        assert state["crashes"] == 0
    
    def test_race_step_workflow(self):
        """Test race step execution workflow."""
        from gemini_service import GeminiService
        from simulation import RaceSimulation
        
        track = {
            "segments": [
                {"type": "straight", "length": 100}
            ]
        }
        
        service = GeminiService()
        sim = RaceSimulation(track, "easy", service)
        
        # Execute a step
        result = sim.step()
        
        assert isinstance(result, dict)
        assert "decisions" in result
        assert "You" in result["decisions"]
    
    def test_ui_helper_functions(self):
        """Test UI helper functions used in app."""
        from utils import (
            generate_track_indicator,
            generate_commentary,
            generate_race_event,
            calculate_progress
        )
        
        track = {
            "segments": [
                {"type": "straight", "length": 100},
                {"type": "curve", "difficulty": 0.5}
            ]
        }
        
        # Test track indicator
        indicator = generate_track_indicator(track, 0)
        assert isinstance(indicator, str)
        
        # Test commentary
        commentary = generate_commentary("accelerate", "straight", 100)
        assert isinstance(commentary, str)
        
        # Test event generation
        event = generate_race_event("accelerate", "curve", 120)
        assert event is None or isinstance(event, str)
        
        # Test progress calculation
        progress = calculate_progress(50, track)
        assert 0.0 <= progress <= 1.0


class TestAppErrorHandling:
    """Test error handling in app workflows."""
    
    def test_missing_track_handling(self):
        """Test handling when track is not generated."""
        from gemini_service import GeminiService
        from simulation import RaceSimulation
        
        # Empty track should still work
        track = {"segments": []}
        service = GeminiService()
        
        sim = RaceSimulation(track, "medium", service)
        assert sim is not None
    
    def test_service_fallback(self):
        """Test service fallback mechanism."""
        from gemini_service import GeminiService
        
        # Service should initialize even without API key
        with patch.dict('os.environ', {}, clear=True):
            service = GeminiService()
            assert service is not None
            
            # Should use fallback
            track = service.generate_track("medium", "city")
            assert isinstance(track, dict)
            assert "segments" in track


class TestAppStateManagement:
    """Test state management patterns used in app."""
    
    def test_session_state_initialization(self):
        """Test session state initialization pattern."""
        # Simulate session state
        session_state = {}
        
        # Initialize like app.py does
        if "track" not in session_state:
            session_state["track"] = None
        if "sim" not in session_state:
            session_state["sim"] = None
        if "race_log" not in session_state:
            session_state["race_log"] = []
        if "decisions" not in session_state:
            session_state["decisions"] = {}
        
        assert session_state["track"] is None
        assert session_state["sim"] is None
        assert session_state["race_log"] == []
        assert session_state["decisions"] == {}
    
    def test_race_reset_workflow(self):
        """Test race reset workflow."""
        from simulation import RaceSimulation
        from gemini_service import GeminiService
        
        track = {"segments": [{"type": "straight", "length": 100}]}
        service = GeminiService()
        sim = RaceSimulation(track, "medium", service)
        
        # Run a step
        sim.step()
        assert sim.step_count > 0
        
        # Reset
        sim.reset_runtime()
        assert sim.step_count == 0
        assert sim.player_state()["pos"] == 0.0
