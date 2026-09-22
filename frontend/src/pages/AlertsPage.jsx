import { useEffect, useState } from "react";
import { api } from "../api";
import StatusBadge from "../components/StatusBadge";

const STATUS_OPCOES = ["aberto", "investigando", "falso_positivo", "resolvido"];

export default function AlertsPage() {
  const [alertas, setAlertas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filtro, setFiltro] = useState("");
  const [salvandoId, setSalvandoId] = useState(null);

  async function carregar(status) {
    setLoading(true);
    setError(null);
    try {
      const dados = await api.listarAlertas({ limite: 100, status: status || undefined });
      setAlertas(dados);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    carregar(filtro);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleStatusChange(alerta, novoStatus) {
    setSalvandoId(alerta.id_alerta);
    try {
      await api.atualizarAlerta(alerta.id_alerta, {
        status_alerta: novoStatus,
        observacoes: alerta.observacoes || null,
      });
      await carregar(filtro);
    } catch (err) {
      alert(err.message);
    } finally {
      setSalvandoId(null);
    }
  }

  return (
    <div className="stack">
      <div className="page-header">
        <h1>Alertas</h1>
        <p>Ataques identificados pelo modelo e fluxo de investigação.</p>
      </div>

      <section className="panel">
        <div className="panel-header">
          <h2>Alertas</h2>
          <select
            value={filtro}
            onChange={(e) => {
              setFiltro(e.target.value);
              carregar(e.target.value);
            }}
          >
            <option value="">Todos os status</option>
            {STATUS_OPCOES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        {error && <div className="alert-box error">{error}</div>}

        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Quando</th>
              <th>Dispositivo</th>
              <th>Tipo</th>
              <th>Severidade</th>
              <th>Confiança</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {alertas.map((a) => (
              <tr key={a.id_alerta}>
                <td>#{a.id_alerta}</td>
                <td>{new Date(a.data_hora_alerta).toLocaleString("pt-BR")}</td>
                <td>{a.nome_dispositivo || `#${a.id_dispositivo}`}</td>
                <td>{a.tipo_ataque}</td>
                <td>
                  <StatusBadge value={a.severidade} />
                </td>
                <td>{(a.probabilidade_confianca * 100).toFixed(2)}%</td>
                <td>
                  <select
                    value={a.status_alerta}
                    disabled={salvandoId === a.id_alerta}
                    onChange={(e) => handleStatusChange(a, e.target.value)}
                  >
                    {STATUS_OPCOES.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
            {!loading && alertas.length === 0 && (
              <tr>
                <td colSpan={7} className="empty">Nenhum alerta encontrado.</td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}
