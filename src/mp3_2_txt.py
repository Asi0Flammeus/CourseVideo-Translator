import os
import re
import time
import requests
import openai
import tiktoken
from pydub import AudioSegment
from dotenv import load_dotenv
from openai import RateLimitError, Timeout, APIError

def num_tokens_from_string(string: str, encoding_name: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens

def split_text_into_chunks(text: str, MAX_TOKENS: int = 1000,
        ENCODING_NAME: str = "cl100k_base", transcript: bool = False) -> list:
    """
    Splits the input text into chunks with a maximum token count, preserving original layout.

    Args:
        text (str): The input text to be split.
        MAX_TOKENS (int): The maximum token count for each chunk (default: 1000).
        ENCODING_NAME (str): The encoding name to be used for tokenization (default: "cl100k_base").

    Returns:
        list: The list of chunks.
    """
    chunks = []
    current_chunk = ""

    if transcript:
        sentences = re.split(r'\.\s+', text)  
        for sentence in sentences:
            sentence_tokens = num_tokens_from_string(sentence, ENCODING_NAME)
            if sentence_tokens + num_tokens_from_string(current_chunk, ENCODING_NAME) <= MAX_TOKENS:
                current_chunk += sentence + ". "
            else:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
    else:
        paragraphs = text.splitlines()  
        for paragraph in paragraphs:
            paragraph_tokens = num_tokens_from_string(paragraph, ENCODING_NAME)

            if paragraph_tokens + num_tokens_from_string(current_chunk, ENCODING_NAME) <= MAX_TOKENS:
                current_chunk += paragraph + "\n"  
            else:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph

    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

class TranscriptionModel:
    """
    This class provides functionality to transcribe audio files using OpenAI's Whisper API
    """

    AUDIO_EXTENSIONS = ('.wav', '.mp3', '.m4a', '.webm', '.mp4', '.mpga', '.mpeg')
    MAX_SUPPORTED_AUDIO_SIZE_MB = 20  

    load_dotenv()
    openai.api_key = os.getenv("API_KEY_OPENAI")

    def __init__(self, output_dir):
        self.transcript = None
        self.original_audio_file = []
        self.audio_files = []
        self.output_dir = output_dir

    def save_text(self, text: str, suffix: str):
        """
        Save a text to the output folder with a specific suffix.

        Args:
            text (str): The text to be saved.
            suffix (str): The suffix to use for the saved text file name.
        """

        audio_file_name = os.path.basename(self.original_audio_file[0])
        os.makedirs(self.output_dir, exist_ok=True)
        file_path = os.path.join(self.output_dir, os.path.splitext(audio_file_name)[0] + f"{suffix}.txt")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)


    def load_audio(self, file_path):
        """
        Loads an audio file from the specified file path.

        Args:
            file_path (str): The path to the audio file.

        Raises:
            ValueError: If the file path is not valid or does not have a valid audio file extension.
        """
        if not os.path.isfile(file_path) or not file_path.endswith(self.AUDIO_EXTENSIONS):
            raise ValueError(f"Invalid audio file: {file_path}")

        self.transcript = None
        self.original_audio_file = []
        self.audio_files = []

        self.original_audio_file.append(file_path)

        audio_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if audio_size_mb > self.MAX_SUPPORTED_AUDIO_SIZE_MB:
            chunk_size_ms = self.MAX_SUPPORTED_AUDIO_SIZE_MB * 1024 * 1024 * 8 // 1000
            audio = AudioSegment.from_file(file_path)
            duration_ms = len(audio)

            for i in range(0, duration_ms, chunk_size_ms):
                chunk = audio[i:i + chunk_size_ms]
                chunk_file_path = f"{os.path.splitext(file_path)[0]}_{i // chunk_size_ms}{os.path.splitext(file_path)[1]}"
                chunk.export(chunk_file_path, format=file_path.split('.')[-1])
                self.audio_files.append(chunk_file_path)
        else:
            self.audio_files.append(file_path)

    def transcribe_audio(self, max_retries=10, retry_delay=5):
        """
        Transcribes the audio data using OpenAI's Whisper API with error handling and retries.

        Args:
            max_retries (int): Maximum number of retry attempts (default: 10)
            retry_delay (int): Delay in seconds between retry attempts (default: 5)

        Returns:
            str: The transcript of the audio data in text format.

        Raises:
            Exception: If transcription fails after all retry attempts.
        """
        if not self.audio_files:
            raise ValueError("No audio files have been loaded.")

        file_path = self.audio_files[0]
        
        for attempt in range(max_retries):
            try:
                with open(file_path, "rb") as audio_file:
                    # Updated to use the new client.audio.transcribe method
                    client = openai.OpenAI()
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file
                    )
                
                # Extract the transcript text
                transcript_text = transcript.text
                return transcript_text

            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise Exception(f"Transcription failed after {max_retries} attempts. Last error: {str(e)}")


    def transcribe_multiple_chunks_audio(self, max_retries=10, retry_delay=5):
        """
        Transcribes all the audio chunks into a single transcript with error handling and retries.

        Args:
            max_retries (int): Maximum number of retry attempts (default: 10)
            retry_delay (int): Delay in seconds between retry attempts (default: 5)

        Returns:
            str: The transcript of the audio data in text format.

        Raises:
            Exception: If transcription fails after all retry attempts for any chunk.
        """
        if not self.audio_files:
            raise ValueError("No audio files have been loaded.")

        sub_audio_file = len(self.audio_files) > 1

        file_path = self.original_audio_file[0]
        transcript_file = f"./outputs/{os.path.splitext(os.path.basename(file_path))[0]}_French_transcript.txt"

        if os.path.exists(transcript_file):
            with open(transcript_file, 'r') as f:
                transcript_text = f.read()
            self.transcript = transcript_text
            while self.audio_files:
                if sub_audio_file:
                    os.remove(self.audio_files[0])
                self.audio_files.pop(0)
            return transcript_text

        transcript_texts = []

        while self.audio_files:
            try:
                transcript_text = self.transcribe_audio(max_retries, retry_delay)
                transcript_texts.append(transcript_text)
            except Exception as e:
                raise Exception(f"Failed to transcribe audio chunk: {str(e)}")
            finally:
                if sub_audio_file:
                    os.remove(self.audio_files[0])
                self.audio_files.pop(0)

        self.transcript = "".join(transcript_texts)
        self.save_text(self.transcript, "")

        return self.transcript

    def load_and_transcribe_audio(self, audio_file, max_retries=10, retry_delay=5):
        self.load_audio(audio_file)
        transcript = self.transcribe_multiple_chunks_audio(max_retries, retry_delay)
        return transcript
