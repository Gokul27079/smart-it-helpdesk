# Smart IT Help Desk – AI Ticket Classification System

A practical Flask + SQLite IT support system that uses an explainable TF-IDF and Logistic Regression pipeline to classify tickets, detect priority, and recommend a support team.

## Features

- Ticket intake with requester details, department, and optional attachment
- Eight ML categories: Hardware, Software, Network, Access & Account, Security, Email, Database, Other
- Confidence score and low-confidence manual-review fallback
- Transparent keyword-based priority detection (Critical, High, Medium, Low)
- Automatic support-team routing
- Unique ticket IDs (`TKT-00001`)
- Dashboard metrics sourced from SQLite, charts, recent queue, filters, and responsive dark UI
- Ticket status workflow: Open → In Progress → Resolved → Closed
- Activity/audit log for status updates
- REST API for classify, CRUD, and status updates
- 128-row bundled training dataset and reproducible model training script
- Pytest coverage for classification, priority, routing, persistence, and APIs

## Architecture

`app.py` exposes browser routes and JSON APIs. `database/database.py` owns SQLite access and the `tickets`/`ticket_logs` schema. `ml/train_model.py` trains and saves artifacts, while `ml/predictor.py` loads them at runtime. `services/priority.py` applies transparent critical/high/medium/low rules and `services/team_router.py` maps categories to support teams. Jinja templates and static CSS/JavaScript form the responsive UI.

## Tech stack

Python 3.10+, Flask, SQLite, pandas, NumPy, scikit-learn, joblib, Chart.js, HTML5, CSS3, JavaScript, pytest.

## Installation and running

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python ml/train_model.py
python app.py
```

Open http://127.0.0.1:5000. The app creates `helpdesk.db` on first start.

## AI workflow

1. Title and description are combined and normalized.
2. `TfidfVectorizer` represents meaningful unigrams and bigrams.
3. A balanced `LogisticRegression` model predicts the category.
4. The highest class probability becomes the confidence score.
5. Top non-zero TF-IDF terms are displayed as detected keywords.
6. Confidence below 60% is visibly flagged for manual review.
7. Priority rules scan normalized text; critical rules take precedence.

TF-IDF and Logistic Regression are deliberately understandable and fast for a final-year project. The dataset is a realistic starter dataset, not a claim of production-grade incident intelligence.

## Database

`tickets` stores request details, model output, priority, routing, status, and timestamps. `ticket_logs` stores creation and status transitions. Foreign keys and indexes support safe deletion and common queue filters.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/classify` | Classify `{title, description}` without persisting |
| POST | `/api/tickets` | Validate, classify, and create a ticket |
| GET | `/api/tickets` | List with `q`, `category`, `priority`, `status`, `department`, `sort` filters |
| GET | `/api/tickets/<id>` | Retrieve a ticket and audit log |
| PUT | `/api/tickets/<id>` | Update status using `{status}` |
| DELETE | `/api/tickets/<id>` | Delete a ticket |

Example:

```bash
curl -X POST http://127.0.0.1:5000/api/classify \
  -H "Content-Type: application/json" \
  -d '{"title":"VPN is not connecting","description":"My laptop cannot connect to the office VPN."}'
```

## Testing

```bash
pytest -q
```

The test suite covers ticket creation, API validation, AI classification, confidence output, priority rules, team routing, database insertion, status transitions, and deletion.

## Screenshots

Run the application locally and capture the Overview, New Ticket, Ticket Queue, and Ticket Detail pages for a portfolio README. The UI intentionally uses live database values rather than seeded dashboard placeholders.

## Future improvements

- Human feedback loop for retraining
- Role-based authentication and SSO
- Celery/RQ background classification for large attachments
- Object storage and virus scanning for uploads
- Multilingual embeddings and semantic similarity
- SLA timers, notifications, and knowledge-base suggestions
- PostgreSQL deployment and structured observability
