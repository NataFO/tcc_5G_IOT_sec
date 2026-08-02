notepad db\01_criar_tabelas.sql

CREATE TABLE tb_usuario (
    id_usuario SERIAL PRIMARY KEY NOT NULL,
    nome_completo VARCHAR(120) NOT NULL,
    login VARCHAR(60) NOT NULL UNIQUE,
    senha_hash CHAR(64) NOT NULL,
    perfil VARCHAR(20) DEFAULT 'analista' NOT NULL,
    ativo SMALLINT DEFAULT 1 NOT NULL,
    criado_em TIMESTAMP DEFAULT NOW() NOT NULL,
    CONSTRAINT chk_perfil CHECK (perfil IN ('admin', 'analista', 'viewer')),
    CONSTRAINT chk_ativo CHECK (ativo IN (0, 1))
);


CREATE TABLE tb_dispositivo (
    id_dispositivo SERIAL PRIMARY KEY NOT NULL,
    nome_dispositivo VARCHAR(100) NOT NULL,
    tipo VARCHAR(60) NOT NULL,
    ip_address INET UNIQUE NOT NULL,
    gnodeb_associado VARCHAR(60) NOT NULL,
    status VARCHAR(10) DEFAULT 'ativo' NOT NULL,
    registrado_em TIMESTAMP DEFAULT NOW() NOT NULL,
    CONSTRAINT chk_status CHECK (status IN ('ativo', 'inativo', 'alerta'))
);

CREATE TABLE tb_log_rede (
    id_log BIGSERIAL PRIMARY KEY NOT NULL,
    id_dispositivo INT NOT NULL,
    momento_captura TIMESTAMP(6) NOT NULL,
    ip_origem INET NOT NULL,
    ip_destino INET NOT NULL,
    porta_origem INTEGER NOT NULL CHECK (porta_origem BETWEEN 0 AND 65535),
    porta_destino INTEGER NOT NULL CHECK (porta_destino BETWEEN 0 AND 65535),
    protocolo VARCHAR(10) NOT NULL,
    bytes_enviados BIGINT NOT NULL,
    pacotes_enviados INT NOT NULL,
    duracao_fluxo_ms DECIMAL(12, 3) NOT NULL,
    classificacao_ia VARCHAR(20) NOT NULL,
    probabilidade_ia DECIMAL(5, 4) NOT NULL,
    CONSTRAINT fk_log_dispositivo FOREIGN KEY (id_dispositivo)
        REFERENCES tb_dispositivo (id_dispositivo) ON DELETE RESTRICT,
    CONSTRAINT chk_classificacao CHECK (classificacao_ia IN ('Normal', 'DoS', 'DDoS', 'Brute Force')),
    CONSTRAINT chk_probabilidade CHECK (probabilidade_ia BETWEEN 0.0 AND 1.0)
);

CREATE TABLE tb_alerta (
    id_alerta SERIAL PRIMARY KEY NOT NULL,
    id_log BIGSERIAL NOT NULL,
    id_dispositivo INT NOT NULL,
    data_hora_alerta TIMESTAMP DEFAULT NOW() NOT NULL,
    tipo_ataque VARCHAR(30) NOT NULL,
    severidade VARCHAR(30) NOT NULL,
    probabilidade_confianca DECIMAL(5, 4) NOT NULL,
    status_alerta VARCHAR(20) DEFAULT 'aberto' NOT NULL,
    responsavel_id INT,
    observacoes TEXT,
    resolvido_em TIMESTAMP,
    CONSTRAINT fk_alerta_log FOREIGN KEY (id_log)
        REFERENCES tb_log_rede (id_log) ON DELETE CASCADE,
    CONSTRAINT fk_alerta_dispositivo FOREIGN KEY (id_dispositivo)
        REFERENCES tb_dispositivo (id_dispositivo) ON DELETE RESTRICT,
    CONSTRAINT fk_alerta_usr FOREIGN KEY (responsavel_id)
        REFERENCES tb_usuario (id_usuario) ON DELETE SET NULL,
    CONSTRAINT chk_tipo_ataque CHECK (tipo_ataque IN ('DoS', 'DDoS', 'Brute Force')),
    CONSTRAINT chk_severidade CHECK (severidade IN ('Baixa', 'Media', 'Alta', 'Critica')),
    CONSTRAINT chk_status_al CHECK (status_alerta IN ('aberto', 'investigando', 'falso_positivo', 'resolvido'))
);