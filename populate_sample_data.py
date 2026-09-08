import os
import sys
import json
from datetime import datetime, timedelta
from uuid import uuid4

# Adiciona a raiz do projeto no PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Suporte a UTF-8 no Windows Console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from microservico.infrastructure.db import DatabaseManager
from microservico.infrastructure.initializer import initialize_database_if_empty
from microservico.infrastructure.repositories import (
    AssociadoRepository,
    ProcessoRepository,
    JornadaRepository,
    EnvelopeRepository,
    DocumentoRepository,
    EnvelopeSignatarioRepository,
    HistoricoManutencaoRepository
)
from microservico.domain.enums import (
    StatusJornada,
    StatusEnvelope,
    StatusSignatario,
    StatusDocumento,
    ProviderEnum,
    TipoAssinaturaEnum,
    CanalValidacaoEnum,
    MotivoManutencaoEnum
)

def populate_sample_data():
    """
    Popula o banco de dados PostgreSQL com dados fictícios ricos e realistas
    para permitir a análise visual de relacionamentos entre tabelas.
    """
    print("=" * 75)
    print("POPULANDO BANCO DE DADOS POSTGRESQL COM DADOS FICTÍCIOS DE EXEMPLO")
    print("=" * 75)

    db_host = os.getenv("DB_HOST", "localhost")
    db_port = int(os.getenv("DB_PORT", "5432"))
    db_name = os.getenv("DB_NAME", "docjourney_db")
    db_user = os.getenv("DB_USER", "postgres")
    db_pass = os.getenv("DB_PASSWORD", "senha123")

    dsn = f"host={db_host} port={db_port} dbname={db_name} user={db_user} password={db_pass}"
    print(f"📡 Conectando ao PostgreSQL em: {db_host}:{db_port}/{db_name}...")

    db_mgr = DatabaseManager(dsn=dsn, use_sqlite=False)
    
    # 1. Garante que o schema e dados iniciais existem
    initialize_database_if_empty(db_mgr)
    print("✅ Schema verificado!")

    # Repositórios
    assoc_repo = AssociadoRepository(db_mgr)
    proc_repo = ProcessoRepository(db_mgr)
    jornada_repo = JornadaRepository(db_mgr)
    env_repo = EnvelopeRepository(db_mgr)
    doc_repo = DocumentoRepository(db_mgr)
    sig_repo = EnvelopeSignatarioRepository(db_mgr)
    manut_repo = HistoricoManutencaoRepository(db_mgr)

    # 2. Criar / Obter Associados (Pessoas Físicas e Jurídicas)
    print("\n1️⃣ Criando/Atualizando Associados de Exemplo...")
    assoc_edilson = assoc_repo.upsert(
        cpf_cnpj="02631353900",
        nome="EDILSON PAULO DE FRANCA",
        email="francaedilson78@gmail.com",
        telefone="42988187402"
    )
    print(f"   -> Associado 1: {assoc_edilson.nome} (ID: {assoc_edilson.id})")

    assoc_aila = assoc_repo.upsert(
        cpf_cnpj="11158072937",
        nome="AILA ELO DE FRANCA",
        email="aila.franca@gmail.com",
        telefone="42999843189"
    )
    print(f"   -> Associado 2: {assoc_aila.nome} (ID: {assoc_aila.id})")

    assoc_pedro = assoc_repo.upsert(
        cpf_cnpj="08489951985",
        nome="PEDRO HENRIQUE LOPES",
        email="pedro.lopes@sicredi.com.br",
        telefone="42999400038"
    )
    print(f"   -> Associado 3: {assoc_pedro.nome} (ID: {assoc_pedro.id})")

    # 3. Criar Processos da Esteira
    print("\n2️⃣ Criando/Obtendo Tipos de Processo...")
    proc_credito = proc_repo.get_or_create("Solicitação de Crédito Comercial V2", "Operações de crédito PJ/PF")
    proc_seguros = proc_repo.get_or_create("Renovação Seguros V2", "Apólices de seguro de vida e automóvel")
    print(f"   -> Processo Crédito ID: {proc_credito.id}")
    print(f"   -> Processo Seguros ID: {proc_seguros.id}")

    # 4. Criar Jornadas / Solicitações (MongoDB Fluid Tasks)
    print("\n3️⃣ Criando Jornadas / Solicitações de Exemplo...")
    
    # Jornada 1: Crédito Comercial (Processo 1225591)
    jornada_credito = jornada_repo.create_jornada(
        id_processo=proc_credito.id,
        mongo_id="6a9b225987db9287e3dde60c",
        num_processo=1225591,
        payload_fluid={
            "num_processo": 1225591,
            "nome_processo": "Solicitação de Crédito Comercial V2",
            "empresa": "VITAL ESPORTE LTDA"
        },
        id_inicial="6a9b21a287db9287e3dde53d"
    )
    jornada_repo.update_status(jornada_credito.id, StatusJornada.EM_PROCESSAMENTO, "Aguardando assinaturas dos envelopes")
    print(f"   -> Jornada 1 (Crédito #1225591) criada! ID: {jornada_credito.id}")

    # Jornada 2: Renovação Seguros (Processo 1160705)
    jornada_seguro = jornada_repo.create_jornada(
        id_processo=proc_seguros.id,
        mongo_id="6a294e101b86f230b17588d1",
        num_processo=1160705,
        payload_fluid={
            "num_processo": 1160705,
            "nome_processo": "Renovação Seguros V2"
        },
        id_inicial="6a2948e51b86f230b174478"
    )
    jornada_repo.update_status(jornada_seguro.id, StatusJornada.INTERVENCAO, "Envelope expirado sem assinatura após 60 dias")
    print(f"   -> Jornada 2 (Seguros #1160705) criada! ID: {jornada_seguro.id}")

    # 5. Criar Envelopes Clusterizados por Escopo Documental
    print("\n4️⃣ Criando Envelopes Clusterizados no PostgreSQL...")

    # Cluster Hash 1 (Jornada 1): CCB + CET (Edilson & Aila)
    hash_ccb_cet = "hash_cluster_ccb_cet_998127391823"
    env_1 = env_repo.create_envelope(
        id_solicitacao=jornada_credito.id,
        hash_escopo_documentos=hash_ccb_cet,
        provider=ProviderEnum.CERTISIGN,
        versao_envelope=1,
        permitir_ordem_assinatura=True
    )
    env_repo.update_external_id(env_1.id, "openapi_env_credito_ccb_01", StatusEnvelope.ASSINATURA_PENDENTE)
    print(f"   -> Envelope 1 (CCB + CET) criado! ID: {env_1.id} (External ID: openapi_env_credito_ccb_01)")

    # Cluster Hash 2 (Jornada 1): Seguro Prestamista (Apenas Edilson)
    hash_prestamista = "hash_cluster_prestamista_882910391203"
    env_2 = env_repo.create_envelope(
        id_solicitacao=jornada_credito.id,
        hash_escopo_documentos=hash_prestamista,
        provider=ProviderEnum.ADESAO,
        versao_envelope=1,
        permitir_ordem_assinatura=False
    )
    env_repo.update_external_id(env_2.id, "openapi_env_credito_prest_02", StatusEnvelope.CONCLUIDO)
    print(f"   -> Envelope 2 (Prestamista) criado! ID: {env_2.id} (External ID: openapi_env_credito_prest_02)")

    # Cluster Hash 3 (Jornada 2): Seguro Auto (Pedro) - EXPIRADO
    hash_seguro_auto = "hash_cluster_seguro_auto_1122334455"
    env_3 = env_repo.create_envelope(
        id_solicitacao=jornada_seguro.id,
        hash_escopo_documentos=hash_seguro_auto,
        provider=ProviderEnum.CERTISIGN,
        versao_envelope=1
    )
    env_repo.update_external_id(env_3.id, "openapi_env_seguro_expirado_03", StatusEnvelope.EXPIRADO)
    print(f"   -> Envelope 3 (Seguro Auto) criado! ID: {env_3.id} (Status: EXPIRADO)")

    # 6. Criar Documentos do Envelope
    print("\n5️⃣ Vinculando Documentos aos Envelopes...")
    doc_repo.add_documento(env_1.id, assoc_edilson.id, "765 - CCB Crédito Comercial.pdf", "hash_ccb_bin_123", tipo_doc_id=765)
    doc_repo.add_documento(env_1.id, assoc_aila.id, "678 - CET Custo Efetivo Total.pdf", "hash_cet_bin_456", tipo_doc_id=678)
    doc_repo.add_documento(env_2.id, assoc_edilson.id, "613 - Seguro Prestamista.pdf", "hash_prestamista_bin_789", tipo_doc_id=613)
    doc_repo.add_documento(env_3.id, assoc_pedro.id, "550 - Proposta Seguro Auto.pdf", "hash_proposta_bin_999", tipo_doc_id=550)
    print("   ✅ Documentos associados com sucesso!")

    # 7. Criar Signatários do Envelope
    print("\n6️⃣ Vinculando Signatários e Canais aos Envelopes...")
    sig_repo.add_signatario(
        id_envelope=env_1.id,
        id_associado=assoc_edilson.id,
        papel_assinante="Titular da Conta / Avalista",
        ordem_assinatura=1,
        tipo_assinatura=TipoAssinaturaEnum.ELETRONIC,
        canal_validacao=CanalValidacaoEnum.EMAIL
    )
    sig_repo.add_signatario(
        id_envelope=env_1.id,
        id_associado=assoc_aila.id,
        papel_assinante="Cônjuge Avalista",
        ordem_assinatura=2,
        tipo_assinatura=TipoAssinaturaEnum.ELETRONIC,
        canal_validacao=CanalValidacaoEnum.WHATSAPP
    )
    sig_repo.add_signatario(
        id_envelope=env_2.id,
        id_associado=assoc_edilson.id,
        papel_assinante="Segurado",
        ordem_assinatura=1,
        tipo_assinatura=TipoAssinaturaEnum.ELETRONIC,
        canal_validacao=CanalValidacaoEnum.EMAIL
    )
    sig_repo.add_signatario(
        id_envelope=env_3.id,
        id_associado=assoc_pedro.id,
        papel_assinante="Segurado Principal",
        ordem_assinatura=1,
        tipo_assinatura=TipoAssinaturaEnum.DIGITAL,
        canal_validacao=CanalValidacaoEnum.EMAIL
    )
    print("   ✅ Signatários vinculados com sucesso!")

    # 8. Logar Histórico de Manutenção
    print("\n7️⃣ Registrando Auditoria de Manutenção...")
    manut_repo.log_manutencao(
        id_solicitacao=jornada_seguro.id,
        id_envelope=env_3.id,
        motivo_codigo=MotivoManutencaoEnum.EXPIRADO_60_DIAS,
        descricao_detalhada="Envelope openapi_env_seguro_expirado_03 cancelado via DELETE /v2/envelope por atingir 60 dias sem conclusão."
    )
    print("   ✅ Histórico de Manutenção gravado!")

    print("\n" + "=" * 75)
    print("🎉 BANCO DE DADOS POSTGRESQL POPULADO COM DADOS FICTÍCIOS COM SUCESSO!")
    print("=" * 75)

if __name__ == "__main__":
    populate_sample_data()
