# Categories

## Entrega Esperada

O módulo `Categories` é responsável pela criação e gerenciamento de categorias para classificação de transações. Funciona como um sistema de "tags" configuráveis pelo usuário, permitindo organização, filtragem e extração de relatórios baseados em categorias.
Nada é hardcoded — toda categorização é modularizada e totalmente configurável pelo usuário.

## Regras de Negócio

`Cada categoria pertence exclusivamente ao usuário autenticado.`

- O usuário pode criar quantas categorias desejar.

- Campos obrigatórios: nome da categoria.
    - Campos opcionais: descrição, cor, ícone.

- O nome da categoria deve ser **único por usuário**. Dois usuários diferentes podem ter categorias com o mesmo nome, mas o mesmo usuário não.

- Categorias podem receber uma **cor** e/ou **ícone** para personalização visual na interface.

- Não existem categorias padrão. O sistema começa vazio e o usuário cria suas próprias categorias conforme sua necessidade.

- Categorias são utilizadas como filtro em **Transactions** e **Reports**.

- Soft-delete é o padrão. Ao desativar uma categoria, as transações vinculadas mantêm a referência no histórico.
    - Uma categoria desativada não aparece nas opções de seleção para novas transações.

`Para auditoria, toda categoria deve herdar o BaseModel contido em core/models.py`

## Modelo de Dados

- Category (Herda de BaseModel):
    - user: ForeignKey → CustomUser
    - name: CharField
    - description: TextField (null=True, blank=True)
    - color: CharField (null=True, blank=True)
    - icon: CharField (null=True, blank=True)

## Fluxo de Criação de Categoria

- Usuário preenche o formulário com nome e campos opcionais.
- Serializer valida unicidade do nome para o usuário autenticado.
- Service cria a categoria vinculada ao usuário.
- Retorna resposta de sucesso com os dados da categoria criada.

## Fluxo de Exclusão (Soft-Delete)

- Usuário solicita exclusão de uma categoria.
- Service marca a categoria como `is_active=False`.
- Transações vinculadas à categoria permanecem inalteradas no histórico.
- A categoria deixa de aparecer nas listagens e seletores da interface.
