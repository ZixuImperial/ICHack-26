
import os
import base64
import random
import socket
import csv
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from google import genai
from google.genai import types
from PIL import Image
import io
import json
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

app = Flask(__name__)
CORS(app)

DEFAULT_LOCATION = "UK"

# Configure Gemini API
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY environment variable not set!")
    print("Please set it with: export GEMINI_API_KEY='your-api-key'")

client = genai.Client(api_key=GEMINI_API_KEY)

# Initialize geocoder
geolocator = Nominatim(user_agent="recycle_checker_app")

# CSV file path for logging
CSV_LOG_FILE = "recycling_log.csv"

# Building bins database
BUILDING_BINS_FILE = "building_bins.json"

# Default bins if building not in database
DEFAULT_BINS = ["Recyclable", "General Waste"]

# Load building bins database
def load_building_bins():
    """Load the building bins database from JSON file"""
    try:
        if os.path.isfile(BUILDING_BINS_FILE):
            with open(BUILDING_BINS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Error loading building bins database: {str(e)}")
        return {}

building_bins_db = load_building_bins()

def save_to_csv(log_data):
    """Save log data to CSV file"""
    try:
        # Check if file exists to determine if we need to write headers
        file_exists = os.path.isfile(CSV_LOG_FILE)

        with open(CSV_LOG_FILE, 'a', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['timestamp', 'location', 'material', 'recyclable', 'description', 'bin_type']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            # Write header if file is new
            if not file_exists:
                writer.writeheader()

            # Parse log_data (should be comma-separated string)
            if isinstance(log_data, str):
                parts = [item.strip() for item in log_data.split(',')]
            else:
                parts = log_data

            # Ensure we have 5 parts (pad if necessary)
            parts = (parts + ['', '', '', '', ''])[:5]

            # Write the row with timestamp
            writer.writerow({
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'location': parts[0],
                'material': parts[1],
                'recyclable': parts[2],
                'description': parts[3],
                'bin_type': parts[4]
            })

            print(f"✓ Logged to CSV: {parts}")
            return True

    except Exception as e:
        print(f"Error saving to CSV: {str(e)}")
        return False

def get_location_info_from_coordinates(latitude, longitude):
    """Get location information including council and building from GPS coordinates"""
    try:
        location = geolocator.reverse(f"{latitude}, {longitude}", exactly_one=True, language='en')

        if location and location.raw.get('address'):
            address = location.raw['address']

            # Try to extract council/municipality information
            # Priority order: city_district, suburb, town, city, county
            council = (
                address.get('city_district') or
                address.get('suburb') or
                address.get('town') or
                address.get('city') or
                address.get('county') or
                address.get('state_district') or
                DEFAULT_LOCATION
            )

            # For UK, also include the county if available
            if address.get('country_code') == 'gb':
                county = address.get('county')
                if county and county != council:
                    council = f"{council}, {county}"

            # Try to extract building information
            # Priority order: building name, amenity, house name, office, or construct from address
            building = (
                address.get('building') or
                address.get('amenity') or
                address.get('house') or
                address.get('office') or
                address.get('tourism') or
                address.get('leisure') or
                None
            )

            # If no specific building name, construct address from components
            if not building:
                house_number = address.get('house_number', '')
                road = address.get('road', '')
                if house_number and road:
                    building = f"{house_number} {road}"
                elif road:
                    building = road
                else:
                    building = "Unknown building"

            print(f"Council: {council}, Building: {building}")
            return council, building

        print("Default out")
        return DEFAULT_LOCATION, "Unknown building"

    except (GeocoderTimedOut, GeocoderServiceError) as e:
        print(f"Geocoding error: {str(e)}")
        return DEFAULT_LOCATION, "Unknown building"
    except Exception as e:
        print(f"Unexpected error in geocoding: {str(e)}")
        return DEFAULT_LOCATION, "Unknown building"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/validate_bins', methods=['POST'])
def validate_bins():
    try:
        # Get the input text from the request
        data = request.get_json()
        input_text = data.get('input_text', '')

        if not input_text:
            return jsonify({'error': 'No input text provided'}), 400

        # Create prompt for Gemini to validate and extract bin types
        prompt = f"""Extract and validate the types of recycling/waste bins from the following text: "{input_text}"

Analyze the input and:
1. Identify valid bin types mentioned (e.g., Recycling, General Waste, Food Waste, Glass, Paper, Plastic, etc.)
2. Correct any spelling mistakes or variations
3. Remove any invalid or nonsensical entries
4. Return only legitimate waste/recycling bin types

Provide your response in the following JSON format:
{{
  "bins": ["Bin Type 1", "Bin Type 2", "Bin Type 3"]
}}

If no valid bin types are found, return an empty array.
"""

        # Generate response from Gemini
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        # Parse the response
        parsed_response = json.loads(response.text)

        # Handle if response is a list - take first element
        if isinstance(parsed_response, list) and len(parsed_response) > 0:
            parsed_response = parsed_response[0]

        # Extract validated bins
        validated_bins = parsed_response.get("bins", [])

        if not validated_bins:
            return jsonify({'error': 'No valid bin types found in the input'}), 400

        return jsonify({
            'bins': validated_bins,
            'count': len(validated_bins)
        })

    except Exception as e:
        print(f"Error validating bins: {str(e)}")
        return jsonify({'error': f'Failed to validate bins: {str(e)}'}), 500

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        # Check if image was uploaded
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400

        image_file = request.files['image']

        if image_file.filename == '':
            return jsonify({'error': 'No image selected'}), 400

        # Read and process the image
        image_data = image_file.read()
        image = Image.open(io.BytesIO(image_data))

        # Optimize image for faster inference
        # Resize to max 800px on longest side while maintaining aspect ratio
        max_size = 800
        if max(image.size) > max_size:
            ratio = max_size / max(image.size)
            new_size = tuple(int(dim * ratio) for dim in image.size)
            image = image.resize(new_size, Image.Resampling.LANCZOS)

        # Convert to RGB if necessary (handles RGBA, grayscale, etc.)
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Compress image to JPEG with good quality
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG', quality=85, optimize=True)
        image_data = img_byte_arr.getvalue()

        # Get GPS coordinates and determine council and building
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        building = "Unknown building"

        if latitude and longitude:
            try:
                council, building = get_location_info_from_coordinates(float(latitude), float(longitude))
                print(f"Location detected: {council}, Building: {building} (Lat: {latitude}, Lon: {longitude})")
            except ValueError:
                council = DEFAULT_LOCATION
                building = "Unknown building"
                print("Invalid GPS coordinates received")
        else:
            council = DEFAULT_LOCATION
            building = "Unknown building"
            print("No GPS coordinates provided")
        # Create prompt for Gemini
        prompt = f"""Can the subject of this photo be put in the recycling bin in its current state?
Firstly identify the type of material and for plastics the exact type.
Then determine whether this can be put in the recycling in the local council.
In this case the local council is {council}.
Then reason about the current state and whether it should be put in the recyling bin.
If the answer is leaning either way then answer accordingly.

Provide your response in the following format:

MAIN_RESPONSE: [A clear, concise answer - either "Yes" or "No" or "Yes - However..." or "Maybe..."]

SUBTEXT: [If the response is a however then provide a simple recommended step before recycling]

LOG: [A comma seperated response with the following information in order: Location, The material and in the case of plastic the exact type, Whether or not it could be recycled Yes/No, A small description of what the item was, The bin type it should go in (Recycle bin if MAIN_RESPONSE is Yes, Non-recycle bin if MAIN_RESPONSE is No, Unknown if MAIN_RESPONSE is Maybe)]
"""
        # Generate response from Gemini
        response = client.models.generate_content(
        model="gemini-3-flash-preview", # Use 'flash' for speed in hackathons
        contents=[
            types.Part.from_bytes(data=image_data, mime_type="image/jpeg"),
            prompt
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json" # Forces JSON output
        )
        )
        print(response.text)
        # Parse the response
        parsed_response = json.loads(response.text)
        print(parsed_response)
        print(council)
        print(prompt)

        # Handle if response is a list (array) - take first element
        if isinstance(parsed_response, list) and len(parsed_response) > 0:
            parsed_response = parsed_response[0]

        # Extract and save LOG data to CSV
        log_data = parsed_response.get("LOG", "")
        if log_data:
            save_to_csv(log_data)

        # Get available bins for this building
        available_bins = building_bins_db.get(building, DEFAULT_BINS)

        return jsonify({
            'main_response': parsed_response.get("MAIN_RESPONSE", "Unknown"),
            'subtext': parsed_response.get("SUBTEXT", "No details provided"),
            'available_bins': available_bins,
            'building': building
        })

    except Exception as e:
        print(f"Error analyzing image: {str(e)}")
        return jsonify({'error': f'Failed to analyze image: {str(e)}'}), 500

def parse_response(response_text):
    """Parse the Gemini response into main response and subtext"""
    try:
        # Split the response by the markers
        main_response = ""
        subtext = ""

        # Look for MAIN_RESPONSE and SUBTEXT markers
        if "MAIN_RESPONSE:" in response_text:
            parts = response_text.split("MAIN_RESPONSE:")
            if len(parts) > 1:
                remaining = parts[1]
                if "SUBTEXT:" in remaining:
                    response_parts = remaining.split("SUBTEXT:")
                    main_response = response_parts[0].strip()
                    subtext = response_parts[1].strip()
                else:
                    main_response = remaining.strip()
        else:
            # If markers aren't found, try to split intelligently
            lines = response_text.strip().split('\n')

            # First non-empty line is main response
            for line in lines:
                if line.strip():
                    main_response = line.strip()
                    break

            # Rest is subtext
            subtext = '\n'.join(lines[1:]).strip()

        # Clean up the responses
        main_response = main_response.replace('*', '').strip()
        subtext = subtext.replace('*', '').strip()

        # Fallback if parsing failed
        if not main_response:
            main_response = "Analysis completed"
        if not subtext:
            subtext = response_text

        return main_response, subtext

    except Exception as e:
        print(f"Error parsing response: {str(e)}")
        return "Unable to determine", response_text

def get_local_ip():
    """Get the local IP address of this machine"""
    try:
        # Create a socket to find local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "localhost"

if __name__ == '__main__':
    # Use a random port between 5000-9999 for security
    # Store in environment variable to persist across debug reloader restarts
    if not os.environ.get('SERVER_PORT'):
        port = random.randint(5000, 9999)
        os.environ['SERVER_PORT'] = str(port)
    else:
        port = int(os.environ.get('SERVER_PORT'))

    local_ip = get_local_ip()

    # Only print startup info in the main process (not in the reloader)
    # The reloader sets WERKZEUG_RUN_MAIN environment variable
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        print("\n" + "="*60)
        print("🌍 RECYCLE CHECKER SERVER STARTING")
        print("="*60)
        print(f"\n📱 Access from this computer:")
        print(f"   http://localhost:{port}")
        print(f"\n📱 Access from mobile (same WiFi):")
        print(f"   http://{local_ip}:{port}")
        print(f"\n⚠️  Security Note: Only share this URL with trusted users")
        print(f"   Server will be accessible to anyone on your network")
        print("\n" + "="*60 + "\n")

    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=port)
