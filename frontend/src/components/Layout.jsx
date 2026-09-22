import { NavLink, useNavigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const links = [
  { to: "/", label: "Visão geral", end: true },
  { to: "/dispositivos", label: "Dispositivos" },
  { to: "/logs", label: "Logs de rede" },
  { to: "/alertas", label: "Alertas" },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">5G</span>
          <div>
            <strong>Segurança 5G/IoT</strong>
            <span className="brand-sub">Detecção com IA</span>
          </div>
        </div>

        <nav className="nav">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="main">
        <header className="topbar">
          <div />
          <div className="user-box">
            <div className="user-info">
              <strong>{user?.login || "usuário"}</strong>
              <span>{user?.perfil || ""}</span>
            </div>
            <button className="btn btn-ghost" onClick={handleLogout}>
              Sair
            </button>
          </div>
        </header>

        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
