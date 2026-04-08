# Accounts

## Entrega Esperada

O módulo `Accounts` é responsável pela criação de usuários e fluxo principal de gerenciamento de contas. A autenticação também é de responsábilidade do módulo.
A garantia é que cada usuário tenha seu prórpio ambiente de utilização, NENHUM usuário deve e pode interagir com informações de outros usuários dentro da plataforma.

## Regras de Negócio

`Cada usuário possui seu próprio ambiente de utilização dentro da plataforma.`

- A criação de contas ocorre na página de registro dentro da plataforma.
    - Para um registro de sucesso, o usuário deve definir seu `nickname`(nome de usuário) e `e-mail`.
    - Após o registro, um e-mail automático será encaminhado para o usuário, contendo uma senha aleatória. Essa senha deve ser utilizada para realizar a autenticação dentro da plataforma.
    - Na primeira autenticação, a plataforma obriga o usuário a cadastrar uma nova senha.

- A plataforma permite autenticação OAuth através de uma conta Google.

- E-mail deve ser único no sistema. Caso já exista informar o usuário na UI.

- A senha temporária NUNCA é retornada na resposta da API. Ela é enviada exclusivamente por e-mail.

- O e-mail de primeiro acesso deve conter:
    - Senha temporária;
    - Instruções de login;
    - Aviso de troca obrigatória.

`Para auditoria, todo usuário deve herdar o BaseModel contido em core/models.py`

## Modelo de Dados
- BaseModel:
    - id: UUID como PrimaryKey.
    - created_at: DateTimeField (auto_now_add=True)
    - updated_at: DateTimeField (auto_now=True)
    - is_active: BooleanField (default=true)

- CustomUser (Herda de BaseModel):
    - email: EmailField
    - nickname: CharField
    - is_first_access: BooleanField (default=True)
    - phone_number: VarChar (null=true, blank=true)

## Fluxo de Registro

- Usuário submete nickname e e-mail via formulário de registro
- Serializer valida unicidade do e-mail e nickname, formato do e-mail e regras do nickname
- Service gera senha temporária.
- Service cria o usuário com `is_first_access=True`
- Service dispara o e-mail com a senha temporária
- Retorna resposta de sucesso com mensagem orientando o usuário a verificar seu e-mail.