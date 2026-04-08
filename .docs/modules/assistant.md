# Assistant

## Entrega Esperada

O módulo `Assistant` oferece uma interface amigável para registro de transações utilizando linguagem natural. O usuário pode interagir por texto ou áudio, e um agente de IA interpreta a intenção, extrai os dados necessários e cria a transação após confirmação do usuário.
O objetivo é eliminar a barreira técnica — não é preciso ser um expert financeiro para registrar transações.

## Regras de Negócio

`O Assistant opera exclusivamente no contexto do usuário autenticado.`

### Interação por Texto

- O usuário pode digitar em linguagem natural para registrar transações.
    - Exemplo: "gastei 50 reais no mercado ontem"
- A LLM interpreta o texto e extrai os dados da transação (valor, categoria, data, tipo, etc.).
- Se informações obrigatórias estiverem faltando, a LLM **solicita os dados adicionais** ao usuário antes de prosseguir.
    - A LLM não assume ou inventa dados. Ela trabalha exclusivamente com o que o usuário informou.

### Interação por Áudio

- O usuário grava áudio diretamente no navegador.
- O áudio é enviado para transcrição via **OpenAI Whisper**.
- O texto transcrito é processado pela LLM seguindo o mesmo fluxo da interação por texto.

### Confirmação (Preview)

- Após interpretar os dados, a LLM retorna um **card/preview** com as informações extraídas da transação.
- O usuário pode:
    - **Confirmar**: a transação é criada no módulo Transactions.
    - **Alterar**: o usuário ajusta os dados antes de confirmar.
    - **Excluir**: o usuário cancela e a transação não é criada.
- Nenhuma transação é salva sem confirmação explícita do usuário.

### Processamento da LLM

- Serviço utilizado: **OpenAI GPT** para interpretação de linguagem natural.
- Serviço de transcrição: **OpenAI Whisper** para conversão de áudio em texto.
- A LLM deve mapear os dados extraídos para os campos do modelo Transaction:
    - name, amount, type (entrada/saída), category, date, description, card (se mencionado).
- Categorias e cartões são mapeados com base nos dados cadastrados pelo usuário. Se a LLM não encontrar correspondência exata, deve solicitar esclarecimento.

`Para auditoria, interações com o Assistant devem ser registradas para rastreabilidade.`

## Modelo de Dados

- AssistantInteraction (Herda de BaseModel):
    - user: ForeignKey → CustomUser
    - input_type: CharField (choices: texto, áudio)
    - input_content: TextField (texto digitado ou transcrição do áudio)
    - llm_response: JSONField (dados extraídos pela LLM)
    - status: CharField (choices: pendente, confirmado, cancelado)
    - transaction: ForeignKey → Transaction (null=True, blank=True)

## Fluxo de Registro por Texto

- Usuário digita uma mensagem em linguagem natural na interface do Assistant.
- Service envia o texto para a LLM (OpenAI GPT) com o contexto das categorias e cartões do usuário.
- LLM interpreta e extrai os dados da transação.
- Se dados obrigatórios estiverem faltando, a LLM responde solicitando as informações necessárias.
- Quando todos os dados estiverem completos, o Service retorna um preview/card para o usuário.
- Usuário confirma, altera ou cancela.
- Se confirmado, o Service cria a transação no módulo Transactions e vincula ao AssistantInteraction.
- Registra o AssistantInteraction com status correspondente.

## Fluxo de Registro por Áudio

- Usuário grava áudio pela interface do navegador.
- O áudio é enviado para o Service que encaminha para o **OpenAI Whisper** para transcrição.
- O texto transcrito é retornado e segue o mesmo fluxo do registro por texto (a partir do envio para a LLM).
- O AssistantInteraction registra o `input_type` como "áudio" e o `input_content` como a transcrição.
