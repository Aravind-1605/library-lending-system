from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Member(db.Model):
    __tablename__ = 'members'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    transactions = db.relationship('Transaction', backref='member', lazy=True)
    alerts = db.relationship('AlertsLog', backref='member', lazy=True)

class Book(db.Model):
    __tablename__ = 'books'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(120), nullable=False)
    isbn = db.Column(db.String(30), unique=True, nullable=False)
    total_copies = db.Column(db.Integer, nullable=False, default=1)
    available_copies = db.Column(db.Integer, nullable=False, default=1)

    transactions = db.relationship('Transaction', backref='book', lazy=True)

class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    issue_date = db.Column(db.Date, nullable=False, default=date.today)
    due_date = db.Column(db.Date, nullable=False)
    return_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='ISSUED')
    fine_amount = db.Column(db.Float, nullable=False, default=0.0)

    @property
    def is_overdue(self):
        if self.status == 'ISSUED':
            return date.today() > self.due_date
        return False

    @property
    def days_overdue(self):
        if self.status == 'ISSUED':
            if date.today() > self.due_date:
                return (date.today() - self.due_date).days
        elif self.return_date and self.return_date > self.due_date:
            return (self.return_date - self.due_date).days
        return 0

    @property
    def calculated_fine(self):
        return float(self.days_overdue * 5)

class AlertsLog(db.Model):
    __tablename__ = 'alerts_log'

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    channel = db.Column(db.String(50), nullable=False)
