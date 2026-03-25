
import sys

def check_gpu():
    print(f"Python: {sys.version}")
    
    # Check PyTorch
    try:
        import torch
        print(f"\nPyTorch Version: {torch.__version__}")
        if torch.cuda.is_available():
            print(f"✅ PyTorch CUDA Available: Yes")
            print(f"   Device: {torch.cuda.get_device_name(0)}")
            print(f"   Count: {torch.cuda.device_count()}")
        else:
            print("❌ PyTorch CUDA Available: No")
    except ImportError:
        print("⚠️ PyTorch not installed")

    # Check TensorFlow (DeepFace backend)
    try:
        import tensorflow as tf
        print(f"\nTensorFlow Version: {tf.__version__}")
        gpus = tf.config.list_physical_devices('GPU')
        if gpus:
            print(f"✅ TensorFlow GPU Available: Yes")
            for gpu in gpus:
                print(f"   Device: {gpu}")
        else:
            print("❌ TensorFlow GPU Available: No")
    except ImportError:
        print("⚠️ TensorFlow not installed")

if __name__ == "__main__":
    check_gpu()
