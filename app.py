import os
import json
import requests
from serpapi import GoogleSearch
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# --- PRODUCTION CONFIG ---
SERPAPI_KEY = os.environ.get("SERPAPI_KEY")
IMGBB_KEY = os.environ.get("IMGBB_KEY")

# Add these two lines for debugging!
print(f"DEBUG: SERPAPI_KEY is Loaded: {bool(SERPAPI_KEY)}")
print(f"DEBUG: IMGBB_KEY is Loaded: {bool(IMGBB_KEY)}")

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
        print("--- DEBUG: Starting Upload ---")
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'error': 'No image data received'}), 400
            
        encoded_image = data['image'].split(',', 1)[1]

        # 1. ImgBB Upload
        print("--- DEBUG: Uploading to ImgBB ---")
        img_res = requests.post("https://api.imgbb.com/1/upload", 
                                {"key": IMGBB_KEY, "image": encoded_image}, timeout=15)
        img_json = img_res.json()
        
        if 'data' not in img_json:
            print(f"--- DEBUG: ImgBB Failed: {img_json} ---")
            return jsonify({'error': 'ImgBB failed', 'raw': img_json}), 500
            
        img_url = img_json['data']['url']
        print(f"--- DEBUG: ImgBB Success: {img_url} ---")

        # 2. Google Lens (Correct New Syntax)
        print("--- DEBUG: Running SerpApi GoogleSearch ---")
        
        try:
            # 1. Initialize the search object
            search = GoogleSearch({
                "engine": "google_lens",
                "url": img_url,
                "api_key": SERPAPI_KEY
            })
            
            # 2. Execute the search and convert to a dictionary (CRITICAL STEP)
            results = search.get_dict()
            
            # 3. Pull the visual matches from the dictionary
            visual_matches = results.get("visual_matches", [])
            print(f"--- DEBUG: Found {len(visual_matches)} visual matches ---")
            
        except Exception as e:
            print(f"SerpApi Connection Error: {e}")
            return jsonify({'error': 'Search Engine Connection Failed'}), 500
        
        # 3. Matching
        visual_matches = search.get("visual_matches", [])
        print(f"--- DEBUG: Found {len(visual_matches)} visual matches ---")
        
        found_name = None
        for match in visual_matches:
            title = match.get("title", "")
            print(f"--- DEBUG: Checking title: {title} ---")
            # Clean title: remove special chars and split into words
            clean_title = title.replace(",", " ").replace("(", " ").replace(")", " ").lower()
            words = clean_title.split()
            
            for word in words:
                cap_word = word.capitalize()
                if cap_word in POKEMON_DB:
                    found_name = cap_word
                    break
            if found_name: break

        if not found_name:
            print("--- DEBUG: No match found in POKEMON_DB ---")
            return jsonify({'error': 'Pokemon not recognized'}), 404

        # 4. Final Response
        print(f"--- DEBUG: Match Found: {found_name} ---")
        info = POKEMON_DB[found_name]
        
        return jsonify({
            'name': found_name,
            'number': info.get('number', '#???'),
            'description': info.get('description', 'No data'),
            'image_url': f"/static/Full Pokemon/{found_name}.png",
            'types': info.get('types', ['Unknown']),
            'pokedex_url': f"https://www.pokemon.com/uk/pokedex/{found_name.lower()}"
        })

    except Exception as e:
        import traceback
        err_msg = traceback.format_exc()
        print(f"--- DEBUG: CRITICAL ERROR ---\n{err_msg}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Use the PORT provided by Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
