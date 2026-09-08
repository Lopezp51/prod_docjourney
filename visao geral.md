Exemplo de dado que vamos receber:

{
  "_id": {
    "$oid": "6a294e101b86f230b17588d1"
  },
  "num_processo": 1160705,
  "nome_processo": "Renovação Seguros V2",
  "status": "Repassado",
  "prioridade": 10,
  "etapa": 200,
  "desc_etapa": "",
  "data_cadastro": {
    "$date": "2026-06-10T08:22:00.000Z"
  },
  "data_realizacao": {
    "$date": "2026-06-10T08:23:59.000Z"
  },
  "robo": "",
  "execucoes": 1,
  "detalhes": "Erro desconhecido: erro=ErroNãoMapeadoAPICAS('detailRetorno diferente dos status_code mapeados à API de adesão eletrônica PASFalha desconhecida na API 01 do PAS. Realizar verificação dos logs.')",
  "fluid_infos": {
    "processo_id": 963,
    "arvore": 1711,
    "nodo": 53152,
    "email_resp": "rpa_0703_reptofluid@sicredi.com.br",
    "emp_origem": "Sede"
  },
  "infos_envio": {
    "atributos": {
      "2581": "111111",
      "3505": "11/06/2026",
      "4068": "1111111",
      "4256": "25 - ESTRELA D' OESTE",
      "4290": "LEGADO",
      "5302": "1111111",
      "6656": "ANTONIO RODRIGUES DOS SANTOS FILHO",
      "6657": "121",
      "6659": "TOKIO MARINE",
      "6688": "1111111",
      "6689": "63 - TOKIO MARINE",
      "6690": "AUTOMOVEL - HB20X HATCH PREMIUM 1.6 FLEX 16V AUT",
      "6691": "11111",
      "6692": "Renovado",
      "6779": "jenm.br",
      "6791": "Jenifer Alva",
      "6824": "2935.57",
      "6834": "12.0",
      "6835": "2.649,54",
      "6836": "12%",
      "9740": "88361-2",
      "10449": "AUTOMOVEL",
      "10769": "jen.br",
      "10790": "Adesão Eletrônica (Robô envia no PAS)",
      "10972": "[\"Whats Corporativo\",\"Whats Enterprise\"]",
      "11053": "Débito em conta",
      "11054": "20/06/2026",
      "11055": "NÃO ACOMPANHAR ASS",
      "11058": "ADESÃO PAS",
      "11102": "SEGUROS",
      "11141": "daniem.br",
      "11278": "jenifom.br",
      "11625": "AG25",
      "12216": "Não",
      "12219": "02/06/2026",
      "12220": "DALOD",
      "12222": "Não"
    },
    "anexos": [
      {
        "nome": "proposS FILHO",
        "hash": "bbqgqxmte5mdgwnzawma",
        "tipo_doc_id": 550,
        "data_anexo": "10/06/2026 08:19:10",
        "extensao": "pdf"
      },
      {
        "nome": "31ce_0",
        "hash": "ovynpumdgwnzawma",
        "tipo_doc_id": 1283,
        "data_anexo": "25/05/2026 10:28:22",
        "extensao": "pdf"
      }
    ]
  },
  "infos_retorno": {
    "fluid_api": {
      "tipo_processo": 0,
      "tempo_processo": 0,
      "versao_arvore": 0,
      "empresa_origem": [
        "1"
      ],
      "empresa_destino": [
        "1"
      ],
      "resp_destino": {
        "1": 0
      },
      "acao_nodo": "acao_1",
      "nodo_atual": 0,
      "parecer": ""
    },
    "infos_campos": {},
    "anexos": {}
  },
  "id_inicial": "6a2948e51b86f230b1754478"
}



Com isso precisamos receber, criar o registro da pessoa no banco de dados se ela não tiver.
Prosseguindo vamos criar o documento ou na certisign ou no PAS, cada uma vai usar uma lógica diferente. Os dados que vamos ter na tarefa serão diferentes, estamos montando ainda, mas vai ser na estruturada json de numero de campo e o valor.


esse é um exemplo de certisign:

