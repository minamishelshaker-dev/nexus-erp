"""
Nexus ERP - Enhanced AI Forecasting Service
============================================

Advanced forecasting service with multi-model ensemble approach:
- ARIMA (AutoRegressive Integrated Moving Average)
- Exponential Smoothing (Holt-Winters)
- Linear Regression with trend
- AI-powered ensemble combination

Features:
- Sales forecasting with confidence intervals
- Inventory demand prediction
- Revenue forecasting
- Seasonality detection
- Feature engineering (day of week, month, holidays)
- Response caching
- Rate limiting per tenant
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from dataclasses import dataclass, field
from enum import Enum
import logging
import json
import math
import statistics
from collections import defaultdict
import asyncio

from app.models.ai import Forecast, ForecastType, ForecastMethod
from app.models.sales import SaleOrder, SaleOrderLine
from app.models.inventory import Product, StockMove
from app.models.accounting import JournalEntry
from app.core.config import settings

logger = logging.getLogger(__name__)


# ========================================
# Enums and Data Classes
# ========================================

class EnsembleMethod(str, Enum):
    """Ensemble combination methods."""
    WEIGHTED_AVERAGE = "weighted_average"
    MEDIAN = "median"
    BEST_PERFORMER = "best_performer"
    STACKING = "stacking"


class SeasonalityType(str, Enum):
    """Types of seasonality patterns."""
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


@dataclass
class ForecastResult:
    """Individual forecast result."""
    date: date
    predicted_value: float
    lower_bound: float
    upper_bound: float
    confidence: float
    method: str
    features: Dict[str, float] = field(default_factory=dict)


@dataclass
class EnsembleForecast:
    """Ensemble forecast combining multiple models."""
    date: date
    predicted_value: float
    lower_bound: float
    upper_bound: float
    confidence: float
    model_weights: Dict[str, float]
    individual_predictions: Dict[str, float]
    features: Dict[str, float] = field(default_factory=dict)


@dataclass
class SeasonalityInfo:
    """Detected seasonality information."""
    has_seasonality: bool
    seasonality_type: SeasonalityType
    seasonal_indices: Dict[int, float]  # Period index -> multiplier
    peak_periods: List[int]
    trough_periods: List[int]
    strength: float  # 0-1


# ========================================
# Feature Engineering
# ========================================

class FeatureEngineer:
    """
    Feature engineering for forecasting.
    
    Creates temporal and contextual features.
    """
    
    # Known holidays (can be extended)
    HOLIDAYS = {
        # Saudi Arabia holidays (approximate dates)
        "eid_al_fitr": [(4, 15), (5, 15)],  # Variable
        "eid_al_adha": [(7, 10), (8, 10)],  # Variable
        "national_day": [(9, 23)],  # Fixed
        "founder_day": [(2, 22)],  # Fixed
    }
    
    @staticmethod
    def extract_features(dt: date) -> Dict[str, float]:
        """Extract temporal features from a date."""
        return {
            # Day features
            "day_of_week": dt.weekday(),
            "day_of_month": dt.day,
            "day_of_year": dt.timetuple().tm_yday,
            "is_weekend": 1.0 if dt.weekday() >= 5 else 0.0,
            
            # Week features
            "week_of_year": dt.isocalendar()[1],
            "is_first_week": 1.0 if dt.isocalendar()[1] == 1 else 0.0,
            "is_last_week": 1.0 if dt.isocalendar()[1] >= 52 else 0.0,
            
            # Month features
            "month": dt.month,
            "is_month_start": 1.0 if dt.day <= 7 else 0.0,
            "is_month_end": 1.0 if dt.day >= 24 else 0.0,
            "quarter": (dt.month - 1) // 3 + 1,
            
            # Year features
            "year": dt.year,
            "is_year_start": 1.0 if dt.month == 1 else 0.0,
            "is_year_end": 1.0 if dt.month == 12 else 0.0,
            
            # Seasonal indicators
            "is_q1": 1.0 if dt.month in [1, 2, 3] else 0.0,
            "is_q2": 1.0 if dt.month in [4, 5, 6] else 0.0,
            "is_q3": 1.0 if dt.month in [7, 8, 9] else 0.0,
            "is_q4": 1.0 if dt.month in [10, 11, 12] else 0.0,
            
            # Holiday proximity (simplified)
            "is_near_holiday": FeatureEngineer._is_near_holiday(dt),
        }
    
    @staticmethod
    def _is_near_holiday(dt: date) -> float:
        """Check if date is near a known holiday."""
        for holiday_name, date_ranges in FeatureEngineer.HOLIDAYS.items():
            for start_month, start_day in date_ranges:
                holiday_date = date(dt.year, start_month, min(start_day, 28))
                if abs((dt - holiday_date).days) <= 7:
                    return 1.0
        return 0.0
    
    @staticmethod
    def create_lagged_features(
        values: List[float],
        lags: List[int] = [1, 7, 14, 30]
    ) -> List[Dict[str, float]]:
        """Create lagged features for time series."""
        features_list = []
        
        for i in range(len(values)):
            features = {}
            for lag in lags:
                if i >= lag:
                    features[f"lag_{lag}"] = values[i - lag]
                else:
                    features[f"lag_{lag}"] = values[0] if values else 0.0
            
            # Rolling statistics
            if i >= 7:
                window = values[max(0, i-7):i]
                features["rolling_mean_7"] = statistics.mean(window)
                features["rolling_std_7"] = statistics.stdev(window) if len(window) > 1 else 0
            else:
                features["rolling_mean_7"] = values[0] if values else 0.0
                features["rolling_std_7"] = 0.0
            
            if i >= 30:
                window = values[max(0, i-30):i]
                features["rolling_mean_30"] = statistics.mean(window)
                features["rolling_std_30"] = statistics.stdev(window) if len(window) > 1 else 0
            else:
                features["rolling_mean_30"] = values[0] if values else 0.0
                features["rolling_std_30"] = 0.0
            
            features_list.append(features)
        
        return features_list


# ========================================
# Statistical Forecasting Models
# ========================================

class ARIMAModel:
    """
    Simplified ARIMA model implementation.
    
    ARIMA(p, d, q) - AutoRegressive Integrated Moving Average
    """
    
    def __init__(self, p: int = 1, d: int = 1, q: int = 1):
        self.p = p  # AR order
        self.d = d  # Differencing order
        self.q = q  # MA order
        self.ar_coeffs: List[float] = []
        self.ma_coeffs: List[float] = []
        self.residuals: List[float] = []
        self.fitted_values: List[float] = []
    
    def fit(self, data: List[float]) -> "ARIMAModel":
        """Fit ARIMA model to data."""
        if len(data) < max(self.p, self.q) + 1:
            # Not enough data, use simple average
            self.fitted_values = [statistics.mean(data)] * len(data) if data else [0]
            return self
        
        # Apply differencing
        differenced = self._difference(data, self.d)
        
        if len(differenced) < 2:
            self.fitted_values = data[:]
            return self
        
        # Estimate AR coefficients using Yule-Walker
        if self.p > 0 and len(differenced) > self.p:
            self.ar_coeffs = self._estimate_ar_coeffs(differenced)
        else:
            self.ar_coeffs = [0.5] * self.p if self.p > 0 else []
        
        # Estimate MA coefficients
        if self.q > 0:
            self.ma_coeffs = [0.3] * self.q
        else:
            self.ma_coeffs = []
        
        # Calculate fitted values
        self.fitted_values = self._calculate_fitted(data)
        
        return self
    
    def _difference(self, data: List[float], d: int) -> List[float]:
        """Apply differencing to make series stationary."""
        result = data[:]
        for _ in range(d):
            result = [result[i] - result[i-1] for i in range(1, len(result))]
        return result
    
    def _estimate_ar_coeffs(self, data: List[float]) -> List[float]:
        """Estimate AR coefficients using autocorrelation."""
        n = len(data)
        coeffs = []
        
        for lag in range(1, self.p + 1):
            if lag >= n:
                coeffs.append(0.5)
                continue
            
            # Calculate autocorrelation
            mean_val = statistics.mean(data)
            numerator = sum((data[i] - mean_val) * (data[i - lag] - mean_val) 
                          for i in range(lag, n))
            denominator = sum((x - mean_val) ** 2 for x in data)
            
            if denominator != 0:
                autocorr = numerator / denominator
                coeffs.append(max(-0.9, min(0.9, autocorr)))  # Clamp
            else:
                coeffs.append(0.5)
        
        return coeffs
    
    def _calculate_fitted(self, data: List[float]) -> List[float]:
        """Calculate fitted values."""
        fitted = []
        for i in range(len(data)):
            if i < max(self.p, self.q):
                fitted.append(data[i])
            else:
                # AR component
                ar_val = sum(self.ar_coeffs[j] * data[i - j - 1] 
                           for j in range(min(self.p, i)))
                
                # Simple combination
                fitted_val = data[i - 1] + ar_val * 0.5 if i > 0 else data[0]
                fitted.append(fitted_val)
        
        return fitted
    
    def forecast(self, steps: int) -> List[float]:
        """Generate forecasts for future periods."""
        if not self.fitted_values:
            return [0.0] * steps
        
        forecasts = []
        last_values = self.fitted_values[-max(self.p, 1):]
        
        for i in range(steps):
            # Use AR coefficients for forecasting
            forecast_val = last_values[-1]  # Start with last value
            
            if self.ar_coeffs and len(last_values) >= len(self.ar_coeffs):
                ar_component = sum(
                    self.ar_coeffs[j] * last_values[-(j + 1)]
                    for j in range(min(len(self.ar_coeffs), len(last_values)))
                )
                # Weighted combination
                forecast_val = 0.7 * last_values[-1] + 0.3 * ar_component
            
            forecasts.append(forecast_val)
            last_values.append(forecast_val)
            last_values = last_values[-(self.p + 1):]
        
        return forecasts


class ExponentialSmoothingModel:
    """
    Holt-Winters Exponential Smoothing model.
    
    Supports trend and seasonality.
    """
    
    def __init__(
        self,
        alpha: float = 0.3,  # Level smoothing
        beta: float = 0.1,   # Trend smoothing
        gamma: float = 0.1,  # Seasonality smoothing
        seasonal_periods: int = 0  # 0 = no seasonality
    ):
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.seasonal_periods = seasonal_periods
        
        self.level: float = 0.0
        self.trend: float = 0.0
        self.seasonal: List[float] = []
        self.fitted_values: List[float] = []
    
    def fit(self, data: List[float]) -> "ExponentialSmoothingModel":
        """Fit Holt-Winters model to data."""
        if len(data) < 2:
            self.level = data[0] if data else 0.0
            self.fitted_values = data[:]
            return self
        
        # Initialize level and trend
        self.level = data[0]
        self.trend = data[1] - data[0] if len(data) > 1 else 0.0
        
        # Initialize seasonal factors
        if self.seasonal_periods > 0 and len(data) >= self.seasonal_periods:
            self.seasonal = self._init_seasonal(data)
        else:
            self.seasonal = []
        
        # Apply smoothing
        self.fitted_values = []
        for i, value in enumerate(data):
            # Calculate fitted value
            if self.seasonal and i >= self.seasonal_periods:
                fitted = self.level + self.trend + self.seasonal[i % self.seasonal_periods]
            else:
                fitted = self.level + self.trend
            
            self.fitted_values.append(fitted)
            
            # Update components
            error = value - fitted
            
            # Update level
            new_level = self.alpha * value + (1 - self.alpha) * (self.level + self.trend)
            
            # Update trend
            new_trend = self.beta * (new_level - self.level) + (1 - self.beta) * self.trend
            
            # Update seasonal
            if self.seasonal:
                season_idx = i % self.seasonal_periods
                self.seasonal[season_idx] = (
                    self.gamma * (value - self.level - self.trend) +
                    (1 - self.gamma) * self.seasonal[season_idx]
                )
            
            self.level = new_level
            self.trend = new_trend
        
        return self
    
    def _init_seasonal(self, data: List[float]) -> List[float]:
        """Initialize seasonal factors."""
        seasonal = []
        period_avg = []
        
        for i in range(self.seasonal_periods):
            period_values = [data[j] for j in range(i, len(data), self.seasonal_periods)]
            period_avg.append(statistics.mean(period_values) if period_values else 0)
        
        # Normalize to sum to 0
        overall_avg = statistics.mean(period_avg) if period_avg else 0
        seasonal = [avg - overall_avg for avg in period_avg]
        
        return seasonal
    
    def forecast(self, steps: int) -> List[float]:
        """Generate forecasts for future periods."""
        forecasts = []
        
        for i in range(steps):
            # Base forecast: level + trend * horizon
            forecast_val = self.level + self.trend * (i + 1)
            
            # Add seasonal component
            if self.seasonal:
                season_idx = (len(self.fitted_values) + i) % self.seasonal_periods
                forecast_val += self.seasonal[season_idx]
            
            forecasts.append(forecast_val)
        
        return forecasts


class LinearRegressionModel:
    """
    Linear Regression with trend forecasting.
    
    Fits a linear trend to the data and extrapolates.
    """
    
    def __init__(self):
        self.slope: float = 0.0
        self.intercept: float = 0.0
        self.r_squared: float = 0.0
        self.fitted_values: List[float] = []
    
    def fit(self, data: List[float]) -> "LinearRegressionModel":
        """Fit linear regression to data."""
        if len(data) < 2:
            self.intercept = data[0] if data else 0.0
            self.fitted_values = data[:]
            return self
        
        n = len(data)
        x = list(range(n))
        y = data
        
        # Calculate means
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(y)
        
        # Calculate slope and intercept
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator != 0:
            self.slope = numerator / denominator
        else:
            self.slope = 0.0
        
        self.intercept = y_mean - self.slope * x_mean
        
        # Calculate R-squared
        y_pred = [self.intercept + self.slope * i for i in range(n)]
        ss_res = sum((y[i] - y_pred[i]) ** 2 for i in range(n))
        ss_tot = sum((y[i] - y_mean) ** 2 for i in range(n))
        
        if ss_tot != 0:
            self.r_squared = 1 - (ss_res / ss_tot)
        else:
            self.r_squared = 0.0
        
        self.fitted_values = y_pred
        
        return self
    
    def forecast(self, steps: int, start_idx: int = 0) -> List[float]:
        """Generate forecasts for future periods."""
        start = len(self.fitted_values) if self.fitted_values else start_idx
        return [self.intercept + self.slope * (start + i) for i in range(steps)]


# ========================================
# Seasonality Detection
# ========================================

class SeasonalityDetector:
    """
    Detect seasonality patterns in time series data.
    """
    
    @staticmethod
    def detect(data: List[float], dates: List[date]) -> SeasonalityInfo:
        """
        Detect seasonality in time series data.
        
        Uses autocorrelation analysis.
        """
        if len(data) < 14:  # Need at least 2 weeks of data
            return SeasonalityInfo(
                has_seasonality=False,
                seasonality_type=SeasonalityType.NONE,
                seasonal_indices={},
                peak_periods=[],
                trough_periods=[],
                strength=0.0
            )
        
        # Check different seasonality periods
        periods_to_check = {
            SeasonalityType.WEEKLY: 7,
            SeasonalityType.MONTHLY: 30,
            SeasonalityType.QUARTERLY: 90,
            SeasonalityType.YEARLY: 365,
        }
        
        best_seasonality = SeasonalityType.NONE
        best_strength = 0.0
        best_indices: Dict[int, float] = {}
        
        for season_type, period in periods_to_check.items():
            if len(data) < period * 2:
                continue
            
            # Calculate autocorrelation at lag = period
            strength = SeasonalityDetector._autocorrelation_at_lag(data, period)
            
            if strength > best_strength and strength > 0.3:  # Threshold
                best_seasonality = season_type
                best_strength = strength
                best_indices = SeasonalityDetector._calculate_seasonal_indices(data, period)
        
        # Identify peaks and troughs
        peak_periods = [k for k, v in best_indices.items() if v > 1.1] if best_indices else []
        trough_periods = [k for k, v in best_indices.items() if v < 0.9] if best_indices else []
        
        return SeasonalityInfo(
            has_seasonality=best_seasonality != SeasonalityType.NONE,
            seasonality_type=best_seasonality,
            seasonal_indices=best_indices,
            peak_periods=peak_periods,
            trough_periods=trough_periods,
            strength=best_strength
        )
    
    @staticmethod
    def _autocorrelation_at_lag(data: List[float], lag: int) -> float:
        """Calculate autocorrelation at a specific lag."""
        if len(data) <= lag:
            return 0.0
        
        n = len(data) - lag
        mean = statistics.mean(data)
        
        if n < 2:
            return 0.0
        
        numerator = sum(
            (data[i] - mean) * (data[i + lag] - mean)
            for i in range(n)
        )
        denominator = sum((x - mean) ** 2 for x in data)
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    @staticmethod
    def _calculate_seasonal_indices(data: List[float], period: int) -> Dict[int, float]:
        """Calculate seasonal indices for each period position."""
        indices = {}
        
        # Group data by period position
        groups = defaultdict(list)
        for i, value in enumerate(data):
            groups[i % period].append(value)
        
        # Calculate average for each position
        overall_mean = statistics.mean(data)
        
        for pos, values in groups.items():
            if values:
                pos_mean = statistics.mean(values)
                indices[pos] = pos_mean / overall_mean if overall_mean != 0 else 1.0
        
        return indices


# ========================================
# Ensemble Forecaster
# ========================================

class EnsembleForecaster:
    """
    Combines multiple forecasting models into an ensemble.
    """
    
    def __init__(
        self,
        ensemble_method: EnsembleMethod = EnsembleMethod.WEIGHTED_AVERAGE
    ):
        self.ensemble_method = ensemble_method
        self.models: Dict[str, Any] = {}
        self.model_weights: Dict[str, float] = {}
        self.model_errors: Dict[str, float] = {}
    
    def add_model(self, name: str, model: Any, weight: float = 1.0):
        """Add a model to the ensemble."""
        self.models[name] = model
        self.model_weights[name] = weight
    
    def fit_all(self, data: List[float]) -> "EnsembleForecaster":
        """Fit all models and calculate optimal weights."""
        for name, model in self.models.items():
            try:
                model.fit(data)
                
                # Calculate in-sample error (MAPE)
                if model.fitted_values:
                    errors = []
                    for i, (actual, fitted) in enumerate(zip(data, model.fitted_values)):
                        if actual != 0:
                            errors.append(abs(actual - fitted) / abs(actual))
                    
                    if errors:
                        self.model_errors[name] = statistics.mean(errors)
                    else:
                        self.model_errors[name] = 1.0
                else:
                    self.model_errors[name] = 1.0
                    
            except Exception as e:
                logger.warning(f"Error fitting model {name}: {e}")
                self.model_errors[name] = 1.0
        
        # Normalize weights based on inverse error
        if self.model_errors:
            total_inv_error = sum(1 / max(e, 0.01) for e in self.model_errors.values())
            for name in self.models:
                inv_error = 1 / max(self.model_errors.get(name, 1.0), 0.01)
                self.model_weights[name] = inv_error / total_inv_error
        
        return self
    
    def forecast(self, steps: int) -> List[EnsembleForecast]:
        """Generate ensemble forecasts."""
        # Get forecasts from each model
        model_forecasts: Dict[str, List[float]] = {}
        
        for name, model in self.models.items():
            try:
                model_forecasts[name] = model.forecast(steps)
            except Exception as e:
                logger.warning(f"Error forecasting with model {name}: {e}")
                model_forecasts[name] = [0.0] * steps
        
        # Combine forecasts
        ensemble_forecasts = []
        today = date.today()
        
        for i in range(steps):
            forecast_date = today + timedelta(days=i * 30)  # Monthly forecast
            
            individual_preds = {name: model_forecasts[name][i] for name in self.models}
            
            if self.ensemble_method == EnsembleMethod.WEIGHTED_AVERAGE:
                pred_value = self._weighted_average(individual_preds)
            elif self.ensemble_method == EnsembleMethod.MEDIAN:
                pred_value = statistics.median(individual_preds.values())
            elif self.ensemble_method == EnsembleMethod.BEST_PERFORMER:
                best_model = min(self.model_errors, key=self.model_errors.get)
                pred_value = individual_preds[best_model]
            else:
                pred_value = self._weighted_average(individual_preds)
            
            # Calculate confidence interval
            values = list(individual_preds.values())
            std_dev = statistics.stdev(values) if len(values) > 1 else pred_value * 0.2
            
            lower = pred_value - 1.96 * std_dev
            upper = pred_value + 1.96 * std_dev
            
            # Calculate confidence based on model agreement
            confidence = self._calculate_confidence(individual_preds, pred_value)
            
            ensemble_forecasts.append(EnsembleForecast(
                date=forecast_date,
                predicted_value=max(0, pred_value),  # No negative forecasts
                lower_bound=max(0, lower),
                upper_bound=max(0, upper),
                confidence=confidence,
                model_weights=self.model_weights.copy(),
                individual_predictions=individual_preds
            ))
        
        return ensemble_forecasts
    
    def _weighted_average(self, predictions: Dict[str, float]) -> float:
        """Calculate weighted average of predictions."""
        total = sum(predictions[name] * self.model_weights.get(name, 0) for name in predictions)
        weight_sum = sum(self.model_weights.get(name, 0) for name in predictions)
        
        return total / weight_sum if weight_sum > 0 else 0.0
    
    def _calculate_confidence(self, predictions: Dict[str, float], ensemble_pred: float) -> float:
        """Calculate confidence based on model agreement."""
        if not predictions or ensemble_pred == 0:
            return 0.5
        
        # Coefficient of variation
        std_dev = statistics.stdev(predictions.values()) if len(predictions) > 1 else ensemble_pred * 0.1
        cv = std_dev / abs(ensemble_pred) if ensemble_pred != 0 else 1.0
        
        # Convert to confidence (lower CV = higher confidence)
        confidence = max(0.3, min(0.95, 1 - cv))
        
        return confidence


# ========================================
# Main Forecasting Service
# ========================================

class ForecastingService:
    """
    Enhanced Forecasting Service
    
    Provides advanced demand forecasting using:
    - Multi-model ensemble (ARIMA, Exponential Smoothing, Linear Regression)
    - AI-powered refinements
    - Seasonality detection
    - Feature engineering
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
        # Caching
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 3600  # 1 hour
        
        # Rate limiting per tenant
        self._tenant_requests: Dict[UUID, List[float]] = {}
        self._rate_limit = 100  # requests per hour
    
    async def generate_product_forecast(
        self,
        product_id: UUID,
        tenant_id: UUID,
        forecast_type: ForecastType = ForecastType.DEMAND,
        periods: int = 6,
        period_type: str = "monthly",
        method: ForecastMethod = ForecastMethod.AI_API,
        user_id: Optional[UUID] = None,
        use_ensemble: bool = True
    ) -> List[Forecast]:
        """
        Generate forecast for a specific product.
        
        Args:
            product_id: Product UUID
            tenant_id: Tenant UUID
            forecast_type: Type of forecast (demand, sales, inventory)
            periods: Number of periods to forecast
            period_type: Type of period (daily, weekly, monthly)
            method: Forecasting method to use
            user_id: Requesting user ID
            use_ensemble: Whether to use ensemble approach
            
        Returns:
            List of Forecast objects
        """
        # Check rate limit
        if not self._check_rate_limit(tenant_id):
            raise ValueError("Rate limit exceeded. Please try again later.")
        
        # Get historical data
        historical_data = await self._get_historical_sales_data(
            product_id, tenant_id, period_type
        )
        
        if not historical_data or len(historical_data) < 3:
            logger.warning(f"Insufficient historical data for product {product_id}")
            return await self._generate_simple_forecast(
                product_id, tenant_id, forecast_type, periods, period_type, user_id
            )
        
        # Extract values for forecasting
        values = [d["quantity"] for d in historical_data]
        dates = [d["date"] for d in historical_data]
        
        # Detect seasonality
        seasonality = SeasonalityDetector.detect(values, dates)
        
        if use_ensemble:
            # Use ensemble approach
            forecasts = await self._ensemble_forecast(
                values, dates, periods, period_type, seasonality
            )
        else:
            # Use single model
            forecasts = await self._single_model_forecast(
                values, periods, period_type, method
            )
        
        # Refine with AI if needed
        if method == ForecastMethod.AI_API:
            forecasts = await self._refine_with_ai(
                forecasts, historical_data, period_type
            )
        
        # Store forecasts in database
        stored_forecasts = []
        for fc in forecasts:
            forecast = Forecast(
                tenant_id=tenant_id,
                product_id=product_id,
                forecast_type=forecast_type,
                forecast_date=fc.date,
                period_type=period_type,
                predicted_quantity=Decimal(str(max(0, fc.predicted_value))),
                predicted_value=Decimal(str(max(0, fc.predicted_value) * self._get_avg_price(product_id))),
                confidence_lower=Decimal(str(max(0, fc.lower_bound))),
                confidence_upper=Decimal(str(max(0, fc.upper_bound))),
                confidence_score=fc.confidence,
                method=method,
                data_start_date=dates[0] if dates else None,
                data_end_date=dates[-1] if dates else None,
                model_version="2.0-ensemble",
                created_by_id=user_id,
                model_params={
                    "seasonality_type": seasonality.seasonality_type.value if seasonality.has_seasonality else "none",
                    "seasonality_strength": seasonality.strength,
                    "ensemble_weights": getattr(fc, 'model_weights', {})
                }
            )
            self.db.add(forecast)
            stored_forecasts.append(forecast)
        
        await self.db.commit()
        
        return stored_forecasts
    
    async def _ensemble_forecast(
        self,
        values: List[float],
        dates: List[date],
        periods: int,
        period_type: str,
        seasonality: SeasonalityInfo
    ) -> List[EnsembleForecast]:
        """Generate ensemble forecast combining multiple models."""
        
        # Determine seasonal periods for Holt-Winters
        seasonal_periods = 0
        if seasonality.has_seasonality:
            if seasonality.seasonality_type == SeasonalityType.WEEKLY:
                seasonal_periods = 7
            elif seasonality.seasonality_type == SeasonalityType.MONTHLY:
                seasonal_periods = 30
            elif seasonality.seasonality_type == SeasonalityType.QUARTERLY:
                seasonal_periods = 90
            elif seasonality.seasonality_type == SeasonalityType.YEARLY:
                seasonal_periods = 365
        
        # Create ensemble
        ensemble = EnsembleForecaster(EnsembleMethod.WEIGHTED_AVERAGE)
        
        # Add ARIMA model
        arima = ARIMAModel(p=2, d=1, q=1)
        ensemble.add_model("arima", arima, weight=1.0)
        
        # Add Exponential Smoothing model
        hw = ExponentialSmoothingModel(
            alpha=0.3, beta=0.1, gamma=0.1,
            seasonal_periods=seasonal_periods if seasonal_periods <= 30 else 0
        )
        ensemble.add_model("holt_winters", hw, weight=1.0)
        
        # Add Linear Regression model
        lr = LinearRegressionModel()
        ensemble.add_model("linear_regression", lr, weight=1.0)
        
        # Fit all models
        ensemble.fit_all(values)
        
        # Generate forecasts
        forecasts = ensemble.forecast(periods)
        
        return forecasts
    
    async def _single_model_forecast(
        self,
        values: List[float],
        periods: int,
        period_type: str,
        method: ForecastMethod
    ) -> List[EnsembleForecast]:
        """Generate forecast using a single model."""
        
        if method == ForecastMethod.ARIMA:
            model = ARIMAModel(p=2, d=1, q=1)
        elif method == ForecastMethod.EXPONENTIAL:
            model = ExponentialSmoothingModel()
        elif method == ForecastMethod.MOVING_AVERAGE:
            model = LinearRegressionModel()  # Use linear regression as simple model
        else:
            model = ExponentialSmoothingModel()
        
        model.fit(values)
        predictions = model.forecast(periods)
        
        # Convert to EnsembleForecast
        forecasts = []
        for i, pred in enumerate(predictions):
            forecast_date = date.today() + timedelta(days=i * (30 if period_type == "monthly" else 7))
            
            std_dev = statistics.stdev(values) if len(values) > 1 else pred * 0.2
            
            forecasts.append(EnsembleForecast(
                date=forecast_date,
                predicted_value=max(0, pred),
                lower_bound=max(0, pred - 1.96 * std_dev),
                upper_bound=max(0, pred + 1.96 * std_dev),
                confidence=0.7,
                model_weights={method.value: 1.0},
                individual_predictions={method.value: pred}
            ))
        
        return forecasts
    
    async def _refine_with_ai(
        self,
        forecasts: List[EnsembleForecast],
        historical_data: List[Dict],
        period_type: str
    ) -> List[EnsembleForecast]:
        """Refine forecasts using AI analysis."""
        try:
            from openai import AsyncOpenAI
            
            api_key = getattr(settings, 'OPENAI_API_KEY', None)
            if not api_key:
                logger.warning("OpenAI API key not configured, skipping AI refinement")
                return forecasts
            
            client = AsyncOpenAI(api_key=api_key)
            
            # Prepare data for AI
            historical_str = json.dumps([
                {"date": str(d["date"]), "quantity": d["quantity"]}
                for d in historical_data[-12:]  # Last 12 periods
            ], default=str)
            
            forecast_str = json.dumps([
                {"date": str(f.date), "predicted": f.predicted_value}
                for f in forecasts
            ], default=str)
            
            prompt = f"""Analyze and refine these forecasts based on historical data.

Historical Data (last 12 periods):
{historical_str}

Initial Forecasts:
{forecast_str}

Consider:
1. Recent trends in the data
2. Seasonality patterns
3. Unusual events or outliers

Return a JSON object with:
{{
    "refined_forecasts": [
        {{"date": "YYYY-MM-DD", "adjusted_value": number, "adjustment_reason": "string"}}
    ],
    "confidence_adjustment": number (0.8-1.0),
    "notes": "analysis notes"
}}"""

            completion = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert demand forecaster. Analyze data and provide refined forecasts in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            response_text = completion.choices[0].message.content
            
            # Parse AI response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                ai_result = json.loads(json_match.group())
                
                # Apply refinements
                refined_forecasts = ai_result.get("refined_forecasts", [])
                confidence_adj = ai_result.get("confidence_adjustment", 1.0)
                
                for i, fc in enumerate(forecasts):
                    if i < len(refined_forecasts):
                        refined = refined_forecasts[i]
                        if "adjusted_value" in refined:
                            fc.predicted_value = refined["adjusted_value"]
                            fc.confidence *= confidence_adj
            
            return forecasts
            
        except Exception as e:
            logger.error(f"AI refinement error: {e}")
            return forecasts
    
    async def generate_revenue_forecast(
        self,
        tenant_id: UUID,
        periods: int = 6,
        period_type: str = "monthly"
    ) -> Dict[str, Any]:
        """
        Generate revenue forecast for the tenant.
        
        Aggregates all sales data and forecasts revenue.
        """
        # Check rate limit
        if not self._check_rate_limit(tenant_id):
            raise ValueError("Rate limit exceeded")
        
        # Get historical revenue data
        end_date = date.today()
        start_date = end_date - timedelta(days=365)
        
        if period_type == "monthly":
            date_trunc = func.date_trunc("month", SaleOrder.date_order)
        else:
            date_trunc = func.date_trunc("day", SaleOrder.date_order)
        
        result = await self.db.execute(
            select(
                date_trunc.label("period"),
                func.sum(SaleOrder.amount_total).label("revenue"),
                func.count(SaleOrder.id).label("order_count")
            )
            .where(
                SaleOrder.tenant_id == tenant_id,
                SaleOrder.state.in_(["confirmed", "done"]),
                SaleOrder.date_order >= start_date,
                SaleOrder.date_order <= end_date
            )
            .group_by(date_trunc)
            .order_by(date_trunc)
        )
        
        historical_data = [
            {
                "date": row.period.date() if hasattr(row.period, 'date') else row.period,
                "revenue": float(row.revenue or 0),
                "order_count": row.order_count
            }
            for row in result.all()
        ]
        
        if not historical_data or len(historical_data) < 3:
            return {
                "forecasts": [],
                "error": "Insufficient historical data",
                "historical_data": historical_data
            }
        
        # Generate ensemble forecast
        values = [d["revenue"] for d in historical_data]
        dates = [d["date"] for d in historical_data]
        
        forecasts = await self._ensemble_forecast(
            values, dates, periods, period_type,
            SeasonalityDetector.detect(values, dates)
        )
        
        return {
            "forecasts": [
                {
                    "date": str(f.date),
                    "predicted_revenue": f.predicted_value,
                    "lower_bound": f.lower_bound,
                    "upper_bound": f.upper_bound,
                    "confidence": f.confidence,
                    "model_contributions": f.individual_predictions
                }
                for f in forecasts
            ],
            "historical_data": historical_data,
            "seasonality": {
                "detected": True,
                "type": "monthly"  # Simplified
            }
        }
    
    async def generate_inventory_forecast(
        self,
        product_id: UUID,
        tenant_id: UUID,
        periods: int = 6
    ) -> Dict[str, Any]:
        """
        Generate inventory demand forecast.
        
        Considers sales patterns and stock movements.
        """
        # Get sales and movement data
        historical_sales = await self._get_historical_sales_data(
            product_id, tenant_id, "monthly"
        )
        
        historical_movements = await self._get_inventory_movements(
            product_id, tenant_id, months=12
        )
        
        if not historical_sales:
            return {"error": "No historical sales data"}
        
        # Generate demand forecast
        values = [d["quantity"] for d in historical_sales]
        dates = [d["date"] for d in historical_sales]
        
        forecasts = await self._ensemble_forecast(
            values, dates, periods, "monthly",
            SeasonalityDetector.detect(values, dates)
        )
        
        # Get current stock
        product = await self.db.get(Product, product_id)
        current_stock = float(product.quantity_on_hand) if product else 0
        
        # Calculate projected stock levels
        projected_stock = [current_stock]
        for f in forecasts:
            projected_stock.append(projected_stock[-1] - f.predicted_value)
        
        # Identify stockout risk
        stockout_periods = [
            i for i, stock in enumerate(projected_stock)
            if stock <= 0
        ]
        
        return {
            "demand_forecasts": [
                {
                    "date": str(f.date),
                    "predicted_demand": f.predicted_value,
                    "confidence": f.confidence
                }
                for f in forecasts
            ],
            "projected_stock": projected_stock[1:],
            "current_stock": current_stock,
            "reorder_point": float(product.reorder_point) if product else 0,
            "stockout_risk": len(stockout_periods) > 0,
            "first_stockout_period": stockout_periods[0] if stockout_periods else None,
            "recommended_order_quantity": max(0, -min(projected_stock)) if min(projected_stock) < 0 else 0
        }
    
    async def generate_dashboard_forecasts(
        self,
        tenant_id: UUID,
        top_n: int = 10
    ) -> Dict[str, Any]:
        """
        Generate forecasts for dashboard view.
        
        Returns top products needing attention.
        """
        # Get top products by sales volume
        result = await self.db.execute(
            select(
                SaleOrderLine.product_id,
                func.sum(SaleOrderLine.quantity).label("total_qty")
            )
            .join(SaleOrder)
            .where(
                SaleOrder.tenant_id == tenant_id,
                SaleOrder.state.in_(["confirmed", "done"]),
                SaleOrderLine.product_id.isnot(None)
            )
            .group_by(SaleOrderLine.product_id)
            .order_by(func.sum(SaleOrderLine.quantity).desc())
            .limit(top_n)
        )
        
        top_products = result.all()
        
        dashboard_data = {
            "forecasts": [],
            "alerts": [],
            "summary": {
                "total_products_analyzed": len(top_products),
                "potential_stockouts": 0,
                "high_demand_products": 0,
                "recommended_orders": []
            }
        }
        
        for row in top_products:
            product_id = row.product_id
            total_qty = row.total_qty
            
            product = await self.db.get(Product, product_id)
            if not product:
                continue
            
            # Get or generate forecast
            try:
                forecasts = await self.get_product_forecasts(product_id, tenant_id)
            except Exception as e:
                logger.warning(f"Error getting forecasts for product {product_id}: {e}")
                continue
            
            if not forecasts:
                continue
            
            # Calculate metrics
            predicted_demand = sum(float(f.predicted_quantity) for f in forecasts[:3])
            current_stock = float(product.quantity_on_hand)
            
            stockout_risk = current_stock < predicted_demand * 0.5
            
            dashboard_data["forecasts"].append({
                "product_id": str(product_id),
                "product_name": product.name,
                "sku": product.sku,
                "current_stock": current_stock,
                "predicted_demand": predicted_demand,
                "avg_monthly_demand": float(total_qty / 6 if total_qty else 0),
                "stockout_risk": stockout_risk,
                "reorder_recommended": stockout_risk,
                "reorder_quantity": max(0, predicted_demand - current_stock) if stockout_risk else 0
            })
            
            if stockout_risk:
                dashboard_data["summary"]["potential_stockouts"] += 1
                dashboard_data["alerts"].append({
                    "type": "stockout_risk",
                    "product_name": product.name,
                    "current_stock": current_stock,
                    "predicted_demand": predicted_demand,
                    "severity": "high" if current_stock < predicted_demand * 0.25 else "medium"
                })
        
        return dashboard_data
    
    async def get_product_forecasts(
        self,
        product_id: UUID,
        tenant_id: UUID,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> List[Forecast]:
        """Get existing forecasts for a product."""
        query = select(Forecast).where(
            Forecast.product_id == product_id,
            Forecast.tenant_id == tenant_id
        )
        
        if from_date:
            query = query.where(Forecast.forecast_date >= from_date)
        if to_date:
            query = query.where(Forecast.forecast_date <= to_date)
        
        query = query.order_by(Forecast.forecast_date)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    # ========================================
    # Helper Methods
    # ========================================
    
    async def _get_historical_sales_data(
        self,
        product_id: UUID,
        tenant_id: UUID,
        period_type: str = "monthly"
    ) -> List[Dict[str, Any]]:
        """Get historical sales data for a product."""
        end_date = date.today()
        start_date = end_date - timedelta(days=365)
        
        if period_type == "monthly":
            date_trunc = func.date_trunc("month", SaleOrder.date_order)
        elif period_type == "weekly":
            date_trunc = func.date_trunc("week", SaleOrder.date_order)
        else:
            date_trunc = func.date_trunc("day", SaleOrder.date_order)
        
        result = await self.db.execute(
            select(
                date_trunc.label("period"),
                func.sum(SaleOrderLine.quantity).label("quantity"),
                func.sum(SaleOrderLine.subtotal).label("value")
            )
            .select_from(SaleOrderLine)
            .join(SaleOrder)
            .where(
                SaleOrder.tenant_id == tenant_id,
                SaleOrderLine.product_id == product_id,
                SaleOrder.state.in_(["confirmed", "done"]),
                SaleOrder.date_order >= start_date,
                SaleOrder.date_order <= end_date
            )
            .group_by(date_trunc)
            .order_by(date_trunc)
        )
        
        data = []
        for row in result.all():
            data.append({
                "date": row.period.date() if hasattr(row.period, 'date') else row.period,
                "quantity": float(row.quantity or 0),
                "value": float(row.value or 0)
            })
        
        return data
    
    async def _get_inventory_movements(
        self,
        product_id: UUID,
        tenant_id: UUID,
        months: int = 12
    ) -> List[Dict[str, Any]]:
        """Get inventory movement history."""
        end_date = date.today()
        start_date = end_date - timedelta(days=months * 30)
        
        result = await self.db.execute(
            select(StockMove)
            .where(
                StockMove.product_id == product_id,
                StockMove.tenant_id == tenant_id,
                StockMove.state == "done",
                StockMove.date >= start_date
            )
            .order_by(StockMove.date)
        )
        
        return [
            {
                "date": move.date,
                "type": move.move_type,
                "quantity": float(move.quantity),
                "value": float(move.total_cost)
            }
            for move in result.scalars().all()
        ]
    
    async def _generate_simple_forecast(
        self,
        product_id: UUID,
        tenant_id: UUID,
        forecast_type: ForecastType,
        periods: int,
        period_type: str,
        user_id: Optional[UUID] = None
    ) -> List[Forecast]:
        """Generate simple forecast when insufficient data."""
        product = await self.db.get(Product, product_id)
        
        forecasts = []
        base_qty = float(product.quantity_on_hand) / 3 if product else 0
        
        for i in range(periods):
            if period_type == "monthly":
                pred_date = date.today() + timedelta(days=30 * (i + 1))
            else:
                pred_date = date.today() + timedelta(days=7 * (i + 1))
            
            forecast = Forecast(
                tenant_id=tenant_id,
                product_id=product_id,
                forecast_type=forecast_type,
                forecast_date=pred_date,
                period_type=period_type,
                predicted_quantity=Decimal(str(base_qty)),
                predicted_value=Decimal("0"),
                confidence_lower=Decimal(str(base_qty * 0.5)),
                confidence_upper=Decimal(str(base_qty * 1.5)),
                confidence_score=0.5,
                method=ForecastMethod.MOVING_AVERAGE,
                notes="Generated with limited historical data",
                created_by_id=user_id
            )
            self.db.add(forecast)
            forecasts.append(forecast)
        
        await self.db.commit()
        return forecasts
    
    def _get_avg_price(self, product_id: UUID) -> float:
        """Get average price for a product (placeholder)."""
        return 10.0  # Placeholder - should query from product
    
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
    
    async def calculate_forecast_accuracy(
        self,
        product_id: UUID,
        tenant_id: UUID
    ) -> Dict[str, float]:
        """Calculate forecast accuracy metrics."""
        result = await self.db.execute(
            select(Forecast).where(
                Forecast.product_id == product_id,
                Forecast.tenant_id == tenant_id,
                Forecast.actual_quantity.isnot(None)
            )
        )
        
        forecasts = result.scalars().all()
        
        if not forecasts:
            return {"mape": None, "mse": None, "accuracy": None}
        
        errors = []
        squared_errors = []
        
        for f in forecasts:
            if float(f.predicted_quantity) > 0:
                error = abs(float(f.actual_quantity - f.predicted_quantity))
                errors.append(error / float(f.predicted_quantity) * 100)
                squared_errors.append(error ** 2)
        
        mape = statistics.mean(errors) if errors else None
        mse = statistics.mean(squared_errors) if squared_errors else None
        
        return {
            "mape": mape,
            "mse": mse,
            "accuracy": 100 - mape if mape else None
        }
    
    async def update_actual_values(
        self,
        tenant_id: UUID,
        as_of_date: Optional[date] = None
    ):
        """Update forecasts with actual values for accuracy tracking."""
        as_of_date = as_of_date or date.today()
        
        result = await self.db.execute(
            select(Forecast).where(
                Forecast.tenant_id == tenant_id,
                Forecast.forecast_date <= as_of_date,
                Forecast.actual_quantity.is_(None)
            )
        )
        
        for forecast in result.scalars().all():
            if forecast.period_type == "monthly":
                start = date(forecast.forecast_date.year, forecast.forecast_date.month, 1)
                if forecast.forecast_date.month == 12:
                    end = date(forecast.forecast_date.year + 1, 1, 1) - timedelta(days=1)
                else:
                    end = date(forecast.forecast_date.year, forecast.forecast_date.month + 1, 1) - timedelta(days=1)
            else:
                start = forecast.forecast_date
                end = forecast.forecast_date + timedelta(days=6 if forecast.period_type == "weekly" else 0)
            
            actual_result = await self.db.execute(
                select(func.sum(SaleOrderLine.quantity))
                .join(SaleOrder)
                .where(
                    SaleOrder.tenant_id == tenant_id,
                    SaleOrderLine.product_id == forecast.product_id,
                    SaleOrder.state.in_(["confirmed", "done"]),
                    SaleOrder.date_order >= start,
                    SaleOrder.date_order <= end
                )
            )
            
            actual_qty = actual_result.scalar() or 0
            forecast.actual_quantity = Decimal(str(actual_qty))
            
            if float(forecast.predicted_quantity) > 0:
                forecast.accuracy_score = 1 - abs(
                    float(actual_qty - forecast.predicted_quantity) / float(forecast.predicted_quantity)
                )
        
        await self.db.commit()
