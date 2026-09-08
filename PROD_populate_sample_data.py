"""
Script de Carga de Dados de Exemplo para Homologação e Demonstração (PROD_populate_sample_data.py).
Popula as tabelas relacionais em inglês do PostgreSQL com casos realistas da esteira Sicredi:
- Associados titulares e intervenientes
- Processos de Crédito, Seguros e Contas
- Jornadas em andamento e concluídas
- Envelopes clusterizados e versionados (V1 e V2 com substituição seletiva)
- Documentos PDFs associados
- Signatários vinculados com canais (E-mail e WhatsApp)
- Registros de auditoria no histórico de manutenção
Nomes 100% em inglês com docstrings em português.
"""

import sys
import os
from datetime import datetime, timedelta

# Adiciona a raiz do projeto no PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Suporte a UTF-8 no Windows Console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from microservico.infrastructure.db import DatabaseManager
from microservico.infrastructure.initializer import initialize_database_if_empty
from microservico.infrastructure.repositories import (
    AssociateRepository,
    ProcessRepository,
    JourneyRepository,
    EnvelopeRepository,
    DocumentRepository,
    EnvelopeSignerRepository,
    MaintenanceHistoryRepository
)
from microservico.domain.enums import (
    JourneyStatus,
    EnvelopeStatus,
    SignerStatus,
    DocumentStatus,
    ProviderType,
    SignatureType,
    ValidationChannel,
    MaintenanceReason
)
from microservico.config import config


