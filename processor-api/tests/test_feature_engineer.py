import pytest
import pandas as pd
import numpy as np
from cafe.feature_engineer import FeatureEngineer
from services.processor_service import ProcessorService

@pytest.fixture
def sample_data():
    """Cria um dataset sintético para testes"""
    np.random.seed(42)
    data = {
        'numeric1': np.random.normal(0, 1, 100),
        'numeric2': np.random.normal(5, 2, 100),
        'category1': np.random.choice(['A', 'B', 'C'], 100),
        'category2': np.random.choice(['X', 'Y', 'Z'], 100),
        'target': np.random.randint(0, 2, 100)
    }
    df = pd.DataFrame(data)
    
    # Adicionar uma coluna altamente correlacionada
    df['numeric1_correlated'] = df['numeric1'] * 1.1 + np.random.normal(0, 0.1, 100)
    
    return df

def test_categorical_encoding(sample_data):
    """Testa a codificação de variáveis categóricas"""
    feature_engineer = FeatureEngineer(
        categorical_encoding_method='onehot',
        max_categories_for_onehot=10
    )
    
    # Processar os dados
    transformed_data = feature_engineer.fit_transform(sample_data)
    
    # Verificar se as colunas categóricas foram codificadas
    assert 'category1_A' in transformed_data.columns
    assert 'category1_B' in transformed_data.columns
    assert 'category1_C' in transformed_data.columns
    assert 'category2_X' in transformed_data.columns
    assert 'category2_Y' in transformed_data.columns
    assert 'category2_Z' in transformed_data.columns
    
    # Verificar que as colunas categóricas originais não estão mais presentes
    assert 'category1' not in transformed_data.columns
    assert 'category2' not in transformed_data.columns

def test_correlation_filtering(sample_data):
    """Testa a filtragem de colunas altamente correlacionadas"""
    feature_engineer = FeatureEngineer(
        correlation_threshold=0.8
    )
    
    # Processar os dados
    transformed_data = feature_engineer.fit_transform(sample_data)
    
    # Verificar se uma das colunas correlacionadas foi removida
    columns = list(transformed_data.columns)
    assert not ('numeric1' in columns and 'numeric1_correlated' in columns)

def test_feature_generation(sample_data):
    """Testa a geração de novas features"""
    feature_engineer = FeatureEngineer(
        generate_features=True
    )
    
    # Processar os dados
    transformed_data = feature_engineer.fit_transform(sample_data)
    
    # Verificar se novas features foram geradas
    # O número de colunas deve ser maior que o original
    assert len(transformed_data.columns) > len(sample_data.columns)
    
    # Verificar se algumas transformações comuns foram aplicadas
    # (nem todas estarão presentes, dependendo da implementação do CAFE)
    polynomial_features = [col for col in transformed_data.columns if '_pow_' in col]
    interaction_features = [col for col in transformed_data.columns if '_mult_' in col]
    
    # Deve haver pelo menos algumas novas features geradas
    generated_features = polynomial_features + interaction_features
    assert len(generated_features) > 0

def test_feature_selection(sample_data):
    """Testa a seleção de features com base na importância"""
    feature_engineer = FeatureEngineer(
        feature_selection_method='feature_importance',
        min_feature_importance=0.01
    )
    
    # Processar os dados - precisa de uma coluna target para feature importance
    transformed_data = feature_engineer.fit_transform(sample_data, target_col='target')
    
    # O número de colunas deve ser menor ou igual ao original (menos a coluna target)
    assert len(transformed_data.columns) <= len(sample_data.columns) - 1