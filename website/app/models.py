"""DB models."""

from uuid import uuid4

from app import db


class User(db.Model):
    """Credentials for users."""

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), index=True, unique=True)
    kindle_email = db.Column(db.String(120), index=True, unique=True)
    api_token = db.Column(db.String(36), unique=True, default=str(uuid4()))
    email_token = db.Column(db.String(36), unique=True, default=str(uuid4()))
    verified = db.Column(db.Boolean, default=False)

    def __repr__(self):
        """
        User friendly representation of object.

        :Returns: String representation of the object
        """
        return '<User {}>'.format(self.email)
