"""
Nexus ERP - OCR Service
========================

OCR (Optical Character Recognition) service for invoice parsing.
Extracts data from invoice images and PDFs using AI vision capabilities.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
import json
import os
import base64
import re
from io import BytesIO

from app.models.ai import OCRResult, OCRStatus
from app.models.accounting import Partner
from app.models.inventory import Product
from app.core.config import settings

logger = logging.getLogger(__name__)


class OCRService:
    """
    OCR Service
    
    Provides OCR capabilities for invoice and document parsing.
    Uses AI vision models to extract structured data.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.upload_dir = settings.UPLOAD_DIR if hasattr(settings, 'UPLOAD_DIR') else "/tmp/uploads"
        os.makedirs(self.upload_dir, exist_ok=True)
    
    # ========================================
    # Main OCR Methods
    # ========================================
    
    async def process_invoice(
        self,
        file_content: bytes,
        filename: str,
        tenant_id: UUID,
        document_type: str = "invoice",
        user_id: Optional[UUID] = None
    ) -> OCRResult:
        """
        Process an invoice image/PDF and extract data.
        
        Args:
            file_content: Binary file content
            filename: Original filename
            tenant_id: Tenant UUID
            document_type: Type of document
            user_id: Requesting user ID
            
        Returns:
            OCRResult with extracted data
        """
        # Create OCR result record
        ocr_result = OCRResult(
            tenant_id=tenant_id,
            document_type=document_type,
            original_filename=filename,
            file_size=len(file_content),
            status=OCRStatus.PROCESSING,
            processing_started_at=datetime.utcnow(),
            created_by_id=user_id
        )
        self.db.add(ocr_result)
        await self.db.flush()
        
        try:
            # Save file temporarily
            file_path = os.path.join(self.upload_dir, f"{ocr_result.id}_{filename}")
            with open(file_path, "wb") as f:
                f.write(file_content)
            
            ocr_result.file_path = file_path
            
            # Determine file type and extract text
            if filename.lower().endswith('.pdf'):
                extracted_text = await self._extract_from_pdf(file_content)
            else:
                extracted_text = await self._extract_from_image(file_content)
            
            ocr_result.raw_text = extracted_text
            
            # Use AI to parse extracted text
            parsed_data = await self._parse_invoice_with_ai(extracted_text, tenant_id)
            
            # Update OCR result with extracted data
            ocr_result.extracted_data = parsed_data
            ocr_result.invoice_number = parsed_data.get("invoice_number")
            ocr_result.invoice_date = self._parse_date(parsed_data.get("invoice_date"))
            ocr_result.due_date = self._parse_date(parsed_data.get("due_date"))
            ocr_result.partner_name = parsed_data.get("vendor_name") or parsed_data.get("customer_name")
            ocr_result.partner_tax_id = parsed_data.get("vendor_tax_id")
            ocr_result.subtotal = Decimal(str(parsed_data.get("subtotal", 0)))
            ocr_result.tax_amount = Decimal(str(parsed_data.get("tax_amount", 0)))
            ocr_result.total_amount = Decimal(str(parsed_data.get("total_amount", 0)))
            ocr_result.currency = parsed_data.get("currency", "SAR")
            ocr_result.line_items = parsed_data.get("line_items", [])
            ocr_result.overall_confidence = parsed_data.get("confidence", 0.8)
            ocr_result.field_confidence = parsed_data.get("field_confidence", {})
            
            # Validate extracted data
            ocr_result.validation_errors = self._validate_extracted_data(parsed_data)
            
            ocr_result.status = OCRStatus.COMPLETED
            ocr_result.processing_completed_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(ocr_result)
            
            return ocr_result
            
        except Exception as e:
            logger.error(f"OCR processing error: {e}")
            ocr_result.status = OCRStatus.FAILED
            ocr_result.processing_notes = str(e)
            ocr_result.processing_completed_at = datetime.utcnow()
            await self.db.commit()
            raise
    
    async def get_ocr_result(
        self,
        ocr_id: UUID,
        tenant_id: UUID
    ) -> Optional[OCRResult]:
        """Get OCR result by ID."""
        result = await self.db.execute(
            select(OCRResult).where(
                OCRResult.id == ocr_id,
                OCRResult.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()
    
    async def list_ocr_results(
        self,
        tenant_id: UUID,
        status: Optional[OCRStatus] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[OCRResult], int]:
        """List OCR results with optional filtering."""
        query = select(OCRResult).where(OCRResult.tenant_id == tenant_id)
        
        if status:
            query = query.where(OCRResult.status == status)
        
        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)
        
        # Paginate
        query = query.order_by(OCRResult.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        return list(result.scalars().all()), total or 0
    
    # ========================================
    # Document Processing
    # ========================================
    
    async def _extract_from_image(self, image_content: bytes) -> str:
        """Extract text from image using AI vision."""
        try:
            from openai import AsyncOpenAI
            
            api_key = getattr(settings, 'OPENAI_API_KEY', None)
            if api_key:
                client = AsyncOpenAI(api_key=api_key)
                
                # Encode image to base64
                image_base64 = base64.b64encode(image_content).decode('utf-8')
                
                # Determine image type
                image_type = "jpeg"
                if image_content[:4] == b'\x89PNG':
                    image_type = "png"
                
                # Use vision model to extract text
                completion = await client.chat.completions.create(
                    model="gpt-4o",  # Vision model
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an OCR expert. Extract all text from the image exactly as it appears. Preserve the structure and formatting."
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Extract all text from this invoice image. Preserve the layout and structure."
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/{image_type};base64,{image_base64}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=2000
                )
                
                return completion.choices[0].message.content
            
        except Exception as e:
            logger.warning(f"AI vision extraction failed: {e}, falling back to pytesseract")
        
        # Fallback to pytesseract
        try:
            import pytesseract
            from PIL import Image
            
            image = Image.open(BytesIO(image_content))
            text = pytesseract.image_to_string(image, lang='ara+eng')
            return text
        except Exception as e2:
            logger.error(f"Pytesseract also failed: {e2}")
            return ""
    
    async def _extract_from_pdf(self, pdf_content: bytes) -> str:
        """Extract text from PDF."""
        try:
            # Try pdfplumber first
            import pdfplumber
            
            text_parts = []
            with pdfplumber.open(BytesIO(pdf_content)) as pdf:
                for page in pdf.pages:
                    text_parts.append(page.extract_text() or "")
            
            return "\n\n".join(text_parts)
            
        except ImportError:
            # Fallback to PyPDF2
            try:
                from PyPDF2 import PdfReader
                
                reader = PdfReader(BytesIO(pdf_content))
                text_parts = []
                for page in reader.pages:
                    text_parts.append(page.extract_text() or "")
                
                return "\n\n".join(text_parts)
                
            except Exception as e:
                logger.error(f"PDF extraction failed: {e}")
                return ""
    
    # ========================================
    # AI Parsing
    # ========================================
    
    async def _parse_invoice_with_ai(
        self,
        text: str,
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """Use AI to parse extracted text into structured invoice data."""
        try:
            from openai import AsyncOpenAI
            
            api_key = getattr(settings, 'OPENAI_API_KEY', None)
            if not api_key:
                logger.warning("OpenAI API key not configured, using fallback parsing")
                return self._fallback_parse(text)
            
            client = AsyncOpenAI(api_key=api_key)
            
            # Get known products for better matching
            products_result = await self.db.execute(
                select(Product.name, Product.sku).where(
                    Product.tenant_id == tenant_id,
                    Product.is_deleted == False
                ).limit(100)
            )
            known_products = [
                {"name": p.name, "sku": p.sku}
                for p in products_result.all()
            ]
            
            # Get known partners
            partners_result = await self.db.execute(
                select(Partner.name, Partner.partner_type).where(
                    Partner.tenant_id == tenant_id
                ).limit(100)
            )
            known_partners = [
                {"name": p.name, "type": p.partner_type}
                for p in partners_result.all()
            ]
            
            prompt = f"""Parse the following invoice text and extract structured data.

Invoice Text:
{text[:3000]}  # Limit text length

Known Products in System:
{json.dumps(known_products[:50])}

Known Partners in System:
{json.dumps(known_partners[:50])}

Extract the following information and return ONLY valid JSON:
{{
    "invoice_number": "string or null",
    "invoice_date": "YYYY-MM-DD or null",
    "due_date": "YYYY-MM-DD or null",
    "vendor_name": "string or null",
    "vendor_tax_id": "string or null",
    "customer_name": "string or null",
    "subtotal": number,
    "tax_amount": number,
    "total_amount": number,
    "currency": "string (e.g., SAR, USD)",
    "line_items": [
        {{
            "description": "string",
            "quantity": number,
            "unit_price": number,
            "total": number,
            "product_match": "SKU or name if matched to known product"
        }}
    ],
    "confidence": 0.0-1.0,
    "field_confidence": {{
        "invoice_number": 0.0-1.0,
        "invoice_date": 0.0-1.0,
        "total_amount": 0.0-1.0
    }}
}}"""

            completion = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert invoice parser. Extract data accurately and return only valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1
            )
            
            response_text = completion.choices[0].message.content
            
            # Parse JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return self._fallback_parse(text)
                
        except Exception as e:
            logger.error(f"AI parsing failed: {e}")
            return self._fallback_parse(text)
    
    def _fallback_parse(self, text: str) -> Dict[str, Any]:
        """Fallback parsing using regex patterns."""
        result = {
            "invoice_number": None,
            "invoice_date": None,
            "due_date": None,
            "vendor_name": None,
            "subtotal": 0,
            "tax_amount": 0,
            "total_amount": 0,
            "currency": "SAR",
            "line_items": [],
            "confidence": 0.3,
            "field_confidence": {}
        }
        
        # Invoice number patterns
        inv_patterns = [
            r'Invoice\s*#?\s*:?\s*([A-Z0-9-]+)',
            r'INV[-\s]?(\d+)',
            r'فاتورة\s*(?:رقم)?\s*:?\s*([A-Z0-9-]+)'
        ]
        for pattern in inv_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["invoice_number"] = match.group(1)
                break
        
        # Date patterns
        date_patterns = [
            r'Date\s*:?\s*(\d{4}-\d{2}-\d{2})',
            r'Date\s*:?\s*(\d{2}/\d{2}/\d{4})',
            r'التاريخ\s*:?\s*(\d{4}-\d{2}-\d{2})'
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["invoice_date"] = match.group(1)
                break
        
        # Total amount patterns
        total_patterns = [
            r'Total\s*:?\s*([\d,]+\.?\d*)',
            r'الإجمالي\s*:?\s*([\d,]+\.?\d*)',
            r'Grand\s*Total\s*:?\s*([\d,]+\.?\d*)'
        ]
        for pattern in total_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    result["total_amount"] = float(match.group(1).replace(',', ''))
                except ValueError:
                    pass
                break
        
        return result
    
    # ========================================
    # Helper Methods
    # ========================================
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse date string to date object."""
        if not date_str:
            return None
        
        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%Y/%m/%d",
            "%d-%m-%Y"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        return None
    
    def _validate_extracted_data(self, data: Dict) -> List[str]:
        """Validate extracted data and return errors."""
        errors = []
        
        if not data.get("invoice_number"):
            errors.append("Invoice number not found")
        
        if not data.get("total_amount"):
            errors.append("Total amount not found")
        
        if data.get("total_amount", 0) <= 0:
            errors.append("Invalid total amount")
        
        if not data.get("line_items"):
            errors.append("No line items detected")
        
        # Check for balance
        if data.get("line_items"):
            items_total = sum(item.get("total", 0) for item in data["line_items"])
            if abs(items_total - data.get("subtotal", 0)) > 0.01:
                errors.append("Line items don't match subtotal")
        
        return errors
    
    # ========================================
    # Invoice Creation from OCR
    # ========================================
    
    async def create_invoice_from_ocr(
        self,
        ocr_id: UUID,
        tenant_id: UUID,
        corrections: Optional[Dict] = None,
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Create an actual invoice from OCR result.
        
        Args:
            ocr_id: OCR result ID
            tenant_id: Tenant UUID
            corrections: Optional corrections to apply
            user_id: Creating user ID
            
        Returns:
            Created invoice data
        """
        ocr_result = await self.get_ocr_result(ocr_id, tenant_id)
        if not ocr_result or ocr_result.status != OCRStatus.COMPLETED:
            raise ValueError("OCR result not found or not completed")
        
        # Apply corrections if provided
        data = ocr_result.extracted_data.copy()
        if corrections:
            data.update(corrections)
        
        # Find or create partner
        partner = None
        if data.get("vendor_name"):
            result = await self.db.execute(
                select(Partner).where(
                    Partner.tenant_id == tenant_id,
                    Partner.name.ilike(f"%{data['vendor_name']}%")
                )
            )
            partner = result.scalar_one_or_none()
        
        # Match line items to products
        matched_items = []
        for item in data.get("line_items", []):
            product_match = item.get("product_match")
            product = None
            
            if product_match:
                result = await self.db.execute(
                    select(Product).where(
                        Product.tenant_id == tenant_id,
                        Product.is_deleted == False,
                        (Product.sku == product_match) | (Product.name.ilike(f"%{product_match}%"))
                    )
                )
                product = result.scalar_one_or_none()
            
            matched_items.append({
                "product_id": str(product.id) if product else None,
                "description": item.get("description", ""),
                "quantity": item.get("quantity", 1),
                "price_unit": item.get("unit_price", 0),
                "subtotal": item.get("total", 0),
                "product_matched": product is not None
            })
        
        # Mark OCR result as used
        ocr_result.created_document_type = "invoice"
        await self.db.commit()
        
        return {
            "ocr_id": str(ocr_id),
            "invoice_number": data.get("invoice_number"),
            "invoice_date": data.get("invoice_date"),
            "partner_id": str(partner.id) if partner else None,
            "partner_name": data.get("vendor_name"),
            "subtotal": data.get("subtotal", 0),
            "tax_amount": data.get("tax_amount", 0),
            "total_amount": data.get("total_amount", 0),
            "currency": data.get("currency", "SAR"),
            "line_items": matched_items,
            "confidence": ocr_result.overall_confidence,
            "validation_errors": ocr_result.validation_errors
        }
