# Sound by Mood - Music Explorer

A music recommendation system that uses AI to find music based on natural language descriptions. The system combines Spotify and YouTube data with Google's Gemini AI to provide intelligent music recommendations.

## Quick Start - Run the Notebook Locally

### 1. Set Up Virtual Environment

```bash
# Navigate to project directory
cd /path/to/soundbymood

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows
```

### 2. Install Dependencies

```bash
# Install required packages
pip install -r requirements.txt
```

### 3. Set Up API Credentials

Create a `.env` file in the project root:

```bash
# Create .env file
cat > .env << EOF
# Spotify API credentials
SPOTIFY_CLIENT_ID=your_spotify_client_id_here
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret_here

# Google AI API key
GOOGLE_API_KEY=your_google_api_key_here
EOF
```

Then edit the `.env` file and add your actual API credentials:

**Spotify API:**
- Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
- Create a new app
- Copy the Client ID and Client Secret

**Google AI API:**
- Go to [Google AI Studio](https://aistudio.google.com/)
- Get an API key for Gemini

### 4. Prepare Data

Ensure your data is in the correct location:

```
data/
├── input/
│   └── Spotify_Youtube.csv    # Main dataset (required)
├── artists.csv                # Enriched artist data (optional)
└── tracks.csv                 # Enriched track data (optional)
```

### 5. Modify the Notebook

You'll need to make a few changes to the notebook to work locally:

**Replace the Kaggle secrets import:**
```python
# Replace this line:
from kaggle_secrets import UserSecretsClient

# With these lines:
import os
from dotenv import load_dotenv
load_dotenv()

# Then replace all UserSecretsClient().get_secret() calls with:
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
```

**Update file paths:**
```python
# Replace Kaggle paths:
spotify_youtube = pd.read_csv('/kaggle/input/spotify-and-youtube/Spotify_Youtube.csv')

# With local paths:
spotify_youtube = pd.read_csv('data/input/Spotify_Youtube.csv')
```

**Update output paths:**
```python
# Replace:
artists_df.to_csv('/kaggle/working/artists.csv', index=False)

# With:
artists_df.to_csv('data/artists.csv', index=False)
```

### 6. Run the Notebook

```bash
# Make sure your virtual environment is activated
jupyter notebook notebooks/youtube-music-exploration.ipynb
```

### 7. Deactivate Virtual Environment (when done)

```bash
deactivate
```

## Example Queries

- "foggy dusk san francisco evening"
- "music for a period drama set in elizabethan england"
- "upbeat workout music"
- "calm meditation background"
- "romantic dinner jazz"
- "epic battle scene soundtrack"

## Troubleshooting

### Common Issues

1. **Missing API Credentials**: Ensure all three API keys are set in your `.env` file
2. **Data File Not Found**: Make sure `Spotify_Youtube.csv` is in `data/input/`
3. **Import Errors**: Make sure your virtual environment is activated and run `pip install -r requirements.txt`
4. **Kaggle-specific code**: Remember to replace Kaggle secrets and file paths as shown above

### Getting Help

If you encounter issues:
1. Check that your virtual environment is activated
2. Verify your API credentials are valid
3. Ensure the data file is in the correct location
4. Check the console output for specific error messages

## File Structure

```
soundbymood/
├── data/
│   ├── input/
│   │   └── Spotify_Youtube.csv
│   ├── artists.csv
│   └── tracks.csv
├── notebooks/
│   └── youtube-music-exploration.ipynb
├── requirements.txt
├── .env
└── README.md
```

## License

This project is for educational and research purposes. Please respect the terms of service for Spotify and Google AI APIs. 