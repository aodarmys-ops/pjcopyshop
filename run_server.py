from app import app, init_db, migrate_pins_to_hash
from waitress import serve
import webbrowser
import threading
import time
import os

def open_browser():
    time.sleep(1)
    webbrowser.open('http://127.0.0.1:5000')

if __name__ == '__main__':
    print("Initializing Database...")
    init_db()
    migrate_pins_to_hash()
    
    print("Starting production server on http://127.0.0.1:5000...")
    threading.Thread(target=open_browser).start()
    
    # Run production WSGI server
    serve(app, host='0.0.0.0', port=5000, threads=6)
