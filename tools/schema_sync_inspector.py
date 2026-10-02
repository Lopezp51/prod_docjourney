#!/usr/bin/env python3
"""
tools/schema_sync_inspector.py
==============================
Utilitário de Introspecção, Comparação (Diff) e Adaptação de Schemas.
Compara schemas do microsserviço/PAS contra o Banco de Dados (SQL) e Automação (RPA).

Uso:
  1. Inspecionar a partir de URL do OpenAPI (ex: FastAPI local ou microsserviço):
     python tools/schema_sync_inspector.py --url http://127.0.0.1:8000/openapi.json

  2. Inspecionar a partir de arquivo JSON de schema local:
     python tools/schema_sync_inspector.py --file caminho/do/schema.json

  3. Inspecionar a partir dos schemas Pydantic internos do projeto:
     python tools/schema_sync_inspector.py --from-pydantic

Gera:
  - Relatório no console com diff de campos (Novos, Faltantes, Divergentes)
  - Arquivo 'migration_patch.sql' com comandos ALTER TABLE prontos
  - Arquivo 'adapter_patch.py' com código Python de modelos e mapeamentos
"""

import os
import sys
import re
import json
import argparse
from typing import Dict, Any, List, Set, Tuple, Optional
from dataclasses import dataclass, field

# Configura UTF-8 no stdout para Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Garante inclusão do diretório raiz no PYTHONPATH
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


# Mapeamento de tipos OpenAPI/JSON Schema -> PostgreSQL
JSON_TYPE_TO_PG = {
    "string": "VARCHAR(255)",
    "string:date-time": "TIMESTAMP WITH TIME ZONE",
    "string:uuid": "UUID",
    "integer": "INTEGER",
    "number": "NUMERIC(15, 2)",
    "boolean": "BOOLEAN",
    "array": "JSONB",
    "object": "JSONB"
}

# Mapeamento conceitual entre Schemas da API e Tabelas do Banco de Dados
SCHEMA_TO_TABLE_MAPPING = {
    "envelope": "envelopes",
    "envelopecreate": "envelopes",
    "envelopecreaterequest": "envelopes",
    "enveloperesponse": "envelopes",
    "signer": "envelope_signers",
    "signercreate": "envelope_signers",
    "signercreateitem": "envelope_signers",
    "document": "documents",
    "documentcreate": "documents",
    "documentcreateitem": "documents",
    "journey": "journey_requests",
    "journeycreate": "journey_requests",
    "journeycreaterequest": "journey_requests",
    "journeyresponse": "journey_requests",
    "associate": "associates",
    "maintenance": "maintenance_history"
}


@dataclass
class FieldSpec:
    name: str
    data_type: str
    pg_type: str
    required: bool = False
    description: str = ""
    default: Any = None


def parse_sql_columns_from_ddl(sql_path: str) -> Dict[str, Set[str]]:
    """Extrai os nomes de colunas por tabela a partir de um arquivo SQL DDL."""
    if not os.path.exists(sql_path):
        return {}

    with open(sql_path, "r", encoding="utf-8") as f:
        content = f.read()

    tables: Dict[str, Set[str]] = {}
    table_pattern = re.compile(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)\s*\((.*?)\);",
        re.DOTALL | re.IGNORECASE
    )

    for match in table_pattern.finditer(content):
        tbl_name = match.group(1).lower()
        cols_body = match.group(2)
        columns = set()

        for line in cols_body.split("\n"):
            line = line.strip().rstrip(",")
            if not line or line.startswith("--") or line.upper().startswith("CONSTRAINT") or line.upper().startswith("PRIMARY"):
                continue
            parts = line.split()
            if parts:
                col_name = parts[0].strip('"`[]')
                if not col_name.upper() in ("PRIMARY", "FOREIGN", "KEY", "CONSTRAINT", "CHECK", "UNIQUE"):
                    columns.add(col_name.lower())

        tables[tbl_name] = columns

    # Também verifica comandos ALTER TABLE ADD COLUMN
    alter_pattern = re.compile(
        r"ALTER\s+TABLE\s+(\w+)\s+ADD\s+COLUMN\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)",
        re.IGNORECASE
    )
    for match in alter_pattern.finditer(content):
        tbl = match.group(1).lower()
        col = match.group(2).lower()
        if tbl in tables:
            tables[tbl].add(col)
        else:
            tables[tbl] = {col}

    return tables


