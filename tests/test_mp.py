import sys
try:
    import mediapipe as mp
    print(f"MediaPipe path: {mp.__file__}")
    print(f"Dir(mp): {dir(mp)}")
    
    try:
        print(f"Solutions: {mp.solutions}")
        print("Standard import successful")
    except AttributeError:
        print("AttributeError: mp.solutions missing")
        try:
            import mediapipe.python.solutions as solutions
            mp.solutions = solutions
            print("Fixed via mediapipe.python.solutions import")
            print(f"Solutions now: {mp.solutions}")
        except ImportError as e:
            print(f"Fallback import failed: {e}")

except ImportError as e:
    print(f"ImportError: {e}")
