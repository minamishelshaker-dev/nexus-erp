"""
Nexus ERP - AI Chatbot Service
===============================

Intelligent chatbot service for ERP assistance.
Provides natural language interface to ERP data and operations.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any, AsyncGenerator
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
import logging
import json
import re

from app.models.ai import ChatSession, ChatMessage, ChatMessageType
from app.models.user import User
from app.models.sales import SaleOrder, Invoice
from app.models.purchase import PurchaseOrder
from app.models.inventory import Product, StockMove
from app.models.accounting import Account, JournalEntry
from app.core.config import settings

logger = logging.getLogger(__name__)


# System prompt for the ERP assistant
ERP_SYSTEM_PROMPT = """أنت مساعد ذكي لنظام Nexus ERP. مهمتك هي مساعدة المستخدمين في:
1. الاستعلام عن البيانات (المخزون، المبيعات، المشتريات، المحاسبة)
2. تنفيذ العمليات (إنشاء أوامر، فواتير، إلخ)
3. الإجابة على الأسئلة حول سياسات الشركة والإجراءات
4. تقديم تحليلات وتوصيات

قواعد مهمة:
- أجب دائماً باللغة العربية ما لم يطلب المستخدم غير ذلك
- كن دقيقاً في البيانات المقدمة
- إذا لم تكن متأكداً من إجابة، اطلب توضيحاً
- عند تنفيذ عمليات، أطلب تأكيداً من المستخدم
- قدم الأرقام بشكل منسق وواضح

البيانات المتاحة:
- المنتجات والمخزون
- أوامر البيع والشراء
- الفواتير
- الحسابات المحاسبية
- حركات المخزون

عندما تحتاج لتنفيذ استعلام أو عملية، أرجع JSON في التنسيق التالي:
{"action": "query|execute", "operation": "operation_name", "params": {...}}

