import os
import json
import requests
import serpapi
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# --- KEYS (ENSURE THESE ARE CORRECT) ---
SERPAPI_KEY = os.environ.get("SERPAPI_KEY")
IMGBB_KEY = os.environ.get("IMGBB_KEY")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 1. LOAD LOCAL DATABASE ON STARTUP
try:
    with open(os.path.join(BASE_DIR, "PokemonData.json"), "r", encoding="utf-8") as f:
        POKEMON_DB = json.load(f)
    print("Local Pokedex Database Loaded!")
except FileNotFoundError:
    print("CRITICAL: PokemonData.json not found! Run the scraper script first.")
    POKEMON_DB = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        data = request.get_json()
        encoded_data = data['image'].split(',', 1)[1]
        
        # Step 1: Upload to ImgBB
        res = requests.post("https://api.imgbb.com/1/upload", {"key": IMGBB_KEY, "image": encoded_data})
        img_url = res.json()['data']['url']

        # Step 2: Google Lens
        client = serpapi.Client(api_key=SERPAPI_KEY)
        results = client.search({"engine": "google_lens", "url": img_url})
        
        # Step 3: Match Name
        visual_matches = results.get("visual_matches", [])
        titles = [match.get("title", "").lower() for match in visual_matches]
        all_words = " ".join(titles).replace(",", " ").split()
        
        # Compare against our local keys (which are Capitalized)
        match_found = None
        for word in all_words:
            capital_word = word.capitalize()
            if capital_word in POKEMON_DB:
                match_found = capital_word
                break

        if not match_found:
            return jsonify({'error': 'Pokemon not recognized'}), 404

        # Step 4: GET DATA FROM LOCAL DB (NO SCRAPING!)
        pokemon_info = POKEMON_DB[match_found]
        
        # Slug is still needed for the external "Details" link
        slug = match_found.lower().replace(" ", "-").replace(".", "").replace("'", "")

        return jsonify({
            'name': match_found,
            'number': pokemon_info['number'],
            'description': pokemon_info['description'],
            'image_url': f"/static/Full Pokemon/{match_found}.png",
            'types': pokemon_info['types'],
            'pokedex_url': f"https://www.pokemon.com/uk/pokedex/{slug}"
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': 'Server error'}), 500

if __name__ == '__main__':
    # Use the PORT provided by Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
