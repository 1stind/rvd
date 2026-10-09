# Handoff Dokumentasi — Web Voting Championship

**Status:** Backend penuh + frontend terintegrasi. Alur vote → payment → leaderboard realtime sudah berjalan end-to-end.
**Tanggal handoff:** 3 Agustus 2026
**Referensi aturan project:** `CLAUDE.md` (root proyek)

---

## 1. Struktur Folder

```
web-voting/
├── app/
│   ├── main.py                 # Entry point: lifespan, middleware, routers, exception handlers
│   ├── core/
│   │   ├── config.py           # Settings (pydantic-settings), baca dari .env
│   │   ├── database.py         # SQLAlchemy 2.0 async engine/session (Alembic manages schema)
│   │   └── security.py         # Argon2 hashing + signed session token
│   ├── models/                 # ORM: Event, Team, VotePackage, Payment, VoteLog, User, AuditLog
│   ├── repositories/           # Query DB per entity (base + event, team, payment, dll.)
│   ├── services/               # Business logic (event, payment, auth, cache, export, seeder, audit)
│   ├── schemas/                # Pydantic request/response (envelope {success, message, data})
│   ├── routers/
│   │   ├── pages.py            # Halaman SSR (Jinja2)
│   │   ├── events.py           # API event/tim + admin CRUD
│   │   ├── auth.py             # Login/logout/session
│   │   ├── payments.py         # Invoice QRIS + webhook Midtrans
│   │   ├── admin.py            # Dashboard, audit log, export Excel
│   │   ├── leaderboard_stream.py  # SSE realtime
│   │   └── deps.py             # require_admin dependency
│   ├── middleware/
│   │   ├── rate_limit.py       # Sliding window per IP (Redis / in-memory)
│   │   ├── security.py         # CSRF double-submit cookie + security headers
│   │   └── audit.py            # Audit log middleware untuk aksi admin
│   ├── utils/                  # Helper umum (new_id, dumps, dll.)
│   ├── templates/
│   │   ├── base.html
│   │   ├── partials/           # navbar, footer
│   │   └── pages/              # landing, events, vote, leaderboard, admin_login,
│   │                           # admin_dashboard, voting_closed
│   └── static/
│       ├── css/custom.css
│       └── js/leaderboard.js   # Alpine scoreboard() — SSE + fallback polling
├── migrations/                 # Alembic (file migration ada, schema masih stub/kosong)
├── uploads/                    # Asset upload (logo tim, dll.) — belum dipakai
├── tests/                      # Belum ada test
├── requirements.txt
├── alembic.ini
├── .env.example
└── README.md
```

Arsitektur **MVC + Service Layer**: router → service → repository → database. Template SSR di-hydrate dengan data dari service layer (bukan `demo_data.py`).

---

## 2. Halaman Frontend (SSR)

| Halaman | Template | Status | Catatan |
|---|---|---|---|
| Landing | `pages/landing.html` | ✅ Terintegrasi DB | Hero + preview top-3 via `scoreboard()` SSE |
| Daftar Event/Tim | `pages/events.html` | ✅ Terintegrasi DB | Grid kontestan dari database; rank/vote statis (server-rendered) |
| Halaman Vote | `pages/vote.html` | ✅ Terintegrasi API | POST `/api/v1/payments`, polling status, modal sukses/gagal |
| Leaderboard | `pages/leaderboard.html` | ✅ SSE realtime | `EventSource` ke `/api/v1/leaderboard/stream` |
| Voting Ditutup | `pages/voting_closed.html` | ✅ Selesai | Ditampilkan jika event bukan `voting_open` |
| Admin Login | `pages/admin_login.html` | ✅ Terintegrasi API | POST `/api/v1/auth/login`, redirect ke `/admin` |
| Admin Dashboard | `pages/admin_dashboard.html` | ✅ Terintegrasi API | Statistik, transaksi, export via `/api/v1/admin/*` |

Semua halaman: mobile-first, Tailwind CDN + JIT config custom (`base.html`), Alpine.js untuk interaksi.

---

## 3. Komponen Reusable

