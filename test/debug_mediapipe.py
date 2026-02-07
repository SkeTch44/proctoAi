
import sys
import traceback

print(f"Python: {sys.version}")

try:
    import cv2
    print(f"✅ OpenCV imported! Version: {cv2.__version__}")
except ImportError:
    print("❌ OpenCV Import Failed")
except Exception as e:
    print(f"❌ OpenCV Error: {e}")

try:
    import mediapipe as mp
    print("✅ MediaPipe imported successfully!")
    print(f"Version: {mp.__version__}")
except Exception as e:
    print("❌ MediaPipe Import Failed (After CV2):")
    traceback.print_exc()
