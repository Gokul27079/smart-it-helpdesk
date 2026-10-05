import csv
import os
import re
from pathlib import Path
from flask import Flask, jsonify, redirect, render_template, request, url_for, flash
from werkzeug.utils import secure_filename

from config import ALLOWED_EXTENSIONS, DATABASE_PATH, MAX_CONTENT_LENGTH, MODEL_DIR, SECRET_KEY, UPLOAD_DIR
from database.database import Database
from ml.predictor import TicketPredictor
from services.priority import detect_priority
from services.team_router import recommended_team

app = Flask(__name__)
app.config.update(SECRET_KEY=SECRET_KEY, MAX_CONTENT_LENGTH=MAX_CONTENT_LENGTH)
UPLOAD_DIR.mkdir(exist_ok=True)
db = Database(DATABASE_PATH)
db.init_db()
predictor = TicketPredictor(MODEL_DIR)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_payload(payload):
    required = ['title', 'description', 'user_name', 'user_email', 'department']
    missing = [field for field in required if not str(payload.get(field, '')).strip()]
    if missing:
        return f"Please provide: {', '.join(missing)}"
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', payload['user_email'].strip()):
        return 'Please enter a valid email address.'
    if len(payload['title'].strip()) < 3 or len(payload['description'].strip()) < 10:
        return 'Title must be at least 3 characters and description at least 10 characters.'
    return None


def classify_payload(title, description):
    result = predictor.predict(title, description)
    priority, reason, matches = detect_priority(f'{title} {description}')
    result.update({'priority': priority, 'priority_reason': reason, 'priority_matches': matches,
                   'recommended_team': recommended_team(result['category'])})
    return result


def serialize_ticket(ticket):
    if not ticket:
        return None
    ticket = dict(ticket)
    ticket['confidence_percent'] = round(ticket['confidence'] * 100, 1)
    ticket['low_confidence'] = ticket['confidence'] < 0.6
    return ticket


@app.context_processor
def inject_globals():
    return {'model_available': predictor.available}


@app.get('/')
def dashboard():
    stats = db.stats()
    recent = [serialize_ticket(t) for t in db.list_tickets()[:8]]
    return render_template('dashboard.html', stats=stats, recent=recent)


@app.route('/tickets/new', methods=['GET', 'POST'])
def create_ticket():
    if request.method == 'POST':
        payload = request.form.to_dict()
        error = validate_payload(payload)
        if error:
            flash(error, 'danger')
            return render_template('create_ticket.html', form=payload), 400
        if not predictor.available:
            flash('The trained AI model is unavailable. Run python ml/train_model.py first.', 'danger')
            return render_template('create_ticket.html', form=payload), 503
        attachment = request.files.get('attachment')
        attachment_name = None
        if attachment and attachment.filename:
            if not allowed_file(attachment.filename):
                flash('That attachment type is not supported.', 'danger')
                return render_template('create_ticket.html', form=payload), 400
            attachment_name = secure_filename(attachment.filename)
            attachment.save(UPLOAD_DIR / attachment_name)
        result = classify_payload(payload['title'], payload['description'])
        result.update(payload, attachment_name=attachment_name)
        ticket = db.create_ticket(result)
        flash(f"Ticket {ticket['ticket_id']} created and classified successfully.", 'success')
        return redirect(url_for('ticket_detail', identifier=ticket['ticket_id']))
    return render_template('create_ticket.html', form={})


@app.get('/tickets')
def tickets():
    filters = {key: request.args.get(key, '').strip() for key in ('q', 'category', 'priority', 'status', 'department', 'sort')}
    rows = [serialize_ticket(t) for t in db.list_tickets(filters)]
    return render_template('tickets.html', tickets=rows, filters=filters)


@app.get('/tickets/<identifier>')
def ticket_detail(identifier):
    ticket = serialize_ticket(db.get_ticket(identifier))
    if not ticket:
        return render_template('error.html', message='Ticket not found.'), 404
    return render_template('ticket_details.html', ticket=ticket, logs=db.logs(identifier))


@app.put('/tickets/<identifier>/status')
def update_status_page(identifier):
    data = request.get_json(silent=True) or request.form
    status = data.get('status', '')
    if status not in {'Open', 'In Progress', 'Resolved', 'Closed'}:
        return jsonify({'error': 'Invalid status.'}), 400
    ticket = db.update_status(identifier, status)
    if not ticket:
        return jsonify({'error': 'Ticket not found.'}), 404
    return jsonify({'ticket': serialize_ticket(ticket)})


@app.delete('/tickets/<identifier>')
def delete_ticket_page(identifier):
    if not db.delete_ticket(identifier):
        return jsonify({'error': 'Ticket not found.'}), 404
    return jsonify({'message': 'Ticket deleted.'})


@app.post('/api/classify')
def api_classify():
    data = request.get_json(silent=True) or {}
    if not data.get('title') or not data.get('description'):
        return jsonify({'error': 'Title and description are required.'}), 400
    if not predictor.available:
        return jsonify({'error': 'Model unavailable. Run python ml/train_model.py.'}), 503
    return jsonify(classify_payload(data['title'], data['description']))


@app.post('/api/tickets')
def api_create_ticket():
    data = request.get_json(silent=True) or {}
    error = validate_payload(data)
    if error:
        return jsonify({'error': error}), 400
    if not predictor.available:
        return jsonify({'error': 'Model unavailable. Run python ml/train_model.py.'}), 503
    result = classify_payload(data['title'], data['description'])
    result.update({k: data[k] for k in ('title', 'description', 'user_name', 'user_email', 'department')})
    ticket = serialize_ticket(db.create_ticket(result))
    return jsonify(ticket), 201


@app.get('/api/tickets')
def api_list_tickets():
    filters = {key: request.args.get(key, '').strip() for key in ('q', 'category', 'priority', 'status', 'department', 'sort')}
    return jsonify([serialize_ticket(t) for t in db.list_tickets(filters)])


@app.get('/api/tickets/<identifier>')
def api_get_ticket(identifier):
    ticket = serialize_ticket(db.get_ticket(identifier))
    if not ticket:
        return jsonify({'error': 'Ticket not found.'}), 404
    ticket['logs'] = db.logs(identifier)
    return jsonify(ticket)


@app.put('/api/tickets/<identifier>')
def api_update_ticket(identifier):
    data = request.get_json(silent=True) or {}
    if 'status' not in data:
        return jsonify({'error': 'Only status updates are supported; provide status.'}), 400
    if data['status'] not in {'Open', 'In Progress', 'Resolved', 'Closed'}:
        return jsonify({'error': 'Invalid status.'}), 400
    ticket = db.update_status(identifier, data['status'])
    if not ticket:
        return jsonify({'error': 'Ticket not found.'}), 404
    return jsonify(serialize_ticket(ticket))


@app.delete('/api/tickets/<identifier>')
def api_delete_ticket(identifier):
    if not db.delete_ticket(identifier):
        return jsonify({'error': 'Ticket not found.'}), 404
    return jsonify({'message': 'Ticket deleted.'})


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
