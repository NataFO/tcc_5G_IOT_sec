import { useEffect, useRef, useState } from "react";
import { api } from "../api";

// De quanto em quanto tempo o painel pergunta à API se há alertas novos.
// O critério do CT05 é exibir a notificação em até 1 s depois de o alerta
// ser gravado; consultando a cada 0,5 s, o pior caso fica em ~0,5 s mais o
// tempo da própria consulta. (Em produção, o ideal seria o servidor
// "empurrar" o alerta via WebSocket/SSE em vez de o painel perguntar.)
const INTERVALO_MS = 500;
const TEMPO_NA_TELA_MS = 8000;
const MAX_NA_TELA = 3;

// Só mostra o atraso medido quando os dois relógios são comparáveis
// (servidor e navegador na mesma máquina/fuso). Com o backend na nuvem
// em UTC, a diferença de fuso daria um número sem sentido.
function atrasoConfiavel(ms) {
  return ms >= 0 && ms < 60 * 60 * 1000;
}

export default function AlertNotifier() {
  const ultimoId = useRef(null); // maior id_alerta já visto
  const [avisos, setAvisos] = useState([]);

  useEffect(() => {
    let ativo = true;
    let timer;

    async function verificar() {
      try {
        const dados = await api.listarAlertas({ limite: 20 });
        if (!ativo) return;
        const maiorId = dados.reduce((m, a) => Math.max(m, a.id_alerta), 0);

        if (ultimoId.current === null) {
          // Primeira consulta: só memoriza o ponto de partida, sem notificar
          // os alertas que já existiam antes de a página abrir.
          ultimoId.current = maiorId;
        } else if (maiorId > ultimoId.current) {
          const agora = Date.now();
          const novos = dados
            .filter((a) => a.id_alerta > ultimoId.current)
            .sort((a, b) => b.id_alerta - a.id_alerta)
            .map((a) => {
              const atrasoMs = agora - new Date(a.data_hora_alerta).getTime();
              // Registro no console do navegador (F12) — útil como evidência do CT05.
              console.info(
                `[CT05] alerta #${a.id_alerta} exibido ${Math.round(atrasoMs)} ms após ser gravado`
              );
              return { ...a, atrasoMs, chave: `${a.id_alerta}-${agora}` };
            });
          ultimoId.current = maiorId;
          setAvisos((atuais) => [...novos, ...atuais].slice(0, MAX_NA_TELA));
          // Avisa as outras telas (ex.: Visão geral) para recarregarem os dados.
          window.dispatchEvent(new CustomEvent("novo-alerta"));
        }
      } catch {
        // Falha de rede momentânea: tenta de novo no próximo ciclo.
      }
      if (ativo) timer = setTimeout(verificar, INTERVALO_MS);
    }

    verificar();
    return () => {
      ativo = false;
      clearTimeout(timer);
    };
  }, []);

  // Cada aviso some sozinho depois de alguns segundos.
  useEffect(() => {
    if (avisos.length === 0) return;
    const t = setTimeout(() => setAvisos((a) => a.slice(0, -1)), TEMPO_NA_TELA_MS);
    return () => clearTimeout(t);
  }, [avisos]);

  if (avisos.length === 0) return null;

  return (
    <div
      role="status"
      aria-live="assertive"
      style={{
        position: "fixed",
        right: 20,
        bottom: 20,
        display: "flex",
        flexDirection: "column",
        gap: 10,
        zIndex: 1000,
        width: 340,
      }}
    >
      {avisos.map((a) => (
        <div
          key={a.chave}
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderLeft: "4px solid var(--danger)",
            borderRadius: "var(--radius)",
            padding: "12px 14px",
            boxShadow: "0 8px 24px rgba(0,0,0,0.35)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
            <strong style={{ color: "#ff8a8d" }}>
              Novo alerta #{a.id_alerta}: {a.tipo_ataque}
            </strong>
            <button
              onClick={() => setAvisos((lista) => lista.filter((x) => x.chave !== a.chave))}
              aria-label="Fechar"
              style={{
                background: "transparent",
                border: "none",
                color: "var(--text-muted)",
                cursor: "pointer",
                fontSize: 16,
                lineHeight: 1,
              }}
            >
              ×
            </button>
          </div>
          <div style={{ fontSize: 13, marginTop: 4 }}>
            {a.nome_dispositivo || `Dispositivo #${a.id_dispositivo}`} · severidade{" "}
            {a.severidade} · confiança {(a.probabilidade_confianca * 100).toFixed(1)}%
          </div>
          <div style={{ fontSize: 12, marginTop: 4, color: "var(--text-muted)" }}>
            {new Date(a.data_hora_alerta).toLocaleTimeString("pt-BR")}
            {atrasoConfiavel(a.atrasoMs) &&
              ` · exibido ${Math.round(a.atrasoMs)} ms após o alerta ser gravado`}
          </div>
        </div>
      ))}
    </div>
  );
}
