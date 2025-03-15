import pytest
import pandas as pd
import numpy as np
from cafe.preprocessor import PreProcessor
from services.processor_service import ProcessorService

@pytest.fixture
def sample_data():
    """Cria um dataset sintético para testes"""
    np.random.seed(42)
    data = {
        'numeric1': np.random.normal(0, 1, 100),
        'numeric2': np.random.normal(5, 2, 100),
        'category': np.random.choice(['A', 'B', 'C'], 100),
        'target': np.random.randint(0, 2, 100)
    }
    # Inserir alguns valores ausentes
    df = pd.DataFrame(data)
    df.loc[10:15, 'numeric1'] = np.nan
    df.loc[20:25, 'numeric2'] = np.nan
    df.loc[30:35, 'category'] = np.nan
    
    # Inserir alguns outliers
    df.loc[40, 'numeric1'] = 10  # outlier
    df.loc[41, 'numeric2'] = 20  # outlier
    
    return df

def test_missing_values_detection(sample_data):
    """Testa a detecção de valores ausentes"""
    preprocessor = PreProcessor(
        imputation_strategy='mean',
        imputation_categorical_strategy='most_frequent'
    )
    
    # Processar os dados
    transformed_data = preprocessor.fit_transform(sample_data)
    
    # Verificar se valores ausentes foram detectados corretamente
    assert preprocessor.column_stats['numeric1']['missing_count'] == 6
    assert preprocessor.column_stats['numeric2']['missing_count'] == 6
    assert preprocessor.column_stats['category']['missing_count'] == 6
    
    # Verificar se não há mais valores ausentes nos dados transformados
    assert transformed_data.isnull().sum().sum() == 0

def test_outlier_detection(sample_data):
    """Testa a detecção de outliers"""
    preprocessor = PreProcessor(
        outlier_detection_method='zscore',
        outlier_treatment_strategy='clip',
        z_score_threshold=3.0
    )
    
    # Processar os dados
    transformed_data = preprocessor.fit_transform(sample_data)
    
    # Verificar se outliers foram detectados corretamente
    assert preprocessor.column_stats['numeric1'].get('outliers_count', 0) >= 1
    assert preprocessor.column_stats['numeric2'].get('outliers_count', 0) >= 1
    
    # Verificar que os valores extremos foram limitados
    assert transformed_data['numeric1'].max() < 10
    assert transformed_data['numeric2'].max() < 20

def test_scaling(sample_data):
    """Testa a normalização/padronização dos dados"""
    preprocessor = PreProcessor(
        scaling_method='minmax',
        scaling_feature_range=(0, 1)
    )
    
    # Processar os dados
    transformed_data = preprocessor.fit_transform(sample_data)
    
    # Verificar se os dados numéricos estão normalizados
    assert transformed_data['numeric1'].min() >= 0
    assert transformed_data['numeric1'].max() <= 1
    assert transformed_data['numeric2'].min() >= 0
    assert transformed_data['numeric2'].max() <= 1
    
    # Verificar que as colunas categóricas não foram normalizadas
    assert 'A' in transformed_data['category'].values
    assert 'B' in transformed_data['category'].values
    assert 'C' in transformed_data['category'].values