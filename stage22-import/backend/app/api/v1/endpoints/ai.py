"""
Nexus ERP - AI API Endpoints
=============================

REST API endpoints for AI-powered features:
- Demand Forecasting
- OCR Invoice Parsing
- AI Chatbot
"""

from datetime import date
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import json

from app.core.database import get_db
from app.core.security import get_current_user, require_permission
from app.models.user import User
from app.models.ai import ForecastType, ForecastMethod, OCRStatus
from app.services.ai.forecasting_service import ForecastingService
from app.services.ai.ocr_service import OCRService
from app.services.ai.chatbot_service import ChatbotService

router = APIRouter(prefix="/ai", tags=["Artificial Intelligence"])


# ========================================
# Request/Response Schemas
# ========================================

class ForecastRequest(BaseModel):
    """Request schema for generating forecast."""
    product_id: UUID
    forecast_type: str = Field(default="demand")
    periods: int = Field(default=6, ge=1, le=24)
    period_type: str = Field(default="monthly")
    method: str = Field(default="ai_api")


class ForecastResponse(BaseModel):
    """Response schema for forecast."""
    id: UUID
    product_id: UUID
    forecast_date: date
    predicted_quantity: float
    confidence_lower: Optional[float]
    confidence_upper: Optional[float]
    confidence_score: float
    method: str


class ChatRequest(BaseModel):
    """Request schema for chat."""
    session_id: Optional[UUID] = None
    message: str = Field(..., min_length=1, max_length=2000)
    context: Optional[dict] = None


class ChatResponse(BaseModel):
    """Response schema for chat."""
    session_id: UUID
    message_id: UUID
    content: str
    intent: Optional[str]
    actions_taken: List[str] = []


class OCRResultResponse(BaseModel):
    """Response schema for OCR result."""
    id: UUID
    status: str
    invoice_number: Optional[str]
    invoice_date: Optional[date]
    partner_name: Optional[str]
    total_amount: Optional[float]
    confidence: float
    validation_errors: List[str]
    extracted_data: dict


# ========================================
# Forecasting Endpoints
# ========================================

