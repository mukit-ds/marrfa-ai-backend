# backend/app/file_processor.py
import io
from typing import List, Dict, Any
from pypdf import PdfReader
from docx import Document
from PIL import Image
import pytesseract
import base64
from openai import OpenAI


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF files."""
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        return f"[Error processing PDF: {str(e)}]"


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX files."""
    try:
        doc = Document(io.BytesIO(file_bytes))
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text.strip()
    except Exception as e:
        return f"[Error processing DOCX: {str(e)}]"


def extract_text_from_txt(file_bytes: bytes) -> str:
    """Extract text from TXT files."""
    try:
        return file_bytes.decode('utf-8').strip()
    except:
        try:
            return file_bytes.decode('latin-1').strip()
        except Exception as e:
            return f"[Error processing TXT: {str(e)}]"


def extract_text_from_image(file_bytes: bytes, client: OpenAI = None) -> str:
    """Extract text from images using OCR."""
    try:
        image = Image.open(io.BytesIO(file_bytes))
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        # If Tesseract is not available, use OpenAI Vision API
        if client:
            try:
                base64_image = base64.b64encode(file_bytes).decode('utf-8')
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Extract all text from this image."},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=1000
                )
                return response.choices[0].message.content.strip()
            except Exception as vision_error:
                return f"[OCR Error: {str(e)}]"
        return f"[OCR Error: {str(e)}]"


def extract_text_from_csv(file_bytes: bytes) -> str:
    """Extract text from CSV files."""
    try:
        content = file_bytes.decode('utf-8')
        return content[:2000] + ("..." if len(content) > 2000 else "")
    except Exception as e:
        return f"[Error processing CSV: {str(e)}]"


def process_uploaded_file(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """Process uploaded file and extract relevant information."""
    result = {
        "filename": filename,
        "file_type": None,
        "text_content": "",
        "error": None,
        "size_kb": len(file_bytes) / 1024
    }

    # Get file extension
    ext = filename.split('.')[-1].lower() if '.' in filename else ''

    try:
        if ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp']:
            result["file_type"] = "image"
            result["text_content"] = extract_text_from_image(file_bytes)
        elif ext == 'pdf':
            result["file_type"] = "pdf"
            result["text_content"] = extract_text_from_pdf(file_bytes)
        elif ext == 'docx':
            result["file_type"] = "docx"
            result["text_content"] = extract_text_from_docx(file_bytes)
        elif ext == 'txt':
            result["file_type"] = "txt"
            result["text_content"] = extract_text_from_txt(file_bytes)
        elif ext == 'csv':
            result["file_type"] = "csv"
            result["text_content"] = extract_text_from_csv(file_bytes)
        else:
            result["error"] = f"Unsupported file type: {ext}"
            result["text_content"] = f"[Unsupported file type: {ext}]"
    except Exception as e:
        result["error"] = str(e)
        result["text_content"] = f"[Processing error: {str(e)}]"

    return result


def analyze_files_with_ai(files_content: List[str], user_query: str = "", client: OpenAI = None) -> str:
    """Use AI to analyze file content in the context of user query."""
    if not client:
        return "AI service is not available for file analysis."

    # Combine all file content
    all_content = "\n\n---\n\n".join(files_content)

    if not all_content or all_content.startswith("["):
        return "I couldn't extract meaningful content from the files."

    prompt = f"""You are Marrfa AI Assistant. Analyze the following file content(s) and answer the user's question about it.

User's question: {user_query if user_query else "Please analyze these files and provide a summary."}

File content(s):
{all_content[:5000]}

Please provide a helpful analysis. If the content is related to real estate or properties, extract key details.
If it's about Marrfa company, extract relevant business information.
If unrelated, politely mention that and summarize what you found.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system",
                 "content": "You are Marrfa AI, a helpful assistant specialized in real estate and company information."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error analyzing files: {str(e)}"