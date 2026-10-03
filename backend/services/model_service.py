import threading
import time
import numpy as np
import json
import os
from tensorflow.keras.models import load_model

# Caminhos dos arquivos
# services/model_service.py -> backend/services -> backend -> raiz do projeto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_PATH    = os.path.join(BASE_DIR, "models", "lstm_final.keras")
FEATURES_PATH = os.path.join(BASE_DIR, "data", "processed", "v1", "features_selecionadas.json")
SCALER_PATH   = os.path.join(BASE_DIR, "data", "processed", "v1", "scaler_params.json")

# Carrega o modelo e as features uma única vez quando o servidor inicia
print("Carregando modelo LSTM...")
model = load_model(MODEL_PATH)

print("Carregando features selecionadas...")
with open(FEATURES_PATH, "r") as f:
    FEATURES = json.load(f)

# Carrega o scaler Min-Max ORIGINAL (o mesmo ajustado no notebook 02 sobre o
# X_train bruto, antes do SMOTE).
#
# Antes, o scaler era "recriado" com fit no X_train.npy — mas esse arquivo já
# está normalizado (0 a 1), então o scaler virava uma identidade e os valores
# brutos recebidos pela API chegavam ao LSTM sem normalização nenhuma. No
# conjunto de teste isso derrubava a acurácia de ~91,7% para ~51,7%
# (quase tudo classificado como ataque).
#
# scaler_params.json é gerado por testes/gerar_conjunto_teste.py e guarda
# data_min/data_max de cada feature, na mesma ordem de features_selecionadas.json.
print("Carregando parâmetros do scaler Min-Max...")
with open(SCALER_PATH, "r") as f:
    _scaler = json.load(f)

if _scaler["features"] != FEATURES:
    raise RuntimeError(
        "scaler_params.json não corresponde a features_selecionadas.json — "
        "gere de novo com testes/gerar_conjunto_teste.py"
    )

DATA_MIN = np.array(_scaler["data_min"], dtype=float)
DATA_MAX = np.array(_scaler["data_max"], dtype=float)
# Mesmo tratamento do sklearn para features constantes (evita divisão por zero)
DATA_RANGE = np.where(DATA_MAX - DATA_MIN == 0, 1.0, DATA_MAX - DATA_MIN)

# Uma inferência por vez. O TensorFlow já usa todos os núcleos do processador
# em CADA chamada; com várias requisições chamando o modelo ao mesmo tempo, as
# chamadas disputam os mesmos núcleos e todas ficam lentas. Com a trava, elas
# esperam numa fila curta e cada uma roda na velocidade normal. Achado no teste
# de carga (CT08/CT09). O tempo de espera na fila é medido separadamente.
_trava_modelo = threading.Lock()

print("Modelo pronto para classificação.")


def normalizar(vetor: np.ndarray) -> np.ndarray:
    """Aplica a mesma normalização Min-Max usada no treino (equivale a scaler.transform)."""
    return (vetor - DATA_MIN) / DATA_RANGE


def classificar_fluxo(dados: dict) -> dict:
    """
    Recebe um dicionário com os dados do fluxo de rede,
    pré-processa e classifica com o modelo LSTM.
    Retorna a classificação e a probabilidade.

    Observação: os nomes das features usadas no treino (features_selecionadas.json)
    usam hífen (ex.: "network_time-delta_avg"), enquanto o schema da API usa
    underscore (ex.: "network_time_delta_avg"). Por isso convertemos o nome da
    feature (hífen -> underscore) antes de buscar no dicionário recebido.
    """
    # Extrai apenas as 20 features selecionadas na ordem correta (valores brutos)
    vetor = np.array([[dados[f.replace("-", "_")] for f in FEATURES]], dtype=float)

    # Normaliza com os parâmetros do scaler do treino
    vetor_scaled = normalizar(vetor)

    # Reformata para o LSTM: (1, 1, 20)
    vetor_lstm = vetor_scaled.reshape(1, 1, 20)

    # Classifica. Chamar model(...) direto é bem mais rápido que model.predict()
    # para UMA amostra (predict monta um pipeline de lote a cada chamada) e dá
    # o mesmo resultado — isso pesa na latência medida no CT03.
    t0 = time.perf_counter()
    with _trava_modelo:
        t1 = time.perf_counter()
        probabilidade = float(model(vetor_lstm, training=False).numpy()[0][0])
        t2 = time.perf_counter()

    # Define a classe e severidade
    # (valores em conformidade com as constraints do banco: 'Normal', 'DDoS', ...)
    if probabilidade >= 0.5:
        classificacao = "DDoS"
        if probabilidade >= 0.9:
            severidade = "Critica"
        elif probabilidade >= 0.7:
            severidade = "Alta"
        else:
            severidade = "Media"
    else:
        classificacao = "Normal"
        severidade = None

    return {
        "classificacao": classificacao,
        "probabilidade": round(probabilidade, 4),
        "severidade": severidade,
        "fila_ms": (t1 - t0) * 1000,
        "modelo_ms": (t2 - t1) * 1000,
    }
