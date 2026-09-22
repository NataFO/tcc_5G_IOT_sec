import { useEffect, useState } from "react";
import { api } from "../api";
import StatusBadge from "../components/StatusBadge";
import { FEATURE_KEYS, PRESET_NORMAL, PRESET_ATAQUE } from "../data/featurePresets";

const META_INICIAL = {
  id_dispositivo: "",
  ip_origem: "10.0.0.5",
  ip_destino: "10.0.0.1",
  porta_origem: 51000,
  porta_destino: 443,
  protocolo: "TCP",
  bytes_enviados: 1500,
  pacotes_enviados: 12,
  duracao_fluxo_ms: 120.5,
};

export default function LogsPage() {
  const [logs, setLogs] = useState([]);
  const [dispositivos, setDispositivos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filtroDispositivo, setFiltroDispositivo] = useState("");

  const [meta, setMeta] = useState(META_INICIAL);
  const [features, setFeatures] = useState(PRESET_NORMAL);
  const [mostrarAvancado, setMostrarAvancado] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState(null);
  const [formError, setFormError] = useState(null);

  async function carregarLogs(idDispositivo) {
    setLoading(true);
    setError(null);
    try {
      const dados = await api.listarLogs({
        limite: 100,
        id_dispositivo: idDispositivo || undefined,
      });
      setLogs(dados);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    api.listarDispositivos().then(setDispositivos).catch(() => {});
    carregarLogs();
  }, []);

  function aplicarPreset(preset) {
    setFeatures(preset);
  }

  async function handleEnviar(e) {
    e.preventDefault();
    setFormError(null);
    setResultado(null);
    if (!meta.id_dispositivo) {
      setFormError("Selecione um dispositivo.");
      return;
    }
    setEnviando(true);
    try {
      const payload = {
        ...meta,
        id_dispositivo: Number(meta.id_dispositivo),
        porta_origem: Number(meta.porta_origem),
        porta_destino: Number(meta.porta_destino),
        bytes_enviados: Number(meta.bytes_enviados),
        pacotes_enviados: Number(meta.pacotes_enviados),
        duracao_fluxo_ms: Number(meta.duracao_fluxo_ms),
        ...Object.fromEntries(
          FEATURE_KEYS.map((k) => [k, Number(features[k])])
        ),
      };
      const log = await api.enviarLog(payload);
      setResultado(log);
      await carregarLogs(filtroDispositivo);
    } catch (err) {
      setFormError(err.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="stack">
      <div className="page-header">
        <h1>Logs de rede</h1>
        <p>Fluxos capturados e classificados pelo modelo LSTM.</p>
      </div>

      <section className="panel">
        <div className="panel-header">
          <h2>Enviar log de teste (POST /logs)</h2>
        </div>
        <form className="stack" onSubmit={handleEnviar}>
          <div className="inline-form">
            <label className="field">
              <span>Dispositivo</span>
              <select
                required
                value={meta.id_dispositivo}
                onChange={(e) => setMeta({ ...meta, id_dispositivo: e.target.value })}
              >
                <option value="">Selecione...</option>
                {dispositivos.map((d) => (
                  <option key={d.id_dispositivo} value={d.id_dispositivo}>
                    #{d.id_dispositivo} — {d.nome_dispositivo}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>IP origem</span>
              <input
                value={meta.ip_origem}
                onChange={(e) => setMeta({ ...meta, ip_origem: e.target.value })}
              />
            </label>
            <label className="field">
              <span>IP destino</span>
              <input
                value={meta.ip_destino}
                onChange={(e) => setMeta({ ...meta, ip_destino: e.target.value })}
              />
            </label>
            <label className="field">
              <span>Porta origem</span>
              <input
                type="number"
                value={meta.porta_origem}
                onChange={(e) => setMeta({ ...meta, porta_origem: e.target.value })}
              />
            </label>
            <label className="field">
              <span>Porta destino</span>
              <input
                type="number"
                value={meta.porta_destino}
                onChange={(e) => setMeta({ ...meta, porta_destino: e.target.value })}
              />
            </label>
            <label className="field">
              <span>Protocolo</span>
              <input
                value={meta.protocolo}
                onChange={(e) => setMeta({ ...meta, protocolo: e.target.value })}
              />
            </label>
            <label className="field">
              <span>Bytes enviados</span>
              <input
                type="number"
                value={meta.bytes_enviados}
                onChange={(e) => setMeta({ ...meta, bytes_enviados: e.target.value })}
              />
            </label>
            <label className="field">
              <span>Pacotes enviados</span>
              <input
                type="number"
                value={meta.pacotes_enviados}
                onChange={(e) => setMeta({ ...meta, pacotes_enviados: e.target.value })}
              />
            </label>
            <label className="field">
              <span>Duração do fluxo (ms)</span>
              <input
                type="number"
                step="0.001"
                value={meta.duracao_fluxo_ms}
                onChange={(e) => setMeta({ ...meta, duracao_fluxo_ms: e.target.value })}
              />
            </label>
          </div>

          <div className="preset-row">
            <button type="button" className="btn btn-ghost btn-small" onClick={() => aplicarPreset(PRESET_NORMAL)}>
              Preencher exemplo normal
            </button>
            <button type="button" className="btn btn-ghost btn-small" onClick={() => aplicarPreset(PRESET_ATAQUE)}>
              Preencher exemplo de ataque
            </button>
            <button
              type="button"
              className="btn btn-ghost btn-small"
              onClick={() => setMostrarAvancado((v) => !v)}
            >
              {mostrarAvancado ? "Ocultar" : "Ver"} features do modelo (avançado)
            </button>
          </div>

          {mostrarAvancado && (
            <div className="feature-grid">
              {FEATURE_KEYS.map((key) => (
                <label className="field" key={key}>
                  <span>{key}</span>
                  <input
                    type="number"
                    step="any"
                    value={features[key]}
                    onChange={(e) =>
                      setFeatures({ ...features, [key]: e.target.value })
                    }
                  />
                </label>
              ))}
            </div>
          )}

          {formError && <div className="alert-box error">{formError}</div>}

          {resultado && (
            <div className="alert-box ok">
              Log #{resultado.id_log} registrado — classificação:{" "}
              <StatusBadge value={resultado.classificacao_ia} /> (probabilidade{" "}
              {(resultado.probabilidade_ia * 100).toFixed(2)}%)
            </div>
          )}

          <div>
            <button className="btn btn-primary" type="submit" disabled={enviando}>
              {enviando ? "Enviando..." : "Enviar log"}
            </button>
          </div>
        </form>
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>Histórico de logs</h2>
          <select
            value={filtroDispositivo}
            onChange={(e) => {
              setFiltroDispositivo(e.target.value);
              carregarLogs(e.target.value);
            }}
          >
            <option value="">Todos os dispositivos</option>
            {dispositivos.map((d) => (
              <option key={d.id_dispositivo} value={d.id_dispositivo}>
                #{d.id_dispositivo} — {d.nome_dispositivo}
              </option>
            ))}
          </select>
        </div>
        {error && <div className="alert-box error">{error}</div>}
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Momento</th>
              <th>Dispositivo</th>
              <th>Fluxo</th>
              <th>Protocolo</th>
              <th>Classificação</th>
              <th>Probabilidade</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id_log}>
                <td>#{log.id_log}</td>
                <td>{new Date(log.momento_captura).toLocaleString("pt-BR")}</td>
                <td>#{log.id_dispositivo}</td>
                <td>
                  {log.ip_origem}:{log.porta_origem} → {log.ip_destino}:{log.porta_destino}
                </td>
                <td>{log.protocolo}</td>
                <td>
                  <StatusBadge value={log.classificacao_ia} />
                </td>
                <td>{(log.probabilidade_ia * 100).toFixed(2)}%</td>
              </tr>
            ))}
            {!loading && logs.length === 0 && (
              <tr>
                <td colSpan={7} className="empty">Nenhum log registrado ainda.</td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}
