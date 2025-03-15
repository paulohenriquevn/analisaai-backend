from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import uuid

class ColumnInfo(BaseModel):
    """Informações sobre uma coluna de dados"""
    name: str
    data_type: str
    missing_count: int = 0
    missing_percentage: float = 0

class DataIssue(BaseModel):
    """Problema identificado nos dados"""
    type: str
    description: str
    severity: str  # 'low', 'medium', 'high'
    column: Optional[str] = None
    suggestion: Optional[str] = None

class FileMetadata(BaseModel):
    """Metadados de um arquivo processado"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    file_size: int
    upload_date: datetime = Field(default_factory=datetime.now)
    file_type: str  # 'csv', 'xlsx', 'xls', 'json'
    status: str  # 'pending', 'processing', 'processed', 'error'
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    encoding: Optional[str] = None
    delimiter: Optional[str] = None
    error_message: Optional[str] = None
    confirmed: bool = False  # Flag para indicar se o upload foi confirmado
    dataset_name: Optional[str] = None  # Nome único para o dataset

class FilePreview(BaseModel):
    """Prévia do conteúdo de um arquivo"""
    columns: List[ColumnInfo]
    rows: List[Dict[str, Any]]
    total_rows: int

class DataAnalysisResult(BaseModel):
    """Resultados da análise de dados"""
    issues: List[DataIssue] = []
    column_stats: Dict[str, Dict[str, Any]] = {}
    row_count: int
    column_count: int