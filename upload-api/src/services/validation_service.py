import logging
import chardet
import csv
from fastapi import UploadFile
from io import StringIO, BytesIO
import pandas as pd
from typing import Optional, List, Dict, Any

logger = logging.getLogger("validation-service")

class ValidationService:
    """
    Serviço responsável por validar e detectar propriedades 
    de arquivos de dados antes do processamento
    """
    
    async def detect_encoding(self, file: UploadFile) -> Optional[str]:
        """
        Detecta o encoding de um arquivo
        
        Args:
            file: Arquivo a ser analisado
            
        Returns:
            String com o encoding detectado ou None se não for possível detectar
        """
        try:
            # Salvar posição atual do cursor do arquivo
            current_position = file.file.tell()
            
            # Ler um trecho do arquivo para detecção
            sample = await file.read(min(1024 * 1024, file.size or 1024 * 1024))  # Ler no máximo 1MB
            
            # Detectar encoding
            detection = chardet.detect(sample)
            
            # Restaurar posição do cursor
            await file.seek(0)
            
            if detection and detection['confidence'] > 0.7:
                logger.info(f"Encoding detectado: {detection['encoding']} (confiança: {detection['confidence']})")
                return detection['encoding']
            else:
                logger.warning(f"Encoding não detectado com confiança suficiente: {detection}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao detectar encoding: {str(e)}")
            # Tentar restaurar posição do cursor em caso de erro
            try:
                await file.seek(0)
            except:
                pass
            return None
    
    async def detect_delimiter(self, file: UploadFile, encoding: str = 'utf-8') -> Optional[str]:
        """
        Detecta o delimitador de um arquivo CSV
        
        Args:
            file: Arquivo CSV a ser analisado
            encoding: Encoding do arquivo
            
        Returns:
            String com o delimitador detectado ou None se não for possível detectar
        """
        try:
            # Salvar posição atual do cursor do arquivo
            current_position = file.file.tell()
            
            # Ler um trecho do arquivo para detecção
            sample_bytes = await file.read(min(1024 * 100, file.size or 1024 * 100))  # Ler no máximo 100KB
            sample = sample_bytes.decode(encoding)
            
            # Restaurar posição do cursor
            await file.seek(0)
            
            # Verificar delimitadores comuns
            delimiters = [',', ';', '\t', '|']
            counts = {}
            
            for delimiter in delimiters:
                # Contar número de colunas consistentes
                try:
                    lines = sample.split('\n')[:10]  # Analisar até 10 primeiras linhas
                    if not lines:
                        continue
                        
                    reader = csv.reader(lines, delimiter=delimiter)
                    rows = list(reader)
                    
                    if not rows:
                        continue
                        
                    # Contar colunas na primeira linha não vazia
                    first_row_cols = 0
                    for row in rows:
                        if row:
                            first_row_cols = len(row)
                            break
                    
                    if first_row_cols <= 1:
                        continue  # Provavelmente não é o delimitador correto
                    
                    # Verificar consistência no número de colunas
                    consistent_rows = 0
                    for row in rows:
                        if len(row) == first_row_cols:
                            consistent_rows += 1
                    
                    # Calcular consistência como porcentagem
                    if rows:
                        consistency = consistent_rows / len(rows)
                        counts[delimiter] = {
                            'columns': first_row_cols,
                            'consistency': consistency
                        }
                except Exception as e:
                    logger.warning(f"Erro ao testar delimitador '{delimiter}': {str(e)}")
            
            # Escolher o melhor delimitador com base na consistência e número de colunas
            best_delimiter = None
            best_score = 0
            
            for delimiter, stats in counts.items():
                # Pontuação baseada em consistência e número de colunas
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
            # Tentar restaurar posição do cursor em caso de erro
            try:
                await file.seek(0)
            except:
                pass
            return None
    
    async def validate_file_structure(self, file: UploadFile, file_extension: str, encoding: str = 'utf-8', delimiter: str = ',') -> Dict[str, Any]:
        """
        Valida a estrutura de um arquivo de dados
        
        Args:
            file: Arquivo a ser validado
            file_extension: Extensão do arquivo
            encoding: Encoding do arquivo
            delimiter: Delimitador (para CSV)
            
        Returns:
            Dicionário com resultados da validação
        """
        result = {
            "is_valid": False,
            "errors": [],
            "warnings": [],
            "column_count": 0,
            "row_sample_count": 0
        }
        
        try:
            # Salvar posição atual do cursor do arquivo
            current_position = file.file.tell()
            
            # Ler um trecho do arquivo para validação
            sample_bytes = await file.read(min(1024 * 100, file.size or 1024 * 100))  # Ler no máximo 100KB
            
            # Restaurar posição do cursor
            await file.seek(0)
            
            # Validar conforme o tipo de arquivo
            if file_extension == 'csv':
                try:
                    sample = sample_bytes.decode(encoding)
                    sample_io = StringIO(sample)
                    df = pd.read_csv(sample_io, delimiter=delimiter, nrows=100)
                    
                    result["is_valid"] = True
                    result["column_count"] = len(df.columns)
                    result["row_sample_count"] = len(df)
                    
                    # Verificar cabeçalhos duplicados
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
                    
                    # Verificar cabeçalhos duplicados
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
            # Tentar restaurar posição do cursor em caso de erro
            try:
                await file.seek(0)
            except:
                pass
        
        return result