| Komponen | Lokasi | Dipakai di | Fungsi |
|---|---|---|---|
| `base.html` | `templates/base.html` | Semua halaman | Layout, Tailwind config, Google Fonts, Alpine CDN |
| Navbar | `partials/navbar.html` | Semua halaman | Sticky nav, menu mobile via Alpine |
| Footer | `partials/footer.html` | Semua halaman | Info navigasi & keamanan pembayaran |
| `scoreboard()` | `static/js/leaderboard.js` | landing, leaderboard | SSE realtime + fallback polling 30 detik |
| `votePage()` | inline di `pages/vote.html` | vote.html | Paket, qty, total, buat invoice, polling status |
| `adminLogin()` | inline di `pages/admin_login.html` | admin_login | Form login ke `/api/v1/auth/login` |
| `.rank-badge` | `static/css/custom.css` | landing, events, vote, leaderboard | Badge medali emas/perak/perunggu |
| `.vote-tick` | `static/css/custom.css` | leaderboard | Animasi flash saat vote berubah |

---

## 4. Route Halaman (`app/routers/pages.py`)

| Method | Path | Handler | Render / Aksi |
|---|---|---|---|
| GET | `/` | `landing` | `pages/landing.html` |
| GET | `/events` | `events_list` | `pages/events.html` |
| GET | `/events/{event_id}/vote/{team_id}` | `vote_page` | `pages/vote.html` atau `voting_closed.html` |
| GET | `/leaderboard` | `leaderboard` | `pages/leaderboard.html` |
| GET | `/admin/login` | `admin_login` | `pages/admin_login.html` (redirect jika sudah login) |
| GET | `/admin` | `admin_dashboard` | `pages/admin_dashboard.html` (redirect jika belum login) |
| GET | `/static/*` | — | Static files |
| GET | `/health` | `health` | JSON health check (`main.py`) |

**Validasi yang sudah ada:** `team.event_id == event_id`, event soft-delete, status voting ditutup → halaman `voting_closed`.

---

## 5. Data Awal (Seeder)

Seeding tidak lagi dilakukan otomatis saat startup. Gunakan CLI:

```bash
# Development: seed demo data + admin
python -m app.seeds run demo
python -m app.seeds run admin --email admin@panitia.id --password admin12345

# Atau sekaligus
python -m app.seeds run all

# Production: seed admin saja
python -m app.seeds run admin --email admin@domain-kamu.com --password <password-kuat>
```

Struktur seed:

| File | Fungsi |
|---|---|
| `app/seeds/demo.py` | Event demo, 6 tim, 1 paket vote, system settings |
| `app/seeds/admin.py` | Admin user (idempoten: skip jika email sudah ada) |
| `app/seeds/run.py` | CLI entry point (`python -m app.seeds`) |

| Entitas | Isi |
|---|---|
| Event | *Kompetisi Band Antar Sekolah 2026*, status `voting_open`, tutup 20 Agustus 2026 |
| Tim | 6 tim (Nada Senja, Ambyar Orchestra, Ritme Malam, dll.) |
| Admin | `admin@panitia.id` / `admin12345` (default) |

Production: jalankan `python -m app.seeds run admin` dengan kredensial kuat. Jangan jalankan `run demo` di production.

---

## 6. API yang Sudah Diimplementasi

Semua respons API memakai envelope `{success, message, data}`.

### Events & tim (`/api/v1/`)

| Method | Path | Auth | Fungsi |
|---|---|---|---|
| GET | `/events` | — | Daftar event (filter status) |
| GET | `/events/{event_id}` | — | Detail event |
| GET | `/events/{event_id}/teams` | — | Tim + vote count |
| GET | `/events/{event_id}/vote-packages` | — | Paket vote event |
| GET | `/leaderboard` | — | Leaderboard (query `event_id`, `limit`) |
| POST | `/admin/events` | Admin | Buat event |
| PUT | `/admin/events/{event_id}` | Admin | Update event |
| DELETE | `/admin/events/{event_id}` | Admin | Soft delete event |
| POST | `/admin/events/{event_id}/teams` | Admin | Tambah tim |
| PUT | `/admin/events/{event_id}/teams/{team_id}` | Admin | Update tim |
| DELETE | `/admin/events/{event_id}/teams/{team_id}` | Admin | Soft delete tim |

