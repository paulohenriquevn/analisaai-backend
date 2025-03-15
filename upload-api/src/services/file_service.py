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
    
    async def get_file_analysis(self, file_id: str) -> Optional[DataAnalysisResult]:

        analysis_path = os.path.join(settings.UPLOAD_FOLDER, file_id, "analysis.json")
        if not os.path.exists(analysis_path):
            return None
            
        try:
            with open(analysis_path, 'r', encoding='utf-8') as f:
                analysis_json = f.read()
                return DataAnalysisResult.parse_raw(analysis_json)
        except Exception as e:
            logger.error(f"Erro ao ler análise do arquivo {file_id}: {str(e)}")
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
                
            analysis = self._analyze_data(df)
            analysis_path = os.path.join(metadata_dir, "analysis.json")
            with open(analysis_path, 'w', encoding='utf-8') as f:
                f.write(analysis.json())
                
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
    
    async def confirm_upload(self, file_id: str) -> Optional[FileMetadata]:
        """
        Confirma o upload de um arquivo e inicia seu processamento
        
        Args:
            file_id: ID único do arquivo
            
        Returns:
            Objeto FileMetadata atualizado ou None se o arquivo não for encontrado
        """
        metadata_dir = os.path.join(settings.UPLOAD_FOLDER, file_id)
        metadata_path = os.path.join(metadata_dir, "metadata.json")
        
        if not os.path.exists(metadata_path):
            logger.error(f"Arquivo {file_id} não encontrado para confirmação")
            return None
            
        try:
            # Carregar metadados atuais
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata_json = f.read()
                metadata = FileMetadata.parse_raw(metadata_json)
            
            # Verificar se o arquivo já foi confirmado
            if metadata.confirmed:
                logger.info(f"Arquivo {file_id} já foi confirmado anteriormente")
                return metadata
                
            # Verificar se o arquivo não está em estado de erro
            if metadata.status == "error":
                logger.error(f"Não é possível confirmar arquivo {file_id} com status de erro")
                return None
                
            # Atualizar status e flag de confirmação
            metadata.confirmed = True
            # Se já estiver em processamento ou processado, apenas atualiza o flag de confirmação
            with open(metadata_path, 'w', encoding='utf-8') as f:
                f.write(metadata.json())
                
            logger.info(f"Arquivo {file_id} confirmado com sucesso")
            
            return metadata
            
        except Exception as e:
            logger.error(f"Erro ao confirmar arquivo {file_id}: {str(e)}")
            return None