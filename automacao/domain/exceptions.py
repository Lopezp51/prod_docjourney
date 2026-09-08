"""
Módulo de Exceções de Domínio do Fluxo da Automação RPA.
Padroniza o tratamento de erros negociais, pré-validação eager e falhas de integração.
Garante a formatação automática de pareceres HTML padronizados para devolução à esteira Fluid.
Nomes de classes e métodos em inglês com docstrings explicativas em português.
"""

from abc import ABC, abstractmethod
from typing import List, Optional


class BaseFlowException(Exception, ABC):
    """
    Classe base abstrata para todas as exceções mapeadas no fluxo da automação RPA.

    Centraliza a captura de erros, o código de rastreio e a geração do parecer
    formatado em HTML para comunicação com a esteira Fluid / MongoDB.

    Atributos:
        message (str): Descrição concisa do erro ocorrido.
        errors (List[str]): Lista consolidada de todas as pendências ou falhas identificadas.
    """

    def __init__(self, message: str, errors: Optional[List[str]] = None):
        """
        Inicializa a exceção de fluxo.

        Parâmetros:
            message (str): Mensagem principal de erro.
            errors (Optional[List[str]]): Lista detalhada de pendências. Se None, inicializa com [message].
        """
        super().__init__(message)
        self.message = message
        self.errors = errors if errors is not None else [message]

    @property
    @abstractmethod
    def flow_error_code(self) -> str:
        """
        Código identificador unívoco do tipo de erro no fluxo da esteira.

        Retorno:
            str: Código de erro alfanumérico (ex.: 'VAL_BULK_ERROR', 'API_UPLOAD_ERROR').
        """
        pass

    def to_fluid_parecer(self) -> str:
        """
        Gera o texto de parecer em formato HTML formatado para devolução e ajuste na tarefa Fluid.

        Retorno:
            str: String HTML com as pendências em lista e instruções para o operador da esteira.
        """
        error_items_html = "".join([f"<li><p style='color: red;'>{err}</p></li>" for err in self.errors])
        return (
            f"Olá Colega! <br>"
            f"<strong>Não</strong> foi possível realizar o envio dos documentos para assinatura.<br>"
            f"Foi identificado o seguinte conjunto de pendências: <br>"
            f"<ul>{error_items_html}</ul><br>"
            f"<strong>Realize o ajuste de TODAS as informações descritas acima e retorne a tarefa para o robô tentar novamente!</strong><br><br>"
            f"Atenciosamente, Robô Orquestrador!"
        )


class BulkValidationError(BaseFlowException):
    """
    Lançada quando a validação antecipada ('tudo de uma vez') detecta uma ou mais incoerências cadastrais.
    Acumula todas as falhas impeditivas (CPF inválido, canal sem dados, documento ausente)
    em um único ciclo, evitando devoluções parciais ('fail-fast').
    """

    @property
    def flow_error_code(self) -> str:
        """
        Retorna o código de identificação de erro de pré-validação em lote.

        Retorno:
            str: 'VAL_BULK_ERROR'.
        """
        return "VAL_BULK_ERROR"


class DocumentUploadError(BaseFlowException):
    """
    Lançada em caso de falha de validação ou upload de arquivos multipart na rota POST /files/envelope/:id/files.
    """

    @property
    def flow_error_code(self) -> str:
        """
        Retorna o código identificador de erro de upload de documentos.

        Retorno:
            str: 'API_UPLOAD_ERROR'.
        """
        return "API_UPLOAD_ERROR"


class OpenApiIntegrationError(BaseFlowException):
    """
    Lançada em caso de falhas de comunicação HTTP, timeout ou rejeição de carga na OpenAPI v2.
    """

    @property
    def flow_error_code(self) -> str:
        """
        Retorna o código identificador de erro na OpenAPI externa.

        Retorno:
            str: 'API_INTEGRATION_ERROR'.
        """
        return "API_INTEGRATION_ERROR"


class EnvelopeClusterError(BaseFlowException):
    """
    Lançada quando ocorre inconsistência matemática ou de dados ao agrupar signatários por escopo documental.
    """

    @property
    def flow_error_code(self) -> str:
        """
        Retorna o código identificador de erro de clusterização documental.

        Retorno:
            str: 'CLUSTER_ERROR'.
        """
        return "CLUSTER_ERROR"


class CorruptedDocumentError(BaseFlowException):
    """
    Lançada quando um ou mais documentos anexados na esteira do Fluid estão corrompidos, vazios (0 bytes),
    ilegíveis ou sem arquivo físico atribuído no armazenamento AWS/Fluid.

    Gera parecer específico instruindo o operador a excluir o documento danificado e anexá-lo novamente.
    """

    @property
    def flow_error_code(self) -> str:
        """
        Retorna o código de identificação de erro de documento corrompido.

        Retorno:
            str: 'CORRUPTED_DOCUMENT_ERROR'.
        """
        return "CORRUPTED_DOCUMENT_ERROR"

    def to_fluid_parecer(self) -> str:
        """
        Gera o texto de parecer formatado em HTML com orientação explícita para o analista excluir e reenviar.

        Retorno:
            str: String HTML com detalhes do documento quebrado e instruções operacionais.
        """
        doc_items_html = "".join([f"<li><p style='color: red;'><strong>{err}</strong></p></li>" for err in self.errors])
        return (
            f"Olá Colega! <br>"
            f"<strong>Não</strong> foi possível realizar o envio dos documentos para assinatura.<br>"
            f"Identificamos que o(s) seguinte(s) documento(s) está(ão) <strong>corrompido(s), vazio(s) ou com falha de carregamento no Fluid/AWS</strong>:<br>"
            f"<ul>{doc_items_html}</ul><br>"
            f"<strong>Orientações para correção:</strong><br>"
            f"1. Acesse este processo no Fluid e vá até a aba de <strong>Anexos</strong>.<br>"
            f"2. Localize e <strong>EXCLUA o(s) documento(s) corrompido(s)</strong> listado(s) acima.<br>"
            f"3. <strong>Anexe novamente</strong> o arquivo PDF correspondente em questão e verifique se o carregamento foi concluído.<br>"
            f"4. Avance ou retorne a tarefa para a fila do robô tentar novamente o processamento.<br><br>"
            f"Atenciosamente, Robô Orquestrador DocJourney!"
        )

