import logging
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List, Optional, Dict, Any

from models.processing_models import (
    ProcessingConfig, ProcessingResult, ProcessingResponse,
    MissingValuesConfig, OutliersConfig, ScalingConfig,
    EncodingConfig, FeatureSelectionConfig
)
from services.processor_service import ProcessorService

logger = logging.getLogger("processor-routes")

router = APIRouter(tags=["Processamento"])

def get_processor_service():
    return ProcessorService()


@router.post("/process", response_model=ProcessingResponse)
async def process_dataset(
    config: ProcessingConfig,
    background_tasks: BackgroundTasks,
    processor_service: ProcessorService = Depends(get_processor_service)
):
    try:
        if not config.dataset_id:
            raise HTTPException(
                status_code=400, 
                detail="O campo dataset_id é obrigatório"
            )
            
        processing_id = await processor_service.process_dataset(config)
        
        response = {
            "id": processing_id,
            "dataset_id": config.dataset_id,
            "status": "processing",
            "summary": "Processamento iniciado. Use o endpoint /process/{processing_id} para verificar o status."
        }
        
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
        
        # Formatar métricas de validação
        validation_metrics = processor_service.format_validation_metrics(result.validation_results)
        
        # Gerar resumo baseado no status
        summary = ""
        if result.status == "completed":
            transformed_features = len(result.transformations_applied) if result.transformations_applied else 0
            missing_values = len(result.missing_values_report) if result.missing_values_report else 0
            outliers = len(result.outliers_report) if result.outliers_report else 0
            
            summary = (
                f"Processamento concluído com sucesso. "
                f"{transformed_features} transformações aplicadas, "
                f"{missing_values} colunas com valores ausentes tratados, "
                f"{outliers} colunas com outliers tratados."
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
        elif result.status == "error":
            summary = f"Erro durante o processamento: {result.error_message}"
        else:
            summary = "Processamento em andamento..."
        
        # Preparar resposta
        response_data = {
            "id": result.id,
            "dataset_id": result.dataset_id,
            "status": result.status,
            "summary": summary,
        }
        
        # Adicionar campos de data/hora se existirem
        if hasattr(result, 'created_at') and result.created_at:
            response_data["created_at"] = result.created_at
        
        if hasattr(result, 'updated_at') and result.updated_at:
            response_data["updated_at"] = result.updated_at
        
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


@router.get("/process/{processing_id}/full", response_model=ProcessingResult)
async def get_full_processing_result(
    processing_id: str,
    processor_service: ProcessorService = Depends(get_processor_service)
):
    try:
        result = await processor_service.get_processing_results(processing_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Processamento não encontrado")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter resultados completos de processamento: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Erro ao obter resultados completos de processamento: {str(e)}"
        )


@router.get("/process/dataset/{dataset_id}", response_model=ProcessingResponse)
async def get_dataset_processing(
    dataset_id: str,
    processor_service: ProcessorService = Depends(get_processor_service)
):
    try:
        # No futuro, implementar a busca pelo processamento mais recente de um dataset
        raise HTTPException(
            status_code=501, 
            detail="Funcionalidade ainda não implementada"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter processamento do dataset: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Erro ao obter processamento do dataset: {str(e)}"
        )


@router.get("/process/{processing_id}/missing-values", response_model=List[Dict[str, Any]])
async def get_missing_values_report(
    processing_id: str,
    processor_service: ProcessorService = Depends(get_processor_service)
):
    try:
        result = await processor_service.get_processing_results(processing_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Processamento não encontrado")
        
        if not result.missing_values_report:
            return []
        
        return [report.dict() for report in result.missing_values_report]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter relatório de valores ausentes: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Erro ao obter relatório de valores ausentes: {str(e)}"
        )


@router.get("/process/{processing_id}/outliers", response_model=List[Dict[str, Any]])
async def get_outliers_report(
    processing_id: str,
    processor_service: ProcessorService = Depends(get_processor_service)
):
    try:
        result = await processor_service.get_processing_results(processing_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Processamento não encontrado")
        
        if not result.outliers_report:
            return []
        
        return [report.dict() for report in result.outliers_report]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter relatório de outliers: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Erro ao obter relatório de outliers: {str(e)}"
        )


@router.get("/process/{processing_id}/feature-importance", response_model=List[Dict[str, Any]])
async def get_feature_importance(
    processing_id: str,
    processor_service: ProcessorService = Depends(get_processor_service)
):
    try:
        result = await processor_service.get_processing_results(processing_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Processamento não encontrado")
        
        if not result.feature_importance:
            return []
        
        return [feature.dict() for feature in result.feature_importance]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter importância das features: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Erro ao obter importância das features: {str(e)}"
        )


@router.get("/process/{processing_id}/transformations", response_model=List[Dict[str, Any]])
async def get_transformations(
    processing_id: str,
    processor_service: ProcessorService = Depends(get_processor_service)
):
    try:
        result = await processor_service.get_processing_results(processing_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Processamento não encontrado")
        
        if not result.transformations_applied:
            return []
        
        return [transform.dict() for transform in result.transformations_applied]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter transformações: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Erro ao obter transformações: {str(e)}"
        )