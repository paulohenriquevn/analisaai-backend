import os
import logging
import pandas as pd
import uuid
import asyncio

from typing import Dict, List, Optional, Any
from datetime import datetime

from config import settings
from models.processing_models import (
    ProcessingConfig, ProcessingResult, 
    MissingValuesReport, OutlierReport, 
    FeatureImportance, TransformationApplied,
    ValidationMetrics
)
from database.db import save_processing_results, update_processing_status, get_processing_results

from cafe import (
    create_data_pipeline
)

logger = logging.getLogger("processor-service")

class ProcessorService:
    
    async def get_processing_results(self, processing_id: str) -> Optional[ProcessingResult]:
        """Obter resultados de processamento pelo ID"""
        try:
            result = await get_processing_results(processing_id)
            if result:
                return ProcessingResult(**result)
            return None
        except Exception as e:
            logger.error(f"Erro ao obter resultados de processamento {processing_id}: {str(e)}")
            return None
    
    def format_validation_metrics(self, validation_results: Dict[str, Any]) -> Optional[ValidationMetrics]:
        """Formata as métricas de validação do CAFE para o formato esperado pela API"""
        if not validation_results:
            return None
            
        try:
            original_features = validation_results.get('original_n_features', 0)
            transformed_features = original_features * (1 - validation_results.get('feature_reduction', 0))
            
            return ValidationMetrics(
                performance_original=validation_results.get('performance_original', 0),
                performance_transformed=validation_results.get('performance_transformed', 0),
                performance_diff=validation_results.get('performance_diff', 0),
                performance_diff_pct=validation_results.get('performance_diff_pct', 0),
                feature_reduction=validation_results.get('feature_reduction', 0),
                original_n_features=original_features,
                transformed_n_features=int(transformed_features),
                best_choice=validation_results.get('best_choice', 'original'),
                metric_used=validation_results.get('metric', 'accuracy')
            )
        except Exception as e:
            logger.warning(f"Erro ao formatar métricas de validação: {str(e)}")
            return None