# Puzzle Grid Viewer

A PyQt5 application for viewing images with customizable grid overlays, designed for puzzle piece planning and analysis.

## Features

- **Image Loading**: Open various image formats (PNG, JPG, JPEG, BMP, GIF, TIFF)
- **Grid Overlay**: Customizable X and Y grid dimensions (1-100 squares)
- **Zoom Controls**: 
  - Zoom in/out with buttons or slider (10% to 500%)
  - Fit to Window functionality
  - Actual Size (100%) reset
- **Document Management**:
  - Save puzzle grid configurations as `.puz.json` files
  - Load saved configurations to restore image, grid, and zoom settings
  - Command line support for opening documents directly

## Installation

1. Set up virtual environment:
   ```bash
   setup_venv.bat
   ```

2. Or install manually:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage
```bash
python puzzle_grid_viewer.py
```

### Load Document from Command Line
```bash
python puzzle_grid_viewer.py path/to/document.puz.json
```

### Application Workflow
1. **Load Document** - Open a previously saved puzzle grid configuration
2. **Open Image** - Load a new image and set grid dimensions
3. **Set Grid Dimensions** - Modify grid after image is loaded
4. **Save Document** - Save current state as `.puz.json` file

## Batch Files

- `setup_venv.bat` - Create virtual environment and install dependencies
- `activate_venv.bat` - Activate the virtual environment
- `install_requirements.bat` - Install/reinstall requirements
- `update_pip.bat` - Update pip in the virtual environment

## Document Format

Saved `.puz.json` files contain:
```json
{
  "grid_x": 10,
  "grid_y": 8,
  "image_path": "path/to/image.jpg",
  "zoom_value": 1.25
}
```

## Requirements

- Python 3.6+
- PyQt5

## License

This project is for personal/educational use.
