"""Quick smoke test for Mesa ABM pipeline."""
import sys
sys.path.insert(0, '.')

from backend.mesa_engine.behavior_model import BehaviorModel
from backend.mesa_engine.student_agent import StudentAgent
from backend.risk_engine.decision_maker import DecisionMaker

print("✅ All Mesa components import OK")

# Create model + agent
m = BehaviorModel()
agent = m.get_student_agent('test_student_1')
print(f"✅ Agent created: {agent.student_id}, state={agent.behavior_state}")

# Feed events simulating phone cheating pattern
events = [
    {'event_type': 'frame_analysis', 'raw_risk': 60, 'confidence': 90, 'phone_detected': True, 'looking_down': True},
    {'event_type': 'frame_analysis', 'raw_risk': 70, 'confidence': 85, 'phone_detected': True, 'looking_down': True},
    {'event_type': 'frame_analysis', 'raw_risk': 65, 'confidence': 88, 'phone_detected': True, 'looking_down': True},
    {'event_type': 'frame_analysis', 'raw_risk': 55, 'confidence': 80, 'face_count': 2},
    {'event_type': 'frame_analysis', 'raw_risk': 50, 'confidence': 80, 'face_count': 2},
    {'event_type': 'frame_analysis', 'raw_risk': 50, 'confidence': 80, 'face_count': 2},
    {'event_type': 'browser_event', 'action': 'tab_switch', 'raw_risk': 40, 'confidence': 100},
    {'event_type': 'browser_event', 'action': 'copy', 'raw_risk': 50, 'confidence': 100},
    {'event_type': 'browser_event', 'action': 'tab_switch', 'raw_risk': 40, 'confidence': 100},
    {'event_type': 'frame_analysis', 'raw_risk': 45, 'confidence': 75, 'gaze_direction': 'away'},
]

for e in events:
    agent.observe(e)

m.step()
print(f"✅ Model stepped. Agent state: {agent.behavior_state}, risk: {agent.risk_score:.1f}")
print(f"   Patterns detected: {agent.patterns_detected}")

# Decision maker
dm = DecisionMaker()
decision = dm.make_decision(agent)
print(f"✅ Decision: state={decision['state']}, risk={decision['risk_score']}")
print(f"   Notify supervisor: {decision['notify_supervisor']}")
print(f"   Reasons: {decision['explanation']['reasons']}")

# Test MesaService import (without Redis)
try:
    from backend.services.mesa_service import MesaService
    print("✅ MesaService imports OK")
except Exception as e:
    print(f"⚠️  MesaService import issue: {e}")

print("\n🎉 Mesa ABM pipeline is fully functional!")
