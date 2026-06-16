<p align="center">
  <img src="assets/writeonside_logo_light.svg" alt="Logótipo WriteOnSide" width="96" />
</p>

<h1 align="center">WriteOnSide</h1>

<p align="center">
  <strong>Uma aplicação leve de notas Markdown num painel lateral para Windows.</strong><br />
  Ficheiros simples no disco. Compatível com Obsidian. Sempre à beira do ecrã.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4?logo=windows" alt="Windows 10 e 11" />
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/version-0.0.50-2ea44f" alt="Versão 0.0.50" />
</p>

<p align="center">
  <strong>Idiomas:</strong>
  <a href="README.md">English</a> |
  <a href="README.zh-CN.md">中文</a> |
  <a href="README.pt.md">Português</a>
</p>

O WriteOnSide guarda notas Markdown numa pasta escolhida por si. Não há base de
dados privada nem serviço na nuvem obrigatório, pelo que o mesmo Vault pode ser
aberto no WriteOnSide, Obsidian, VS Code ou noutro editor.

> [!NOTE]
> O WriteOnSide `0.0.50` é um projeto em desenvolvimento ativo, ainda em
> pré-lançamento. Faça cópias de segurança das notas importantes e reveja as
> notas de versão antes de atualizar.

## Instalação

### Transferir uma build para Windows

