import json, os, re, cloudscraper, requests, unicodedata
from urllib.parse import urlparse, quote
from concurrent.futures import ThreadPoolExecutor
from rapidfuzz import process, fuzz
from bs4 import BeautifulSoup

try :
    from .utils.resolvers import resolve_video_url, check_stream_health
    from .utils.config import Config
    from .utils.utils import Utils
except ImportError:
    from src.utils.resolvers import resolve_video_url, check_stream_health
    from src.utils.config import Config
    from src.utils.utils import Utils


PATH = os.path.dirname(os.path.abspath(__file__))
PATH_DIR = os.path.join(PATH, "data", "json")
PATH_ANIME = os.path.join(PATH_DIR, "AnimeInfo.json")
BASE_URL = Utils.findLink()

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
}

class Cardinal:

    def findLink():
        return {"url": BASE_URL}
        
    def getAllAnime(reset="False"):
        global BASE_URL
        base_url = BASE_URL if BASE_URL else Utils.findLink()
        if not base_url:
            return "Erreur : Impossible de joindre Anime-Sama pour trouver l'URL."
        BASE_URL = base_url

        os.makedirs(PATH_DIR, exist_ok=True) # Verifi l'existance du dossier data/json

        is_empty = True
        existing_alts_by_link = {}
        if os.path.exists(PATH_ANIME) and os.path.getsize(PATH_ANIME) > 2:
            try:
                with open(PATH_ANIME, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                    if isinstance(existing, list) and len(existing) > 0:
                        is_empty = False
                        for item in existing:
                            if isinstance(item, dict) and item.get("link") and item.get("alt_titles"):
                                existing_alts_by_link[item["link"]] = item["alt_titles"]
            except Exception:
                is_empty = True

        is_reset = str(reset).strip().lower() in ["true", "1", "yes", "t"]

        if not is_empty and not is_reset:
            return "Fichier déjà existant. Ajoutez l'argument reset='True' pour tout actualiser."

        scraper = cloudscraper.create_scraper()  # équivaut à un navigateur
        max_pages = 1
        page_1_html = ""

        try:
            first_response = scraper.get(f"{base_url}/catalogue/fragment.php?page=1", timeout=10)
            if first_response.status_code == 200:
                json_data = first_response.json()
                page_1_html = json_data.get('liste', '')
                total_items = int(json_data.get('total', 0))
                if total_items > 0:
                    max_pages = (total_items + 47) // 48
                else:
                    pagi_soup = BeautifulSoup(json_data.get('pagination', ''), 'lxml')
                    page_input = pagi_soup.find('input', attrs={'max': True})
                    if page_input and page_input.get('max', '').isdigit():
                        max_pages = int(page_input['max'])
        except Exception:
            pass

        if max_pages <= 1 and not page_1_html:
            first_response = scraper.get(f"{base_url}/catalogue", timeout=10)
            if first_response.status_code != 200:
                return first_response.status_code

            soup_init = BeautifulSoup(first_response.content, 'lxml')
            page_input = soup_init.find('input', attrs={'max': True})
            if page_input and page_input.get('max', '').isdigit():
                max_pages = int(page_input['max'])
            else:
                pagi_links = soup_init.select('.pagi-pages .pagi-num')
                nums = [int(a.get_text(strip=True)) for a in pagi_links if a.get_text(strip=True).isdigit()]
                max_pages = max(nums) if nums else 1

        def fetch_page_content(page_num):
            if page_num == 1 and page_1_html:
                return page_1_html
            for _ in range(3):
                try:
                    r = scraper.get(f"{base_url}/catalogue/fragment.php?page={page_num}", timeout=10)
                    if r.status_code == 200:
                        return r.json().get('liste', '')
                    r_cat = scraper.get(f"{base_url}/catalogue/?page={page_num}", timeout=10)
                    if r_cat.status_code == 200:
                        return r_cat.content
                except Exception:
                    pass
            return ""

        with ThreadPoolExecutor(max_workers=10) as executor:
            pages_content = list(executor.map(fetch_page_content, range(1, max_pages + 1)))

        data = []
        seen_links = set()

        for content in pages_content:
            if not content:
                continue
            soup = BeautifulSoup(content, 'lxml')

            cards = soup.select('.as-carte')
            if cards:
                for card in cards:
                    titre = card.get('data-nom', '').strip()
                    if not titre:
                        t_tag = card.find(class_='as-carte-titre') or card.find(['h3', 'h2'])
                        titre = t_tag.get_text(strip=True) if t_tag else ""

                    a_tag = card.find('a', class_='as-carte-lien') or card.find('a')
                    link = a_tag.get('href', '').strip() if a_tag else card.get('data-url', '').strip()
                    if link:
                        parsed = urlparse(link)
                        path = parsed.path.rstrip('/')
                        link = f"{base_url.rstrip('/')}{path}"

                    cover = card.get('data-img', '').strip()
                    if not cover:
                        img_tag = card.find('img')
                        cover = img_tag.get('src', '').strip() if img_tag else ""

                    if titre and link and link not in seen_links:
                        seen_links.add(link)
                        entry = {
                            "title": Cardinal.normalize_title(titre),
                            "link": link,
                            "cover": cover
                        }
                        if link in existing_alts_by_link:
                            entry["alt_titles"] = existing_alts_by_link[link]
                        data.append(entry)
            else:
                titles = soup.find_all('h2', class_="card-title")
                for title_tag in titles:
                    card_link = title_tag.find_parent('a')
                    titre = title_tag.get_text(strip=True)
                    link = card_link.get('href', '') if card_link else ""
                    if link and link.startswith('/'):
                        link = f"{base_url.rstrip('/')}{link}"
                    img_tag = card_link.find('img', class_="card-image") if card_link else None
                    img_src = img_tag.get('src', '') if img_tag else ""

                    if titre and link and link not in seen_links:
                        seen_links.add(link)
                        entry = {
                            "title": Cardinal.normalize_title(titre),
                            "link": link,
                            "cover": img_src
                        }
                        if link in existing_alts_by_link:
                            entry["alt_titles"] = existing_alts_by_link[link]
                        data.append(entry)

        with open(PATH_ANIME, "w", encoding='utf-8') as t:
            json.dump(data, t, ensure_ascii=False, indent=2)

        return "Recuperation achever"

    def loadBaseAnimeData():
        if os.path.exists(PATH_ANIME) == True:
            try:
                with open(PATH_ANIME, "r", encoding="utf-8") as data:
                    anime_data = json.load(data)
            except Exception:
                anime_data = []

            # Si le fichier est vide, on déclenche l'actualisation
            if not anime_data:
                Cardinal.getAllAnime(reset="True")
                if os.path.exists(PATH_ANIME):
                    with open(PATH_ANIME, "r", encoding="utf-8") as refreshed:
                        return json.load(refreshed)
                return []

            if BASE_URL:
                # Extraire le domaine de BASE_URL (ex: "anime-sama.si")
                base_domain = BASE_URL.replace("https://", "").replace("http://", "").rstrip("/")

                # Initialiser la variable AVANT la boucle
                needs_refresh = False

                # Vérifier si au moins un lien dans les données utilise un mauvais domaine
                for anime in anime_data:
                    if "link" in anime:
                        anime_link = anime["link"]
                        # Vérifier si le lien contient le bon domaine
                        if base_domain not in anime_link:
                            needs_refresh = True
                            break  # Un seul suffit pour déclencher l'actualisation complète

                if needs_refresh:
                    Cardinal.getAllAnime(reset="True")
                    with open(PATH_ANIME, "r", encoding="utf-8") as refreshed:
                        return json.load(refreshed)

            return anime_data
        else:
            Cardinal.getAllAnime(reset="True")
            if os.path.exists(PATH_ANIME):
                with open(PATH_ANIME, "r", encoding="utf-8") as refreshed:
                    return json.load(refreshed)
            return f"Fichier non existant veuillez request : http://{Config.IP}:{Config.PORT}/api/getAllAnime"
    
    def normalize_title(title):
        if not title:
            return ""

        # Normalize les accents en standards
        title = unicodedata.normalize("NFKD", title)
        title = "".join([c for c in title if not unicodedata.combining(c)])

        # Converti les guillemets spéciaux en guillemets simples
        title = title.replace("“", "\"").replace("”", "\"")
        title = title.replace("‘", "'").replace("’", "'")

        # Remplacer les caractères interdits JSON ou filesystem
        forbidden = r'[\/\\\:\*\?\"\<\>\|]'
        title = re.sub(forbidden, " ", title)

        # Nettoyer les caractères non alphanumériques excessifs
        title = re.sub(r"[^a-zA-Z0-9\-\_\&\.\'\#\s]", " ", title)

        # Réduire espaces multiples
        title = re.sub(r"\s+", " ", title).strip()

        return title
    
    def clean_string(text):
        """Une fonction pour nettoyer et normaliser une chaîne de caractères."""
        if not text:
            return ""
        # Met tout en minuscule
        text = text.lower()
        # Ne garde que les lettres, les chiffres et les espaces
        text = re.sub(r'[^a-z0-9\s]', '', text)
        # Enlève les espaces en trop
        text = re.sub(r'\s+', ' ', text).strip()
        return text
            
    STOP_WORDS = {'le', 'la', 'les', 'un', 'une', 'de', 'du', 'des', 'the', 'a', 'an', 'of', 'in', 'to', 'no', 'et', 'and'}

    @staticmethod
    def _evaluate_match(cq, ct):
        if cq == ct:
            return 100.0

        q_words = cq.split()
        t_words = ct.split()
        if not q_words or not t_words:
            return 0.0

        # Cas 1: cq est une sous-chaîne exacte de ct (ex: 'naruto' in 'naruto shippuden')
        if cq in ct:
            extra_words = max(0, len(t_words) - len(q_words))
            ratio_len = len(cq) / len(ct)
            return max(60.0, 75.0 + 15.0 * ratio_len - (extra_words * 2.5))

        # Cas 2: ct est une sous-chaîne exacte de cq (ex: 'frieren' in 'sousou no frieren')
        if ct in cq and len(ct) >= 3:
            non_matching_q = [w for w in q_words if not any(fuzz.ratio(w, tw) >= 70 for tw in t_words)]
            non_matching_substantive = [w for w in non_matching_q if w not in Cardinal.STOP_WORDS]
            # Si plus de 2 mots substantiels ajoutés ne correspondent à rien, rejeter
            if len(non_matching_substantive) >= 3:
                return 0.0
            ratio_len = len(ct) / len(cq)
            return 80.0 + 20.0 * ratio_len

        # Cas 3: Ni l'un ni l'autre n'est sous-chaîne
        # Chaque mot important de la requête doit correspondre à au moins un mot du titre
        for qw in q_words:
            if qw in Cardinal.STOP_WORDS:
                continue
            best_w = max((fuzz.ratio(qw, tw) for tw in t_words), default=0)
            if best_w < 70:
                return 0.0

        # Vérifier aussi la couverture inverse pour rejeter les titres trop longs et hors-sujet
        matched_t = 0
        substantive_t = 0
        for tw in t_words:
            if tw in Cardinal.STOP_WORDS:
                continue
