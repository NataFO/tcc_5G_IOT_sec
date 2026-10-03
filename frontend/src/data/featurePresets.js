// Valores de exemplo para as 20 features numéricas que o modelo LSTM espera.
// Servem para testar rapidamente o POST /logs pela interface — em uso real
// esses valores viriam de uma ferramenta de captura de tráfego.
//
// Os dois presets são amostras REAIS do conjunto de teste (valores brutos,
// testes/conjunto_teste_bruto.csv), escolhidas entre as que o modelo
// classifica corretamente e com valores típicos do seu grupo. Os valores
// inventados que estavam aqui antes ficavam fora da distribuição do dataset
// e o preset "Normal" acabava classificado como ataque.
export const FEATURE_KEYS = [
  "network_packets_all_count",
  "network_packets_dst_count",
  "network_ports_src_count",
  "network_ports_all_count",
  "network_time_delta_avg",
  "network_packet_size_min",
  "network_ports_dst_count",
  "network_packets_src_count",
  "network_tcp_flags_rst_count",
  "network_tcp_flags_syn_count",
  "network_tcp_flags_ack_count",
  "network_time_delta_max",
  "network_window_size_std_deviation",
  "network_time_delta_min",
  "network_mss_max",
  "network_time_delta_std_deviation",
  "network_ttl_avg",
  "network_packet_size_max",
  "network_interval_packets",
  "network_mss_min",
];

// Tráfego benigno — amostra 2032 do conjunto de teste (probabilidade de ataque: 0.10)
export const PRESET_NORMAL = {
  network_packets_all_count: 14,
  network_packets_dst_count: 7,
  network_ports_src_count: 2,
  network_ports_all_count: 2,
  network_time_delta_avg: 0.015919786,
  network_packet_size_min: 54,
  network_ports_dst_count: 2,
  network_packets_src_count: 7,
  network_tcp_flags_rst_count: 0,
  network_tcp_flags_syn_count: 0,
  network_tcp_flags_ack_count: 14,
  network_time_delta_max: 0.067932,
  network_window_size_std_deviation: 29218.571436953,
  network_time_delta_min: 0,
  network_mss_max: 0,
  network_time_delta_std_deviation: 0.023477818,
  network_ttl_avg: 159.5,
  network_packet_size_max: 72,
  network_interval_packets: 308.615384615,
  network_mss_min: 0,
};

// Ataque DDoS — amostra 4789 do conjunto de teste (probabilidade de ataque: 1.00)
export const PRESET_ATAQUE = {
  network_packets_all_count: 120795,
  network_packets_dst_count: 120625,
  network_ports_src_count: 28911,
  network_ports_all_count: 28911,
  network_time_delta_avg: 1.0861e-05,
  network_packet_size_min: 60,
  network_ports_dst_count: 166,
  network_packets_src_count: 170,
  network_tcp_flags_rst_count: 164,
  network_tcp_flags_syn_count: 0,
  network_tcp_flags_ack_count: 164,
  network_time_delta_max: 0.019545306,
  network_window_size_std_deviation: 142.429407225,
  network_time_delta_min: 2.6e-08,
  network_mss_max: 0,
  network_time_delta_std_deviation: 8.5158e-05,
  network_ttl_avg: 64.26090736,
  network_packet_size_max: 230,
  network_interval_packets: 0.022078911,
  network_mss_min: 0,
};
