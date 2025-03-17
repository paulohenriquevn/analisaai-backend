Módulo de treinamento para o Analisa.ai, focando inicialmente no serviço de treinamento (training_service) e seus testes unitários. Considerando que o sistema deve utilizar a biblioteca "FLAML".

Primeiro, vamos criar o código para o training_service.py . 

Um fato importante é que os dados já foram tratados pelo modulo de processor-api. Por isso o modulo de treinamento deve focar em encontrar o melhor modelo e os melhores hiperparametros.