# Web Voting Championship

Platform voting kompetisi online dengan pembayaran QRIS (Midtrans) — pembayaran otomatis dikonversi menjadi vote.

## Status Saat Ini (Sprint 1–7 selesai, Sprint 8 sebagian)

Backend penuh sudah terhubung ke database. Alur inti **vote → pembayaran → leaderboard realtime** sudah berjalan end-to-end.

### Halaman publik (SSR)

- `/` — Landing page + preview top-3 Leaderboard live (SSE)
- `/events` — Daftar tim pada event yang sedang berjalan
- `/events/{event_id}/vote/{team_id}` — Pilih paket vote, buat invoice QRIS, polling status pembayaran
- `/leaderboard` — Leaderboard live via Server-Sent Events
- `/admin/login` — Login admin (session cookie)
- `/admin` — Dashboard panitia (statistik, transaksi, export)

### API (`/api/v1/`)

- **Events & tim** — baca publik + CRUD admin
- **Auth** — login, logout, profil, ganti password
- **Payments** — buat invoice QRIS, cek status, webhook Midtrans (idempotent)
- **Leaderboard** — data awal + stream SSE realtime
- **Admin** — dashboard, daftar transaksi, audit log, export Excel

### Sprint checklist

| Sprint | Status | Ringkasan |
|---|---|---|
| 1 — Frontend | ✅ Selesai | SSR Jinja2 + Alpine.js + Tailwind |
| 2 — Database | ✅ Selesai | SQLAlchemy async, models, seeder; Alembic migration masih stub |
| 3 — CRUD Event/Tim | ✅ Selesai | Service + repository + dashboard admin |
| 4 — Auth | ✅ Selesai | Session cookie, Argon2, middleware `require_admin` |
| 5 — Midtrans | ✅ Selesai | QRIS + webhook + mock fallback jika key kosong |
| 6 — Vote engine + SSE | ✅ Selesai | Vote hanya setelah payment SUCCESS; `EventSource` di `leaderboard.js` |
| 7 — Cache & export | ✅ Selesai | Redis/in-memory cache, audit log, export Excel |
| 8 — Hardening | 🟡 Sebagian | Rate limit, CSRF, security headers, audit middleware sudah ada |
| 8 — Belum | ⬜ Menyusul | Queue system, Turnstile CAPTCHA, Cloudflare, monitoring, deployment |

## Menjalankan Secara Lokal

```bash
pip install -r requirements.txt
cp .env.example .env
# Dev tanpa Postgres: set DATABASE_URL=sqlite+aiosqlite:///./web_voting.db
# Dev tanpa Redis: set REDIS_URL=memory://
uvicorn app.main:app --reload
```

Buka http://localhost:8000 — health check di `/health`.

Saat database kosong, **seeder otomatis** mengisi:
- 1 event *Kompetisi Band Antar Sekolah 2026* (status Voting Open)
- 6 tim peserta
- 3 paket vote (Bronze / Silver / Gold)
- Admin: `admin@panitia.id` / `admin12345`

> **Midtrans:** isi `MIDTRANS_SERVER_KEY` & `MIDTRANS_CLIENT_KEY` di `.env` untuk QRIS asli. Tanpa key, sistem memakai mock QRIS (dev). Webhook lokal butuh tunnel publik (ngrok) ke `/api/v1/payments/webhook`.

## Struktur & Aturan Proyek

Arsitektur **MVC + Service Layer** — router hanya terima request/kirim response, business logic di `services/`, query DB di `repositories/`.

Aturan bisnis penting:
- Tidak ada vote tanpa transaksi pembayaran sukses
- Vote tidak dihitung dari nominal pembayaran (harus lewat `vote_packages`)
- `vote_snapshot` disimpan per transaksi agar perubahan paket tidak mengubah riwayat
- Realtime memakai SSE, bukan WebSocket
- Tidak ada hard delete pada data transaksi

Detail implementasi dan handoff teknis: lihat `HANDOFF.md`.
