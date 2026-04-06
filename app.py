import os
import json
import requests
import serpapi
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# --- KEYS (ENSURE THESE ARE CORRECT) ---
SERPAPI_KEY = "4d2aba90b29c07b833c32e9188908d11299ef2126e50dab873ee41bf25d3d7e7"
IMGBB_KEY = "58f4278c0df1a7a54c5ae3135d115031"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 1. LOAD LOCAL DATABASE ON STARTUP
try:
    with open(os.path.join(BASE_DIR, "PokemonData.json"), "r", encoding="utf-8") as f:
        POKEMON_DB = json.load(f)
    print("Local Pokedex Database Loaded!")
except FileNotFoundError:
    print("CRITICAL: PokemonData.json not found! Run the scraper script first.")
    POKEMON_DB = {}

print(POKEMON_DB.keys())

@app.route('/')
def index():
    return render_template('index.html')

# NEW ROUTE: This serves the grid data to your new Pokedex tab
@app.route('/api/all_pokemon')
def get_all_pokemon():
    return jsonify(POKEMON_DB)

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
        titles = [match.get("title", "").title() for match in visual_matches]
        all_words = ", ".join(titles).title()
        
        print(all_words)

        # Compare against our local keys
        match_found = None
        matches = []
        for pokemon in list(POKEMON_DB.keys()):
            for i in range(all_words.count(pokemon)):
                matches.append(pokemon)

        print(matches)

        if not matches:
            return jsonify({'error': 'Pokemon not recognized'}), 404
        else:
            match_found = max(set(matches), key=matches.count)

        # Step 4: GET DATA FROM LOCAL DB
        pokemon_info = POKEMON_DB[match_found]
        
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

# ALWAYS keep this at the very bottom
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
