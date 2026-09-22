import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import StatusBadge from "../components/StatusBadge";

export default function DashboardPage() {
  const [dispositivos, setDispositivos] = useState([]);
  const [logs, setLogs] = useState([]);
  const [alertas, setAlertas] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let ativo = true;
    async function carregar() {
      setLoading(true);
      setError(null);
      try {
        const [d, l, a] = await Promise.all([
          api.listarDispositivos(),
          api.listarLogs({ limite: 10 }),
          api.listarAlertas({ limite: 5, status: "aberto" }),
        ]);
        if (!ativo) return;
        setDispositivos(d);
        setLogs(l);
        setAlertas(a);
      } catch (err) {
        if (ativo) setError(err.message);
      } finally {
        if (ativo) setLoading(false);
      }
    }
    carregar();
    return () => {
      ativo = false;
    };
  }, []);

  const dispositivosAtivos = dispositivos.filter((d) => d.status === "ativo").length;
  const logsAtaque = logs.filter((l) => l.classificacao_ia !== "Normal").length;

  return (
    <div className="stack">
      <div className="page-header">
        <h1>Visão geral</h1>
        <p>Resumo do monitoramento de dispositivos e tráfego de rede.</p>
      </div>

      {error && <div className="alert-box error">{error}</div>}

      <div className="stat-grid">
        <div className="stat-card">
          <span className="stat-label">Dispositivos ativos</span>
          <span className="stat-value">{loading ? "…" : dispositivosAtivos}</span>
          <span className="stat-sub">{dispositivos.length} cadastrados no total</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Alertas em aberto</span>
          <span className="stat-value">{loading ? "…" : alertas.length}</span>
          <span className="stat-sub">Exigem investigação</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Últimos logs com ataque</span>
          <span className="stat-value">{loading ? "…" : logsAtaque}</span>
          <span className="stat-sub">Entre os 10 logs mais recentes</span>
        </div>
      </div>

      <div className="grid-2">
        <section className="panel">
          <div className="panel-header">
            <h2>Logs recentes</h2>
            <Link to="/logs">Ver todos</Link>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Momento</th>
                <th>Dispositivo</th>
                <th>Origem → Destino</th>
                <th>Classificação</th>
              </tr>
            </thead>
            <tbody>
              {logs.slice(0, 6).map((log) => (
                <tr key={log.id_log}>
                  <td>{new Date(log.momento_captura).toLocaleString("pt-BR")}</td>
                  <td>#{log.id_dispositivo}</td>
                  <td>
                    {log.ip_origem}:{log.porta_origem} → {log.ip_destino}:{log.porta_destino}
                  </td>
                  <td>
                    <StatusBadge value={log.classificacao_ia} />
                  </td>
                </tr>
              ))}
              {!loading && logs.length === 0 && (
                <tr>
                  <td colSpan={4} className="empty">Nenhum log registrado ainda.</td>
                </tr>
              )}
            </tbody>
          </table>
        </section>

        <section className="panel">
          <div className="panel-header">
            <h2>Alertas em aberto</h2>
            <Link to="/alertas">Ver todos</Link>
          </div>
          <table className="table">
            <thead>
              <tr>
                <th>Quando</th>
                <th>Dispositivo</th>
                <th>Tipo</th>
                <th>Severidade</th>
              </tr>
            </thead>
            <tbody>
              {alertas.map((a) => (
                <tr key={a.id_alerta}>
                  <td>{new Date(a.data_hora_alerta).toLocaleString("pt-BR")}</td>
                  <td>{a.nome_dispositivo}</td>
                  <td>{a.tipo_ataque}</td>
                  <td>
                    <StatusBadge value={a.severidade} />
                  </td>
                </tr>
              ))}
              {!loading && alertas.length === 0 && (
                <tr>
                  <td colSpan={4} className="empty">Nenhum alerta em aberto. 🎉</td>
                </tr>
              )}
            </tbody>
          </table>
        </section>
      </div>
    </div>
  );
}
