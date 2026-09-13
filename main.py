import os
import sys

# Add backend directory to sys.path so imports like 'services' work seamlessly
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from backend.main import app  # noqa: F401
