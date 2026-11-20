"""
Nexus ERP - AI Services Package
================================

This package provides AI-powered services for the ERP system:
- Forecasting: Demand prediction with multi-model ensemble
- Anomaly Detection: Statistical and ML-based detection
- Natural Language Query: Convert NL to SQL queries
- Assistant: Context-aware AI assistant
- OCR: Invoice and document parsing
- Chatbot: Natural language interface
"""

from app.services.ai.forecasting_service import (
    ForecastingService,
    EnsembleForecaster,
    ARIMAModel,
    ExponentialSmoothingModel,
    LinearRegressionModel,
    FeatureEngineer,
    SeasonalityDetector,
)

from app.services.ai.anomaly_service import (
    AnomalyService,
    FinancialAnomalyDetector,
    InventoryAnomalyDetector,
    StatisticalAnalyzer,
    IsolationForestHints,
    AnomalyAlert,
    AnomalyType,
    SeverityLevel,
)

from app.services.ai.nl_query_service import (
    NLQueryService,
    IntentClassifier,
    EntityExtractor,
    QueryGenerator,
    ResponseGenerator,
    QueryIntent,
    EntityType,
    ParsedQuery,
    GeneratedQuery,
    QueryResult,
)

from app.services.ai.assistant_service import (
    AssistantService,
    ContextManager,
    InsightGenerator,
    ActionExecutor,
    AssistantModule,
    AssistantContext,
    AssistantResponse,
    ProactiveInsight,
    ActionRecommendation,
    InsightType,
    ActionType,
)

from app.services.ai.ocr_service import OCRService
from app.services.ai.chatbot_service import ChatbotService
from app.services.ai.core import (
    AIEngine,
    AIContext,
    AIResult,
    AITaskType,
    get_ai_engine,
    initialize_ai_engine,
)
from app.services.ai.llm_provider import (
    LLMService,
    LLMConfig,
    LLMResponse,
    get_llm_service,
)

__all__ = [
    # Forecasting
    "ForecastingService",
    "EnsembleForecaster",
    "ARIMAModel",
    "ExponentialSmoothingModel",
    "LinearRegressionModel",
    "FeatureEngineer",
    "SeasonalityDetector",
    
    # Anomaly Detection
    "AnomalyService",
    "FinancialAnomalyDetector",
    "InventoryAnomalyDetector",
    "StatisticalAnalyzer",
    "IsolationForestHints",
    "AnomalyAlert",
    "AnomalyType",
    "SeverityLevel",
    
    # Natural Language Query
    "NLQueryService",
    "IntentClassifier",
    "EntityExtractor",
    "QueryGenerator",
    "ResponseGenerator",
    "QueryIntent",
    "EntityType",
    "ParsedQuery",
    "GeneratedQuery",
    "QueryResult",
    
    # Assistant
    "AssistantService",
    "ContextManager",
    "InsightGenerator",
    "ActionExecutor",
    "AssistantModule",
    "AssistantContext",
    "AssistantResponse",
    "ProactiveInsight",
    "ActionRecommendation",
    "InsightType",
    "ActionType",
    
    # Legacy Services
    "OCRService",
    "ChatbotService",
    
    # Core
    "AIEngine",
    "AIContext",
    "AIResult",
    "AITaskType",
    "get_ai_engine",
    "initialize_ai_engine",
    
    # LLM
    "LLMService",
    "LLMConfig",
    "LLMResponse",
    "get_llm_service",
]
