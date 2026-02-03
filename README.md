# 🎬 ClipVox — Gerador de Videoclipes com IA

## 📁 Estrutura do Projeto

```
clipvox/
├── frontend/                  ← React + Vite (Static Site no Render)
│   ├── public/
│   │   └── favicon.svg
│   ├── src/
│   │   ├── main.jsx           ← Entry point do React
│   │   ├── App.jsx            ← Roteador principal
│   │   └── pages/
│   │       ├── Landing.jsx    ← Página inicial (sua landing page!)
│   │       └── Dashboard.jsx  ← Tela do usuário (em desenvolvimento)
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── backend/                   ← FastAPI Python (Web Service no Render)
│   ├── main.py                ← API principal
│   └── requirements.txt       ← Dependências Python
├── render.yaml                ← Configuração do deploy no Render
└── README.md                  ← Você está aqui!
```

---

## 🚀 COMO RODAR LOCAL

### 1. Frontend
```bash
cd frontend
npm install
npm run dev
# Acesse: http://localhost:3000
```

### 2. Backend
```bash
cd backend
pip install -r requirements.txt
python main.py
# Acesse: http://localhost:8000/docs  (Swagger)
```

---

## ☁️ DEPLOY NO RENDER (passo a passo)

### Passo 1 — Criar repositório no GitHub
- Crie um repo chamado `clipvox`
- Coloque todos os arquivos na raiz

### Passo 2 — Conectar ao Render
1. Acesse: https://dashboard.render.com
2. Clique em **"New"** → **"Blueprint"**
3. Conecte seu GitHub
4. Seleciona o repositório `clipvox`
5. O Render vai ler o `render.yaml` automaticamente

### Passo 3 — Deploy automático
O Render vai criar:
- **clipvox-frontend** → Static Site (sua landing page)
- **clipvox-backend** → Web Service (API FastAPI)

### Passo 4 — Testar
- Frontend: `https://clipvox-frontend.onrender.com`
- Backend: `https://clipvox-backend.onrender.com/docs`
- Health: `https://clipvox-backend.onrender.com/health`

---

## 📋 TODO (próximos passos)

- [ ] Dashboard com upload de áudio
- [ ] Integração com API de análise de áudio (Librosa)
- [ ] Integração com Claude API (conceito criativo)
- [ ] Integração com Stability AI (geração de vídeo)
- [ ] Sistema de créditos com pagamento
- [ ] PostgreSQL no Render
- [ ] Canvas de edição de cenas
