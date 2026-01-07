# FileSplitter

A web-based CSV file splitter and cleaner tool. Upload large CSV files and get back a ZIP containing smaller, cleaned CSV chunks.

## Features

- **CSV Splitting**: Split large CSV files into smaller chunks with a configurable number of rows per file
- **Blank Row Removal**: Automatically removes completely blank rows from the output files
- **Header Preservation**: Each split file includes the original header row
- **Web UI**: Simple, clean web interface for easy file processing
- **ZIP Download**: All processed files are packaged into a single downloadable ZIP

## Installation

1. Clone this repository:
```bash
git clone https://github.com/YOUR_USERNAME/filesplitter.git
cd filesplitter
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the Flask application:
```bash
python app.py
```

2. Open your browser and navigate to:
```
http://127.0.0.1:5000/
```

3. Upload a CSV file and specify the number of rows per output file (default: 700,000)

4. Click "Split & Download ZIP" to process and download your files

## How It Works

1. **Upload**: The CSV file is uploaded through the web interface
2. **Split**: The file is split into multiple CSV files, each containing up to the specified number of rows (plus header)
3. **Clean**: Blank rows are removed from each split file
4. **Package**: All processed files are zipped together
5. **Download**: The ZIP file is automatically downloaded to your browser

## Requirements

- Python 3.7+
- Flask 3.0+

## License

MIT License
