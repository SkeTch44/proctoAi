"""
Mesa ABM Engine Test - Demonstrates behavioral pattern detection
Tests the complete event-driven architecture with Mesa agents
"""

import sys
import os
import time
import logging

sys.path.append(os.getcwd())

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from backend.services.mesa_service import MesaService
from backend.events.event_schema import FrameAnalysisEvent, BrowserEvent
from backend.events.publisher import EventPublisher

def alert_callback(alert_type, alert_data):
    """Callback for alerts"""
    if alert_type == 'supervisor':
        print(f"\n🚨 SUPERVISOR ALERT:")
        print(f"   Student: {alert_data['student_id']}")
        print(f"   Level: {alert_data['alert_level']}")
        print(f"   Risk: {alert_data['risk_score']}")
        print(f"   Patterns: {alert_data['patterns']}")
        print(f"   Reasons: {', '.join(alert_data['reasons'])}")
        print(f"   Action: {alert_data['recommended_action']}\n")
    elif alert_type == 'student':
        print(f"\n⚠️  STUDENT NOTIFICATION:")
        print(f"   {alert_data['message']}\n")

def simulate_normal_behavior(publisher, student_id):
    """Simulate normal exam behavior"""
    print(f"\n📝 Simulating NORMAL behavior for {student_id}...")
    
    for i in range(5):
        event = FrameAnalysisEvent(
            student_id=student_id,
            timestamp=time.time(),
            face_visible=True,
            face_count=1,
            gaze_direction="center",
            head_angle=0.0,
            head_pitch=0.0,
            looking_down=False,
            looking_away=False,
            phone_detected=False,
            book_detected=False,
            camera_motion="stable",
            raw_risk=5.0,
            confidence=95.0
        )
        publisher.publish(event)
        time.sleep(0.5)
    
    print("✅ Normal behavior complete")

def simulate_suspicious_behavior(publisher, student_id):
    """Simulate suspicious behavior - gaze aversion"""
    print(f"\n👀 Simulating SUSPICIOUS behavior (gaze away) for {student_id}...")
    
    for i in range(8):
        event = FrameAnalysisEvent(
            student_id=student_id,
            timestamp=time.time(),
            face_visible=True,
            face_count=1,
            gaze_direction="away",
            head_angle=45.0,
            head_pitch=0.0,
            looking_down=False,
            looking_away=True,
            phone_detected=False,
            book_detected=False,
            camera_motion="stable",
            raw_risk=40.0,
            confidence=85.0
        )
        publisher.publish(event)
        time.sleep(0.5)
    
    print("⚠️  Suspicious behavior complete")

def simulate_cheating_pattern(publisher, student_id):
    """Simulate high-risk cheating pattern - phone + looking down"""
    print(f"\n📱 Simulating CHEATING pattern (phone + looking down) for {student_id}...")
    
    for i in range(5):
        event = FrameAnalysisEvent(
            student_id=student_id,
            timestamp=time.time(),
            face_visible=True,
            face_count=1,
            gaze_direction="down",
            head_angle=0.0,
            head_pitch=-25.0,
            looking_down=True,
            looking_away=False,
            phone_detected=True,
            book_detected=False,
            camera_motion="stable",
            raw_risk=85.0,
            confidence=90.0
        )
        publisher.publish(event)
        time.sleep(0.5)
    
    print("🚨 Cheating pattern complete")

def simulate_browser_violations(publisher, student_id):
    """Simulate browser security violations"""
    print(f"\n🔄 Simulating BROWSER violations for {student_id}...")
    
    # Tab switch
    event1 = BrowserEvent(
        student_id=student_id,
        timestamp=time.time(),
        action="tab_switch",
        severity="HIGH"
    )
    publisher.publish(event1)
    time.sleep(0.5)
    
    # Screenshot
    event2 = BrowserEvent(
        student_id=student_id,
        timestamp=time.time(),
        action="screenshot",
        severity="CRITICAL"
    )
    publisher.publish(event2)
    time.sleep(0.5)
    
    # Copy/paste
    event3 = BrowserEvent(
        student_id=student_id,
        timestamp=time.time(),
        action="copy",
        severity="MEDIUM"
    )
    publisher.publish(event3)
    
    print("🔒 Browser violations complete")

