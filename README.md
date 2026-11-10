# OptiLine — Balanceador da Célula de Costura

Aplicativo em Streamlit para gerar uma proposta de balanceamento de uma célula de costura usando a heurística **Ranked Positional Weight (RPW)**, respeitando precedências, tempo de ciclo, equipamentos disponíveis e habilidades das costureiras.

## O que foi adaptado

- Entrada por operação, tempo padrão, equipamento e predecessoras.
- Cálculo de peso posicional RPW: tempo da operação + tempos dos sucessores.
- Alocação única de cada operação em um posto.
- Respeito integral às precedências informadas.
- Limite de tempo de ciclo por posto.
- Limite físico de máquinas por tipo.
- Matriz editável de habilidades das costureiras A–H.
- Cada posto é associado a uma costureira, que pode operar mais de um tipo de máquina.
- Uma mesma costureira pode receber operações de equipamentos diferentes quando possui as habilidades correspondentes.
- A alocação tenta preencher o tempo de ciclo e equilibrar as cargas dos postos, respeitando a quantidade física de cada máquina.
- Indicadores de postos, carga, ociosidade, eficiência e índice de suavidade.
- Diagrama de precedência colorido por equipamento, com legenda de máquinas e postos.
- Exportação CSV e relatório XLSX com distribuição, pesos RPW, indicadores, máquinas e habilidades.

## Formato de entrada

CSV ou XLSX com as colunas:

```csv
ID,Operação,Tempo,Equipamento,Predecessores
O01,Chulear babado alça,0.371,Overloque,-
O02,Franzir babado nas alças,0.979,Franzidor,O01
O03,Unir frente e cavas com forro,0.332,Overloque,-
```

Predecessoras múltiplas devem ser separadas por vírgula, por exemplo `O05,O06`.

## Como executar

```bash
pip install -r requirements.txt
streamlit run app.py
```

Na barra lateral, ajuste o tempo de ciclo, a quantidade disponível de cada máquina e a matriz de habilidades. Depois, informe as operações e clique em **Gerar balanceamento RPW**.

## Observação sobre a alocação

O algoritmo considera cada costureira como um posto de trabalho. Ela pode transitar entre máquinas e executar operações de equipamentos diferentes no mesmo posto, desde que tenha habilidade para todos eles. No diagrama, o **preenchimento** do nó representa a máquina e a **borda** representa o posto; os postos usam azul, laranja, roxo e amarelo em sequência. A quantidade de máquinas físicas de cada tipo não pode exceder o limite informado. Se as restrições forem incompatíveis, o sistema apresenta a operação que não pôde ser alocada e orienta a revisar tempo de ciclo, máquinas ou habilidades.
