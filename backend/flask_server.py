#!/usr/bin/env python3
"""
Flask server that hosts ALL agent API endpoints.
Run this instead of individual agent files to enable frontend connections.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os

# Import ALL agent blueprints
from manager_agent import manager_api_bp
from secretary_agent import secretary_api_bp
from secretary_tools import secretary_tools_api_bp
from scheduler_agent import scheduler_api_bp
from therapist_agent import therapist_api_bp
from scheduler_tools import scheduler_tools_api_bp, scheduler_oauth_bp

def create_app():
    app = Flask(__name__)
    CORS(app)  # Enable CORS for frontend connections
    
    # Register ALL agent API blueprints
    blueprints = [
        (manager_api_bp, "Manager API"),
        (secretary_api_bp, "Secretary API"), 
        (scheduler_api_bp, "Scheduler API"),
        (therapist_api_bp, "Therapist API"),
        (scheduler_tools_api_bp, "Scheduler Tools API"),
        (secretary_tools_api_bp, "Secretary Tools API"),
        (scheduler_oauth_bp, "OAuth API")
    ]
    
    for bp, name in blueprints:
        if bp:
            app.register_blueprint(bp)
            print(f"✅ Registered {name}")
        else:
            print(f"❌ Failed to import {name}")
    
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({"status": "ok", "message": "Flask server running with all agents"})

    @app.route("/debug/bedrock")
    def debug_bedrock():
        return {
            "AWS_REGION": os.getenv("AWS_REGION"),
            "BEDROCK_MODEL_SCHEDULER": os.getenv("BEDROCK_MODEL_SCHEDULER"),
            "BEDROCK_MODEL_ID": os.getenv("BEDROCK_MODEL_ID"),
            "BEDROCK_MODEL_SECRETARY": os.getenv("BEDROCK_MODEL_SECRETARY"),
            "HAS_BEARER": bool(os.getenv("AWS_BEARER_TOKEN_BEDROCK")),
        }

    @app.route("/debug/scheduler")
    def debug_scheduler():
        try:
            from scheduler_agent import get_agent, MODEL_ID_SCHEDULER, AWS_REGION
            agent = get_agent()
            model_id = getattr(agent.model, "model_id", None)
            return {
                "AWS_REGION": AWS_REGION,
                "MODEL_ID_SCHEDULER(from_env)": MODEL_ID_SCHEDULER,
                "MODEL_ID_SCHEDULER(from_agent)": model_id,
                "HAS_BEARER": bool(os.getenv("AWS_BEARER_TOKEN_BEDROCK")),
            }
        except Exception as e:
            return {"error": str(e)}

    @app.route("/debug/endpoints")
    def debug_endpoints():
        """List all registered endpoints for debugging"""
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append({
                "endpoint": rule.endpoint,
                "methods": list(rule.methods),
                "rule": str(rule)
            })
        return {"routes": routes}
    
    return app

if __name__ == '__main__':
    app = create_app()
    print("🚀 Starting unified Flask server with all agents...")
    print("📍 Available at: http://localhost:8081")
    print("🔍 Debug endpoints at: http://localhost:8081/debug/endpoints")
    
    # Run on port 8081 to avoid conflict with OAuth server on 8080
    app.run(host='localhost', port=8081, debug=True)