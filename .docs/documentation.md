# Auri

## Objetivo Principal

O **Auri** é um sistema de controle financeiro, atualmente desenvolvido para solucionar o problema de controle monetário pessoal. O mercado está cheio de sistemas financeiros, porém nada melhor do que ter um modular, feito sob medida para sí mesmo e com funcionalidades desenvolvidas para atender meu controle. 

Contendo um módulo integrado com Inteligência Artificial para registro de transações com captura de áudio e com linguagem neutra, então não é preciso um expert para poder utilizar.

## Visão Geral de Funcionalidades

O sistema é modular, garantindo isolamento de domínios. Os principais módulos são:

- Autenticação:
  - Cada usuário possúi o seu ambiente de utilização, assim nenhum usuário vê informações de outro usuário. 
  - A criação da conta ocorre através do registro dentro da plataforma. O usuário determina seu nome de usuário e seu e-mail. Ao completar o registro, um e-mail é disparado e ele recebe uma senha de primeiro acesso. Ao realizar o primeiro acesso, a plataforma obriga ele a cadastrar uma nova senha.
  - OAuth será implementado para usuários que desejam utilizar autenticação com a conta do Google.

- Transações:
  - A principal função do sistema. As transações podem ser saídas ou entradas.
  - Transações podem ser recorrentes, permitindo que o usuário não precise registrar a mesma transação todo mês.
  - Parcelamento é opcional, permitindo registros automáticos de acordo com as informações requisitadas.
  - Categorização, nomenclatura e descrição das transações podem ser atribuídas, garantindo um controle total e apurado das transações.

- Cards:
  - Controle de gastos em cartões dentro da plataforma. Esse módulo permite que o usuário 'cadastre' cartões

- Categories:
  - Controle e categorização das transações. Focado em criar 'tags' para atribuir em transações, para realização de filtros e extração de relatórios.
  - Categorias podem ser criadas e configuradas por usuários, nada será hardcoded, tudo modularizado e configurável.

- Reports:
  - Dedicado para extração de relatórios, a ideia é permitir que o usuário possa baixar seus dados da plataforma.
  - Extensões como CSV, Excel e PDF são permitidas e garante que o usuário tenha a experiência de ter seus dados a qualquer momento.

- Assistant: 
  - Interface amigável para registro de transações utilizando linguagem neutra.
  - Captura de áudio com transcrição utilizando um agente de IA que realiza a transação através do registro.

## Padrões Técnicos Globais

- Stack Base e Arquitetura
  - Backend: Python com Django. Padrão arquitetural Monolítico.
  - Separação de Domínios: O projeto será dividido em django-apps focados em domínios específicos (ex: accounts, transactions, assistant). Evitar acoplamento profundo entre apps; comunicação entre domínios deve ocorrer preferencialmente via camada de Services ou Django Signals.
  - API: o projeto já contemplará a criação das APIs, com FastAPI para integração mobile e com framework frontend futuramente. Documentação completa de todos os endpoints.

- Banco de Dados e Modelagem
  - Bancos Utilizados: PostgreSQL, conteinerizado via Docker para desenvolvimento e AWS RDS em produção.
  - Padrão de Tabelas (Base Model): Todos os modelos principais devem herdar de um BaseModel contendo campos de auditoria de tempo: created_at (Data de criação) e updated_at (Última modificação).
  - Deleção Segura: Soft-delete (desativação via campo booleano is_active=False) deve ser o padrão para registros sensíveis. Hard-delete (remoção real do banco) apenas para tabelas de log ou tabelas pivô simples.  

- Frontend e Interação (UI)
  - Renderização: Server-Side Rendering (SSR) exclusivo utilizando Django Templates.
  - Frontend com framework (Next.js) será implementado na segunda semana após o lançamento do MVP.
  - Mobile será implementado no segundo mês após o Next.js ser implementado.

- Metodologia de Testes (TDD)
  - Framework: pytest com pytest-django.
  - Abordagem TDD: Os testes devem ser escritos antes da implementação lógica (orientados pelas Specs do SDD-Writer).
  - Cobertura Esperada: Testes devem focar em Regras de Negócio (Camada de Services/Managers) e Contratos de View (Garantir que a view retorna o template correto com o contexto certo).