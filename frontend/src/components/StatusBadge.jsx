const TONES = {
  Normal: "ok",
  DDoS: "danger",
  DoS: "danger",
  "Brute Force": "danger",
  Baixa: "info",
  Media: "warn",
  Alta: "danger",
  Critica: "danger",
  ativo: "ok",
  inativo: "muted",
  alerta: "warn",
  aberto: "warn",
  investigando: "info",
  falso_positivo: "muted",
  resolvido: "ok",
};

export default function StatusBadge({ value }) {
  if (!value) return <span className="badge muted">—</span>;
  const tone = TONES[value] || "muted";
  return <span className={`badge ${tone}`}>{value}</span>;
}
