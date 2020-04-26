import logging
import sys
logging.basicConfig(stream=sys.stderr)
sys.path.insert(0, '/home/pi/sendtokindle/')
from sendtokindle import app as application
application.secret_key = 'gs&&6nu$^hy-uowy*$0s3an%fxr21g2t41ofle!6i97hxx#7ji'