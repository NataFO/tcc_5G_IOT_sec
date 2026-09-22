import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ login: "", senha: "" });
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const from = location.state?.from?.pathname || "/";

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(form.login, form.senha);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.message || "Não foi possível entrar");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-screen">
      <form className="auth-card" onSubmit={handleSubmit}>
        <div className="brand brand-center">
          <span className="brand-mark">5G</span>
          <div>
            <strong>Segurança 5G/IoT</strong>
            <span className="brand-sub">Painel de monitoramento</span>
          </div>
        </div>

        <label className="field">
          <span>Login</span>
          <input
            type="text"
            value={form.login}
            onChange={(e) => setForm({ ...form, login: e.target.value })}
            autoFocus
            required
          />
        </label>

        <label className="field">
          <span>Senha</span>
          <input
            type="password"
            value={form.senha}
            onChange={(e) => setForm({ ...form, senha: e.target.value })}
            required
          />
        </label>

        {error && <div className="alert-box error">{error}</div>}

        <button className="btn btn-primary" type="submit" disabled={loading}>
          {loading ? "Entrando..." : "Entrar"}
        </button>
      </form>
    </div>
  );
}