@router.post("/forecast/product/{product_id}")
async def generate_product_forecast(
    product_id: UUID,
    periods: int = Query(6, ge=1, le=24),
    period_type: str = Query("monthly"),
    forecast_type: str = Query("demand"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate demand forecast for a specific product."""
    await require_permission(current_user, "ai.forecast.create")
    
    service = ForecastingService(db)
    
    try:
        forecast_type_enum = ForecastType(forecast_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid forecast type")
    
    forecasts = await service.generate_product_forecast(
        product_id=product_id,
        tenant_id=current_user.tenant_id,
        forecast_type=forecast_type_enum,
        periods=periods,
        period_type=period_type,
        user_id=current_user.id
    )
    
    return {
        "product_id": str(product_id),
        "forecasts": [
            {
                "id": str(f.id),
                "forecast_date": f.forecast_date.isoformat(),
                "predicted_quantity": float(f.predicted_quantity),
                "predicted_value": float(f.predicted_value),
                "confidence_lower": float(f.confidence_lower) if f.confidence_lower else None,
                "confidence_upper": float(f.confidence_upper) if f.confidence_upper else None,
                "confidence_score": f.confidence_score,
                "method": f.method.value
            }
            for f in forecasts
        ]
    }


@router.get("/forecast/dashboard")
async def get_forecast_dashboard(
    top_n: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get forecast dashboard with top products and alerts."""
    await require_permission(current_user, "ai.forecast.read")
    
    service = ForecastingService(db)
    dashboard = await service.generate_dashboard_forecasts(
        tenant_id=current_user.tenant_id,
        top_n=top_n
    )
    
    return dashboard


@router.get("/forecast/product/{product_id}")
async def get_product_forecasts(
    product_id: UUID,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get existing forecasts for a product."""
    await require_permission(current_user, "ai.forecast.read")
    
    service = ForecastingService(db)
    forecasts = await service.get_product_forecasts(
        product_id=product_id,
        tenant_id=current_user.tenant_id,
        from_date=from_date,
        to_date=to_date
    )
    
    return {
        "product_id": str(product_id),
        "forecasts": [
            {
                "id": str(f.id),
                "forecast_date": f.forecast_date.isoformat(),
                "predicted_quantity": float(f.predicted_quantity),
                "actual_quantity": float(f.actual_quantity) if f.actual_quantity else None,
                "accuracy_score": f.accuracy_score,
                "confidence_score": f.confidence_score
            }
            for f in forecasts
        ]
    }


@router.get("/forecast/{product_id}/accuracy")
async def get_forecast_accuracy(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get forecast accuracy metrics for a product."""
    await require_permission(current_user, "ai.forecast.read")
    
    service = ForecastingService(db)
    accuracy = await service.calculate_forecast_accuracy(
        product_id=product_id,
        tenant_id=current_user.tenant_id
    )
    
    return accuracy


# ========================================
# OCR Endpoints
# ========================================

@router.post("/parse-invoice", response_model=OCRResultResponse)
async def parse_invoice(
    file: UploadFile = File(...),
    document_type: str = Query("invoice"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Parse an invoice image/PDF and extract data.
    
    Supported formats: PDF, JPEG, PNG
    """
    await require_permission(current_user, "ai.ocr.create")
    
    # Validate file type
    allowed_types = ["application/pdf", "image/jpeg", "image/png", "image/jpg"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}"
        )
    
    # Read file content
    content = await file.read()
    
    # Process with OCR
    service = OCRService(db)
    
    try:
        result = await service.process_invoice(
            file_content=content,
            filename=file.filename or "uploaded_file",
            tenant_id=current_user.tenant_id,
            document_type=document_type,
            user_id=current_user.id
        )
        
        return OCRResultResponse(
            id=result.id,
            status=result.status.value,
            invoice_number=result.invoice_number,
            invoice_date=result.invoice_date,
            partner_name=result.partner_name,
            total_amount=float(result.total_amount) if result.total_amount else None,
            confidence=result.overall_confidence,
            validation_errors=result.validation_errors,
            extracted_data=result.extracted_data
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ocr/results")
async def list_ocr_results(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List OCR processing results."""
    await require_permission(current_user, "ai.ocr.read")
    
    service = OCRService(db)
    
    status_enum = None
    if status:
        try:
            status_enum = OCRStatus(status)
        except ValueError:
            pass
    
    results, total = await service.list_ocr_results(
        tenant_id=current_user.tenant_id,
        status=status_enum,
        page=page,
        page_size=page_size
    )
    
    return {
        "items": [
            {
                "id": str(r.id),
                "document_type": r.document_type,
                "original_filename": r.original_filename,
                "status": r.status.value,
                "invoice_number": r.invoice_number,
                "partner_name": r.partner_name,
                "total_amount": float(r.total_amount) if r.total_amount else None,
                "confidence": r.overall_confidence,
                "created_at": r.created_at.isoformat()
            }
            for r in results
        ],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/ocr/results/{ocr_id}")
async def get_ocr_result(
    ocr_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed OCR result."""
    await require_permission(current_user, "ai.ocr.read")
    
    service = OCRService(db)
    result = await service.get_ocr_result(ocr_id, current_user.tenant_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="OCR result not found")
    
    return {
        "id": str(result.id),
        "document_type": result.document_type,
        "original_filename": result.original_filename,
        "status": result.status.value,
        "invoice_number": result.invoice_number,
        "invoice_date": result.invoice_date.isoformat() if result.invoice_date else None,
        "due_date": result.due_date.isoformat() if result.due_date else None,
        "partner_name": result.partner_name,
        "partner_tax_id": result.partner_tax_id,
        "subtotal": float(result.subtotal) if result.subtotal else None,
        "tax_amount": float(result.tax_amount) if result.tax_amount else None,
        "total_amount": float(result.total_amount) if result.total_amount else None,
        "currency": result.currency,
        "line_items": result.line_items,
        "raw_text": result.raw_text,
        "extracted_data": result.extracted_data,
        "confidence": result.overall_confidence,
        "field_confidence": result.field_confidence,
        "validation_errors": result.validation_errors,
        "validation_warnings": result.validation_warnings,
        "processing_notes": result.processing_notes
    }


@router.post("/ocr/results/{ocr_id}/create-invoice")
async def create_invoice_from_ocr(
    ocr_id: UUID,
    corrections: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create an invoice from OCR result with optional corrections."""
    await require_permission(current_user, "ai.ocr.create")
    
    service = OCRService(db)
    
    try:
        invoice_data = await service.create_invoice_from_ocr(
            ocr_id=ocr_id,
            tenant_id=current_user.tenant_id,
            corrections=corrections,
            user_id=current_user.id
        )
        
        return invoice_data
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ========================================
# Chatbot Endpoints
# ========================================

@router.post("/chat/session")
async def create_chat_session(
    context: Optional[dict] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new chat session."""
    await require_permission(current_user, "ai.chat.create")
    
    service = ChatbotService(db)
    session = await service.create_session(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        context=context
    )
    
    return {
        "session_id": str(session.id),
        "title": session.title,
        "created_at": session.created_at.isoformat()
    }


@router.post("/chat/message", response_model=ChatResponse)
async def send_chat_message(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a message to the chatbot and get response."""
    await require_permission(current_user, "ai.chat.create")
    
    service = ChatbotService(db)
    
    # Create session if not provided
    if not request.session_id:
        session = await service.create_session(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            context=request.context
        )
        session_id = session.id
    else:
        session_id = request.session_id
    
    # Process message
    try:
        operation_permissions = {
            "get_stock": "inventory.stock.view",
            "get_sales": "sales.orders.view",
            "get_purchases": "purchase.orders.view",
            "get_accounts": "accounting.accounts.view"
        }
        allowed_operations = [
            operation for operation, permission in operation_permissions.items()
            if getattr(current_user, "is_superuser", False) or current_user.has_permission(permission)
        ]
        response = await service.process_message(
            session_id=session_id,
            user_message=request.message,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            allowed_operations=allowed_operations
        )
        
        return ChatResponse(
            session_id=session_id,
            message_id=response.id,
            content=response.content,
            intent=response.intent,
            actions_taken=response.actions_taken or []
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/chat/stream")
async def stream_chat_message(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Stream chat response for real-time display."""
    await require_permission(current_user, "ai.chat.create")
    
    service = ChatbotService(db)
    
    # Create session if not provided
    if not request.session_id:
        session = await service.create_session(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            context=request.context
        )
        session_id = session.id
    else:
        session_id = request.session_id
    
    return StreamingResponse(
        service.stream_message(
            session_id=session_id,
            user_message=request.message,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id
        ),
        media_type="text/event-stream"
    )


@router.get("/chat/sessions")
async def list_chat_sessions(
    active_only: bool = True,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List chat sessions for the current user."""
    await require_permission(current_user, "ai.chat.read")
    
    service = ChatbotService(db)
    sessions, total = await service.list_sessions(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        active_only=active_only,
        page=page,
        page_size=page_size
    )
    
    return {
        "items": [
            {
                "id": str(s.id),
                "title": s.title,
                "message_count": s.message_count,
                "is_active": s.is_active,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat()
            }
            for s in sessions
        ],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/chat/sessions/{session_id}")
async def get_chat_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a chat session with messages."""
    await require_permission(current_user, "ai.chat.read")
    
    service = ChatbotService(db)
    session = await service.get_session(session_id, current_user.id, current_user.tenant_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "id": str(session.id),
        "title": session.title,
        "context": session.context,
        "message_count": session.message_count,
        "is_active": session.is_active,
        "created_at": session.created_at.isoformat(),
        "messages": [
            {
                "id": str(m.id),
                "type": m.message_type.value,
                "content": m.content,
                "intent": m.intent,
                "created_at": m.created_at.isoformat()
            }
            for m in session.messages
        ]
    }


@router.get("/chat/quick-query")
async def quick_query(
    query_type: str = Query(..., description="Type of quick query"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Execute a quick pre-defined query."""
    await require_permission(current_user, "ai.chat.read")
    query_permissions = {
        "dashboard_summary": ["reports.all.view"],
        "low_stock": ["inventory.stock.view"],
        "pending_orders": ["sales.orders.view", "purchase.orders.view"]
    }
    required = query_permissions.get(query_type)
    if required is None:
        raise HTTPException(status_code=400, detail="Unknown quick query type")
    if not getattr(current_user, "is_superuser", False):
        missing = [permission for permission in required if not current_user.has_permission(permission)]
        if missing:
            raise HTTPException(status_code=403, detail="Permission required for this quick query")
    
    service = ChatbotService(db)
    result = await service.quick_query(
        query_type=query_type,
        tenant_id=current_user.tenant_id
    )
    
    return result