def extract_openapi_schemas(openapi_dict: Dict[str, Any]) -> Dict[str, Dict[str, FieldSpec]]:
    """Extrai entidades e campos de uma especificação OpenAPI 3.0 ou Swagger 2.0."""
    schemas = (
        openapi_dict.get("components", {}).get("schemas", {})
        or openapi_dict.get("definitions", {})
    )

    parsed_entities: Dict[str, Dict[str, FieldSpec]] = {}

    for entity_name, entity_def in schemas.items():
        properties = entity_def.get("properties", {})
        required_list = entity_def.get("required", [])

        fields_dict: Dict[str, FieldSpec] = {}
        for prop_name, prop_meta in properties.items():
            raw_type = prop_meta.get("type", "string")
            fmt = prop_meta.get("format")
            type_key = f"{raw_type}:{fmt}" if fmt and f"{raw_type}:{fmt}" in JSON_TYPE_TO_PG else raw_type
            pg_type = JSON_TYPE_TO_PG.get(type_key, JSON_TYPE_TO_PG.get(raw_type, "VARCHAR(255)"))

            if raw_type == "string" and prop_name.endswith("_id") and "uuid" in prop_name:
                pg_type = "UUID"
            elif raw_type == "string" and (prop_name.endswith("_hash") or "hash" in prop_name):
                pg_type = "VARCHAR(64)"

            fields_dict[prop_name] = FieldSpec(
                name=prop_name,
                data_type=raw_type,
                pg_type=pg_type,
                required=(prop_name in required_list),
                description=prop_meta.get("description", ""),
                default=prop_meta.get("default")
            )

        if fields_dict:
            parsed_entities[entity_name] = fields_dict

# Aliases e sinônimos conhecidos entre o mundo PAS / Microsserviço / Banco / RPA
KNOWN_ALIASES: Dict[str, Set[str]] = {
    "tax_id": {"cpf", "cnpj", "tax_id", "cpf_cnpj", "documento"},
    "name": {"name", "nome", "file_name", "signer_name", "document_name"},
    "order": {"order", "ordem", "signature_order"},
    "role": {"role", "papel", "signer_role", "flow_role"},
    "phone": {"phone", "telefone", "celular"},
    "email": {"email", "e_mail", "mail"},
    "signature_type": {"signature_type", "tipo_assinatura"},
    "validation_channel": {"validation_channel", "canal_validacao"},
    "document_hash": {"document_hash", "source_hash", "hash", "hash_code"},
    "template_id": {"template_id", "tipo_doc_id", "doc_type_id", "configuration_id"},
    "status": {"status", "journey_status", "envelope_status", "signature_status"},
    "external_envelope_id": {"external_envelope_id", "external_id", "envelope_id"}
}


def matches_alias(field_a: str, field_b: str) -> bool:
    """Verifica se dois nomes de campos são idênticos ou sinônimos conhecidos."""
    a = field_a.lower()
    b = field_b.lower()
    if a == b:
        return True
    for canon, aliases in KNOWN_ALIASES.items():
        if a in aliases and b in aliases:
            return True
    return False


def extract_automation_models() -> Dict[str, Set[str]]:
    """Extrai atributos dos modelos de domínio da automação RPA."""
    try:
        from automacao.domain import models as auto_models
        auto_entities: Dict[str, Set[str]] = {}
        for attr_name in ("SignerData", "AttachmentData", "DocumentTypeMapping"):
            cls = getattr(auto_models, attr_name, None)
            if cls and hasattr(cls, "__dataclass_fields__"):
                auto_entities[attr_name] = set(cls.__dataclass_fields__.keys())
        return auto_entities
    except Exception as e:
        print(f"[AVISO] Não foi possível inspecionar automacao.domain.models: {e}")
        return {}


