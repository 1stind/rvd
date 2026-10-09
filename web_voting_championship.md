# CLAUDE.md — Web Voting Championship

## 1. Project Overview
- Name: Web Voting Championship
- Description: Multi-event online voting platform with paid voting using QRIS and Indonesian payment gateways.
- Goal: Build a secure, transparent, reusable voting platform for competitions where payments are automatically converted into votes.

### Target Users
- Event Organizer (EO)
- School Competition Committee
- Contest Participants
- Supporters

- Version: v1.0.0
- Status: Active Development

## 2. Tech Stack
- Language: Python 3.13
- Framework: FastAPI
- Frontend: HTML + Jinja2
- Styling: Tailwind CSS
- Database: PostgreSQL
- ORM: SQLAlchemy 2.0
- Migration: Alembic
- Authentication: Session Authentication
- Queue: Redis
- Realtime: Server-Sent Events (SSE)
- Cache: Redis
- Payment Gateway: Midtrans
- Web Server: Nginx
- Deployment: Ubuntu VPS
- CDN & Security: Cloudflare
- Package Manager: pip

## 3. Commands
```bash
uvicorn app.main:app --reload
alembic revision --autogenerate -m "migration_name"
alembic upgrade head
pip install -r requirements.txt
pip freeze > requirements.txt
```

## 4. Project Structure
web-voting/
  app/
    core/
    routers/
    services/
    repositories/
    models/
    schemas/
    middleware/
    utils/
    templates/
    static/
    main.py
  uploads/
  migrations/
  tests/
  .env
  requirements.txt

## 5. Naming Convention
- File: snake_case.py
- Class: PascalCase
- Function: snake_case
- Variable: snake_case
- Constant: UPPER_SNAKE_CASE

## 6. Code Convention
- Clean Architecture
- SOLID
- DRY
- Type hint
- No hardcode

## 7. API Base
/api/v1/

## 8. Performance
- Target: 500 concurrent users

## 9. Security
- HTTPS
- Cloudflare
- CAPTCHA
- Argon2
- CSRF
- Rate limiter

## 10. Roadmap
- Sprint 1 → FastAPI, Landing Page
- Sprint 2 → Database
- Sprint 3 → CRUD
- Sprint 4 → Auth
- Sprint 5 → Payment
- Sprint 6 → Vote Engine
- Sprint 7 → Queue
- Sprint 8 → Deployment
