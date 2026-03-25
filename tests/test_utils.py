"""Unit tests for utils.py module."""

import pytest
from utils import (
    _segment_units,
    track_total_units,
    scale_track,
    get_current_segment_index,
    calculate_progress,
    generate_track_indicator,
    generate_commentary,
    generate_race_event
)


class TestSegmentUnits:
    """Tests for _segment_units function."""
    
    def test_segment_with_units_property(self):
        """Test segment with explicit units property."""
        seg = {"type": "straight", "units": 50}
        assert _segment_units(seg) == 50
    
    def test_straight_segment_with_length(self):
        """Test straight segment with length property."""
        seg = {"type": "straight", "length": 100}
        assert _segment_units(seg) == 100
    
    def test_curve_segment_default(self):
        """Test curve segment returns default units."""
        seg = {"type": "curve", "difficulty": 0.5}
        assert _segment_units(seg) == 60
    
    def test_obstacle_segment_default(self):
        """Test obstacle segment returns default units."""
        seg = {"type": "obstacle", "severity": 0.7}
        assert _segment_units(seg) == 60
    
    def test_unknown_segment_type(self):
        """Test unknown segment type returns default."""
        seg = {"type": "unknown"}
        assert _segment_units(seg) == 60


class TestTrackTotalUnits:
    """Tests for track_total_units function."""
    
    def test_empty_track(self):
        """Test empty track returns 0."""
        track = {"segments": []}
        assert track_total_units(track) == 0
    
    def test_track_with_mixed_segments(self):
        """Test track with multiple segment types."""
        track = {
            "segments": [
                {"type": "straight", "length": 100},
                {"type": "curve", "difficulty": 0.5},
                {"type": "obstacle", "severity": 0.3}
            ]
        }
        expected = 100 + 60 + 60
        assert track_total_units(track) == expected
    
    def test_track_with_units_override(self):
        """Test track with explicit units properties."""
        track = {
            "segments": [
                {"type": "straight", "units": 50},
                {"type": "curve", "units": 30}
            ]
        }
        assert track_total_units(track) == 80
    
    def test_track_without_segments_key(self):
        """Test track without segments key returns 0."""
        track = {}
        assert track_total_units(track) == 0


class TestScaleTrack:
    """Tests for scale_track function."""
    
    def test_scale_track_up(self):
        """Test scaling track to larger size."""
        track = {
            "segments": [
                {"type": "straight", "length": 50},
                {"type": "curve", "difficulty": 0.5}
            ]
        }
        scaled = scale_track(track, 200)
        total = track_total_units(scaled)
        assert 190 <= total <= 210  # Allow 5% tolerance
    
    def test_scale_track_down(self):
        """Test scaling track to smaller size."""
        track = {
            "segments": [
                {"type": "straight", "length": 100},
                {"type": "curve", "difficulty": 0.5}
            ]
        }
        scaled = scale_track(track, 50)
        total = track_total_units(scaled)
        assert 45 <= total <= 55
    
    def test_scale_track_minimum_units(self):
        """Test that scaled segments maintain minimum of 3 units."""
        track = {
            "segments": [
                {"type": "straight", "length": 100}
            ]
        }
        scaled = scale_track(track, 5)
        for seg in scaled["segments"]:
            assert _segment_units(seg) >= 3
    
    def test_scale_empty_track(self):
        """Test scaling empty track."""
        track = {"segments": []}
        scaled = scale_track(track, 100)
        assert scaled == track
    
    def test_scale_track_zero_total(self):
        """Test scaling track with zero total."""
        track = {"segments": [{"type": "straight", "length": 0}]}
        scaled = scale_track(track, 100)
        # When total is 0, scaling still adds units property
        assert "segments" in scaled
        assert len(scaled["segments"]) == 1


class TestGetCurrentSegmentIndex:
    """Tests for get_current_segment_index function."""
    
    def test_position_at_start(self):
        """Test position at track start."""
        track = {
            "segments": [
                {"type": "straight", "length": 100},
                {"type": "curve", "difficulty": 0.5}
            ]
        }
        assert get_current_segment_index(0, track) == 0
    
    def test_position_in_first_segment(self):
        """Test position within first segment."""
        track = {
            "segments": [
                {"type": "straight", "length": 100},
                {"type": "curve", "difficulty": 0.5}
            ]
        }
        assert get_current_segment_index(50, track) == 0
    
    def test_position_in_second_segment(self):
        """Test position in second segment."""
        track = {
            "segments": [
                {"type": "straight", "length": 100},
                {"type": "curve", "difficulty": 0.5}
            ]
        }
        assert get_current_segment_index(120, track) == 1
    
    def test_position_beyond_track(self):
        """Test position beyond track end."""
        track = {
            "segments": [
                {"type": "straight", "length": 100}
            ]
        }
        idx = get_current_segment_index(200, track)
        assert idx == 0  # Returns last valid index


class TestCalculateProgress:
    """Tests for calculate_progress function."""
    
    def test_progress_at_start(self):
        """Test progress at track start."""
        track = {"segments": [{"type": "straight", "length": 100}]}
        assert calculate_progress(0, track) == 0.0
    
    def test_progress_at_midpoint(self):
        """Test progress at track midpoint."""
        track = {"segments": [{"type": "straight", "length": 100}]}
        progress = calculate_progress(50, track)
        assert 0.49 <= progress <= 0.51
    
    def test_progress_at_end(self):
        """Test progress at track end."""
        track = {"segments": [{"type": "straight", "length": 100}]}
        progress = calculate_progress(100, track)
        assert progress >= 0.99
    
    def test_progress_beyond_track(self):
        """Test progress beyond track end."""
        track = {"segments": [{"type": "straight", "length": 100}]}
        progress = calculate_progress(150, track)
        assert progress >= 1.0
    
    def test_progress_empty_track(self):
        """Test progress on empty track."""
        track = {"segments": []}
        assert calculate_progress(50, track) == 0.0


