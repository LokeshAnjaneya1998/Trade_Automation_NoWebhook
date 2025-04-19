# auth_server.py

import logging
import webbrowser
from flask import Flask, request, abort

from src.fyers_integration import FyersIntegration
#from src.config_manager import ConfigManager

app = Flask(__name__)
fyers_integration = FyersIntegration()

@app.route("/capture_auth_code", methods=["GET"])
def capture_auth_code():
    """
    Fyers will redirect here after login with ?auth_code=...
    We'll automatically fetch the access_token and save it.
    """
    auth_code = request.args.get("auth_code")
    if not auth_code:
        return "Error: no 'auth_code' received from Fyers.", 400

    # Generate and store access_token in config.json
    fyers_integration.fetch_access_token(auth_code)
    return "Access token generated and saved. You can close this tab now."

@app.before_request
def block_unwanted_requests():
    # We only allow GET /capture_auth_code
    if request.method == "GET" and request.path == "/capture_auth_code":
        return
    # Otherwise, block
    abort(403)

def run_auth_server():
    """
    1) Generates the Fyers Auth URL
    2) Opens the browser to that URL
    3) Listens on port 80 for Fyers to redirect back with auth_code
    4) fetches and saves the access_token automatically
    """
    logging.basicConfig(level=logging.INFO)
    # Generate the login URL
    auth_url = fyers_integration.generate_auth_url()
    if auth_url:
        webbrowser.open(auth_url)
        logging.info(f"Opening Fyers login URL in your browser: {auth_url}")

    # Run local Flask server on port 80.
    # Make sure this is allowed on your machine (sudo or use a different port if needed).
    app.run(host="0.0.0.0", port=80)

if __name__ == "__main__":
    run_auth_server()