{
  "_id": {
    "$oid": "6a2b02da1b86f230b176a3f2"
  },
  "num_processo": 1170216,
  "nome_processo": "Solicitação de Crédito Comercial V2",
  "status": "Fluid - Preencher Campos",
  "prioridade": 10,
  "etapa": 200,
  "desc_etapa": "Finalizar",
  "data_cadastro": {
    "$date": "2026-06-11T15:43:00.000Z"
  },
  "data_realizacao": {
    "$date": "2026-06-11T15:45:33.000Z"
  },
  "robo": "Cooper",
  "execucoes": 1,
  "detalhes": "Protocolado",
  "fluid_infos": {
    "processo_id": 891,
    "arvore": 1704,
    "nodo": 52798,
    "email_resp": "camila_driele@sicredi.com.br",
    "emp_origem": "AG25"
  },
  "infos_envio": {
    "atributos": {
      "1367": "933037",
      "1474": "C62520460-0",
      
      "10273": "-1",
      "10274": "-1",
      "10410": [
        [
          {
            "id": 10417,
            "valor": "1"
          },
          {
            "id": 10819,
            "valor": "Não"
          },
          {
            "id": 10411,
            "valor": "11111111111"
          },
          {
            "id": 10412,
            "valor": "EDILSON RO"
          },
          {
            "id": 11248,
            "valor": "[\"Representante da Empresa\",\"Sócio/Avalista\",\"Cônjuge Avalista\"]"
          },
          {
            "id": 11249,
            "valor": "[\"765\\\\t- CCB\",\"613\\\\t- Seguro Prestamista\",\"678\\\\t- CET\"]"
          },
          {
            "id": 10414,
            "valor": "WhatsApp Enterprise"
          },
          {
            "id": 10416,
            "valor": "99999999996"
          },
          {
            "id": 10418,
            "valor": "Eletrônica"
          }
        ],
        [
          {
            "id": 10417,
            "valor": "1"
          },
          {
            "id": 10819,
            "valor": "Não"
          },
          {
            "id": 10411,
            "valor": "11111111111"
          },
          {
            "id": 10412,
            "valor": "AILA ELO"
          },
          {
            "id": 11248,
            "valor": "[\"Representante da Empresa\",\"Sócio/Avalista\",\"Cônjuge Avalista\"]"
          },
          {
            "id": 11249,
            "valor": "[\"765\\\\t- CCB\",\"678\\\\t- CET\"]"
          },
          {
            "id": 10414,
            "valor": "WhatsApp Enterprise"
          },
          {
            "id": 10416,
            "valor": "(99) 9999999999"
          },
          {
            "id": 10418,
            "valor": "Eletrônica"
          }
        ]
      ],
      "10617": "ME",
      "11364": "[\"765 - CCB\",\"613 - Seguro Prestamista\",\"678 - CET\"]",
      
      "12569": "VINCULADO"
    },
    "anexos": [
      {
        "nome": "COMPROMETIEMENTO AVAL",
        "hash": "wdpsgdxzawma",
        "tipo_doc_id": 98,
        "data_anexo": "11/06/2026 15:41:00",
        "extensao": "pdf"
      },
      {
        "nome": "reportcadon - cadastro",
        "hash": "hsevz8sexodqxmdgwnzawma",
        "tipo_doc_id": 98,
        "data_anexo": "11/06/2026 15:41:01",
        "extensao": "pdf"
      },
      {
        "nome": "PRESTAMISTA_C62520460-0_VITAL ESPORTE LTDA",
        "hash": "xnmkvkqxmdgwnzawma",
        "tipo_doc_id": 613,
        "data_anexo": "11/06/2026 15:41:01",
        "extensao": "pdf"
      },
      {
        "nome": "CEITAL ESPORTE LTDA",
        "hash": "ae09zdqwdmdgwnzawma",
        "tipo_doc_id": 678,
        "data_anexo": "11/06/2026 15:41:00",
        "extensao": "pdf"
      },
      {
        "nome": "CONT60-0_VITAL ESPORTE LTDA",
        "hash": "nkpgxcqxmdgwnzawma",
        "tipo_doc_id": 765,
        "data_anexo": "11/06/2026 15:41:01",
        "extensao": "pdf"
      },
      {
        "nome": "ata de aprovação",
        "hash": "d67d9erwqaxmji1mdgwnzawma",
        "tipo_doc_id": 297,
        "data_anexo": "10/06/2026 09:25:12",
        "extensao": "pdf"
      },
      {
        "nome": "SIMULACRED_DO703_DATA0906202616h06m",
        "hash": "him981p8qydxote4mdgwnzawma",
        "tipo_doc_id": 753,
        "data_anexo": "09/06/2026 16:18:48",
        "extensao": "pdf"
      }
    ]
  },
  "infos_retorno": {
    "fluid_api": {
      "tipo_processo": 891,
      "tempo_processo": 0,
      "versao_arvore": 1704,
      "empresa_origem": [
        "1"
      ],
      "empresa_destino": [
        "1"
      ],
      "resp_destino": {
        "1": 0
      },
      "acao_nodo": "acao_1",
      "nodo_atual": 52798
    },
    "infos_campos": {
      "1": [
        "11253": "\\nNome Assinante: EDILSONLO\\nID Assinante: 345345345\\nLink Assinatura: Link enviado no WhatsApp: 11111111111<br>ID Botmaker: dfgdfgdfgdgdfgdfg\\n<br>\\n\\nNome Assinante: AILA ELO\\nID Assinante: 456456456456\\nLink Assinatura: Link enviado no WhatsApp: 354345345345345<br>ID Botmaker: fgfghfghfghfghfgh\\n<br>\\n",
      ]
    },
    "anexos": {}
  },
  "id_inicial": "6a2b01e91b86f230b176a329"
}

vamos usar o 10410 só.

# significado dos campos

10417: ordem de assinatura pode ir de 1 a 10, na certisign pode haver ordem de assinatura, assim só pode continuar se a ordem ser seguida.
10411: cpf da pessoa
10412: nome da pessoa
8665: é um campo seleção tendo as opções "Procurador Segurado", " Segurado", "Conjuge Segurado", "Titular da conta para débito", "Representate 1", "Representate 2", "Representate 3", "Representate 4", "Representate 5", "Conjuge representante 1", "Conjuge representante 2", "Conjuge representante 3", "Conjuge representante 5", "Procurador representante 1 a 5", "Procurador Conjuge representante 1 a 5"
10751: vai vir uma lista de documento que vai ter o ID, para a gente saber qual documento vamos usar que vai vir do json do processo.
10418: botão seleção tendo duas opções "Eletronica" e "Certificado Digital"
10414: botão de escolha "E-mail", "Whatsapp Enterprise", "Presencial - Foto", se for presecial não vai vir pra automação então ta de boa
10415: email da pessoa
11101: n usamos
10416: telefone da pessoa