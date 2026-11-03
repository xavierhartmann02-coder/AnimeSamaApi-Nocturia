import os

try:
    from .src.api import *
    from .src.utils.config import Config, Utils
except ImportError:
    from src.api import *
    from src.utils.config import Config, Utils

class Api:
    
    @staticmethod
    def launch(port=None, ip=None, debug_state: bool = False, reload_status: bool = False):
        Utils.hashCheck()
        Utils.gitCheck()

        # Récupération dynamique du port fourni par Render
        port = int(os.environ.get("PORT", port if port else 5000))
        ip = os.environ.get("HOST", ip if ip else "0.0.0.0")

        Config.IP = ip
        Config.PORT = port

        # Utilisation de l'instance Flask importée
        Yui.app.run(
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
