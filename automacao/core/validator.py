"""
Módulo do Motor de Pré-Validação em Lote ('Tudo de uma Vez').
Valida todas as inconsistências cadastrais, documentos e canais de contato antes de iniciar chamadas de criação.
Nomes de classes, métodos e variáveis 100% em inglês com docstrings explicativas em português.
"""

import re
from typing import List, Optional
from automacao.domain.models import SignerData, AttachmentData
from automacao.domain.exceptions import BulkValidationError, CorruptedDocumentError


class TaskPayloadValidator:
    """
    Engine de Pré-Validação Antecipada e Exaustiva.

    Executa a verificação completa de todos os signatários e anexos da tarefa antes de qualquer
    comunicação externa, acumulando todas as falhas em exceções especializadas.
    """

    @staticmethod
    def _validate_tax_id(tax_id: str) -> bool:
        """
        Valida se o número de CPF informado possui formato e dígitos verificadores válidos.

        Parâmetros:
            tax_id (str): Número do documento (com ou sem pontuação).

        Retorno:
            bool: True se o CPF for matematicamente válido, False caso contrário.
        """
        clean_tax_id = re.sub(r"\D", "", tax_id or "")
        if len(clean_tax_id) != 11:
            return False
        # Sequências repetidas inválidas
        if clean_tax_id == clean_tax_id[0] * 11:
            return False
        # Cálculo dos dígitos verificadores (Módulo 11)
        for i in range(9, 11):
            sum_val = sum(int(clean_tax_id[num]) * ((i + 1) - num) for num in range(0, i))
            digit = ((sum_val * 10) % 11) % 10
            if int(clean_tax_id[i]) != digit:
                return False
        return True

    # Alias retrocompatível
    _validar_cpf = _validate_tax_id

    @staticmethod
    def _validate_email(email: str) -> bool:
        """
        Valida a estrutura sintática de um endereço de e-mail.

        Parâmetros:
            email (str): E-mail a ser validado.

        Retorno:
            bool: True se o e-mail for válido, False caso contrário.
        """
        if not email:
            return False
        pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        return bool(re.match(pattern, email.strip()))

    # Alias retrocompatível
    _validar_email = _validate_email

    @staticmethod
    def _validate_phone(phone: str) -> bool:
        """
        Valida se o telefone possui a quantidade de dígitos exigida para linhas brasileiras (com DDD).

        Parâmetros:
            phone (str): Número de telefone com DDD.

        Retorno:
            bool: True se possuir 10 ou 11 dígitos numéricos, False caso contrário.
        """
        clean_phone = re.sub(r"\D", "", phone or "")
        return len(clean_phone) in (10, 11)

    # Alias retrocompatível
    _validar_telefone = _validate_phone

    @staticmethod
    def _validate_attachment_integrity(att: AttachmentData) -> Optional[str]:
        """
        Valida a integridade física e os metadados do documento anexado.
        Detecta se o arquivo está corrompido, sem conteúdo (0 bytes), sem arquivo físico atribuído
        pela AWS/Fluid ou com cabeçalho PDF inválido.

        Parâmetros:
            att (AttachmentData): Instância do anexo a ser validado.

        Retorno:
            Optional[str]: Mensagem descritiva do erro se corrompido, ou None se íntegro.
        """
        doc_name = att.name or f"Anexo sem nome (Código: {att.doc_type_id or 'Não informado'})"

        # 1. Verificação de arquivo não atribuído pelo Fluid/AWS (hash nulo, vazio ou literal 'null')
        if not att.hash_code or att.hash_code.strip().lower() in ("", "null", "none", "undefined", "0"):
            return (
                f"Documento '{doc_name}': Nenhum arquivo físico foi atribuído ao anexo "
                f"(localizador/hash ausente por instabilidade na AWS ou falha de upload no Fluid)."
            )

        # 2. Verificação de flag explícita de corrupção ou erro na esteira
        if getattr(att, "is_corrupted", False):
            reason = getattr(att, "corruption_reason", None) or "Falha de integridade reportada pela esteira"
            return f"Documento '{doc_name}': Arquivo corrompido ou inacessível no armazenamento ({reason})."

        # 3. Verificação de tamanho (0 bytes)
        if att.file_size is not None and att.file_size <= 0:
            return f"Documento '{doc_name}': O arquivo possui 0 bytes (arquivo vazio gerado por falha no upload)."

        # 4. Verificação de integridade do conteúdo binário (se carregado em memória)
        if att.binary_content is not None:
            if len(att.binary_content) == 0:
                return f"Documento '{doc_name}': Conteúdo binário está vazio (0 bytes)."

            # Validação específica para PDFs
            if (att.extension or "pdf").lower() == "pdf":
                if not att.binary_content.startswith(b"%PDF"):
                    # Verifica se o arquivo é um XML de erro da AWS S3
                    if b"<Error>" in att.binary_content or b"<Code>" in att.binary_content:
                        return (
                            f"Documento '{doc_name}': O arquivo não é um PDF válido; "
                            f"contém mensagem de erro de armazenamento da AWS S3."
                        )
                    return f"Documento '{doc_name}': Cabeçalho de arquivo PDF inválido ou corrompido (não inicia com '%PDF')."

                if len(att.binary_content) < 32:
                    return f"Documento '{doc_name}': Arquivo PDF corrompido ou truncado (tamanho inferior a 32 bytes)."

        return None

    def validate_task_data(
        self,
        signers: List[SignerData],
        attachments: List[AttachmentData]
    ) -> None:
        """
        Executa a varredura e validação completa dos dados de signatários e anexos da tarefa.

        Parâmetros:
            signers (List[SignerData]): Lista de signatários extraídos do processo.
            attachments (List[AttachmentData]): Lista de arquivos PDFs anexados.

        Exceções:
            CorruptedDocumentError: Disparada se algum documento estiver quebrado, vazio ou sem arquivo atribuído.
            BulkValidationError: Disparada se pendências cadastrais forem encontradas.
        """
        errors: List[str] = []
        corrupted_doc_errors: List[str] = []

        # 1. Validação de Integridade Física dos Documentos Anexados
        for att in attachments:
            integrity_err = self._validate_attachment_integrity(att)
            if integrity_err:
                corrupted_doc_errors.append(integrity_err)

        attachments_names_map = {anexo.name.strip().lower(): anexo for anexo in attachments}
        attachments_hashes_set = {anexo.hash_code.strip() for anexo in attachments if anexo.hash_code}

        if not signers:
            errors.append("Nenhum signatário válido foi encontrado na tarefa do processo.")

        for idx, sig in enumerate(signers, start=1):
            signer_label = f"Signatário #{idx} ({sig.name or 'Nome não informado'})"

            # 1. Validação de CPF/CNPJ
            if not sig.tax_id:
                errors.append(f"{signer_label}: CPF não foi informado.")
            elif not self._validate_tax_id(sig.tax_id):
                errors.append(f"{signer_label}: CPF '{sig.tax_id}' é inválido.")

            # 2. Validação do Canal de Comunicação e Autenticação
            channel = (sig.validation_channel or "").upper()
            if channel == "EMAIL":
                if not sig.email:
                    errors.append(f"{signer_label}: Canal de validação é E-mail, mas o e-mail não foi informado.")
                elif not self._validate_email(sig.email):
                    errors.append(f"{signer_label}: E-mail '{sig.email}' possui formato inválido.")
            elif channel in ("WHATSAPP", "WHATSAPP ENTERPRISE", "SMS"):
                if not sig.phone:
                    errors.append(f"{signer_label}: Canal de validação é WhatsApp/SMS, mas o telefone não foi informado.")
                elif not self._validate_phone(sig.phone):
                    errors.append(f"{signer_label}: Telefone '{sig.phone}' possui formato inválido (exigido DDD + Número).")

            # 3. Validação de Documentos Vinculados ao Signatário
            if not sig.document_ids:
                errors.append(f"{signer_label}: Nenhum documento foi vinculado para assinatura desta pessoa.")
            else:
                for doc_ref in sig.document_ids:
                    doc_ref_lower = doc_ref.strip().lower()
                    found = any(
                        doc_ref_lower in att_name or att_name in doc_ref_lower
                        for att_name in attachments_names_map
                    )
                    if not found and doc_ref not in attachments_hashes_set:
                        errors.append(
                            f"{signer_label}: O documento '{doc_ref}' exigido para assinatura não consta na lista de anexos PDFs da solicitação."
                        )

        # Se houver documentos corrompidos ou sem arquivo atribuído, levanta CorruptedDocumentError com prioridade
        if corrupted_doc_errors:
            all_errors = corrupted_doc_errors + errors
            raise CorruptedDocumentError(
                message=(
                    f"Foram identificados {len(corrupted_doc_errors)} documento(s) corrompido(s) "
                    f"ou sem arquivo atribuído na esteira Fluid."
                ),
                errors=all_errors
            )

        if errors:
            raise BulkValidationError(
                message=f"Foram encontradas {len(errors)} pendências impeditivas na solicitação.",
                errors=errors
            )
