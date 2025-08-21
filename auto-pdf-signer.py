#!/usr/bin/env python3
"""
Auto PDF Signer Script

This script automatically signs PDF documents by:
1. Reading entity data from a text file
2. Filling form fields if available
3. Placing signatures in signature fields or fallback locations
4. Flattening the PDF to make it non-editable
"""

import os
import sys
from typing import Dict, Tuple, List, Optional
import re
from pathlib import Path

try:
    import fitz  # PyMuPDF
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.utils import ImageReader
    from PIL import Image
except ImportError as e:
    print(f"Error: Required packages not installed. Please run: pip install PyMuPDF reportlab Pillow")
    print(f"Missing package: {e}")
    sys.exit(1)


class AutoPDFSigner:
    """Main class for handling PDF signing operations."""
    
    def __init__(self, input_pdf: str, entity_file: str, signature_image: str):
        self.input_pdf = input_pdf
        self.entity_file = entity_file
        self.signature_image = signature_image
        self.entity_data = {}
        self.pdf_doc = None
        
    def load_entity_data(self) -> Dict[str, str]:
        """
        Load entity data from text file with key=value pairs.
        
        Returns:
            Dictionary containing entity data
        """
        entity_data = {}
        
        try:
            with open(self.entity_file, 'r', encoding='utf-8') as file:
                for line_num, line in enumerate(file, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                        
                    if '=' in line:
                        key, value = line.split('=', 1)
                        entity_data[key.strip()] = value.strip()
                    else:
                        print(f"Warning: Invalid format on line {line_num}: {line}")
                        
        except FileNotFoundError:
            print(f"Error: Entity file '{self.entity_file}' not found.")
            sys.exit(1)
        except Exception as e:
            print(f"Error reading entity file: {e}")
            sys.exit(1)
            
        self.entity_data = entity_data
        return entity_data
    
    def create_signature_pdf(self, width: float = 200, height: float = 100) -> str:
        """
        Create a PDF containing the signature image using ReportLab.
        
        Args:
            width: Width of signature in points
            height: Height of signature in points
            
        Returns:
            Path to the created signature PDF
        """
        signature_pdf_path = "temp_signature.pdf"
        
        try:
            # Create a canvas for the signature
            c = canvas.Canvas(signature_pdf_path, pagesize=(width, height))
            
            # Load and draw the signature image
            img = ImageReader(self.signature_image)
            c.drawImage(img, 0, 0, width=width, height=height)
            c.save()
            
            return signature_pdf_path
            
        except Exception as e:
            print(f"Error creating signature PDF: {e}")
            return None
    
    def fill_form_fields(self, pdf_doc: fitz.Document) -> bool:
        """
        Fill form fields in the PDF with entity data.
        
        Args:
            pdf_doc: PyMuPDF document object
            
        Returns:
            True if form fields were found and filled, False otherwise
        """
        form_filled = False
        
        for page_num in range(len(pdf_doc)):
            page = pdf_doc[page_num]
            
            # Get form fields (widgets) on this page
            widgets = list(page.widgets())  # Convert generator to list
            
            for widget in widgets:
                field_name = widget.field_name
                field_type = widget.field_type
                
                if field_type == fitz.PDF_WIDGET_TYPE_TEXT:
                    # Try to match field name with entity data
                    value = self.find_matching_entity_value(field_name)
                    if value:
                        try:
                            widget.field_value = value
                            widget.update()
                            form_filled = True
                            print(f"Filled field '{field_name}' with '{value}'")
                        except Exception as e:
                            print(f"Error filling field '{field_name}': {e}")
                
        return form_filled
    
    def find_matching_entity_value(self, field_name: str) -> Optional[str]:
        """
        Find matching entity value for a form field name.
        
        Args:
            field_name: Name of the form field
            
        Returns:
            Matching value from entity data or None
        """
        field_name_lower = field_name.lower()
        
        # Direct match first
        for key, value in self.entity_data.items():
            if key.lower() == field_name_lower:
                return value
        
        # Enhanced field mappings for company-related fields
        company_field_patterns = [
            'recipient', 'receiving party', 'offeree', 'representatives', 
            'representative', 'company', 'name', 'entity', 'party',
            'organization', 'corporation', 'firm', 'business'
        ]
        
        address_field_patterns = [
            'address', 'location', 'street', 'city', 'state', 'zip',
            'postal', 'residence', 'place'
        ]
        
        # Check if field name matches company patterns
        for pattern in company_field_patterns:
            if pattern in field_name_lower:
                # Return company name from entity data
                for key, value in self.entity_data.items():
                    if key.lower() in ['company', 'name', 'entity']:
                        return value
        
        # Check if field name matches address patterns
        for pattern in address_field_patterns:
            if pattern in field_name_lower:
                # Return address from entity data
                for key, value in self.entity_data.items():
                    if key.lower() in ['address', 'location']:
                        return value
        
        # Additional specific mappings
        field_mappings = {
            'title': ['title', 'position'],
            'date': ['date'],
            'signature': ['company', 'name']  # For signature fields, use company name
        }
        
        for pattern, keys in field_mappings.items():
            if pattern in field_name_lower:
                for key in keys:
                    for entity_key, entity_value in self.entity_data.items():
                        if key.lower() in entity_key.lower():
                            return entity_value
        
        return None
    
    def place_signature(self, pdf_doc: fitz.Document) -> bool:
        """
        Place signature in designated signature fields.
        
        Args:
            pdf_doc: PyMuPDF document object
            
        Returns:
            True if signature fields were found and filled, False otherwise
        """
        signature_placed = False
        
        for page_num in range(len(pdf_doc)):
            page = pdf_doc[page_num]
            widgets = page.widgets()
            
            for widget in widgets:
                if widget.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                    try:
                        # Get widget rectangle
                        rect = widget.rect
                        
                        # Create signature PDF with appropriate size
                        sig_width = rect.width
                        sig_height = rect.height
                        
                        signature_pdf_path = self.create_signature_pdf(sig_width, sig_height)
                        if signature_pdf_path:
                            # Insert signature as image
                            page.insert_image(rect, filename=self.signature_image)
                            signature_placed = True
                            print(f"Placed signature in signature field on page {page_num + 1}")
                            
                            # Clean up temporary file
                            if os.path.exists(signature_pdf_path):
                                os.remove(signature_pdf_path)
                                
                    except Exception as e:
                        print(f"Error placing signature in field: {e}")
        
        return signature_placed
    
    def fill_definition_fields(self, pdf_doc: fitz.Document) -> bool:
        """
        Fill definition fields with company name, typically found in definitions sections.
        Only fills the first occurrence of each term to avoid over-replacement.
        
        Args:
            pdf_doc: PyMuPDF document object
            
        Returns:
            True if any definitions were filled, False otherwise
        """
        definitions_filled = False
        company_name = None
        
        # Get company name from entity data
        for key, value in self.entity_data.items():
            if key.lower() in ['company', 'name', 'entity']:
                company_name = value
                break
        
        if not company_name:
            print("No company name found in entity data for definition filling.")
            return False
        
        # Definition terms to look for - ONLY "Recipient" to avoid over-filling
        definition_terms = [
            'Recipient'  # Only target the Recipient field
        ]
        
        # Track which patterns we've already replaced (once per document)
        replaced_patterns = set()
        # Track areas where we've already made replacements to avoid overlaps
        filled_areas = []
        
        print(f"Searching for definition fields to fill with '{company_name}'...")
        
        # Focus on early pages where definitions are typically found
        max_pages_to_search = min(5, len(pdf_doc))  # Search first 5 pages or all if fewer
        
        for page_num in range(max_pages_to_search):
            page = pdf_doc[page_num]
            
            # Search for each definition term
            for term in definition_terms:
                if term in replaced_patterns:
                    continue  # Skip if we've already replaced this term
                    
                instances = page.search_for(term, flags=fitz.TEXT_DEHYPHENATE)
                
                if instances:
                    print(f"Found '{term}' on page {page_num + 1}")
                    # Only replace the first instance of each term
                    inst = instances[0]
                    
                    # Check if this area overlaps with a previously filled area
                    inst_area = fitz.Rect(inst.x0 - 10, inst.y0 - 10, inst.x1 + 10, inst.y1 + 10)
                    area_overlap = False
                    for filled_area in filled_areas:
                        if inst_area.intersects(filled_area):
                            area_overlap = True
                            print(f"Skipping '{term}' - overlaps with previously filled area")
                            break
                    
                    if area_overlap:
                        continue  # Skip this instance as it overlaps with previous fill
                    try:
                        # Look for underscores or blank space after the term
                        # Expand search area to the right and down to find fill-in areas
                        search_area = fitz.Rect(inst.x1, inst.y0 - 10, inst.x1 + 500, inst.y1 + 50)
                        
                        # Look for underscore patterns near the term
                        underscore_patterns = [
                            '________________________',  # Very long underscores
                            '__________________',        # Long underscores  
                            '______________',            # Medium underscores
                            '__________',                # Short underscores
                            '_______',                  # Very short underscores
                            '____',                     # Minimal underscores
                            '___'                       # Even shorter
                        ]
                        replacement_made = False
                        
                        # First try to find underscores
                        for underscore_pattern in underscore_patterns:
                            underscore_instances = page.search_for(underscore_pattern, clip=search_area)
                            if underscore_instances:
                                # Use the first (closest) underscore pattern found
                                underscore_rect = underscore_instances[0]
                                
                                # Insert company name directly over the underscores without redaction
                                # This avoids any risk of blanking out text above or below
                                text_x = underscore_rect.x0
                                text_y = underscore_rect.y1 - 2  # Slightly above the bottom for proper baseline
                                
                                page.insert_text(
                                    fitz.Point(text_x, text_y),
                                    company_name,
                                    fontsize=10,
                                    color=(0, 0, 0)
                                )
                                
                                replaced_patterns.add(term)
                                replacement_made = True
                                definitions_filled = True
                                print(f"✅ Filled definition '{term}' (underscores) with '{company_name}' on page {page_num + 1}")
                                break
                        
                        # If no underscores found, try other patterns
                        if not replacement_made:
                            # Check for "term means" pattern
                            means_pattern = f"{term} means"
                            means_instances = page.search_for(means_pattern, flags=fitz.TEXT_DEHYPHENATE)
                            if means_instances:
                                means_rect = means_instances[0]
                                # Insert company name after "means"
                                insert_point = fitz.Point(means_rect.x1 + 5, means_rect.y1)
                                page.insert_text(
                                    insert_point,
                                    f" {company_name}",
                                    fontsize=10,
                                    color=(0, 0, 0)
                                )
                                definitions_filled = True
                                print(f"✅ Filled definition '{term}' (means) with '{company_name}' on page {page_num + 1}")
                                replacement_made = True
                                # Mark this term as completed to prevent any future fills
                                replaced_patterns.add(term)
                            
                            # Check for "term:" pattern
                            elif not replacement_made:
                                colon_pattern = f"{term}:"
                                colon_instances = page.search_for(colon_pattern, flags=fitz.TEXT_DEHYPHENATE)
                                if colon_instances:
                                    colon_rect = colon_instances[0]
                                    # Insert company name after colon
                                    insert_point = fitz.Point(colon_rect.x1 + 5, colon_rect.y1)
                                    page.insert_text(
                                        insert_point,
                                        f" {company_name}",
                                        fontsize=10,
                                        color=(0, 0, 0)
                                    )
                                    definitions_filled = True
                                    print(f"✅ Filled definition '{term}' (colon) with '{company_name}' on page {page_num + 1}")
                                    replacement_made = True
                                    # Mark this term as completed to prevent any future fills
                                    replaced_patterns.add(term)
                        
                        # If still no replacement made, look for square brackets and fill-in areas
                        if not replacement_made:
                            # Look for square brackets pattern [________________]
                            # This is common in legal documents for fill-in areas
                            # Expand search area to cover more possibilities
                            bracket_search = fitz.Rect(inst.x0 - 50, inst.y0 - 30, inst.x1 + 700, inst.y1 + 60)
                            
                            print(f"Searching for brackets near '{term}' in area: {bracket_search}")
                            
                            # Look specifically for square brackets first, as they're most likely for fill-ins
                            # Search for square brackets pattern [________________] 
                            square_bracket_instances = page.search_for("[", clip=bracket_search)
                            
                            if square_bracket_instances:
                                print(f"Found {len(square_bracket_instances)} '[' bracket(s) near '{term}'")
                                
                                # Look for the square bracket that's AFTER the term (fill-in area)
                                term_x_end = inst.x1
                                relevant_brackets = [br for br in square_bracket_instances if br.x0 > term_x_end]
                                
                                if relevant_brackets:
                                    bracket_rect = relevant_brackets[0]  # Use the first bracket after the term
                                    
                                    # Look for closing bracket after the opening bracket
                                    closing_bracket_search = fitz.Rect(bracket_rect.x1, bracket_rect.y0 - 10, bracket_rect.x1 + 500, bracket_rect.y1 + 10)
                                    closing_bracket_instances = page.search_for("]", clip=closing_bracket_search)
                                    
                                    if closing_bracket_instances:
                                        closing_bracket_rect = closing_bracket_instances[0]
                                        print(f"Found square bracket fill area for '{term}': [ at [{bracket_rect.x0:.1f},{bracket_rect.y0:.1f}] to ] at [{closing_bracket_rect.x0:.1f},{closing_bracket_rect.y0:.1f}]")
                                        
                                        # Calculate the center of the area between brackets
                                        fill_area_center_x = (bracket_rect.x1 + closing_bracket_rect.x0) / 2
                                        fill_area_y = bracket_rect.y1 - 3  # Slightly above the baseline
                                        
                                        # Clear any underscores in the bracket area first
                                        bracket_fill_area = fitz.Rect(bracket_rect.x1 + 1, bracket_rect.y0 - 5, closing_bracket_rect.x0 - 1, bracket_rect.y1 + 5)
                                        
                                        # Skip underscore removal to avoid text blanking
                                        # Just insert text directly without clearing underscores
                                        
                                        # Insert company name in the center of the bracket area
                                        # Adjust x position to center the text better
                                        text_width_estimate = len(company_name) * 5  # Estimate text width
                                        insert_point = fitz.Point(fill_area_center_x - text_width_estimate/2, fill_area_y)
                                        page.insert_text(
                                            insert_point,
                                            company_name,
                                            fontsize=10,
                                            color=(0, 0, 0)
                                        )
                                        
                                        definitions_filled = True
                                        print(f"✅ Filled definition '{term}' (square brackets) with '{company_name}' on page {page_num + 1}")
                                        replacement_made = True
                                        # Track this area as filled to prevent overlaps
                                        filled_areas.append(fitz.Rect(bracket_rect.x0 - 20, bracket_rect.y0 - 10, closing_bracket_rect.x1 + 20, closing_bracket_rect.y1 + 10))
                                        # Mark this term as completed to prevent any future fills
                                        replaced_patterns.add(term)
                                        break
                                    else:
                                        print(f"Found opening [ for '{term}' but no closing ]")
                                else:
                                    print(f"Found [ brackets but none are after the '{term}' text")
                            else:
                                print(f"No square brackets found near '{term}'")
                            
                            if not replacement_made:
                                print(f"No bracket pairs found near '{term}', checking for other fill patterns...")
                                
                                # Look for lines/underscores without brackets  
                                line_found = False
                                for underscore_pattern in underscore_patterns:
                                    underscore_instances = page.search_for(underscore_pattern, clip=bracket_search)
                                    if underscore_instances:
                                        print(f"Found underscore pattern '{underscore_pattern}' near '{term}'")
                                        underscore_rect = underscore_instances[0]
                                        
                                        # Insert company name directly over the underscore area without redaction
                                        center_x = (underscore_rect.x0 + underscore_rect.x1) / 2
                                        text_width_estimate = len(company_name) * 5
                                        insert_point = fitz.Point(center_x - text_width_estimate/2, underscore_rect.y1 - 2)
                                        page.insert_text(
                                            insert_point,
                                            company_name,
                                            fontsize=10,
                                            color=(0, 0, 0)
                                        )
                                        
                                        definitions_filled = True
                                        print(f"✅ Filled definition '{term}' (underscore line) with '{company_name}' on page {page_num + 1}")
                                        replacement_made = True
                                        line_found = True
                                        # Track this area as filled to prevent overlaps
                                        filled_areas.append(fitz.Rect(underscore_rect.x0 - 20, underscore_rect.y0 - 10, underscore_rect.x1 + 20, underscore_rect.y1 + 10))
                                        # Mark this term as completed to prevent any future fills
                                        replaced_patterns.add(term)
                                        break
                                
                                if not line_found:
                                    print(f"No fill-in patterns found near '{term}'")
                            
                            # If no square brackets, try parentheses
                            if not replacement_made:
                                # Try to find opening parenthesis after the term
                                paren_search = fitz.Rect(inst.x1, inst.y0 - 5, inst.x1 + 100, inst.y1 + 5)
                                paren_instances = page.search_for("(", clip=paren_search)
                                
                                if paren_instances:
                                    # Insert company name after opening parenthesis
                                    paren_rect = paren_instances[0]
                                    insert_point = fitz.Point(paren_rect.x1 + 2, paren_rect.y1)
                                    page.insert_text(
                                        insert_point,
                                        f'"{company_name}"',
                                        fontsize=10,
                                        color=(0, 0, 0)
                                    )
                                    definitions_filled = True
                                    print(f"✅ Filled definition '{term}' (parentheses) with '{company_name}' on page {page_num + 1}")
                                    replacement_made = True
                                    # Track this area as filled to prevent overlaps
                                    filled_areas.append(fitz.Rect(paren_rect.x0 - 20, paren_rect.y0 - 10, paren_rect.x0 + 200, paren_rect.y1 + 10))
                                    # Mark this term as completed to prevent any future fills
                                    replaced_patterns.add(term)
                                    # Also mark related terms to prevent substring matches
                                    if term == 'Representatives':
                                        replaced_patterns.add('Representative')
                                        print(f"Also marked 'Representative' as completed to prevent duplicates")
                                else:
                                    # Last resort: place text directly after the term with some spacing
                                    insert_point = fitz.Point(inst.x1 + 10, inst.y1)
                                    page.insert_text(
                                        insert_point,
                                        f' ("{company_name}")',
                                        fontsize=10,
                                        color=(0, 0, 0)
                                    )
                                    definitions_filled = True
                                    print(f"✅ Filled definition '{term}' (direct placement) with '{company_name}' on page {page_num + 1}")
                                    # Track this area as filled to prevent overlaps
                                    filled_areas.append(fitz.Rect(inst.x0 - 20, inst.y0 - 10, inst.x1 + 200, inst.y1 + 10))
                                    # Mark this term as completed to prevent any future fills
                                    replaced_patterns.add(term)
                        
                    except Exception as e:
                        print(f"❌ Error filling definition '{term}' on page {page_num + 1}: {e}")
        
        if definitions_filled:
            print(f"Completed filling definitions. Replaced {len(replaced_patterns)} definition(s).")
        else:
            print("No definition fields found to fill.")
            
        return definitions_filled

    def fallback_placement(self, pdf_doc: fitz.Document) -> None:
        """
        Fallback placement of signature and text when no form fields are available.
        
        Args:
            pdf_doc: PyMuPDF document object
        """
        print("No form fields found. Using fallback placement...")
        
        # First, try to fill definition fields
        definitions_filled = self.fill_definition_fields(pdf_doc)
        
        # Get the last page for signature placement
        last_page = pdf_doc[-1]
        page_rect = last_page.rect
        
        # Search for signature-related keywords on all pages
        signature_keywords = ['signature', 'sign here', 'by:', 'signed by', 'name:', 'title:', 'date:']
        signature_locations = []
        
        for page_num in range(len(pdf_doc)):
            page = pdf_doc[page_num]
            
            for keyword in signature_keywords:
                instances = page.search_for(keyword, flags=fitz.TEXT_DEHYPHENATE)
                for inst in instances:
                    signature_locations.append((page_num, inst, keyword))
        
        # Determine signature placement
        if signature_locations:
            # Use the last found signature location
            page_num, rect, keyword = signature_locations[-1]
            target_page = pdf_doc[page_num]
            
            # Place signature below the found keyword
            sig_rect = fitz.Rect(rect.x0, rect.y1 + 10, rect.x0 + 150, rect.y1 + 60)
        else:
            # Fallback to bottom-left of last page
            target_page = last_page
            sig_rect = fitz.Rect(50, page_rect.height - 150, 200, page_rect.height - 100)
        
        # Insert signature image
        try:
            target_page.insert_image(sig_rect, filename=self.signature_image)
            print(f"Placed signature on page {target_page.number + 1}")
        except Exception as e:
            print(f"Error placing signature: {e}")
        
        # Add entity data as text
        self.add_entity_text(target_page, sig_rect)
    
    def add_entity_text(self, page: fitz.Page, sig_rect: fitz.Rect) -> None:
        """
        Add entity data as text near the signature.
        
        Args:
            page: PyMuPDF page object
            sig_rect: Rectangle where signature was placed
        """
        try:
            y_position = sig_rect.y1 + 20
            
            for key, value in self.entity_data.items():
                text = f"{key}: {value}"
                text_rect = fitz.Rect(sig_rect.x0, y_position, sig_rect.x0 + 300, y_position + 15)
                
                page.insert_text(
                    text_rect.tl,
                    text,
                    fontsize=10,
                    color=(0, 0, 0)
                )
                
                y_position += 20
                
        except Exception as e:
            print(f"Error adding entity text: {e}")
    
    def flatten_pdf(self, pdf_doc: fitz.Document) -> None:
        """
        Flatten the PDF to make form fields non-editable.
        
        Args:
            pdf_doc: PyMuPDF document object
        """
        try:
            # Create a new document for flattened content
            flattened_doc = fitz.open()
            
            # Convert each page to an image and back to PDF (flattening)
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                
                # Get page as pixmap with good resolution
                mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for quality
                pix = page.get_pixmap(matrix=mat)
                
                # Create new page in flattened document
                new_page = flattened_doc.new_page(width=page.rect.width, height=page.rect.height)
                
                # Insert the pixmap as image
                new_page.insert_image(page.rect, pixmap=pix)
                
            # Replace original document content
            pdf_doc.close()
            
            # Re-open the document and replace with flattened content
            temp_bytes = flattened_doc.write()
            flattened_doc.close()
            
            # Update the original document reference
            self.pdf_doc = fitz.open("pdf", temp_bytes)
                
            print("PDF flattened successfully")
            
        except Exception as e:
            print(f"Error flattening PDF: {e}")
    
    def process_pdf(self, output_path: str = "signed_output.pdf") -> bool:
        """
        Main processing function that orchestrates the entire signing process.
        
        Args:
            output_path: Path for the output signed PDF
            
        Returns:
            True if processing was successful, False otherwise
        """
        try:
            # Load entity data
            print("Loading entity data...")
            self.load_entity_data()
            print(f"Loaded entity data: {self.entity_data}")
            
            # Open PDF document
            print("Opening PDF document...")
            self.pdf_doc = fitz.open(self.input_pdf)
            
            # Try to fill form fields
            print("Checking for form fields...")
            form_fields_filled = self.fill_form_fields(self.pdf_doc)
            
            # Try to place signature in signature fields
            print("Checking for signature fields...")
            signature_fields_filled = self.place_signature(self.pdf_doc)
            
            # If no form fields or signature fields were found, use fallback
            if not form_fields_filled and not signature_fields_filled:
                self.fallback_placement(self.pdf_doc)
            
            # Flatten the PDF
            print("Flattening PDF...")
            self.flatten_pdf(self.pdf_doc)
            
            # Save the result
            print(f"Saving signed PDF to {output_path}...")
            self.pdf_doc.save(output_path)
            self.pdf_doc.close()
            
            print(f"Successfully created signed PDF: {output_path}")
            return True
            
        except Exception as e:
            print(f"Error processing PDF: {e}")
            if self.pdf_doc:
                self.pdf_doc.close()
            return False


def main():
    """Main function to run the PDF signer."""
    # File paths
    input_pdf = "input.pdf"
    entity_file = "entity.txt"
    signature_image = "signature.jpg"
    output_pdf = "signed_output.pdf"
    
    # Check if all required files exist
    required_files = [input_pdf, entity_file, signature_image]
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print("Error: Missing required files:")
        for file in missing_files:
            print(f"  - {file}")
        sys.exit(1)
    
    # Create signer instance and process
    signer = AutoPDFSigner(input_pdf, entity_file, signature_image)
    success = signer.process_pdf(output_pdf)
    
    if success:
        print("\n✅ PDF signing completed successfully!")
    else:
        print("\n❌ PDF signing failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()

