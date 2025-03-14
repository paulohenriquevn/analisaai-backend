import os
import logging
import pandas as pd
import uuid
import asyncio

from typing import Dict, Optional, Any
from datetime import datetime

from config import settings
from models.processing_models import (
    ProcessingConfig, ProcessingResult, 
)
from database.db import save_processing_results, update_processing_results, update_processing_status

from cafe import (
    create_data_pipeline
)

logger = logging.getLogger("processor-service")

class ProcessorUploadService:
    
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
        
        task = asyncio.create_task(self._process_dataset_task(processing_id, config))
        
        task.add_done_callback(
            lambda t: self._handle_task_exception(t, processing_id)
        )

        return processing_id
    
    def _handle_task_exception(self, task, processing_id):
        try:
            exc = task.exception()
            if exc:
                logger.error(f"Erro durante processamento {processing_id}: {str(exc)}")
                
                loop = asyncio.get_event_loop()
                loop.run_until_complete(
                    update_processing_status(
                        processing_id, 
                        "error", 
                        error_message=f"Erro durante processamento: {str(exc)}"
                    )
                )
        except Exception as e:
            logger.error(f"Erro ao lidar com exceção da tarefa: {str(e)}")

    def _build_preprocessor_config(self, config: ProcessingConfig) -> Dict[str, Any]:
        preprocessor_config = {}
        
        if config.missing_values:
            missing_config = {
                'imputation_strategy': config.missing_values.strategy,
                'imputation_categorical_strategy': config.missing_values.categorical_strategy,
                'imputation_numerical_strategy': config.missing_values.numerical_strategy,
                'imputation_constant': config.missing_values.fill_value
            }
            preprocessor_config.update(missing_config)
        
        if config.outliers:
            outliers_config = {
                'outlier_detection_method': config.outliers.detection_method,
                'outlier_treatment_strategy': config.outliers.treatment_strategy,
                'z_score_threshold': config.outliers.z_threshold,
                'iqr_multiplier': config.outliers.iqr_multiplier
            }
            preprocessor_config.update(outliers_config)
        
        if config.scaling:
            scaling_config = {
                'scaling_method': config.scaling.method,
                'scaling_feature_range': config.scaling.feature_range
            }
            preprocessor_config.update(scaling_config)
        
        if config.columns_to_ignore:
            preprocessor_config['columns_to_ignore'] = config.columns_to_ignore
            
        return preprocessor_config
    
    def _build_feature_engineer_config(self, config: ProcessingConfig) -> Dict[str, Any]:
        feature_config = {
            'correlation_threshold': settings.CAFE_CORRELATION_THRESHOLD,
            'generate_features': settings.CAFE_GENERATE_FEATURES
        }
        
        if config.encoding:
            encoding_config = {
                'categorical_encoding_method': config.encoding.method,
                'max_categories_for_onehot': config.encoding.max_categories
            }
            feature_config.update(encoding_config)
        
        if config.feature_selection:
            selection_config = {
                'feature_selection_method': config.feature_selection.method,
                'max_features': config.feature_selection.max_features,
                'min_feature_importance': config.feature_selection.min_importance
            }
            feature_config.update(selection_config)
            
        return feature_config
    
    def _build_validator_config(self, config: ProcessingConfig) -> Dict[str, Any]:
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
        return 'classification'

    async def _process_dataset_task(self, processing_id: str, config: ProcessingConfig):
        try:
            df = await self.fetch_dataset(config.dataset_id)
            if df is None:
                await update_processing_status(
                    processing_id, 
                    "error", 
                    error_message="Não foi possível carregar o dataset"
                )
                return
            
            loop = asyncio.get_event_loop()
            
            processing_results = {}
            
            try:
                results = await loop.run_in_executor(
                    None, 
                    self._process_data_sync, 
                    df, 
                    config
                )
                
                if results:
                    processing_results.update(results)
                    
                    best_choice = "original"
                    validation_results = processing_results.get("validation_results")
                    if validation_results:
                        best_choice = validation_results.get('best_choice')
                    
                    await update_processing_results(
                        processing_id,
                        {
                            "status": "completed",
                            "best_choice": best_choice,
                            "preprocessing_config": processing_results.get("preprocessing_config"),
                            "feature_engineering_config": processing_results.get("feature_engineering_config"),
                            "validation_results": processing_results.get("validation_results"),
                            "missing_values_report": processing_results.get("missing_values_report"),
                            "outliers_report": processing_results.get("outliers_report"),
                            "feature_importance": processing_results.get("feature_importance"),
                            "transformations_applied": processing_results.get("transformations_applied")
                        }
                    )
                else:
                    await update_processing_status(processing_id, "error", "Processamento falhou ao gerar resultados")
            
            except Exception as e:
                logger.error(f"Erro durante processamento {processing_id}: {str(e)}")
                await update_processing_status(
                    processing_id, 
                    "error", 
                    error_message=f"Erro durante processamento: {str(e)}"
                )
                
        except Exception as e:
            logger.error(f"Erro durante processamento {processing_id}: {str(e)}")
            await update_processing_status(
                processing_id, 
                "error", 
                error_message=f"Erro durante processamento: {str(e)}"
            )

    def _process_data_sync(self, df, config):
        try:
            # Configurar CAFE
            preprocessor_config = self._build_preprocessor_config(config)
            feature_engineer_config = self._build_feature_engineer_config(config)
            validator_config = self._build_validator_config(config)
            
            # Criar pipeline CAFE
            pipeline = create_data_pipeline(
                preprocessor_config=preprocessor_config,
                feature_engineer_config=feature_engineer_config,
                validator_config=validator_config,
                auto_validate=True
            )
            
            # Processar dados
            target_col = config.target_column if config.target_column else None
            transformed_df = pipeline.fit_transform(df, target_col=target_col)
            
            # Extrair resultados
            results = {
                "preprocessing_config": preprocessor_config,
                "feature_engineering_config": feature_engineer_config,
                "validation_results": pipeline.get_validation_results(),
            }
            
            return results
        except Exception as e:
            logger.error(f"Erro durante processamento síncrono: {str(e)}")
            raise

        """Extrai transformações aplicadas pelo pipeline CAFE"""
        try:
            transformations = []
            
            # Transformações do preprocessor
            preprocessor = pipeline.preprocessor
            if hasattr(preprocessor, 'transformations_applied'):
                for transform in preprocessor.transformations_applied:
                    transformation = {
                        'column': transform.get('column', ''),
                        'original_type': transform.get('original_type', ''),
                        'transformation_type': transform.get('type', ''),
                        'details': transform.get('details', {})
                    }
                    
                    # Certifique-se de que os valores são serializáveis
                    if 'details' in transformation and transformation['details']:
                        try:
                            # Converter valores numpy para valores Python nativos
                            details = {}
                            for k, v in transformation['details'].items():
                                if hasattr(v, 'tolist'):  # Numpy array
                                    details[k] = v.tolist()
                                elif hasattr(v, 'item'):  # Numpy scalar
                                    details[k] = v.item()
                                else:
                                    details[k] = v
                            transformation['details'] = details
                        except Exception as e:
                            logger.warning(f"Erro ao processar detalhes da transformação: {str(e)}")
                            transformation['details'] = {}
                    
                    transformations.append(transformation)
            
            # Transformações do feature engineer
            feature_engineer = pipeline.feature_engineer
            if hasattr(feature_engineer, 'transformations_applied'):
                for transform in feature_engineer.transformations_applied:
                    transformation = {
                        'column': transform.get('column', ''),
                        'original_type': transform.get('original_type', ''),
                        'transformation_type': transform.get('type', ''),
                        'details': transform.get('details', {})
                    }
                    
                    # Mesma lógica de processamento para detalhes
                    if 'details' in transformation and transformation['details']:
                        try:
                            details = {}
                            for k, v in transformation['details'].items():
                                if hasattr(v, 'tolist'):
                                    details[k] = v.tolist()
                                elif hasattr(v, 'item'):
                                    details[k] = v.item()
                                else:
                                    details[k] = v
                            transformation['details'] = details
                        except Exception as e:
                            logger.warning(f"Erro ao processar detalhes da transformação: {str(e)}")
                            transformation['details'] = {}
                    
                    transformations.append(transformation)
                    
            return transformations if transformations else None
        except Exception as e:
            logger.warning(f"Erro ao extrair transformações aplicadas: {str(e)}")
        return None
        """Extrai transformações aplicadas pelo pipeline CAFE"""
        try:
            transformations = []
            
            # Transformações do preprocessor
            preprocessor = pipeline.preprocessor
            if hasattr(preprocessor, 'transformations_applied'):
                for transform in preprocessor.transformations_applied:
                    transformations.append({
                        'column': transform.get('column', ''),
                        'original_type': transform.get('original_type', ''),
                        'transformation_type': transform.get('type', ''),
                        'details': transform.get('details', {})
                    })
            
            # Transformações do feature engineer
            feature_engineer = pipeline.feature_engineer
            if hasattr(feature_engineer, 'transformations_applied'):
                for transform in feature_engineer.transformations_applied:
                    transformations.append({
                        'column': transform.get('column', ''),
                        'original_type': transform.get('original_type', ''),
                        'transformation_type': transform.get('type', ''),
                        'details': transform.get('details', {})
                    })
                    
            return transformations if transformations else None
        except Exception as e:
            logger.warning(f"Erro ao extrair transformações aplicadas: {str(e)}")
            return None