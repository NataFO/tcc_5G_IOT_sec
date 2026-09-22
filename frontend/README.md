# Frontend — Segurança 5G/IoT

Dashboard em React (Vite) para o backend FastAPI do TCC. Cobre login,
dispositivos, logs de rede (com envio de teste para o POST /logs) e alertas.

## Como rodar

```bash
npm install
cp .env.example .env   # ajuste VITE_API_URL se a API não estiver em localhost:8000
npm run dev
```

Acesse http://localhost:5173. Faça login com um usuário já cadastrado na
tabela `tb_usuario` (login + senha em texto puro — o backend compara com o
hash bcrypt salvo).

A API precisa estar rodando (`uvicorn main:app --reload` dentro de `backend/`)
e com CORS liberado (já está configurado em `main.py`).

## Páginas

- **Visão geral** (`/`) — estatísticas rápidas, últimos logs e alertas em aberto.
- **Dispositivos** (`/dispositivos`) — lista, cadastro e desativação de dispositivos IoT.
- **Logs de rede** (`/logs`) — histórico de logs e um formulário para testar o
  `POST /logs` (inclui presets de exemplo "normal" e "ataque" para as 20
  features do modelo LSTM).
- **Alertas** (`/alertas`) — lista de alertas gerados automaticamente quando
  um log é classificado como ataque, com atualização de status.

## Observação sobre autenticação

O `POST /auth/login` já retorna um token JWT e o frontend guarda/envia esse
token (`Authorization: Bearer ...`) em todas as chamadas. Hoje, porém, as
rotas de dispositivos/logs/alertas no backend ainda não validam esse token
(não há um `Depends` de verificação de JWT nelas) — ou seja, a proteção real
das rotas ainda precisa ser adicionada no backend se isso for um requisito do
TCC.
