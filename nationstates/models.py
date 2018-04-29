from flaskbb.extensions import db
from flaskbb.user.models import User


User.nation = db.Column(db.String, nullable=True)
