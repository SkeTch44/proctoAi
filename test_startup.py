
try:
    print("Importing app...")
    from backend.app import app, socketio
    print("App imported successfully.")
    print("Mesa service status:", app.config.get('MESA_ENABLED', 'Not explicitly set'))
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
