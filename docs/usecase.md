# **Documento de Use Cases Revisado - MVP**  
**Funcionalidades:** Upload do Arquivo, Treinamento do Modelo, Avaliação do Modelo, Predição.  

---

### **Use Case 1: Upload do Arquivo para Treinamento e Validação**  
**Ator Primário:** Usuário (PME)  
**Pré-condição:** Usuário autenticado na plataforma.  
**Descrição:** Upload de arquivo (CSV, Excel) para análise.  
**Fluxo Principal:**  
1. Usuário acessa a tela de **Upload de Dados**.  
2. Seleciona arquivo (até **100 MB**) nos formatos suportados.  
3. Define parâmetros (separador de colunas, encoding).  
4. Sistema analisa a estrutura, exibe preview e **sugere tratamento de dados ausentes** (ex.: remoção de linhas).  
5. Usuário confirma a importação.  
6. Sistema armazena dados e notifica o sucesso.  

**Fluxo Alternativo (Erro no Upload):**  
- Se o arquivo estiver corrompido/exceder 100 MB: alerta de erro com sugestões.  
- Se encoding não for detectado: sistema usa **UTF-8 como padrão**.  

**Critérios de Aceitação:**  
✅ Suportar arquivos de **até 100 MB** (CSV/Excel).  
✅ Exibir preview dos dados e **sugestões de pré-processamento** (ex.: dados ausentes).  
✅ Detectar separador/encoding automaticamente, com fallback para UTF-8.  
✅ Alertar sobre inconsistências **antes da importação**.  
✅ Notificar sucesso/falha com mensagens claras.  

---

### **Use Case 2: Treinamento do Modelo**  
**Ator Primário:** Usuário (PME)  
**Pré-condição:** Dados válidos carregados.  
**Descrição:** Configuração e treinamento de modelo de Machine Learning.  
**Fluxo Principal:**  
1. Usuário seleciona conjunto de dados e define variável-alvo.  
2. Sistema identifica tipo de problema (classificação, regressão, clustering).  
3. Sistema sugere algoritmos e **aplica pré-processamento automático** (ex.: normalização, tratamento de missing values).  
4. Usuário escolhe algoritmo ou ajusta **hiperparâmetros básicos** (ex.: número de árvores em Random Forest).  
5. Sistema exibe **barra de progresso** durante o treinamento.  
6. Após conclusão, sistema exibe desempenho inicial e salva o modelo.  

**Fluxo Alternativo (Erro):**  
- Se dados forem desbalanceados: sistema sugere técnicas como oversampling.  
- Se treinamento falhar: log de erro com explicação técnica simplificada.  

**Critérios de Aceitação:**  
✅ Permitir ajuste de **hiperparâmetros básicos** (valores padrão pré-definidos).  
✅ Exibir **transformações aplicadas** (ex.: "Dados normalizados com Min-Max Scaling").  
✅ Acompanhamento via **barra de progresso/notificações em tempo real**.  
✅ Alertar sobre **datasets desbalanceados** durante a seleção da variável-alvo.  

---

### **Use Case 3: Avaliação do Modelo**  
**Ator Primário:** Usuário (PME)  
**Pré-condição:** Modelo treinado com sucesso.  
**Descrição:** Avaliação de desempenho do modelo.  
**Fluxo Principal:**  
1. Usuário seleciona modelo e visualiza métricas:  
   - **Classificação/Regressão:** Acurácia, F1-score, RMSE.  
   - **Clustering:** Silhouette Score, gráficos de dispersão.  
2. Sistema exibe comparação de modelos em **tabelas e gráficos side-by-side**.  
3. Usuário ajusta hiperparâmetros ou solicita **ajuste automático** (ex.: GridSearch).  
4. Sistema permite salvar/descarte do modelo.  

**Fluxo Alternativo (Baixo Desempenho):**  
- Sistema sugere **re-treinamento com ajuste automático de hiperparâmetros**.  

**Critérios de Aceitação:**  
✅ Exibir **gráficos interativos** (matriz de confusão, curva ROC).  
✅ Para clustering: incluir **visualização de clusters 2D/3D**.  
✅ Permitir comparação de modelos com **ranking baseado em métricas**.  

---

### **Use Case 4: Predição com Modelo Treinado**  
**Ator Primário:** Usuário (PME)  
**Pré-condição:** Modelo treinado e aprovado.  
**Descrição:** Realização de previsões em novos dados.  
**Fluxo Principal:**  
1. Usuário faz upload de novos dados ou **insere manualmente via formulário**.  
2. Sistema valida compatibilidade (ex.: colunas faltantes) e aplica pré-processamento.  
3. Sistema retorna previsões em **até 30 segundos** (processamento assíncrono para grandes volumes).  
4. Previsões podem ser exportadas em CSV ou acessadas via **API REST básica** (POST `/predict`).  

**Fluxo Alternativo (Erro):**  
- Se dados forem incompatíveis: sistema sugere template para correção.  

**Critérios de Aceitação:**  
✅ Validar dados de entrada **em tempo real** durante upload manual.  
✅ Fornecer **template de CSV** com colunas requeridas pelo modelo.  
✅ Garantir tempo de resposta ≤30s para arquivos de até 10 MB.  

---

### **Requisitos Gerais do MVP**  
1. **Segurança:**   
   - ✅ Opção de exclusão de dados em conformidade com LGPD.  

2. **Usabilidade:**  
   - ✅ Tooltips explicativos para métricas (ex.: "Recall: capacidade de identificar casos positivos").  
   - ✅ Limitação do MVP: suporte apenas a **modelos clássicos** (ex.: Random Forest, Regressão Logística).  

3. **Tratamento de Edge Cases:**  
   - ✅ Alertar se a variável-alvo tiver >90% de valores únicos (problema de clustering).  
   - ✅ Bloquear treinamento se dataset tiver <50 linhas.  

---

**Notas Finais:**  
- A API de predição será funcional no MVP, mas com limite de 10 requisições/minuto.  
- Modelos de deep learning e análises multivariadas complexas serão priorizados em versões futuras.  

--- 

O documento agora está mais robusto, com especificações técnicas claras para desenvolvedores e garantia de usabilidade para PMEs. 😊