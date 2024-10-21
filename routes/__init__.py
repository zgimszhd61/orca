from flask import Flask
from .route_a import route_a


def register_routes(app: Flask):
    app.register_blueprint(route_a)