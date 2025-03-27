#!/usr/bin/env python3
import subprocess
from pathlib import Path
from tqdm import tqdm

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
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to get PDF page count: {e.stderr}")
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
                'convert',  # ImageMagick command
                '-density', str(dpi),
                f"{pdf_path}[{i}]",
                '-quality', '100',
                str(output_file)
            ], check=True, capture_output=True)
            png_files.append(str(output_file))
        except subprocess.CalledProcessError as e:
            convert_errors.append(f"Error converting page {i+1}: {e.stderr.decode()}")

    # Report any conversion errors
    if convert_errors:
        print("\nWarning: Some pages failed to convert:")
        for error in convert_errors:
            print(f"  - {error}")

    return png_files

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python3 pdf2png.py path_to_pdf")
        sys.exit(1)
        
    try:
        png_files = convert_pdf_to_images(sys.argv[1])
        print(f"\nSuccessfully converted to PNG files:")
        for png_file in png_files:
            print(f"  - {png_file}")
    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)
