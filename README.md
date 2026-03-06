# NoobTools Suite - Professional Pipeline for 3ds Max

O **NoobTools Suite** é um conjunto de ferramentas modulares desenvolvidas em Python e MaxScript para acelerar o fluxo de trabalho de artistas 3D no 3ds Max. Com foco em organização, automação de tarefas repetitivas e gestão eficiente de assets.

## 🚀 Funcionalidades Principais

### 📦 Asset Manager (Geo)
- **Navegação Inteligente:** Organização baseada em categorias e subpastas.
- **Busca por Tags:** Suporte a metadados via `metadata.json`.
- **Importação Rápida:** Arraste e solte ou duplo-clique para importar `.max`, `.fbx`, `.obj` e `.3ds`.
- **Auto-Layer & Prefix:** Organiza assets automaticamente em camadas e aplica prefixos na importação.

### 🎨 Material Manager (Mat)
- **Gestão de Bibliotecas:** Navegação completa de arquivos `.mat`.
- **Preview Dinâmico:** Suporte a miniaturas automáticas se houver um `.jpg` com o mesmo nome.
- **Modos de Aplicação:**
  - **Duplo Clique:** Aplica o material à seleção na cena instantaneamente.
  - **Context Menu:** Opções para enviar materiais específicos para o **Slate Editor** ou **Compact Editor** (forçando o modo correto).

### 🛠️ NoobFix (Scene Tools)
- **Relink Scanner Pro:** Sistema avançado de busca e correção de assets perdidos (Bitmaps, V-Ray, Corona, FStorm).
- **Collect Assets:** Ferramenta para coletar todos os assets da cena para uma pasta de projeto (Move to Project).
- **Scene Cleaner:** Remove camadas vazias, grupos vazios e limpa a cena com feedback detalhado.
- **Scale Checker:** Audita as Unidades do Sistema (System Units) e o fator de escala de objetos selecionados.
- **Asset Tracker Refresh:** Atalho rápido para atualizar caminhos de texturas.

### ⚙️ Settings & Performance
- **Persistência:** Salva caminhos de bibliotecas e preferências de backup automaticamente.
- **Hot Reload:** Sistema de recarga de módulos Python sem necessidade de reiniciar o 3ds Max.
- **Multi-Version:** Compatível com 3ds Max 2023 até 2026 (PySide2 e PySide6).

---

## 🛠️ Instalação
1. Baixe o arquivo `NoobToolsInstall.mzp`.
2. Arraste e solte o arquivo em qualquer viewport do 3ds Max.
3. Clique em "Install" e aguarde a mensagem de sucesso.
4. O botão aparecerá automaticamente na sua Toolbar.

---

## 📜 Changelog

### [v4.12] - 2026-03-06
- **New Feature:** **Relink Scanner** integrado ao NoobFix para busca massiva de assets perdidos.
- **New Feature:** **Collect Assets** (Copy to Project) para organizar bibliotecas externas.
- **Enhancement:** Detecção de renderizador (V-Ray, Corona, Arnold) no painel de info do Asset Manager.
- **Versão:** Sincronização global da versão para `v4.12`.

### [v4.11] - 2026-03-06
- **Fix:** Previews (bolinhas) agora compatíveis com Corona, VRay e FStorm (não ficam mais pretos).
- **UX:** Viewport agora atualiza instantaneamente ao aplicar materiais (redrawViews).
- **Logic:** Refinado o duplo clique para garantir que apenas aplique o material.

### [v4.9] - 2026-03-06
- **Refinement:** Duplo clique no Material Manager agora apenas aplica ao objeto (mais rápido).
- **Fix:** Forçado o modo do Material Editor (Slate vs Compact) ao usar o menu de contexto.
- **Stability:** Corrigido erro de lógica na abertura dos editores.

### [v4.8] - 2026-03-06
- **Overhaul:** Material Manager agora possui suporte a Categorias e Subpastas igual ao Asset Manager.
- **UI:** Adicionado painel de informações de material e botão "APPLY TO SELECTED".
- **Logic:** Correção na aplicação de materiais para multi-seleção simultânea.

### [v4.7] - 2026-03-06
- **Fix:** Removido erro crítico `import_history` que crashava o plugin na importação.
- **Enhancement:** Implementado Menu de Contexto (botão direito) no Material Manager.

### [v4.6] - 2026-03-05
- **New Feature:** Implementado o **Material Manager** em substituição ao antigo Histórico.
- **UX:** Scene Tools agora usam popups de aviso em vez de toasts para resultados importantes.
- **Cleanup:** Removido o *Compact Mode* para simplificar a interface.

### [v4.5] - 2026-03-05
- **Architecture:** Refatoração completa para sistema modular em pastas (`src/core`, `src/ui`, etc).
- **Hot Reload:** Implementado sistema de `importlib.reload` para desenvolvimento ágil.

---
*Developed by NoobViz Engineering*
