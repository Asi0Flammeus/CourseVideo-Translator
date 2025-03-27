import os
import subprocess
from pathlib import Path
from tqdm import tqdm
import time
import shutil

def setup_wine_environment():
    """Setup Wine environment with necessary components"""
    wine_prefix = Path.home() / '.wine_officetopdf'
    os.environ['DISPLAY'] = ':0'
    os.environ['WINEDEBUG'] = '-all'
    os.environ['WINEPREFIX'] = str(wine_prefix)
    os.environ['WINEARCH'] = 'win32'  # Use 32-bit architecture
    
    # Remove existing prefix if it exists
    if wine_prefix.exists():
        shutil.rmtree(wine_prefix)
    
    print("Setting up new Wine environment...")
    
    # Initialize wine prefix
    subprocess.run(['wineboot', '--init'], 
                  env=os.environ, 
                  stdout=subprocess.DEVNULL,
                  stderr=subprocess.DEVNULL)
    time.sleep(5)
    
    # Install required Windows components
    print("Installing required Windows components (this may take a few minutes)...")
    subprocess.run(['winetricks', '-q', 'dotnet40'], 
                  env=os.environ,
                  stdout=subprocess.DEVNULL,
                  stderr=subprocess.DEVNULL)
    
    return wine_prefix

def convert_pptx_to_images(pptx_path: str, output_dir: str = None, cleanup: bool = True, dpi: int = 300) -> list:
    """
    Convert PowerPoint slides to PNG images using Wine + OfficeToPDF and ImageMagick.
    """
    # Validate input file exists
    pptx_path = Path(pptx_path).resolve()
    if not pptx_path.exists():
        raise FileNotFoundError(f"PowerPoint file not found: {pptx_path}")

    # Setup output directory
    if output_dir is None:
        output_dir = pptx_path.parent / "slides"
    else:
        output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Setup Wine
    wine_prefix = setup_wine_environment()

    # Download OfficeToPDF if not present
    officetopdf_path = Path.cwd() / 'OfficeToPDF.exe'
    if not officetopdf_path.exists():
        print("\nDownloading OfficeToPDF...")
        subprocess.run([
            'wget',
            '-O', str(officetopdf_path),
            'https://github.com/cognidox/OfficeToPDF/releases/download/v1.9.0.2/OfficeToPDF.exe'
        ], check=True)

    # Convert PPTX to PDF
    pdf_path = output_dir / f"{pptx_path.stem}.pdf"
    
    try:
        print("\nConverting PPTX to PDF...")
        print(f"Converting: {pptx_path} -> {pdf_path}")
        
        result = subprocess.run(
            ['wine', str(officetopdf_path), str(pptx_path), str(pdf_path)],
            env=os.environ,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0 or not pdf_path.exists():
            print("\nConversion Debug Info:")
            print(f"Return Code: {result.returncode}")
            print(f"StdOut: {result.stdout}")
            print(f"StdErr: {result.stderr}")
            raise RuntimeError("PDF file was not created. See debug info above.")
            
    except Exception as e:
        raise RuntimeError(f"Failed to convert PPTX to PDF: {str(e)}")

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
    
    for i in tqdm(range(pdf_pages), desc="Converting slides", unit="slide"):
        output_file = output_dir / f"slide_{i:03d}.png"
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
            convert_errors.append(f"Error converting page {i}: {e.stderr.decode()}")

    # Report any conversion errors
    if convert_errors:
        print("\nWarning: Some pages failed to convert:")
        for error in convert_errors:
            print(f"  - {error}")

    # Cleanup
    if cleanup and pdf_path.exists():
        try:
            pdf_path.unlink()
        except Exception as e:
            print(f"\nWarning: Failed to remove temporary PDF file: {str(e)}")

    return png_files

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python3 converter.py path_to_pptx")
        sys.exit(1)
        
    try:
        # Kill any existing wine processes
        subprocess.run(['wineserver', '-k'], 
                     stdout=subprocess.DEVNULL, 
                     stderr=subprocess.DEVNULL)
        
        png_files = convert_pptx_to_images(sys.argv[1])
        print(f"\nSuccessfully converted to PNG files:")
        for png_file in png_files:
            print(f"  - {png_file}")
    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)
