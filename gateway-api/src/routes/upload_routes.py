import io
import httpx
import logging
from pydantic import BaseModel
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request, status


from config import settings


logger = logging.getLogger("upload-routes")


router = APIRouter()

class DatasetConfirmation(BaseModel):
    dataset_name: str
    description: Optional[str] = None

async def forward_request(url: str, method: str, headers: Dict[str, str] = None, 
                          params: Dict[str, Any] = None, data: Dict[str, Any] = None, 
                          files: Dict[str, Any] = None, json: Dict[str, Any] = None,
                          timeout: int = settings.DEFAULT_TIMEOUT):
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                data=data,
                files=files,
                json=json
            )
            
            return {
                "status_code": response.status_code,
                "content": response.json() if response.headers.get("content-type") == "application/json" else response.text,
                "headers": dict(response.headers)
            }
    except httpx.RequestError as e:
        logger.error(f"Erro ao encaminhar requisição para {url}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Serviço não disponível: {str(e)}"
        )
    except httpx.TimeoutException as e:
        logger.error(f"Timeout ao encaminhar requisição para {url}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Timeout na requisição: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Erro não esperado ao encaminhar requisição para {url}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {str(e)}"
        )


@router.post("/", tags=["Upload"])
async def post_upload_file(
    request: Request,
    file: UploadFile = File(...),
    delimiter: Optional[str] = Form(","),
    encoding: Optional[str] = Form(None)
):

    target_url = f"{settings.UPLOAD_API_URL}/api/v1/upload"
    
    try:

        headers = {
            "Accept": request.headers.get("Accept", "application/json"),
            "Accept-Language": request.headers.get("Accept-Language", "pt-BR"),
            "User-Agent": request.headers.get("User-Agent", "AnalisaAI-Gateway")
        }

        if "Authorization" in request.headers:
            headers["Authorization"] = request.headers["Authorization"]
        
        file_content = await file.read()
        files = {
            "file": (file.filename, io.BytesIO(file_content), file.content_type)
        }
        
        form_data = {}
        if delimiter:
            form_data["delimiter"] = delimiter
        if encoding:
            form_data["encoding"] = encoding
        
        response = await forward_request(
            url=target_url,
            method="POST",
            headers=headers,
            data=form_data,
            files=files
        )
        
        return response["content"]
    except Exception as e:
        logger.error(f"Erro ao processar upload: {str(e)}")
        raise


@router.get("/files/{file_id}/preview", tags=["Upload"])
async def get_file_preview(
    request: Request,
    file_id: str,
):
    target_url = f"{settings.UPLOAD_API_URL}/api/v1/files/{file_id}/preview"
    
    try:
        headers = {
            "Accept": request.headers.get("Accept", "application/json"),
            "Accept-Language": request.headers.get("Accept-Language", "pt-BR"),
            "User-Agent": request.headers.get("User-Agent", "AnalisaAI-Gateway")
        }
        
        if "Authorization" in request.headers:
            headers["Authorization"] = request.headers["Authorization"]
        
        response = await forward_request(
            url=target_url,
            method="GET",
            headers=headers,
        )
        
        return response["content"]
    except Exception as e:
        logger.error(f"Erro ao preview: {str(e)}")
        raise


@router.get("/files", tags=["Upload"])
async def get_list_files(
    request: Request,
    limit: int = 10,
    offset: int = 0
):

    target_url = f"{settings.UPLOAD_API_URL}/api/v1/files"
    
    try:
        headers = {
            "Accept": request.headers.get("Accept", "application/json"),
            "Accept-Language": request.headers.get("Accept-Language", "pt-BR"),
            "User-Agent": request.headers.get("User-Agent", "AnalisaAI-Gateway")
        }
        
        if "Authorization" in request.headers:
            headers["Authorization"] = request.headers["Authorization"]
        
        response = await forward_request(
            url=target_url,
            method="GET",
            headers=headers,
            params={"limit": limit, "offset": offset}
        )
        
        return response["content"]
    except Exception as e:
        logger.error(f"Erro ao listar arquivos: {str(e)}")
        raise


@router.delete("/files/{file_id}", tags=["Upload"])
async def delete_file(
    request: Request,
    file_id: str
):
    target_url = f"{settings.UPLOAD_API_URL}/api/v1/files/{file_id}"
    
    # Encaminhar requisição para o serviço de upload
    try:
        # Coletar cabeçalhos relevantes
        headers = {
            "Accept": request.headers.get("Accept", "application/json"),
            "Accept-Language": request.headers.get("Accept-Language", "pt-BR"),
            "User-Agent": request.headers.get("User-Agent", "AnalisaAI-Gateway")
        }
        
        # Se houver token de autenticação, encaminhar
        if "Authorization" in request.headers:
            headers["Authorization"] = request.headers["Authorization"]
        
        # Encaminhar requisição
        response = await forward_request(
            url=target_url,
            method="DELETE",
            headers=headers
        )
        
        # Retornar resposta com o status code original
        return response["content"]
    except Exception as e:
        logger.error(f"Erro ao remover arquivo: {str(e)}")
        raise


@router.post("/files/{file_id}/confirm", tags=["Upload"])
async def post_confirm_file_upload(
    request: Request,
    file_id: str,
    confirmation: DatasetConfirmation,
):
    target_url = f"{settings.UPLOAD_API_URL}/api/v1/files/{file_id}/confirm"
    
    try:
        headers = {
            "Accept": request.headers.get("Accept", "application/json"),
            "Accept-Language": request.headers.get("Accept-Language", "pt-BR"),
            "User-Agent": request.headers.get("User-Agent", "AnalisaAI-Gateway")
        }
        
        if "Authorization" in request.headers:
            headers["Authorization"] = request.headers["Authorization"]
        
        response = await forward_request(
            url=target_url,
            method="POST",
            headers=headers,
            json=confirmation.dict()
        )
        
        return response["content"]
    except Exception as e:
        logger.error(f"Erro ao confirma o upload do arquivo: {str(e)}")
        raise
