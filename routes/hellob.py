from flask import Blueprint

hellob_bp = Blueprint('hellob', __name__)

@hellob_bp.route('/hellob')
def hello_b():
    return 'hellob'