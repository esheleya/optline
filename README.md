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
- Cada operação recebe uma costureira habilitada para o equipamento exigido.
- Uma mesma costureira pode aparecer em mais de um posto e transitar entre máquinas nas quais possui habilidade.
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

O algoritmo considera os postos como recursos de máquina, mas não prende a costureira a uma única máquina. A mesma costureira pode ser selecionada para diferentes postos quando possui as habilidades correspondentes, representando a dinâmica da célula. No diagrama, o **preenchimento** do nó representa a máquina e a **borda** representa o posto; os postos usam azul, laranja, roxo e amarelo em sequência. A quantidade de postos de cada equipamento não pode exceder o limite físico informado. Se as restrições forem incompatíveis, o sistema apresenta a operação que não pôde ser alocada e orienta a revisar tempo de ciclo, máquinas ou habilidades.
