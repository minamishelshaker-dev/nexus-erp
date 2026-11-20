"""
Nexus ERP - Financial Anomaly Detection Service
================================================

AI-powered anomaly detection for financial transactions.
Detects unusual patterns, potential fraud, and data entry errors.

Features:
- Statistical analysis of transactions
- Duplicate detection
- Unusual amount detection
- Timing anomaly detection
- Risk scoring
- Alert generation
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
from collections import defaultdict

from app.models.ai import AnomalyDetection
from app.models.accounting import JournalEntry, JournalItem, Account, AccountType
from app.services.ai.core import AIEngine, AIContext, AIResult, get_ai_engine, ai_task, AITaskType
from app.services.ai.llm_provider import LLMConfig

logger = logging.getLogger(__name__)


# ========================================
# Enums and Data Classes
# ========================================

class AnomalyType(str, Enum):
    """Types of financial anomalies."""
    DUPLICATE_ENTRY = "duplicate_entry"
    UNUSUAL_AMOUNT = "unusual_amount"
    UNUSUAL_TIMING = "unusual_timing"
    UNUSUAL_ACCOUNT = "unusual_account"
    UNBALANCED_ENTRY = "unbalanced_entry"
    ROUND_NUMBER = "round_number"
    SEQUENTIAL_PATTERN = "sequential_pattern"
    MISSING_REFERENCE = "missing_reference"
    UNUSUAL_PARTNER = "unusual_partner"
    THRESHOLD_BREACH = "threshold_breach"


class RiskLevel(str, Enum):
    """Risk levels for anomalies."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AnomalyAlert:
    """Anomaly alert data structure."""
    anomaly_type: AnomalyType
    risk_level: RiskLevel
    description: str
    source_id: UUID
    source_model: str
    detected_value: Decimal
    expected_value: Optional[Decimal]
    deviation_percent: float
    recommendation: str
    confidence: float
    related_entries: List[UUID] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnomalyStats:
    """Statistics for anomaly detection."""
    total_transactions: int
    total_anomalies: int
    anomalies_by_type: Dict[str, int]
    anomalies_by_risk: Dict[str, int]
    avg_deviation: float
    top_risky_accounts: List[Dict[str, Any]]


# ========================================
# Statistical Helpers
# ========================================

class StatisticalAnalyzer:
    """
    Statistical analysis utilities for anomaly detection.
    """
    
    @staticmethod
    def calculate_z_score(value: float, mean: float, std_dev: float) -> float:
        """Calculate Z-score for a value."""
        if std_dev == 0:
            return 0
        return (value - mean) / std_dev
    
    @staticmethod
    def calculate_percentile(value: float, data: List[float]) -> float:
        """Calculate percentile rank of a value in data."""
        if not data:
            return 0
        sorted_data = sorted(data)
        count = sum(1 for x in sorted_data if x <= value)
        return (count / len(sorted_data)) * 100
    
    @staticmethod
    def calculate_iqr_bounds(data: List[float], multiplier: float = 1.5) -> Tuple[float, float]:
        """Calculate IQR-based bounds for outlier detection."""
        if len(data) < 4:
            return (min(data) if data else 0, max(data) if data else 0)
        
        sorted_data = sorted(data)
        q1_idx = int(len(sorted_data) * 0.25)
        q3_idx = int(len(sorted_data) * 0.75)
        
        q1 = sorted_data[q1_idx]
        q3 = sorted_data[q3_idx]
        iqr = q3 - q1
        
        lower_bound = q1 - multiplier * iqr
        upper_bound = q3 + multiplier * iqr
        
        return (lower_bound, upper_bound)
    
    @staticmethod
    def detect_sequential_pattern(numbers: List[float], tolerance: float = 0.01) -> bool:
        """Detect if numbers follow a sequential pattern (potential fraud)."""
        if len(numbers) < 3:
            return False
        
        # Check for arithmetic sequence
        diffs = [numbers[i+1] - numbers[i] for i in range(len(numbers)-1)]
        avg_diff = statistics.mean(diffs)
        
        # Check if differences are consistent
        variance = statistics.variance(diffs) if len(diffs) > 1 else 0
        return variance < (avg_diff * tolerance)
    
    @staticmethod
    def is_round_number(value: float, threshold: float = 0.01) -> bool:
        """Check if value is suspiciously round (e.g., 1000, 5000)."""
        if value == 0:
            return False
        
        # Check if value is close to common round numbers
        round_numbers = [10, 50, 100, 500, 1000, 5000, 10000, 50000, 100000]
        
        for rn in round_numbers:
            if abs(value % rn) < threshold * rn:
                return True
            if abs((rn - (value % rn)) % rn) < threshold * rn:
                return True
        
        return False
    
    @staticmethod
    def calculate_string_similarity(s1: str, s2: str) -> float:
        """Calculate similarity between two strings (Levenshtein-based)."""
        if not s1 or not s2:
            return 0.0
        
        s1, s2 = s1.lower(), s2.lower()
        
        if len(s1) < len(s2):
            s1, s2 = s2, s1
        
        if len(s2) == 0:
            return 1.0 if len(s1) == 0 else 0.0
        
        previous_row = range(len(s2) + 1)
        
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return 1 - previous_row[-1] / max(len(s1), len(s2))


