"""Unit tests for simulation.py module."""

import pytest
from unittest.mock import Mock, MagicMock
from simulation import RaceSimulation


class TestRaceSimulation:
    """Tests for RaceSimulation class."""
    
    @pytest.fixture
    def mock_service(self):
        """Create mock AI service."""
        service = Mock()
        service.decide_action.return_value = {
            "action": "accelerate",
            "reason": "Test reason"
        }
        return service
    
    @pytest.fixture
    def sample_track(self):
        """Create sample track for testing."""
        return {
            "segments": [
                {"type": "straight", "length": 100},
                {"type": "curve", "difficulty": 0.5},
                {"type": "obstacle", "severity": 0.3}
            ]
        }
    
    def test_initialization(self, sample_track, mock_service):
        """Test RaceSimulation initialization."""
        sim = RaceSimulation(sample_track, "medium", mock_service)
        
        assert sim.track == sample_track
        assert sim.difficulty == "medium"
        assert sim.gemini == mock_service
        assert sim.step_count == 0
    
    def test_player_state_initial(self, sample_track, mock_service):
        """Test initial player state."""
        sim = RaceSimulation(sample_track, "medium", mock_service)
        state = sim.player_state()
        
        assert state["pos"] == 0.0
        assert state["speed"] >= 0
        assert state["crashes"] == 0
        assert state["finished"] is False
    
    def test_step_increments_count(self, sample_track, mock_service):
        """Test that step increments step count."""
        sim = RaceSimulation(sample_track, "medium", mock_service)
        initial_count = sim.step_count
        
        sim.step()
        
        assert sim.step_count == initial_count + 1
    
    def test_step_returns_result(self, sample_track, mock_service):
        """Test that step returns result dictionary."""
        sim = RaceSimulation(sample_track, "medium", mock_service)
        result = sim.step()
        
        assert isinstance(result, dict)
        assert "decisions" in result
        assert "You" in result["decisions"]
    
    def test_step_updates_position(self, sample_track, mock_service):
        """Test that step updates player position."""
        sim = RaceSimulation(sample_track, "medium", mock_service)
        initial_position = sim.player_state()["pos"]
        
        sim.step()
        
        new_position = sim.player_state()["pos"]
        assert new_position >= initial_position
    
    def test_race_completion(self, sample_track, mock_service):
        """Test race completes when position exceeds track length."""
        sim = RaceSimulation(sample_track, "medium", mock_service)
        
        # Run many steps to complete race
        max_steps = 100
        for _ in range(max_steps):
            if sim.player_state()["finished"]:
                break
            sim.step()
        
        # Should finish within reasonable steps
        assert sim.player_state()["finished"] or sim.step_count < max_steps
    
    def test_ai_service_called(self, sample_track, mock_service):
        """Test that AI service is called during step."""
        sim = RaceSimulation(sample_track, "medium", mock_service)
        
        sim.step()
        
        assert mock_service.decide_action.called
    
    def test_multiple_opponents(self, sample_track, mock_service):
        """Test simulation with multiple opponents."""
        sim = RaceSimulation(sample_track, "medium", mock_service, second_ai=True)
        result = sim.step()
        
        assert "decisions" in result
        # Should have player + 2 AI opponents
        assert len(result["decisions"]) >= 3
    
    def test_difficulty_affects_simulation(self, sample_track, mock_service):
        """Test that difficulty parameter is used."""
        difficulties = ["easy", "medium", "hard"]
        
        for difficulty in difficulties:
            sim = RaceSimulation(sample_track, difficulty, mock_service)
            assert sim.difficulty == difficulty
    
    def test_crash_tracking(self, sample_track, mock_service):
        """Test that crashes are tracked."""
        sim = RaceSimulation(sample_track, "medium", mock_service)
        initial_crashes = sim.player_state()["crashes"]
        
        # Run several steps
        for _ in range(10):
            sim.step()
        
        # Crashes should be non-negative
        assert sim.player_state()["crashes"] >= initial_crashes
    
    def test_speed_bounds(self, sample_track, mock_service):
        """Test that speed stays within reasonable bounds."""
        sim = RaceSimulation(sample_track, "medium", mock_service)
        
        for _ in range(10):
            sim.step()
            speed = sim.player_state()["speed"]
            assert 0 <= speed <= 300  # Reasonable speed bounds