def populate_sample_data() -> bool:
    """
    Popula o banco de dados PostgreSQL com instâncias e relacionamentos realistas de teste.

    Retorno:
        bool: True se a carga foi executada com sucesso.
    """
    print("=" * 75)
    print("POPULANDO BANCO DE DADOS POSTGRESQL COM DADOS DE EXEMPLO (PRODUÇÃO)")
    print("=" * 75)

    dsn = f"host={config.DB_HOST} port={config.DB_PORT} dbname={config.DB_NAME} user={config.DB_USER} password={config.DB_PASSWORD}"
    print(f"📡 Conectando ao PostgreSQL em: {config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}...")

    db_mgr = DatabaseManager(dsn=dsn, use_sqlite=False)
    initialize_database_if_empty(db_mgr)
    print("✅ Schema PROD_schema.sql e processos verificados!")

    assoc_repo = AssociateRepository(db_mgr)
    proc_repo = ProcessRepository(db_mgr)
    journey_repo = JourneyRepository(db_mgr)
    env_repo = EnvelopeRepository(db_mgr)
    doc_repo = DocumentRepository(db_mgr)
    signer_repo = EnvelopeSignerRepository(db_mgr)
    manut_repo = MaintenanceHistoryRepository(db_mgr)

    # 1. Associados
    print("\n1. Inserindo Associados de Exemplo...")
    assoc_1 = assoc_repo.upsert(tax_id="02631353900", name="EDILSON PAULO DE FRANCA", email="francaedilson78@gmail.com", phone="42988187402")
    assoc_2 = assoc_repo.upsert(tax_id="11158072937", name="PEDRO HENRIQUE LOPES", email="pedro_hlopes@sicredi.com.br", phone="42999843189")
    assoc_3 = assoc_repo.upsert(tax_id="08489951985", name="MARIA SILVA TESTEMUNHA", email="maria.testemunha@gmail.com", phone="41988887777")
    assoc_4 = assoc_repo.upsert(tax_id="12345678000199", name="COOPERATIVA AGROPECUARIA SICREDI LTDA", email="contato@agrocoop.com.br", phone="4133334444")
    print(f"   -> 4 Associados persistidos ({assoc_1.name}, {assoc_2.name}, {assoc_3.name}, {assoc_4.name}).")

    # 2. Processos
    print("\n2. Recuperando Tipos de Processos do Catálogo...")
    proc_credito = proc_repo.get_or_create(name="Solicitação de Crédito Comercial V2")
    proc_seguros = proc_repo.get_or_create(name="Renovação Seguros V2")
    print(f"   -> Processo Crédito: {proc_credito.name}")
    print(f"   -> Processo Seguros: {proc_seguros.name}")

    # 3. Jornada 1: Crédito Comercial com 2 Envelopes (Cluster Documental)
    print("\n3. Criando Jornada de Crédito Comercial #1225591...")
    journey_1 = journey_repo.create_journey(
        process_id=proc_credito.id,
        mongo_id="mongo_proc_1225591",
        process_number=1225591,
        fluid_payload={"etapa": "Formalização", "cooperativa": "0703", "agencia": "11"}
    )
    journey_repo.update_status(journey_1.id, JourneyStatus.IN_PROCESS, "Envelopes enviados para assinatura dos titulares.")

    # Envelope 1 (Edilson assina CCB e CET)
    scope_hash_1 = "hash_escopo_ccb_cet_765_678"
    env_1 = env_repo.create_envelope(
        request_id=journey_1.id,
        document_scope_hash=scope_hash_1,
        provider=ProviderType.CERTISIGN,
        envelope_version=1
    )
    env_repo.update_external_id(env_1.id, "openapi_env_credito_001", EnvelopeStatus.PENDING_SIGNATURE)

    # Documentos do Envelope 1
    doc_1 = doc_repo.add_document(
        envelope_id=env_1.id,
        associate_id=assoc_1.id,
        file_name="765 - CCB Cédula de Crédito Bancário.pdf",
        source_hash="sha256_ccb_binary_001",
        document_type_id=765
    )
    doc_2 = doc_repo.add_document(
        envelope_id=env_1.id,
        associate_id=assoc_1.id,
        file_name="678 - CET Custo Efetivo Total.pdf",
        source_hash="sha256_cet_binary_002",
        document_type_id=678
    )

    # Signatários do Envelope 1
    signer_repo.add_signer(
        envelope_id=env_1.id,
        associate_id=assoc_1.id,
        signer_role="Titular",
        signature_order=1,
        signature_type=SignatureType.ELECTRONIC,
        validation_channel=ValidationChannel.EMAIL
    )
    signer_repo.add_signer(
        envelope_id=env_1.id,
        associate_id=assoc_2.id,
        signer_role="Avalista / Garantidor",
        signature_order=2,
        signature_type=SignatureType.ELECTRONIC,
        validation_channel=ValidationChannel.WHATSAPP
    )
    print(f"   -> Envelope 1 criado (ID: {env_1.id}, Versão 1, 2 Docs, 2 Signatários).")

    # 4. Jornada 2: Renovação de Seguros com Substituição Seletiva (V1 -> V2)
    print("\n4. Criando Jornada de Seguros com Substituição Seletiva #1160705...")
    journey_2 = journey_repo.create_journey(
        process_id=proc_seguros.id,
        mongo_id="mongo_proc_1160705",
        process_number=1160705,
        fluid_payload={"apolice": "AP-999888", "ramo": "Vida"}
    )

    scope_hash_seg = "hash_escopo_seguro_vida_613"
    # Versão 1 (Substituída / Cancelada)
    env_v1 = env_repo.create_envelope(
        request_id=journey_2.id,
        document_scope_hash=scope_hash_seg,
        provider=ProviderType.CERTISIGN,
        envelope_version=1
    )
    env_repo.update_external_id(env_v1.id, "openapi_env_seguro_antigo", EnvelopeStatus.PENDING_SIGNATURE)
    env_repo.mark_replaced_cancelled(env_v1.id)

    # Versão 2 (Ativa)
    env_v2 = env_repo.create_envelope(
        request_id=journey_2.id,
        document_scope_hash=scope_hash_seg,
        provider=ProviderType.CERTISIGN,
        envelope_version=2
    )
    env_repo.update_external_id(env_v2.id, "openapi_env_seguro_v2_novo", EnvelopeStatus.PENDING_SIGNATURE)

    doc_repo.add_document(
        envelope_id=env_v2.id,
        associate_id=assoc_1.id,
        file_name="613 - Proposta de Seguro Vida V2.pdf",
        source_hash="sha256_seguro_v2_binary",
        document_type_id=613
    )
    signer_repo.add_signer(
        envelope_id=env_v2.id,
        associate_id=assoc_1.id,
        signer_role="Proponente",
        signature_order=1,
        signature_type=SignatureType.ELECTRONIC,
        validation_channel=ValidationChannel.EMAIL
    )

    # Registro no Histórico de Manutenção
    manut_repo.log_maintenance(
        request_id=journey_2.id,
        envelope_id=env_v1.id,
        reason_code=MaintenanceReason.DOC_VERSION_CHANGE,
        detailed_description="Proposta de seguro reenviada com nova versão do documento PDF retificada pelo operador."
    )
    print(f"   -> Envelope V1 (ID: {env_v1.id}) marcado como REPLACED_CANCELED.")
    print(f"   -> Envelope V2 (ID: {env_v2.id}) criado e ativo.")

    # 5. Envelope Expirado (> 60 Dias)
    print("\n5. Criando Caso de Envelope Expirado (> 60 Dias)...")
    env_exp = env_repo.create_envelope(
        request_id=journey_1.id,
        document_scope_hash="hash_escopo_expirado_antigo",
        provider=ProviderType.CERTISIGN,
        envelope_version=1
    )
    env_repo.update_external_id(env_exp.id, "openapi_env_expirado_legado", EnvelopeStatus.PENDING_SIGNATURE)

    # Retrocede data de expiração no SQL direto
    conn = db_mgr.get_connection()
    past_date = datetime.now() - timedelta(days=65)
    with conn.cursor() as cur:
        cur.execute("UPDATE envelopes SET expired_at = %s WHERE id = %s", (past_date, str(env_exp.id)))
    conn.commit()
    conn.close()

    manut_repo.log_maintenance(
        request_id=journey_1.id,
        envelope_id=env_exp.id,
        reason_code=MaintenanceReason.EXPIRED_60_DAYS,
        detailed_description="Envelope pendente expirou automaticamente por exceder prazo de 60 dias corridos."
    )
    print(f"   -> Envelope Expirado (ID: {env_exp.id}) com log de auditoria EXPIRED_60_DAYS gerado.")

    print("\n" + "=" * 75)
    print("CARGA DE DADOS FICTÍCIOS EXECUTADA COM SUCESSO NO POSTGRESQL!")
    print("=" * 75)
    return True


if __name__ == "__main__":
    success = populate_sample_data()
    sys.exit(0 if success else 1)
