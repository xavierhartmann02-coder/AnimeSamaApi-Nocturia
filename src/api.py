from flask import Flask, jsonify, request, Response
import requests

try:
    from .backend import *
except ImportError:
    from src.backend import *

class Yui:

    app = Flask(__name__)
    app.json.ensure_ascii = False

    @app.route('/', methods=["GET"])
    def home():
        q = request.args.get("q", "").strip()
        if not q:
            return jsonify({"error": "Paramètre 'q' manquant"}), 400
        else:
            cardinal = "Cardinal.test()"
            return jsonify({
                'Bonjours' : "Je suis une api...",
                'Valeur q ' : q,
                'Cardinal value' : cardinal
            })

    @app.route('/config', methods=["GET"])
    def config():
        return jsonify({
            'IP': Config.IP,
            'PORT': Config.PORT
        })

    @app.route('/api/status', methods=["GET"])
    def status():
        return jsonify({'API Status' : 'Online'})
        
    @app.route('/api/getAnimeSamaURL', methods=["GET"])
    def getAnimeSamaURL():
        reponse = Cardinal.findLink()
        return jsonify(reponse)
    
    @app.route('/api/getAllAnime', methods=["GET"])
    def getAllAnime():
        reset = request.args.get("r", "").strip()
        reponse = Cardinal.getAllAnime(reset)
        return jsonify(reponse)
        
    @app.route('/api/loadBaseAnimeData')
    def loadBaseAnimeData():
        return jsonify(Cardinal.loadBaseAnimeData())
    
    @app.route('/api/getSerchAnime', methods=["GET"])
    def serchAnime():
        querry = request.args.get("q", "").strip()
        limit = request.args.get("l", "").strip()

        if not querry:
            return jsonify({"error": "Paramètre 'q' manquant"}), 400
        try:
            limit = int(limit) if limit else 5   # convertir en entier
        except ValueError:
            limit = 5 # valeur par défaut si l'argument est invalide
        return jsonify(Cardinal.serchAnime(querry, limit))
    
    @app.route('/api/getInfoAnime', methods=["GET"])
    def getInfoAnime():
        querry = request.args.get("q", "").strip() or request.args.get("n", "").strip()
        if not querry:
            return jsonify({"error": "Paramètre 'q' manquant"}), 400
                
        return jsonify(Cardinal.getInfoAnime(querry))
    
    @app.route('/api/getSpecificAnime', methods=["GET"])
    def getSpecificAnime():
        querry = request.args.get("q", "").strip() or request.args.get("n", "").strip()
        saison = request.args.get("s", "").strip()
        version = request.args.get("v", "").strip()
    
        if not querry:
            return jsonify({"error": "Paramètre 'q' manquant"}), 400

        res = Cardinal.getSpecificAnime(querry, saison, version)
        if res is None:
            return jsonify({})
        return jsonify(res)    
    
    @app.route('/api/getAnimeLink', methods=["GET"])
    def getAnimeLink():
        nom = request.args.get("n", "").strip() or request.args.get("q", "").strip()
        saison = request.args.get("s", "").strip()
        version = request.args.get("v", "").strip()
        episode = request.args.get("e", "").strip() or request.args.get("ep", "").strip()

        if not nom:
            return jsonify({"error": "Paramètre 'n' manquant"}), 400
        
        return jsonify(Cardinal.getAnimeLink(nom, saison, version, episode))

    @app.route('/api/proxy', methods=["GET"])
    def proxy_hls():
        url = request.args.get('url', '').strip()
        if not url:
            return "URL manquante", 400
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://anime-sama.fr/'
        }
        
        try:
            resp = requests.get(url, headers=headers, stream=True, timeout=10)
            
            excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
            response_headers = [(name, value) for (name, value) in resp.raw.headers.items()
                                if name.lower() not in excluded_headers]
            
            response_headers.append(('Access-Control-Allow-Origin', '*'))
            response_headers.append(('Access-Control-Allow-Headers', '*'))

            return Response(resp.iter_content(chunk_size=1024), status=resp.status_code, headers=response_headers)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/getScanLink', methods=["GET"])
    def getScanLink():
        nom = request.args.get("n", "").strip() or request.args.get("q", "").strip()
        chaptitre = request.args.get("c", "").strip()

        if not nom:
            return jsonify({"error": "Paramètre 'n' manquant"}), 400

        return jsonify(Cardinal.getScanLink(nom, chaptitre))

    @app.route('/api/getScanHashmap', methods=["GET"])
    def getScanHashmap():
        nom = request.args.get("n", "").strip() or request.args.get("q", "").strip()

        if not nom:
            return jsonify({"error": "Paramètre 'n' manquant"}), 400

        return jsonify(Cardinal.getScanHashmap(nom))
