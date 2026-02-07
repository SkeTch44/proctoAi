"""
Simplified test script for CheatDetector suspicion scoring system
Tests core logic without requiring cv2/mediapipe dependencies
"""
import sys
import os
import json

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


def test_scoring_formula():
    """Test the weighted scoring formula"""
    print("\n=== Testing Scoring Formula ===")
    
    # Import with mock dependencies
    from models.cheat_detector import CheatDetector
    
    detector = CheatDetector()
    
    # Test case 1: All zeros
    score = detector.calculate_suspicion_score(0, 0, 0, 0, 0, 0)
    print(f"All zeros: {score} (expected: 0)")
    assert score == 0, "All zeros should result in score 0"
    
    # Test case 2: Face absence only (weight 35%)
    score = detector.calculate_suspicion_score(0, 100, 0, 0, 0, 0)
    print(f"Face absence (100): {score} (expected: 35)")
    assert score == 35, "Face absence 100 should result in score 35"
    
    # Test case 3: Multiple faces only (weight 30%)
    score = detector.calculate_suspicion_score(0, 0, 100, 0, 0, 0)
    print(f"Multiple faces (100): {score} (expected: 30)")
    assert score == 30, "Multiple faces 100 should result in score 30"
    
    # Test case 4: Gaze only (weight 15%)
    score = detector.calculate_suspicion_score(100, 0, 0, 0, 0, 0)
    print(f"Gaze (100): {score} (expected: 15)")
    assert score == 15, "Gaze 100 should result in score 15"
    
    # Test case 5: Tab switch only (weight 10%)
    score = detector.calculate_suspicion_score(0, 0, 0, 0, 0, 100)
    print(f"Tab switch (100): {score} (expected: 10)")
    assert score == 10, "Tab switch 100 should result in score 10"
    
    # Test case 6: All max values
    score = detector.calculate_suspicion_score(100, 100, 100, 100, 100, 100)
    print(f"All max (100): {score} (expected: 100)")
    assert score == 100, "All max should result in score 100"
    
    # Test case 7: Mixed values
    score = detector.calculate_suspicion_score(50, 50, 50, 50, 50, 50)
    print(f"All 50: {score} (expected: 50)")
    assert score == 50, "All 50 should result in score 50"
    
    # Test case 8: Verify weights sum to 100%
    weights = detector.WEIGHTS
    total_weight = sum(weights.values())
    print(f"Total weight: {total_weight} (expected: 1.0)")
    assert abs(total_weight - 1.0) < 0.001, "Weights should sum to 1.0"
    
    print("✓ Scoring formula tests passed")


def test_threshold_classification():
    """Test threshold classification"""
    print("\n=== Testing Threshold Classification ===")
    
    from models.cheat_detector import CheatDetector
    detector = CheatDetector()
    
    # Test LOW threshold (1-30)
    assert detector._classify_severity(0) == 'LOW', "Score 0 should be LOW"
    assert detector._classify_severity(1) == 'LOW', "Score 1 should be LOW"
    assert detector._classify_severity(15) == 'LOW', "Score 15 should be LOW"
    assert detector._classify_severity(30) == 'LOW', "Score 30 should be LOW"
    print("✓ LOW threshold (1-30) correct")
    
    # Test MEDIUM threshold (31-70)
    assert detector._classify_severity(31) == 'MEDIUM', "Score 31 should be MEDIUM"
    assert detector._classify_severity(50) == 'MEDIUM', "Score 50 should be MEDIUM"
    assert detector._classify_severity(70) == 'MEDIUM', "Score 70 should be MEDIUM"
    print("✓ MEDIUM threshold (31-70) correct")
    
    # Test HIGH threshold (71-100)
    assert detector._classify_severity(71) == 'HIGH', "Score 71 should be HIGH"
    assert detector._classify_severity(85) == 'HIGH', "Score 85 should be HIGH"
    assert detector._classify_severity(100) == 'HIGH', "Score 100 should be HIGH"
    print("✓ HIGH threshold (71-100) correct")
    
    print("✓ Threshold classification tests passed")


