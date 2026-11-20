"""
Nexus ERP - Advanced Anomaly Detection Service
===============================================

Comprehensive anomaly detection service with:
- Statistical methods: Z-score, IQR, MAD (Median Absolute Deviation)
- ML-based: Isolation Forest hints, pattern recognition
- Financial anomaly detection:
  - Unusual transaction amounts
  - Duplicate entries
  - Round number fraud
  - Timing anomalies
- Inventory anomaly detection:
  - Sudden stock changes
  - Negative stock events
  - Unusual sales patterns
- Alert generation with severity levels
- Response caching and rate limiting
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload
from dataclasses import dataclass, field
from enum import Enum
import logging
import json
import statistics
import math
from collections import defaultdict
import asyncio

from app.models.ai import AnomalyDetection
from app.models.accounting import JournalEntry, JournalItem, Account, AccountType
from app.models.sales import SaleOrder, SaleOrderLine
from app.models.inventory import Product, StockMove
from app.models.purchase import PurchaseOrder
from app.core.config import settings

logger = logging.getLogger(__name__)


# ========================================
# Enums and Data Classes
# ========================================

class AnomalyType(str, Enum):
    """Types of anomalies that can be detected."""
    # Financial anomalies
    DUPLICATE_ENTRY = "duplicate_entry"
    UNUSUAL_AMOUNT = "unusual_amount"
    ROUND_NUMBER = "round_number"
    TIMING_ANOMALY = "timing_anomaly"
    UNUSUAL_ACCOUNT = "unusual_account"
    SEQUENTIAL_PATTERN = "sequential_pattern"
    THRESHOLD_BREACH = "threshold_breach"
    BENFORD_VIOLATION = "benford_violation"
    
    # Inventory anomalies
    SUDDEN_STOCK_CHANGE = "sudden_stock_change"
    NEGATIVE_STOCK = "negative_stock"
    UNUSUAL_SALES_PATTERN = "unusual_sales_pattern"
    STOCKOUT_RISK = "stockout_risk"
    DEAD_STOCK = "dead_stock"
    
    # General
    MISSING_REFERENCE = "missing_reference"
    UNBALANCED_ENTRY = "unbalanced_entry"
    UNUSUAL_PARTNER = "unusual_partner"


class SeverityLevel(str, Enum):
    """Severity levels for anomalies."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DetectionMethod(str, Enum):
    """Detection methods used."""
    Z_SCORE = "z_score"
    IQR = "iqr"
    MAD = "mad"
    ISOLATION_FOREST = "isolation_forest"
    STATISTICAL_RULE = "statistical_rule"
    AI_ANALYSIS = "ai_analysis"
    PATTERN_MATCHING = "pattern_matching"


@dataclass
class AnomalyAlert:
    """Anomaly alert data structure."""
    id: Optional[UUID] = None
    anomaly_type: AnomalyType = AnomalyType.UNUSUAL_AMOUNT
    severity: SeverityLevel = SeverityLevel.MEDIUM
    title: str = ""
    description: str = ""
    source_model: str = ""
    source_id: Optional[UUID] = None
    detected_value: Decimal = Decimal("0")
    expected_value: Optional[Decimal] = None
    deviation_percent: float = 0.0
    detection_method: DetectionMethod = DetectionMethod.STATISTICAL_RULE
    confidence: float = 0.0
    recommendation: str = ""
    related_entities: List[UUID] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class AnomalyStatistics:
    """Statistics for anomaly detection."""
    total_analyzed: int = 0
    total_anomalies: int = 0
    anomalies_by_type: Dict[str, int] = field(default_factory=dict)
    anomalies_by_severity: Dict[str, int] = field(default_factory=dict)
    avg_deviation: float = 0.0
    detection_rate: float = 0.0


# ========================================
# Statistical Analysis Tools
# ========================================

