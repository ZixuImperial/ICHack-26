# ICHack-26 - Recycle Checker

A web application that helps users determine if items are recyclable by analyzing photos using AI.

## Features

- 📱 **Mobile-friendly**: Take photos directly from your phone's camera
- 💻 **Desktop support**: Upload images from your computer
- 🤖 **AI-powered**: Uses Google's Gemini API for intelligent image analysis
- ♻️ **Detailed feedback**: Get comprehensive recycling instructions
- 🎨 **Clean UI**: Minimal, modern design that's easy to use

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- A Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

### Installation

1. **Clone the repository**
   ```bash
   cd ICHack-26
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**

   Create a `.env` file in the root directory:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your Gemini API key:
   ```
   GEMINI_API_KEY=your_actual_api_key_here
   ```

   Alternatively, export it directly:
   ```bash
   export GEMINI_API_KEY='your_actual_api_key_here'
   ```

   On Windows:
   ```cmd
   set GEMINI_API_KEY=your_actual_api_key_here
   ```

### Running the Application

1. **Start the Flask server**
   ```bash
   python app.py
   ```

   The server will start on a **random port** (between 5000-9999) for security.
   The console will display the exact URLs to access the app:
   - Local access URL (for this computer)
   - Network access URL (for mobile devices on the same WiFi)

2. **Access the application**
   - Copy the URL shown in the console output
   - On this computer: Use the `http://localhost:PORT` URL
   - On mobile (same WiFi): Use the `http://IP_ADDRESS:PORT` URL

   **Security Note**: The randomized port makes it harder for others on your WiFi to find the service, but anyone with the URL can still access it. Only share the URL with trusted users.

## Usage

1. **Take or Upload a Photo**
   - On mobile: Click "Take Photo" to use your camera
   - On desktop: Click "Upload Photo" to select an image file

2. **Analyze**
   - Review the photo preview
   - Click "Check if Recyclable" to analyze

3. **Get Results**
   - View the main verdict (recyclable or not)
   - Read detailed recycling instructions and tips

## Project Structure

```
ICHack-26/
├── app.py                 # Flask backend server
├── analyze_logs.py        # Recycling log analyzer
├── example_usage.py       # Example analytics usage
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variable template
├── templates/
│   └── index.html        # Main HTML page
├── static/
│   ├── style.css         # Styling
│   └── script.js         # Frontend JavaScript
└── README.md             # This file
```

## Technologies Used

- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Backend**: Python, Flask
- **AI**: Google Gemini API
- **Image Processing**: Pillow (PIL)

## Security Features

- **Random Port Assignment**: The server uses a random port (5000-9999) each time it starts, making it harder for unauthorized users on your WiFi to discover the service
- **Network Isolation**: Only accessible to devices on the same local network
- **HTTPS Recommended**: For production use, deploy behind HTTPS to protect data in transit

**Important**: This is a development server suitable for local/demo use. For production deployment, use a proper WSGI server (like Gunicorn) with HTTPS, authentication, and rate limiting.

## Analytics & Logging

The app automatically logs all recycling checks to `recycling_log.csv` with the following data:
- Timestamp
- Location (GPS-based council)
- Material type
- Recyclability status
- Item description

### Analyzing Recycling Data

Use the built-in analyzer to generate statistics:

```bash
python analyze_logs.py
```

This will display:
- Material distribution and percentages
- Recyclability rates by material
- Location-based breakdowns
- Detailed statistics

### Programmatic Access

Use the analyzer in your own scripts:

```python
from analyze_logs import read_recycling_logs, analyze_material_distribution

logs = read_recycling_logs()
analysis = analyze_material_distribution(logs)

# Get material distribution
for material, stats in analysis['materials'].items():
    print(f"{material}: {stats['percentage']}%")
```

See [example_usage.py](example_usage.py) for more examples.

## API Endpoints

- `GET /` - Serves the main application page
- `POST /analyze` - Accepts an image and returns recycling analysis

## Troubleshooting

**Issue**: "GEMINI_API_KEY environment variable not set!"
- **Solution**: Make sure you've set the `GEMINI_API_KEY` environment variable

**Issue**: Camera doesn't work on mobile
- **Solution**: Ensure you're accessing the app via HTTPS or localhost, as browsers require secure contexts for camera access

**Issue**: Cannot connect from mobile device
- **Solution**: Make sure both devices are on the same network and you're using the correct IP address

## License

This project was created for ICHack 2026.

## Contributing

Feel free to submit issues or pull requests!