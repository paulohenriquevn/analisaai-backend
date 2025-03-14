LIGUAGEM: TYPESCRIPT 
FRAMEWORK: ANGULARJS

### **Estrutura do Projeto Figma (Fluxo Completo)**  
**Nome do Arquivo:** `AnalisaJá - Fluxo Completo MVP`  
**Seções Principais:**  
1. **Autenticação**  
2. **Upload de Dados**  
3. **Treinamento do Modelo**  
4. **Avaliação do Modelo**  
5. **Predição**  
6. **Configurações e Ajuda**  

---

### **Telas e Componentes Essenciais**  
#### **1. Autenticação**  
- **Tela de Login:**  
  - Campos: Email, Senha, Botão "Entrar".  
  - Link para "Esqueci a senha" e "Criar conta".  
- **Tela de Registro:**  
  - Campos: Nome, Email, Senha, Confirmação de Senha.  

#### **2. Upload de Dados**  
- **Dashboard:**  
  - Botão "Novo Upload" destacado.  
  - Lista de datasets já carregados (se houver).  
- **Tela de Upload:**  
  - Área de drag-and-drop para arquivos.  
  - Seletor de arquivo local.  
  - Opções avançadas: separador de colunas, encoding (UTF-8 como padrão).  
- **Preview de Dados:**  
  - Grid com visualização das primeiras 10 linhas.  
  - Alertas de dados ausentes/inconsistências (ex.: badge vermelho em colunas problemáticas).  
- **Erro de Upload:**  
  - Modal com mensagem amigável (ex.: "Arquivo muito grande! Tamanho máximo: 100 MB").  

#### **3. Treinamento do Modelo**  
- **Seleção de Dataset:**  
  - Card com nome do dataset, data de upload, tamanho.  
  - Botão "Treinar Modelo".  
- **Configuração do Treinamento:**  
  - Dropdown para seleção da **variável-alvo**.  
  - Cards com sugestões de algoritmos (ex.: "Recomendamos Regressão Linear para seus dados").  
  - Seção de **ajuste de hiperparâmetros** (ex.: número de árvores, taxa de aprendizado).  
- **Progresso do Treinamento:**  
  - Barra de progresso animada.  
  - Log de etapas (ex.: "Divisão treino/teste concluída", "Treinamento em andamento").  

#### **4. Avaliação do Modelo**  
- **Resumo do Modelo:**  
  - Métricas principais em cards (ex.: Acurácia: 92%, F1-score: 0.89).  
  - Gráficos interativos: Matriz de Confusão, Curva ROC.  
- **Comparação de Modelos:**  
  - Tabela comparativa com modelos treinados (ex.: "Random Forest vs. Regressão Logística").  
  - Botão "Selecionar Melhor Modelo".  

#### **5. Predição**  
- **Upload de Dados para Predição:**  
  - Similar à tela de upload inicial, mas com aviso: "Certifique-se de que as colunas correspondem ao modelo X").  
- **Resultados da Predição:**  
  - Tabela com coluna adicional "Previsão".  
  - Botões: "Exportar CSV", "Copiar para Área de Transferência".  
- **API Integration Guide (Acesso Rápido):**  
  - Exemplo de requisição HTTP (curl ou Python).  

#### **6. Configurações e Ajuda**  
- **Perfil do Usuário:**  
  - Foto, nome, opção de exclusão de conta.  
- **Documentação:**  
  - Tooltips integrados (ex.: ao passar o mouse sobre "F1-score", exibir explicação).  

---

### **Fluxo de Navegação (User Flow)**  
1. **Login → Dashboard → Upload → Treinamento → Avaliação → Predição.**  
2. **Fluxos Alternativos:**  
   - Tratamento de erros (ex.: redirecionar para tela de upload após falha).  
   - Comparação de modelos durante a avaliação.  

---

### **Design Guidelines**  
- **Cores Primárias:** Azul Profissional (#2A5CAA) + Verde Tecnológico (#00C897).  
- **Tipografia:** Inter (para textos) + Roboto Mono (para códigos/API).  
- **Componentes Reutilizáveis:**  
  - Botões primários/secundários.  
  - Cards de dataset/modelo.  
  - Modais de erro/sucesso.  
- **Microinterações:**  
  - Hover em botões.  
  - Animação de loading durante treinamento.  

---

### **Passo a Passo para Criar no Figma**  
1. **Crie um novo projeto** e nomeie conforme o MVP.  
2. **Adicione Frames** para cada tela (ex.: `Login`, `Dashboard`, `Upload`).  
3. **Use Auto Layout** para componentes repetidos (ex.: lista de datasets).  
4. **Adicione Protótipos** ligando os botões às telas correspondentes (ex.: Botão "Treinar" → Tela de Configuração do Treinamento).  
5. **Incorpore os Wireframes** abaixo como referência:  

#### Wireframes de Referência (Low-Fidelity):  
- **Upload de Dados:**  
  ```
  [Header] > [Drag-and-Drop Area] > [Preview Table] > [Botão "Confirmar"]
  ```  
- **Avaliação do Modelo:**  
  ```
  [Gráfico de Barras] | [Tabela de Métricas] | [Botão "Comparar Modelos"]
  ```  

---

### **Link de Inspiração (Figma Community)**  
https://www.figma.com/design/VmC7hkW8xFVIPXyIyfMQzL/HaRchers-Dashboard-(Community)?node-id=0-1&p=f&t=B9EjVYiLVoAwOzjs-0

Se precisar de ajuda técnica para estruturar componentes específicos, estou à disposição! 😊