# app/app.py
import os
from . import create_app
from dotenv import load_dotenv

load_dotenv()  # load from .env if present

app = create_app()

if __name__ == "__main__":
    # dev server
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
