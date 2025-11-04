"""
MongoDB Document Models - Match current results structure
These models reflect the EXACT structure of the current results being generated
"""

from mongoengine import (
    Document, EmbeddedDocument,
    StringField, FloatField, DictField, ListField,
    DateTimeField, IntField, BooleanField, EmbeddedDocumentField
)
from datetime import datetime


# ==================== ML TRAINING RESULTS ====================
# Matches the structure of model_results_[timestamp].json

class ModelMetrics(EmbeddedDocument):
    """
    Embedded document for model performance metrics
    """
    mse = FloatField(required=True)  # Mean Squared Error
    mae = FloatField(required=True)  # Mean Absolute Error
    mape = FloatField(required=True)  # Mean Absolute Percentage Error
    mape_percent = FloatField()       # MAPE as percentage
    objective_achieved = BooleanField(default=False)  # MAPE < 10%


class MLTrainingResult(Document):
    """
    Stores ML model training results
    Matches the structure of model_results_[timestamp].json
    """
    meta = {
        'collection': 'ml_training_results',
        'indexes': [
            'batch_id',
            'category',
            'timestamp',
            ('batch_id', 'category')  # Compound index
        ]
    }

    # Identification
    batch_id = StringField(required=True)  # Format: YYYYMMDD_HHMMSS
    category = StringField(required=True)  # e.g., "Classe_Carnes Vermelhas"

    # Model parameters
    n_lags = IntField(default=4)  # Number of lag features used
    test_size_weeks = IntField(default=12)  # Test size in weeks
    frequency = StringField(default='W-MON')  # Time series frequency

    # Performance metrics
    metrics = EmbeddedDocumentField(ModelMetrics, required=True)

    # Timestamps
    timestamp = DateTimeField(default=datetime.utcnow)  # Training timestamp
    created_at = DateTimeField(default=datetime.utcnow)

    def __repr__(self):
        return f"<MLTrainingResult(batch_id='{self.batch_id}', category='{self.category}', mape={self.metrics.mape if self.metrics else 'N/A'})>"


# ==================== PREDICTIONS ====================
# Matches the structure of predictions_*.csv files

class PredictionEntry(EmbeddedDocument):
    """
    Single prediction entry for a specific week
    """
    week = DateTimeField(required=True)  # Week date
    predicted_value = FloatField(required=True)  # Predicted price/value
    actual_value = FloatField()  # Actual value (if available for validation)

    # Optional: confidence intervals if calculated
    lower_bound = FloatField()
    upper_bound = FloatField()


class CategoryPrediction(Document):
    """
    Stores predictions for a specific category
    Matches the structure of predictions_[category].csv
    """
    meta = {
        'collection': 'category_predictions',
        'indexes': [
            'batch_id',
            'category',
            'created_at',
            ('batch_id', 'category')
        ]
    }

    # Identification
    batch_id = StringField(required=True)  # Format: YYYYMMDD_HHMMSS
    category = StringField(required=True)  # e.g., "Classe_Carnes Vermelhas"

    # Predictions list (12 weeks forward)
    predictions = ListField(EmbeddedDocumentField(PredictionEntry), required=True)

    # Metadata
    n_weeks_predicted = IntField(default=12)  # Number of weeks predicted
    base_date = DateTimeField()  # Starting date for predictions

    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)

    def __repr__(self):
        return f"<CategoryPrediction(batch_id='{self.batch_id}', category='{self.category}', n_predictions={len(self.predictions)})>"


# ==================== PRICE LEADERSHIP ANALYSIS (Q2) ====================
# Matches the results from Question 2 analysis

class GrangerCausalityResult(EmbeddedDocument):
    """
    Granger causality test results
    """
    a_causes_b_pvalue = FloatField()  # P-value for A causes B
    b_causes_a_pvalue = FloatField()  # P-value for B causes A
    is_a_leader = BooleanField()      # True if A is price leader
    is_b_leader = BooleanField()      # True if B is price leader
    max_lag = IntField()               # Maximum lag used in test


class CrossCorrelationResult(EmbeddedDocument):
    """
    Cross-correlation analysis results
    """
    max_correlation_value = FloatField()  # Maximum correlation found
    max_correlation_lag = IntField()      # Lag at maximum correlation
    ccf_values = ListField(FloatField())  # All CCF values
    lags = ListField(IntField())          # Corresponding lags


class PriceLeadershipAnalysis(Document):
    """
    Stores price leadership analysis results (Question 2)
    """
    meta = {
        'collection': 'price_leadership_analyses',
        'indexes': [
            'batch_id',
            'product_id',
            'establishment_a_id',
            'establishment_b_id',
            'created_at',
            ('batch_id', 'product_id')
        ]
    }

    # Identification
    batch_id = StringField(required=True)
    product_id = IntField(required=True)  # Product ID being analyzed
    establishment_a_id = IntField(required=True)  # First establishment
    establishment_b_id = IntField(required=True)  # Second establishment

    # Analysis results
    granger_causality = EmbeddedDocumentField(GrangerCausalityResult)
    cross_correlation = EmbeddedDocumentField(CrossCorrelationResult)

    # Analysis parameters
    frequency = StringField(default='W-MON')  # Time series frequency
    max_lag = IntField(default=8)  # Maximum lag for analysis

    # Data info
    n_observations = IntField()  # Number of observations used
    date_range_start = DateTimeField()
    date_range_end = DateTimeField()

    # Timestamps
    created_at = DateTimeField(default=datetime.utcnow)

    def __repr__(self):
        return f"<PriceLeadershipAnalysis(product_id={self.product_id}, estab_a={self.establishment_a_id}, estab_b={self.establishment_b_id})>"


# ==================== COMPLETE MODEL RUN SUMMARY ====================
# Stores summary of a complete ML pipeline run

class PipelineRunSummary(Document):
    """
    Summary of a complete ML pipeline execution
    Aggregates results from all categories and analyses
    """
    meta = {
        'collection': 'pipeline_runs',
        'indexes': [
            'batch_id',
            'status',
            'started_at'
        ]
    }

    # Identification
    batch_id = StringField(required=True, unique=True)

    # Status tracking
    status = StringField(required=True, choices=['started', 'completed', 'failed'])

    # Summary data
    categories_processed = ListField(StringField())  # List of categories
    total_records_processed = IntField()

    # Performance summary
    average_mape = FloatField()  # Average MAPE across all categories
    best_performing_category = StringField()
    worst_performing_category = StringField()
    objectives_achieved = IntField()  # Count of categories with MAPE < 10%

    # Error tracking
    errors = ListField(DictField())  # Any errors encountered

    # Timestamps
    started_at = DateTimeField(default=datetime.utcnow)
    completed_at = DateTimeField()

    # Metadata
    ml_model_version = StringField()  # Version tracking
    parameters_used = DictField()  # Parameters for the run

    def __repr__(self):
        return f"<PipelineRunSummary(batch_id='{self.batch_id}', status='{self.status}')>"