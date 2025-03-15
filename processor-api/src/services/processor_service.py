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
    
    def get_explorer_statistics(self, transformation_stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formata as estatísticas do Explorer para exibição na API
        
        Args:
            transformation_stats: Estatísticas de transformação do Explorer
            
        Returns:
            Dicionário formatado com estatísticas do Explorer
        """
        if not transformation_stats:
            return {}
            
        try:
            # Extrair as estatísticas mais relevantes
            stats = {
                "total_transformations_tested": transformation_stats.get('total_transformations_tested', 0),
                "best_transformation": transformation_stats.get('best_transformation', 'N/A'),
                "feature_reduction": transformation_stats.get('feature_change_pct', 0),
                "original_features": transformation_stats.get('original_feature_count', 0),
                "transformed_features": transformation_stats.get('transformed_feature_count', 0),
            }
            
            # Adicionar informações sobre transformações mais comuns
            most_common = transformation_stats.get('most_common_transformations', [])
            if most_common:
                stats['most_common_transformations'] = most_common
                
            # Adicionar informações sobre desempenho do modelo
            if 'time_spent' in transformation_stats:
                stats['processing_time'] = transformation_stats['time_spent']
                
            return stats
        except Exception as e:
            logger.warning(f"Erro ao formatar estatísticas do Explorer: {str(e)}")
            return {}
            
    async def visualize_transformations(self, processing_id: str) -> Optional[str]:
        """
        Gera (ou recupera) visualizações para as transformações aplicadas
        
        Args:
            processing_id: ID do processamento
            
        Returns:
            Caminho para o arquivo de visualização ou None
        """
        try:
            report_folder = os.path.join(settings.PROCESSED_FOLDER, processing_id)
            visualizations = {
                "transformation_tree": os.path.join(report_folder, "transformation_tree.png"),
                "transformations": os.path.join(report_folder, "transformations.png"),
                "missing_values": os.path.join(report_folder, "missing_values.png"),
                "outliers": os.path.join(report_folder, "outliers.png"),
                "feature_importance": os.path.join(report_folder, "feature_importance.png"),
                "feature_distributions": os.path.join(report_folder, "feature_distributions.png"),
                "correlation_matrix": os.path.join(report_folder, "correlation_matrix.png"),
                "target_correlations": os.path.join(report_folder, "target_correlations.png")
            }
            
            # Verificar quais visualizações existem
            existing_visualizations = {}
            for name, path in visualizations.items():
                if os.path.exists(path):
                    existing_visualizations[name] = path
                    
            return existing_visualizations
        except Exception as e:
            logger.error(f"Erro ao recuperar visualizações: {str(e)}")
            return None