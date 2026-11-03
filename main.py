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
        """
        Lance l'application Yui avec les paramètres spécifiés.
        """
        Utils.hashCheck()
        Utils.gitCheck()

        # Récupération automatique du port et de l'IP (priorité aux variables d'environnement de Render)
        port = int(os.environ.get("PORT", port if port else 5000))
        ip = os.environ.get("HOST", ip if ip else "0.0.0.0")

        Config.IP = ip
        Config.PORT = port

        Yui.app.run(
            host=ip,
            port=port,
            debug=debug_state, 
            use_reloader=reload_status
        )

if __name__ == "__main__":
    # En production sur Render, on désactive par défaut le debug et le reloader
    Api.launch(
        debug_state=os.environ.get("DEBUG", "False").lower() == "true",
        reload_status=False
    )