def test_alert_type_determination():
    """Test alert type determination"""
    print("\n=== Testing Alert Type Determination ===")
    
    from models.cheat_detector import CheatDetector
    detector = CheatDetector()
    
    # Test highest score wins
    alert_type = detector._determine_alert_type(10, 100, 0, 5)
    assert alert_type == 'FACE_ABSENCE', "Highest score should determine alert type"
    print(f"✓ Alert type for (10, 100, 0, 5): {alert_type}")
    
    alert_type = detector._determine_alert_type(5, 0, 100, 0)
    assert alert_type == 'MULTIPLE_FACES', "Multiple faces should be detected"
    print(f"✓ Alert type for (5, 0, 100, 0): {alert_type}")
    
    alert_type = detector._determine_alert_type(100, 0, 0, 0)
    assert alert_type == 'GAZE_DEVIATION', "Gaze deviation should be detected"
    print(f"✓ Alert type for (100, 0, 0, 0): {alert_type}")
    
    alert_type = detector._determine_alert_type(0, 0, 0, 0)
    assert alert_type == 'NONE', "No anomaly should return NONE"
    print(f"✓ Alert type for (0, 0, 0, 0): {alert_type}")
    
    print("✓ Alert type determination tests passed")


def test_alert_logging():
    """Test JSON alert logging"""
    print("\n=== Testing Alert Logging ===")
    
    from models.cheat_detector import CheatDetector
    
    # Clean up existing log
    log_file = 'suspicion_log.json'
    if os.path.exists(log_file):
        os.remove(log_file)
    
    detector = CheatDetector()
    
    # Create test result
    test_result = {
        'alert_type': 'MULTIPLE_FACES',
        'severity': 'HIGH',
        'suspicion_score': 75,
        'details': {
            'gaze_deviation': 10,
            'face_absence': 0,
            'multiple_faces': 100,
            'emotion_anomaly': 5
        }
    }
    
    # Log alert
    detector.log_alert('test_session_123', test_result)
    
    # Verify log file exists
    assert os.path.exists(log_file), "Log file should be created"
    
    # Read and verify contents
    with open(log_file, 'r') as f:
        logs = json.load(f)
    
    assert len(logs) == 1, "Should have 1 log entry"
    assert logs[0]['session_id'] == 'test_session_123', "Session ID should match"
    assert logs[0]['alert_type'] == 'MULTIPLE_FACES', "Alert type should match"
    assert logs[0]['severity'] == 'HIGH', "Severity should match"
    assert logs[0]['score_impact'] == 75, "Score impact should match"
    assert 'timestamp' in logs[0], "Should have timestamp"
    
    print(f"✓ Alert logged successfully")
    print(f"  Session: {logs[0]['session_id']}")
    print(f"  Type: {logs[0]['alert_type']}")
    print(f"  Severity: {logs[0]['severity']}")
    print(f"  Score: {logs[0]['score_impact']}")
    
    # Test appending
    test_result2 = {
        'alert_type': 'FACE_ABSENCE',
        'severity': 'MEDIUM',
        'suspicion_score': 50,
        'details': {}
    }
    
    detector.log_alert('test_session_456', test_result2)
    
    with open(log_file, 'r') as f:
        logs = json.load(f)
    
    assert len(logs) == 2, "Should have 2 log entries"
    print("✓ Alert appending works correctly")
    
    # Clean up
    os.remove(log_file)
    print("✓ Alert logging tests passed")


def test_config():
    """Test configuration"""
    print("\n=== Testing Configuration ===")
    
    from models.cheat_detector import CheatDetector
    
    # Test default config
    detector = CheatDetector()
    assert detector.config['face_confidence_threshold'] == 0.8
    assert detector.config['log_file'] == 'suspicion_log.json'
    print("✓ Default config loaded correctly")
    
    # Test custom config
    custom_config = {
        'log_file': 'custom_log.json',
        'face_confidence_threshold': 0.9
    }
    detector2 = CheatDetector(custom_config)
    assert detector2.log_file == 'custom_log.json'
    assert detector2.config['face_confidence_threshold'] == 0.9
    print("✓ Custom config applied correctly")
    
    print("✓ Configuration tests passed")


def main():
    """Run all tests"""
    print("=" * 60)
    print("CheatDetector Suspicion Scoring System - Test Suite")
    print("=" * 60)
    
    try:
        test_scoring_formula()
        test_threshold_classification()
        test_alert_type_determination()
        test_alert_logging()
        test_config()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        print("\nSummary:")
        print("  - Weighted scoring formula: VERIFIED")
        print("  - Threshold classification: VERIFIED")
        print("  - Alert type determination: VERIFIED")
        print("  - JSON logging: VERIFIED")
        print("  - Configuration: VERIFIED")
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