### Auth (`/api/v1/auth/`)

| Method | Path | Fungsi |
|---|---|---|
| POST | `/login` | Set session cookie (`wvc_session`) |
| POST | `/logout` | Hapus session |
| GET | `/me` | Profil user saat ini |
| POST | `/change-password` | Ganti password |

### Payments (`/api/v1/`)

| Method | Path | Fungsi |
|---|---|---|
| POST | `/payments` | Buat invoice QRIS (body: `team_id`, `package_code`, `qty`) |
| GET | `/payments/{payment_id}/status` | Polling status pembayaran |
| POST | `/payments/webhook` | Callback Midtrans (signature + idempotency) |

### Leaderboard realtime

| Method | Path | Fungsi |
|---|---|---|
| GET | `/leaderboard/stream?event_id=` | **SSE** — push update setelah vote masuk |

### Admin (`/api/v1/admin/` — semua butuh session admin)

| Method | Path | Fungsi |
|---|---|---|
| GET | `/dashboard` | Statistik event (vote, revenue, tim) |
| GET | `/payments` | Daftar transaksi |
| GET | `/audit-logs` | Jejak audit aksi admin |
| GET | `/exports/results` | Download Excel hasil voting |
| GET | `/exports/payments` | Download Excel transaksi |

---

## 7. State Management

- **Tidak ada global store.** Setiap halaman Alpine (`x-data`) berdiri sendiri.
- **Hydration pattern:** data awal di-render server-side (Jinja2), di-embed ke Alpine sebagai JSON. Interaksi selanjutnya via fetch/SSE.
- **Leaderboard realtime:** `EventSource` ke `/api/v1/leaderboard/stream` + fallback polling `/api/v1/leaderboard` setiap 30 detik.
- **Vote flow:** `votePage()` POST invoice → polling `/payments/{id}/status` tiap 3 detik → modal sukses/gagal/kedaluwarsa.
- **CSRF:** cookie `wvc_csrf` + header `X-CSRF-Token` pada mutasi state (POST/PUT/DELETE). Webhook Midtrans dikecualikan (ditandatangani signature).
- **Session:** cookie `wvc_session` (signed, 12 jam).

---

## 8. Model Database

| Model | Tabel | Fungsi |
|---|---|---|
| `Event` | `events` | Kompetisi; lifecycle: draft → published → voting_open → closed → finished → archived |
| `Team` | `teams` | Peserta per event |
| `VotePackage` | `vote_packages` | Paket harga & jumlah vote (sumber kebenaran) |
| `Payment` | `payments` | Transaksi + `vote_snapshot` (immutable) |
| `VoteLog` | `vote_logs` | Log vote setelah payment SUCCESS |
| `User` | `users` | Admin/panitia |
| `AuditLog` | `audit_logs` | Jejak audit |

Tabel dibuat via Alembic migration (`9db3118321d8_refactor_database_architecture.py`). Schema adalah single source of truth; tidak ada `create_all()` di aplikasi.

---

## 9. Middleware & Keamanan

| Middleware | Status | Fungsi |
|---|---|---|
| `RateLimitMiddleware` | ✅ | Sliding window per IP; bucket terpisah untuk public/payment/webhook/auth |
| `SecurityMiddleware` | ✅ | X-Content-Type-Options, X-Frame-Options, Referrer-Policy, set cookie CSRF |
| `CsrfMiddleware` | ✅ | Validasi double-submit cookie pada mutasi `/api/` |
| `AuditMiddleware` | ✅ | Log aksi admin ke `audit_logs` |

---

## 10. Sprint Progress

