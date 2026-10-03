"""
Reconstrói, a partir dos CSVs brutos, exatamente o mesmo pré-processamento do
notebook 02_pipeline_preprocessamento.ipynb e gera dois arquivos:

  1. data/processed/v1/scaler_params.json
     data_min/data_max do MinMaxScaler ajustado no X_train BRUTO (antes do
     SMOTE). O backend usa isso para normalizar os fluxos recebidos em
     POST /logs/. (O notebook não salvou o scaler, só os arrays já
     normalizados — por isso ele precisa ser reconstruído.)

  2. testes/conjunto_teste_bruto.csv
     As 6.759 amostras do conjunto de TESTE com os valores BRUTOS das 20
     features (nomes com underscore, como a API espera), o rótulo real
     (label: 0 = benigno, 1 = ataque) e o tipo de ataque (ddos, dos, mitm,
     recon, ...). É o que o testes_automatizados.py envia para a API.

Mesmo split do notebook: 70/15/15, estratificado, random_state=42.
O script confere se a normalização reconstruída bate com o X_test.npy salvo
pelo notebook — se não bater, ele para com erro.

Uso (na raiz do projeto ou dentro de testes/):
  python testes/gerar_conjunto_teste.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw"
PROC = BASE / "data" / "processed" / "v1"
SAIDA_CSV = BASE / "testes" / "conjunto_teste_bruto.csv"

print("Lendo CSVs brutos (pode levar ~1 min)...")
df_attack = pd.read_csv(RAW / "attack_samples_5sec.csv")
df_benign = pd.read_csv(RAW / "benign_samples_5sec.csv")
df_attack["label"] = 1
df_benign["label"] = 0
df = pd.concat([df_attack, df_benign], ignore_index=True)

df_numeric = df.select_dtypes(include=[np.number])
X = df_numeric.drop(columns=["label"])
y = df_numeric["label"]

features = json.loads((PROC / "features_selecionadas.json").read_text())

# Mesmo split do notebook 02
X_train, X_temp, y_train, y_temp = train_test_split(
    X[features], y, test_size=0.30, random_state=42, stratify=y
)
X_val, X_test, y_val, y_test = train_test_split(
    X_temp, y_temp, test_size=0.50, random_state=42, stratify=y_temp
)

scaler = MinMaxScaler().fit(X_train)

# Conferência contra o que o notebook salvou
X_test_ref = np.load(PROC / "X_test.npy").reshape(-1, len(features))
y_test_ref = np.load(PROC / "y_test.npy")
dif = np.abs(scaler.transform(X_test) - X_test_ref).max()
if not np.array_equal(y_test.values, y_test_ref) or dif > 1e-9:
    raise SystemExit(
        f"ERRO: a reconstrução não bate com X_test.npy/y_test.npy (dif máx = {dif}). "
        "Os CSVs brutos ou o notebook mudaram?"
    )
print(f"Reconstrução confere com X_test.npy (diferença máxima = {dif}).")

# 1) Parâmetros do scaler
params = {
    "features": features,
    "data_min": scaler.data_min_.tolist(),
    "data_max": scaler.data_max_.tolist(),
    "origem": "MinMaxScaler ajustado no X_train bruto (antes do SMOTE), "
              "split 70/15/15 estratificado, random_state=42",
}
(PROC / "scaler_params.json").write_text(json.dumps(params, indent=2), encoding="utf-8")
print(f"Salvo: {PROC / 'scaler_params.json'}")

# 2) Conjunto de teste bruto, com rótulo e tipo de ataque
saida = X_test.copy()
saida.columns = [f.replace("-", "_") for f in features]
saida["label"] = y_test.values
tipos = df.loc[X_test.index, "label2"].fillna("benigno").values
saida["tipo_ataque_real"] = np.where(saida["label"] == 0, "benigno", tipos)
SAIDA_CSV.parent.mkdir(exist_ok=True)
saida.to_csv(SAIDA_CSV, index=False)
print(f"Salvo: {SAIDA_CSV} ({len(saida)} amostras)")
print(saida["tipo_ataque_real"].value_counts().to_string())
