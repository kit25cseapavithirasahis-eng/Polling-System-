import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_socketio import SocketIO, emit
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Poll, Choice, Vote
from sqlalchemy import func

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretpremiumkey123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*")
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

# --- ROUTES ---

@app.route('/')
def index():
    polls = Poll.query.order_by(Poll.created_at.desc()).all()
    return render_template('index.html', polls=polls)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists', 'error')
        else:
            new_user = User(username=username, password=generate_password_hash(password, method='scrypt'))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        question = request.form.get('question')
        choices = request.form.getlist('choices')
        
        # Filter out empty choices
        choices = [c.strip() for c in choices if c.strip()]
        
        if not question or len(choices) < 2:
            flash('Please provide a question and at least two choices.', 'error')
            return redirect(url_for('create'))
            
        new_poll = Poll(question=question, creator_id=current_user.id)
        db.session.add(new_poll)
        db.session.flush() # Get the poll id
        
        for choice_text in choices:
            new_choice = Choice(text=choice_text, poll_id=new_poll.id)
            db.session.add(new_choice)
            
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('create.html')

@app.route('/poll/<int:poll_id>')
def view_poll(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    
    # Check if user has already voted
    has_voted = False
    voted_choice_id = None
    if current_user.is_authenticated:
        vote = Vote.query.filter_by(poll_id=poll_id, user_id=current_user.id).first()
        if vote:
            has_voted = True
            voted_choice_id = vote.choice_id
            
    # Calculate initial results
    results = get_poll_results(poll_id)
    
    return render_template('poll.html', poll=poll, has_voted=has_voted, voted_choice_id=voted_choice_id, initial_results=results)

@app.route('/api/vote', methods=['POST'])
@login_required
def vote():
    data = request.get_json()
    poll_id = data.get('poll_id')
    choice_id = data.get('choice_id')
    
    poll = Poll.query.get(poll_id)
    choice = Choice.query.get(choice_id)
    
    if not poll or not choice or choice.poll_id != poll.id:
        return jsonify({'status': 'error', 'message': 'Invalid poll or choice'}), 400
        
    # Check for duplicate
    existing_vote = Vote.query.filter_by(poll_id=poll_id, user_id=current_user.id).first()
    if existing_vote:
        return jsonify({'status': 'error', 'message': 'You have already voted on this poll.'}), 400
        
    new_vote = Vote(poll_id=poll_id, choice_id=choice_id, user_id=current_user.id)
    db.session.add(new_vote)
    db.session.commit()
    
    # Broadcast new results
    results = get_poll_results(poll_id)
    socketio.emit('results_updated', {'poll_id': poll_id, 'results': results}, namespace='/')
    
    return jsonify({'status': 'success', 'message': 'Vote recorded successfully!'})

def get_poll_results(poll_id):
    # Get all choices and their vote counts
    results = db.session.query(
        Choice.id, Choice.text, func.count(Vote.id).label('vote_count')
    ).outerjoin(Vote, Choice.id == Vote.choice_id).filter(Choice.poll_id == poll_id).group_by(Choice.id).all()
    
    return [{'id': r.id, 'text': r.text, 'count': r.vote_count} for r in results]

# --- SOCKET IO ---

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    socketio.run(app, debug=True, host='127.0.0.1', port=5000, allow_unsafe_werkzeug=True)
