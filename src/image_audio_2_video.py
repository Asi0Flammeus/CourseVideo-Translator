#!/usr/bin/env python3
import os
import re
import psutil
import resource
import gc
import logging
from pathlib import Path
import subprocess
from threading import Lock
from tqdm import tqdm
from moviepy.video.VideoClip import ImageClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.compositing.concatenate import concatenate_videoclips

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def convert_pdf_to_images(pdf_path: str, output_dir: str = None, dpi: int = 300) -> list:
    """
    Convert PDF pages to PNG images using ImageMagick.
    
    Args:
        pdf_path (str): Path to the input PDF file
        output_dir (str, optional): Directory to save PNG files. Defaults to 'slides' subfolder
        dpi (int, optional): Resolution of output images. Defaults to 300
    
    Returns:
        list: List of paths to generated PNG files
    """
    # Validate input file exists
    pdf_path = Path(pdf_path).resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    # Setup output directory
    if output_dir is None:
        output_dir = pdf_path.parent / "slides"
    else:
        output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get number of pages from PDF
    try:
        result = subprocess.run(
            ['pdfinfo', str(pdf_path)], 
            capture_output=True, 
            text=True, 
            check=True
        )
        pdf_pages = int([line for line in result.stdout.split('\n') 
                        if 'Pages' in line][0].split()[1])
    except Exception as e:
        raise RuntimeError(f"Failed to get PDF page count: {str(e)}")

    # Convert PDF pages to PNG
    print(f"\nConverting {pdf_pages} pages to PNG...")
    png_files = []
    convert_errors = []
    
    for i in tqdm(range(pdf_pages), desc="Converting pages", unit="page"):
        output_file = output_dir / f"{i+1:02d}.png"
        try:
            subprocess.run([
                'convert',
                '-density', str(dpi),
                f"{pdf_path}[{i}]",
                '-quality', '100',
                str(output_file)
            ], check=True, capture_output=True)
            png_files.append(str(output_file))
        except subprocess.CalledProcessError as e:
            convert_errors.append(f"Error converting page {i+1}: {e.stderr.decode()}")

    if convert_errors:
        print("\nWarning: Some pages failed to convert:")
        for error in convert_errors:
            print(f"  - {error}")

    return png_files

def check_files_match(directory):
    """Check if number of PNG and MP3 files match in the directory"""
    files = os.listdir(directory)
    png_files = sorted([f for f in files if f.lower().endswith('.png')])
    mp3_files = sorted([f for f in files if f.lower().endswith('.mp3')])
    
    logger.info(f"Found {len(png_files)} PNG files and {len(mp3_files)} MP3 files")
    
    return len(png_files) == len(mp3_files) and len(png_files) > 0

def create_video(directory, output_path, memory_limit_percent=50):
    """Create video from images and audio files"""
    try:
        # Get sorted files
        files = sorted(os.listdir(directory))
        
        # Filter and sort files
        image_files = sorted([f for f in files if f.lower().endswith('.png')])
        audio_files = sorted([f for f in files if f.lower().endswith('.mp3')])
        
        logger.info(f"Found {len(image_files)} images and {len(audio_files)} audio files")
        
        if not image_files or not audio_files:
            raise ValueError(f"No image or audio files found in {directory}")
        if len(image_files) != len(audio_files):
            raise ValueError(f"Unequal number of images ({len(image_files)}) and audio files ({len(audio_files)})")

        # Create clips list
        clips = []
        
        # Process each pair of files
        for img, aud in zip(image_files, audio_files):
            image_path = os.path.join(directory, img)
            audio_path = os.path.join(directory, aud)
            
            logger.info(f"Processing image: {img} with audio: {aud}")
            
            try:
                # Load audio first to get duration
                audio = AudioFileClip(audio_path)
                duration = audio.duration
                
                # Create video clip
                image = ImageClip(image_path)
                video = image.set_duration(duration + 0.5)  # Add small buffer
                video = video.set_audio(audio)
                
                clips.append(video)
                
                logger.info(f"Successfully created clip for {img} with duration {duration}")
                
            except Exception as e:
                logger.error(f"Error processing {img} and {aud}: {str(e)}")
                raise
        
        if not clips:
            raise ValueError("No clips were created successfully")
            
        logger.info(f"Created {len(clips)} clips, proceeding to concatenation")
        
        # Concatenate all clips
        final_clip = concatenate_videoclips(clips)
        
        # Write final video
        final_clip.write_videofile(
            output_path,
            codec='libx264',
            fps=1,
            threads=max(1, psutil.cpu_count() // 2),
            ffmpeg_params=[
                '-preset', 'ultrafast',
                '-crf', '28'
            ]
        )
        
        # Cleanup
        final_clip.close()
        for clip in clips:
            clip.close()
        gc.collect()
            
    except Exception as e:
        logger.error(f"Error in create_video: {str(e)}")
        raise

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python3 slides_to_video.py path_to_pdf output_video.mp4")
        sys.exit(1)
        
    try:
        pdf_path = sys.argv[1]
        output_video = sys.argv[2]
        slides_dir = os.path.join(os.path.dirname(pdf_path), "slides")
        
        # Check if we need to convert the PDF
        if not check_files_match(slides_dir):
            logger.info("Files don't match or missing, converting PDF to PNG...")
            convert_pdf_to_images(pdf_path)
            
            # Check again after conversion
            if not check_files_match(slides_dir):
                raise ValueError("Number of PNG files still doesn't match MP3 files after conversion")
        
        # Create the video
        logger.info("Creating video...")
        create_video(slides_dir, output_video)
        logger.info(f"Video created successfully: {output_video}")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)
