from flask import Blueprint

hello_bp = Blueprint('hello', __name__)

@hello_bp.route('/hellobbb')
def hello():
    return 'hello worldssss'