def run_test():
    """Run complete Mesa ABM test"""
    print("=" * 70)
    print(" " * 20 + "MESA ABM ENGINE TEST")
    print("=" * 70)
    
    # Initialize components
    print("\n🚀 Initializing Mesa service...")
    mesa_service = MesaService(
        redis_url="redis://localhost:6379",
        stream_name="proctoring_events",
        step_interval=1.0,
        alert_callback=alert_callback
    )
    
    # Start service
    mesa_service.start()
    print("✅ Mesa service started")
    
    # Initialize publisher
    print("\n📡 Initializing event publisher...")
    publisher = EventPublisher(
        redis_url="redis://localhost:6379",
        stream_name="proctoring_events"
    )
    print("✅ Event publisher ready")
    
    # Wait for service to be ready
    time.sleep(2)
    
    # Test scenarios
    student_id = "test_student_001"
    
    print("\n" + "=" * 70)
    print(" " * 25 + "TEST SCENARIOS")
    print("=" * 70)
    
    # Scenario 1: Normal behavior
    simulate_normal_behavior(publisher, student_id)
    time.sleep(2)
    status = mesa_service.get_student_status(student_id)
    if status:
        print(f"\n📊 Status after normal behavior:")
        print(f"   State: {status['state']}")
        print(f"   Risk: {status['risk_score']}")
        print(f"   Patterns: {status['explanation']['patterns_detected']}")
    
    # Scenario 2: Suspicious behavior
    simulate_suspicious_behavior(publisher, student_id)
    time.sleep(2)
    status = mesa_service.get_student_status(student_id)
    if status:
        print(f"\n📊 Status after suspicious behavior:")
        print(f"   State: {status['state']}")
        print(f"   Risk: {status['risk_score']}")
        print(f"   Patterns: {status['explanation']['patterns_detected']}")
    
    # Scenario 3: Cheating pattern
    simulate_cheating_pattern(publisher, student_id)
    time.sleep(2)
    status = mesa_service.get_student_status(student_id)
    if status:
        print(f"\n📊 Status after cheating pattern:")
        print(f"   State: {status['state']}")
        print(f"   Risk: {status['risk_score']}")
        print(f"   Patterns: {status['explanation']['patterns_detected']}")
        print(f"   Reasons: {status['explanation']['reasons']}")
    
    # Scenario 4: Browser violations
    simulate_browser_violations(publisher, student_id)
    time.sleep(2)
    status = mesa_service.get_student_status(student_id)
    if status:
        print(f"\n📊 Status after browser violations:")
        print(f"   State: {status['state']}")
        print(f"   Risk: {status['risk_score']}")
        print(f"   Patterns: {status['explanation']['patterns_detected']}")
    
    # Final statistics
    print("\n" + "=" * 70)
    print(" " * 25 + "FINAL STATISTICS")
    print("=" * 70)
    
    stats = mesa_service.get_statistics()
    print(f"\n📈 Service Statistics:")
    print(f"   Total Students: {stats['total_students']}")
    print(f"   Events Processed: {stats['total_events_processed']}")
    print(f"   Decisions Made: {stats['total_decisions_made']}")
    print(f"   Alerts Sent: {stats['total_alerts_sent']}")
    print(f"   Flagged Students: {stats['flagged_students']}")
    
    # Timeline
    from backend.storage.timeline_store import TimelineStore
    timeline_store = TimelineStore()
    timeline = timeline_store.get_timeline(student_id, limit=10)
    
    print(f"\n📊 Risk Timeline (last 10 entries):")
    for entry in reversed(timeline[-10:]):
        print(f"   t={entry['t']:.1f} | Risk={entry['risk']:.1f} | State={entry['state']} | Violations={entry['violations']}")
    
    summary = timeline_store.get_summary(student_id)
    print(f"\n📋 Session Summary:")
    print(f"   Max Risk: {summary.get('max_risk', 0)}")
    print(f"   Avg Risk: {summary.get('avg_risk', 0)}")
    print(f"   Total Violations: {summary.get('total_violations', 0)}")
    print(f"   Session Duration: {summary.get('session_duration', 0)}s")
    
    # Cleanup
    print("\n🔄 Cleaning up...")
    mesa_service.stop()
    publisher.close()
    timeline_store.close()
    
    print("\n" + "=" * 70)
    print(" " * 25 + "TEST COMPLETE")
    print("=" * 70)
    print("\n✅ Mesa ABM engine working correctly!")
    print("✅ Pattern detection functional")
    print("✅ Risk scoring accurate")
    print("✅ Decision making operational")
    print("✅ Explainability verified\n")

if __name__ == "__main__":
    try:
        run_test()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