Transfira o `WriteOnSide.exe` mais recente em
[GitHub Releases](https://github.com/Thymine2001/WriteOnSide/releases).

O WriteOnSide é atualmente distribuído como aplicação portátil para Windows,
num único ficheiro:

1. Transfira `WriteOnSide.exe`.
2. Coloque-o numa pasta onde pretenda manter a aplicação.
3. Execute e selecione uma pasta de notas ou um Vault Obsidian existente.
4. Use `Ctrl+Shift+Enter` para mostrar ou ocultar o painel.

O SmartScreen do Windows pode mostrar um aviso para builds de desenvolvimento
não assinadas. Confirme que o ficheiro provém deste repositório antes de o
executar.

## Destaques

### Painel lateral

- Painel sem moldura, altura total e sempre visível
- Layout configurável à esquerda ou à direita do ecrã
- Atalho global para mostrar/ocultar, predefinido `Ctrl+Shift+Enter`
- Largura do painel, largura do Explorador e opacidade ajustáveis
- Animações suaves ao abrir, fechar, reorganizar e redimensionar
- Ícone na bandeja do sistema e arranque opcional com o Windows
- Comportamento de instância única e posicionamento em áreas de trabalho
  multi-monitor

### Edição Markdown

- Código-fonte editável com realce de sintaxe em tempo real
- Modo de leitura renderizado com ligações e imagens
- Barra de ferramentas para títulos, ênfase, citações, listas, tarefas,
  tabelas, código, ligações, imagens, realce e cores de texto
- Front matter YAML com títulos, etiquetas, datas, aliases e outros metadados
- Localizar e substituir, números de linha, esquema e títulos fixos
- Blocos de código com etiqueta de linguagem e cópia num clique
- Fontes, tamanhos, temas e atalhos de comandos configuráveis

### Idioma da interface

A aplicação inclui **English**, **中文** e **Português**. Altere em
**Definições → Geral → Idioma**.

### Compatibilidade com Obsidian

| Funcionalidade | Suporte |
|---|---|
| Wiki links: `[[Note]]`, `[[Note\|alias]]`, `[[Note#Heading]]` | Sim |
| Referências de bloco: `[[Note#^block-id]]` | Sim |
| Incorporações: `![[file]]` | Sim |
| Callouts: `> [!note]` | Modo de leitura |
| Notas de rodapé, `%%comentários%%` e `#tags` inline | Sim |
| Listas de tarefas: `- [ ]` e `- [x]` | Sim |
| Renomear nota e atualizar wikilinks de entrada | Sim |

Escrever `[[` abre a conclusão de notas. `Ctrl+clique` segue um wikilink no modo
de edição. A ferramenta Backlinks lista notas que ligam à nota atual.

### Ficheiros e anexos

- Explorador de ficheiros com carregamento preguiçoso e pesquisa recursiva
- Filtragem por etiquetas YAML com seleção múltipla
- Criar, renomear, eliminar, arrastar e pré-visualizar ficheiros
- Editar Markdown e formatos de texto ou código comuns
- Colar ou arrastar imagens para as notas
- Pasta de anexos configurável com ligações relativas portáteis
- Gravações atómicas e cópias de segurança com carimbo temporal fora do Vault
- Visualizador de imagens com zoom e deslocamento

## Requisitos do sistema

**Para utilizadores finais:**

- Windows 10 ou Windows 11
- Sessão de ambiente de trabalho padrão; Windows on ARM ainda não foi testado
  formalmente

**Para desenvolvimento a partir do código-fonte:**

- Python 3.12
- Os pacotes listados em [`requirements.txt`](requirements.txt)

## Executar a partir do código-fonte

```powershell
git clone https://github.com/Thymine2001/WriteOnSide.git
cd WriteOnSide

py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\writeonside.py
```

Na primeira execução, selecione uma pasta de notas ou um Vault Obsidian existente.

## Utilização básica

- Use o botão hamburger para abrir ou fechar o Explorador de ficheiros.
- Alterne entre os modos Edição e Leitura na barra de ferramentas.
- Crie notas a partir da barra de ferramentas ou do Explorador.
- Cole uma imagem diretamente numa nota Markdown para a copiar para a pasta de
  anexos configurada.
- Selecione etiquetas YAML na secção inferior do Explorador para filtrar notas.
- Abra Definições para configurar a pasta de notas, layout, larguras, opacidade,
  tema, fonte, atalho global e atalhos da barra de ferramentas.
- Fechar o painel oculta a aplicação; use o atalho global ou o menu da bandeja
  para a mostrar novamente.

## Testes

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

A árvore de código-fonte atual contém 44 testes unitários que cobrem
configuração, renderização Markdown, atalhos, armazenamento, indexação de
notas, sintaxe Obsidian, renomeação de wikilinks e internacionalização.

## Criar um EXE para Windows

O script de lançamento requer PyInstaller e PyMuPDF além das dependências de
execução:

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller pymupdf
.\build_release.ps1
```

O script:

1. Incrementa a versão de patch em `VERSION`.
2. Exporta ficheiros PNG e ICO a partir dos logótipos SVG.
3. Cria um executável Windows num único ficheiro com PyInstaller.
4. Grava-o em `dist-native-tree-vX.Y.Z\WriteOnSide.exe`.
5. Mantém os três diretórios de lançamento mais recentes.

Consulte [`BUILDING.md`](BUILDING.md) para comandos adicionais e resolução de
problemas.

## Localização dos dados

| Dados | Localização |
|---|---|
| Notas e anexos | Pasta escolhida pelo utilizador ou Vault Obsidian |
| Definições | `%LOCALAPPDATA%\WriteOnSide\config.json` |
| Cópias de segurança geridas | `%LOCALAPPDATA%\WriteOnSide\Backups\` |

O WriteOnSide não requer conta nem serviço na nuvem integrado. As notas só saem
do computador quando o utilizador coloca o Vault num serviço de sincronização
configurado separadamente.

## Estrutura do projeto

```text
writeonside.py          Ponto de entrada da aplicação
writeonside_app/        Código-fonte da aplicação
assets/                 Recursos SVG, PNG e ICO
scripts/                Scripts auxiliares de build
tests/                  Testes unitários
licenses/               Textos de licenças de terceiros
WriteOnSide.spec        Configuração PyInstaller
build_release.ps1       Script de lançamento versionado para Windows
BUILDING.md             Instruções detalhadas de build
THIRD_PARTY_NOTICES.md  Atribuição de dependências e índice de licenças
LICENSE                 Licença MIT do código-fonte WriteOnSide
```

## Licenciamento

O código-fonte original do WriteOnSide está licenciado sob a
[Licença MIT](LICENSE).

Os componentes de terceiros continuam sujeitos às respetivas licenças listadas
em [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

<p align="center">
  <sub>Python | Tkinter | Markdown | Ficheiros simples compatíveis com Obsidian</sub>
</p>
