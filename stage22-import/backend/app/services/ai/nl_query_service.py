"""
Nexus ERP - Natural Language Query Service
===========================================

Converts natural language questions to database queries.

Features:
- Intent classification for business queries
- Entity extraction (dates, amounts, products, customers)
- SQL query generation from natural language
- Response generation in natural language
- Safety: tenant isolation, read-only by default
- Example queries supported:
  - "Show me profit drop last month"
  - "What are the top selling products"
  - "Which customers haven't ordered in 60 days"
  - "Compare this year sales vs last year"
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple, Union
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, not_, text, desc, asc
from sqlalchemy.orm import selectinload
from dataclasses import dataclass, field
from enum import Enum
import logging
import json
import re
from collections import defaultdict
import asyncio

from app.models.sales import SaleOrder, SaleOrderLine, Invoice
from app.models.purchase import PurchaseOrder, PurchaseOrderLine
from app.models.inventory import Product, StockMove
from app.models.accounting import Account, JournalEntry, JournalItem
from app.models.crm import Customer
from app.core.config import settings

logger = logging.getLogger(__name__)


# ========================================
# Enums and Data Classes
# ========================================

class QueryIntent(str, Enum):
    """Types of query intents."""
    # Sales queries
    SALES_SUMMARY = "sales_summary"
    TOP_PRODUCTS = "top_products"
    SALES_COMPARISON = "sales_comparison"
    SALES_TREND = "sales_trend"
    
    # Customer queries
    CUSTOMER_LIST = "customer_list"
    INACTIVE_CUSTOMERS = "inactive_customers"
    CUSTOMER_DETAILS = "customer_details"
    TOP_CUSTOMERS = "top_customers"
    
    # Inventory queries
    STOCK_STATUS = "stock_status"
    LOW_STOCK = "low_stock"
    PRODUCT_DETAILS = "product_details"
    
    # Financial queries
    REVENUE = "revenue"
    PROFIT = "profit"
    EXPENSES = "expenses"
    ACCOUNT_BALANCE = "account_balance"
    
    # Comparison queries
    PERIOD_COMPARISON = "period_comparison"
    YEAR_OVER_YEAR = "year_over_year"
    
    # General
    UNKNOWN = "unknown"


class EntityType(str, Enum):
    """Types of entities that can be extracted."""
    DATE = "date"
    DATE_RANGE = "date_range"
    AMOUNT = "amount"
    PRODUCT = "product"
    CUSTOMER = "customer"
    ACCOUNT = "account"
    PERIOD = "period"
    NUMBER = "number"


class QuerySafetyLevel(str, Enum):
    """Safety levels for generated queries."""
    SAFE = "safe"  # Read-only, safe
    RESTRICTED = "restricted"  # Requires approval
    DANGEROUS = "dangerous"  # Not allowed


@dataclass
class ExtractedEntity:
    """Extracted entity from natural language."""
    entity_type: EntityType
    value: Any
    raw_text: str
    confidence: float = 1.0


@dataclass
class ParsedQuery:
    """Parsed natural language query."""
    original_text: str
    intent: QueryIntent
    entities: List[ExtractedEntity]
    filters: Dict[str, Any]
    aggregations: List[str]
    ordering: Optional[Tuple[str, str]] = None
    limit: Optional[int] = None
    confidence: float = 1.0


@dataclass
class GeneratedQuery:
    """Generated SQL query with metadata."""
    sql: str
    params: Dict[str, Any]
    safety_level: QuerySafetyLevel
    tables_accessed: List[str]
    estimated_rows: Optional[int] = None
    explanation: str = ""


@dataclass
class QueryResult:
    """Result of executing a natural language query."""
    success: bool
    data: List[Dict[str, Any]]
    summary: str
    explanation: str
    query_sql: str
    row_count: int
    execution_time_ms: float
    visualizations: List[Dict[str, Any]] = field(default_factory=list)


# ========================================
# Intent Classifier
# ========================================

class IntentClassifier:
    """
    Classifies the intent of natural language queries.
    """
    
    # Intent patterns with keywords and phrases
    INTENT_PATTERNS = {
        QueryIntent.SALES_SUMMARY: {
            "keywords": ["sales", "sold", "revenue", "sell", "selling"],
            "patterns": [
                r"show.*sales",
                r"total.*sales",
                r"sales.*(summary|report|overview)",
                r"how much.*sold",
                r"revenue.*last",
            ]
        },
        QueryIntent.TOP_PRODUCTS: {
            "keywords": ["top", "best", "popular", "selling", "products"],
            "patterns": [
                r"top.*products?",
                r"best.*selling",
                r"most.*popular",
                r"highest.*sales",
                r"top.*selling",
            ]
        },
        QueryIntent.SALES_COMPARISON: {
            "keywords": ["compare", "versus", "vs", "difference", "against"],
            "patterns": [
                r"compare.*sales",
                r"sales.*vs",
                r"difference.*between",
                r"this.*vs.*last",
            ]
        },
        QueryIntent.SALES_TREND: {
            "keywords": ["trend", "pattern", "over time", "growth", "decline"],
            "patterns": [
                r"sales.*trend",
                r"trend.*sales",
                r"sales.*over.*time",
                r"growth.*pattern",
            ]
        },
        QueryIntent.INACTIVE_CUSTOMERS: {
            "keywords": ["inactive", "haven't", "not ordered", "no order", "missing"],
            "patterns": [
                r"customers?.*haven'?t",
                r"customers?.*not.*order",
                r"inactive.*customers?",
                r"no.*order.*days?",
                r"which.*customers?.*not",
            ]
        },
        QueryIntent.CUSTOMER_LIST: {
            "keywords": ["customers", "clients", "buyers"],
            "patterns": [
                r"list.*customers?",
                r"show.*customers?",
                r"all.*customers?",
                r"customer.*list",
            ]
        },
        QueryIntent.TOP_CUSTOMERS: {
            "keywords": ["top", "best", "highest", "most"],
            "patterns": [
                r"top.*customers?",
                r"best.*customers?",
                r"customers?.*most.*purchase",
                r"highest.*spending",
            ]
        },
        QueryIntent.STOCK_STATUS: {
            "keywords": ["stock", "inventory", "quantity", "available"],
            "patterns": [
                r"stock.*status",
                r"inventory.*level",
                r"current.*stock",
                r"how much.*stock",
            ]
        },
        QueryIntent.LOW_STOCK: {
            "keywords": ["low", "out", "shortage", "reorder", "critical"],
            "patterns": [
                r"low.*stock",
                r"stock.*out",
                r"need.*reorder",
                r"below.*minimum",
                r"critical.*stock",
            ]
        },
        QueryIntent.REVENUE: {
            "keywords": ["revenue", "income", "earnings"],
            "patterns": [
                r"total.*revenue",
                r"show.*revenue",
                r"revenue.*this",
                r"how much.*revenue",
            ]
        },
        QueryIntent.PROFIT: {
            "keywords": ["profit", "margin", "earnings", "net"],
            "patterns": [
                r"profit.*drop",
                r"show.*profit",
                r"profit.*margin",
                r"net.*income",
                r"gross.*profit",
            ]
        },
        QueryIntent.EXPENSES: {
            "keywords": ["expenses", "costs", "spending", "expenditure"],
            "patterns": [
                r"total.*expenses",
                r"show.*expenses",
                r"expense.*report",
                r"costs.*this",
            ]
        },
        QueryIntent.YEAR_OVER_YEAR: {
            "keywords": ["year", "yoy", "annual", "compared"],
            "patterns": [
                r"this.*year.*vs.*last",
                r"year.*over.*year",
                r"yoy",
                r"compare.*years?",
                r"annual.*comparison",
            ]
        },
        QueryIntent.PERIOD_COMPARISON: {
            "keywords": ["month", "quarter", "period", "last", "this"],
            "patterns": [
                r"this.*month.*vs",
                r"last.*month",
                r"this.*quarter",
                r"previous.*period",
            ]
        },
    }
    
    @classmethod
    def classify(cls, text: str) -> Tuple[QueryIntent, float]:
        """
        Classify the intent of a natural language query.
        
        Returns (intent, confidence)
        """
        text_lower = text.lower()
        scores: Dict[QueryIntent, float] = defaultdict(float)
        
        for intent, config in cls.INTENT_PATTERNS.items():
            # Check keywords
            keyword_matches = sum(1 for kw in config["keywords"] if kw in text_lower)
            scores[intent] += keyword_matches * 0.3
            
            # Check patterns
            for pattern in config["patterns"]:
                if re.search(pattern, text_lower):
                    scores[intent] += 0.5
        
        if not scores:
            return QueryIntent.UNKNOWN, 0.0
        
        best_intent = max(scores, key=scores.get)
        confidence = min(1.0, scores[best_intent])
        
        return best_intent, confidence


# ========================================
# Entity Extractor
# ========================================

class EntityExtractor:
    """
    Extracts entities from natural language queries.
    """
    
    # Date patterns
    DATE_PATTERNS = [
        # ISO format
        (r"(\d{4}-\d{2}-\d{2})", "iso"),
        # DD/MM/YYYY or MM/DD/YYYY
        (r"(\d{1,2}/\d{1,2}/\d{4})", "slash"),
        # Month name patterns
        (r"(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})?(?:\s*,?\s*(\d{4}))?", "month_name"),
        # Relative dates
        (r"today", "relative"),
        (r"yesterday", "relative"),
        (r"this\s+week", "relative"),
        (r"last\s+week", "relative"),
        (r"this\s+month", "relative"),
        (r"last\s+month", "relative"),
        (r"this\s+quarter", "relative"),
        (r"last\s+quarter", "relative"),
        (r"this\s+year", "relative"),
        (r"last\s+year", "relative"),
        (r"past\s+(\d+)\s+days?", "relative_days"),
        (r"last\s+(\d+)\s+days?", "relative_days"),
        (r"(\d+)\s+days?\s+ago", "days_ago"),
    ]
    
    MONTH_NAMES = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
        "jan": 1, "feb": 2, "mar": 3, "apr": 4,
        "jun": 6, "jul": 7, "aug": 8, "sep": 9,
        "oct": 10, "nov": 11, "dec": 12
    }
    
    @classmethod
    def extract_all(cls, text: str) -> List[ExtractedEntity]:
        """Extract all entities from text."""
        entities = []
        
        # Extract dates
        entities.extend(cls.extract_dates(text))
        
        # Extract amounts
        entities.extend(cls.extract_amounts(text))
        
        # Extract numbers
        entities.extend(cls.extract_numbers(text))
        
        # Extract periods
        entities.extend(cls.extract_periods(text))
        
        return entities
    
    @classmethod
    def extract_dates(cls, text: str) -> List[ExtractedEntity]:
        """Extract date entities from text."""
        entities = []
        text_lower = text.lower()
        today = date.today()
        
        # Check relative dates
        relative_dates = {
            "today": (today, today),
            "yesterday": (today - timedelta(days=1), today - timedelta(days=1)),
            "this week": (
                today - timedelta(days=today.weekday()),
                today - timedelta(days=today.weekday()) + timedelta(days=6)
            ),
            "last week": (
                today - timedelta(days=today.weekday() + 7),
                today - timedelta(days=today.weekday() + 1)
            ),
            "this month": (
                date(today.year, today.month, 1),
                date(today.year, today.month, 1) + timedelta(days=32) - timedelta(days=1)
            ),
            "last month": (
                date(today.year, today.month - 1, 1) if today.month > 1 else date(today.year - 1, 12, 1),
                date(today.year, today.month, 1) - timedelta(days=1)
            ),
            "this quarter": cls._get_quarter_range(today),
            "last quarter": cls._get_previous_quarter_range(today),
            "this year": (date(today.year, 1, 1), date(today.year, 12, 31)),
            "last year": (date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)),
        }
        
        for pattern, (start, end) in relative_dates.items():
            if pattern in text_lower:
                entities.append(ExtractedEntity(
                    entity_type=EntityType.DATE_RANGE,
                    value={"start": start, "end": end},
                    raw_text=pattern,
                    confidence=1.0
                ))
        
        # Check relative days pattern
        days_match = re.search(r"(?:past|last)\s+(\d+)\s+days?", text_lower)
        if days_match:
            days = int(days_match.group(1))
            start = today - timedelta(days=days)
            entities.append(ExtractedEntity(
                entity_type=EntityType.DATE_RANGE,
                value={"start": start, "end": today},
                raw_text=days_match.group(0),
                confidence=1.0
            ))
        
        # Check days ago pattern
        ago_match = re.search(r"(\d+)\s+days?\s+ago", text_lower)
        if ago_match:
            days = int(ago_match.group(1))
            target_date = today - timedelta(days=days)
            entities.append(ExtractedEntity(
                entity_type=EntityType.DATE,
                value=target_date,
                raw_text=ago_match.group(0),
                confidence=1.0
            ))
        
        # Check month names
        for month_name, month_num in cls.MONTH_NAMES.items():
            if month_name in text_lower:
                # Determine year (default to current or last if "last")
                year = today.year
                if "last" in text_lower and month_name in text_lower:
                    if month_num > today.month:
                        year -= 1
                
                entities.append(ExtractedEntity(
                    entity_type=EntityType.DATE_RANGE,
                    value={
                        "start": date(year, month_num, 1),
                        "end": date(year, month_num, 1) + timedelta(days=32) - timedelta(days=1)
                    },
                    raw_text=month_name,
                    confidence=0.9
                ))
        
        return entities
    
    @classmethod
    def _get_quarter_range(cls, d: date) -> Tuple[date, date]:
        """Get quarter date range for a date."""
        quarter = (d.month - 1) // 3
        start = date(d.year, quarter * 3 + 1, 1)
        end = date(d.year, quarter * 3 + 4, 1) - timedelta(days=1) if quarter < 3 else date(d.year, 12, 31)
        return start, end
    
    @classmethod
    def _get_previous_quarter_range(cls, d: date) -> Tuple[date, date]:
        """Get previous quarter date range."""
        quarter = (d.month - 1) // 3
        if quarter == 0:
            start = date(d.year - 1, 10, 1)
            end = date(d.year - 1, 12, 31)
        else:
            start = date(d.year, (quarter - 1) * 3 + 1, 1)
            end = date(d.year, quarter * 3, 1) - timedelta(days=1)
        return start, end
    
    @classmethod
    def extract_amounts(cls, text: str) -> List[ExtractedEntity]:
        """Extract monetary amounts from text."""
        entities = []
        
        # Match currency amounts
        patterns = [
            r"\$([\d,]+(?:\.\d{2})?)",
            r"([\d,]+(?:\.\d{2})?)\s*(?:dollars?|usd)",
            r"(?:sar|ر\.س)\s*([\d,]+(?:\.\d{2})?)",
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                amount = float(match.replace(",", ""))
                entities.append(ExtractedEntity(
                    entity_type=EntityType.AMOUNT,
                    value=amount,
                    raw_text=match,
                    confidence=0.9
                ))
        
        return entities
    
    @classmethod
    def extract_numbers(cls, text: str) -> List[ExtractedEntity]:
        """Extract numeric values from text."""
        entities = []
        
        # Match numbers with optional context
        matches = re.findall(r"\b(\d+(?:,\d{3})*(?:\.\d+)?)\b", text)
        
        for match in matches:
            value = float(match.replace(",", ""))
            entities.append(ExtractedEntity(
                entity_type=EntityType.NUMBER,
                value=value,
                raw_text=match,
                confidence=1.0
            ))
        
        return entities
    
    @classmethod
    def extract_periods(cls, text: str) -> List[ExtractedEntity]:
        """Extract time periods from text."""
        entities = []
        text_lower = text.lower()
        
        period_mapping = {
            "daily": "day",
            "weekly": "week",
            "monthly": "month",
            "quarterly": "quarter",
            "yearly": "year",
            "annual": "year",
            "annually": "year",
        }
        
        for pattern, period in period_mapping.items():
            if pattern in text_lower:
                entities.append(ExtractedEntity(
                    entity_type=EntityType.PERIOD,
                    value=period,
                    raw_text=pattern,
                    confidence=1.0
                ))
        
        return entities


# ========================================
# Query Generator
# ========================================

class QueryGenerator:
    """
    Generates SQL queries from parsed natural language.
    """
    
    def __init__(self, tenant_id: UUID):
        self.tenant_id = tenant_id
    
    def generate(self, parsed: ParsedQuery) -> GeneratedQuery:
        """Generate SQL query from parsed query."""
        intent = parsed.intent
        
        # Route to appropriate query generator
        generators = {
            QueryIntent.SALES_SUMMARY: self._generate_sales_summary,
            QueryIntent.TOP_PRODUCTS: self._generate_top_products,
            QueryIntent.INACTIVE_CUSTOMERS: self._generate_inactive_customers,
            QueryIntent.TOP_CUSTOMERS: self._generate_top_customers,
            QueryIntent.LOW_STOCK: self._generate_low_stock,
            QueryIntent.STOCK_STATUS: self._generate_stock_status,
            QueryIntent.REVENUE: self._generate_revenue,
            QueryIntent.PROFIT: self._generate_profit,
            QueryIntent.YEAR_OVER_YEAR: self._generate_yoy_comparison,
            QueryIntent.PERIOD_COMPARISON: self._generate_period_comparison,
        }
        
        generator = generators.get(intent, self._generate_unknown)
        return generator(parsed)
    
    def _get_date_filter(self, entities: List[ExtractedEntity]) -> Tuple[Optional[date], Optional[date]]:
        """Extract date range from entities."""
        for entity in entities:
            if entity.entity_type == EntityType.DATE_RANGE:
                return entity.value["start"], entity.value["end"]
            elif entity.entity_type == EntityType.DATE:
                return entity.value, entity.value
        return None, None
    
    def _generate_sales_summary(self, parsed: ParsedQuery) -> GeneratedQuery:
        """Generate sales summary query."""
        start_date, end_date = self._get_date_filter(parsed.entities)
        
        if start_date and end_date:
            date_filter = f"AND so.date_order BETWEEN :start_date AND :end_date"
            params = {
                "tenant_id": str(self.tenant_id),
                "start_date": start_date,
                "end_date": end_date
            }
        else:
            # Default to last 30 days
            date_filter = "AND so.date_order >= CURRENT_DATE - INTERVAL '30 days'"
            params = {"tenant_id": str(self.tenant_id)}
        
        sql = f"""
        SELECT 
            COUNT(*) as total_orders,
            COALESCE(SUM(so.amount_total), 0) as total_revenue,
            COALESCE(AVG(so.amount_total), 0) as avg_order_value,
            MIN(so.date_order) as period_start,
            MAX(so.date_order) as period_end
        FROM sale_orders so
        WHERE so.tenant_id = :tenant_id
        AND so.state IN ('confirmed', 'done')
        {date_filter}
        """
        
        return GeneratedQuery(
            sql=sql,
            params=params,
            safety_level=QuerySafetyLevel.SAFE,
            tables_accessed=["sale_orders"],
            explanation="Retrieving sales summary with total orders, revenue, and average order value"
        )
    
    def _generate_top_products(self, parsed: ParsedQuery) -> GeneratedQuery:
        """Generate top selling products query."""
        start_date, end_date = self._get_date_filter(parsed.entities)
        
        # Get limit from entities or default
        limit = 10
        for entity in parsed.entities:
            if entity.entity_type == EntityType.NUMBER:
                limit = int(entity.value)
                break
        
        if start_date and end_date:
            date_filter = f"AND so.date_order BETWEEN :start_date AND :end_date"
            params = {
                "tenant_id": str(self.tenant_id),
                "start_date": start_date,
                "end_date": end_date,
                "limit": limit
            }
        else:
            date_filter = "AND so.date_order >= CURRENT_DATE - INTERVAL '30 days'"
            params = {"tenant_id": str(self.tenant_id), "limit": limit}
        
        sql = f"""
        SELECT 
            p.id as product_id,
            p.name as product_name,
            p.sku,
            SUM(sol.quantity) as total_quantity_sold,
            SUM(sol.subtotal) as total_revenue,
            COUNT(DISTINCT so.id) as order_count
        FROM sale_order_lines sol
        JOIN sale_orders so ON sol.sale_order_id = so.id
        JOIN products p ON sol.product_id = p.id
        WHERE so.tenant_id = :tenant_id
        AND so.state IN ('confirmed', 'done')
        {date_filter}
        GROUP BY p.id, p.name, p.sku
        ORDER BY total_revenue DESC
        LIMIT :limit
        """
        
        return GeneratedQuery(
            sql=sql,
            params=params,
            safety_level=QuerySafetyLevel.SAFE,
            tables_accessed=["sale_order_lines", "sale_orders", "products"],
            explanation=f"Retrieving top {limit} products by revenue"
        )
    
    def _generate_inactive_customers(self, parsed: ParsedQuery) -> GeneratedQuery:
        """Generate inactive customers query."""
        # Default to 60 days if not specified
        days = 60
        for entity in parsed.entities:
            if entity.entity_type == EntityType.NUMBER:
                days = int(entity.value)
                break
        
        sql = """
        SELECT 
            c.id as customer_id,
            c.name as customer_name,
            c.email,
            c.phone,
            MAX(so.date_order) as last_order_date,
            EXTRACT(DAY FROM CURRENT_DATE - MAX(so.date_order)) as days_since_last_order
        FROM customers c
        LEFT JOIN sale_orders so ON c.id = so.partner_id 
            AND so.tenant_id = :tenant_id
            AND so.state IN ('confirmed', 'done')
        WHERE c.tenant_id = :tenant_id
        AND c.is_active = true
        GROUP BY c.id, c.name, c.email, c.phone
        HAVING MAX(so.date_order) IS NULL 
            OR MAX(so.date_order) < CURRENT_DATE - INTERVAL '1 day' * :days
        ORDER BY days_since_last_order DESC NULLS FIRST
        """
        
        return GeneratedQuery(
            sql=sql,
            params={"tenant_id": str(self.tenant_id), "days": days},
            safety_level=QuerySafetyLevel.SAFE,
            tables_accessed=["customers", "sale_orders"],
            explanation=f"Finding customers who haven't ordered in the last {days} days"
        )
    
    def _generate_top_customers(self, parsed: ParsedQuery) -> GeneratedQuery:
        """Generate top customers query."""
        limit = 10
        for entity in parsed.entities:
            if entity.entity_type == EntityType.NUMBER:
                limit = int(entity.value)
                break
        
        start_date, end_date = self._get_date_filter(parsed.entities)
        
        if start_date and end_date:
            date_filter = f"AND so.date_order BETWEEN :start_date AND :end_date"
            params = {
                "tenant_id": str(self.tenant_id),
                "start_date": start_date,
                "end_date": end_date,
                "limit": limit
            }
        else:
            date_filter = ""
            params = {"tenant_id": str(self.tenant_id), "limit": limit}
        
        sql = f"""
        SELECT 
            c.id as customer_id,
            c.name as customer_name,
            COUNT(so.id) as order_count,
            SUM(so.amount_total) as total_spent,
            AVG(so.amount_total) as avg_order_value
        FROM customers c
        JOIN sale_orders so ON c.id = so.partner_id
        WHERE so.tenant_id = :tenant_id
        AND so.state IN ('confirmed', 'done')
        {date_filter}
        GROUP BY c.id, c.name
        ORDER BY total_spent DESC
        LIMIT :limit
        """
        
        return GeneratedQuery(
            sql=sql,
            params=params,
            safety_level=QuerySafetyLevel.SAFE,
            tables_accessed=["customers", "sale_orders"],
            explanation=f"Retrieving top {limit} customers by total spending"
        )
    
    def _generate_low_stock(self, parsed: ParsedQuery) -> GeneratedQuery:
        """Generate low stock products query."""
        limit = 20
        for entity in parsed.entities:
            if entity.entity_type == EntityType.NUMBER:
                limit = int(entity.value)
                break
        
        sql = """
        SELECT 
            p.id as product_id,
            p.name as product_name,
            p.sku,
            p.quantity_on_hand as current_stock,
            p.reorder_point,
            p.quantity_on_hand - p.reorder_point as shortage
        FROM products p
        WHERE p.tenant_id = :tenant_id
        AND p.is_deleted = false
        AND p.quantity_on_hand <= p.reorder_point
        ORDER BY shortage ASC
        LIMIT :limit
        """
        
        return GeneratedQuery(
            sql=sql,
            params={"tenant_id": str(self.tenant_id), "limit": limit},
            safety_level=QuerySafetyLevel.SAFE,
            tables_accessed=["products"],
            explanation="Finding products below reorder point"
        )
    
    def _generate_stock_status(self, parsed: ParsedQuery) -> GeneratedQuery:
        """Generate stock status query."""
        sql = """
        SELECT 
            p.id as product_id,
            p.name as product_name,
            p.sku,
            p.quantity_on_hand as current_stock,
            p.quantity_available,
            p.reorder_point,
            CASE 
                WHEN p.quantity_on_hand <= 0 THEN 'OUT_OF_STOCK'
                WHEN p.quantity_on_hand <= p.reorder_point THEN 'LOW_STOCK'
                ELSE 'IN_STOCK'
            END as stock_status
        FROM products p
        WHERE p.tenant_id = :tenant_id
        AND p.is_deleted = false
        ORDER BY p.quantity_on_hand ASC
        LIMIT 50
        """
        
        return GeneratedQuery(
            sql=sql,
            params={"tenant_id": str(self.tenant_id)},
            safety_level=QuerySafetyLevel.SAFE,
            tables_accessed=["products"],
            explanation="Retrieving current stock status for all products"
        )
    
    def _generate_revenue(self, parsed: ParsedQuery) -> GeneratedQuery:
        """Generate revenue query."""
        start_date, end_date = self._get_date_filter(parsed.entities)
        
        if start_date and end_date:
            date_filter = f"AND so.date_order BETWEEN :start_date AND :end_date"
            params = {
                "tenant_id": str(self.tenant_id),
                "start_date": start_date,
                "end_date": end_date
            }
        else:
            # Default to this month
            date_filter = "AND so.date_order >= DATE_TRUNC('month', CURRENT_DATE)"
            params = {"tenant_id": str(self.tenant_id)}
        
        sql = f"""
        SELECT 
            DATE_TRUNC('day', so.date_order) as date,
            SUM(so.amount_total) as daily_revenue,
            COUNT(*) as order_count
        FROM sale_orders so
        WHERE so.tenant_id = :tenant_id
        AND so.state IN ('confirmed', 'done')
        {date_filter}
        GROUP BY DATE_TRUNC('day', so.date_order)
        ORDER BY date
        """
        
        return GeneratedQuery(
            sql=sql,
            params=params,
            safety_level=QuerySafetyLevel.SAFE,
            tables_accessed=["sale_orders"],
            explanation="Retrieving daily revenue breakdown"
        )
    
    def _generate_profit(self, parsed: ParsedQuery) -> GeneratedQuery:
        """Generate profit query."""
        start_date, end_date = self._get_date_filter(parsed.entities)
        
        if start_date and end_date:
            date_filter = f"AND je.date BETWEEN :start_date AND :end_date"
            params = {
                "tenant_id": str(self.tenant_id),
                "start_date": start_date,
                "end_date": end_date
            }
        else:
            date_filter = "AND je.date >= DATE_TRUNC('month', CURRENT_DATE)"
            params = {"tenant_id": str(self.tenant_id)}
        
        sql = f"""
        SELECT 
            a.account_type,
            a.name as account_name,
            SUM(ji.debit) as total_debits,
            SUM(ji.credit) as total_credits,
            SUM(ji.debit) - SUM(ji.credit) as net_amount
        FROM journal_items ji
        JOIN journal_entries je ON ji.journal_entry_id = je.id
        JOIN accounts a ON ji.account_id = a.id
        WHERE je.tenant_id = :tenant_id
        AND je.state = 'posted'
        {date_filter}
        GROUP BY a.account_type, a.name
        ORDER BY a.account_type, net_amount DESC
        """
        
        return GeneratedQuery(
            sql=sql,
            params=params,
            safety_level=QuerySafetyLevel.SAFE,
            tables_accessed=["journal_items", "journal_entries", "accounts"],
            explanation="Calculating profit from revenue and expense accounts"
        )
    
    def _generate_yoy_comparison(self, parsed: ParsedQuery) -> GeneratedQuery:
        """Generate year-over-year comparison query."""
        sql = """
        WITH yearly_data AS (
            SELECT 
                EXTRACT(YEAR FROM so.date_order) as year,
                SUM(so.amount_total) as total_revenue,
                COUNT(*) as total_orders,
                AVG(so.amount_total) as avg_order_value
            FROM sale_orders so
            WHERE so.tenant_id = :tenant_id
            AND so.state IN ('confirmed', 'done')
            AND so.date_order >= DATE_TRUNC('year', CURRENT_DATE) - INTERVAL '2 years'
            GROUP BY EXTRACT(YEAR FROM so.date_order)
        )
        SELECT 
            year,
            total_revenue,
            total_orders,
            avg_order_value,
            LAG(total_revenue) OVER (ORDER BY year) as prev_year_revenue,
            LAG(total_orders) OVER (ORDER BY year) as prev_year_orders,
            (total_revenue - LAG(total_revenue) OVER (ORDER BY year)) / 
                NULLIF(LAG(total_revenue) OVER (ORDER BY year), 0) * 100 as revenue_growth_pct
        FROM yearly_data
        ORDER BY year DESC
        """
        
        return GeneratedQuery(
            sql=sql,
            params={"tenant_id": str(self.tenant_id)},
            safety_level=QuerySafetyLevel.SAFE,
            tables_accessed=["sale_orders"],
            explanation="Comparing year-over-year sales performance"
        )
    
    def _generate_period_comparison(self, parsed: ParsedQuery) -> GeneratedQuery:
        """Generate period comparison query."""
        sql = """
        WITH monthly_data AS (
            SELECT 
                DATE_TRUNC('month', so.date_order) as month,
                SUM(so.amount_total) as total_revenue,
                COUNT(*) as total_orders
            FROM sale_orders so
            WHERE so.tenant_id = :tenant_id
            AND so.state IN ('confirmed', 'done')
            AND so.date_order >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '12 months'
            GROUP BY DATE_TRUNC('month', so.date_order)
        )
        SELECT 
            month,
            total_revenue,
            total_orders,
            LAG(total_revenue) OVER (ORDER BY month) as prev_month_revenue,
            (total_revenue - LAG(total_revenue) OVER (ORDER BY month)) / 
                NULLIF(LAG(total_revenue) OVER (ORDER BY month), 0) * 100 as growth_pct
        FROM monthly_data
        ORDER BY month DESC
        """
        
        return GeneratedQuery(
            sql=sql,
            params={"tenant_id": str(self.tenant_id)},
            safety_level=QuerySafetyLevel.SAFE,
            tables_accessed=["sale_orders"],
            explanation="Comparing monthly sales performance"
        )
    
    def _generate_unknown(self, parsed: ParsedQuery) -> GeneratedQuery:
        """Generate query for unknown intent."""
        return GeneratedQuery(
            sql="SELECT 'Unable to generate query' as message",
            params={},
            safety_level=QuerySafetyLevel.SAFE,
            tables_accessed=[],
            explanation="Could not understand the query intent"
        )


# ========================================
# Response Generator
# ========================================

class ResponseGenerator:
    """
    Generates natural language responses from query results.
    """
    
    @classmethod
    def generate(
        cls,
        intent: QueryIntent,
        data: List[Dict[str, Any]],
        entities: List[ExtractedEntity]
    ) -> Tuple[str, str]:
        """
        Generate natural language response.
        
        Returns (summary, detailed_explanation)
        """
        if not data:
            return "No data found for your query.", "The query returned no results. Try adjusting your search criteria."
        
        generators = {
            QueryIntent.SALES_SUMMARY: cls._generate_sales_summary_response,
            QueryIntent.TOP_PRODUCTS: cls._generate_top_products_response,
            QueryIntent.INACTIVE_CUSTOMERS: cls._generate_inactive_customers_response,
            QueryIntent.TOP_CUSTOMERS: cls._generate_top_customers_response,
            QueryIntent.LOW_STOCK: cls._generate_low_stock_response,
            QueryIntent.STOCK_STATUS: cls._generate_stock_status_response,
            QueryIntent.REVENUE: cls._generate_revenue_response,
            QueryIntent.PROFIT: cls._generate_profit_response,
            QueryIntent.YEAR_OVER_YEAR: cls._generate_yoy_response,
            QueryIntent.PERIOD_COMPARISON: cls._generate_period_comparison_response,
        }
        
        generator = generators.get(intent, cls._generate_generic_response)
        return generator(data, entities)
    
    @classmethod
    def _generate_sales_summary_response(
        cls,
        data: List[Dict],
        entities: List[ExtractedEntity]
    ) -> Tuple[str, str]:
        """Generate sales summary response."""
        row = data[0] if data else {}
        
        total_orders = row.get("total_orders", 0)
        total_revenue = float(row.get("total_revenue", 0))
        avg_order = float(row.get("avg_order_value", 0))
        
        summary = f"📊 **Sales Summary**: {total_orders} orders totaling {total_revenue:,.2f} SAR"
        
        explanation = (
            f"Your sales data shows:\n\n"
            f"• **Total Orders**: {total_orders:,}\n"
            f"• **Total Revenue**: {total_revenue:,.2f} SAR\n"
            f"• **Average Order Value**: {avg_order:,.2f} SAR\n\n"
            f"This represents your sales performance for the selected period."
        )
        
        return summary, explanation
    
    @classmethod
    def _generate_top_products_response(
        cls,
        data: List[Dict],
        entities: List[ExtractedEntity]
    ) -> Tuple[str, str]:
        """Generate top products response."""
        if not data:
            return "No top products found.", "There are no sales records to determine top products."
        
        top_product = data[0] if data else {}
        product_name = top_product.get("product_name", "Unknown")
        revenue = float(top_product.get("total_revenue", 0))
        
        summary = f"🏆 **Top Product**: {product_name} with {revenue:,.2f} SAR in sales"
        
        explanation = "**Top Selling Products:**\n\n"
        for i, row in enumerate(data[:5], 1):
            name = row.get("product_name", "Unknown")
            qty = row.get("total_quantity_sold", 0)
            rev = float(row.get("total_revenue", 0))
            explanation += f"{i}. **{name}** - {qty:,} units sold, {rev:,.2f} SAR\n"
        
        return summary, explanation
    
    @classmethod
    def _generate_inactive_customers_response(
        cls,
        data: List[Dict],
        entities: List[ExtractedEntity]
    ) -> Tuple[str, str]:
        """Generate inactive customers response."""
        count = len(data)
        
        summary = f"👥 **Inactive Customers**: {count} customers haven't ordered recently"
        
        explanation = f"**Found {count} inactive customers:**\n\n"
        
        for row in data[:5]:
            name = row.get("customer_name", "Unknown")
            days = row.get("days_since_last_order", "N/A")
            explanation += f"• **{name}** - Last order: {days} days ago\n"
        
        if count > 5:
            explanation += f"\n... and {count - 5} more customers"
        
        return summary, explanation
    
    @classmethod
    def _generate_top_customers_response(
        cls,
        data: List[Dict],
        entities: List[ExtractedEntity]
    ) -> Tuple[str, str]:
        """Generate top customers response."""
        if not data:
            return "No customer data found.", "There are no customer records with orders."
        
        top = data[0]
        name = top.get("customer_name", "Unknown")
        spent = float(top.get("total_spent", 0))
        
        summary = f"⭐ **Top Customer**: {name} has spent {spent:,.2f} SAR"
        
        explanation = "**Top Customers by Spending:**\n\n"
        for i, row in enumerate(data[:5], 1):
            name = row.get("customer_name", "Unknown")
            orders = row.get("order_count", 0)
            spent = float(row.get("total_spent", 0))
            explanation += f"{i}. **{name}** - {orders} orders, {spent:,.2f} SAR\n"
        
        return summary, explanation
    
    @classmethod
    def _generate_low_stock_response(
        cls,
        data: List[Dict],
        entities: List[ExtractedEntity]
    ) -> Tuple[str, str]:
        """Generate low stock response."""
        count = len(data)
        
        summary = f"⚠️ **Low Stock Alert**: {count} products need reordering"
        
        explanation = "**Products Below Reorder Point:**\n\n"
        
        for row in data[:5]:
            name = row.get("product_name", "Unknown")
            current = row.get("current_stock", 0)
            reorder = row.get("reorder_point", 0)
            shortage = float(row.get("shortage", 0))
            
            explanation += f"• **{name}** - Current: {current}, Reorder Point: {reorder}, Shortage: {abs(shortage):.0f}\n"
        
        if count > 5:
            explanation += f"\n... and {count - 5} more products"
        
        return summary, explanation
    
    @classmethod
    def _generate_stock_status_response(
        cls,
        data: List[Dict],
        entities: List[ExtractedEntity]
    ) -> Tuple[str, str]:
        """Generate stock status response."""
        out_of_stock = sum(1 for d in data if d.get("stock_status") == "OUT_OF_STOCK")
        low_stock = sum(1 for d in data if d.get("stock_status") == "LOW_STOCK")
        in_stock = sum(1 for d in data if d.get("stock_status") == "IN_STOCK")
        
        summary = f"📦 **Inventory Status**: {in_stock} in stock, {low_stock} low, {out_of_stock} out of stock"
        
        explanation = (
            f"**Inventory Overview:**\n\n"
            f"• ✅ **In Stock**: {in_stock} products\n"
            f"• ⚠️ **Low Stock**: {low_stock} products\n"
            f"• ❌ **Out of Stock**: {out_of_stock} products\n"
        )
        
        return summary, explanation
    
    @classmethod
    def _generate_revenue_response(
        cls,
        data: List[Dict],
        entities: List[ExtractedEntity]
    ) -> Tuple[str, str]:
        """Generate revenue response."""
        if not data:
            return "No revenue data found.", "There are no sales records for the selected period."
        
        total_revenue = sum(float(d.get("daily_revenue", 0)) for d in data)
        total_orders = sum(d.get("order_count", 0) for d in data)
        avg_daily = total_revenue / len(data) if data else 0
        
        summary = f"💰 **Revenue**: {total_revenue:,.2f} SAR from {total_orders} orders"
        
        explanation = (
            f"**Revenue Analysis:**\n\n"
            f"• **Total Revenue**: {total_revenue:,.2f} SAR\n"
            f"• **Total Orders**: {total_orders:,}\n"
            f"• **Average Daily Revenue**: {avg_daily:,.2f} SAR\n"
        )
        
        return summary, explanation
    
    @classmethod
    def _generate_profit_response(
        cls,
        data: List[Dict],
        entities: List[ExtractedEntity]
    ) -> Tuple[str, str]:
        """Generate profit response."""
        # This is simplified - real profit calculation would be more complex
        summary = "📈 **Financial Summary**: See detailed breakdown below"
        
        explanation = "**Account Balances:**\n\n"
        
        for row in data[:10]:
            account = row.get("account_name", "Unknown")
            net = float(row.get("net_amount", 0))
            explanation += f"• **{account}**: {net:,.2f} SAR\n"
        
        return summary, explanation
    
    @classmethod
    def _generate_yoy_response(
        cls,
        data: List[Dict],
        entities: List[ExtractedEntity]
    ) -> Tuple[str, str]:
        """Generate year-over-year response."""
        if len(data) < 2:
            return "Insufficient data for year-over-year comparison.", "Need at least 2 years of data."
        
        current = data[0]
        previous = data[1]
        
        current_revenue = float(current.get("total_revenue", 0))
        prev_revenue = float(previous.get("total_revenue", 0))
        growth = float(current.get("revenue_growth_pct", 0) or 0)
        
        direction = "increased" if growth > 0 else "decreased"
        
        summary = f"📊 **YoY Comparison**: Revenue {direction} by {abs(growth):.1f}%"
        
        explanation = (
            f"**Year-over-Year Performance:**\n\n"
            f"• **{int(current.get('year', 0))}**: {current_revenue:,.2f} SAR ({current.get('total_orders', 0):,} orders)\n"
            f"• **{int(previous.get('year', 0))}**: {prev_revenue:,.2f} SAR ({previous.get('total_orders', 0):,} orders)\n"
            f"• **Change**: {growth:+.1f}%\n"
        )
        
        return summary, explanation
    
    @classmethod
    def _generate_period_comparison_response(
        cls,
        data: List[Dict],
        entities: List[ExtractedEntity]
    ) -> Tuple[str, str]:
        """Generate period comparison response."""
        if len(data) < 2:
            return "Insufficient data for period comparison.", "Need at least 2 months of data."
        
        current = data[0]
        previous = data[1]
        
        current_revenue = float(current.get("total_revenue", 0))
        prev_revenue = float(previous.get("total_revenue", 0))
        growth = float(current.get("growth_pct", 0) or 0)
        
        direction = "higher" if growth > 0 else "lower"
        
        summary = f"📅 **Monthly Comparison**: This month is {abs(growth):.1f}% {direction} than last month"
        
        explanation = (
            f"**Monthly Performance Comparison:**\n\n"
            f"• **Current Month**: {current_revenue:,.2f} SAR\n"
            f"• **Previous Month**: {prev_revenue:,.2f} SAR\n"
            f"• **Change**: {growth:+.1f}%\n"
        )
        
        return summary, explanation
    
    @classmethod
    def _generate_generic_response(
        cls,
        data: List[Dict],
        entities: List[ExtractedEntity]
    ) -> Tuple[str, str]:
        """Generate generic response."""
        summary = f"Query returned {len(data)} results"
        
        explanation = "**Results:**\n\n"
        for i, row in enumerate(data[:5], 1):
            explanation += f"{i}. {row}\n"
        
        if len(data) > 5:
            explanation += f"\n... and {len(data) - 5} more results"
        
        return summary, explanation


# ========================================
# Main NL Query Service
# ========================================

class NLQueryService:
    """
    Natural Language Query Service
    
    Main service for processing natural language queries.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
        # Caching
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5 minutes
        
        # Rate limiting
        self._tenant_requests: Dict[UUID, List[float]] = {}
        self._rate_limit = 100  # requests per hour
    
    async def process_query(
        self,
        query_text: str,
        tenant_id: UUID,
        user_id: Optional[UUID] = None,
        use_ai_enhancement: bool = True
    ) -> QueryResult:
        """
        Process a natural language query.
        
        Args:
            query_text: Natural language query
            tenant_id: Tenant UUID
            user_id: Optional user UUID
            use_ai_enhancement: Whether to use AI for query enhancement
            
        Returns:
            QueryResult with data and natural language response
        """
        import time
        start_time = time.time()
        
        # Check rate limit
        if not self._check_rate_limit(tenant_id):
            return QueryResult(
                success=False,
                data=[],
                summary="Rate limit exceeded",
                explanation="Please try again later.",
                query_sql="",
                row_count=0,
                execution_time_ms=0
            )
        
        try:
            # Step 1: Parse the query
            parsed = await self._parse_query(query_text, tenant_id)
            
            # Step 2: Generate SQL
            generator = QueryGenerator(tenant_id)
            generated = generator.generate(parsed)
            
            # Step 3: Validate safety
            if generated.safety_level == QuerySafetyLevel.DANGEROUS:
                return QueryResult(
                    success=False,
                    data=[],
                    summary="Query rejected for safety reasons",
                    explanation="This query type is not allowed.",
                    query_sql="",
                    row_count=0,
                    execution_time_ms=0
                )
            
            # Step 4: Execute query
            data = await self._execute_query(generated)
            
            # Step 5: Generate response
            summary, explanation = ResponseGenerator.generate(
                parsed.intent, data, parsed.entities
            )
            
            # Step 6: Optionally enhance with AI
            if use_ai_enhancement and data:
                summary, explanation = await self._enhance_with_ai(
                    query_text, parsed.intent, data, summary, explanation
                )
            
            execution_time = (time.time() - start_time) * 1000
            
            # Step 7: Generate visualization suggestions
            visualizations = self._suggest_visualizations(parsed.intent, data)
            
            return QueryResult(
                success=True,
                data=data,
                summary=summary,
                explanation=explanation,
                query_sql=generated.sql,
                row_count=len(data),
                execution_time_ms=execution_time,
                visualizations=visualizations
            )
            
        except Exception as e:
            logger.error(f"Query processing error: {e}")
            return QueryResult(
                success=False,
                data=[],
                summary="Error processing query",
                explanation=str(e),
                query_sql="",
                row_count=0,
                execution_time_ms=0
            )
    
    async def _parse_query(
        self,
        query_text: str,
        tenant_id: UUID
    ) -> ParsedQuery:
        """Parse natural language query."""
        # Classify intent
        intent, confidence = IntentClassifier.classify(query_text)
        
        # Extract entities
        entities = EntityExtractor.extract_all(query_text)
        
        # Parse filters
        filters = self._parse_filters(entities)
        
        # Parse aggregations
        aggregations = self._parse_aggregations(query_text)
        
        # Parse ordering
        ordering = self._parse_ordering(query_text)
        
        # Parse limit
        limit = self._parse_limit(query_text, entities)
        
        return ParsedQuery(
            original_text=query_text,
            intent=intent,
            entities=entities,
            filters=filters,
            aggregations=aggregations,
            ordering=ordering,
            limit=limit,
            confidence=confidence
        )
    
    def _parse_filters(self, entities: List[ExtractedEntity]) -> Dict[str, Any]:
        """Parse filters from entities."""
        filters = {}
        
        for entity in entities:
            if entity.entity_type == EntityType.DATE_RANGE:
                filters["date_range"] = entity.value
            elif entity.entity_type == EntityType.AMOUNT:
                if "amount_min" not in filters:
                    filters["amount_min"] = entity.value
                else:
                    filters["amount_max"] = entity.value
        
        return filters
    
    def _parse_aggregations(self, text: str) -> List[str]:
        """Parse aggregation functions from text."""
        aggregations = []
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["total", "sum", "amount"]):
            aggregations.append("sum")
        
        if any(word in text_lower for word in ["average", "avg", "mean"]):
            aggregations.append("avg")
        
        if any(word in text_lower for word in ["count", "number", "how many"]):
            aggregations.append("count")
        
        if any(word in text_lower for word in ["max", "highest", "top"]):
            aggregations.append("max")
        
        if any(word in text_lower for word in ["min", "lowest", "bottom"]):
            aggregations.append("min")
        
        return aggregations if aggregations else ["sum"]
    
    def _parse_ordering(self, text: str) -> Optional[Tuple[str, str]]:
        """Parse ordering from text."""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["top", "highest", "most", "best"]):
            return ("revenue", "desc")
        
        if any(word in text_lower for word in ["bottom", "lowest", "least", "worst"]):
            return ("revenue", "asc")
        
        return None
    
    def _parse_limit(self, text: str, entities: List[ExtractedEntity]) -> Optional[int]:
        """Parse result limit from text."""
        # Check for explicit number in text
        for entity in entities:
            if entity.entity_type == EntityType.NUMBER:
                # Check context
                if "top" in text.lower() or "first" in text.lower():
                    return int(entity.value)
        
        # Default limits
        if "top" in text.lower():
            return 10
        
        return None
    
    async def _execute_query(self, generated: GeneratedQuery) -> List[Dict[str, Any]]:
        """Execute the generated SQL query."""
        try:
            result = await self.db.execute(
                text(generated.sql),
                generated.params
            )
            
            # Convert to list of dicts
            columns = result.keys()
            data = [dict(zip(columns, row)) for row in result.fetchall()]
            
            return data
            
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            raise
    
    async def _enhance_with_ai(
        self,
        query_text: str,
        intent: QueryIntent,
        data: List[Dict],
        summary: str,
        explanation: str
    ) -> Tuple[str, str]:
        """Enhance response with AI analysis."""
        try:
            import sys
            sys.path.insert(0, '/home/z/my-project')
            from z_ai_web_dev_sdk import ZAI
            
            zai = await ZAI.create()
            
            # Prepare context
            data_summary = json.dumps(data[:10], default=str)  # First 10 rows
            
            prompt = f"""Analyze this query result and provide enhanced insights.

Original Query: {query_text}
Query Intent: {intent.value}

Data Summary (first 10 rows):
{data_summary}

Current Summary: {summary}

Provide:
1. An enhanced summary (one line, include key metrics)
2. A detailed explanation with:
   - Key insights from the data
   - Notable patterns or trends
   - Actionable recommendations

Return JSON: {{"summary": "...", "explanation": "..."}}"""

            completion = await zai.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a business intelligence analyst. Provide clear, actionable insights in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            response_text = completion.choices[0].message.content
            
            # Parse AI response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                ai_result = json.loads(json_match.group())
                return ai_result.get("summary", summary), ai_result.get("explanation", explanation)
            
            return summary, explanation
            
        except Exception as e:
            logger.error(f"AI enhancement error: {e}")
            return summary, explanation
    
    def _suggest_visualizations(
        self,
        intent: QueryIntent,
        data: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Suggest visualizations for the data."""
        visualizations = []
        
        if not data:
            return visualizations
        
        # Sales/revenue trends
        if intent in [QueryIntent.REVENUE, QueryIntent.SALES_TREND, QueryIntent.SALES_SUMMARY]:
            if "date" in data[0] and "daily_revenue" in data[0]:
                visualizations.append({
                    "type": "line_chart",
                    "title": "Revenue Trend",
                    "x_field": "date",
                    "y_field": "daily_revenue",
                    "description": "Daily revenue over time"
                })
        
        # Top products/customers
        if intent in [QueryIntent.TOP_PRODUCTS, QueryIntent.TOP_CUSTOMERS]:
            visualizations.append({
                "type": "bar_chart",
                "title": "Top Performers",
                "x_field": "product_name" if intent == QueryIntent.TOP_PRODUCTS else "customer_name",
                "y_field": "total_revenue" if intent == QueryIntent.TOP_PRODUCTS else "total_spent",
                "description": "Ranked by value"
            })
        
        # Stock status
        if intent in [QueryIntent.STOCK_STATUS, QueryIntent.LOW_STOCK]:
            visualizations.append({
                "type": "table",
                "title": "Stock Status",
                "columns": ["product_name", "current_stock", "reorder_point", "stock_status"],
                "description": "Current inventory levels"
            })
        
        # Year-over-year comparison
        if intent == QueryIntent.YEAR_OVER_YEAR:
            visualizations.append({
                "type": "bar_chart",
                "title": "Year-over-Year Comparison",
                "x_field": "year",
                "y_field": "total_revenue",
                "description": "Annual revenue comparison"
            })
        
        return visualizations
    
    def _check_rate_limit(self, tenant_id: UUID) -> bool:
        """Check if tenant has exceeded rate limit."""
        import time
        current_time = time.time()
        
        if tenant_id not in self._tenant_requests:
            self._tenant_requests[tenant_id] = []
        
        # Clean old requests
        self._tenant_requests[tenant_id] = [
            t for t in self._tenant_requests[tenant_id]
            if current_time - t < 3600
        ]
        
        if len(self._tenant_requests[tenant_id]) >= self._rate_limit:
            return False
        
        self._tenant_requests[tenant_id].append(current_time)
        return True
    
    async def get_query_suggestions(
        self,
        tenant_id: UUID,
        context: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Get suggested queries based on context."""
        suggestions = [
            {
                "query": "Show me sales summary for this month",
                "description": "Get total orders, revenue, and average order value"
            },
            {
                "query": "What are the top 10 selling products",
                "description": "See best performing products by revenue"
            },
            {
                "query": "Which customers haven't ordered in 60 days",
                "description": "Find inactive customers for follow-up"
            },
            {
                "query": "Compare this year sales vs last year",
                "description": "Year-over-year performance comparison"
            },
            {
                "query": "Show low stock products",
                "description": "Products below reorder point"
            },
            {
                "query": "What is the revenue trend over last 3 months",
                "description": "Daily revenue analysis"
            },
            {
                "query": "Who are the top customers by spending",
                "description": "Best customers by total purchases"
            },
            {
                "query": "Show profit for this quarter",
                "description": "Financial performance summary"
            },
        ]
        
        return suggestions
