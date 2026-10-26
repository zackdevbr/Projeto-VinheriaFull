# Deploy rápido — front na Vercel, backend no notebook via túnel

## 1. Contexto

Todas as tasks do produto estão prontas e a entrega é em 26/10/2026. O usuário quer o painel publicado na Vercel ainda hoje, do jeito mais rápido possível, e decidiu manter o backend FastAPI rodando no próprio notebook, como já acontece no desenvolvimento. A solução definitiva (backend contínuo na EC2 do FIWARE, com chave de API) fica para depois e não faz parte deste plano.

O que já está pronto e é reaproveitado sem mudança de código:

- O front chama sempre caminhos relativos (`/api/...`, em `frontend/src/api/client.js`). Em desenvolvimento o proxy do Vite (`frontend/vite.config.js`) encaminha para `localhost:8000`. Na Vercel, o mesmo papel fica com um rewrite no `vercel.json`.
- O roteamento usa `BrowserRouter` (`frontend/src/main.jsx`), então a Vercel precisa devolver `index.html` para qualquer rota que não seja arquivo estático. Sem isso, um F5 numa página interna dá 404.

Por que precisa de túnel: o rewrite da Vercel roda nos servidores da Vercel, que não enxergam o `localhost` do notebook. O `cloudflared` em modo *quick tunnel* publica o `localhost:8000` numa URL HTTPS pública (`https://<aleatorio>.trycloudflare.com`), sem conta e sem página de aviso. Como o rewrite é feito no servidor, não existe CORS nem bloqueio de conteúdo misto.

Limitações aceitas pelo usuário:

- O site só responde com o notebook ligado, o `uvicorn` no ar e o túnel aberto.
- A URL do quick tunnel muda a cada vez que o `cloudflared` reinicia. Nesse caso é preciso trocar a URL no `vercel.json` e publicar de novo (cerca de 1 minuto).
- A API não tem autenticação. Quem tiver a URL do túnel tem acesso a tudo, inclusive ao `/api/chat`, que consome a cota do Gemini. O túnel deve ser desligado depois da demo.

## 2. Objetivo

Abrir `https://<projeto>.vercel.app` em qualquer navegador mostra o painel com dados reais vindos do backend do notebook, e `https://<projeto>.vercel.app/api/config/health` responde o JSON de saúde.

## 3. Detalhes técnicos

Arquivos:

- **Criar** `frontend/vercel.json`:

  ```json
  {
    "$schema": "https://openapi.vercel.sh/vercel.json",
    "rewrites": [
      { "source": "/api/:path*", "destination": "https://<URL-DO-TUNEL>/api/:path*" },
      { "source": "/(.*)", "destination": "/index.html" }
    ]
  }
  ```

  A ordem importa: o rewrite de `/api` vem antes do fallback de SPA. Arquivos estáticos existentes (`/assets/...`) são servidos antes dos rewrites pela própria Vercel.

- **Modificar** `.gitignore` (raiz): adicionar `.vercel/`. A pasta é criada pelo CLI no `vercel link` e guarda os IDs do projeto.

Configuração do projeto na Vercel (respondida no primeiro `vercel` interativo):

- Diretório raiz: `frontend` (o comando roda de dentro dela).
- Framework: Vite (detectado sozinho). Build `npm run build`, saída `dist`.
- Nenhuma variável de ambiente na Vercel. O front não lê nenhuma no build.

Nada muda no backend. O `uvicorn` continua escutando em `127.0.0.1:8000`, e o `cloudflared` se conecta a ele localmente.

## 4. Ferramentas e requisitos

- `cloudflared` para Windows: `winget install --id Cloudflare.cloudflared`. Não está instalado hoje.
- Vercel CLI via `npx vercel`, sem instalação global. Node já está instalado.
- Conta Vercel do usuário. O login (`npx vercel login`) é interativo e feito pelo próprio usuário com `! npx vercel login` no prompt.
- Backend no ar: `cd backend && uvicorn app.main:app` com o `.env` atual (FIWARE_HOST, chave do Gemini).
- EC2 do FIWARE ligada, para que o painel mostre dados reais.

## 5. Passos

Cada passo para e reporta o resultado antes do próximo.

1. Instalar o `cloudflared` com `winget install --id Cloudflare.cloudflared`. Abrir um terminal novo e rodar `cloudflared --version`. Esperado: imprime a versão.
2. Subir o backend em um terminal: `cd backend` e depois `uvicorn app.main:app`. Esperado: `curl http://localhost:8000/api/config/health` responde JSON.
3. Abrir o túnel em outro terminal: `cloudflared tunnel --url http://localhost:8000`. Esperado: o log mostra uma URL `https://<aleatorio>.trycloudflare.com`. Anotar a URL e deixar o terminal aberto.
4. Testar o túnel: `curl https://<aleatorio>.trycloudflare.com/api/config/health`. Esperado: o mesmo JSON do passo 2.
5. Criar `frontend/vercel.json` com o conteúdo da seção 3, trocando `<URL-DO-TUNEL>` pelo host anotado no passo 3 (sem `https://` duplicado e sem barra no final).
6. Adicionar `.vercel/` ao `.gitignore` da raiz. Conferir com `git status`: aparecem só `frontend/vercel.json` e `.gitignore`.
7. Rodar `npm run build` dentro de `frontend`. Esperado: termina sem erro e gera `frontend/dist`.
8. Commit: `chore: adiciona vercel.json com rewrite da api e fallback de spa`.
9. O usuário faz o login: `! npx vercel login`. Esperado: mensagem de login concluído.
10. **Ação externa, confirmar com o usuário antes.** Dentro de `frontend`, rodar `npx vercel` (preview). Responder: escopo = conta do usuário, link para projeto existente = não, nome = `smart-solutions-vinheria` (ou o que o usuário preferir), diretório = `./`, manter as configurações detectadas do Vite. Esperado: imprime uma URL de preview.
11. Verificar o preview (seção 6). Se passar, publicar em produção: `npx vercel --prod`. Esperado: imprime a URL de produção `https://<projeto>.vercel.app`.
12. Verificar a produção (seção 6) e reportar a URL ao usuário.

### Quando a URL do túnel mudar

Repetir o passo 3, trocar a URL em `frontend/vercel.json`, rodar `npx vercel --prod` dentro de `frontend` e commitar com `chore: atualiza url do tunel no vercel.json`.

## 6. Como verificar

- `curl https://<projeto>.vercel.app/api/config/health` responde o mesmo JSON do backend local.
- Abrir `https://<projeto>.vercel.app` no navegador: a visão geral lista as vinherias com status.
- Entrar numa página interna (por exemplo o detalhe de uma vinheria) e apertar F5: a página recarrega normalmente, sem 404 da Vercel.
- Abrir um gráfico de histórico e mandar uma pergunta no chatbot: os dois respondem.
- No DevTools, aba Network: as chamadas vão para `https://<projeto>.vercel.app/api/...`, sem erro de CORS nem de conteúdo misto.
- Desligar o `cloudflared` e recarregar o site: as chamadas `/api` falham. Isso confirma que o backend é o do notebook. Religar depois do teste. Se a URL mudar, aplicar o procedimento do fim da seção 5.
