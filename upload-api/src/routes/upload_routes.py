from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks, Depends, Header, Request
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
import uuid
import logging
import os
from datetime import datetime

from services.file_service import FileService
from services.validation_service import ValidationService
from models.file_metadata import FileMetadata, FilePreview, DataAnalysisResult
from config import settings

# Inicialização do logger
logger = logging.getLogger("upload-routes")

# Inicialização do router
router = APIRouter(tags=["Upload"])

# Injeções de dependência para serviços
def get_file_service():
    return FileService()

def get_validation_service():
    return ValidationService()

@router.post("/upload", response_model=FileMetadata)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    delimiter: Optional[str] = Form(","),
    encoding: Optional[str] = Form(None),
    file_service: FileService = Depends(get_file_service),
    validation_service: ValidationService = Depends(get_validation_service),
):
    """
    Endpoint para upload de arquivos de dados (CSV, Excel, JSON)
    
    Args:
        file: Arquivo enviado pelo usuário
        delimiter: Separador de colunas (para CSV)
        encoding: Encoding do arquivo (UTF-8 como padrão)
        
    Returns:
        Metadados do arquivo processado incluindo ID único
    """
    # Validar tamanho do arquivo
    if file.size and file.size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413, 
            detail=f"Arquivo muito grande. O tamanho máximo permitido é {settings.MAX_FILE_SIZE/1024/1024} MB"
        )
    
    # Validar tipo de arquivo
    file_extension = file.filename.split(".")[-1].lower()
    if file_extension not in settings.SUPPORTED_FILE_TYPES:
        raise HTTPException(
            status_code=415, 
            detail=f"Tipo de arquivo não suportado. Os tipos suportados são: {', '.join(settings.SUPPORTED_FILE_TYPES)}"
        )
    
    try:
        # Gerar ID único para o arquivo
        file_id = str(uuid.uuid4())
        
        # Se não for fornecido encoding, tenta detectar automaticamente
        if not encoding:
            encoding = await validation_service.detect_encoding(file)
            if not encoding:
                encoding = settings.DEFAULT_ENCODING
                logger.info(f"Encoding não detectado, usando padrão: {encoding}")
                
        # Se for um CSV, tenta detectar o delimitador automaticamente
        if file_extension == "csv" and delimiter == ",":
            detected_delimiter = await validation_service.detect_delimiter(file, encoding)
            if detected_delimiter:
                delimiter = detected_delimiter
                logger.info(f"Delimitador detectado: {delimiter}")
        
        # Salvar arquivo
        file_path = await file_service.save_file(file, file_id)
        
        # Processar arquivo em background
        background_tasks.add_task(
            file_service.process_file,
            file_path=file_path,
            file_id=file_id,
            file_name=file.filename,
            file_extension=file_extension,
            delimiter=delimiter,
            encoding=encoding
        )
        
        # Retornar metadados iniciais
        return FileMetadata(
            id=file_id,
            filename=file.filename,
            file_size=file.size,
            upload_date=datetime.now(),
            file_type=file_extension,
            status="processing",
            encoding=encoding,
            delimiter=delimiter if file_extension == "csv" else None
        )
        
    except Exception as e:
        logger.error(f"Erro durante upload do arquivo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar arquivo: {str(e)}")

@router.get("/files/{file_id}/preview", response_model=FilePreview)
async def get_file_preview(
    file_id: str,
    file_service: FileService = Depends(get_file_service)
):
    """
    Obtém uma prévia do arquivo carregado
    
    Args:
        file_id: ID único do arquivo
        
    Returns:
        Prévia das primeiras linhas do arquivo e informações de colunas
    """
    try:
        preview = await file_service.get_file_preview(file_id)
        if not preview:
            raise HTTPException(status_code=404, detail="Arquivo não encontrado ou ainda em processamento")
        return preview
    except Exception as e:
        logger.error(f"Erro ao obter prévia do arquivo {file_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar prévia: {str(e)}")

@router.get("/files/{file_id}/analysis", response_model=DataAnalysisResult)
async def get_file_analysis(
    file_id: str,
    file_service: FileService = Depends(get_file_service)
):
    """
    Obtém análise detalhada do arquivo carregado
    
    Args:
        file_id: ID único do arquivo
        
    Returns:
        Análise detalhada incluindo estatísticas e problemas identificados
    """
    try:
        analysis = await file_service.get_file_analysis(file_id)
        if not analysis:
            raise HTTPException(status_code=404, detail="Arquivo não encontrado ou análise não disponível")
        return analysis
    except Exception as e:
        logger.error(f"Erro ao obter análise do arquivo {file_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar análise: {str(e)}")

@router.get("/files", response_model=List[FileMetadata])
async def list_files(
    limit: int = 10,
    offset: int = 0,
    file_service: FileService = Depends(get_file_service)
):
    """
    Lista arquivos carregados pelo usuário
    
    Args:
        limit: Número máximo de arquivos a retornar
        offset: Deslocamento para paginação
        
    Returns:
        Lista de metadados de arquivos
    """
    try:
        files = await file_service.list_files(limit, offset)
        return files
    except Exception as e:
        logger.error(f"Erro ao listar arquivos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar arquivos: {str(e)}")

@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    file_service: FileService = Depends(get_file_service)
):
    """
    Remove um arquivo e seus dados processados
    
    Args:
        file_id: ID único do arquivo
        
    Returns:
        Confirmação de remoção
    """
    try:
        success = await file_service.delete_file(file_id)
        if not success:
            raise HTTPException(status_code=404, detail="Arquivo não encontrado")
        return {"message": "Arquivo removido com sucesso", "file_id": file_id}
    except Exception as e:
        logger.error(f"Erro ao remover arquivo {file_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao remover arquivo: {str(e)}")