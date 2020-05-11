from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask import Blueprint
from rq import Queue

from app.config import Config
from app.extensions import csrf
from worker import conn

app = Flask(__name__)
app.config.from_object(Config)
app.config['SECRET_KEY'] = b'_5#y2L"F4Q8z\n\xec]/'

# Enable CSRF protection for forms
csrf.init_app(app)

# Database engine
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Allow any domain to all the API
CORS(app)

# Used to catch errors and wrap with HTTP exceptions
errors = Blueprint('errors', __name__)

# Redis queue
q = Queue(connection=conn)

from app import routes, models
