import uuid
import logging

from datetime import datetime
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks, Depends
from typing import Optional, List
from services.file_service import FileService
from services.validation_service import ValidationService
from models.file_metadata import FileMetadata, FilePreview
from config import settings

logger = logging.getLogger("upload-routes")

router = APIRouter(tags=["Upload"])

class DatasetConfirmation(BaseModel):
    dataset_name: str
    description: Optional[str] = None

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

    if file.size and file.size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413, 
            detail=f"Arquivo muito grande. O tamanho máximo permitido é {settings.MAX_FILE_SIZE/1024/1024} MB"
        )
    
    file_extension = file.filename.split(".")[-1].lower()
    if file_extension not in settings.SUPPORTED_FILE_TYPES:
        raise HTTPException(
            status_code=415, 
            detail=f"Tipo de arquivo não suportado. Os tipos suportados são: {', '.join(settings.SUPPORTED_FILE_TYPES)}"
        )
    
    try:
        file_id = str(uuid.uuid4())
        
        if not encoding:
            encoding = await validation_service.detect_encoding(file)
            if not encoding:
                encoding = settings.DEFAULT_ENCODING
                logger.info(f"Encoding não detectado, usando padrão: {encoding}")
                
        if file_extension == "csv" and delimiter == ",":
            detected_delimiter = await validation_service.detect_delimiter(file, encoding)
            if detected_delimiter:
                delimiter = detected_delimiter
                logger.info(f"Delimitador detectado: {delimiter}")
        
        file_path = await file_service.save_file(file, file_id)
        
        background_tasks.add_task(
            file_service.process_file,
            file_path=file_path,
            file_id=file_id,
            file_name=file.filename,
            file_extension=file_extension,
            delimiter=delimiter,
            encoding=encoding
        )
        
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
    try:
        preview = await file_service.get_file_preview(file_id)
        if not preview:
            raise HTTPException(status_code=404, detail="Arquivo não encontrado ou ainda em processamento")
        return preview
    except Exception as e:
        logger.error(f"Erro ao obter prévia do arquivo {file_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar prévia: {str(e)}")

@router.get("/files", response_model=List[FileMetadata])
async def list_files(
    limit: int = 10,
    offset: int = 0,
    file_service: FileService = Depends(get_file_service)
):
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
    try:
        success = await file_service.delete_file(file_id)
        if not success:
            raise HTTPException(status_code=404, detail="Arquivo não encontrado")
        return {"message": "Arquivo removido com sucesso", "file_id": file_id}
    except Exception as e:
        logger.error(f"Erro ao remover arquivo {file_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao remover arquivo: {str(e)}")
    

@router.post("/files/{file_id}/confirm", response_model=FileMetadata)
async def confirm_file_upload(
    file_id: str,
    confirmation: DatasetConfirmation,
    file_service: FileService = Depends(get_file_service)
):
    try:
        metadata = await file_service.confirm_upload(file_id, confirmation.dataset_name, confirmation.description)
        if not metadata:
            raise HTTPException(status_code=404, detail="Arquivo não encontrado")
        return metadata
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Erro de validação ao confirmar upload do arquivo {file_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao confirmar upload do arquivo {file_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao confirmar upload: {str(e)}")