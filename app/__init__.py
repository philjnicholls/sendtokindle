from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask import Blueprint

from app.config import Config
from app.extensions import csrf

app = Flask(__name__)
app.config.from_object(Config)
app.config['SECRET_KEY'] = b'_5#y2L"F4Q8z\n\xec]/'
csrf.init_app(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
CORS(app)
errors = Blueprint('errors', __name__)

from app import routes, models