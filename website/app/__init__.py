from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask import Blueprint

from app.config import Config
from app.extensions import csrf

from rq import Queue
from rq.job import Job
from worker import conn

from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)
app.config['SECRET_KEY'] = b'_5#y2L"F4Q8z\n\xec]/'

# Enable CSRF protection for forms
csrf.init_app(app)

# Database engine
db = SQLAlchemy(app)
migrate = Migrate(app, db)

q = Queue(connection=conn)

# Allow any domain to all the API
CORS(app)

# Used to catch errors and wrap with HTTP exceptions
errors = Blueprint('errors', __name__)

from app import routes, models