def main():
    # Set the base path
    base_path = "../../../vault/DBxPBN/workspace/assets/educational-content/courses/Free/"
    
    # Get and sort the folders in the base path
    try:
        folders = [f for f in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, f))]
        folders.sort()
        
        # Print available folders
        print("\nAvailable folders:")
        for i, folder in enumerate(folders, 1):
            print(f"{i}. {folder}")
            
        # Get user input for folder selection
        while True:
            try:
                selection = int(input("\nEnter the number of the folder to process (1-{}): ".format(len(folders))))
                if 1 <= selection <= len(folders):
                    break
                print("Invalid selection. Please try again.")
            except ValueError:
                print("Please enter a valid number.")
        
        selected_folder = folders[selection-1]
        folder_path = os.path.join(base_path, selected_folder, "translation/fr/v001")
        
        # Get all subfolders
        subfolders = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]
        subfolders.sort()
        
        # Process each subfolder
        for subfolder in subfolders:
            slides_path = os.path.join(folder_path, subfolder, "slides")
            
            # Check if slides folder exists
            if not os.path.exists(slides_path):
                print(f"\nSkipping {subfolder} - no slides folder found")
                continue
                
            print(f"\nProcessing {subfolder}...")
            
            # Get all MP3 files in the slides folder
            mp3_files = [f for f in os.listdir(slides_path) if f.lower().endswith('.mp3')]
            mp3_files.sort()
            
            if not mp3_files:
                print(f"No MP3 files found in {subfolder}/slides")
                continue
            
            # Process each MP3 file
            transcriber = TranscriptionModel(slides_path)
            for mp3_file in mp3_files:
                transcript_file = os.path.join(slides_path, f"{os.path.splitext(mp3_file)[0]}.txt")
                
                # Check if transcript already exists
                if os.path.exists(transcript_file):
                    print(f"Skipping {mp3_file} - transcript already exists")
                    continue
                
                print(f"Transcribing: {mp3_file}")
                try:
                    mp3_path = os.path.join(slides_path, mp3_file)
                    transcript = transcriber.load_and_transcribe_audio(mp3_path)
                    print(f"Transcription completed for {mp3_file}")
                except Exception as e:
                    print(f"Error transcribing {mp3_file}: {str(e)}")
                    continue
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()

