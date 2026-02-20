# 🛠️ NoobTools Suite para 3ds Max

![Preview do NoobTools Suite](assets/preview.png)

O **NoobTools Suite** é um plugin avançado e super completo, desenvolvido em Python (PySide) e MaxScript para o Autodesk 3ds Max. A ideia principal dele é acelerar e facilitar a vida dos artistas 3D. Ele traz um gerenciador de bibliotecas de modelos super rápido, uma interface moderna e ferramentas inteligentes para diagnosticar a cena e dar relink em arquivos perdidos.

---

## ✨ Funcionalidades

A ferramenta é dividida em 4 abas, cada uma pensada para resolver uma parte chata do fluxo de trabalho:

### 1. 📦 Asset Manager (Gerenciador de Biblioteca)

- **Pastas e Favoritos:** Escolha a pasta raiz da sua biblioteca. Clique com o botão direito para favoritar caminhos e acessar suas pastas mais usadas com um clique.
- **Filtros e Pesquisa:** Navegue automaticamente por Categorias e Subcategorias. Filtre os arquivos pelo formato (`.MAX`, `.FBX`, `.SKP`, `.OBJ`) ou digite o que precisa na barra de busca.
- **Miniaturas Inteligentes (Thumbnails):** O plugin gera e salva as miniaturas dos seus blocos em segundo plano. Isso significa que o 3ds Max não trava enquanto você navega pelas pastas!
- **Leitor de Renderizador:** Sem precisar abrir o arquivo, o plugin lê as informações do `.max` e te avisa na aba "Asset Info" qual motor de render foi usado para criar aquele bloco (V-Ray, Corona, Arnold, FStorm, etc.).
- **Importação em Massa (Batch Import):** \* Selecione um ou vários blocos e importe tudo de uma vez. Acompanhe pelo carregamento fluido da barra de progresso.
  - Tem opções automáticas para jogar os blocos em **Layers (Auto Layer)** e colocar **Prefixos** no nome dos objetos.
- **Ferramentas de Hierarquia (Tools):** Agrupe, desagrupe, abra ou feche grupos direto pela interface, sem precisar ficar caçando as opções no Max.

### 2. 🔗 NoobFix (Diagnóstico e Relink)

- **Scan da Cena:** Lê a cena atual e mostra uma lista com todos os assets (texturas, proxies, etc.) que estão faltando.
- **Seleção Direta:** Dê um duplo clique em um arquivo da lista para selecionar automaticamente os objetos 3D que estão usando aquele material problemático.
- **Relink em Background:** Ele busca as texturas perdidas em uma pasta e nas subpastas usando uma _Thread_ separada. Você pode continuar trabalhando no Max enquanto ele relinka milhares de arquivos silenciosamente!
- **Ferramentas Extras:**
  - `STRIP`: Remove caminhos quebrados da cena de forma definitiva para manter o arquivo leve e limpo.
  - `UNC`: Converte caminhos locais (ex: `C:\texturas`) para caminhos de rede universais.
  - `COLETAR`: Copia todas as texturas usadas na cena direto para a pasta "Maps" do seu projeto atual.
- **Opções de Busca:** Dá para escolher ignorar as extensões (ótimo se você trocou um JPG por um PNG, por exemplo).

### 3. 🕒 History (Histórico)

- Uma tabela organizada que registra tudo o que você importou recentemente.
- Veja a **Data, Hora, Nome do Arquivo e Tipo** das suas últimas importações. Se errar e perder o bloco na cena, você sabe exatamente o que foi puxado.

### 4. ⚙️ Settings (Configurações)

- **Auto-Backup:** Uma trava de segurança muito útil. Ele salva uma cópia da sua cena (na pasta `_backup`) antes de você rodar ações destrutivas, como usar o _Strip_ ou importar muita coisa.
- **Limpeza de Cache:** Veja na hora quanto espaço em disco (MB) as miniaturas estão ocupando e limpe a cache com um clique para liberar espaço.

---

## 🎨 Interface Gráfica (UI/UX)

- **Design Moderno:** Interface escura e limpa (Dark Mode), pensada para quem passa o dia inteiro modelando ou renderizando.
- **Responsiva:** Barras de rolagem customizadas, botões fáceis de clicar (hitbox arrumada) e o mouse muda para a "mãozinha" para dar um feedback visual legal.

---

## 💻 Requisitos do Sistema

- **Autodesk 3ds Max:** Compatível com versões de 2020 até 2025+.
- **Motor:** Funciona usando o Python nativo do próprio 3ds Max (reconhece e suporta PySide2 e PySide6 automaticamente).

---

## 🚀 Como Instalar

O plugin já vem empacotado em um instalador (`.mzp`), então é bem fácil de colocar para rodar:

1. Baixe o arquivo de instalação `.mzp` aqui do repositório (na área de _Releases_).
2. Abra o seu **Autodesk 3ds Max**.
3. No menu lá em cima, vá em **`Scripting` > `Run Script...`** _(Em versões mais antigas, o menu se chama só `MAXScript`)_.
4. Escolha o arquivo `.mzp` que você baixou e clique em **Open**.
5. O instalador faz o resto! _(Aviso: não tente arrastar e soltar o `.mzp` direto na tela (viewport) porque não vai funcionar. Use sempre o menu Run Script)._
6. Depois disso, é só colocar a ferramenta em um atalho de teclado ou num botão da sua _Toolbar_ pelo menu `Customize User Interface`.

---

## 👨‍💻 Contribuições

Este projeto está sempre evoluindo. Sentiu falta de alguma funcionalidade, tem ideias para melhorar o código ou achou algum _bug_?
Fique à vontade para abrir uma _Issue_ ou mandar um _Pull Request_!

---

## 📄 Licença

Projeto de código aberto sob a licença MIT. Sinta-se livre para usar, estudar, modificar e compartilhar.
