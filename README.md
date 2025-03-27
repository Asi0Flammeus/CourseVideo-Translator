# The Quest to automatize the video translation of lectures

Here we define a video lecture, as a video with someone talking about a subject and using a powerpoint presentation.
This type of video is used in every chapter of any courses in PlanB Network, so there's a need to find a way to make the whole process as automated as possible.

## Video Translation workflows

- inputs: video vo + ppt vo of n slides
- process 1: extract n audios from videos vo
- process 2: translate audio
- process 3: translate ppt
- process 4: export ppt into images
- process 5: generate video from n images and n audios, both translated
- output: video translated

## Notes

- each individual building blocks/process can be used indivually 
    - see below sections for the requirements for each one of them
    - the most tricky is the pptx converter

# PPTX to PNG Converter - Requirements and Setup

This tool converts PowerPoint presentations to high-quality PNG images, with one image per slide. It requires several system dependencies to function properly.

## System Requirements

### Required Software

1. **LibreOffice** - For converting PPTX to PDF
   - Ubuntu/Debian: `sudo apt-get install libreoffice`
   - macOS: `brew install libreoffice`
   - Windows: Download from [LibreOffice website](https://www.libreoffice.org/download/download/)

2. **Poppler Utils** (for pdfinfo) - For PDF analysis
   - Ubuntu/Debian: `sudo apt-get install poppler-utils`
   - macOS: `brew install poppler`
   - Windows: Available through Cygwin or MSYS2

3. **ImageMagick** - For PDF to PNG conversion
   - Ubuntu/Debian: `sudo apt-get install imagemagick`
        - if it's not magick version 7 that is installed, I suggest you to compile it from source (see section below)
   - macOS: `brew install imagemagick`
   - Windows: Download from [ImageMagick website](https://imagemagick.org/script/download.php)

### Python Requirements

- Python 3.6 or higher
- Standard library only (no additional Python packages required)

## Installation

1. Install system dependencies:

   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install libreoffice poppler-utils imagemagick

   # macOS (using Homebrew)
   brew install libreoffice poppler imagemagick

   # Windows
   # Install manually from the provided websites
   ```

2. Download the script and make it accessible in your Python path.

## Usage

### As a Python Function

```python
from pptx_converter import convert_pptx_slide

# Basic usage
png_files = convert_pptx_slide("presentation.pptx")

# Custom output directory
png_files = convert_pptx_slide("presentation.pptx", output_dir="output/slides")

# Keep temporary PDF file
png_files = convert_pptx_slide("presentation.pptx", cleanup=False)
```

### Command Line Usage

```bash
python pptx_converter.py presentation.pptx
python pptx_converter.py presentation.pptx --output-dir custom/path
python pptx_converter.py presentation.pptx --keep-pdf
```

## Output

- Creates PNG files named `{original_filename}.{slide_number}.png`
- Default output directory is `slides/` in the same directory as the input file
- Images are generated at 300 DPI with maximum quality
- Temporary PDF file is deleted by default after conversion

## Troubleshooting

1. **LibreOffice errors**: Ensure LibreOffice is properly installed and accessible from command line
2. **ImageMagick policy**: If ImageMagick fails, you might need to update its security policy:
   ```bash
   sudo sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/' /etc/ImageMagick-6/policy.xml
   ```
3. **Path issues**: Ensure all required programs are in your system PATH

## Notes

- The script requires proper permissions to create directories and files
- Processing time depends on the number and complexity of slides
- Memory usage scales with slide resolution and complexity

## Install ImageMagick-7 from source

Remove current imageMagick installation 


```sh
sudo apt remove imagemagick
sudo apt autoremove
```

Install the lastest version 

```sh
# Install build dependencies
sudo apt update
sudo apt install build-essential checkinstall libx11-dev libxext-dev zlib1g-dev libpng-dev libjpeg-dev libfreetype6-dev libxml2-dev

# Download and install ImageMagick 7
cd /tmp
wget https://imagemagick.org/archive/ImageMagick.tar.gz
tar xvzf ImageMagick.tar.gz
cd ImageMagick-*

# Configure and install
./configure
make
sudo checkinstall
```

Update ImageMagick policy to allow PDF operation (crucial step)

```sh
sudo mkdir /etc/ImageMagick-7
sudo cp ./config/policy.xml
sudo nano /etc/ImageMagick-7/policy.xml
```

Add this in your policy map

```xml

  <!-- Enable PDF reading -->
  <policy domain="coder" rights="read|write" pattern="PDF" />
  
  <!-- Other common formats -->
  <policy domain="coder" rights="read|write" pattern="JPEG" />
  <policy domain="coder" rights="read|write" pattern="PNG" />
  <policy domain="coder" rights="read|write" pattern="TIFF" />
  <policy domain="coder" rights="read|write" pattern="GIF" />
```
Replace the line `<policy domain="coder" rights="none" pattern="PDF" />` by `<policy domain="coder" rights="read|write" pattern="PDF" />`

