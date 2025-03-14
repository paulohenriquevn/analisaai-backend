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
    """
    Serviço responsável por gerenciar operações de arquivo como upload, 
    processamento, análise e exclusão.
    """
    
    async def get_file_preview(self, file_id: str) -> Optional[FilePreview]:
        """
        Obtém a prévia de um arquivo processado
        
        Args:
            file_id: ID único do arquivo
            
        Returns:
            Objeto FilePreview ou None se o arquivo não for encontrado
        """
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
        """
        Obtém a análise detalhada de um arquivo processado
        
        Args:
            file_id: ID único do arquivo
            
        Returns:
            Objeto DataAnalysisResult ou None se o arquivo não for encontrado
        """
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
        """
        Lista os arquivos processados
        
        Args:
            limit: Número máximo de arquivos a retornar
            offset: Deslocamento para paginação
            
        Returns:
            Lista de objetos FileMetadata
        """
        result = []
        
        # Listar diretórios no UPLOAD_FOLDER (cada diretório representa um arquivo)
        dirs = [d for d in os.listdir(settings.UPLOAD_FOLDER) 
                if os.path.isdir(os.path.join(settings.UPLOAD_FOLDER, d))]
        
        # Ordenar por data de modificação (mais recentes primeiro)
        dirs.sort(key=lambda x: os.path.getmtime(os.path.join(settings.UPLOAD_FOLDER, x)), reverse=True)
        
        # Aplicar paginação
        dirs = dirs[offset:offset+limit]
        
        # Carregar metadados de cada arquivo
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
        """
        Remove um arquivo e seus dados processados
        
        Args:
            file_id: ID único do arquivo
            
        Returns:
            True se o arquivo foi removido com sucesso, False caso contrário
        """
        file_dir = os.path.join(settings.UPLOAD_FOLDER, file_id)
        if not os.path.exists(file_dir):
            return False
            
        try:
            # Remover arquivos de dados brutos
            for ext in settings.SUPPORTED_FILE_TYPES:
                file_path = os.path.join(settings.UPLOAD_FOLDER, f"{file_id}.{ext}")
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            # Remover diretório de metadados e resultados
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
        """
        Salva o arquivo enviado pelo usuário no sistema de arquivos
        
        Args:
            file: Arquivo enviado
            file_id: ID único gerado para o arquivo
            
        Returns:
            Caminho completo do arquivo salvo
        """
        file_extension = file.filename.split(".")[-1].lower()
        file_path = os.path.join(settings.UPLOAD_FOLDER, f"{file_id}.{file_extension}")
        
        # Salvar arquivo no sistema de arquivos
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
        """
        Processa o arquivo enviado, extraindo metadados e realizando análise inicial
        
        Args:
            file_path: Caminho do arquivo salvo
            file_id: ID único do arquivo
            file_name: Nome original do arquivo
            file_extension: Extensão do arquivo
            delimiter: Separador de colunas (para CSV)
            encoding: Encoding do arquivo
        """
        try:
            # Criar diretório para armazenar metadados e análise
            metadata_dir = os.path.join(settings.UPLOAD_FOLDER, file_id)
            os.makedirs(metadata_dir, exist_ok=True)
            
            # Carregar dados com base no tipo de arquivo
            if file_extension == 'csv':
                df = pd.read_csv(file_path, delimiter=delimiter, encoding=encoding, low_memory=False)
            elif file_extension in ['xlsx', 'xls']:
                df = pd.read_excel(file_path)
            elif file_extension == 'json':
                df = pd.read_json(file_path, encoding=encoding)
            else:
                raise ValueError(f"Tipo de arquivo não suportado: {file_extension}")
                
            # Gerar metadados do arquivo
            row_count = len(df)
            column_count = len(df.columns)
            
            # Salvar metadados
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
                delimiter=delimiter if file_extension == "csv" else None
            )
            
            # Salvar metadados em formato JSON
            metadata_path = os.path.join(metadata_dir, "metadata.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                f.write(metadata.json())
                
            # Gerar prévia do arquivo (primeiras 10 linhas)
            preview = self._generate_preview(df)
            preview_path = os.path.join(metadata_dir, "preview.json")
            with open(preview_path, 'w', encoding='utf-8') as f:
                f.write(preview.json())
                
            # Gerar análise de dados
            analysis = self._analyze_data(df)
            analysis_path = os.path.join(metadata_dir, "analysis.json")
            with open(analysis_path, 'w', encoding='utf-8') as f:
                f.write(analysis.json())
                
            logger.info(f"Arquivo {file_id} processado com sucesso.")
            
        except Exception as e:
            logger.error(f"Erro ao processar arquivo {file_id}: {str(e)}")
            
            # Em caso de erro, atualizar metadados para indicar falha
            metadata_dir = os.path.join(settings.UPLOAD_FOLDER, file_id)
            os.makedirs(metadata_dir, exist_ok=True)
            
            metadata = FileMetadata(
                id=file_id,
                filename=file_name,
                file_size=os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                upload_date=datetime.now(),
                file_type=file_extension,
                status="error",
                error_message=str(e)
            )
            
            # Salvar metadados com erro
            metadata_path = os.path.join(metadata_dir, "metadata.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                f.write(metadata.json())
    
    def _generate_preview(self, df: pd.DataFrame) -> FilePreview:
        """
        Gera uma prévia do DataFrame com as primeiras 10 linhas
        
        Args:
            df: DataFrame a ser analisado
            
        Returns:
            Objeto FilePreview com a prévia dos dados
        """
        # Obter as primeiras 10 linhas
        preview_df = df.head(10)
        
        # Converter para lista de dicionários (formato JSON-friendly)
        rows = preview_df.replace({np.nan: None}).to_dict('records')
        
        # Extrair informações das colunas
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
    
    def _analyze_data(self, df: pd.DataFrame) -> DataAnalysisResult:
        """
        Realiza análise detalhada do DataFrame
        
        Args:
            df: DataFrame a ser analisado
            
        Returns:
            Objeto DataAnalysisResult com a análise dos dados
        """
        # Identificar problemas nos dados
        issues = []
        
        # Verificar valores ausentes por coluna
        for col in df.columns:
            missing_count = df[col].isna().sum()
            if missing_count > 0:
                missing_percentage = (missing_count / len(df)) * 100
                issues.append(DataIssue(
                    type="missing_values",
                    description=f"A coluna '{col}' contém {missing_count} valores ausentes ({missing_percentage:.2f}%)",
                    severity="high" if missing_percentage > 20 else "medium" if missing_percentage > 5 else "low",
                    column=col,
                    suggestion="Considere remover as linhas com valores ausentes ou preencher com a média/moda"
                ))
        
        # Verificar se há duplicatas
        duplicate_count = df.duplicated().sum()
        if duplicate_count > 0:
            duplicate_percentage = (duplicate_count / len(df)) * 100
            issues.append(DataIssue(
                type="duplicates",
                description=f"O dataset contém {duplicate_count} linhas duplicadas ({duplicate_percentage:.2f}%)",
                severity="high" if duplicate_percentage > 10 else "medium" if duplicate_percentage > 1 else "low",
                suggestion="Considere remover as linhas duplicadas"
            ))
            
        # Estatísticas numéricas por coluna
        column_stats = {}
        for col in df.columns:
            try:
                if pd.api.types.is_numeric_dtype(df[col]):
                    stats = {
                        "min": float(df[col].min()) if not pd.isna(df[col].min()) else None,
                        "max": float(df[col].max()) if not pd.isna(df[col].max()) else None,
                        "mean": float(df[col].mean()) if not pd.isna(df[col].mean()) else None,
                        "median": float(df[col].median()) if not pd.isna(df[col].median()) else None,
                        "std": float(df[col].std()) if not pd.isna(df[col].std()) else None
                    }
                else:
                    unique_values = df[col].nunique()
                    unique_percentage = (unique_values / len(df)) * 100
                    stats = {
                        "unique_values": int(unique_values),
                        "unique_percentage": float(unique_percentage),
                        "most_common": df[col].value_counts().index[0] if not df[col].value_counts().empty else None
                    }
                    
                    # Verificar se coluna categórica tem muitos valores únicos
                    if unique_values > 50:
                        issues.append(DataIssue(
                            type="high_cardinality",
                            description=f"A coluna '{col}' tem alta cardinalidade ({unique_values} valores únicos)",
                            severity="medium",
                            column=col,
                            suggestion="Considere agrupar categorias menos frequentes"
                        ))
                
                column_stats[col] = stats
            except Exception as e:
                logger.warning(f"Erro ao calcular estatísticas para coluna {col}: {str(e)}")
                column_stats[col] = {"error": str(e)}
                
        # Verificar se o dataset é muito pequeno
        if len(df) < 50:
            issues.append(DataIssue(
                type="small_dataset",
                description=f"O dataset contém apenas {len(df)} linhas, o que pode ser insuficiente para treinamento",
                severity="high",
                suggestion="Considere coletar mais dados antes de prosseguir com o treinamento"
            ))
            
        # Verificar desbalanceamento em colunas com potencial de serem variáveis-alvo
        for col in df.columns:
            # Verificar apenas colunas categóricas com número limitado de valores únicos
            if not pd.api.types.is_numeric_dtype(df[col]) and df[col].nunique() <= 10:
                value_counts = df[col].value_counts(normalize=True)
                if value_counts.max() > 0.9:  # Se uma classe representa mais de 90% dos dados
                    issues.append(DataIssue(
                        type="imbalanced_target",
                        description=f"A coluna '{col}' está severamente desbalanceada (classe dominante: {value_counts.idxmax()} com {value_counts.max()*100:.2f}%)",
                        severity="high",
                        column=col,
                        suggestion="Para problemas de classificação, considere técnicas de balanceamento como oversampling ou undersampling"
                    ))
        
        return DataAnalysisResult(
            issues=issues,
            column_stats=column_stats,
            row_count=len(df),
            column_count=len(df.columns)
        )