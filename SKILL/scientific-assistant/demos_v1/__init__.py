"""
demos_v1/__init__.py - Package initialization, Flask app creation, route registration
"""
import os
import sys
import warnings
from flask import Flask

# Create Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB 제한


def create_app():
    """Create and configure the Flask app with all routes registered."""
    from demos_v1.routes_api import register_api_routes
    from demos_v1.routes_chat import register_chat_routes
    from demos_v1.logpresso import register_logpresso_routes
    from demos_v1.knowledge import register_knowledge_routes
    
    register_api_routes(app)
    register_chat_routes(app)
    register_logpresso_routes(app)
    register_knowledge_routes(app)
    
    return app