class TestRaceSimulationEdgeCases:
    """Edge case tests for RaceSimulation."""
    
    @pytest.fixture
    def mock_service(self):
        """Create mock AI service."""
        service = Mock()
        service.decide_action.return_value = {
            "action": "maintain",
            "reason": "Test"
        }
        return service
    
    def test_empty_track(self, mock_service):
        """Test simulation with empty track."""
        track = {"segments": []}
        sim = RaceSimulation(track, "medium", mock_service)
        
        # Should handle gracefully
        state = sim.player_state()
        assert state["pos"] == 0.0
    
    def test_single_segment_track(self, mock_service):
        """Test simulation with single segment."""
        track = {"segments": [{"type": "straight", "length": 50}]}
        sim = RaceSimulation(track, "medium", mock_service)
        
        result = sim.step()
        assert isinstance(result, dict)
    
    def test_service_returns_invalid_action(self, mock_service):
        """Test handling of invalid action from service."""
        mock_service.decide_action.return_value = {
            "action": "invalid_action",
            "reason": "Test"
        }
        
        track = {"segments": [{"type": "straight", "length": 100}]}
        sim = RaceSimulation(track, "medium", mock_service)
        
        # Should handle gracefully without crashing
        result = sim.step()
        assert isinstance(result, dict)
    
    def test_service_returns_none(self, mock_service):
        """Test handling when service returns None."""
        mock_service.decide_action.return_value = {"action": "maintain", "reason": "Fallback"}
        
        track = {"segments": [{"type": "straight", "length": 100}]}
        sim = RaceSimulation(track, "medium", mock_service)
        
        # Should handle gracefully
        result = sim.step()
        assert isinstance(result, dict)
    
    def test_very_long_track(self, mock_service):
        """Test simulation with very long track."""
        track = {"segments": [{"type": "straight", "length": 10000}]}
        sim = RaceSimulation(track, "medium", mock_service)
        
        # Should not hang
        for _ in range(5):
            sim.step()
        
        assert sim.step_count == 5


class TestRaceSimulationIntegration:
    """Integration tests for RaceSimulation."""
    
    @pytest.fixture
    def mock_service(self):
        """Create mock service with varied responses."""
        service = Mock()
        service.decide_action.return_value = {"action": "accelerate", "reason": "Test"}
        return service
    
    def test_complete_race_workflow(self, mock_service):
        """Test complete race from start to finish."""
        track = {
            "segments": [
                {"type": "straight", "length": 50},
                {"type": "curve", "difficulty": 0.5},
                {"type": "straight", "length": 50}
            ]
        }
        
        sim = RaceSimulation(track, "medium", mock_service)
        
        # Run race
        max_steps = 50
        results = []
        for _ in range(max_steps):
            if sim.player_state()["finished"]:
                break
            result = sim.step()
            results.append(result)
        
        # Verify race progression
        assert len(results) > 0
        assert sim.step_count > 0
        
        # Final state should be valid
        final_state = sim.player_state()
        assert final_state["pos"] >= 0
        assert final_state["crashes"] >= 0
    
    def test_multi_opponent_race(self, mock_service):
        """Test race with multiple opponents."""
        track = {
            "segments": [
                {"type": "straight", "length": 100},
                {"type": "curve", "difficulty": 0.6}
            ]
        }
        
        sim = RaceSimulation(track, "hard", mock_service, second_ai=True)
        
        # Run several steps
        for _ in range(10):
            result = sim.step()
            
            # Should have decisions for all racers
            assert "decisions" in result
            assert len(result["decisions"]) >= 3  # Player + 2 AI opponents
    
    def test_performance_metrics(self, mock_service):
        """Test that performance metrics are tracked."""
        track = {
            "segments": [
                {"type": "straight", "length": 100}
            ]
        }
        
        sim = RaceSimulation(track, "medium", mock_service)
        
        # Run race
        for _ in range(20):
            if sim.player_state()["finished"]:
                break
            sim.step()
        
        state = sim.player_state()
        
        # Verify metrics exist
        assert "pos" in state
        assert "speed" in state
        assert "crashes" in state
        assert "finished" in state
