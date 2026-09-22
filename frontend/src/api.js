const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, { method = "GET", body, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };

  if (auth) {
    const token = localStorage.getItem("token");
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  let data = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!res.ok) {
    const message =
      (data && data.detail) || res.statusText || "Erro na requisição";

    // Sessão ausente/expirada: agora que o backend valida o token em
    // toda rota protegida, um 401 aqui significa que é preciso logar
    // de novo — limpa o token e manda o usuário para a tela de login
    // em vez de deixar a página quebrada com um erro cru.
    if (res.status === 401 && auth) {
      localStorage.removeItem("token");
      if (window.location.pathname !== "/login") {
        window.location.assign("/login");
      }
    }

    throw new ApiError(message, res.status);
  }

  return data;
}

export const api = {
  // Autenticação
  login: (login, senha) =>
    request("/auth/login", { method: "POST", body: { login, senha }, auth: false }),

  // Dispositivos
  listarDispositivos: () => request("/dispositivos/"),
  buscarDispositivo: (id) => request(`/dispositivos/${id}`),
  criarDispositivo: (dados) =>
    request("/dispositivos/", { method: "POST", body: dados }),
  atualizarDispositivo: (id, dados) =>
    request(`/dispositivos/${id}`, { method: "PATCH", body: dados }),
  desativarDispositivo: (id) =>
    request(`/dispositivos/${id}`, { method: "DELETE" }),

  // Logs
  listarLogs: ({ limite = 50, id_dispositivo } = {}) => {
    const params = new URLSearchParams({ limite });
    if (id_dispositivo) params.set("id_dispositivo", id_dispositivo);
    return request(`/logs/?${params.toString()}`);
  },
  enviarLog: (dados) => request("/logs/", { method: "POST", body: dados }),

  // Alertas
  listarAlertas: ({ limite = 50, status } = {}) => {
    const params = new URLSearchParams({ limite });
    if (status) params.set("status", status);
    return request(`/alertas/?${params.toString()}`);
  },
  atualizarAlerta: (id, dados) =>
    request(`/alertas/${id}`, { method: "PATCH", body: dados }),
};

export { ApiError };
