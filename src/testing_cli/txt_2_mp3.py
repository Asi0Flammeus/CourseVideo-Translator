import os
from pathlib import Path
import requests
import time
from config import HEADERS

def text_to_speech(text_filepath, voice_id, max_retries=10, retry_delay=5):
    text_filepath = Path(text_filepath)
    output_path = text_filepath.with_suffix(".mp3")

    text_to_speak = text_filepath.read_text()
    tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    data = {
        "text": text_to_speak,
        "model_id": "eleven_turbo_v2_5",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.8,
            "style": 0.0,
            "use_speaker_boost": True
        }
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(tts_url, headers=HEADERS, json=data, stream=False)
            response.raise_for_status()  # Raises an HTTPError for bad responses

            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    f.write(chunk)
            # print(f"Audio stream saved successfully to {output_path}")
            return  

        except requests.exceptions.RequestException as e:
            # print(f"Attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                raise Exception(f"Failed after {max_retries} attempts. Last error: {str(e)}")

