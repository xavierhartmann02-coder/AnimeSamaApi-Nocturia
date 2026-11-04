from urllib.parse import urljoin, quote

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
        
        # Si c'est un fichier de playlist HLS (.m3u8), on réécrit les liens internes
        if '.m3u8' in url:
            content = resp.content.decode('utf-8', errors='ignore')
            base_url = url.rsplit('/', 1)[0] + '/'
            
            new_lines = []
            for line in content.splitlines():
                line_str = line.strip()
                if line_str and not line_str.startswith('#'):
                    # Convertir le lien relatif/absolu du segment en URL absolue pointant vers notre proxy
                    abs_segment_url = urljoin(base_url, line_str)
                    proxy_segment_url = f"https://animesamaapi-nocturia-1.onrender.com/api/proxy?url={quote(abs_segment_url, safe='')}"
                    new_lines.append(proxy_segment_url)
                else:
                    new_lines.append(line)
            
            new_content = "\n".join(new_lines)
            return Response(
                new_content, 
                status=resp.status_code, 
                content_type='application/vnd.apple.mpegurl', 
                headers={'Access-Control-Allow-Origin': '*'}
            )

        # Pour les fichiers binaires (.ts, .mp4, etc.)
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        response_headers = [(name, value) for (name, value) in resp.raw.headers.items()
                            if name.lower() not in excluded_headers]
        
        response_headers.append(('Access-Control-Allow-Origin', '*'))
        response_headers.append(('Access-Control-Allow-Headers', '*'))

        return Response(resp.iter_content(chunk_size=1024), status=resp.status_code, headers=response_headers)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
