import logging
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List, Optional, Dict, Any

from models.processing_models import (
    ProcessingConfig, ProcessingResult, ProcessingResponse,
    MissingValuesConfig, OutliersConfig, ScalingConfig,
    EncodingConfig, FeatureSelectionConfig
)
from services.processor_service import ProcessorService
from services.processor_upload_service import ProcessorUploadService


logger = logging.getLogger("processor-routes")

router = APIRouter(tags=["Processamento"])

def get_processor_service():
    return ProcessorService()

def get_processor_upload_service():
    return ProcessorUploadService()


@router.post("/process", response_model=ProcessingResponse)
async def process_dataset(
    config: ProcessingConfig,
    background_tasks: BackgroundTasks,
    processor_upload_service: ProcessorUploadService = Depends(get_processor_upload_service)
):
    try:
        if not config.dataset_id:
            raise HTTPException(
                status_code=400, 
                detail="O campo dataset_id é obrigatório"
            )
        
        # Verificar se o modo de exploração automática deve ser ativado
        auto_explore = config.use_auto_explore or (
            config.feature_selection and 
            config.feature_selection.method == "auto" and 
            config.feature_selection.auto_explore
        )
        
        if auto_explore:
            logger.info(f"Modo de exploração automática ativado para o dataset {config.dataset_id}")
            
        target_column = config.target_column
        
        processing_id = await processor_upload_service.process_dataset(config)
        
        response = {
            "id": processing_id,
            "dataset_id": config.dataset_id,
            "status": "processing",
            "auto_explore_used": auto_explore,
            "summary": "Processamento iniciado." + 
                      (" Exploração automática de features ativada." if auto_explore else "") + 
                      " Use o endpoint /process/{processing_id} para verificar o status."
        }
        
        if target_column:
            response["target_column"] = target_column
        
        # Converter para o modelo
        return ProcessingResponse(**response)
    except Exception as e:
        logger.error(f"Erro ao iniciar processamento: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao iniciar processamento: {str(e)}")


@router.get("/process/{processing_id}", response_model=ProcessingResponse)
async def get_processing_result(
    processing_id: str,
    processor_service: ProcessorService = Depends(get_processor_service)
):
    try:
        result = await processor_service.get_processing_results(processing_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Processamento não encontrado")
        
        # Verificar se o Explorer foi usado
        auto_explore_used = bool(result.get("transformation_statistics"))
        
        # Formatar métricas de validação
        validation_metrics = processor_service.format_validation_metrics(result.get("validation_results"))
        
        # Gerar resumo baseado no status
        summary = ""
        if result.get("status") == "completed":
            transformed_features = len(result.get("transformations_applied", [])) if result.get("transformations_applied") else 0
            missing_values = len(result.get("missing_values_report", [])) if result.get("missing_values_report") else 0
            outliers = len(result.get("outliers_report", [])) if result.get("outliers_report") else 0
            
            # Incluir informação da coluna target no resumo
            target_info = ""
            if result.get("target_column"):
                target_info = f" Coluna target: {result.get('target_column')}."
            
            summary = (
                f"Processamento concluído com sucesso.{target_info} "
                f"{transformed_features} transformações aplicadas, "
                f"{missing_values} colunas com valores ausentes tratados, "
                f"{outliers} colunas com outliers tratados."
            )
            
            if auto_explore_used:
                # Adicionar estatísticas da exploração automática
                stats = result.get("transformation_statistics") or {}
                transformations_tested = stats.get('total_transformations_tested', 0)
                best_transformation = stats.get('best_transformation', 'N/A')
                
                summary += (
                    f" Exploração automática testou {transformations_tested} configurações" +
                    f" para encontrar a melhor transformação {best_transformation}."
                )
            
            if validation_metrics:
                best = validation_metrics.best_choice
                diff_pct = validation_metrics.performance_diff_pct
                feature_red_pct = validation_metrics.feature_reduction * 100
                
                summary += (
                    f" Validação recomenda usar dados {best}. "
                    f"Diferença de performance: {diff_pct:.2f}%. "
                    f"Redução de features: {feature_red_pct:.1f}%."
                )
        elif result.get("status") == "error":
            summary = f"Erro durante o processamento: {result.get('error_message')}"
        else:
            summary = "Processamento em andamento..."
        
        # Preparar resposta
        response_data = {
            "id": result.get("id"),
            "dataset_id": result.get("dataset_id"),
            "status": result.get("status"),
            "summary": summary,
            "auto_explore_used": auto_explore_used
        }
        
        # Adicionar a coluna target se disponível
        if result.get("target_column"):
            response_data["target_column"] = result.get("target_column")
        
        # Adicionar campos de data/hora se existirem
        if result.get('created_at'):
            response_data["created_at"] = result.get('created_at')
        
        if result.get('updated_at'):
            response_data["updated_at"] = result.get('updated_at')
        
        # Adicionar métricas de validação se existirem
        if validation_metrics:
            response_data["validation_metrics"] = validation_metrics
        
        return ProcessingResponse(**response_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter resultados de processamento: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Erro ao obter resultados de processamento: {str(e)}"
        )

@router.post("/process/auto", response_model=ProcessingResponse)
async def process_dataset_auto(
    config: ProcessingConfig,
    background_tasks: BackgroundTasks,
    processor_upload_service: ProcessorUploadService = Depends(get_processor_upload_service)
):
    """
    Endpoint para processamento com exploração automática de features ativada.
    Simplifica a criação de requisições que usam o Explorer sem precisar configurar
    manualmente os parâmetros.
    """
    try:
        if not config.dataset_id:
            raise HTTPException(
                status_code=400, 
                detail="O campo dataset_id é obrigatório"
            )
        
        # Forçar o modo de exploração automática
        config.use_auto_explore = True
        
        if not config.feature_selection:
            config.feature_selection = FeatureSelectionConfig(
                method="auto",
                auto_explore=True
            )
        else:
            config.feature_selection.method = "auto"
            config.feature_selection.auto_explore = True
        
        # Incluir target se informado
        target_info = ""
        if config.target_column:
            target_info = f" Coluna target: {config.target_column}."
            
        processing_id = await processor_upload_service.process_dataset(config)
        
        response = {
            "id": processing_id,
            "dataset_id": config.dataset_id,
            "status": "processing",
            "auto_explore_used": True,
            "summary": f"Processamento com exploração automática iniciado.{target_info} Use o endpoint /process/{processing_id} para verificar o status."
        }
        
        # Adicionar coluna target se disponível
        if config.target_column:
            response["target_column"] = config.target_column
        
        # Converter para o modelo
        return ProcessingResponse(**response)
    except Exception as e:
        logger.error(f"Erro ao iniciar processamento automático: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao iniciar processamento automático: {str(e)}")