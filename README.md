# Auto PDF Signer

A Python script that automatically signs PDF documents by filling form fields or placing signatures and entity data in appropriate locations.

## Features

- **Form Field Detection**: Automatically detects and fills AcroForm fields in PDFs
- **Signature Placement**: Places signature images in designated signature fields
- **Fallback Mode**: When no form fields are available, intelligently places signatures and text based on content analysis
- **PDF Flattening**: Converts filled PDFs to non-editable format
- **Modular Design**: Clean, maintainable code with separate functions for each operation

## Requirements

- Python 3.7+
- PyMuPDF (for PDF processing)
- ReportLab (for PDF creation)
- Pillow (for image handling)

## Installation

1. Clone or download the script files
2. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Input Files Required

1. **input.pdf** - The PDF document to be signed (e.g., NDA, contract)
2. **entity.txt** - Key-value pairs with entity information:
   ```
   Company=WaltCo Ltd.
   Address=One Microsoft Way, Redmond, WA 98052, US
   Name=John Doe
   Title=CEO
   ```
3. **signature.jpg** - Digital signature image file

### Running the Script

```bash
python auto-pdf-signer.py
```

The script will generate `signed_output.pdf` with the signature and entity data applied.

## How It Works

### 1. Form Field Processing
- Detects AcroForm fields in the PDF
- Maps field names to entity data using intelligent matching
- Fills text fields with appropriate values
- Places signature images in signature fields

### 2. Fallback Mode
When no form fields are found:
- Searches PDF text for signature-related keywords
- Places signature near detected keywords or in bottom-left of last page
- Adds entity data as text near the signature

### 3. PDF Flattening
- Converts the filled PDF to a flattened, non-editable format
- Ensures signatures and data cannot be modified

## Code Structure

### Main Functions

- `load_entity_data()` - Reads and parses entity.txt file
- `fill_form_fields()` - Fills AcroForm fields with entity data
- `place_signature()` - Places signature in designated signature fields
- `fallback_placement()` - Handles PDFs without form fields
- `flatten_pdf()` - Converts PDF to non-editable format

### Class: AutoPDFSigner

The main class that orchestrates the entire signing process:

```python
signer = AutoPDFSigner("input.pdf", "entity.txt", "signature.jpg")
signer.process_pdf("signed_output.pdf")
```

## Field Mapping

The script intelligently maps form field names to entity data:

| Field Keywords | Entity Keys Matched |
|----------------|-------------------|
| name, company, entity | Company, Name |
| address, location | Address |
| title, position | Title |
| date | Date |

## Error Handling

- Validates required input files exist
- Gracefully handles missing or invalid form fields
- Provides detailed error messages and logging
- Continues processing even if some operations fail

## Examples

### With Form Fields
If your PDF has form fields named "CompanyName", "Address", etc., they will be automatically filled with matching data from entity.txt.

### Without Form Fields
If no form fields exist, the script will:
1. Search for signature-related text
2. Place signature near found keywords
3. Add entity data as text below the signature

## Troubleshooting

### Common Issues

1. **Missing Dependencies**: Install all packages from requirements.txt
2. **Virtual Environment**: Use a virtual environment to avoid package conflicts
3. **File Permissions**: Ensure read/write access to input and output files
4. **Image Format**: Signature should be in JPG, PNG, or other PIL-supported formats

### Debug Output

The script provides verbose output showing:
- Entity data loaded
- Form fields found and filled
- Signature placement locations
- Processing steps and any errors

## License

This script is provided as-is for educational and practical use. Modify as needed for your specific requirements.

