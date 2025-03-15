import os
import logging
import pandas as pd
import uuid
import asyncio
import matplotlib.pyplot as plt

from typing import Dict, Optional, Any
from datetime import datetime

from config import settings
from models.processing_models import (
    ProcessingConfig, ProcessingResult, 
)
from database.db import save_processing_results, update_processing_results, update_processing_status

from cafe import (
    create_data_pipeline,
    Explorer,
    ReportDataPipeline,
    ReportVisualizer
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
            updated_at=datetime.now(),
            transformation_statistics={}  # Inicializar com um objeto vazio
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
                'missing_values_strategy': config.missing_values.strategy,
                'categorical_strategy': config.missing_values.categorical_strategy,
                'numerical_strategy': config.missing_values.numerical_strategy,
                'imputation_constant': config.missing_values.fill_value
            }
            preprocessor_config.update(missing_config)
        
        if config.outliers:
            outliers_config = {
                'outlier_method': config.outliers.detection_method,
                'outlier_treatment_strategy': config.outliers.treatment_strategy,
                'z_score_threshold': config.outliers.z_threshold,
                'iqr_multiplier': config.outliers.iqr_multiplier
            }
            preprocessor_config.update(outliers_config)
        
        if config.scaling:
            scaling_config = {
                'scaling': config.scaling.method,
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
                'categorical_strategy': config.encoding.method,
                'max_categories_for_onehot': config.encoding.max_categories
            }
            feature_config.update(encoding_config)
        
        if config.feature_selection:
            selection_config = {
                'feature_selection': config.feature_selection.method,
                'feature_selection_params': {
                    'k': config.feature_selection.max_features,
                    'threshold': config.feature_selection.min_importance
                }
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
                # Verificar se o modo de exploração automática está ativado
                use_explorer = config.feature_selection and config.feature_selection.method == 'auto'
                
                results = await loop.run_in_executor(
                    None, 
                    self._process_data_sync if not use_explorer else self._process_data_with_explorer, 
                    df, 
                    config,
                    processing_id
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
                            "transformations_applied": processing_results.get("transformations_applied"),
                            "transformation_statistics": processing_results.get("transformation_statistics", {})
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

    def _process_data_with_explorer(self, df, config, processing_id):
        """
        Processa dados usando o Explorer do CAFE para encontrar automaticamente as melhores configurações.
        
        Args:
            df: DataFrame com os dados
            config: Configuração de processamento
            processing_id: ID do processamento
            
        Returns:
            Dicionário com resultados do processamento
        """
        try:
            target_col = config.target_column
            logger.info(f"Iniciando exploração automática de configurações para o dataset (target: {target_col})")

            # Criar pasta para armazenar resultados
            report_folder = os.path.join(settings.PROCESSED_FOLDER, processing_id)
            os.makedirs(report_folder, exist_ok=True)
            
            # Inicializar Explorer com a coluna alvo
            explorer = Explorer(target_col=target_col)
            
            # Executar análise de transformações
            # Isto testa várias combinações de configurações para encontrar a melhor
            logger.info("Analisando transformações com Explorer...")
            transformed_df = explorer.analyze_transformations(df)
            
            # Obter a configuração ótima descoberta pelo Explorer
            best_config = explorer.get_best_pipeline_config()
            logger.info(f"Melhor configuração encontrada pelo Explorer: {best_config}")
            
            # Obter estatísticas sobre as transformações testadas
            transformation_stats = explorer.get_transformation_statistics()
            
            # Criar pipeline com a configuração ótima
            pipeline = explorer.create_optimal_pipeline()
            
            # Ajustar novamente o pipeline e transformar os dados
            # (para garantir resultados consistentes)
            logger.info("Aplicando pipeline otimizado aos dados...")
            transformed_df = pipeline.fit_transform(df, target_col=target_col)
            
            # Salvar o dataset transformado
            transformed_file_path = os.path.join(report_folder, f"{config.dataset_id}_transformed.csv")
            transformed_df.to_csv(transformed_file_path, index=False)
            
            # Visualizar árvore de transformações (opcional)
            explorer.visualize_transformations(os.path.join(report_folder, "transformation_tree.png"))
            
            # Criar ReportDataPipeline para gerar relatórios
            reporter = ReportDataPipeline(
                df=df,  # Dataset original
                target_col=target_col,
                preprocessor=pipeline.preprocessor,
                feature_engineer=pipeline.feature_engineer,
                validator=pipeline.validator
            )
            
            # Criar ReportVisualizer para gerar visualizações
            visualizer = ReportVisualizer()
            
            # 1. Obter relatório de valores ausentes
            missing_values_report = reporter.get_missing_values()
            missing_values_list = []
            if not missing_values_report.empty:
                missing_values_list = missing_values_report.to_dict('records')
                
                # Gerar visualização de valores ausentes
                fig_missing = visualizer.visualize_missing_values(missing_values_report)
                if fig_missing:
                    plt.figure(fig_missing.number)
                    plt.savefig(os.path.join(report_folder, "missing_values.png"))
                    plt.close(fig_missing)
            
            # 2. Obter relatório de outliers
            outliers_report = reporter.get_outliers()
            outliers_list = []
            if not outliers_report.empty:
                outliers_list = outliers_report.to_dict('records')
                
                # Gerar visualização de outliers
                fig_outliers = visualizer.visualize_outliers(outliers_report, df)
                if fig_outliers:
                    plt.figure(fig_outliers.number)
                    plt.savefig(os.path.join(report_folder, "outliers.png"))
                    plt.close(fig_outliers)
            
            # 3. Obter relatório de importância de features
            importance_report = reporter.get_feature_importance()
            feature_importance_list = []
            if not importance_report.empty:
                feature_importance_list = importance_report.to_dict('records')
                
                # Gerar visualização de importância de features
                fig_importance = visualizer.visualize_feature_importance(importance_report)
                if fig_importance:
                    plt.figure(fig_importance.number)
                    plt.savefig(os.path.join(report_folder, "feature_importance.png"))
                    plt.close(fig_importance)
            
            # 4. Obter resultados de validação
            validation_results = pipeline.get_validation_results()
            if validation_results:
                # Preparar estatísticas para visualização
                stats = {
                    'dimensoes_originais': df.shape,
                    'dimensoes_transformadas': transformed_df.shape,
                    'reducao_features_pct': transformation_stats.get('feature_change_pct', 0),
                    'ganho_performance_pct': validation_results.get('performance_diff_pct', 0),
                    'decisao_final': validation_results.get('best_choice', 'original').upper()
                }
                
                # Visualizar transformações
                fig_transformations = visualizer.visualize_transformations(validation_results, stats)
                if fig_transformations:
                    plt.figure(fig_transformations.number)
                    plt.savefig(os.path.join(report_folder, "transformations.png"))
                    plt.close(fig_transformations)
            
            # 5. Visualizações adicionais
            # 5.1 Visualização de distribuição de dados
            top_features = importance_report.head(6)['feature'].tolist() if not importance_report.empty else None
            fig_distribution = visualizer.visualize_data_distribution(df, columns=top_features)
            if fig_distribution:
                plt.figure(fig_distribution.number)
                plt.savefig(os.path.join(report_folder, "feature_distributions.png"))
                plt.close(fig_distribution)
            
            # 5.2 Visualização de matriz de correlação
            correlation_plots = visualizer.visualize_correlation_matrix(df, target_col=target_col)
            if correlation_plots:
                if isinstance(correlation_plots, tuple):
                    fig_corr, fig_target_corr = correlation_plots
                    plt.figure(fig_corr.number)
                    plt.savefig(os.path.join(report_folder, "correlation_matrix.png"))
                    plt.close(fig_corr)
                    
                    plt.figure(fig_target_corr.number)
                    plt.savefig(os.path.join(report_folder, "target_correlations.png"))
                    plt.close(fig_target_corr)
                else:
                    plt.figure(correlation_plots.number)
                    plt.savefig(os.path.join(report_folder, "correlation_matrix.png"))
                    plt.close(correlation_plots)
                    
            # Extrair transformações aplicadas pelo pipeline
            transformations_list = self._extract_transformations(pipeline)
            
            # Preparar resultados para retorno
            results = {
                "preprocessing_config": best_config.get('preprocessor_config', {}),
                "feature_engineering_config": best_config.get('feature_engineer_config', {}),
                "validation_results": pipeline.get_validation_results(),
                "missing_values_report": missing_values_list,
                "outliers_report": outliers_list,
                "feature_importance": feature_importance_list,
                "transformations_applied": transformations_list,
                "transformation_statistics": transformation_stats
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Erro durante exploração automática: {str(e)}")
            raise
    
    def _process_data_sync(self, df, config, processing_id):
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
            
            # Criar a pasta para armazenar as visualizações
            report_folder = os.path.join(settings.PROCESSED_FOLDER, processing_id)
            os.makedirs(report_folder, exist_ok=True)
            
            # Salvar o dataset transformado
            transformed_file_path = os.path.join(report_folder, f"{config.dataset_id}_transformed.csv")
            transformed_df.to_csv(transformed_file_path, index=False)
            
            # Criar ReportDataPipeline para gerar relatórios
            reporter = ReportDataPipeline(
                df=df,  # Dataset original
                target_col=target_col,
                preprocessor=pipeline.preprocessor,
                feature_engineer=pipeline.feature_engineer,
                validator=pipeline.validator
            )
            
            # Criar ReportVisualizer para gerar visualizações
            visualizer = ReportVisualizer()
            
            # 1. Obter relatório de valores ausentes
            missing_values_report = reporter.get_missing_values()
            missing_values_list = []
            if not missing_values_report.empty:
                missing_values_list = missing_values_report.to_dict('records')
                
                # Gerar visualização de valores ausentes
                fig_missing = visualizer.visualize_missing_values(missing_values_report)
                if fig_missing:
                    plt.figure(fig_missing.number)
                    plt.savefig(os.path.join(report_folder, "missing_values.png"))
                    plt.close(fig_missing)
            
            # 2. Obter relatório de outliers
            outliers_report = reporter.get_outliers()
            outliers_list = []
            if not outliers_report.empty:
                outliers_list = outliers_report.to_dict('records')
                
                # Gerar visualização de outliers
                fig_outliers = visualizer.visualize_outliers(outliers_report, df)
                if fig_outliers:
                    plt.figure(fig_outliers.number)
                    plt.savefig(os.path.join(report_folder, "outliers.png"))
                    plt.close(fig_outliers)
            
            # 3. Obter relatório de importância de features
            importance_report = reporter.get_feature_importance()
            feature_importance_list = []
            if not importance_report.empty:
                feature_importance_list = importance_report.to_dict('records')
                
                # Gerar visualização de importância de features
                fig_importance = visualizer.visualize_feature_importance(importance_report)
                if fig_importance:
                    plt.figure(fig_importance.number)
                    plt.savefig(os.path.join(report_folder, "feature_importance.png"))
                    plt.close(fig_importance)
            
            # 4. Obter relatório de transformações
            transformations_report = reporter.get_transformations()
            transformations_list = []
            
            # Mostrar estatísticas de transformações
            stats = transformations_report.get('estatisticas', {})
            if stats and stats.get('dimensoes_originais') is not None:
                # Gerar visualização das transformações
                validation_results = transformations_report.get('validacao', {})
                fig_transformations = visualizer.visualize_transformations(validation_results, stats)
                if fig_transformations:
                    plt.figure(fig_transformations.number)
                    plt.savefig(os.path.join(report_folder, "transformations.png"))
                    plt.close(fig_transformations)
            
            # 5. Gerar visualizações adicionais
            
            # 5.1 Visualização de distribuição de dados
            top_features = importance_report.head(6)['feature'].tolist() if not importance_report.empty else None
            fig_distribution = visualizer.visualize_data_distribution(df, columns=top_features)
            if fig_distribution:
                plt.figure(fig_distribution.number)
                plt.savefig(os.path.join(report_folder, "feature_distributions.png"))
                plt.close(fig_distribution)
            
            # 5.2 Visualização de matriz de correlação
            correlation_plots = visualizer.visualize_correlation_matrix(df, target_col=target_col)
            if correlation_plots:
                if isinstance(correlation_plots, tuple):
                    fig_corr, fig_target_corr = correlation_plots
                    plt.figure(fig_corr.number)
                    plt.savefig(os.path.join(report_folder, "correlation_matrix.png"))
                    plt.close(fig_corr)
                    
                    plt.figure(fig_target_corr.number)
                    plt.savefig(os.path.join(report_folder, "target_correlations.png"))
                    plt.close(fig_target_corr)
                else:
                    plt.figure(correlation_plots.number)
                    plt.savefig(os.path.join(report_folder, "correlation_matrix.png"))
                    plt.close(correlation_plots)
            
            # 6. Obter resumo conciso
            summary = reporter.get_report_summary()
            
            # Extrair transformações aplicadas pelo pipeline
            transformations_list = self._extract_transformations(pipeline)
            
            # Preparar resultados para retorno
            results = {
                "preprocessing_config": preprocessor_config,
                "feature_engineering_config": feature_engineer_config,
                "validation_results": pipeline.get_validation_results(),
                "missing_values_report": missing_values_list,
                "outliers_report": outliers_list,
                "feature_importance": feature_importance_list,
                "transformations_applied": transformations_list,
            }
            
            return results
        except Exception as e:
            logger.error(f"Erro durante processamento síncrono: {str(e)}")
            raise

    def _extract_transformations(self, pipeline):
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