def extract_pydantic_schemas_from_code() -> Dict[str, Dict[str, FieldSpec]]:
    """Extrai schemas diretamente dos modelos Pydantic do microsserviço."""
    try:
        from microservico.api import schemas as ms_schemas
    except ImportError:
        print("[AVISO] Não foi possível importar 'microservico.api.schemas'.")
        return {}

    parsed_entities: Dict[str, Dict[str, FieldSpec]] = {}
    import pydantic

    for attr_name in dir(ms_schemas):
        cls = getattr(ms_schemas, attr_name)
        if isinstance(cls, type) and issubclass(cls, pydantic.BaseModel) and cls is not pydantic.BaseModel:
            schema_dict = cls.model_json_schema() if hasattr(cls, "model_json_schema") else cls.schema()
            properties = schema_dict.get("properties", {})
            required_list = schema_dict.get("required", [])
            fields_dict: Dict[str, FieldSpec] = {}

            for prop_name, prop_meta in properties.items():
                raw_type = prop_meta.get("type", "string")
                fmt = prop_meta.get("format")
                type_key = f"{raw_type}:{fmt}" if fmt and f"{raw_type}:{fmt}" in JSON_TYPE_TO_PG else raw_type
                pg_type = JSON_TYPE_TO_PG.get(type_key, JSON_TYPE_TO_PG.get(raw_type, "VARCHAR(255)"))

                fields_dict[prop_name] = FieldSpec(
                    name=prop_name,
                    data_type=raw_type,
                    pg_type=pg_type,
                    required=(prop_name in required_list),
                    description=prop_meta.get("description", ""),
                    default=prop_meta.get("default")
                )
            parsed_entities[cls.__name__] = fields_dict

    return parsed_entities