class StatisticalAnalyzer:
    """
    Statistical analysis utilities for anomaly detection.
    """
    
    @staticmethod
    def z_score(value: float, mean: float, std_dev: float) -> float:
        """Calculate Z-score for a value."""
        if std_dev == 0:
            return 0.0
        return (value - mean) / std_dev
    
    @staticmethod
    def modified_z_score(value: float, median: float, mad: float) -> float:
        """
        Calculate modified Z-score using MAD.
        
        More robust to outliers than standard Z-score.
        """
        if mad == 0:
            return 0.0
        # 0.6745 is the 75th percentile of the standard normal distribution
        return 0.6745 * (value - median) / mad
    
    @staticmethod
    def calculate_mad(data: List[float]) -> Tuple[float, float]:
        """
        Calculate Median Absolute Deviation.
        
        Returns (median, mad)
        """
        if not data:
            return 0.0, 0.0
        
        median_val = statistics.median(data)
        absolute_deviations = [abs(x - median_val) for x in data]
        mad = statistics.median(absolute_deviations)
        
        return median_val, mad
    
    @staticmethod
    def iqr_bounds(data: List[float], multiplier: float = 1.5) -> Tuple[float, float, float, float]:
        """
        Calculate IQR-based bounds for outlier detection.
        
        Returns (q1, q3, lower_bound, upper_bound)
        """
        if len(data) < 4:
            min_val = min(data) if data else 0
            max_val = max(data) if data else 0
            return min_val, max_val, min_val, max_val
        
        sorted_data = sorted(data)
        n = len(sorted_data)
        
        q1_idx = int(n * 0.25)
        q3_idx = int(n * 0.75)
        
        q1 = sorted_data[q1_idx]
        q3 = sorted_data[q3_idx]
        iqr = q3 - q1
        
        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr
        
        return q1, q3, lower_bound, upper_bound
    
    @staticmethod
    def benford_expected_distribution() -> Dict[int, float]:
        """
        Get expected Benford's Law distribution.
        
        Used for detecting manipulated numbers.
        """
        return {
            1: 0.301,  # 30.1%
            2: 0.176,  # 17.6%
            3: 0.125,  # 12.5%
            4: 0.097,  # 9.7%
            5: 0.079,  # 7.9%
            6: 0.067,  # 6.7%
            7: 0.058,  # 5.8%
            8: 0.051,  # 5.1%
            9: 0.046,  # 4.6%
        }
    
    @staticmethod
    def benford_test(numbers: List[float]) -> Tuple[float, Dict[int, float]]:
        """
        Test if numbers follow Benford's Law.
        
        Returns (chi_square_stat, observed_distribution)
        """
        if not numbers:
            return 0.0, {}
        
        # Get first digits
        first_digits = []
        for num in numbers:
            if num == 0:
                continue
            abs_num = abs(num)
            # Get first non-zero digit
            while abs_num >= 10:
                abs_num /= 10
            while abs_num < 1 and abs_num > 0:
                abs_num *= 10
            first_digit = int(abs_num)
            if 1 <= first_digit <= 9:
                first_digits.append(first_digit)
        
        if not first_digits:
            return 0.0, {}
        
        # Calculate observed distribution
        observed = {i: 0 for i in range(1, 10)}
        for digit in first_digits:
            observed[digit] += 1
        
        total = len(first_digits)
        observed_dist = {i: observed[i] / total for i in range(1, 10)}
        
        # Chi-square test
        expected = StatisticalAnalyzer.benford_expected_distribution()
        chi_square = 0.0
        
        for digit in range(1, 10):
            expected_count = expected[digit] * total
            if expected_count > 0:
                chi_square += (observed[digit] - expected_count) ** 2 / expected_count
        
        return chi_square, observed_dist
    
    @staticmethod
    def is_round_number(value: float, threshold: float = 0.02) -> bool:
        """
        Check if value is suspiciously round.
        
        Round numbers may indicate estimation or manipulation.
        """
        if value == 0:
            return False
        
        abs_value = abs(value)
        
        # Check common round number thresholds
        round_thresholds = [10, 50, 100, 500, 1000, 5000, 10000, 50000, 100000]
        
        for threshold_val in round_thresholds:
            # Check if divisible by threshold
            remainder = abs_value % threshold_val
            if remainder < threshold_val * threshold or (threshold_val - remainder) < threshold_val * threshold:
                return True
        
        # Check if ends with many zeros
        str_val = f"{abs_value:.2f}".rstrip('0').rstrip('.')
        if len(str_val) > 2 and str_val[-2:] in ['00', '50']:
            return True
        
        return False
    
    @staticmethod
    def levenshtein_distance(s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return StatisticalAnalyzer.levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    @staticmethod
    def string_similarity(s1: str, s2: str) -> float:
        """Calculate similarity between two strings (0-1)."""
        if not s1 or not s2:
            return 0.0
        
        distance = StatisticalAnalyzer.levenshtein_distance(s1.lower(), s2.lower())
        max_len = max(len(s1), len(s2))
        
        return 1.0 - (distance / max_len)


# ========================================
# Isolation Forest Hints
# ========================================

class IsolationForestHints:
    """
    Simplified Isolation Forest implementation for anomaly detection.
    
    This is a lightweight version that provides hints about anomalies
    without requiring scikit-learn or heavy ML libraries.
    """
    
    def __init__(self, n_trees: int = 100, subsample_size: int = 256):
        self.n_trees = n_trees
        self.subsample_size = subsample_size
        self.trees: List[Dict] = []
        self.avg_path_lengths: Dict[int, float] = {}
    
    def fit(self, data: List[List[float]]) -> "IsolationForestHints":
        """
        Build isolation trees from data.
        
        Data should be a list of feature vectors.
        """
        import random
        
        if not data:
            return self
        
        n_samples = min(len(data), self.subsample_size)
        
        self.trees = []
        
        for _ in range(self.n_trees):
            # Subsample
            subsample = random.sample(data, min(n_samples, len(data)))
            
            # Build tree
            tree = self._build_tree(subsample, 0, max_depth=int(math.log2(n_samples)))
            self.trees.append(tree)
        
        return self
    
    def _build_tree(
        self,
        data: List[List[float]],
        depth: int,
        max_depth: int
    ) -> Dict:
        """Build a single isolation tree."""
        if depth >= max_depth or len(data) <= 1:
            return {"size": len(data), "external": True}
        
        # Select random feature
        n_features = len(data[0]) if data else 0
        if n_features == 0:
            return {"size": len(data), "external": True}
        
        feature_idx = random.randint(0, n_features - 1)
        
        # Get feature values
        values = [d[feature_idx] for d in data if len(d) > feature_idx]
        if not values:
            return {"size": len(data), "external": True}
        
        min_val, max_val = min(values), max(values)
        
        if min_val == max_val:
            return {"size": len(data), "external": True}
        
        # Random split point
        split_value = random.uniform(min_val, max_val)
        
        # Split data
        left_data = [d for d in data if len(d) > feature_idx and d[feature_idx] < split_value]
        right_data = [d for d in data if len(d) > feature_idx and d[feature_idx] >= split_value]
        
        return {
            "feature_idx": feature_idx,
            "split_value": split_value,
            "left": self._build_tree(left_data, depth + 1, max_depth),
            "right": self._build_tree(right_data, depth + 1, max_depth),
            "external": False
        }
    
    def anomaly_score(self, point: List[float]) -> float:
        """
        Calculate anomaly score for a point.
        
        Returns score between 0 and 1, where higher = more anomalous.
        """
        if not self.trees:
            return 0.5
        
        # Average path length
        total_path_length = 0.0
        
        for tree in self.trees:
            path_length = self._path_length(point, tree, 0)
            total_path_length += path_length
        
        avg_path = total_path_length / len(self.trees)
        
        # Normalize to anomaly score
        # Using harmonic number approximation for normalization
        c = 2.0 * (math.log(self.subsample_size - 1) + 0.5772156649) - 2.0 * (self.subsample_size - 1) / self.subsample_size
        
        if c == 0:
            return 0.5
        
        score = 2 ** (-avg_path / c)
        
        return score
    
    def _path_length(self, point: List[float], tree: Dict, depth: int) -> float:
        """Calculate path length for a point in a tree."""
        if tree.get("external", False):
            # Add expected path length for unbuilt subtree
            size = tree.get("size", 1)
            if size <= 1:
                return depth
            # Expected path length for size n
            return depth + 2.0 * (math.log(size - 1) + 0.5772156649) - 2.0 * (size - 1) / size
        
        feature_idx = tree["feature_idx"]
        split_value = tree["split_value"]
        
        if len(point) <= feature_idx:
            return depth + 1
        
        if point[feature_idx] < split_value:
            return self._path_length(point, tree["left"], depth + 1)
        else:
            return self._path_length(point, tree["right"], depth + 1)


# ========================================
# Financial Anomaly Detector
# ========================================

class FinancialAnomalyDetector:
    """
    Detects anomalies in financial transactions.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._analyzer = StatisticalAnalyzer()
        
        # Thresholds
        self.z_score_threshold = 3.0
        self.mad_threshold = 3.5
        self.similarity_threshold = 0.85
    
    async def detect_unusual_amounts(
        self,
        tenant_id: UUID,
        days: int = 30
    ) -> List[AnomalyAlert]:
        """Detect transactions with unusual amounts."""
        alerts = []
        
        start_date = date.today() - timedelta(days=days)
        
        # Get journal items
        result = await self.db.execute(
            select(JournalItem)
            .join(JournalEntry)
            .where(
                JournalEntry.tenant_id == tenant_id,
                JournalEntry.date >= start_date,
                JournalEntry.state == "posted"
            )
        )
        
        items = result.scalars().all()
        
        # Group by account
        account_items = defaultdict(list)
        for item in items:
            account_items[item.account_id].append(item)
        
        for account_id, account_item_list in account_items.items():
            if len(account_item_list) < 5:
                continue
            
            amounts = [float(item.debit or item.credit or 0) for item in account_item_list]
            
            # Z-score method
            mean = statistics.mean(amounts)
            std_dev = statistics.stdev(amounts) if len(amounts) > 1 else 0
            
            # MAD method (more robust)
            median_val, mad = StatisticalAnalyzer.calculate_mad(amounts)
            
            # IQR bounds
            q1, q3, lower_bound, upper_bound = StatisticalAnalyzer.iqr_bounds(amounts)
            
            for item in account_item_list:
                amount = float(item.debit or item.credit or 0)
                
                # Check Z-score
                z_score = StatisticalAnalyzer.z_score(amount, mean, std_dev) if std_dev > 0 else 0
                
                # Check modified Z-score
                mod_z_score = StatisticalAnalyzer.modified_z_score(amount, median_val, mad) if mad > 0 else 0
                
                # Check IQR bounds
                outside_iqr = amount < lower_bound or amount > upper_bound
                
                # Determine if anomaly
                is_anomaly = (
                    abs(z_score) > self.z_score_threshold or
                    abs(mod_z_score) > self.mad_threshold or
                    outside_iqr
                )
                
                if is_anomaly:
                    # Get account info
                    account = await self.db.get(Account, account_id)
                    account_name = account.name if account else str(account_id)
                    
                    # Calculate deviation
                    expected = mean if mean != 0 else median_val
                    deviation = abs(amount - expected) / expected * 100 if expected != 0 else 0
                    
                    # Determine severity
                    if abs(z_score) > 4 or abs(mod_z_score) > 5:
                        severity = SeverityLevel.CRITICAL
                    elif abs(z_score) > 3 or abs(mod_z_score) > 4:
                        severity = SeverityLevel.HIGH
                    else:
                        severity = SeverityLevel.MEDIUM
                    
                    alerts.append(AnomalyAlert(
                        anomaly_type=AnomalyType.UNUSUAL_AMOUNT,
                        severity=severity,
                        title=f"Unusual Amount in {account_name}",
                        description=f"Transaction amount {amount:,.2f} is unusual for account {account_name}. "
                                   f"Expected range: {lower_bound:,.2f} to {upper_bound:,.2f}",
                        source_model="journal_item",
                        source_id=item.id,
                        detected_value=Decimal(str(amount)),
                        expected_value=Decimal(str(expected)),
                        deviation_percent=deviation,
                        detection_method=DetectionMethod.Z_SCORE if abs(z_score) > abs(mod_z_score) else DetectionMethod.MAD,
                        confidence=min(1.0, max(abs(z_score), abs(mod_z_score)) / 5),
                        recommendation=f"Review transaction for accuracy. Z-score: {z_score:.2f}, "
                                      f"Modified Z-score: {mod_z_score:.2f}",
                        metadata={
                            "z_score": z_score,
                            "modified_z_score": mod_z_score,
                            "mean": mean,
                            "median": median_val,
                            "std_dev": std_dev,
                            "mad": mad,
                            "iqr_bounds": [lower_bound, upper_bound],
                            "account_name": account_name
                        }
                    ))
        
        return alerts
    
    async def detect_duplicate_entries(
        self,
        tenant_id: UUID,
        days: int = 30
    ) -> List[AnomalyAlert]:
        """Detect potential duplicate journal entries."""
        alerts = []
        
        start_date = date.today() - timedelta(days=days)
        
        # Get journal entries
        result = await self.db.execute(
            select(JournalEntry)
            .options(selectinload(JournalEntry.lines))
            .where(
                JournalEntry.tenant_id == tenant_id,
                JournalEntry.date >= start_date,
                JournalEntry.state == "posted"
            )
            .order_by(JournalEntry.date)
        )
        
        entries = result.scalars().all()
        
        # Group by amount (potential duplicates often have same amount)
        amount_groups = defaultdict(list)
        for entry in entries:
            key = round(float(entry.total_debit), 2)
            amount_groups[key].append(entry)
        
        # Check groups with multiple entries
        for amount, group in amount_groups.items():
            if len(group) < 2:
                continue
            
            for i, entry1 in enumerate(group):
                for entry2 in group[i + 1:]:
                    # Calculate similarity
                    similarity = self._calculate_entry_similarity(entry1, entry2)
                    
                    if similarity > self.similarity_threshold:
                        alerts.append(AnomalyAlert(
                            anomaly_type=AnomalyType.DUPLICATE_ENTRY,
                            severity=SeverityLevel.HIGH,
                            title="Potential Duplicate Entry",
                            description=f"Entries {entry1.number} and {entry2.number} appear to be duplicates "
                                       f"(similarity: {similarity:.1%})",
                            source_model="journal_entry",
                            source_id=entry1.id,
                            detected_value=entry1.total_debit,
                            expected_value=None,
                            deviation_percent=(1 - similarity) * 100,
                            detection_method=DetectionMethod.PATTERN_MATCHING,
                            confidence=similarity,
                            recommendation=f"Review entries {entry1.number} and {entry2.number}. "
                                          "Consider reversing one entry if confirmed duplicate.",
                            related_entities=[entry2.id],
                            metadata={
                                "entry1_number": entry1.number,
                                "entry1_date": entry1.date.isoformat(),
                                "entry2_number": entry2.number,
                                "entry2_date": entry2.date.isoformat(),
                                "similarity_score": similarity
                            }
                        ))
        
        return alerts
    
    async def detect_round_number_fraud(
        self,
        tenant_id: UUID,
        days: int = 30
    ) -> List[AnomalyAlert]:
        """Detect suspiciously round transaction amounts."""
        alerts = []
        
        start_date = date.today() - timedelta(days=days)
        
        # Get journal items
        result = await self.db.execute(
            select(JournalItem)
            .join(JournalEntry)
            .where(
                JournalEntry.tenant_id == tenant_id,
                JournalEntry.date >= start_date,
                JournalEntry.state == "posted"
            )
        )
        
        items = result.scalars().all()
        
        # Track round number frequency
        round_count = 0
        total_count = 0
        
        for item in items:
            amount = float(item.debit or item.credit or 0)
            if amount > 0:
                total_count += 1
                if StatisticalAnalyzer.is_round_number(amount):
                    round_count += 1
                    
                    alerts.append(AnomalyAlert(
                        anomaly_type=AnomalyType.ROUND_NUMBER,
                        severity=SeverityLevel.LOW,
                        title="Round Number Transaction",
                        description=f"Transaction amount {amount:,.2f} is a suspiciously round number",
                        source_model="journal_item",
                        source_id=item.id,
                        detected_value=Decimal(str(amount)),
                        expected_value=None,
                        deviation_percent=0,
                        detection_method=DetectionMethod.STATISTICAL_RULE,
                        confidence=0.6,
                        recommendation="Verify this amount is accurate. Round numbers may indicate estimation or manipulation.",
                        metadata={"amount": amount}
                    ))
        
        # Check for excessive round numbers (Benford's Law violation)
        if total_count > 20:
            amounts = [float(item.debit or item.credit or 0) for item in items if (item.debit or item.credit)]
            chi_square, observed_dist = StatisticalAnalyzer.benford_test(amounts)
            
            # High chi-square indicates deviation from Benford's Law
            if chi_square > 15.51:  # Critical value at 0.05 significance for 8 degrees of freedom
                alerts.append(AnomalyAlert(
                    anomaly_type=AnomalyType.BENFORD_VIOLATION,
                    severity=SeverityLevel.MEDIUM,
                    title="Benford's Law Violation",
                    description=f"Transaction amounts deviate significantly from expected distribution "
                               f"(chi-square: {chi_square:.2f})",
                    source_model="journal_entries",
                    source_id=None,
                    detected_value=Decimal(str(chi_square)),
                    expected_value=Decimal("15.51"),
                    deviation_percent=(chi_square - 15.51) / 15.51 * 100,
                    detection_method=DetectionMethod.STATISTICAL_RULE,
                    confidence=min(1.0, chi_square / 30),
                    recommendation="Investigate transaction data for potential manipulation. "
                                  "Numbers should naturally follow Benford's Law distribution.",
                    metadata={
                        "chi_square": chi_square,
                        "observed_distribution": observed_dist,
                        "expected_distribution": StatisticalAnalyzer.benford_expected_distribution(),
                        "round_number_rate": round_count / total_count if total_count > 0 else 0
                    }
                ))
        
        return alerts
    
    async def detect_timing_anomalies(
        self,
        tenant_id: UUID,
        days: int = 30
    ) -> List[AnomalyAlert]:
        """Detect unusual timing patterns in transactions."""
        alerts = []
        
        start_date = date.today() - timedelta(days=days)
        
        result = await self.db.execute(
            select(JournalEntry)
            .where(
                JournalEntry.tenant_id == tenant_id,
                JournalEntry.date >= start_date,
                JournalEntry.state == "posted"
            )
            .order_by(JournalEntry.date)
        )
        
        entries = result.scalars().all()
        
        # Check for weekend transactions
        for entry in entries:
            if entry.date.weekday() >= 5:  # Saturday or Sunday
                alerts.append(AnomalyAlert(
                    anomaly_type=AnomalyType.TIMING_ANOMALY,
                    severity=SeverityLevel.LOW,
                    title="Weekend Transaction",
                    description=f"Entry {entry.number} was recorded on {entry.date.strftime('%A, %B %d')}",
                    source_model="journal_entry",
                    source_id=entry.id,
                    detected_value=entry.total_debit,
                    expected_value=None,
                    deviation_percent=0,
                    detection_method=DetectionMethod.STATISTICAL_RULE,
                    confidence=0.7,
                    recommendation="Verify this weekend transaction was intentional.",
                    metadata={
                        "day_of_week": entry.date.strftime("%A"),
                        "date": entry.date.isoformat()
                    }
                ))
        
        # Check for unusual clustering
        date_counts = defaultdict(int)
        for entry in entries:
            date_counts[entry.date] += 1
        
        if date_counts:
            counts = list(date_counts.values())
            mean_count = statistics.mean(counts)
            std_count = statistics.stdev(counts) if len(counts) > 1 else 0
            
            for entry_date, count in date_counts.items():
                if std_count > 0:
                    z_score = (count - mean_count) / std_count
                    
                    if z_score > 2:  # More than 2 std devs above mean
                        alerts.append(AnomalyAlert(
                            anomaly_type=AnomalyType.TIMING_ANOMALY,
                            severity=SeverityLevel.MEDIUM,
                            title="Unusual Transaction Clustering",
                            description=f"{count} transactions on {entry_date}, "
                                       f"which is {z_score:.1f} standard deviations above average",
                            source_model="journal_entry",
                            source_id=None,
                            detected_value=Decimal(str(count)),
                            expected_value=Decimal(str(mean_count)),
                            deviation_percent=(count - mean_count) / mean_count * 100 if mean_count > 0 else 0,
                            detection_method=DetectionMethod.Z_SCORE,
                            confidence=min(1.0, z_score / 4),
                            recommendation=f"Review transactions on {entry_date} for potential errors or fraud.",
                            metadata={
                                "date": entry_date.isoformat(),
                                "count": count,
                                "average_count": mean_count,
                                "z_score": z_score
                            }
                        ))
        
        return alerts
    
    async def detect_sequential_patterns(
        self,
        tenant_id: UUID,
        days: int = 30
    ) -> List[AnomalyAlert]:
        """Detect sequential patterns in transaction amounts."""
        alerts = []
        
        start_date = date.today() - timedelta(days=days)
        
        result = await self.db.execute(
            select(JournalEntry)
            .where(
                JournalEntry.tenant_id == tenant_id,
                JournalEntry.date >= start_date,
                JournalEntry.state == "posted"
            )
            .order_by(JournalEntry.date)
        )
        
        entries = result.scalars().all()
        
        if len(entries) < 5:
            return alerts
        
        amounts = [float(entry.total_debit) for entry in entries]
        
        # Check for arithmetic sequence (sequential pattern)
        if len(amounts) >= 5:
            diffs = [amounts[i + 1] - amounts[i] for i in range(len(amounts) - 1)]
            
            if diffs:
                mean_diff = statistics.mean(diffs)
                variance = statistics.variance(diffs) if len(diffs) > 1 else 0
                
                # Low variance in differences suggests sequential pattern
                if mean_diff != 0 and variance / (abs(mean_diff) ** 2) < 0.01:
                    alerts.append(AnomalyAlert(
                        anomaly_type=AnomalyType.SEQUENTIAL_PATTERN,
                        severity=SeverityLevel.HIGH,
                        title="Sequential Pattern Detected",
                        description="Transaction amounts show a suspicious sequential pattern",
                        source_model="journal_entry",
                        source_id=entries[-1].id,
                        detected_value=Decimal(str(amounts[-1])),
                        expected_value=None,
                        deviation_percent=0,
                        detection_method=DetectionMethod.PATTERN_MATCHING,
                        confidence=0.8,
                        recommendation="Investigate potential manipulation. "
                                      "Transaction amounts appear to follow an artificial sequence.",
                        metadata={
                            "recent_amounts": amounts[-10:],
                            "average_difference": mean_diff,
                            "variance": variance
                        }
                    ))
        
        return alerts
    
    def _calculate_entry_similarity(self, entry1: JournalEntry, entry2: JournalEntry) -> float:
        """Calculate similarity between two journal entries."""
        scores = []
        
        # Date similarity (within 7 days is similar)
        date_diff = abs((entry1.date - entry2.date).days)
        date_score = max(0, 1 - date_diff / 7)
        scores.append(date_score)
        
        # Amount similarity
        amount1 = float(entry1.total_debit)
        amount2 = float(entry2.total_debit)
        
        if max(amount1, amount2) > 0:
            amount_score = 1 - abs(amount1 - amount2) / max(amount1, amount2)
        else:
            amount_score = 1.0
        scores.append(amount_score)
        
        # Description similarity
        if entry1.description and entry2.description:
            desc_score = StatisticalAnalyzer.string_similarity(entry1.description, entry2.description)
            scores.append(desc_score)
        
        # Reference similarity
        if entry1.ref and entry2.ref:
            ref_score = StatisticalAnalyzer.string_similarity(entry1.ref, entry2.ref)
            scores.append(ref_score)
        
        return statistics.mean(scores) if scores else 0.0


# ========================================
# Inventory Anomaly Detector
# ========================================

class InventoryAnomalyDetector:
    """
    Detects anomalies in inventory data.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._analyzer = StatisticalAnalyzer()
    
    async def detect_sudden_stock_changes(
        self,
        tenant_id: UUID,
        days: int = 30
    ) -> List[AnomalyAlert]:
        """Detect sudden unexpected changes in stock levels."""
        alerts = []
        
        start_date = date.today() - timedelta(days=days)
        
        # Get stock movements
        result = await self.db.execute(
            select(StockMove)
            .where(
                StockMove.tenant_id == tenant_id,
                StockMove.state == "done",
                StockMove.date >= start_date
            )
            .order_by(StockMove.product_id, StockMove.date)
        )
        
        moves = result.scalars().all()
        
        # Group by product
        product_moves = defaultdict(list)
        for move in moves:
            product_moves[move.product_id].append(move)
        
        for product_id, move_list in product_moves.items():
            if len(move_list) < 5:
                continue
            
            # Get quantities
            quantities = [float(move.quantity) for move in move_list]
            
            # Calculate statistics
            mean_qty = statistics.mean(quantities)
            std_qty = statistics.stdev(quantities) if len(quantities) > 1 else 0
            median_qty, mad = StatisticalAnalyzer.calculate_mad(quantities)
            
            # Get product info
            product = await self.db.get(Product, product_id)
            product_name = product.name if product else str(product_id)
            
            for move in move_list:
                qty = float(move.quantity)
                
                # Check for unusual quantity
                z_score = StatisticalAnalyzer.z_score(qty, mean_qty, std_qty) if std_qty > 0 else 0
                mod_z_score = StatisticalAnalyzer.modified_z_score(qty, median_qty, mad) if mad > 0 else 0
                
                if abs(z_score) > 3 or abs(mod_z_score) > 3.5:
                    deviation = abs(qty - mean_qty) / mean_qty * 100 if mean_qty != 0 else 0
                    
                    alerts.append(AnomalyAlert(
                        anomaly_type=AnomalyType.SUDDEN_STOCK_CHANGE,
                        severity=SeverityLevel.HIGH if abs(z_score) > 4 else SeverityLevel.MEDIUM,
                        title=f"Unusual Stock Movement for {product_name}",
                        description=f"Stock movement of {qty} units is unusual for {product_name}. "
                                   f"Average: {mean_qty:.1f} units",
                        source_model="stock_move",
                        source_id=move.id,
                        detected_value=Decimal(str(qty)),
                        expected_value=Decimal(str(mean_qty)),
                        deviation_percent=deviation,
                        detection_method=DetectionMethod.MAD if abs(mod_z_score) > abs(z_score) else DetectionMethod.Z_SCORE,
                        confidence=min(1.0, max(abs(z_score), abs(mod_z_score)) / 5),
                        recommendation=f"Verify stock movement for {product_name}. "
                                      f"Z-score: {z_score:.2f}, Modified Z-score: {mod_z_score:.2f}",
                        metadata={
                            "product_name": product_name,
                            "z_score": z_score,
                            "modified_z_score": mod_z_score,
                            "average_quantity": mean_qty,
                            "move_type": move.move_type
                        }
                    ))
        
        return alerts
    
    async def detect_negative_stock(
        self,
        tenant_id: UUID
    ) -> List[AnomalyAlert]:
        """Detect products with negative stock levels."""
        alerts = []
        
        # Get products with negative stock
        result = await self.db.execute(
            select(Product)
            .where(
                Product.tenant_id == tenant_id,
                Product.is_deleted == False,
                Product.quantity_on_hand < 0
            )
        )
        
        products = result.scalars().all()
        
        for product in products:
            alerts.append(AnomalyAlert(
                anomaly_type=AnomalyType.NEGATIVE_STOCK,
                severity=SeverityLevel.CRITICAL,
                title=f"Negative Stock: {product.name}",
                description=f"Product {product.name} has negative stock: {product.quantity_on_hand}",
                source_model="product",
                source_id=product.id,
                detected_value=product.quantity_on_hand,
                expected_value=Decimal("0"),
                deviation_percent=100,
                detection_method=DetectionMethod.STATISTICAL_RULE,
                confidence=1.0,
                recommendation=f"Immediately investigate negative stock for {product.name}. "
                              "This may indicate data entry errors or missing transactions.",
                metadata={
                    "product_name": product.name,
                    "sku": product.sku,
                    "quantity_on_hand": float(product.quantity_on_hand)
                }
            ))
        
        return alerts
    
    async def detect_unusual_sales_patterns(
        self,
        tenant_id: UUID,
        days: int = 30
    ) -> List[AnomalyAlert]:
        """Detect unusual sales patterns."""
        alerts = []
        
        start_date = date.today() - timedelta(days=days)
        
        # Get sales by product
        result = await self.db.execute(
            select(
                SaleOrderLine.product_id,
                func.sum(SaleOrderLine.quantity).label("total_qty"),
                func.count(SaleOrderLine.id).label("line_count")
            )
            .join(SaleOrder)
            .where(
                SaleOrder.tenant_id == tenant_id,
                SaleOrder.state.in_(["confirmed", "done"]),
                SaleOrder.date_order >= start_date,
                SaleOrderLine.product_id.isnot(None)
            )
            .group_by(SaleOrderLine.product_id)
        )
        
        product_sales = result.all()
        
        if len(product_sales) < 5:
            return alerts
        
        # Calculate statistics
        quantities = [float(row.total_qty) for row in product_sales]
        mean_qty = statistics.mean(quantities)
        std_qty = statistics.stdev(quantities) if len(quantities) > 1 else 0
        
        for row in product_sales:
            product_id = row.product_id
            total_qty = float(row.total_qty)
            
            # Check for unusual sales volume
            if std_qty > 0:
                z_score = (total_qty - mean_qty) / std_qty
                
                # Very high sales
                if z_score > 3:
                    product = await self.db.get(Product, product_id)
                    product_name = product.name if product else str(product_id)
                    
                    alerts.append(AnomalyAlert(
                        anomaly_type=AnomalyType.UNUSUAL_SALES_PATTERN,
                        severity=SeverityLevel.MEDIUM,
                        title=f"Unusually High Sales: {product_name}",
                        description=f"Product {product_name} has unusually high sales volume: "
                                   f"{total_qty:.0f} units (average: {mean_qty:.0f})",
                        source_model="sale_order_line",
                        source_id=None,
                        detected_value=Decimal(str(total_qty)),
                        expected_value=Decimal(str(mean_qty)),
                        deviation_percent=(total_qty - mean_qty) / mean_qty * 100 if mean_qty > 0 else 0,
                        detection_method=DetectionMethod.Z_SCORE,
                        confidence=min(1.0, z_score / 4),
                        recommendation="Review if high sales are legitimate or if there are data issues.",
                        metadata={
                            "product_name": product_name,
                            "total_quantity": total_qty,
                            "average_quantity": mean_qty,
                            "z_score": z_score
                        }
                    ))
                
                # Very low sales (dead stock indicator)
                elif z_score < -2 and total_qty == 0:
                    product = await self.db.get(Product, product_id)
                    if product:
                        alerts.append(AnomalyAlert(
                            anomaly_type=AnomalyType.DEAD_STOCK,
                            severity=SeverityLevel.LOW,
                            title=f"No Sales Activity: {product.name}",
                            description=f"Product {product.name} has had no sales in the last {days} days "
                                       f"despite having stock: {product.quantity_on_hand}",
                            source_model="product",
                            source_id=product.id,
                            detected_value=Decimal("0"),
                            expected_value=Decimal(str(mean_qty)),
                            deviation_percent=100,
                            detection_method=DetectionMethod.STATISTICAL_RULE,
                            confidence=0.7,
                            recommendation="Consider running promotions or reviewing pricing for slow-moving stock.",
                            metadata={
                                "product_name": product.name,
                                "current_stock": float(product.quantity_on_hand),
                                "average_sales": mean_qty
                            }
                        ))
        
        return alerts
    
    async def detect_stockout_risks(
        self,
        tenant_id: UUID
    ) -> List[AnomalyAlert]:
        """Detect products at risk of stockout."""
        alerts = []
        
        # Get products below reorder point
        result = await self.db.execute(
            select(Product)
            .where(
                Product.tenant_id == tenant_id,
                Product.is_deleted == False,
                Product.quantity_on_hand <= Product.reorder_point
            )
        )
        
        products = result.scalars().all()
        
        for product in products:
            # Calculate days of stock remaining
            # (simplified - should use average daily sales)
            days_remaining = 0
            if product.quantity_on_hand > 0:
                # Estimate based on last 30 days sales
                start_date = date.today() - timedelta(days=30)
                
                sales_result = await self.db.execute(
                    select(func.sum(SaleOrderLine.quantity))
                    .join(SaleOrder)
                    .where(
                        SaleOrderLine.product_id == product.id,
                        SaleOrder.state.in_(["confirmed", "done"]),
                        SaleOrder.date_order >= start_date
                    )
                )
                
                total_sold = sales_result.scalar() or 0
                daily_avg = float(total_sold) / 30 if total_sold else 0
                
                if daily_avg > 0:
                    days_remaining = float(product.quantity_on_hand) / daily_avg
            
            severity = SeverityLevel.CRITICAL if product.quantity_on_hand <= 0 else (
                SeverityLevel.HIGH if days_remaining < 7 else SeverityLevel.MEDIUM
            )
            
            alerts.append(AnomalyAlert(
                anomaly_type=AnomalyType.STOCKOUT_RISK,
                severity=severity,
                title=f"Stockout Risk: {product.name}",
                description=f"Product {product.name} is below reorder point. "
                           f"Current stock: {product.quantity_on_hand}, "
                           f"Reorder point: {product.reorder_point}, "
                           f"Est. days remaining: {days_remaining:.0f}",
                source_model="product",
                source_id=product.id,
                detected_value=product.quantity_on_hand,
                expected_value=product.reorder_point,
                deviation_percent=abs(float(product.quantity_on_hand - product.reorder_point) / 
                                     float(product.reorder_point) * 100) if product.reorder_point else 0,
                detection_method=DetectionMethod.STATISTICAL_RULE,
                confidence=0.9,
                recommendation=f"Reorder {product.name} immediately. "
                              f"Suggested quantity: {float(product.reorder_point - product.quantity_on_hand + product.reorder_point):.0f}",
                metadata={
                    "product_name": product.name,
                    "sku": product.sku,
                    "current_stock": float(product.quantity_on_hand),
                    "reorder_point": float(product.reorder_point),
                    "days_remaining": days_remaining
                }
            ))
        
        return alerts


# ========================================
# Main Anomaly Service
# ========================================

class AnomalyService:
    """
    Main Anomaly Detection Service
    
    Coordinates financial and inventory anomaly detection.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._financial_detector = FinancialAnomalyDetector(db)
        self._inventory_detector = InventoryAnomalyDetector(db)
        
        # Caching
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5 minutes
        
        # Rate limiting
        self._tenant_requests: Dict[UUID, List[float]] = {}
        self._rate_limit = 50  # requests per hour
    
    async def detect_all_anomalies(
        self,
        tenant_id: UUID,
        days: int = 30,
        include_financial: bool = True,
        include_inventory: bool = True
    ) -> List[AnomalyAlert]:
        """
        Run all anomaly detection checks.
        
        Args:
            tenant_id: Tenant UUID
            days: Number of days to analyze
            include_financial: Whether to include financial anomalies
            include_inventory: Whether to include inventory anomalies
            
        Returns:
            List of detected anomalies
        """
        # Check rate limit
        if not self._check_rate_limit(tenant_id):
            raise ValueError("Rate limit exceeded")
        
        all_alerts = []
        
        if include_financial:
            # Financial anomalies
            all_alerts.extend(await self._financial_detector.detect_unusual_amounts(tenant_id, days))
            all_alerts.extend(await self._financial_detector.detect_duplicate_entries(tenant_id, days))
            all_alerts.extend(await self._financial_detector.detect_round_number_fraud(tenant_id, days))
            all_alerts.extend(await self._financial_detector.detect_timing_anomalies(tenant_id, days))
            all_alerts.extend(await self._financial_detector.detect_sequential_patterns(tenant_id, days))
        
        if include_inventory:
            # Inventory anomalies
            all_alerts.extend(await self._inventory_detector.detect_sudden_stock_changes(tenant_id, days))
            all_alerts.extend(await self._inventory_detector.detect_negative_stock(tenant_id))
            all_alerts.extend(await self._inventory_detector.detect_unusual_sales_patterns(tenant_id, days))
            all_alerts.extend(await self._inventory_detector.detect_stockout_risks(tenant_id))
        
        # Sort by severity
        severity_order = {
            SeverityLevel.CRITICAL: 0,
            SeverityLevel.HIGH: 1,
            SeverityLevel.MEDIUM: 2,
            SeverityLevel.LOW: 3
        }
        all_alerts.sort(key=lambda x: severity_order.get(x.severity, 4))
        
        # Store anomalies in database
        for alert in all_alerts:
            await self._store_anomaly(alert, tenant_id)
        
        return all_alerts
    
    async def detect_financial_anomalies(
        self,
        tenant_id: UUID,
        days: int = 30,
        anomaly_types: Optional[List[AnomalyType]] = None
    ) -> List[AnomalyAlert]:
        """Detect only financial anomalies."""
        alerts = []
        
        if not anomaly_types or AnomalyType.UNUSUAL_AMOUNT in anomaly_types:
            alerts.extend(await self._financial_detector.detect_unusual_amounts(tenant_id, days))
        
        if not anomaly_types or AnomalyType.DUPLICATE_ENTRY in anomaly_types:
            alerts.extend(await self._financial_detector.detect_duplicate_entries(tenant_id, days))
        
        if not anomaly_types or AnomalyType.ROUND_NUMBER in anomaly_types:
            alerts.extend(await self._financial_detector.detect_round_number_fraud(tenant_id, days))
        
        if not anomaly_types or AnomalyType.TIMING_ANOMALY in anomaly_types:
            alerts.extend(await self._financial_detector.detect_timing_anomalies(tenant_id, days))
        
        if not anomaly_types or AnomalyType.SEQUENTIAL_PATTERN in anomaly_types:
            alerts.extend(await self._financial_detector.detect_sequential_patterns(tenant_id, days))
        
        return alerts
    
    async def detect_inventory_anomalies(
        self,
        tenant_id: UUID,
        days: int = 30,
        anomaly_types: Optional[List[AnomalyType]] = None
    ) -> List[AnomalyAlert]:
        """Detect only inventory anomalies."""
        alerts = []
        
        if not anomaly_types or AnomalyType.SUDDEN_STOCK_CHANGE in anomaly_types:
            alerts.extend(await self._inventory_detector.detect_sudden_stock_changes(tenant_id, days))
        
        if not anomaly_types or AnomalyType.NEGATIVE_STOCK in anomaly_types:
            alerts.extend(await self._inventory_detector.detect_negative_stock(tenant_id))
        
        if not anomaly_types or AnomalyType.UNUSUAL_SALES_PATTERN in anomaly_types:
            alerts.extend(await self._inventory_detector.detect_unusual_sales_patterns(tenant_id, days))
        
        if not anomaly_types or AnomalyType.STOCKOUT_RISK in anomaly_types:
            alerts.extend(await self._inventory_detector.detect_stockout_risks(tenant_id))
        
        return alerts
    
    async def get_anomaly_statistics(
        self,
        tenant_id: UUID,
        days: int = 30
    ) -> AnomalyStatistics:
        """Get statistics about detected anomalies."""
        start_date = date.today() - timedelta(days=days)
        
        # Get stored anomalies
        result = await self.db.execute(
            select(AnomalyDetection)
            .where(
                AnomalyDetection.tenant_id == tenant_id,
                AnomalyDetection.created_at >= start_date
            )
        )
        
        anomalies = result.scalars().all()
        
        # Get total analyzed transactions
        tx_result = await self.db.execute(
            select(func.count(JournalEntry.id))
            .where(
                JournalEntry.tenant_id == tenant_id,
                JournalEntry.date >= start_date
            )
        )
        total_transactions = tx_result.scalar() or 0
        
        # Calculate statistics
        anomalies_by_type = defaultdict(int)
        anomalies_by_severity = defaultdict(int)
        deviations = []
        
        for anomaly in anomalies:
            anomalies_by_type[anomaly.anomaly_type] += 1
            anomalies_by_severity[anomaly.severity] += 1
            deviations.append(anomaly.deviation_percent)
        
        return AnomalyStatistics(
            total_analyzed=total_transactions,
            total_anomalies=len(anomalies),
            anomalies_by_type=dict(anomalies_by_type),
            anomalies_by_severity=dict(anomalies_by_severity),
            avg_deviation=statistics.mean(deviations) if deviations else 0.0,
            detection_rate=len(anomalies) / total_transactions if total_transactions > 0 else 0.0
        )
    
    async def get_anomaly_details(
        self,
        anomaly_id: UUID,
        tenant_id: UUID
    ) -> Optional[AnomalyDetection]:
        """Get details of a specific anomaly."""
        result = await self.db.execute(
            select(AnomalyDetection)
            .where(
                AnomalyDetection.id == anomaly_id,
                AnomalyDetection.tenant_id == tenant_id
            )
        )
        return result.scalar_one_or_none()
    
    async def acknowledge_anomaly(
        self,
        anomaly_id: UUID,
        user_id: UUID,
        notes: Optional[str] = None
    ) -> AnomalyDetection:
        """Acknowledge an anomaly."""
        anomaly = await self.db.get(AnomalyDetection, anomaly_id)
        
        if not anomaly:
            raise ValueError("Anomaly not found")
        
        anomaly.status = "acknowledged"
        anomaly.acknowledged_by_id = user_id
        anomaly.acknowledged_at = datetime.now()
        
        if notes:
            anomaly.resolution_notes = notes
        
        await self.db.commit()
        await self.db.refresh(anomaly)
        
        return anomaly
    
    async def resolve_anomaly(
        self,
        anomaly_id: UUID,
        user_id: UUID,
        resolution: str
    ) -> AnomalyDetection:
        """Resolve an anomaly."""
        anomaly = await self.db.get(AnomalyDetection, anomaly_id)
        
        if not anomaly:
            raise ValueError("Anomaly not found")
        
        anomaly.status = "resolved"
        anomaly.acknowledged_by_id = user_id
        anomaly.acknowledged_at = datetime.now()
        anomaly.resolution_notes = resolution
        
        await self.db.commit()
        await self.db.refresh(anomaly)
        
        return anomaly
    
    async def dismiss_anomaly(
        self,
        anomaly_id: UUID,
        user_id: UUID,
        reason: str
    ) -> AnomalyDetection:
        """Dismiss an anomaly as false positive."""
        anomaly = await self.db.get(AnomalyDetection, anomaly_id)
        
        if not anomaly:
            raise ValueError("Anomaly not found")
        
        anomaly.status = "dismissed"
        anomaly.acknowledged_by_id = user_id
        anomaly.acknowledged_at = datetime.now()
        anomaly.resolution_notes = f"Dismissed: {reason}"
        
        await self.db.commit()
        await self.db.refresh(anomaly)
        
        return anomaly
    
    async def _store_anomaly(
        self,
        alert: AnomalyAlert,
        tenant_id: UUID
    ) -> AnomalyDetection:
        """Store an anomaly in the database."""
        anomaly = AnomalyDetection(
            tenant_id=tenant_id,
            anomaly_type=alert.anomaly_type.value,
            severity=alert.severity.value,
            source_model=alert.source_model,
            source_id=alert.source_id,
            detected_value=alert.detected_value,
            expected_value=alert.expected_value or Decimal("0"),
            deviation_percent=alert.deviation_percent,
            description=alert.description,
            recommendation=alert.recommendation,
            confidence_score=alert.confidence,
            detection_model=alert.detection_method.value,
            status="new"
        )
        
        self.db.add(anomaly)
        await self.db.commit()
        await self.db.refresh(anomaly)
        
        return anomaly
    
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
    
    async def calculate_risk_score(
        self,
        entity_type: str,
        entity_id: UUID,
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """
        Calculate a risk score for an entity.
        
        Returns risk score (0-100) and breakdown by factors.
        """
        if entity_type == "journal_entry":
            return await self._calculate_journal_entry_risk(entity_id, tenant_id)
        elif entity_type == "product":
            return await self._calculate_product_risk(entity_id, tenant_id)
        else:
            return {"error": "Unknown entity type"}
    
    async def _calculate_journal_entry_risk(
        self,
        entry_id: UUID,
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """Calculate risk score for a journal entry."""
        entry = await self.db.get(JournalEntry, entry_id)
        
        if not entry or entry.tenant_id != tenant_id:
            return {"error": "Entry not found"}
        
        risk_factors = []
        total_score = 0
        
        # Factor 1: Amount unusualness
        result = await self.db.execute(
            select(
                func.avg(JournalEntry.total_debit).label("avg"),
                func.stddev(JournalEntry.total_debit).label("std")
            )
            .where(
                JournalEntry.tenant_id == tenant_id,
                JournalEntry.state == "posted"
            )
        )
        row = result.one()
        mean_amount = float(row.avg or 0)
        std_amount = float(row.std or 0)
        
        if std_amount > 0:
            z_score = abs((float(entry.total_debit) - mean_amount) / std_amount)
            amount_risk = min(25, z_score * 5)
            risk_factors.append({
                "factor": "amount_deviation",
                "score": amount_risk,
                "z_score": z_score,
                "description": f"Amount is {z_score:.1f} standard deviations from mean"
            })
            total_score += amount_risk
        
        # Factor 2: Timing
        if entry.date.weekday() >= 5:
            risk_factors.append({
                "factor": "weekend_transaction",
                "score": 10,
                "description": "Transaction recorded on weekend"
            })
            total_score += 10
        
        # Factor 3: Round number
        if StatisticalAnalyzer.is_round_number(float(entry.total_debit)):
            risk_factors.append({
                "factor": "round_number",
                "score": 5,
                "description": "Amount is a suspiciously round number"
            })
            total_score += 5
        
        # Factor 4: Missing reference
        if not entry.ref and not entry.description:
            risk_factors.append({
                "factor": "missing_reference",
                "score": 10,
                "description": "Entry has no reference or description"
            })
            total_score += 10
        
        # Factor 5: High value
        if mean_amount > 0 and float(entry.total_debit) > mean_amount * 3:
            risk_factors.append({
                "factor": "high_value",
                "score": 15,
                "description": f"Amount is more than 3x average ({mean_amount:,.2f})"
            })
            total_score += 15
        
        # Cap at 100
        total_score = min(100, total_score)
        
        # Determine risk level
        if total_score >= 70:
            risk_level = SeverityLevel.CRITICAL
        elif total_score >= 50:
            risk_level = SeverityLevel.HIGH
        elif total_score >= 30:
            risk_level = SeverityLevel.MEDIUM
        else:
            risk_level = SeverityLevel.LOW
        
        return {
            "entry_id": str(entry_id),
            "entry_number": entry.number,
            "risk_score": total_score,
            "risk_level": risk_level.value,
            "risk_factors": risk_factors,
            "recommendation": self._get_risk_recommendation(total_score)
        }
    
    async def _calculate_product_risk(
        self,
        product_id: UUID,
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """Calculate risk score for a product."""
        product = await self.db.get(Product, product_id)
        
        if not product or product.tenant_id != tenant_id:
            return {"error": "Product not found"}
        
        risk_factors = []
        total_score = 0
        
        # Factor 1: Stock level
        if product.quantity_on_hand < 0:
            risk_factors.append({
                "factor": "negative_stock",
                "score": 30,
                "description": "Product has negative stock"
            })
            total_score += 30
        elif product.quantity_on_hand <= product.reorder_point:
            risk_factors.append({
                "factor": "below_reorder_point",
                "score": 20,
                "description": "Stock is below reorder point"
            })
            total_score += 20
        
        # Factor 2: No recent sales (dead stock)
        start_date = date.today() - timedelta(days=90)
        result = await self.db.execute(
            select(func.sum(SaleOrderLine.quantity))
            .join(SaleOrder)
            .where(
                SaleOrderLine.product_id == product_id,
                SaleOrder.state.in_(["confirmed", "done"]),
                SaleOrder.date_order >= start_date
            )
        )
        recent_sales = result.scalar() or 0
        
        if recent_sales == 0 and product.quantity_on_hand > 0:
            risk_factors.append({
                "factor": "no_recent_sales",
                "score": 15,
                "description": "No sales in the last 90 days"
            })
            total_score += 15
        
        total_score = min(100, total_score)
        
        if total_score >= 50:
            risk_level = SeverityLevel.HIGH
        elif total_score >= 25:
            risk_level = SeverityLevel.MEDIUM
        else:
            risk_level = SeverityLevel.LOW
        
        return {
            "product_id": str(product_id),
            "product_name": product.name,
            "risk_score": total_score,
            "risk_level": risk_level.value,
            "risk_factors": risk_factors
        }
    
    def _get_risk_recommendation(self, score: int) -> str:
        """Get recommendation based on risk score."""
        if score >= 70:
            return "CRITICAL: Immediate review required. Consider holding transaction until verified."
        elif score >= 50:
            return "HIGH RISK: Detailed review recommended within 24 hours."
        elif score >= 30:
            return "MEDIUM RISK: Standard review recommended."
        else:
            return "LOW RISK: No immediate action required."
