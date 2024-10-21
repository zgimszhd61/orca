from flask import Blueprint

route_a = Blueprint('route_a', __name__)

@route_a.route('/a/bbb')
def hello():
    return 'helloabb'