def compare_and_generate(
    service_schemas: Dict[str, Dict[str, FieldSpec]],
    db_tables: Dict[str, Set[str]],
    output_dir: str
) -> None:
    """Realiza o diff completo e gera os arquivos de migração e adaptação."""
    auto_models = extract_automation_models()
    missing_in_db: Dict[str, List[FieldSpec]] = {}
    missing_in_automation: Dict[str, List[FieldSpec]] = {}

    print("\n" + "=" * 80)
    print("🔍 RELATÓRIO DE INTROSPECÇÃO E CONCILIAÇÃO DE SCHEMAS")
    print("=" * 80)

    # Entidades que afetam a automação
    schema_to_auto_entity = {
        "signercreateitem": "SignerData",
        "signer": "SignerData",
        "documentcreateitem": "AttachmentData",
        "document": "AttachmentData"
    }

    for schema_name, fields in service_schemas.items():
        clean_name = schema_name.lower().replace("_", "")
        matched_table = None

        for pattern, tbl in SCHEMA_TO_TABLE_MAPPING.items():
            if pattern in clean_name:
                matched_table = tbl
                break

        matched_auto = None
        for pattern, auto_cls in schema_to_auto_entity.items():
            if pattern in clean_name:
                matched_auto = auto_cls
                break

        print(f"\n📦 Entidade: [ {schema_name} ]")
        print(f"   Mapeamento Banco: [{matched_table or 'N/A'}] | Automação RPA: [{matched_auto or 'N/A'}]")
        print(f"   Total de atributos no schema: {len(fields)}")

        db_cols = db_tables.get(matched_table, set()) if matched_table else set()
        auto_cols = auto_models.get(matched_auto, set()) if matched_auto else set()

        for field_name, fspec in fields.items():
            snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', field_name).lower()

            # 1. Checagem Banco de Dados
            if matched_table:
                # Verifica correspondência direta ou via aliases
                direct_match = snake_name in db_cols or field_name.lower() in db_cols
                alias_match = any(matches_alias(snake_name, col) for col in db_cols)

                # Campos aninhados (como signers / documents) são relacionamentos 1:N
                is_nested_relation = fspec.data_type in ("array", "object") and snake_name in ("signers", "documents")

                if not direct_match and not alias_match and not is_nested_relation:
                    if matched_table not in missing_in_db:
                        missing_in_db[matched_table] = []
                    missing_in_db[matched_table].append(fspec)
                    print(f"   ⚠️  BANCO: Faltando coluna '{matched_table}.{snake_name}' ({fspec.pg_type})")
                elif alias_match and not direct_match:
                    print(f"   🔄 BANCO: '{snake_name}' resolvido via Alias/Sinônimo existente no banco")
                elif direct_match:
                    print(f"   ✅ BANCO: '{snake_name}' OK")

            # 2. Checagem Automação RPA
            if matched_auto:
                direct_auto = snake_name in auto_cols or field_name.lower() in auto_cols
                alias_auto = any(matches_alias(snake_name, col) for col in auto_cols)

                if not direct_auto and not alias_auto:
                    if matched_auto not in missing_in_automation:
                        missing_in_automation[matched_auto] = []
                    missing_in_automation[matched_auto].append(fspec)
                    print(f"   ⚠️  RPA: Modelo '{matched_auto}' não possui o campo '{snake_name}'")
                else:
                    print(f"   ✅ RPA: '{matched_auto}.{snake_name}' OK")

    # Geração do arquivo SQL de Migração
    migration_file = os.path.join(output_dir, "migration_patch.sql")
    with open(migration_file, "w", encoding="utf-8") as f:
        f.write("-- ====================================================================\n")
        f.write("-- MIGRATION_PATCH.SQL: Atualizações geradas automaticamente pelo Inspector\n")
        f.write("-- Adiciona com segurança colunas novas identificadas no schema do microsserviço/PAS\n")
        f.write("-- ====================================================================\n\n")

        if not missing_in_db:
            f.write("-- Nenhuma coluna crítica faltante no banco de dados! Schemas em conformidade.\n")
        else:
            for tbl, fspecs in missing_in_db.items():
                f.write(f"-- Atualizações para a tabela: {tbl}\n")
                for fspec in fspecs:
                    snake_name = re.sub(r'(?<!^)(?=[A-Z])', '_', fspec.name).lower()
                    f.write(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS {snake_name} {fspec.pg_type};\n")
                f.write("\n")

    # Geração do Adaptador Python para Automação
    adapter_file = os.path.join(output_dir, "adapter_patch.py")
    with open(adapter_file, "w", encoding="utf-8") as f:
        f.write('"""\n')
        f.write('adapter_patch.py: Camada de Adaptação Dinâmica de Schemas para a Automação RPA.\n')
        f.write('Mapeia campos defasados ou variáveis para o novo contrato exigido pelo Microsserviço/PAS.\n')
        f.write('"""\n\n')
        f.write('from typing import Dict, Any, List, Optional\n')
        f.write('from dataclasses import dataclass, field, asdict\n\n\n')
        
        f.write('class SchemaPayloadAdapter:\n')
        f.write('    """Normalizador de payloads para comunicação segura com o Microsserviço."""\n\n')
        f.write('    @staticmethod\n')
        f.write('    def adapt_signer_to_service(signer_data: Dict[str, Any]) -> Dict[str, Any]:\n')
        f.write('        """Converte signatário da automação para o contrato do microsserviço."""\n')
        f.write('        return {\n')
        f.write('            "tax_id": str(signer_data.get("tax_id") or signer_data.get("cpf") or "").strip(),\n')
        f.write('            "name": str(signer_data.get("name") or signer_data.get("nome") or "").strip(),\n')
        f.write('            "email": signer_data.get("email"),\n')
        f.write('            "phone": signer_data.get("phone") or signer_data.get("telefone"),\n')
        f.write('            "role": signer_data.get("role") or signer_data.get("papel") or "ASSINAR",\n')
        f.write('            "order": int(signer_data.get("order") or signer_data.get("ordem") or 1),\n')
        f.write('            "signature_type": signer_data.get("signature_type") or "ELETRONIC",\n')
        f.write('            "validation_channel": signer_data.get("validation_channel") or "WHATSAPP"\n')
        f.write('        }\n\n')

        f.write('    @staticmethod\n')
        f.write('    def adapt_document_to_service(doc_data: Dict[str, Any]) -> Dict[str, Any]:\n')
        f.write('        """Converte anexo da automação para o contrato do microsserviço."""\n')
        f.write('        return {\n')
        f.write('            "template_id": str(doc_data.get("doc_type_id") or doc_data.get("template_id") or "10410"),\n')
        f.write('            "name": doc_data.get("name") or doc_data.get("nome") or "documento.pdf",\n')
        f.write('            "document_hash": doc_data.get("hash_code") or doc_data.get("hash") or "",\n')
        f.write('            "mime_type": "application/pdf",\n')
        f.write('            "size_bytes": doc_data.get("file_size") or doc_data.get("tamanho") or 0\n')
        f.write('        }\n\n')

        if missing_in_automation:
            f.write('# Novos campos identificados para inclusão nos modelos da automação:\n')
            for auto_entity, fspecs in missing_in_automation.items():
                f.write(f'# Model {auto_entity}:\n')
                for fspec in fspecs:
                    f.write(f'#   {fspec.name}: Optional[{fspec.data_type}] = None\n')

    print("\n" + "=" * 80)
    print("🎯 SUCESSO! ARQUIVOS DE ADAPTAÇÃO GERADOS COM SUCESSO:")
    print(f"  1. SQL de Migração do Banco:  {os.path.relpath(migration_file, ROOT_DIR)}")
    print(f"  2. Adaptador Python RPA:      {os.path.relpath(adapter_file, ROOT_DIR)}")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Inspetor e Conciliador de Schemas Microsserviço/Banco/Automação")
    parser.add_argument("--url", type=str, help="URL do endpoint openapi.json (ex: http://127.0.0.1:8000/openapi.json)")
    parser.add_argument("--file", type=str, help="Caminho para arquivo JSON contendo a especificação OpenAPI ou Schemas")
    parser.add_argument("--from-pydantic", action="store_true", help="Inspeciona direto dos modelos Pydantic de microservico.api.schemas")
    parser.add_argument("--sql", type=str, default="PROD_schema.sql", help="Arquivo DDL do banco (padrão: PROD_schema.sql)")
    parser.add_argument("--out", type=str, default=".", help="Diretório de saída para os patches gerados")

    args = parser.parse_args()

    # 1. Carrega schema do banco de dados
    sql_path = os.path.join(ROOT_DIR, args.sql) if not os.path.isabs(args.sql) else args.sql
    if not os.path.exists(sql_path):
        sql_path = os.path.join(ROOT_DIR, "schema.sql")

    db_tables = parse_sql_columns_from_ddl(sql_path)
    print(f"📊 Banco de Dados carregado de: {os.path.basename(sql_path)} ({len(db_tables)} tabelas mapeadas)")

    service_schemas: Dict[str, Dict[str, FieldSpec]] = {}

    # 2. Carrega schema do serviço
    if args.url:
        import urllib.request
        print(f"🌐 Conectando à URL: {args.url} ...")
        try:
            req = urllib.request.Request(args.url, headers={"User-Agent": "SchemaInspector/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                service_schemas = extract_openapi_schemas(data)
        except Exception as e:
            print(f"❌ Erro ao acessar URL OpenAPI: {e}")
            sys.exit(1)

    elif args.file:
        file_path = os.path.join(ROOT_DIR, args.file) if not os.path.isabs(args.file) else args.file
        print(f"📁 Lendo arquivo de schema: {file_path} ...")
        if not os.path.exists(file_path):
            print(f"❌ Arquivo não encontrado: {file_path}")
            sys.exit(1)
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            service_schemas = extract_openapi_schemas(data)

    elif args.from_pydantic:
        print("🐍 Inspecionando modelos Pydantic do microsserviço...")
        service_schemas = extract_pydantic_schemas_from_code()

    else:
        # Se nenhum argumento foi passado, tenta primeiro Pydantic, e se não houver, tenta openapi local
        print("ℹ️  Nenhum parâmetro explícito fornecido. Executando auto-inspeção dos modelos Pydantic locais...")
        service_schemas = extract_pydantic_schemas_from_code()

    if not service_schemas:
        print("❌ Nenhum schema foi extraído. Use --url <URL>, --file <FILE> ou --from-pydantic.")
        sys.exit(1)

    out_dir = os.path.join(ROOT_DIR, args.out) if not os.path.isabs(args.out) else args.out
    compare_and_generate(service_schemas, db_tables, out_dir)


if __name__ == "__main__":
    main()
