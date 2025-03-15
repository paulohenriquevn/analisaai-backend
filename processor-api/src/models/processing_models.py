from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import uuid

class MissingValuesConfig(BaseModel):
    """Configuração para tratamento de valores ausentes"""
    strategy: str = "auto"  # 'auto', 'mean', 'median', 'most_frequent', 'constant'
    fill_value: Optional[Any] = None  # Valor para preencher quando strategy='constant'
    categorical_strategy: Optional[str] = "most_frequent"  # Estratégia específica para variáveis categóricas
    numerical_strategy: Optional[str] = "auto"  # Estratégia específica para variáveis numéricas

class OutliersConfig(BaseModel):
    """Configuração para tratamento de outliers"""
    detection_method: str = "zscore"  # 'zscore', 'iqr', 'isolation_forest'
    treatment_strategy: str = "auto"  # 'auto', 'clip', 'remove', 'impute'
    z_threshold: Optional[float] = 3.0  # Para método 'zscore'
    iqr_multiplier: Optional[float] = 1.5  # Para método 'iqr'

class ScalingConfig(BaseModel):
    """Configuração para normalização/padronização de dados"""
    method: str = "auto"  # 'auto', 'minmax', 'standard', 'robust', 'none'
    feature_range: Optional[tuple] = (0, 1)  # Para método 'minmax'

class EncodingConfig(BaseModel):
    """Configuração para codificação de variáveis categóricas"""
    method: str = "auto"  # 'auto', 'onehot', 'target', 'label', 'binary'
    max_categories: Optional[int] = 10  # Limite para one-hot encoding

class FeatureSelectionConfig(BaseModel):
    """Configuração para seleção de features"""
    method: str = "auto"  # 'auto', 'correlation', 'feature_importance', 'recursive'
    max_features: Optional[int] = None  # Número máximo de features a manter
    min_importance: Optional[float] = 0.01  # Importância mínima para manter a feature
    auto_explore: Optional[bool] = False  # Nova flag para ativar o modo de exploração automática

class ProcessingConfig(BaseModel):
    """Configuração completa para processamento de dados"""
    dataset_id: str
    missing_values: Optional[MissingValuesConfig] = MissingValuesConfig()
    outliers: Optional[OutliersConfig] = OutliersConfig()
    scaling: Optional[ScalingConfig] = ScalingConfig()
    encoding: Optional[EncodingConfig] = EncodingConfig()
    feature_selection: Optional[FeatureSelectionConfig] = FeatureSelectionConfig()
    target_column: Optional[str] = None
    columns_to_ignore: Optional[List[str]] = []
    use_auto_explore: Optional[bool] = False

class MissingValuesReport(BaseModel):
    """Relatório de valores ausentes por coluna"""
    column: str
    data_type: str
    missing_count: int
    missing_percentage: float
    strategy_applied: str
    filled_with: Optional[Any] = None

class OutlierReport(BaseModel):
    """Relatório de outliers por coluna"""
    column: str
    outliers_count: int
    outliers_percentage: float
    method_used: str
    strategy_applied: str

class FeatureImportance(BaseModel):
    """Importância de features"""
    feature: str
    importance: float
    rank: int

class TransformationApplied(BaseModel):
    """Transformação aplicada em uma coluna"""
    column: str
    original_type: str
    transformation_type: str  # 'missing', 'outlier', 'scaling', 'encoding', 'dropped'
    details: Dict[str, Any]

class ProcessingResult(BaseModel):
    """Resultado completo do processamento de dados"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    dataset_id: str
    status: str  # 'processing', 'completed', 'error'
    error_message: Optional[str] = None
    missing_values_report: Optional[List[Dict[str, Any]]] = []
    outliers_report: Optional[List[Dict[str, Any]]] = []
    feature_importance: Optional[List[Dict[str, Any]]] = []
    transformations_applied: Optional[List[Dict[str, Any]]] = []
    preprocessing_config: Optional[Dict[str, Any]] = {}
    feature_engineering_config: Optional[Dict[str, Any]] = {}
    validation_results: Optional[Dict[str, Any]] = {}
    transformation_statistics: Optional[Dict[str, Any]] = {}  # Novo campo para estatísticas do Explorer
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        validate_assignment = True

class ValidationMetrics(BaseModel):
    """Métricas de validação do processamento"""
    performance_original: float
    performance_transformed: float
    performance_diff: float
    performance_diff_pct: float
    feature_reduction: float
    original_n_features: int
    transformed_n_features: int
    best_choice: str  # 'original' ou 'transformed'
    metric_used: str  # 'accuracy', 'f1', 'r2', etc.

class ProcessingResponse(BaseModel):
    """Resposta simplificada do processamento"""
    id: str
    dataset_id: str
    status: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    summary: Optional[str] = None
    validation_metrics: Optional[ValidationMetrics] = None
    auto_explore_used: Optional[bool] = False  # Novo campo indicando se o Explorer foi usado
    
    class Config:
        validate_assignment = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }