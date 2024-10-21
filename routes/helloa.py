from flask import Blueprint

helloa_bp = Blueprint('helloa', __name__)

@helloa_bp.route('/helloa')
def hello_a():
    return 'helloa'