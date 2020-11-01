import logging
import sys
import os

from app.config import BASE_DIR

logging.basicConfig(stream=sys.stderr)
sys.stdout = sys.stderr

sys.path.insert(0, BASE_DIR)
from app import app as application
application.secret_key = 'gs&&6nu$^hy-uowy*$0s3an%fxr21g2t41ofle!6i97hxx#7ji'