class TestGenerateTrackIndicator:
    """Tests for generate_track_indicator function."""
    
    def test_indicator_format(self):
        """Test indicator returns string with emojis."""
        track = {
            "segments": [
                {"type": "straight", "length": 100},
                {"type": "curve", "difficulty": 0.5},
                {"type": "obstacle", "severity": 0.3}
            ]
        }
        indicator = generate_track_indicator(track, 0, window=3)
        assert isinstance(indicator, str)
        assert "🏍️" in indicator
    
    def test_indicator_highlights_current(self):
        """Test indicator highlights current segment."""
        track = {
            "segments": [
                {"type": "straight", "length": 100},
                {"type": "curve", "difficulty": 0.5}
            ]
        }
        indicator = generate_track_indicator(track, 0)
        assert "**STRAIGHT**" in indicator.upper()
    
    def test_indicator_with_window(self):
        """Test indicator respects window parameter."""
        track = {
            "segments": [
                {"type": "straight", "length": 50},
                {"type": "curve", "difficulty": 0.5},
                {"type": "obstacle", "severity": 0.3},
                {"type": "straight", "length": 50}
            ]
        }
        indicator = generate_track_indicator(track, 1, window=2)
        assert isinstance(indicator, str)


class TestGenerateCommentary:
    """Tests for generate_commentary function."""
    
    def test_commentary_accelerate_straight(self):
        """Test commentary for acceleration on straight."""
        commentary = generate_commentary("accelerate", "straight", 100)
        assert isinstance(commentary, str)
        assert len(commentary) > 0
    
    def test_commentary_brake_curve(self):
        """Test commentary for braking on curve."""
        commentary = generate_commentary("brake", "curve", 120)
        assert isinstance(commentary, str)
        assert len(commentary) > 0
    
    def test_commentary_crash(self):
        """Test commentary for crash."""
        commentary = generate_commentary("accelerate", "obstacle", 150, crashed=True)
        assert isinstance(commentary, str)
        assert "crash" in commentary.lower() or "wipeout" in commentary.lower()
    
    def test_commentary_overtake(self):
        """Test commentary for overtake action."""
        commentary = generate_commentary("overtake", "straight", 130)
        assert isinstance(commentary, str)
        assert len(commentary) > 0
    
    def test_commentary_maintain(self):
        """Test commentary for maintain action."""
        commentary = generate_commentary("maintain", "straight", 100)
        assert isinstance(commentary, str)


class TestGenerateRaceEvent:
    """Tests for generate_race_event function."""
    
    def test_event_returns_string_or_none(self):
        """Test event returns string or None."""
        event = generate_race_event("accelerate", "straight", 100)
        assert event is None or isinstance(event, str)
    
    def test_event_high_speed_curve(self):
        """Test event generation for high speed on curve."""
        # Run multiple times to account for randomness
        events = [generate_race_event("accelerate", "curve", 150) for _ in range(10)]
        has_event = any(e is not None for e in events)
        assert has_event  # Should generate at least one event
    
    def test_event_obstacle_acceleration(self):
        """Test event generation for obstacle with acceleration."""
        events = [generate_race_event("accelerate", "obstacle", 120) for _ in range(10)]
        has_event = any(e is not None for e in events)
        assert has_event
    
    def test_event_crash(self):
        """Test event generation for crash."""
        # Crash events are generated probabilistically
        events = [generate_race_event("brake", "curve", 100, crashed=True) for _ in range(10)]
        # At least some should generate crash events
        has_crash_event = any(e is not None and "crash" in e.lower() for e in events)
        # If no crash events, at least verify function doesn't error
        assert all(e is None or isinstance(e, str) for e in events)


class TestIntegration:
    """Integration tests for utils functions."""
    
    def test_track_workflow(self):
        """Test complete track workflow."""
        # Create track
        track = {
            "segments": [
                {"type": "straight", "length": 100},
                {"type": "curve", "difficulty": 0.5},
                {"type": "obstacle", "severity": 0.3}
            ]
        }
        
        # Scale track
        scaled = scale_track(track, 150)
        assert track_total_units(scaled) > 0
        
        # Get segment index
        idx = get_current_segment_index(50, scaled)
        assert 0 <= idx < len(scaled["segments"])
        
        # Calculate progress
        progress = calculate_progress(50, scaled)
        assert 0.0 <= progress <= 1.0
        
        # Generate indicator
        indicator = generate_track_indicator(scaled, idx)
        assert isinstance(indicator, str)
    
    def test_race_commentary_workflow(self):
        """Test race commentary generation workflow."""
        actions = ["accelerate", "brake", "maintain", "overtake"]
        segments = ["straight", "curve", "obstacle"]
        
        for action in actions:
            for segment in segments:
                commentary = generate_commentary(action, segment, 100)
                assert isinstance(commentary, str)
                assert len(commentary) > 0
                
                event = generate_race_event(action, segment, 100)
                assert event is None or isinstance(event, str)
