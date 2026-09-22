import { useEffect, useState } from "react";
import { api } from "../api";
import StatusBadge from "../components/StatusBadge";

const FORM_INICIAL = {
  nome_dispositivo: "",
  tipo: "",
  ip_address: "",
  gnodeb_associado: "",
};

export default function DevicesPage() {
  const [dispositivos, setDispositivos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [form, setForm] = useState(FORM_INICIAL);
  const [salvando, setSalvando] = useState(false);
  const [formError, setFormError] = useState(null);

  async function carregar() {
    setLoading(true);
    setError(null);
    try {
      const dados = await api.listarDispositivos();
      setDispositivos(dados);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    carregar();
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setFormError(null);
    setSalvando(true);
    try {
      await api.criarDispositivo(form);
      setForm(FORM_INICIAL);
      await carregar();
    } catch (err) {
      setFormError(err.message);
    } finally {
      setSalvando(false);
    }
  }

  async function handleDesativar(id) {
    if (!confirm("Desativar este dispositivo?")) return;
    try {
      await api.desativarDispositivo(id);
      await carregar();
    } catch (err) {
      alert(err.message);
    }
  }

  return (
    <div className="stack">
      <div className="page-header">
        <h1>Dispositivos IoT</h1>
        <p>Cadastro e status dos dispositivos monitorados na rede 5G.</p>
      </div>

      <section className="panel">
        <div className="panel-header">
          <h2>Novo dispositivo</h2>
        </div>
        <form className="inline-form" onSubmit={handleSubmit}>
          <label className="field">
            <span>Nome</span>
            <input
              required
              value={form.nome_dispositivo}
              onChange={(e) => setForm({ ...form, nome_dispositivo: e.target.value })}
            />
          </label>
          <label className="field">
            <span>Tipo</span>
            <input
              required
              placeholder="sensor, câmera, gateway..."
              value={form.tipo}
              onChange={(e) => setForm({ ...form, tipo: e.target.value })}
            />
          </label>
          <label className="field">
            <span>Endereço IP</span>
            <input
              required
              placeholder="192.168.0.10"
              value={form.ip_address}
              onChange={(e) => setForm({ ...form, ip_address: e.target.value })}
            />
          </label>
          <label className="field">
            <span>gNodeB associado</span>
            <input
              required
              value={form.gnodeb_associado}
              onChange={(e) => setForm({ ...form, gnodeb_associado: e.target.value })}
            />
          </label>
          <button className="btn btn-primary" type="submit" disabled={salvando}>
            {salvando ? "Salvando..." : "Cadastrar"}
          </button>
        </form>
        {formError && <div className="alert-box error">{formError}</div>}
      </section>

      <section className="panel">
        <div className="panel-header">
          <h2>Dispositivos cadastrados</h2>
        </div>
        {error && <div className="alert-box error">{error}</div>}
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Nome</th>
              <th>Tipo</th>
              <th>IP</th>
              <th>gNodeB</th>
              <th>Status</th>
              <th>Registrado em</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {dispositivos.map((d) => (
              <tr key={d.id_dispositivo}>
                <td>#{d.id_dispositivo}</td>
                <td>{d.nome_dispositivo}</td>
                <td>{d.tipo}</td>
                <td>{d.ip_address}</td>
                <td>{d.gnodeb_associado}</td>
                <td>
                  <StatusBadge value={d.status} />
                </td>
                <td>{new Date(d.registrado_em).toLocaleString("pt-BR")}</td>
                <td>
                  {d.status === "ativo" && (
                    <button
                      className="btn btn-ghost btn-small"
                      onClick={() => handleDesativar(d.id_dispositivo)}
                    >
                      Desativar
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {!loading && dispositivos.length === 0 && (
              <tr>
                <td colSpan={8} className="empty">Nenhum dispositivo cadastrado.</td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}