# ========================================
# Anomaly Detection Service
# ========================================

class AnomalyDetectionService:
    """
    Financial Anomaly Detection Service
    
    Detects unusual patterns in financial transactions using:
    - Statistical analysis
    - Pattern recognition
    - AI-powered insights
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._analyzer = StatisticalAnalyzer()
        self._ai_engine = get_ai_engine(db)
        
        # Configuration
        self.z_score_threshold = 3.0  # Values beyond 3 standard deviations
        self.duplicate_similarity_threshold = 0.85
        self.round_number_threshold = 0.02
        self.amount_deviation_threshold = 0.5  # 50% deviation
    
    # ========================================
    # Main Detection Methods
    # ========================================
    
    async def detect_all_anomalies(
        self,
        tenant_id: UUID,
        days: int = 30,
        include_dismissed: bool = False
    ) -> List[AnomalyAlert]:
        """
        Run all anomaly detection checks.
        
        Args:
            tenant_id: Tenant UUID
            days: Number of days to analyze
            include_dismissed: Include previously dismissed anomalies
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        # Run all detection methods
        anomalies.extend(await self.detect_duplicate_entries(tenant_id, days))
        anomalies.extend(await self.detect_unusual_amounts(tenant_id, days))
        anomalies.extend(await self.detect_timing_anomalies(tenant_id, days))
        anomalies.extend(await self.detect_round_numbers(tenant_id, days))
        anomalies.extend(await self.detect_unusual_patterns(tenant_id, days))
        
        # Sort by risk level
        risk_order = {RiskLevel.CRITICAL: 0, RiskLevel.HIGH: 1, RiskLevel.MEDIUM: 2, RiskLevel.LOW: 3}
        anomalies.sort(key=lambda x: risk_order.get(x.risk_level, 4))
        
        return anomalies
    
    @ai_task(AITaskType.ANOMALY_DETECTION)
    async def detect_duplicate_entries(
        self,
        tenant_id: UUID,
        days: int = 30
    ) -> List[AnomalyAlert]:
        """
        Detect potential duplicate journal entries.
        
        Checks for:
        - Same amount, date, and account
        - Similar descriptions
        - Same reference numbers
        """
        alerts = []
        
        start_date = date.today() - timedelta(days=days)
        
        # Get recent journal entries
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
        
        # Group by amount (potential duplicates will have same amount)
        amount_groups = defaultdict(list)
        for entry in entries:
            key = float(entry.total_debit)
            amount_groups[key].append(entry)
        
        # Check groups with multiple entries
        for amount, group in amount_groups.items():
            if len(group) < 2:
                continue
            
            for i, entry1 in enumerate(group):
                for entry2 in group[i+1:]:
                    # Check similarity
                    similarity = self._calculate_entry_similarity(entry1, entry2)
                    
                    if similarity > self.duplicate_similarity_threshold:
                        alerts.append(AnomalyAlert(
                            anomaly_type=AnomalyType.DUPLICATE_ENTRY,
                            risk_level=RiskLevel.HIGH,
                            description=f"Potential duplicate entries: {entry1.number} and {entry2.number}",
                            source_id=entry1.id,
                            source_model="journal_entry",
                            detected_value=entry1.total_debit,
                            expected_value=None,
                            deviation_percent=(1 - similarity) * 100,
                            recommendation=f"Review entries {entry1.number} and {entry2.number} for potential duplication. Consider reversing one entry.",
                            confidence=similarity,
                            related_entries=[entry2.id],
                            metadata={
                                "entry1_number": entry1.number,
                                "entry2_number": entry2.number,
                                "entry1_date": entry1.date.isoformat(),
                                "entry2_date": entry2.date.isoformat()
                            }
                        ))
        
        return alerts
    
    @ai_task(AITaskType.ANOMALY_DETECTION)
    async def detect_unusual_amounts(
        self,
        tenant_id: UUID,
        days: int = 30
    ) -> List[AnomalyAlert]:
        """
        Detect transactions with unusual amounts.
        
        Uses statistical analysis to find outliers.
        """
        alerts = []
        
        start_date = date.today() - timedelta(days=days)
        
        # Get journal items with amounts
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
        
        # Analyze each account
        for account_id, account_items_list in account_items.items():
            if len(account_items_list) < 5:
                continue  # Need enough data for statistical analysis
            
            amounts = [float(item.debit or item.credit) for item in account_items_list]
            mean = statistics.mean(amounts)
            std_dev = statistics.stdev(amounts) if len(amounts) > 1 else 0
            
            # Get bounds using IQR method
            lower_bound, upper_bound = StatisticalAnalyzer.calculate_iqr_bounds(amounts)
            
            for item in account_items_list:
                amount = float(item.debit or item.credit)
                
                # Check Z-score
                z_score = StatisticalAnalyzer.calculate_z_score(amount, mean, std_dev)
                
                if abs(z_score) > self.z_score_threshold:
                    # Get account info
                    account = await self.db.get(Account, account_id)
                    
                    deviation = ((amount - mean) / mean * 100) if mean != 0 else 0
                    
                    alerts.append(AnomalyAlert(
                        anomaly_type=AnomalyType.UNUSUAL_AMOUNT,
                        risk_level=RiskLevel.HIGH if abs(z_score) > 4 else RiskLevel.MEDIUM,
                        description=f"Unusual amount in account {account.name if account else account_id}: {amount:.2f}",
                        source_id=item.id,
                        source_model="journal_item",
                        detected_value=Decimal(str(amount)),
                        expected_value=Decimal(str(mean)),
                        deviation_percent=abs(deviation),
                        recommendation=f"Review transaction for accuracy. Expected range: {lower_bound:.2f} to {upper_bound:.2f}",
                        confidence=min(1.0, abs(z_score) / 5),
                        metadata={
                            "z_score": z_score,
                            "mean": mean,
                            "std_dev": std_dev,
                            "account_name": account.name if account else None
                        }
                    ))
        
        return alerts
    
    @ai_task(AITaskType.ANOMALY_DETECTION)
    async def detect_timing_anomalies(
        self,
        tenant_id: UUID,
        days: int = 30
    ) -> List[AnomalyAlert]:
        """
        Detect unusual timing patterns in transactions.
        
        Looks for:
        - Transactions outside business hours
        - Weekend transactions
        - Unusual clustering
        """
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
                    anomaly_type=AnomalyType.UNUSUAL_TIMING,
                    risk_level=RiskLevel.LOW,
                    description=f"Weekend transaction: {entry.number} on {entry.date.strftime('%A')}",
                    source_id=entry.id,
                    source_model="journal_entry",
                    detected_value=entry.total_debit,
                    expected_value=None,
                    deviation_percent=0,
                    recommendation="Verify this weekend transaction was intentional.",
                    confidence=0.7,
                    metadata={
                        "day_of_week": entry.date.strftime('%A'),
                        "date": entry.date.isoformat()
                    }
                ))
        
        # Check for unusual clustering (many transactions on same day)
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
                            anomaly_type=AnomalyType.UNUSUAL_TIMING,
                            risk_level=RiskLevel.MEDIUM,
                            description=f"Unusual transaction clustering on {entry_date}: {count} transactions",
                            source_id=UUID(int=0),  # No specific entry
                            source_model="journal_entry",
                            detected_value=Decimal(str(count)),
                            expected_value=Decimal(str(mean_count)),
                            deviation_percent=((count - mean_count) / mean_count * 100) if mean_count else 0,
                            recommendation=f"Review transactions on {entry_date} for potential errors or fraud.",
                            confidence=min(1.0, z_score / 4),
                            metadata={
                                "date": entry_date.isoformat(),
                                "count": count,
                                "average_count": mean_count
                            }
                        ))
        
        return alerts
    
    @ai_task(AITaskType.ANOMALY_DETECTION)
    async def detect_round_numbers(
        self,
        tenant_id: UUID,
        days: int = 30
    ) -> List[AnomalyAlert]:
        """
        Detect suspiciously round transaction amounts.
        
        Round numbers may indicate estimation or manipulation.
        """
        alerts = []
        
        start_date = date.today() - timedelta(days=days)
        
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
        
        for item in items:
            amount = float(item.debit or item.credit)
            
            if amount > 0 and StatisticalAnalyzer.is_round_number(amount, self.round_number_threshold):
                alerts.append(AnomalyAlert(
                    anomaly_type=AnomalyType.ROUND_NUMBER,
                    risk_level=RiskLevel.LOW,
                    description=f"Round number transaction: {amount:.2f}",
                    source_id=item.id,
                    source_model="journal_item",
                    detected_value=Decimal(str(amount)),
                    expected_value=None,
                    deviation_percent=0,
                    recommendation="Verify this round amount is accurate. May indicate estimation.",
                    confidence=0.6,
                    metadata={
                        "amount": amount
                    }
                ))
        
        return alerts
    
    @ai_task(AITaskType.ANOMALY_DETECTION)
    async def detect_unusual_patterns(
        self,
        tenant_id: UUID,
        days: int = 30
    ) -> List[AnomalyAlert]:
        """
        Detect unusual patterns using AI analysis.
        
        Uses ML to find complex patterns that simple rules miss.
        """
        alerts = []
        
        start_date = date.today() - timedelta(days=days)
        
        # Get transaction data for AI analysis
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
        
        if len(entries) < 10:
            return alerts
        
        # Prepare data for AI analysis
        transaction_data = []
        amounts = []
        
        for entry in entries:
            entry_data = {
                "number": entry.number,
                "date": entry.date.isoformat(),
                "amount": float(entry.total_debit),
                "move_type": entry.move_type.value if hasattr(entry.move_type, 'value') else str(entry.move_type),
                "line_count": len(entry.lines) if entry.lines else 0,
                "description": entry.description or ""
            }
            transaction_data.append(entry_data)
            amounts.append(float(entry.total_debit))
        
        # Check for sequential patterns
        if StatisticalAnalyzer.detect_sequential_pattern(amounts[-10:]):
            alerts.append(AnomalyAlert(
                anomaly_type=AnomalyType.SEQUENTIAL_PATTERN,
                risk_level=RiskLevel.HIGH,
                description="Sequential pattern detected in recent transaction amounts",
                source_id=entries[-1].id,
                source_model="journal_entry",
                detected_value=Decimal(str(amounts[-1])),
                expected_value=None,
                deviation_percent=0,
                recommendation="Investigate potential manipulation. Transaction amounts show suspicious sequential pattern.",
                confidence=0.8,
                metadata={
                    "recent_amounts": amounts[-10:]
                }
            ))
        
        # Use AI for advanced pattern detection
        context = AIContext(tenant_id=tenant_id, module="accounting")
        
        ai_result = await self._ai_engine.analyze(
            data={"transactions": transaction_data[-50:]},  # Last 50 transactions
            analysis_type="anomaly",
            context=context,
            additional_instructions="""Analyze these financial transactions for:
            1. Unusual patterns or trends
            2. Potential fraud indicators
            3. Data quality issues
            
            Return a JSON object with:
            {
                "anomalies": [
                    {
                        "type": "anomaly_type",
                        "severity": "low|medium|high|critical",
                        "description": "description",
                        "entry_number": "affected_entry",
                        "recommendation": "action to take"
                    }
                ],
                "summary": "overall assessment"
            }"""
        )
        
        if ai_result.success and ai_result.data:
            try:
                ai_anomalies = ai_result.data.get("anomalies", [])
                for anomaly in ai_anomalies:
                    # Find the entry
                    entry_number = anomaly.get("entry_number")
                    entry_id = None
                    for entry in entries:
                        if entry.number == entry_number:
                            entry_id = entry.id
                            break
                    
                    severity = anomaly.get("severity", "medium")
                    risk_level = {
                        "critical": RiskLevel.CRITICAL,
                        "high": RiskLevel.HIGH,
                        "medium": RiskLevel.MEDIUM,
                        "low": RiskLevel.LOW
                    }.get(severity, RiskLevel.MEDIUM)
                    
                    alerts.append(AnomalyAlert(
                        anomaly_type=AnomalyType.UNUSUAL_PATTERN,
                        risk_level=risk_level,
                        description=anomaly.get("description", "AI-detected anomaly"),
                        source_id=entry_id or UUID(int=0),
                        source_model="journal_entry",
                        detected_value=Decimal("0"),
                        expected_value=None,
                        deviation_percent=0,
                        recommendation=anomaly.get("recommendation", "Review this transaction."),
                        confidence=0.7,
                        metadata={
                            "ai_detected": True,
                            "anomaly_type": anomaly.get("type")
                        }
                    ))
            except Exception as e:
                logger.error(f"Failed to process AI anomalies: {e}")
        
        return alerts
    
    # ========================================
    # Risk Scoring
    # ========================================
    
    async def calculate_transaction_risk_score(
        self,
        entry_id: UUID,
        tenant_id: UUID
    ) -> Dict[str, Any]:
        """
        Calculate a risk score for a specific transaction.
        
        Returns risk score (0-100) and breakdown by factors.
        """
        entry = await self.db.get(JournalEntry, entry_id)
        if not entry or entry.tenant_id != tenant_id:
            return {"error": "Entry not found"}
        
        risk_factors = []
        total_score = 0
        
        # Factor 1: Amount unusualness
        result = await self.db.execute(
            select(func.avg(JournalEntry.total_debit), func.stddev(JournalEntry.total_debit))
            .where(
                JournalEntry.tenant_id == tenant_id,
                JournalEntry.state == "posted"
            )
        )
        row = result.one()
        mean_amount = float(row[0] or 0)
        std_amount = float(row[1] or 0)
        
        if std_amount > 0:
            z_score = abs((float(entry.total_debit) - mean_amount) / std_amount)
            amount_risk = min(25, z_score * 5)  # Max 25 points
            risk_factors.append({"factor": "amount_deviation", "score": amount_risk, "z_score": z_score})
            total_score += amount_risk
        
        # Factor 2: Timing
        if entry.date.weekday() >= 5:  # Weekend
            risk_factors.append({"factor": "weekend_transaction", "score": 10})
            total_score += 10
        
        # Factor 3: Round number
        if StatisticalAnalyzer.is_round_number(float(entry.total_debit)):
            risk_factors.append({"factor": "round_number", "score": 5})
            total_score += 5
        
        # Factor 4: Missing reference
        if not entry.ref and not entry.description:
            risk_factors.append({"factor": "missing_reference", "score": 10})
            total_score += 10
        
        # Factor 5: High value transaction
        if float(entry.total_debit) > mean_amount * 3 if mean_amount > 0 else False:
            risk_factors.append({"factor": "high_value", "score": 15})
            total_score += 15
        
        # Cap at 100
        total_score = min(100, total_score)
        
        # Determine risk level
        if total_score >= 70:
            risk_level = RiskLevel.CRITICAL
        elif total_score >= 50:
            risk_level = RiskLevel.HIGH
        elif total_score >= 30:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW
        
        return {
            "entry_id": str(entry_id),
            "entry_number": entry.number,
            "risk_score": total_score,
            "risk_level": risk_level.value,
            "risk_factors": risk_factors,
            "recommendation": self._get_risk_recommendation(total_score)
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
    
    # ========================================
    # Statistics and Reporting
    # ========================================
    
    async def get_anomaly_statistics(
        self,
        tenant_id: UUID,
        days: int = 30
    ) -> AnomalyStats:
        """Get statistics about detected anomalies."""
        
        # Get stored anomalies
        start_date = date.today() - timedelta(days=days)
        
        result = await self.db.execute(
            select(AnomalyDetection)
            .where(
                AnomalyDetection.tenant_id == tenant_id,
                AnomalyDetection.created_at >= start_date
            )
        )
        
        stored_anomalies = result.scalars().all()
        
        # Get total transactions
        tx_result = await self.db.execute(
            select(func.count(JournalEntry.id))
            .where(
                JournalEntry.tenant_id == tenant_id,
                JournalEntry.date >= start_date
            )
        )
        total_transactions = tx_result.scalar() or 0
        
        # Calculate stats
        anomalies_by_type = defaultdict(int)
        anomalies_by_risk = defaultdict(int)
        deviations = []
        
        for anomaly in stored_anomalies:
            anomalies_by_type[anomaly.anomaly_type] += 1
            anomalies_by_risk[anomaly.severity] += 1
            deviations.append(anomaly.deviation_percent)
        
        # Get top risky accounts
        top_accounts_result = await self.db.execute(
            select(
                Account.id,
                Account.name,
                func.count(AnomalyDetection.id).label("anomaly_count")
            )
            .join(AnomalyDetection, AnomalyDetection.source_id == Account.id)
            .where(AnomalyDetection.tenant_id == tenant_id)
            .group_by(Account.id, Account.name)
            .order_by(desc("anomaly_count"))
            .limit(5)
        )
        
        top_accounts = [
            {"id": str(row.id), "name": row.name, "anomaly_count": row.anomaly_count}
            for row in top_accounts_result.all()
        ]
        
        return AnomalyStats(
            total_transactions=total_transactions,
            total_anomalies=len(stored_anomalies),
            anomalies_by_type=dict(anomalies_by_type),
            anomalies_by_risk=dict(anomalies_by_risk),
            avg_deviation=statistics.mean(deviations) if deviations else 0,
            top_risky_accounts=top_accounts
        )
    
    # ========================================
    # Storage and Management
    # ========================================
    
    async def store_anomaly(
        self,
        alert: AnomalyAlert,
        tenant_id: UUID
    ) -> AnomalyDetection:
        """Store an anomaly detection in the database."""
        
        anomaly = AnomalyDetection(
            tenant_id=tenant_id,
            anomaly_type=alert.anomaly_type.value,
            severity=alert.risk_level.value,
            source_model=alert.source_model,
            source_id=alert.source_id,
            detected_value=alert.detected_value,
            expected_value=alert.expected_value or Decimal("0"),
            deviation_percent=alert.deviation_percent,
            description=alert.description,
            recommendation=alert.recommendation,
            confidence_score=alert.confidence,
            status="new"
        )
        
        self.db.add(anomaly)
        await self.db.commit()
        await self.db.refresh(anomaly)
        
        return anomaly
    
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
    
    # ========================================
    # Helper Methods
    # ========================================
    
    def _calculate_entry_similarity(self, entry1: JournalEntry, entry2: JournalEntry) -> float:
        """Calculate similarity between two journal entries."""
        scores = []
        
        # Date similarity (within 3 days is similar)
        date_diff = abs((entry1.date - entry2.date).days)
        date_score = max(0, 1 - date_diff / 7)  # Decay over 7 days
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
            desc_score = StatisticalAnalyzer.calculate_string_similarity(
                entry1.description, entry2.description
            )
            scores.append(desc_score)
        
        # Reference similarity
        if entry1.ref and entry2.ref:
            ref_score = StatisticalAnalyzer.calculate_string_similarity(
                entry1.ref, entry2.ref
            )
            scores.append(ref_score)
        
        return statistics.mean(scores) if scores else 0
