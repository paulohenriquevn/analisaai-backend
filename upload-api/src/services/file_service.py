import os
import logging
import pandas as pd
import json
import uuid
from typing import Dict, List, Any, Optional, Tuple
from fastapi import UploadFile
from datetime import datetime
import chardet
import aiofiles
import asyncio
import numpy as np

from config import settings
from models.file_metadata import FileMetadata, FilePreview, DataAnalysisResult, ColumnInfo, DataIssue
from database.db import is_dataset_name_unique, save_dataset

logger = logging.getLogger("file-service")

class FileService:

    async def get_file_preview(self, file_id: str) -> Optional[FilePreview]:

        preview_path = os.path.join(settings.UPLOAD_FOLDER, file_id, "preview.json")
        if not os.path.exists(preview_path):
            return None
            
        try:
            with open(preview_path, 'r', encoding='utf-8') as f:
                preview_json = f.read()
                return FilePreview.parse_raw(preview_json)
        except Exception as e:
            logger.error(f"Erro ao ler prévia do arquivo {file_id}: {str(e)}")
            return None
    
    async def list_files(self, limit: int = 10, offset: int = 0) -> List[FileMetadata]:

        result = []
        
        dirs = [d for d in os.listdir(settings.UPLOAD_FOLDER) 
                if os.path.isdir(os.path.join(settings.UPLOAD_FOLDER, d))]
        
        dirs.sort(key=lambda x: os.path.getmtime(os.path.join(settings.UPLOAD_FOLDER, x)), reverse=True)
        
        dirs = dirs[offset:offset+limit]
        
        for dir_name in dirs:
            metadata_path = os.path.join(settings.UPLOAD_FOLDER, dir_name, "metadata.json")
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata_json = f.read()
                        metadata = FileMetadata.parse_raw(metadata_json)
                        result.append(metadata)
                except Exception as e:
                    logger.error(f"Erro ao ler metadados do arquivo {dir_name}: {str(e)}")
        
        return result
    
    async def delete_file(self, file_id: str) -> bool:

        file_dir = os.path.join(settings.UPLOAD_FOLDER, file_id)
        if not os.path.exists(file_dir):
            return False
            
        try:
            for ext in settings.SUPPORTED_FILE_TYPES:
                file_path = os.path.join(settings.UPLOAD_FOLDER, f"{file_id}.{ext}")
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            for root, dirs, files in os.walk(file_dir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(file_dir)
            
            logger.info(f"Arquivo {file_id} removido com sucesso")
            return True
        except Exception as e:
            logger.error(f"Erro ao remover arquivo {file_id}: {str(e)}")
            return False
    
    async def save_file(self, file: UploadFile, file_id: str) -> str:
        file_extension = file.filename.split(".")[-1].lower()
        file_path = os.path.join(settings.UPLOAD_FOLDER, f"{file_id}.{file_extension}")
        
        async with aiofiles.open(file_path, 'wb') as out_file:
            content = await file.read()
            await out_file.write(content)
            
        logger.info(f"Arquivo salvo: {file_path}")
        return file_path
    
    async def process_file(
        self, 
        file_path: str, 
        file_id: str, 
        file_name: str, 
        file_extension: str,
        delimiter: str = ",",
        encoding: str = "utf-8"
    ) -> None:
        try:
            metadata_dir = os.path.join(settings.UPLOAD_FOLDER, file_id)
            os.makedirs(metadata_dir, exist_ok=True)
            
            if file_extension == 'csv':
                df = pd.read_csv(file_path, delimiter=delimiter, encoding=encoding, low_memory=False)
            elif file_extension in ['xlsx', 'xls']:
                df = pd.read_excel(file_path)
            elif file_extension == 'json':
                df = pd.read_json(file_path, encoding=encoding)
            else:
                raise ValueError(f"Tipo de arquivo não suportado: {file_extension}")
                
            row_count = len(df)
            column_count = len(df.columns)
            
            metadata = FileMetadata(
                id=file_id,
                filename=file_name,
                file_size=os.path.getsize(file_path),
                upload_date=datetime.now(),
                file_type=file_extension,
                status="processed",
                row_count=row_count,
                column_count=column_count,
                encoding=encoding,
                delimiter=delimiter if file_extension == "csv" else None,
                confirmed=False
            )
            
            metadata_path = os.path.join(metadata_dir, "metadata.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                f.write(metadata.json())
                
            preview = self._generate_preview(df)
            preview_path = os.path.join(metadata_dir, "preview.json")
            with open(preview_path, 'w', encoding='utf-8') as f:
                f.write(preview.json())
                
            logger.info(f"Arquivo {file_id} processado com sucesso.")
            
        except Exception as e:
            logger.error(f"Erro ao processar arquivo {file_id}: {str(e)}")
            
            metadata_dir = os.path.join(settings.UPLOAD_FOLDER, file_id)
            os.makedirs(metadata_dir, exist_ok=True)
            
            metadata = FileMetadata(
                id=file_id,
                filename=file_name,
                file_size=os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                upload_date=datetime.now(),
                file_type=file_extension,
                status="error",
                error_message=str(e),
                confirmed=False
            )
            
            metadata_path = os.path.join(metadata_dir, "metadata.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                f.write(metadata.json())
    
    def _generate_preview(self, df: pd.DataFrame) -> FilePreview:

        preview_df = df.head(10)
        
        rows = preview_df.replace({np.nan: None}).to_dict('records')
        
        columns = []
        for col in df.columns:
            dtype = str(df[col].dtype)
            missing_count = df[col].isna().sum()
            missing_percentage = (missing_count / len(df)) * 100
            
            columns.append(ColumnInfo(
                name=col,
                data_type=dtype,
                missing_count=missing_count,
                missing_percentage=missing_percentage
            ))
        
        return FilePreview(
            columns=columns,
            rows=rows,
            total_rows=len(df)
        )
    
    async def confirm_upload(self, file_id: str, dataset_name: str, description: Optional[str] = None) -> Optional[FileMetadata]:

        metadata_path = os.path.join(settings.UPLOAD_FOLDER, file_id, "metadata.json")
        
        print("metadata_path", metadata_path)
        if not os.path.exists(metadata_path):
            logger.error(f"Arquivo {file_id} não encontrado para confirmação")
            return None
            
        try:
            if not await is_dataset_name_unique(dataset_name):
                raise ValueError(f"O nome de dataset '{dataset_name}' já está em uso. Por favor, escolha outro nome.")
            
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata_json = f.read()
                metadata = FileMetadata.parse_raw(metadata_json)
            
            if metadata.confirmed:
                logger.info(f"Arquivo {file_id} já foi confirmado anteriormente")
                return metadata
                
            if metadata.status == "error":
                logger.error(f"Não é possível confirmar arquivo {file_id} com status de erro")
                return None
                
            metadata.confirmed = True
            metadata.dataset_name = dataset_name
            
            dataset_data = {
                "id": file_id,
                "name": dataset_name,
                "filename": metadata.filename,
                "file_type": metadata.file_type,
                "file_size": metadata.file_size,
                "row_count": metadata.row_count,
                "column_count": metadata.column_count,
                "created_at": metadata.upload_date,
                "updated_at": datetime.now(),
                "status": metadata.status,
                "description": description
            }
            
            await save_dataset(dataset_data)
            
            # Atualizar o arquivo de metadados
            with open(metadata_path, 'w', encoding='utf-8') as f:
                f.write(metadata.json())
                
            logger.info(f"Arquivo {file_id} confirmado com sucesso como dataset '{dataset_name}'")
            
            return metadata
            
        except ValueError as e:
            logger.error(f"Erro de validação: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Erro ao confirmar arquivo {file_id}: {str(e)}")
            raise