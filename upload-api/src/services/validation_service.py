import logging
import chardet
import csv
from fastapi import UploadFile
from io import StringIO, BytesIO
import pandas as pd
from typing import Optional, List, Dict, Any

logger = logging.getLogger("validation-service")

class ValidationService:

    async def detect_encoding(self, file: UploadFile) -> Optional[str]:
        try:
            sample = await file.read(min(1024 * 1024, file.size or 1024 * 1024))  # Ler no máximo 1MB
            
            detection = chardet.detect(sample)
            
            await file.seek(0)
            
            if detection and detection['confidence'] > 0.7:
                logger.info(f"Encoding detectado: {detection['encoding']} (confiança: {detection['confidence']})")
                return detection['encoding']
            else:
                logger.warning(f"Encoding não detectado com confiança suficiente: {detection}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao detectar encoding: {str(e)}")
            try:
                await file.seek(0)
            except:
                pass
            return None
    
    async def detect_delimiter(self, file: UploadFile, encoding: str = 'utf-8') -> Optional[str]:
        try:
            sample_bytes = await file.read(min(1024 * 100, file.size or 1024 * 100))  # Ler no máximo 100KB
            sample = sample_bytes.decode(encoding)
            
            await file.seek(0)
            
            delimiters = [',', ';', '\t', '|']
            counts = {}
            
            for delimiter in delimiters:
                try:
                    lines = sample.split('\n')[:10]
                    if not lines:
                        continue
                        
                    reader = csv.reader(lines, delimiter=delimiter)
                    rows = list(reader)
                    
                    if not rows:
                        continue
                        
                    first_row_cols = 0
                    for row in rows:
                        if row:
                            first_row_cols = len(row)
                            break
                    
                    if first_row_cols <= 1:
                        continue
                    
                    consistent_rows = 0
                    for row in rows:
                        if len(row) == first_row_cols:
                            consistent_rows += 1
                    
                    if rows:
                        consistency = consistent_rows / len(rows)
                        counts[delimiter] = {
                            'columns': first_row_cols,
                            'consistency': consistency
                        }
                except Exception as e:
                    logger.warning(f"Erro ao testar delimitador '{delimiter}': {str(e)}")
            
            best_delimiter = None
            best_score = 0
            
            for delimiter, stats in counts.items():
                score = stats['consistency'] * stats['columns']
                if score > best_score:
                    best_score = score
                    best_delimiter = delimiter
            
            if best_delimiter:
                logger.info(f"Delimitador detectado: '{best_delimiter}' (score: {best_score})")
                return best_delimiter
            else:
                logger.warning("Não foi possível detectar um delimitador confiável")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao detectar delimitador: {str(e)}")
            try:
                await file.seek(0)
            except:
                pass
            return None
    
    async def validate_file_structure(self, file: UploadFile, file_extension: str, encoding: str = 'utf-8', delimiter: str = ',') -> Dict[str, Any]:
        result = {
            "is_valid": False,
            "errors": [],
            "warnings": [],
            "column_count": 0,
            "row_sample_count": 0
        }
        
        try:
            sample_bytes = await file.read(min(1024 * 100, file.size or 1024 * 100))  # Ler no máximo 100KB
            
            await file.seek(0)
            
            if file_extension == 'csv':
                try:
                    sample = sample_bytes.decode(encoding)
                    sample_io = StringIO(sample)
                    df = pd.read_csv(sample_io, delimiter=delimiter, nrows=100)
                    
                    result["is_valid"] = True
                    result["column_count"] = len(df.columns)
                    result["row_sample_count"] = len(df)
                    
                    duplicated_headers = df.columns[df.columns.duplicated()].tolist()
                    if duplicated_headers:
                        result["warnings"].append(f"O arquivo contém cabeçalhos duplicados: {', '.join(duplicated_headers)}")
                    
                except Exception as e:
                    result["errors"].append(f"Erro ao processar CSV: {str(e)}")
            
            elif file_extension in ['xlsx', 'xls']:
                try:
                    sample_io = BytesIO(sample_bytes)
                    df = pd.read_excel(sample_io, nrows=100)
                    
                    result["is_valid"] = True
                    result["column_count"] = len(df.columns)
                    result["row_sample_count"] = len(df)
                    
                    duplicated_headers = df.columns[df.columns.duplicated()].tolist()
                    if duplicated_headers:
                        result["warnings"].append(f"O arquivo contém cabeçalhos duplicados: {', '.join(duplicated_headers)}")
                    
                except Exception as e:
                    result["errors"].append(f"Erro ao processar Excel: {str(e)}")
            
            elif file_extension == 'json':
                try:
                    sample = sample_bytes.decode(encoding)
                    df = pd.read_json(StringIO(sample))
                    
                    result["is_valid"] = True
                    result["column_count"] = len(df.columns)
                    result["row_sample_count"] = len(df)
                    
                except Exception as e:
                    result["errors"].append(f"Erro ao processar JSON: {str(e)}")
            
            else:
                result["errors"].append(f"Tipo de arquivo não suportado: {file_extension}")
            
        except Exception as e:
            result["errors"].append(f"Erro ao validar arquivo: {str(e)}")
            try:
                await file.seek(0)
            except:
                pass
        
        return result