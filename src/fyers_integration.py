import logging, pytz, datetime
from fyers_apiv3 import fyersModel
from src.config_manager import ConfigManager, AppConfig

IST = pytz.timezone("Asia/Kolkata")

class FyersIntegration:
    """Handles v3 auth + thin helpers for REST calls."""

    def __init__(self):
        self.cfg = ConfigManager.load()
        self.config: AppConfig = ConfigManager.load()

    # ---------- OAUTH ---------- #
    def auth_url(self) -> str:
        s = fyersModel.SessionModel(
            client_id=self.cfg.client_id,
            redirect_uri=self.cfg.redirect_uri,
            response_type="code",
            state="state123",
            secret_key=self.cfg.secret_key,
            grant_type="authorization_code",
        )
        return s.generate_authcode()

    def generate_auth_url(self):
        """
        Creates Fyers OAuth login URL for the user to log in and get ?auth_code=...
        """
        if not self.config.client_id or not self.config.redirect_uri or not self.config.secret_key:
            logging.error("Missing client_id, redirect_uri, or secret_key in config.json.")
            return None
        session = fyersModel.SessionModel(
            client_id=self.config.client_id,
            redirect_uri=self.config.redirect_uri,
            response_type="code",
            state="sample",
            secret_key=self.config.secret_key,
            grant_type="authorization_code",
        )
        return session.generate_authcode()

    def fetch_access_token(self, auth_code: str):
        """
        Exchanges auth_code for access_token, then saves it in config.json.
        """
        session = fyersModel.SessionModel(
            client_id=self.config.client_id,
            redirect_uri=self.config.redirect_uri,
            response_type="code",
            state="sample",
            secret_key=self.config.secret_key,
            grant_type="authorization_code",
        )
        session.set_token(auth_code)
        response = session.generate_token()
        logging.info(f"[fetch_access_token] Response: {response}")

        if "access_token" in response:
            self.config.auth_code = auth_code
            self.config.access_token = response["access_token"]
            ConfigManager.save(self.config)
            logging.info("[fetch_access_token] Access token saved to config.json.")
        else:
            logging.error("[fetch_access_token] Error: No access_token in response.")


    def exchange_code(self, auth_code: str):
        s = fyersModel.SessionModel(
            client_id=self.cfg.client_id,
            redirect_uri=self.cfg.redirect_uri,
            response_type="code",
            state="state123",
            secret_key=self.cfg.secret_key,
            grant_type="authorization_code",
        )
        s.set_token(auth_code)
        resp = s.generate_token()
        if "access_token" in resp:
            self.cfg.auth_code = auth_code
            self.cfg.access_token = resp["access_token"]
            ConfigManager.save(self.cfg)
            logging.info("access_token stored.")
        else:
            logging.error(f"Token error: {resp}")

    # ---------- REST thin wrappers ---------- #
    def fyers(self):
        if not self.cfg.access_token:
            raise ValueError("No access_token. Run auth_server.py first.")
        return fyersModel.FyersModel(
            token=self.cfg.access_token,
            is_async=False,
            client_id=self.cfg.client_id)

    def history(self, fy, symbol, resolution, date_from, date_to):
        payload = {
            "symbol": symbol,
            "resolution": resolution,
            "date_format": "1",
            "range_from": date_from,
            "range_to": date_to,
            "cont_flag": "0"
        }
        return fy.history(payload)

    def place_order(self, fy, order):
        resp = fy.place_order(order)
        logging.getLogger("FyersREST").info(f"REST /place_order resp: {resp}")
        return resp
