#!/usr/bin/env python3
import os
import sys
from tqdm import tqdm
import psutil
from pathlib import Path
import logging
import subprocess
from image_audio_2_video import create_video

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_separator(char="-", length=40):
    print(char * length)

def print_system_info():
    """Print system resource information"""
    mem = psutil.virtual_memory()
    print("\nSystem Resources:")
    print_separator()
    print(f"Total Memory: {mem.total/1e9:.1f}GB")
    print(f"Available Memory: {mem.available/1e9:.1f}GB")
    print(f"CPU Cores: {psutil.cpu_count()}")
    print(f"Will use {psutil.cpu_count()//2} cores and 50% of available memory")
    print_separator()

def select_input_folder():
    """Allow user to select an input folder from available options"""
    input_dir = Path("../inputs")
    if not input_dir.exists():
        print(f"Error: Input directory '{input_dir}' not found.")
        sys.exit(1)
        
    subdirs = [d for d in input_dir.iterdir() if d.is_dir()]
    subdirs = sorted(subdirs, key=lambda x: x.name)
    
    if not subdirs:
        print("No subdirectories found in the inputs directory.")
        sys.exit(1)
    
    print("\nAvailable folders:")
    print_separator()
    for i, subdir in enumerate(subdirs, 1):
        print(f"{i:2}. {subdir.name}")
    print_separator()
    
    while True:
        try:
            choice = int(input("Enter the number for the folder to process: "))
            if 1 <= choice <= len(subdirs):
                return subdirs[choice - 1].name
            print("Invalid number. Please try again.")
        except ValueError:
            print("Please enter a valid number.")

def get_chapter_structure(input_path: Path) -> list:
    """
    Get all chapters with their PDF files and slides folders.
    Expected structure:
    - chapter_name/
        - chapter.pdf
        - slides/
            - 00.mp3, 01.mp3, ...
            - 00.png, 01.png, ...
    """
    chapters = []
    
    # Get immediate subdirectories (chapters)
    for chapter_dir in sorted(input_path.iterdir()):
        if not chapter_dir.is_dir():
            continue
            
        # Look for PDF file in chapter directory
        pdf_files = list(chapter_dir.glob('*.pdf'))
        if not pdf_files:
            logger.warning(f"No PDF file found in chapter: {chapter_dir.name}")
            continue
            
        # Check for slides directory
        slides_dir = chapter_dir / 'slides'
        if not slides_dir.exists():
            logger.warning(f"No slides directory found in chapter: {chapter_dir.name}")
            continue
            
        chapters.append({
            'name': chapter_dir.name,
            'path': chapter_dir,
            'pdf': pdf_files[0],  # Take first PDF if multiple exist
            'slides_dir': slides_dir
        })
    
    return sorted(chapters, key=lambda x: x['name'])

def check_files_match(slides_dir: Path) -> bool:
    """Check if number of PNG and MP3 files match in the directory"""
    if not slides_dir.exists():
        return False
        
    files = os.listdir(slides_dir)
    png_files = sorted([f for f in files if f.lower().endswith('.png')])
    mp3_files = sorted([f for f in files if f.lower().endswith('.mp3')])
    
    logger.info(f"Found {len(png_files)} PNG files and {len(mp3_files)} MP3 files")
    
    if len(png_files) != len(mp3_files):
        logger.warning(f"Number of PNG files ({len(png_files)}) doesn't match MP3 files ({len(mp3_files)})")
        return False
        
    # Check sequential numbering
    expected_numbers = [f"{i:02d}" for i in range(len(png_files))]
    png_numbers = [f.split('.')[0] for f in png_files]
    mp3_numbers = [f.split('.')[0] for f in mp3_files]
    
    if png_numbers != expected_numbers or mp3_numbers != expected_numbers:
        logger.warning("Files are not numbered sequentially starting from 00")
        return False
    
    return True

def convert_pdf_to_images(pdf_path: Path, output_dir: Path, dpi: int = 300) -> bool:
    """
    Convert PDF pages to PNG images using ImageMagick.
    Returns True if conversion was successful.
    """
    try:
        # Get number of pages from PDF
        result = subprocess.run(
            ['pdfinfo', str(pdf_path)], 
            capture_output=True, 
            text=True, 
            check=True
        )
        pdf_pages = int([line for line in result.stdout.split('\n') 
                        if 'Pages' in line][0].split()[1])
        
        # Convert PDF pages to PNG
        logger.info(f"Converting {pdf_pages} pages to PNG...")
        convert_errors = []
        
        for i in tqdm(range(pdf_pages), desc="Converting pages", unit="page"):
            output_file = output_dir / f"{i:02d}.png"
            try:
                subprocess.run([
                    'convert',
                    '-density', str(dpi),
                    f"{pdf_path}[{i}]",
                    '-quality', '100',
                    str(output_file)
                ], check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                convert_errors.append(f"Error converting page {i}: {e.stderr.decode()}")

        if convert_errors:
            for error in convert_errors:
                logger.error(error)
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Error converting PDF: {str(e)}")
        return False

def process_folder(folder_name: str):
    """Process all chapters in the given folder"""
    input_path = Path("../inputs") / folder_name
    output_path = Path("../outputs") / folder_name
    
    # Create output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Get chapter structure
    chapters = get_chapter_structure(input_path)
    
    if not chapters:
        print(f"No valid chapters found in {folder_name}")
        return
    
    # Process each chapter
    for chapter in tqdm(chapters, desc="Processing chapters"):
        print(f"\nProcessing chapter: {chapter['name']}")
        print_separator()
        
        # Check if we need to convert the PDF
        if not check_files_match(chapter['slides_dir']):
            logger.info("Files don't match or missing, converting PDF to PNG...")
            if convert_pdf_to_images(chapter['pdf'], chapter['slides_dir']):
                logger.info("Successfully converted PDF to PNGs")
                
                # Check again after conversion
                if not check_files_match(chapter['slides_dir']):
                    logger.error("Number of PNG files still doesn't match MP3 files after conversion")
                    continue
            else:
                logger.error(f"Failed to convert PDF: {chapter['pdf']}")
                continue
        
        # Create video at chapter level
        output_video = output_path / f"{chapter['name']}.mp4"
        if not output_video.exists():
            try:
                create_video(str(chapter['slides_dir']), str(output_video), memory_limit_percent=50)
                print(f"Created video: {output_video}")
            except Exception as e:
                logger.error(f"Error creating video: {e}")
        else:
            print(f"Skipping existing video: {output_video}")

def main():
    print("Chapter-based PDF to Video Converter")
    print_separator("=")
    
    # Display system resources
    print_system_info()
    
    # Select input folder
    folder_name = select_input_folder()
    
    print(f"\nProcessing folder: {folder_name}")
    print_separator()
    
    # Process the selected folder
    process_folder(folder_name)
    
    print("\nProcessing completed.")
    print_separator("=")

if __name__ == "__main__":
    main()
