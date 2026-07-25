# Frontend (Next.js 16)

Next.js 16 UI for the Python debugging backend.

## 1) Install

```bash
cd frontend
npm install
```

## 2) Configure API base URL

```bash
copy .env.local.example .env.local
```

Edit `.env.local` if your backend runs on a different URL.

## 3) Run

```bash
npm run dev
```

Open <http://localhost:3000>.

## Pages

- `/` - run one debug session and inspect attempt history
- `/eval` - run QuixBugs eval and inspect pass-rate table

