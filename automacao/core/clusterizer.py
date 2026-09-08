"""
Módulo de Clusterização e Agrupamento por Escopo Documental.
Agrupa signatários pela interseção exata dos documentos que lhes cabe assinar.
Gera identificador determinístico via SHA256 para cada combinação única.
Nomes de classes, métodos e variáveis 100% em inglês com docstrings explicativas em português.
"""

import hashlib
from typing import List, Dict
from automacao.domain.models import SignerData, AttachmentData, EnvelopeCluster
from automacao.domain.exceptions import EnvelopeClusterError


class DocumentScopeClusterizer:
    """
    Motor de Clusterização por Escopo Documental.

    Garante a premissa de integridade documental exigida pela API de assinaturas:
    todos os signatários associados a um envelope assinam rigorosamente o mesmo conjunto de documentos.
    A quantidade de envelopes gerados é diretamente proporcional à cardinalidade de combinações
    únicas de [Signatários x Documentos].
    """

    @staticmethod
    def generate_scope_hash(document_ids: List[str]) -> str:
        """
        Gera um hash SHA256 determinístico e ordenado a partir da lista de documentos informada.

        Parâmetros:
            document_ids (List[str]): Lista de nomes ou identificadores dos documentos.

        Retorno:
            str: Hash hexadecimal SHA256 representativo do escopo.
        """
        sorted_docs = sorted([str(d).strip().lower() for d in document_ids if d])
        content_str = "|".join(sorted_docs)
        return hashlib.sha256(content_str.encode("utf-8")).hexdigest()

    # Alias retrocompatível
    gerar_hash_escopo = generate_scope_hash

    def clusterize(
        self,
        signers: List[SignerData],
        attachments: List[AttachmentData]
    ) -> List[EnvelopeCluster]:
        """
        Agrupa os signatários pelo escopo documental único e associa os anexos físicos correspondentes.

        Parâmetros:
            signers (List[SignerData]): Lista de signatários da tarefa.
            attachments (List[AttachmentData]): Lista de anexos disponíveis na solicitação.

        Retorno:
            List[EnvelopeCluster]: Lista de clusters estruturados com hash, documentos, signatários e anexos.

        Exceções:
            EnvelopeClusterError: Lançado se a lista de signatários estiver vazia.
        """
        if not signers:
            raise EnvelopeClusterError("Não é possível clusterizar um grupo vazio de signatários.")

        clusters_map: Dict[str, List[SignerData]] = {}
        docs_by_hash: Dict[str, List[str]] = {}

        for sig in signers:
            scope_hash = self.generate_scope_hash(sig.document_ids)
            if scope_hash not in clusters_map:
                clusters_map[scope_hash] = []
                docs_by_hash[scope_hash] = sorted([str(d).strip() for d in sig.document_ids if d])
            clusters_map[scope_hash].append(sig)

        attachments_map = {att.name.strip().lower(): att for att in attachments}
        result_clusters: List[EnvelopeCluster] = []

        for scope_hash, group_signers in clusters_map.items():
            doc_ids = docs_by_hash[scope_hash]
            group_attachments: List[AttachmentData] = []

            for doc_id in doc_ids:
                doc_id_lower = doc_id.lower()
                for att_name, att_obj in attachments_map.items():
                    if doc_id_lower in att_name or att_name in doc_id_lower or doc_id == att_obj.hash_code:
                        if att_obj not in group_attachments:
                            group_attachments.append(att_obj)

            result_clusters.append(
                EnvelopeCluster(
                    scope_hash=scope_hash,
                    document_ids=doc_ids,
                    signers=group_signers,
                    attachments=group_attachments
                )
            )

        return result_clusters
