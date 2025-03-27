import os
import sys
import time
import deepl
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Language mappings
SUPPORTED_LANGUAGES = {
    "cs": "Czech",
    "de": "German",
    "en": "English",
    "es": "Spanish",
    "et": "Estonian",
    "fi": "Finnish",
    "fr": "French",
    "id": "Indonesian",
    "it": "Italian",
    "ja": "Japanese",
    "nb-NO": "Norwegian (Bokmål)",
    "pt": "Portuguese",
    "ru": "Russian",
    "vi": "Vietnamese",
    "zh-Hans": "Chinese (Simplified)"
}

DEEPL_LANGUAGE_MAPPING = {
    "cs": "CS",
    "de": "DE",
    "en": "EN-US",
    "es": "ES",
    "et": "ET",
    "fi": "FI",
    "fr": "FR",
    "id": "ID",
    "it": "IT",
    "ja": "JA",
    "nb-NO": "NB",
    "pt": "PT",
    "ru": "RU",
    "vi": "VI",
    "zh-Hans": "ZH"
}

class TranslationError(Exception):
    """Custom exception for translation errors"""
    pass

class TextTranslator:
    def __init__(self, auth_key: str = None):
        """Initialize translator with DeepL API key"""
        self.auth_key = auth_key or os.getenv('DEEPL_API_KEY')
        if not self.auth_key:
            raise ValueError("DeepL API key is required. Set DEEPL_API_KEY environment variable.")
        
        self.translator = deepl.Translator(self.auth_key)
        
    def translate_text(self, text: str, target_language: str, max_retries=3, retry_delay=5) -> str:
        """Translate text using DeepL API with retry mechanism"""
        if not text.strip():
            return text
            
        deepl_target_lang = DEEPL_LANGUAGE_MAPPING.get(target_language)
        if not deepl_target_lang:
            raise TranslationError(f"Unsupported target language: {target_language}")
            
        for attempt in range(max_retries):
            try:
                result = self.translator.translate_text(text, target_lang=deepl_target_lang)
                return result.text
                
            except Exception as e:
                print(f"Translation attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise TranslationError(f"Translation failed after {max_retries} attempts: {str(e)}")

def prompt_language_selection(prompt_text: str) -> str:
    """Interactive language selection prompt"""
    print(f"\n{prompt_text}")
    for code, name in sorted(SUPPORTED_LANGUAGES.items()):
        print(f"{code}: {name}")
    
    while True:
        lang = input("\nEnter language code: ").lower()
        if lang in SUPPORTED_LANGUAGES:
            return lang
        print("Invalid language code. Please try again.")

def main():
    """CLI entry point"""
    base_path = "../../../vault/DBxPBN/workspace/assets/educational-content/courses/Free/"
    
    try:
        # Get and sort the folders in the base path
        folders = [f for f in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, f))]
        folders.sort()
        
        # Print available folders
        print("\n=== Text Translator ===")
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
        
        # Language selection
        source_lang = prompt_language_selection("Select source language:")
        target_lang = prompt_language_selection("Select target language:")
        
        # Define source and target folder paths
        source_folder_path = os.path.join(base_path, selected_folder, f"translation/{source_lang}/v001")
        target_folder_path = os.path.join(base_path, selected_folder, f"translation/{target_lang}/v001")
        
        # Check if source folder exists
        if not os.path.exists(source_folder_path):
            raise Exception(f"Source folder does not exist: {source_folder_path}")
        
        # Create target folder if it doesn't exist
        os.makedirs(target_folder_path, exist_ok=True)
        
        # Show confirmation
        print("\nPlease confirm the following paths:")
        print(f"\nSource folder: {source_folder_path}")
        print(f"Target folder: {target_folder_path}")
        
        confirm = input("\nProceed with translation? (y/n): ").lower()
        if confirm != 'y':
            print("Translation cancelled.")
            return
        
        # Initialize translator
        translator = TextTranslator()
        
        # Get all subfolders
        subfolders = [f for f in os.listdir(source_folder_path) if os.path.isdir(os.path.join(source_folder_path, f))]
        subfolders.sort()
        
        # Process each subfolder
        for subfolder in subfolders:
            source_slides_path = os.path.join(source_folder_path, subfolder, "slides")
            target_slides_path = os.path.join(target_folder_path, subfolder, "slides")
            
            # Check if source slides folder exists
            if not os.path.exists(source_slides_path):
                print(f"\nSkipping {subfolder} - no slides folder found")
                continue
                
            # Create target slides folder
            os.makedirs(target_slides_path, exist_ok=True)
            
            # Get all TXT files in the slides folder
            txt_files = [f for f in os.listdir(source_slides_path) if f.lower().endswith('.txt')]
            txt_files.sort()
            
            if not txt_files:
                print(f"No TXT files found in {subfolder}/slides")
                continue
            
            print(f"\nProcessing {subfolder}...")
            
            # Process each TXT file
            for txt_file in txt_files:
                print(f"\nTranslating: {txt_file}")
                
                # Construct input and output paths
                input_path = os.path.join(source_slides_path, txt_file)
                output_path = os.path.join(target_slides_path, txt_file)
                
                # Check if translated file already exists
                if os.path.exists(output_path):
                    print(f"Skipping {txt_file} - translation already exists at: {output_path}")
                    continue
                
                try:
                    # Read source file
                    with open(input_path, 'r', encoding='utf-8') as f:
                        source_text = f.read()
                    
                    # Translate text
                    translated_text = translator.translate_text(source_text, target_lang)
                    
                    # Save translated text
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(translated_text)
                    
                    print(f"Translation completed for {txt_file}")
                    print(f"Saved to: {output_path}")
                    
                except Exception as e:
                    print(f"Error translating {txt_file}: {str(e)}")
                    continue
                    
    except TranslationError as e:
        print(f"\nTranslation error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

