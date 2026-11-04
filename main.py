import os
from flask_cors import CORS

try:
    from .src.api import app
    from .src.utils.config import Config, Utils
except ImportError:
    from src.api import app
    from src.utils.config import Config, Utils

class Api:
    
    @staticmethod
    def launch(port=None, ip=None, debug_state: bool = False, reload_status: bool = False):
        try:
            Utils.hashCheck()
            Utils.gitCheck()
        except Exception:
            pass

        # Récupération dynamique du port fourni par Render
        port = int(os.environ.get("PORT", port if port else 5000))
        ip = os.environ.get("HOST", ip if ip else "0.0.0.0")

        try:
            Config.IP = ip
            Config.PORT = port
        except Exception:
            pass

        # Activation du CORS sur l'application Flask
        CORS(app)

        # Utilisation de l'instance Flask importée
        app.run(
            host=ip,
            port=port,
            debug=debug_state, 
            use_reloader=reload_status
        )

if __name__ == "__main__":
    Api.launch(
        debug_state=os.environ.get("DEBUG", "False").lower() == "true",
        reload_status=False
    )