| Sprint | Status | Detail |
|---|---|---|
| 1 — Frontend | ✅ | SSR + Alpine + Tailwind, semua halaman publik & admin |
| 2 — Database | ✅ | SQLAlchemy async, 7 models, seeder; Alembic migration belum diisi |
| 3 — CRUD Event/Tim | ✅ | Service + repository + admin dashboard UI |
| 4 — Auth | ✅ | Argon2, session cookie, `require_admin`, login form terhubung |
| 5 — Midtrans | ✅ | Snap QRIS, webhook signature, idempotency, mock fallback dev |
| 6 — Vote engine + SSE | ✅ | Vote hanya setelah SUCCESS; broadcast SSE via Redis/in-memory pub/sub |
| 7 — Cache & export | ✅ | Redis cache leaderboard, audit log, export Excel (openpyxl) |
| 8 — Hardening | 🟡 | Rate limit, CSRF, security headers sudah; sisanya belum |

### Yang belum dikerjakan

- **Queue system** — `MAX_ACTIVE_USER=500` ada di config, logic antrian & halaman waiting belum ada
- **Turnstile CAPTCHA** — belum diintegrasikan
- **Cloudflare** — `CLOUDFLARE_API_KEY` ada di config, belum dipakai
- **Monitoring & deployment** — belum ada (VPS, CI/CD, logging terpusat)
- **Automated test** — folder `tests/` kosong
- **Halaman error kustom** (404/500 desain) — API pakai JSON envelope; halaman SSR fallback ke default FastAPI
- **Riwayat vote per user** — butuh auth publik (saat ini auth hanya admin)
- **Meta tag Open Graph, favicon, sitemap**
- **Upload asset tim** — folder `uploads/` belum terhubung

---

## 11. Bug / Keterbatasan yang Diketahui

1. **`scoreboard()` method `destroy()` tidak dipanggil otomatis oleh Alpine** — aman untuk multi-page (full reload), tapi perlu hook cleanup jika nanti jadi SPA.
2. **`events.html` rank/vote statis** — tidak live seperti landing/leaderboard; pertimbangkan SSE atau polling jika UX perlu konsisten.
3. **Format angka tidak seragam** — `events.html` pakai Jinja format, halaman lain pakai `toLocaleString('id-ID')` di JS.
4. **Menu mobile tidak auto-close** setelah link diklik (`navbar.html`).
5. **Mock QRIS** — tanpa key Midtrans, `qr_string` berupa teks mock (bukan gambar QR); cukup untuk dev, bukan production.
6. **Redis opsional** — fallback in-memory (`REDIS_URL=memory://`) hanya aman single-process; production multi-worker wajib Redis.
7. **`demo_data.py` masih ada** — legacy Sprint 1, tidak lagi diimport; bisa dihapus.

---

## 12. Menjalankan & Konfigurasi

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Variabel `.env` penting:

| Variabel | Default | Keterangan |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Dev: `sqlite+aiosqlite:///./web_voting.db` |
| `SECRET_KEY` | — | Wajib diganti production |
| `MIDTRANS_SERVER_KEY` / `MIDTRANS_CLIENT_KEY` | kosong | Kosong = mock QRIS |
| `MIDTRANS_IS_PRODUCTION` | `false` | `true` untuk live |
| `APP_BASE_URL` | `http://localhost:8000` | URL publik untuk callback webhook |
| `REDIS_URL` | `redis://localhost:6379/0` | Dev: `memory://` untuk fallback in-memory |
| `MAX_ACTIVE_USER` | `500` | Belum dipakai (queue system menyusul) |

**Webhook lokal:** Midtrans butuh URL publik. Pakai ngrok/tunnel ke `POST /api/v1/payments/webhook`.

**Login admin dev:** `admin@panitia.id` / `admin12345` (dari seeder).

---

## 13. Prioritas Selanjutnya

1. **Automated test** — minimal payment flow, webhook idempotency, vote engine, auth
3. **Queue system** — enforce `MAX_ACTIVE_USER`, halaman antrian waiting
4. **Turnstile + Cloudflare** — proteksi bot & DDoS
5. **Deployment** — VPS, HTTPS, env production, matikan auto-seed
6. **UX polish** — halaman error kustom, favicon/OG tags, live update di `events.html`
