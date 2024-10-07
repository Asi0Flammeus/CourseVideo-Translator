import os
import hashlib

from config import voice_ids
from image_audio_2_video import create_video
from initial_translation import convert_pptx_to_png, print_separator, select_directory, select_source_version, language_codes
from txt_2_mp3 import text_to_speech


ROOT_DIR = "../test/"  # Replace this with your actual root directory path

def calculate_sha256(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def decrement_version(path):
    parts = path.split(os.sep)
    for i, part in enumerate(parts):
        if part.startswith('v') and part[1:].isdigit():
            current_version = int(part[1:])
            new_version = max(current_version - 1, 1)  # Ensure version doesn't go below 1
            parts[i] = f'v{new_version:03d}'
            return os.sep.join(parts)
    return path  # Return original path if no version found

def file_has_changed(filepath):
    previous_version_path = decrement_version(filepath)
    if not os.path.exists(filepath) or not os.path.exists(previous_version_path):
        return False, f"One or both files do not exist: \n{filepath}\n{previous_version_path}"

    current_hash = calculate_sha256(filepath)
    previous_hash = calculate_sha256(previous_version_path)

    are_identical = current_hash == previous_hash
    return not(are_identical)

def get_available_languages(folder_path):
    return [lang for lang in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, lang)) and lang in language_codes]

def create_numbered_languages(available_langs):
    return list(enumerate([(lang, language_codes[lang]) for lang in available_langs], 1))

def print_languages(numbered_langs):
    print("\nAvailable languages:")
    print_separator()
    for number, (code, name) in numbered_langs:
        print(f"{number:2}. {name:20} ({code})")
    print_separator()

def get_language_choice(numbered_langs, prompt, default=None):
    while True:
        if default:
            prompt = f"{prompt} (default: {default}): "
        try:
            user_input = input(prompt).strip()
            if default and user_input == "":
                return default

            choice = int(user_input)
            if 1 <= choice <= len(numbered_langs):
                return numbered_langs[choice - 1][1][0]  # Return the language code
            print("Invalid number. Please try again.")
        except (ValueError, IndexError):
            print("Please enter a valid number.")

def select_language(folder_path):
    available_langs = get_available_languages(folder_path)
    if not available_langs:
        print("No valid language folders found.")
        return None

    numbered_langs = create_numbered_languages(available_langs)
    print_languages(numbered_langs)

    lang = get_language_choice(numbered_langs, "\nEnter the number for the target language: ")
    return lang

def mp4_exists(item_path):
    return any(item.lower().endswith('.mp4') for item in os.listdir(item_path))

if __name__ == "__main__":

    print("This script will let you generate a reviewed version!")
    print_separator("=")
    selected_dir = select_directory(ROOT_DIR)
    available_langs = get_available_languages(selected_dir)
    numbered_languages = create_numbered_languages(available_langs)
    print_separator()
    print_languages(numbered_languages)
    lang = get_language_choice(numbered_languages, "\nEnter the number for the language: ")
    version = select_source_version(selected_dir, lang)
    update_version_path = os.path.join(selected_dir, lang, version)
    items = os.listdir(update_version_path)

    for item in sorted(items):
        item_path = os.path.join(update_version_path, item)
        if os.path.isdir(item_path):
            print_separator("=")
            print(f"Processing chapter {item}...")
            
            if not mp4_exists(item_path):
                PPTX_NAME = f"{item}.pptx"
                pptx_path = os.path.join(item_path, PPTX_NAME)

                print()
                print("Processing pptx...")
                print_separator(" ")
                print("Exporting pptx...")
                convert_pptx_to_png(pptx_path)

                print_separator(" ")
                print("Processing transcripts...")
                slide_path = os.path.join(item_path, "slides/")
                slide_items = os.listdir(slide_path)

                for slide_item in sorted(slide_items):
                    slide_item_path = os.path.join(slide_path, slide_item)
                    
                    if slide_item.lower().endswith('.txt'):
                        print(f"Generating audio for {slide_item}...")
                        voice = slide_item.split('.')[-2].split('_')[-1]
                        text_to_speech(slide_item_path, voice_ids[voice])
                        
                video_path = os.path.join(item_path, f"{item}.mp4")
                print_separator(" ")
                print("Exporting chapter video...")
                create_video(slide_path, video_path)
            else:
                print(f"Skipping chapter {item} as MP4 file already exists.")

        print_separator("=")
    print_separator(" ")
    course = os.path.basename(selected_dir)
    print(f"The {version} of {course} in {lang} has been fully generated!")
