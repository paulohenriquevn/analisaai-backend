import os
import logging
import pandas as pd
import numpy as np
import uuid
import json
from typing import Dict, List, Optional, Any
import httpx
from datetime import datetime

from config import settings
from models.processing_models import (
    ProcessingConfig, ProcessingResult, 
    MissingValuesReport, OutlierReport, 
    FeatureImportance, TransformationApplied,
    ValidationMetrics
)
from database.db import save_processing_results, update_processing_status, get_processing_results

# Importar componentes do CAFE
from cafe import (
    PreProcessor,
    FeatureEngineer,
    PerformanceValidator,
    DataPipeline,
    Explorer,
    create_data_pipeline
)

logger = logging.getLogger("processor-service")

class ProcessorService:
    
    async def fetch_dataset(self, dataset_id: str) -> Optional[pd.DataFrame]:
        try:
            
            file_data = os.path.join(settings.UPLOAD_FOLDER, f"{dataset_id}.csv")
            df = pd.read_csv(file_data)
            
            file_path = os.path.join(settings.PROCESSED_FOLDER, f"{dataset_id}_original.csv")
            df.to_csv(file_path)
            
            logger.info(f"Dataset {dataset_id} carregado com sucesso: {df.shape[0]} linhas, {df.shape[1]} colunas")
            return df
                
        except Exception as e:
            logger.error(f"Erro ao buscar dataset {dataset_id}: {str(e)}")
            return None
    
    async def process_dataset(self, config: ProcessingConfig) -> str:
        
        processing_id = str(uuid.uuid4())
        
        # Salvar entrada inicial no banco de dados
        initial_result = ProcessingResult(
            id=processing_id,
            dataset_id=config.dataset_id,
            status="processing",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        await save_processing_results(initial_result.dict())
        
        # Iniciar processamento em background
        self._process_dataset_task(processing_id, config)
        
        return processing_id
    
    async def _process_dataset_task(self, processing_id: str, config: ProcessingConfig):
        try:
            df = await self.fetch_dataset(config.dataset_id)
            if df is None:
                await update_processing_status(
                    processing_id, 
                    "error", 
                    "Não foi possível carregar o dataset"
                )
                return
            
            # Converter configuração para os formatos esperados pelo CAFE
            preprocessor_config = self._build_preprocessor_config(config)
            feature_engineer_config = self._build_feature_engineer_config(config)
            validator_config = self._build_validator_config(config)
            
            # Criar pipeline CAFE
            pipeline = create_data_pipeline(
                preprocessor_config=preprocessor_config,
                feature_engineer_config=feature_engineer_config,
                validator_config=validator_config,
                auto_validate=settings.CAFE_AUTO_VALIDATE
            )
            
            # Processar dados
            target_col = config.target_column if config.target_column else None
            transformed_df = pipeline.fit_transform(df, target_col=target_col)
            
            # Extrair resultados e relatórios
            missing_values_report = self._extract_missing_values_report(pipeline, df)
            outliers_report = self._extract_outliers_report(pipeline, df)
            feature_importance = self._extract_feature_importance(pipeline, df, target_col)
            transformations_applied = self._extract_transformations(pipeline, df)
            validation_results = pipeline.get_validation_results()
            
            # Salvar dataset processado
            processed_file_path = os.path.join(
                settings.PROCESSED_FOLDER, 
                f"{config.dataset_id}_processed.csv"
            )
            transformed_df.to_csv(processed_file_path, index=False)
            
            # Criar resultado do processamento
            result = ProcessingResult(
                id=processing_id,
                dataset_id=config.dataset_id,
                status="completed",
                missing_values_report=missing_values_report,
                outliers_report=outliers_report,
                feature_importance=feature_importance,
                transformations_applied=transformations_applied,
                preprocessing_config=preprocessor_config,
                feature_engineering_config=feature_engineer_config,
                validation_results=validation_results
            )
            
            # Atualizar no banco de dados
            await save_processing_results(result.dict())
            logger.info(f"Processamento concluído com sucesso: {processing_id}")
            
        except Exception as e:
            logger.error(f"Erro durante processamento {processing_id}: {str(e)}")
            await update_processing_status(
                processing_id, 
                "error", 
                f"Erro durante processamento: {str(e)}"
            )
    
    def _build_preprocessor_config(self, config: ProcessingConfig) -> Dict[str, Any]:
        """Constrói configuração para o PreProcessor do CAFE"""
        preprocessor_config = {}
        
        # Configurar tratamento de valores ausentes
        if config.missing_values:
            missing_config = {
                'imputation_strategy': config.missing_values.strategy,
                'imputation_categorical_strategy': config.missing_values.categorical_strategy,
                'imputation_numerical_strategy': config.missing_values.numerical_strategy,
                'imputation_constant': config.missing_values.fill_value
            }
            preprocessor_config.update(missing_config)
        
        # Configurar tratamento de outliers
        if config.outliers:
            outliers_config = {
                'outlier_detection_method': config.outliers.detection_method,
                'outlier_treatment_strategy': config.outliers.treatment_strategy,
                'z_score_threshold': config.outliers.z_threshold,
                'iqr_multiplier': config.outliers.iqr_multiplier
            }
            preprocessor_config.update(outliers_config)
        
        # Configurar normalização/padronização
        if config.scaling:
            scaling_config = {
                'scaling_method': config.scaling.method,
                'scaling_feature_range': config.scaling.feature_range
            }
            preprocessor_config.update(scaling_config)
        
        # Configurar colunas a ignorar
        if config.columns_to_ignore:
            preprocessor_config['columns_to_ignore'] = config.columns_to_ignore
            
        return preprocessor_config
    
    def _build_feature_engineer_config(self, config: ProcessingConfig) -> Dict[str, Any]:
        """Constrói configuração para o FeatureEngineer do CAFE"""
        feature_config = {
            'correlation_threshold': settings.CAFE_CORRELATION_THRESHOLD,
            'generate_features': settings.CAFE_GENERATE_FEATURES
        }
        
        # Configurar codificação de variáveis categóricas
        if config.encoding:
            encoding_config = {
                'categorical_encoding_method': config.encoding.method,
                'max_categories_for_onehot': config.encoding.max_categories
            }
            feature_config.update(encoding_config)
        
        # Configurar seleção de features
        if config.feature_selection:
            selection_config = {
                'feature_selection_method': config.feature_selection.method,
                'max_features': config.feature_selection.max_features,
                'min_feature_importance': config.feature_selection.min_importance
            }
            feature_config.update(selection_config)
            
        return feature_config
    
    def _build_validator_config(self, config: ProcessingConfig) -> Dict[str, Any]:
        """Constrói configuração para o PerformanceValidator do CAFE"""
        task = self._infer_task_type(config.target_column) if config.target_column else 'classification'
        
        validator_config = {
            'max_performance_drop': settings.CAFE_MAX_PERFORMANCE_DROP,
            'cv_folds': settings.CAFE_CV_FOLDS,
            'metric': 'accuracy' if task == 'classification' else 'r2',
            'task': task,
            'base_model': 'rf',
            'verbose': True
        }
        
        return validator_config
    
    def _infer_task_type(self, target_column: str) -> str:
        """Infere o tipo de tarefa baseado na coluna alvo"""
        # Somente uma inferência simples, seria necessário analisar o dataset para inferir corretamente
        return 'classification'
    
    def _extract_missing_values_report(self, pipeline, df) -> List[MissingValuesReport]:
        """Extrai relatório de valores ausentes do pipeline CAFE"""
        try:
            reports = []
            preprocessor = pipeline.preprocessor
            
            for col in df.columns:
                col_stats = preprocessor.column_stats.get(col, {})
                missing_count = col_stats.get('missing_count', 0)
                missing_pct = col_stats.get('missing_percentage', 0.0)
                strategy = col_stats.get('imputation_strategy', 'none')
                filled_with = col_stats.get('imputation_value', None)
                
                if missing_count > 0 or strategy != 'none':
                    reports.append(MissingValuesReport(
                        column=col,
                        data_type=str(df[col].dtype),
                        missing_count=missing_count,
                        missing_percentage=missing_pct,
                        strategy_applied=strategy,
                        filled_with=filled_with
                    ))
            
            return reports
        except Exception as e:
            logger.warning(f"Erro ao extrair relatório de valores ausentes: {str(e)}")
            return []
    
    def _extract_outliers_report(self, pipeline, df) -> List[OutlierReport]:
        """Extrai relatório de outliers do pipeline CAFE"""
        try:
            reports = []
            preprocessor = pipeline.preprocessor
            
            for col in df.columns:
                if pd.api.types.is_numeric_dtype(df[col]):
                    col_stats = preprocessor.column_stats.get(col, {})
                    outliers_count = col_stats.get('outliers_count', 0)
                    outliers_pct = col_stats.get('outliers_percentage', 0.0)
                    method = col_stats.get('outlier_detection_method', 'none')
                    strategy = col_stats.get('outlier_treatment_strategy', 'none')
                    
                    if outliers_count > 0:
                        reports.append(OutlierReport(
                            column=col,
                            outliers_count=outliers_count,
                            outliers_percentage=outliers_pct,
                            method_used=method,
                            strategy_applied=strategy
                        ))
            
            return reports
        except Exception as e:
            logger.warning(f"Erro ao extrair relatório de outliers: {str(e)}")
            return []
    
    def _extract_feature_importance(self, pipeline, df, target_col) -> List[FeatureImportance]:
        """Extrai importância das features do pipeline CAFE"""
        try:
            if target_col and hasattr(pipeline, 'get_feature_importance'):
                importance_df = pipeline.get_feature_importance(df, target_col=target_col)
                
                result = []
                for i, (_, row) in enumerate(importance_df.iterrows()):
                    result.append(FeatureImportance(
                        feature=row['feature'],
                        importance=float(row['importance']),
                        rank=i+1
                    ))
                return result
            return []
        except Exception as e:
            logger.warning(f"Erro ao extrair importância das features: {str(e)}")
            return []
    
    def _extract_transformations(self, pipeline, df) -> List[TransformationApplied]:
        """Extrai todas as transformações aplicadas pelo pipeline CAFE"""
        try:
            transformations = []
            
            # Extrair transformações do preprocessor
            for col in df.columns:
                col_stats = pipeline.preprocessor.column_stats.get(col, {})
                
                # Transformações de valores ausentes
                if col_stats.get('missing_count', 0) > 0:
                    transformations.append(TransformationApplied(
                        column=col,
                        original_type=str(df[col].dtype),
                        transformation_type='missing',
                        details={
                            'strategy': col_stats.get('imputation_strategy', 'none'),
                            'missing_count': col_stats.get('missing_count', 0),
                            'missing_percentage': col_stats.get('missing_percentage', 0.0)
                        }
                    ))
                
                # Transformações de outliers
                if col_stats.get('outliers_count', 0) > 0:
                    transformations.append(TransformationApplied(
                        column=col,
                        original_type=str(df[col].dtype),
                        transformation_type='outlier',
                        details={
                            'method': col_stats.get('outlier_detection_method', 'none'),
                            'strategy': col_stats.get('outlier_treatment_strategy', 'none'),
                            'outliers_count': col_stats.get('outliers_count', 0),
                            'outliers_percentage': col_stats.get('outliers_percentage', 0.0)
                        }
                    ))
                
                # Transformações de escala
                if col_stats.get('scaling_applied', False):
                    transformations.append(TransformationApplied(
                        column=col,
                        original_type=str(df[col].dtype),
                        transformation_type='scaling',
                        details={
                            'method': col_stats.get('scaling_method', 'none'),
                            'original_min': col_stats.get('original_min'),
                            'original_max': col_stats.get('original_max'),
                            'scaled_min': col_stats.get('scaled_min'),
                            'scaled_max': col_stats.get('scaled_max')
                        }
                    ))
            
            # Extrair transformações do feature engineer
            if hasattr(pipeline, 'feature_engineer') and pipeline.feature_engineer:
                for transform_info in pipeline.feature_engineer.transformations_applied:
                    if transform_info.get('type') == 'encoding':
                        transformations.append(TransformationApplied(
                            column=transform_info.get('column', ''),
                            original_type='category',
                            transformation_type='encoding',
                            details={
                                'method': transform_info.get('method', 'none'),
                                'original_categories': transform_info.get('original_categories', []),
                                'new_columns': transform_info.get('new_columns', [])
                            }
                        ))
                    elif transform_info.get('type') == 'dropped':
                        transformations.append(TransformationApplied(
                            column=transform_info.get('column', ''),
                            original_type=transform_info.get('dtype', 'unknown'),
                            transformation_type='dropped',
                            details={
                                'reason': transform_info.get('reason', 'unknown'),
                                'correlation_with': transform_info.get('correlation_with', None),
                                'correlation_value': transform_info.get('correlation_value', None)
                            }
                        ))
                    elif transform_info.get('type') == 'generated':
                        transformations.append(TransformationApplied(
                            column=transform_info.get('column', ''),
                            original_type='N/A',
                            transformation_type='generated',
                            details={
                                'method': transform_info.get('method', 'unknown'),
                                'source_columns': transform_info.get('source_columns', []),
                                'transformation': transform_info.get('transformation', '')
                            }
                        ))
            
            return transformations
        except Exception as e:
            logger.warning(f"Erro ao extrair transformações: {str(e)}")
            return []
    
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