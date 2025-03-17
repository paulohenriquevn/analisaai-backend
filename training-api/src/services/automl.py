import pandas as pd
from pycaret.classification import *
from pycaret.regression import *
import logging
import joblib

class AutoMLPyCaret:
    def __init__(self, dataset=None, target_column=None, problem_type=None, log_level=logging.INFO):
        """
        Inicializa o módulo de AutoML.

        :param dataset: DataFrame do Pandas contendo os dados (opcional).
        :param target_column: Nome da coluna alvo (opcional).
        :param problem_type: Tipo de problema ('classificacao' ou 'regressao') (opcional).
        :param log_level: Nível de logging (opcional).
        """
        self.dataset = dataset
        self.target_column = target_column
        self.problem_type = problem_type
        self.best_model = None
        self.setup_params = None

        # Configuração do logging
        logging.basicConfig(level=log_level)
        self.logger = logging.getLogger(__name__)

    def setup_environment(self, **kwargs):
        """
        Configura o ambiente do PyCaret para o tipo de problema especificado.
        """
        try:
            if self.problem_type == "classificacao":
                self.setup_params = setup(
                    data=self.dataset,
                    target=self.target_column,
                    session_id=123,
                    **kwargs
                )
            elif self.problem_type == "regressao":
                self.setup_params = setup(
                    data=self.dataset,
                    target=self.target_column,
                    session_id=123,
                    **kwargs
                )
            else:
                raise ValueError("Tipo de problema inválido. Escolha entre 'classificacao' ou 'regressao'.")

            self.logger.info("Ambiente do PyCaret configurado com sucesso.")
        except Exception as e:
            self.logger.error(f"Erro ao configurar o ambiente: {e}")
            raise

    def compare_models(self):
        """
        Compara vários modelos e retorna o melhor com base na métrica padrão.
        """
        try:
            self.logger.info("Comparando modelos...")
            best_model = compare_models()
            self.best_model = best_model
            self.logger.info(f"Melhor modelo selecionado: {best_model}")
            return best_model
        except Exception as e:
            self.logger.error(f"Erro ao comparar modelos: {e}")
            raise

    def tune_model(self, **kwargs):
        """
        Ajusta os hiperparâmetros do melhor modelo.
        """
        try:
            if self.best_model is None:
                raise ValueError("Nenhum modelo foi selecionado ainda. Execute compare_models() primeiro.")

            self.logger.info("Ajustando hiperparâmetros do modelo...")
            tuned_model = tune_model(self.best_model, **kwargs)
            self.best_model = tuned_model
            self.logger.info("Hiperparâmetros ajustados com sucesso.")
            return tuned_model
        except Exception as e:
            self.logger.error(f"Erro ao ajustar hiperparâmetros: {e}")
            raise

    def finalize_model(self):
        """
        Finaliza o modelo treinando-o em todo o conjunto de dados.
        """
        try:
            if self.best_model is None:
                raise ValueError("Nenhum modelo foi selecionado ainda. Execute compare_models() primeiro.")

            self.logger.info("Finalizando o modelo...")
            final_model = finalize_model(self.best_model)
            self.best_model = final_model
            self.logger.info("Modelo finalizado com sucesso.")
            return final_model
        except Exception as e:
            self.logger.error(f"Erro ao finalizar o modelo: {e}")
            raise

    def save_model(self, filepath):
        """
        Salva o modelo treinado para inferência futura.
        """
        try:
            if self.best_model is None:
                raise ValueError("Nenhum modelo foi treinado ainda.")

            self.logger.info(f"Salvando o modelo em {filepath}...")
            save_model(self.best_model, filepath)
            self.logger.info("Modelo salvo com sucesso.")
        except Exception as e:
            self.logger.error(f"Erro ao salvar o modelo: {e}")
            raise

    def evaluate_model(self):
        """
        Avalia o modelo usando métricas apropriadas.
        """
        try:
            if self.best_model is None:
                raise ValueError("Nenhum modelo foi treinado ainda.")

            self.logger.info("Avaliando o modelo...")
            metrics = predict_model(self.best_model, verbose=False)
            return metrics
        except Exception as e:
            self.logger.error(f"Erro ao avaliar o modelo: {e}")
            raise

    def load_model(self, filepath):
        """
        Carrega um modelo salvo para inferência.
        """
        try:
            self.logger.info(f"Carregando o modelo de {filepath}...")
            self.best_model = load_model(filepath)
            self.logger.info("Modelo carregado com sucesso.")
        except Exception as e:
            self.logger.error(f"Erro ao carregar o modelo: {e}")
            raise

    def predict(self, new_data):
        """
        Realiza inferência usando o modelo carregado.

        :param new_data: DataFrame contendo os dados para inferência.
        :return: Previsões do modelo.
        """
        try:
            if self.best_model is None:
                raise ValueError("Nenhum modelo foi carregado ainda. Execute load_model() primeiro.")

            self.logger.info("Realizando inferência...")
            predictions = predict_model(self.best_model, data=new_data)
            self.logger.info("Inferência concluída com sucesso.")
            return predictions
        except Exception as e:
            self.logger.error(f"Erro ao realizar inferência: {e}")
            raise

# Exemplo de uso
if __name__ == "__main__":
    # Carregar dataset
    dataset = pd.read_csv("seu_dataset.csv")
    target_column = "target"
    problem_type = "regressao"  # Ou "regressao"

    # Instanciar o módulo de AutoML
    automl = AutoMLPyCaret(dataset, target_column, problem_type)

    # Configurar o ambiente
    automl.setup_environment()

    # Comparar e selecionar o melhor modelo
    automl.compare_models()

    # Ajustar hiperparâmetros do melhor modelo
    automl.tune_model()

    # Finalizar o modelo
    automl.finalize_model()

    # Avaliar o modelo
    metrics = automl.evaluate_model()

    dataset_id = 1
    # Salvar o modelo para inferência
    # automl.save_model(f"/tmp/analisaai/processed/{dataset_id}/{dataset_id}_modelo")

    # Carregar o modelo salvo
    # automl.load_model(f"/tmp/analisaai/processed/{dataset_id}/{dataset_id}_modelo")

    print("Metricas")
    print(metrics)
    # Dados novos para inferência
    # new_data = pd.DataFrame()

    # # Realizar inferência
    # predictions = automl.predict(new_data)
    # print(predictions)