العمليات المتاحة:
- get_stock: الحصول على رصيد المخزون
- get_sales: الحصول على بيانات المبيعات
- get_purchases: الحصول على بيانات المشتريات
- get_accounts: الحصول على أرصدة الحسابات
- create_order: إنشاء أمر جديد (يتطلب تأكيد)
"""


class ChatbotService:
    """
    Chatbot Service
    
    Provides AI-powered conversational interface for ERP operations.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ========================================
    # Session Management
    # ========================================
    
    async def create_session(
        self,
        user_id: UUID,
        tenant_id: UUID,
        context: Optional[Dict] = None,
        title: Optional[str] = None
    ) -> ChatSession:
        """Create a new chat session."""
        session = ChatSession(
            tenant_id=tenant_id,
            user_id=user_id,
            title=title or f"محادثة {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            context=context or {}
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session
    
    async def get_session(
        self,
        session_id: UUID,
        user_id: UUID,
        tenant_id: UUID
    ) -> Optional[ChatSession]:
        """Get a chat session scoped to its owner and active tenant."""
        if tenant_id is None:
            return None
        result = await self.db.execute(
            select(ChatSession)
            .options(selectinload(ChatSession.messages))
            .where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
                ChatSession.tenant_id == tenant_id,
                ChatSession.is_deleted == False
            )
        )
        return result.scalar_one_or_none()
    
    async def list_sessions(
        self,
        user_id: UUID,
        tenant_id: UUID,
        active_only: bool = True,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[ChatSession], int]:
        """List chat sessions for a user."""
        query = select(ChatSession).where(
            ChatSession.user_id == user_id,
            ChatSession.tenant_id == tenant_id,
            ChatSession.is_deleted == False
        )
        
        if active_only:
            query = query.where(ChatSession.is_active == True)
        
        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)
        
        # Paginate
        query = query.order_by(ChatSession.updated_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        return list(result.scalars().all()), total or 0
    
    # ========================================
    # Chat Processing
    # ========================================
    
    async def process_message(
        self,
        session_id: UUID,
        user_message: str,
        tenant_id: UUID,
        user_id: UUID,
        allowed_operations: Optional[List[str]] = None
    ) -> ChatMessage:
        """
        Process a user message and generate AI response.
        
        Args:
            session_id: Chat session ID
            user_message: User's message text
            tenant_id: Tenant UUID
            user_id: User UUID
            
        Returns:
            Assistant's response message
        """
        # Get session
        session = await self.get_session(session_id, user_id, tenant_id)
        if not session:
            raise ValueError("Session not found")
        
        # Store user message
        user_msg = ChatMessage(
            session_id=session_id,
            message_type=ChatMessageType.USER,
            content=user_message
        )
        self.db.add(user_msg)
        await self.db.flush()
        
        # Get conversation history
        history = session.messages[-10:]  # Last 10 messages for context
        
        # Process with AI
        response_data = await self._process_with_ai(
            user_message,
            history,
            session.context,
            tenant_id
        )
        
        # Execute any actions
        actions_taken = []
        data_results = {}
        
        if response_data.get("actions"):
            for action in response_data["actions"]:
                result = await self._execute_action(action, tenant_id, allowed_operations or [])
                actions_taken.append(action.get("operation"))
                data_results[action.get("operation")] = result
        
        # Store assistant response
        assistant_msg = ChatMessage(
            session_id=session_id,
            message_type=ChatMessageType.ASSISTANT,
            content=response_data["content"],
            intent=response_data.get("intent"),
            entities=response_data.get("entities", {}),
            actions_taken=actions_taken,
            data_results=data_results,
            prompt_tokens=response_data.get("prompt_tokens", 0),
            completion_tokens=response_data.get("completion_tokens", 0),
            total_tokens=response_data.get("total_tokens", 0),
            model_used=response_data.get("model")
        )
        self.db.add(assistant_msg)
        
        # Update session
        session.message_count += 2
        session.tokens_used += response_data.get("total_tokens", 0)
        
        await self.db.commit()
        await self.db.refresh(assistant_msg)
        
        return assistant_msg
    
    async def stream_message(
        self,
        session_id: UUID,
        user_message: str,
        tenant_id: UUID,
        user_id: UUID
    ) -> AsyncGenerator[str, None]:
        """
        Stream AI response for real-time display.
        
        Yields response chunks as they are generated.
        """
        try:
            from openai import AsyncOpenAI
            
            api_key = getattr(settings, 'OPENAI_API_KEY', None)
            if not api_key:
                yield f"data: {json.dumps({'error': 'OpenAI API key not configured'})}\n\n"
                return
            
            client = AsyncOpenAI(api_key=api_key)
            
            # Get session and history
            session = await self.get_session(session_id, user_id, tenant_id)
            if not session:
                raise ValueError("Session not found")
            
            # Build messages
            messages = [{"role": "system", "content": ERP_SYSTEM_PROMPT}]
            
            for msg in session.messages[-5:]:  # Last 5 messages
                messages.append({
                    "role": "user" if msg.message_type == ChatMessageType.USER else "assistant",
                    "content": msg.content
                })
            
            messages.append({"role": "user", "content": user_message})
            
            # Stream completion
            full_response = ""
            async for chunk in await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                stream=True,
                temperature=0.7
            ):
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield f"data: {json.dumps({'content': content})}\n\n"
            
            # Store messages after streaming
            user_msg = ChatMessage(
                session_id=session_id,
                message_type=ChatMessageType.USER,
                content=user_message
            )
            self.db.add(user_msg)
            
            assistant_msg = ChatMessage(
                session_id=session_id,
                message_type=ChatMessageType.ASSISTANT,
                content=full_response
            )
            self.db.add(assistant_msg)
            
            session.message_count += 2
            await self.db.commit()
            
            yield f"data: {json.dumps({'done': True})}\n\n"
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    # ========================================
    # AI Processing
    # ========================================
    
    async def _process_with_ai(
        self,
        user_message: str,
        history: List[ChatMessage],
        context: Dict,
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """Process message with AI and return structured response."""
        try:
            from openai import AsyncOpenAI
            
            api_key = getattr(settings, 'OPENAI_API_KEY', None)
            if not api_key:
                return {
                    "content": "عذراً، خدمة الذكاء الاصطناعي غير متوفرة حالياً. يرجى التواصل مع الدعم الفني.",
                    "actions": []
                }
            
            client = AsyncOpenAI(api_key=api_key)
            
            # Build messages
            messages = [
                {"role": "system", "content": ERP_SYSTEM_PROMPT},
                {"role": "system", "content": f"Context: {json.dumps(context)}"}
            ]
            
            for msg in history:
                messages.append({
                    "role": "user" if msg.message_type == ChatMessageType.USER else "assistant",
                    "content": msg.content
                })
            
            messages.append({"role": "user", "content": user_message})
            
            # Get completion
            completion = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            response_content = completion.choices[0].message.content
            
            # Extract any JSON actions
            actions = []
            json_matches = re.findall(r'\{[^{}]*"action"[^{}]*\}', response_content)
            for match in json_matches:
                try:
                    action = json.loads(match)
                    actions.append(action)
                except json.JSONDecodeError:
                    pass
            
            # Extract intent and entities
            intent = self._extract_intent(user_message)
            entities = self._extract_entities(user_message)
            
            return {
                "content": response_content,
                "intent": intent,
                "entities": entities,
                "actions": actions,
                "prompt_tokens": completion.usage.prompt_tokens if hasattr(completion, 'usage') else 0,
                "completion_tokens": completion.usage.completion_tokens if hasattr(completion, 'usage') else 0,
                "total_tokens": completion.usage.total_tokens if hasattr(completion, 'usage') else 0,
                "model": settings.OPENAI_MODEL
            }
            
        except Exception as e:
            logger.error(f"AI processing error: {e}")
            return {
                "content": f"عذراً، حدث خطأ في المعالجة. يرجى المحاولة مرة أخرى. ({str(e)})",
                "actions": []
            }
    
    def _extract_intent(self, message: str) -> str:
        """Extract user intent from message."""
        message_lower = message.lower()
        
        intents = {
            "stock_query": ["رصيد", "مخزون", "كمية", "stock", "inventory"],
            "sales_query": ["مبيعات", "بيع", "أمر بيع", "sales", "order"],
            "purchase_query": ["مشتريات", "شراء", "أمر شراء", "purchase"],
            "account_query": ["حساب", "رصيد حساب", "account", "balance"],
            "create_order": ["إنشاء", "أمر جديد", "create", "new order"],
            "help": ["مساعدة", "كيف", "ما هي", "help", "how to"]
        }
        
        for intent, keywords in intents.items():
            if any(kw in message_lower for kw in keywords):
                return intent
        
        return "general_query"
    
    def _extract_entities(self, message: str) -> Dict[str, Any]:
        """Extract entities from message."""
        entities = {}
        
        # Extract dates
        date_patterns = [
            (r'(\d{4}-\d{2}-\d{2})', 'date'),
            (r'(\d{2}/\d{2}/\d{4})', 'date'),
            (r'اليوم', 'today'),
            (r'أمس', 'yesterday'),
            (r'هذا الشهر', 'this_month'),
            (r'الشهر الماضي', 'last_month')
        ]
        
        for pattern, key in date_patterns:
            if re.search(pattern, message):
                entities['date_filter'] = key
                break
        
        # Extract numbers
        numbers = re.findall(r'\b\d+(?:\.\d+)?\b', message)
        if numbers:
            entities['numbers'] = [float(n) for n in numbers]
        
        # Extract product names (heuristic)
        product_pattern = r'منتج[:\s]+([^\s,\.]+)|المنتج\s+([^\s,\.]+)'
        match = re.search(product_pattern, message)
        if match:
            entities['product'] = match.group(1) or match.group(2)
        
        return entities
    
    # ========================================
    # Action Execution
    # ========================================
    
    async def _execute_action(
        self,
        action: Dict,
        tenant_id: UUID,
        allowed_operations: List[str]
    ) -> Dict[str, Any]:
        """Execute only read operations explicitly authorized by the caller."""
        operation = action.get("operation")
        params = action.get("params", {})
        if operation not in allowed_operations:
            return {"error": "Permission required for this data operation"}
        
        if operation == "get_stock":
            return await self._action_get_stock(tenant_id, params)
        elif operation == "get_sales":
            return await self._action_get_sales(tenant_id, params)
        elif operation == "get_purchases":
            return await self._action_get_purchases(tenant_id, params)
        elif operation == "get_accounts":
            return await self._action_get_accounts(tenant_id, params)
        else:
            return {"error": f"Unknown operation: {operation}"}
    
    async def _action_get_stock(self, tenant_id: UUID, params: Dict) -> Dict:
        """Get stock information."""
        product_name = params.get("product")
        
        query = select(Product).where(
            Product.tenant_id == tenant_id,
            Product.is_deleted == False
        )
        
        if product_name:
            query = query.where(Product.name.ilike(f"%{product_name}%"))
        
        query = query.limit(10)
        
        result = await self.db.execute(query)
        products = result.scalars().all()
        
        return {
            "products": [
                {
                    "name": p.name,
                    "sku": p.sku,
                    "quantity_on_hand": float(p.quantity_on_hand),
                    "quantity_available": float(p.quantity_available),
                    "average_cost": float(p.average_cost)
                }
                for p in products
            ]
        }
    
    async def _action_get_sales(self, tenant_id: UUID, params: Dict) -> Dict:
        """Get sales information."""
        days = params.get("days", 30)
        
        from datetime import timedelta
        start_date = date.today() - timedelta(days=days)
        
        # Get sales summary
        result = await self.db.execute(
            select(
                func.count(SaleOrder.id).label("total_orders"),
                func.sum(SaleOrder.amount_total).label("total_amount")
            )
            .where(
                SaleOrder.tenant_id == tenant_id,
                SaleOrder.date_order >= start_date
            )
        )
        
        summary = result.one()
        
        return {
            "period_days": days,
            "total_orders": summary.total_orders or 0,
            "total_amount": float(summary.total_amount or 0)
        }
    
    async def _action_get_purchases(self, tenant_id: UUID, params: Dict) -> Dict:
        """Get purchases information."""
        days = params.get("days", 30)
        
        from datetime import timedelta
        start_date = date.today() - timedelta(days=days)
        
        result = await self.db.execute(
            select(
                func.count(PurchaseOrder.id).label("total_orders"),
                func.sum(PurchaseOrder.amount_total).label("total_amount")
            )
            .where(
                PurchaseOrder.tenant_id == tenant_id,
                PurchaseOrder.date_order >= start_date
            )
        )
        
        summary = result.one()
        
        return {
            "period_days": days,
            "total_orders": summary.total_orders or 0,
            "total_amount": float(summary.total_amount or 0)
        }
    
    async def _action_get_accounts(self, tenant_id: UUID, params: Dict) -> Dict:
        """Get account information."""
        account_code = params.get("account_code")
        
        query = select(Account).where(
            Account.tenant_id == tenant_id,
            Account.is_deleted == False
        )
        
        if account_code:
            query = query.where(Account.code.like(f"{account_code}%"))
        
        query = query.limit(20)
        
        result = await self.db.execute(query)
        accounts = result.scalars().all()
        
        return {
            "accounts": [
                {
                    "code": a.code,
                    "name": a.name,
                    "balance": float(a.balance),
                    "type": a.account_type.value
                }
                for a in accounts
            ]
        }
    
    # ========================================
    # Quick Queries
    # ========================================
    
    async def quick_query(
        self,
        query_type: str,
        tenant_id: UUID,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Execute quick pre-defined queries.
        
        Args:
            query_type: Type of quick query
            tenant_id: Tenant UUID
            params: Optional parameters
            
        Returns:
            Query results
        """
        params = params or {}
        
        if query_type == "dashboard_summary":
            return await self._dashboard_summary(tenant_id)
        elif query_type == "low_stock":
            return await self._low_stock_alerts(tenant_id)
        elif query_type == "pending_orders":
            return await self._pending_orders(tenant_id)
        else:
            return {"error": f"Unknown query type: {query_type}"}
    
    async def _dashboard_summary(self, tenant_id: UUID) -> Dict:
        """Get dashboard summary."""
        from datetime import timedelta
        
        today = date.today()
        month_start = date(today.year, today.month, 1)
        
        # Sales this month
        sales_result = await self.db.execute(
            select(func.sum(SaleOrder.amount_total))
            .where(
                SaleOrder.tenant_id == tenant_id,
                SaleOrder.date_order >= month_start
            )
        )
        sales_total = sales_result.scalar() or 0
        
        # Purchases this month
        purchases_result = await self.db.execute(
            select(func.sum(PurchaseOrder.amount_total))
            .where(
                PurchaseOrder.tenant_id == tenant_id,
                PurchaseOrder.date_order >= month_start
            )
        )
        purchases_total = purchases_result.scalar() or 0
        
        # Low stock count
        low_stock_result = await self.db.execute(
            select(func.count(Product.id))
            .where(
                Product.tenant_id == tenant_id,
                Product.is_deleted == False,
                Product.quantity_on_hand <= Product.reorder_point
            )
        )
        low_stock_count = low_stock_result.scalar() or 0
        
        return {
            "sales_this_month": float(sales_total),
            "purchases_this_month": float(purchases_total),
            "low_stock_products": low_stock_count,
            "generated_at": datetime.now().isoformat()
        }
    
    async def _low_stock_alerts(self, tenant_id: UUID) -> Dict:
        """Get low stock alerts."""
        result = await self.db.execute(
            select(Product)
            .where(
                Product.tenant_id == tenant_id,
                Product.is_deleted == False,
                Product.quantity_on_hand <= Product.reorder_point
            )
            .limit(20)
        )
        
        products = result.scalars().all()
        
        return {
            "alerts": [
                {
                    "product": p.name,
                    "sku": p.sku,
                    "current_stock": float(p.quantity_on_hand),
                    "reorder_point": float(p.reorder_point),
                    "shortage": float(p.reorder_point - p.quantity_on_hand)
                }
                for p in products
            ]
        }
    
    async def _pending_orders(self, tenant_id: UUID) -> Dict:
        """Get pending orders."""
        # Pending sale orders
        sale_orders = await self.db.execute(
            select(SaleOrder)
            .where(
                SaleOrder.tenant_id == tenant_id,
                SaleOrder.state.in_(["draft", "confirmed"])
            )
            .limit(10)
        )
        
        # Pending purchase orders
        purchase_orders = await self.db.execute(
            select(PurchaseOrder)
            .where(
                PurchaseOrder.tenant_id == tenant_id,
                PurchaseOrder.state.in_(["draft", "confirmed", "approved"])
            )
            .limit(10)
        )
        
        return {
            "pending_sale_orders": [
                {
                    "number": o.number,
                    "amount": float(o.amount_total),
                    "state": o.state
                }
                for o in sale_orders.scalars().all()
            ],
            "pending_purchase_orders": [
                {
                    "number": o.number,
                    "amount": float(o.amount_total),
                    "state": o.state
                }
                for o in purchase_orders.scalars().all()
            ]
        }


# Import selectinload for relationships
from sqlalchemy.orm import selectinload
