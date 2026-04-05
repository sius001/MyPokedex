import os
import json
import requests
import serpapi
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# --- PRODUCTION CONFIG ---
# This pulls keys from Render's "Environment Variables" menu instead of hardcoding them
SERPAPI_KEY = os.environ.get("SERPAPI_KEY")
IMGBB_KEY = os.environ.get("IMGBB_KEY")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load the local JSON database we built with the scraper
try:
    with open(os.path.join(BASE_DIR, "PokemonData.json"), "r", encoding="utf-8") as f:
        POKEMON_DB = json.load(f)
    print("Database loaded successfully.")
except Exception as e:
    print(f"Error loading database: {e}")
    POKEMON_DB = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        data = request.get_json()
        encoded_image = data['image'].split(',', 1)[1]

        # 1. ImgBB Upload
        img_res = requests.post("https://api.imgbb.com/1/upload", 
                                {"key": IMGBB_KEY, "image": encoded_image})
        img_url = img_res.json()['data']['url']

        # 2. Google Lens (SerpApi)
        client = serpapi.Client(api_key=SERPAPI_KEY)
        search = client.search({"engine": "google_lens", "url": img_url})
        
        # 3. Matching
        visual_matches = search.get("visual_matches", [])
        found_name = None
        
        # We look for a match in our POKEMON_DB keys
        for match in visual_matches:
            title_words = match.get("title", "").lower().split()
            for word in title_words:
                cap_word = word.capitalize()
                if cap_word in POKEMON_DB:
                    found_name = cap_word
                    break
            if found_name: break

        if not found_name:
            return jsonify({'error': 'Pokemon not recognized'}), 404

        # 4. Return Data
        info = POKEMON_DB[found_name]
        slug = found_name.lower().replace(" ", "-").replace(".", "").replace("'", "")
        
        return jsonify({
            'name': found_name,
            'number': info['number'],
            'description': info['description'],
            'image_url': f"/static/Full Pokemon/{found_name}.png",
            'types': info['types'],
            'pokedex_url': f"https://www.pokemon.com/uk/pokedex/{slug}"
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Use the PORT provided by Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
