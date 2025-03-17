import os
import logging
import pandas as pd
import numpy as np
import joblib
from typing import Dict, List, Tuple, Union, Optional

# Importação correta do AutoML no FLAML
try:
    from flaml import AutoML
except ImportError:
    try:
        from flaml.automl import AutoML
    except ImportError:
        raise ImportError(
            "AutoML não está disponível. Instale flaml[automl] com o comando: pip install flaml[automl]"
        )
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score, accuracy_score, f1_score, precision_score, recall_score

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TrainingService:
    """
    Serviço responsável pelo treinamento de modelos usando FLAML para automação de machine learning.
    Focado em encontrar o melhor modelo e hiperparâmetros para os dados já processados.
    """
    
    def __init__(self, time_budget: int = 60, task: str = "classification", 
                 metric: Optional[str] = None, ensemble: bool = True):
        """
        Inicializa o serviço de treinamento.
        
        Args:
            time_budget: Orçamento de tempo em segundos para treinamento
            task: Tipo de tarefa ("classification", "regression", "ranking", etc.)
            metric: Métrica de avaliação (None para usar a padrão com base na tarefa)
            ensemble: Se deve utilizar ensemble de modelos
        """
        self.automl = AutoML()
        self.time_budget = time_budget
        self.task = task
        self.metric = metric
        self.ensemble = ensemble
        self.model = None
        self.features_info = {}
        
        # Define a métrica padrão com base na tarefa, se não especificada
        if not metric:
            if task == "classification":
                self.metric = "accuracy"
            elif task == "regression":
                self.metric = "r2"
                
        logger.info(f"TrainingService inicializado - Task: {task}, Metric: {self.metric}")
    
    def train(self, X: pd.DataFrame, y: pd.Series, 
              test_size: float = 0.2, 
              categorical_features: List[str] = None,
              numeric_features: List[str] = None) -> Dict:
        """
        Treina o modelo usando AutoML com FLAML.
        
        Args:
            X: Features de treinamento
            y: Target de treinamento
            test_size: Proporção do conjunto de teste
            categorical_features: Lista de features categóricas 
            numeric_features: Lista de features numéricas
            
        Returns:
            Dictionary com os resultados do treinamento
        """
        try:
            logger.info(f"Iniciando treinamento com {X.shape[0]} amostras e {X.shape[1]} features")
            
            # Armazena informações sobre as features para uso posterior
            self.features_info = {
                'categorical_features': categorical_features or [],
                'numeric_features': numeric_features or [],
                'feature_names': list(X.columns)
            }
            
            # Divide os dados em treino e teste
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42
            )
            
            # Configura o treinamento baseado no tipo de tarefa
            settings = {
                'time_budget': self.time_budget,  
                'task': self.task,
                'metric': self.metric,
                'ensemble': self.ensemble,
                'verbose': 1
            }
            
            # Armazena informações sobre colunas categóricas, mas não passa diretamente para o FLAML
            # pois alguns estimadores como LGBM não aceitam este parâmetro diretamente
            if categorical_features:
                self.features_info['categorical_features'] = categorical_features
                
                # Verifica se as colunas categóricas estão no tipo 'object' ou 'category'
                for col in categorical_features:
                    if col in X_train.columns and X_train[col].dtype.name not in ['object', 'category']:
                        X_train[col] = X_train[col].astype('category')
                        X_test[col] = X_test[col].astype('category')
            
            # Treina o modelo com FLAML AutoML
            self.automl.fit(X_train=X_train, y_train=y_train, **settings)
            
            # Obtém o melhor modelo de forma segura, verificando a estrutura
            if hasattr(self.automl.model, 'estimator'):
                # Para modelos simples
                best_model = self.automl.model.estimator
            elif hasattr(self.automl.model, 'estimators'):
                # Para modelos Stacking ou Ensemble
                best_model = self.automl.model
            else:
                # Fallback para qualquer outro caso
                best_model = self.automl.model
                
            self.model = best_model
            
            # Faz previsões no conjunto de teste
            y_pred = self.automl.predict(X_test)
            
            # Calcula métricas apropriadas com base no tipo de tarefa
            evaluation_results = self._evaluate_model(y_test, y_pred)
            
            # Prepara o relatório de treinamento
            training_report = {
                'best_model': self.automl.best_estimator,
                'best_config': self.automl.best_config,
                'best_loss': self.automl.best_loss,
                'evaluation': evaluation_results,
                'feature_importance': self._get_feature_importance()
            }
            
            # Adiciona informações de tempo se disponíveis
            try:
                if hasattr(self.automl, 'time_spent'):
                    training_report['time_spent'] = self.automl.time_spent
                elif hasattr(self.automl, 'search_time'):
                    training_report['time_spent'] = self.automl.search_time
                else:
                    # Fallback para valores não disponíveis
                    training_report['time_spent'] = None
            except Exception:
                training_report['time_spent'] = None
            
            logger.info(f"Treinamento concluído - Melhor modelo: {self.automl.best_estimator}")
            return training_report
            
        except Exception as e:
            logger.error(f"Erro durante o treinamento: {str(e)}")
            raise
    
    def _evaluate_model(self, y_true: pd.Series, y_pred: Union[pd.Series, np.ndarray]) -> Dict:
        """
        Avalia o modelo com métricas apropriadas com base no tipo de tarefa.
        
        Args:
            y_true: Valores reais
            y_pred: Previsões do modelo
            
        Returns:
            Dictionary com as métricas de avaliação
        """
        metrics = {}
        
        if self.task == "regression":
            metrics = {
                'mse': mean_squared_error(y_true, y_pred),
                'rmse': np.sqrt(mean_squared_error(y_true, y_pred)),
                'r2': r2_score(y_true, y_pred)
            }
        elif self.task == "classification":
            # Para classificação multiclasse algumas métricas precisam de ajustes
            is_multiclass = len(np.unique(y_true)) > 2
            
            metrics = {
                'accuracy': accuracy_score(y_true, y_pred)
            }
            
            # Para classificação binária ou multiclasse com average
            average = 'weighted' if is_multiclass else 'binary'
            metrics.update({
                'precision': precision_score(y_true, y_pred, average=average, zero_division=0),
                'recall': recall_score(y_true, y_pred, average=average, zero_division=0),
                'f1': f1_score(y_true, y_pred, average=average, zero_division=0)
            })
            
        return metrics
    
    def _get_feature_importance(self) -> Dict:
        """
        Obtém a importância das features, se disponível no modelo.
        
        Returns:
            Dictionary com os nomes das features e suas importâncias
        """
        feature_importance = {}
        feature_names = self.features_info.get('feature_names', [])
        
        try:
            if self.model is None:
                return feature_importance
                
            # Tenta extrair importância de features de modelos ensemble
            if hasattr(self.model, 'estimators') and hasattr(self.model, 'estimators_'):
                # Para modelos StackingRegressor/StackingClassifier e outros ensembles
                # Tentamos usar o melhor estimador do conjunto ou a média de todos
                importances = None
                
                # Tenta usar o melhor estimador se disponível
                try:
                    # Alguns ensembles têm estimadores finais com importance
                    if hasattr(self.model, 'final_estimator') and hasattr(self.model.final_estimator, 'feature_importances_'):
                        importances = self.model.final_estimator.feature_importances_
                    # Outros podem ter uma lista de estimadores base
                    elif len(self.model.estimators_) > 0:
                        # Encontra o primeiro estimador que tem importância de features
                        for estimator in self.model.estimators_:
                            if hasattr(estimator, 'feature_importances_'):
                                importances = estimator.feature_importances_
                                break
                except (AttributeError, IndexError):
                    pass
                
                # Se encontramos alguma importância, a usamos
                if importances is not None:
                    for i, importance in enumerate(importances):
                        if i < len(feature_names):
                            feature_importance[feature_names[i]] = float(importance)
                    return feature_importance
            
            # Tenta obter importância de feature de diferentes maneiras para modelos simples
            if hasattr(self.model, 'feature_importances_'):
                importances = self.model.feature_importances_
                for i, importance in enumerate(importances):
                    if i < len(feature_names):
                        feature_importance[feature_names[i]] = float(importance)
            
            elif hasattr(self.model, 'coef_'):
                importances = np.abs(self.model.coef_)
                if importances.ndim > 1:
                    importances = np.mean(importances, axis=0)
                for i, importance in enumerate(importances):
                    if i < len(feature_names):
                        feature_importance[feature_names[i]] = float(importance)
                        
            # Tenta para modelos como os da biblioteca de AutoML do FLAML
            elif hasattr(self.automl, 'feature_importances_') and self.automl.feature_importances_ is not None:
                importances = self.automl.feature_importances_
                # Se estiver em formato de dicionário
                if isinstance(importances, dict):
                    for feature, importance in importances.items():
                        feature_importance[feature] = float(importance)
                # Se estiver em formato de array
                elif isinstance(importances, (list, np.ndarray)):
                    for i, importance in enumerate(importances):
                        if i < len(feature_names):
                            feature_importance[feature_names[i]] = float(importance)
        
        except (AttributeError, TypeError, ValueError) as e:
            logger.warning(f"Não foi possível obter importância das features: {str(e)}")
        
        return feature_importance
    
    def save_model(self, path: str) -> str:
        """
        Salva o modelo treinado no caminho especificado.
        
        Args:
            path: Caminho onde o modelo será salvo
            
        Returns:
            Caminho completo do arquivo salvo
        """
        if self.automl is None:
            raise ValueError("Não há modelo treinado para salvar.")
        
        # Cria o diretório se não existir
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        # Salva o modelo, as configurações e as informações das features
        model_data = {
            'automl': self.automl,
            'features_info': self.features_info,
            'task': self.task,
            'metric': self.metric
        }
        
        try:
            joblib.dump(model_data, path)
            logger.info(f"Modelo salvo com sucesso em: {path}")
            return path
        except Exception as e:
            logger.error(f"Erro ao salvar o modelo: {str(e)}")
            raise
    
    @classmethod
    def load_model(cls, path: str) -> 'TrainingService':
        """
        Carrega um modelo previamente treinado.
        
        Args:
            path: Caminho do modelo salvo
            
        Returns:
            Instância de TrainingService com o modelo carregado
        """
        try:
            model_data = joblib.load(path)
            
            # Cria uma nova instância
            service = cls(
                task=model_data.get('task', 'classification'),
                metric=model_data.get('metric')
            )
            
            # Restaura o modelo e as informações das features
            service.automl = model_data.get('automl')
            service.features_info = model_data.get('features_info', {})
            service.model = service.automl.model.estimator if service.automl else None
            
            logger.info(f"Modelo carregado com sucesso de: {path}")
            return service
        except Exception as e:
            logger.error(f"Erro ao carregar o modelo: {str(e)}")
            raise
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Faz previsões com o modelo treinado.
        
        Args:
            X: Features para previsão
            
        Returns:
            Array de previsões
        """
        if self.automl is None:
            raise ValueError("Não há modelo treinado para fazer previsões.")
        
        try:
            # Verifica se as colunas coincidem com as usadas no treinamento
            expected_columns = set(self.features_info.get('feature_names', []))
            provided_columns = set(X.columns)
            
            if expected_columns and expected_columns != provided_columns:
                missing = expected_columns - provided_columns
                extra = provided_columns - expected_columns
                
                message = "As colunas para previsão não coincidem com as usadas no treinamento."
                if missing:
                    message += f" Colunas faltando: {missing}."
                if extra:
                    message += f" Colunas extras: {extra}."
                
                raise ValueError(message)
            
            # Faz a previsão
            predictions = self.automl.predict(X)
            return predictions
        
        except Exception as e:
            logger.error(f"Erro ao fazer previsões: {str(e)}")
            raise
    
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Faz previsões de probabilidade para classificação.
        
        Args:
            X: Features para previsão
            
        Returns:
            Array de probabilidades
        """
        if self.automl is None:
            raise ValueError("Não há modelo treinado para fazer previsões.")
        
        if self.task != "classification":
            raise ValueError("Previsão de probabilidade só é aplicável para tarefas de classificação.")
        
        try:
            return self.automl.predict_proba(X)
        except Exception as e:
            logger.error(f"Erro ao fazer previsões de probabilidade: {str(e)}")
            raise