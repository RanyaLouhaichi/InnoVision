from typing import Dict, Optional
import pytesseract # type: ignore
from PIL import Image
import re
import os

class ValidationAgent:
    def __init__(self):
        try:
            pytesseract.get_tesseract_version()
            print("Tesseract is available.")
        except Exception as e:
            print(f"Tesseract not found or not configured: {e}. OCR validation will not work.")
            print("Ensure Tesseract OCR is installed and in your PATH, or TESSDATA_PREFIX is set.")

    def _ocr_image(self, image_path: str, lang: str = 'fra+ara') -> Optional[str]:
        try:
            if not os.path.exists(image_path):
                print(f"Image not found for OCR: {image_path}")
                return None
            text = pytesseract.image_to_string(Image.open(image_path), lang=lang)
            return text.strip()
        except Exception as e:
            print(f"OCR error on {image_path} with lang {lang}: {e}")
            return None

    def validate_cin(self, image_path: str) -> Dict:
        validation_result = {"is_valid": False, "cin_number": None, "error": None, "raw_text": None}
        raw_text = self._ocr_image(image_path, lang='ara+fra')
        if not raw_text:
            validation_result["error"] = "OCR failed or no text found in image."
            return validation_result
        validation_result["raw_text"] = raw_text
        cin_match = re.search(r'\b(\d{8})\b', raw_text)
        if cin_match:
            validation_result["cin_number"] = cin_match.group(1)
            validation_result["is_valid"] = True
            print(f"CIN found: {validation_result['cin_number']}")
        else:
            validation_result["error"] = "CIN number pattern (8 digits) not found in the document."
            print(f"CIN pattern not found in OCR text: {raw_text[:200]}...")
        return validation_result

    def validate_passport(self, image_path: str) -> Dict:
        validation_result = {"is_valid": False, "passport_number": None, "error": None, "raw_text": None}
        raw_text = self._ocr_image(image_path, lang='fra')
        if not raw_text:
            validation_result["error"] = "OCR failed or no text found in image."
            return validation_result
        validation_result["raw_text"] = raw_text
        passport_match = re.search(r'\b([A-Z0-9]{7,12})\b', raw_text) 
        if passport_match:
            validation_result["passport_number"] = passport_match.group(1)
            validation_result["is_valid"] = True
        else:
            validation_result["error"] = "Passport number pattern not found."
        return validation_result