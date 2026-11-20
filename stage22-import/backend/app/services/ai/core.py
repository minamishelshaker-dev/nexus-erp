"""
Nexus ERP - AI Engine Core
==========================

Central AI orchestration engine that coordinates all AI services.
Provides unified access to AI capabilities throughout the ERP system.

Features:
- AI service registry
- Context management
- Request routing
- Response caching
- Performance monitoring
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Callable, Awaitable
from uuid import UUID
from dataclasses import dataclass, field
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
import logging
import json
import hashlib
import asyncio
from functools import wraps
import time

from app.services.ai.llm_provider import (
    LLMService, LLMConfig, LLMResponse, get_llm_service
)

logger = logging.getLogger(__name__)


# ========================================
# AI Context Management
# ========================================

@dataclass
class AIContext:
    """
    AI Context for requests
    
    Holds all context information needed for AI operations.
    """
    tenant_id: UUID
    user_id: Optional[UUID] = None
    module: str = "general"  # sales, inventory, accounting, etc.
    language: str = "ar"  # ar, en
    timezone: str = "Asia/Riyadh"
    currency: str = "SAR"
    session_id: Optional[UUID] = None
    request_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "tenant_id": str(self.tenant_id),
            "user_id": str(self.user_id) if self.user_id else None,
            "module": self.module,
            "language": self.language,
            "timezone": self.timezone,
            "currency": self.currency,
            "session_id": str(self.session_id) if self.session_id else None,
            "request_id": self.request_id,
            "metadata": self.metadata
        }


@dataclass
class AIResult:
    """
    Standard AI result structure.
    """
    success: bool
    data: Any
    message: str
    confidence: float = 1.0
    source: str = "ai"  # ai, cache, fallback
    model: str = ""
    tokens_used: int = 0
    latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "confidence": self.confidence,
            "source": self.source,
            "model": self.model,
            "tokens_used": self.tokens_used,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


# ========================================
# AI Task Types
# ========================================

class AITaskType(str, Enum):
    """Types of AI tasks."""
    FORECAST = "forecast"
    ANOMALY_DETECTION = "anomaly_detection"
    NATURAL_LANGUAGE_QUERY = "nl_query"
    INSIGHT_GENERATION = "insight"
    CHAT = "chat"
    OCR = "ocr"
    RECOMMENDATION = "recommendation"
    CLASSIFICATION = "classification"


# ========================================
# Response Cache
# ========================================

class AIResponseCache:
    """
    In-memory cache for AI responses.
    
    Reduces API calls for repeated queries.
    """
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._hits = 0
        self._misses = 0
    
    def _generate_key(self, task_type: str, content: str, context: AIContext) -> str:
        """Generate a cache key."""
        key_data = f"{task_type}:{content}:{context.tenant_id}:{context.module}"
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    def get(self, task_type: str, content: str, context: AIContext) -> Optional[AIResult]:
        """Get cached result if available and not expired."""
        key = self._generate_key(task_type, content, context)
        
        if key in self._cache:
            cached = self._cache[key]
            if datetime.now() < cached["expires_at"]:
                self._hits += 1
                cached["result"].source = "cache"
                return cached["result"]
            else:
                del self._cache[key]
        
        self._misses += 1
        return None
    
    def set(self, task_type: str, content: str, context: AIContext, result: AIResult):
        """Cache a result."""
        # Evict old entries if cache is full
        if len(self._cache) >= self._max_size:
            self._evict_oldest()
        
        key = self._generate_key(task_type, content, context)
        self._cache[key] = {
            "result": result,
            "expires_at": datetime.now() + timedelta(seconds=self._ttl_seconds),
            "created_at": datetime.now()
        }
    
    def _evict_oldest(self):
        """Evict the oldest entries."""
        if not self._cache:
            return
        
        # Remove 10% of oldest entries
        items = sorted(self._cache.items(), key=lambda x: x[1]["created_at"])
        for key, _ in items[:len(items) // 10 + 1]:
            del self._cache[key]
    
    def clear(self):
        """Clear the cache."""
        self._cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0
        
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "ttl_seconds": self._ttl_seconds
        }


# ========================================
# Performance Monitor
# ========================================

class AIPerformanceMonitor:
    """
    Monitor AI service performance.
    
    Tracks latency, success rates, and resource usage.
    """
    
    def __init__(self):
        self._metrics: Dict[str, List[Dict[str, Any]]] = {}
        self._start_times: Dict[str, float] = {}
    
    def start_request(self, request_id: str):
        """Mark the start of a request."""
        self._start_times[request_id] = time.time()
    
    def end_request(
        self,
        request_id: str,
        task_type: str,
        success: bool,
        tokens: int = 0,
        error: Optional[str] = None
    ):
        """Mark the end of a request and record metrics."""
        start_time = self._start_times.pop(request_id, time.time())
        latency_ms = (time.time() - start_time) * 1000
        
        if task_type not in self._metrics:
            self._metrics[task_type] = []
        
        self._metrics[task_type].append({
            "timestamp": datetime.now().isoformat(),
            "latency_ms": latency_ms,
            "success": success,
            "tokens": tokens,
            "error": error
        })
        
        # Keep only last 1000 entries per task type
        if len(self._metrics[task_type]) > 1000:
            self._metrics[task_type] = self._metrics[task_type][-1000:]
    
    def get_stats(self, task_type: Optional[str] = None) -> Dict[str, Any]:
        """Get performance statistics."""
        if task_type:
            metrics = self._metrics.get(task_type, [])
            return self._calculate_stats(task_type, metrics)
        
        return {
            task: self._calculate_stats(task, m)
            for task, m in self._metrics.items()
        }
    
    def _calculate_stats(self, task_type: str, metrics: List[Dict]) -> Dict[str, Any]:
        """Calculate statistics for a task type."""
        if not metrics:
            return {"count": 0}
        
        latencies = [m["latency_ms"] for m in metrics]
        successes = sum(1 for m in metrics if m["success"])
        total_tokens = sum(m["tokens"] for m in metrics)
        
        return {
            "task_type": task_type,
            "count": len(metrics),
            "success_rate": successes / len(metrics),
            "avg_latency_ms": sum(latencies) / len(latencies),
            "min_latency_ms": min(latencies),
            "max_latency_ms": max(latencies),
            "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 20 else max(latencies),
            "total_tokens": total_tokens,
            "avg_tokens": total_tokens / len(metrics)
        }


# ========================================
# AI Engine Core
# ========================================

class AIEngine:
    """
    AI Engine Core
    
    Central orchestration for all AI operations in the ERP.
    """
    
    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        self._llm_service = get_llm_service()
        self._cache = AIResponseCache()
        self._monitor = AIPerformanceMonitor()
        self._services: Dict[str, Any] = {}
        self._initialized = False
    
    async def initialize(self):
        """Initialize the AI engine."""
        if self._initialized:
            return
        
        # Initialize LLM provider
        try:
            # Test connection
            await self._llm_service.complete(
                [{"role": "user", "content": "test"}],
                LLMConfig(max_tokens=5)
            )
            logger.info("AI Engine initialized successfully")
        except Exception as e:
            logger.warning(f"AI Engine initialization warning: {e}")
        
        self._initialized = True
    
    def register_service(self, name: str, service: Any):
        """Register an AI service."""
        self._services[name] = service
    
    def get_service(self, name: str) -> Any:
        """Get a registered service."""
        return self._services.get(name)
    
    # ========================================
    # Core AI Operations
    # ========================================
    
    async def complete(
        self,
        prompt: str,
        context: AIContext,
        system_prompt: Optional[str] = None,
        config: Optional[LLMConfig] = None,
        use_cache: bool = True
    ) -> AIResult:
        """
        Generate a completion.
        
        Args:
            prompt: The user prompt
            context: AI context with tenant/user info
            system_prompt: Optional system prompt
            config: LLM configuration
            use_cache: Whether to use response caching
            
        Returns:
            AIResult with the completion
        """
        request_id = f"req_{datetime.now().timestamp()}"
        self._monitor.start_request(request_id)
        
        try:
            # Check cache
            if use_cache:
                cached = self._cache.get(AITaskType.CHAT.value, prompt, context)
                if cached:
                    self._monitor.end_request(request_id, AITaskType.CHAT.value, True)
                    return cached
            
            # Build messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Get completion
            config = config or LLMConfig()
            response = await self._llm_service.complete(messages, config)
            
            result = AIResult(
                success=True,
                data=response.content,
                message="Completion generated successfully",
                confidence=0.9,
                source="ai",
                model=response.model,
                tokens_used=response.total_tokens,
                latency_ms=response.latency_ms
            )
            
            # Cache result
            if use_cache:
                self._cache.set(AITaskType.CHAT.value, prompt, context, result)
            
            self._monitor.end_request(
                request_id, AITaskType.CHAT.value, True, response.total_tokens
            )
            
            return result
            
        except Exception as e:
            self._monitor.end_request(
                request_id, AITaskType.CHAT.value, False, error=str(e)
            )
            return AIResult(
                success=False,
                data=None,
                message=f"Completion failed: {str(e)}",
                confidence=0.0
            )
    
    async def complete_json(
        self,
        prompt: str,
        context: AIContext,
        system_prompt: Optional[str] = None,
        config: Optional[LLMConfig] = None
    ) -> AIResult:
        """
        Generate a completion and parse as JSON.
        """
        config = config or LLMConfig()
        config.temperature = min(config.temperature, 0.3)
        
        # Add JSON instruction to system prompt
        json_instruction = "\n\nIMPORTANT: Your response must be valid JSON only. No additional text."
        system_prompt = (system_prompt or "") + json_instruction
        
        result = await self.complete(prompt, context, system_prompt, config)
        
        if result.success:
            try:
                import re
                json_match = re.search(r'\{.*\}|\[.*\]', result.data, re.DOTALL)
                if json_match:
                    result.data = json.loads(json_match.group())
                else:
                    result.data = json.loads(result.data)
            except json.JSONDecodeError as e:
                result.success = False
                result.message = f"Failed to parse JSON: {str(e)}"
                result.confidence = 0.0
        
        return result
    
    async def analyze(
        self,
        data: Any,
        analysis_type: str,
        context: AIContext,
        additional_instructions: Optional[str] = None
    ) -> AIResult:
        """
        Perform AI analysis on data.
        
        Args:
            data: Data to analyze
            analysis_type: Type of analysis (forecast, anomaly, insight, etc.)
            context: AI context
            additional_instructions: Extra instructions for the analysis
            
        Returns:
            AIResult with analysis findings
        """
        system_prompts = {
            "forecast": """You are a demand forecasting expert. Analyze the provided data and generate accurate forecasts.
            Consider trends, seasonality, and patterns. Provide confidence intervals.""",
            
            "anomaly": """You are a financial anomaly detection expert. Analyze transactions for unusual patterns.
            Look for: duplicate entries, unusual amounts, timing anomalies, and suspicious patterns.
            Provide risk scores and recommendations.""",
            
            "insight": """You are a business intelligence expert. Analyze data and generate actionable insights.
            Focus on: trends, opportunities, risks, and recommendations.""",
            
            "query": """You are a database query expert. Convert natural language questions to database queries.
            Return structured query parameters."""
        }
        
        system_prompt = system_prompts.get(analysis_type, "You are an AI assistant.")
        if additional_instructions:
            system_prompt += f"\n\n{additional_instructions}"
        
        prompt = f"Analyze the following data:\n\n{json.dumps(data, default=str)}"
        
        return await self.complete_json(prompt, context, system_prompt)
    
    # ========================================
    # Convenience Methods
    # ========================================
    
    async def forecast(
        self,
        historical_data: List[Dict],
        periods: int,
        context: AIContext
    ) -> AIResult:
        """Generate a forecast from historical data."""
        return await self.analyze(
            data={"historical_data": historical_data, "periods": periods},
            analysis_type="forecast",
            context=context
        )
    
    async def detect_anomalies(
        self,
        transactions: List[Dict],
        context: AIContext
    ) -> AIResult:
        """Detect anomalies in transactions."""
        return await self.analyze(
            data={"transactions": transactions},
            analysis_type="anomaly",
            context=context
        )
    
    async def generate_insights(
        self,
        data: Dict[str, Any],
        context: AIContext
    ) -> AIResult:
        """Generate business insights from data."""
        return await self.analyze(
            data=data,
            analysis_type="insight",
            context=context
        )
    
    async def parse_query(
        self,
        natural_language_query: str,
        context: AIContext
    ) -> AIResult:
        """Parse a natural language query."""
        return await self.analyze(
            data={"query": natural_language_query},
            analysis_type="query",
            context=context
        )
    
    # ========================================
    # Statistics and Monitoring
    # ========================================
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self._cache.get_stats()
    
    def get_performance_stats(self, task_type: Optional[str] = None) -> Dict[str, Any]:
        """Get performance statistics."""
        return self._monitor.get_stats(task_type)
    
    def get_llm_stats(self) -> Dict[str, Any]:
        """Get LLM service statistics."""
        return self._llm_service.get_stats()
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get all statistics."""
        return {
            "cache": self.get_cache_stats(),
            "performance": self.get_performance_stats(),
            "llm": self.get_llm_stats(),
            "initialized": self._initialized
        }
    
    def clear_cache(self):
        """Clear the response cache."""
        self._cache.clear()


