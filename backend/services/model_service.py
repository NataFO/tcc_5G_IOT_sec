import numpy as np
import json
import os
from tensorflow.keras.models import load_model
from sklearn.preprocessing import MinMaxScaler

# Caminhos dos arquivos
# services/model_service.py -> backend/services -> backend -> raiz do projeto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_PATH    = os.path.join(BASE_DIR, "models", "lstm_final.keras")
FEATURES_PATH = os.path.join(BASE_DIR, "data", "processed", "v1", "features_selecionadas.json")
TRAIN_PATH    = os.path.join(BASE_DIR, "data", "processed", "v1", "X_train.npy")

# Carrega o modelo e as features uma única vez quando o servidor inicia
print("Carregando modelo LSTM...")
model = load_model(MODEL_PATH)

print("Carregando features selecionadas...")
with open(FEATURES_PATH, "r") as f:
    FEATURES = json.load(f)

# Recria o scaler usando os dados de treino
print("Recriando scaler Min-Max...")
X_train = np.load(TRAIN_PATH)
X_train_flat = X_train.reshape(X_train.shape[0], X_train.shape[2])
scaler = MinMaxScaler()
scaler.fit(X_train_flat)

print("Modelo pronto para classificação.")

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
    # Extrai apenas as 20 features selecionadas na ordem correta
    vetor = np.array([[dados[f.replace("-", "_")] for f in FEATURES]])

    # Normaliza com o mesmo scaler do treino
    vetor_scaled = scaler.transform(vetor)

    # Reformata para o LSTM: (1, 1, 20)
    vetor_lstm = vetor_scaled.reshape(1, 1, 20)

    # Classifica
    probabilidade = float(model.predict(vetor_lstm, verbose=0)[0][0])

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
        "severidade": severidade
    }
