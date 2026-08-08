# Bharat OS

Eligibility reasoning and application preparation for Indian government funding schemes.

Helps startups and MSMEs discover schemes they qualify for, understand why, identify
document gaps, and generate editable application drafts.

## Stack

- **Backend:** FastAPI, Python 3.11, SQLAlchemy 2, PostgreSQL
- **Frontend:** Next.js 15, React 19, Tailwind CSS
- **AI:** Provider-neutral LLM adapter (mock by default, Gemini optional)

## Quick start

```bash
# Create databases
sudo -u postgres createuser --createdb "$USER"
sudo -u postgres createdb -O "$USER" bharat_os

# Install
cp .env.example .env
make install
make migrate
make seed

# Run
make dev-backend   # http://localhost:8000
make dev-frontend  # http://localhost:3000
```

## Commands

```
make install        install dependencies
make migrate        run database migrations
make seed           load scheme data
make dev-backend    start API server
make dev-frontend   start frontend
make test           run tests
make lint           run linters
```