# ========================================
# Decorators for AI Functions
# ========================================

def ai_task(task_type: AITaskType):
    """
    Decorator for AI task functions.
    
    Adds logging, timing, and error handling.
    """
    def decorator(func: Callable[..., Awaitable[AIResult]]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                latency = (time.time() - start_time) * 1000
                
                logger.info(
                    f"AI Task {task_type.value} completed in {latency:.2f}ms, "
                    f"success={result.success}, confidence={result.confidence}"
                )
                
                return result
                
            except Exception as e:
                latency = (time.time() - start_time) * 1000
                logger.error(f"AI Task {task_type.value} failed: {e}")
                
                return AIResult(
                    success=False,
                    data=None,
                    message=str(e),
                    confidence=0.0,
                    latency_ms=latency
                )
        
        return wrapper
    return decorator


# ========================================
# Global Instance
# ========================================

_ai_engine_instance: Optional[AIEngine] = None


def get_ai_engine(db: Optional[AsyncSession] = None) -> AIEngine:
    """Get or create the AI engine instance."""
    global _ai_engine_instance
    
    if _ai_engine_instance is None:
        _ai_engine_instance = AIEngine(db)
    
    if db and _ai_engine_instance.db is None:
        _ai_engine_instance.db = db
    
    return _ai_engine_instance


async def initialize_ai_engine(db: Optional[AsyncSession] = None):
    """Initialize the global AI engine."""
    engine = get_ai_engine(db)
    await engine.initialize()
    return engine
