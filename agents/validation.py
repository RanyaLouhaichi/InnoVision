from typing import Dict, Optional
import pytesseract # type: ignore
from PIL import Image
import re
import os

class ValidationAgent:
    def __init__(self):
        self.tesseract_available = self._check_tesseract()
        
    def _check_tesseract(self) -> bool:
        """Check if Tesseract is available and properly configured"""
        try:
            pytesseract.get_tesseract_version()
            print("✅ Tesseract is available and configured.")
            return True
        except Exception as e:
            print(f"❌ Tesseract not found or not configured: {e}")
            print("📝 To fix this:")
            print("   1. Install Tesseract OCR: https://github.com/tesseract-ocr/tesseract")
            print("   2. Add Tesseract to your system PATH")
            print("   3. Or set TESSDATA_PREFIX environment variable")
            print("   4. Install language packs for French and Arabic if needed")
            return False

    def _ocr_image(self, image_path: str, lang: str = 'fra+ara') -> Optional[str]:
        """Extract text from image using OCR with better error handling"""
        if not self.tesseract_available:
            print("❌ Tesseract not available - cannot perform OCR")
            return None
            
        try:
            if not os.path.exists(image_path):
                print(f"❌ Image file not found: {image_path}")
                return None
            
            # Verify it's a valid image file
            try:
                with Image.open(image_path) as img:
                    # Convert to RGB if necessary
                    if img.mode not in ('RGB', 'L'):
                        img = img.convert('RGB')
                    
                    # Perform OCR with custom configuration
                    custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz '
                    text = pytesseract.image_to_string(img, lang=lang, config=custom_config)
                    
                    if text and text.strip():
                        print(f"✅ OCR successful, extracted {len(text.strip())} characters")
                        return text.strip()
                    else:
                        print("⚠️ OCR completed but no text was extracted")
                        return None
                        
            except Exception as img_error:
                print(f"❌ Error opening/processing image: {img_error}")
                return None
                
        except Exception as e:
            print(f"❌ OCR error on {image_path} with lang {lang}: {e}")
            # Try with a simpler language setting as fallback
            try:
                print("🔄 Retrying OCR with simplified settings...")
                text = pytesseract.image_to_string(Image.open(image_path), lang='fra')
                return text.strip() if text and text.strip() else None
            except Exception as fallback_error:
                print(f"❌ Fallback OCR also failed: {fallback_error}")
                return None

    def validate_cin(self, image_path: str) -> Dict:
        """Validate Tunisian CIN (Carte d'Identité Nationale) with improved pattern matching"""
        validation_result = {
            "is_valid": False, 
            "cin_number": None, 
            "error": None, 
            "raw_text": None,
            "confidence": 0.0
        }
        
        # First try OCR
        raw_text = self._ocr_image(image_path, lang='ara+fra')
        if not raw_text:
            validation_result["error"] = "OCR failed or no text found in image. Please ensure the image is clear and contains text."
            return validation_result
        
        validation_result["raw_text"] = raw_text
        
        # Multiple CIN patterns for Tunisian CIN
        cin_patterns = [
            r'\b(\d{8})\b',  # Standard 8-digit CIN
            r'CIN[:\s]*(\d{8})',  # CIN: 12345678
            r'N°[:\s]*(\d{8})',   # N°: 12345678
            r'رقم[:\s]*(\d{8})',   # Arabic equivalent
        ]
        
        found_cin = None
        confidence = 0.0
        
        for pattern in cin_patterns:
            matches = re.finditer(pattern, raw_text, re.IGNORECASE)
            for match in matches:
                potential_cin = match.group(1)
                # Additional validation: CIN should be exactly 8 digits
                if len(potential_cin) == 8 and potential_cin.isdigit():
                    found_cin = potential_cin
                    confidence = 0.9 if 'CIN' in raw_text.upper() else 0.7
                    break
            if found_cin:
                break
        
        if found_cin:
            validation_result["cin_number"] = found_cin
            validation_result["is_valid"] = True
            validation_result["confidence"] = confidence
            print(f"✅ CIN found: {found_cin} (confidence: {confidence})")
        else:
            validation_result["error"] = "CIN number pattern (8 digits) not found in the document. Please ensure the image shows a clear Tunisian CIN."
            print(f"❌ CIN pattern not found in OCR text: {raw_text[:200]}...")
        
        return validation_result

    def validate_passport(self, image_path: str) -> Dict:
        """Validate passport with improved pattern matching"""
        validation_result = {
            "is_valid": False, 
            "passport_number": None, 
            "error": None, 
            "raw_text": None,
            "confidence": 0.0
        }
        
        raw_text = self._ocr_image(image_path, lang='fra+eng')
        if not raw_text:
            validation_result["error"] = "OCR failed or no text found in image."
            return validation_result
        
        validation_result["raw_text"] = raw_text
        
        # Multiple passport patterns
        passport_patterns = [
            r'PASSPORT[:\s]*([A-Z0-9]{6,12})',  # PASSPORT: ABC123456
            r'N°[:\s]*([A-Z0-9]{6,12})',       # N°: ABC123456
            r'NO[:\s]*([A-Z0-9]{6,12})',       # NO: ABC123456
            r'\b([A-Z]{1,2}\d{6,8})\b',        # Pattern like AB1234567
            r'\b([A-Z0-9]{7,9})\b',            # General alphanumeric pattern
        ]
        
        found_passport = None
        confidence = 0.0
        
        for pattern in passport_patterns:
            matches = re.finditer(pattern, raw_text.upper())
            for match in matches:
                potential_passport = match.group(1)
                # Additional validation
                if 6 <= len(potential_passport) <= 12:
                    found_passport = potential_passport
                    confidence = 0.9 if 'PASSPORT' in raw_text.upper() else 0.6
                    break
            if found_passport:
                break
        
        if found_passport:
            validation_result["passport_number"] = found_passport
            validation_result["is_valid"] = True
            validation_result["confidence"] = confidence
            print(f"✅ Passport found: {found_passport} (confidence: {confidence})")
        else:
            validation_result["error"] = "Passport number pattern not found in the document."
            print(f"❌ Passport pattern not found in OCR text: {raw_text[:200]}...")
        
        return validation_result

    def validate_document_generic(self, image_path: str, doc_type: str = "document") -> Dict:
        """Generic document validation that just checks if text can be extracted"""
        validation_result = {
            "is_valid": False, 
            "doc_type": doc_type,
            "error": None, 
            "raw_text": None,
            "text_length": 0
        }
        
        raw_text = self._ocr_image(image_path)
        if not raw_text:
            validation_result["error"] = f"Could not extract text from {doc_type} image."
            return validation_result
        
        validation_result["raw_text"] = raw_text
        validation_result["text_length"] = len(raw_text)
        validation_result["is_valid"] = len(raw_text) > 10  # At least 10 characters
        
        if validation_result["is_valid"]:
            print(f"✅ {doc_type} validation successful - extracted {len(raw_text)} characters")
        else:
            validation_result["error"] = f"Insufficient text extracted from {doc_type} (only {len(raw_text)} characters)"
        
        return validation_result