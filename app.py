import os
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from apscheduler.schedulers.background import BackgroundScheduler

load_dotenv()

from models import db, Member, Book, Transaction, AlertsLog
from services.sns_service import SNSService
from services.reminder_service import ReminderService

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'library-secret-key-38294719')

database_url = os.environ.get('DATABASE_URL', '').strip()
if not database_url:
    base_dir = os.path.abspath(os.path.dirname(__file__))
    database_url = f"sqlite:///{os.path.join(base_dir, 'library.db')}"
elif database_url.startswith('mysql://'):
    database_url = database_url.replace('mysql://', 'mysql+pymysql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

sns_service = SNSService()
reminder_service = ReminderService(sns_service)

scheduler = BackgroundScheduler(daemon=True)

def scheduled_reminder_job():
    with app.app_context():
        reminder_service.process_overdue_reminders()

if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    try:
        scheduler.add_job(
            func=scheduled_reminder_job,
            trigger='cron',
            hour=9,
            minute=0,
            id='daily_overdue_reminders',
            replace_existing=True
        )
        scheduler.start()
    except Exception as exc:
        print(f"Scheduler initialization failed: {exc}", flush=True)

def seed_demo_data():
    if Book.query.first() or Member.query.first():
        return

    today = date.today()

    demo_books = [
        Book(title="Clean Code: A Handbook of Agile Software Craftsmanship", author="Robert C. Martin", isbn="978-0132350884", total_copies=4, available_copies=3),
        Book(title="The Pragmatic Programmer: Your Journey To Mastery", author="David Thomas, Andrew Hunt", isbn="978-0135957059", total_copies=3, available_copies=2),
        Book(title="Design Patterns: Elements of Reusable Object-Oriented Software", author="Erich Gamma et al.", isbn="978-0201633610", total_copies=2, available_copies=2),
        Book(title="Introduction to Algorithms", author="Thomas H. Cormen et al.", isbn="978-0262033848", total_copies=5, available_copies=4),
        Book(title="Designing Data-Intensive Applications", author="Martin Kleppmann", isbn="978-1449373320", total_copies=4, available_copies=3),
        Book(title="You Don't Know JS: Scope & Closures", author="Kyle Simpson", isbn="978-1449335588", total_copies=3, available_copies=3),
        Book(title="Continuous Delivery", author="Jez Humble, David Farley", isbn="978-0321601919", total_copies=2, available_copies=2),
        Book(title="Site Reliability Engineering", author="Betsy Beyer et al.", isbn="978-1491929124", total_copies=3, available_copies=3),
        Book(title="Python Crash Course", author="Eric Matthes", isbn="978-1593279288", total_copies=5, available_copies=4),
        Book(title="Fluent Python", author="Luciano Ramalho", isbn="978-1491946008", total_copies=3, available_copies=3),
        Book(title="Database System Concepts", author="Abraham Silberschatz et al.", isbn="978-0073523323", total_copies=4, available_copies=4),
        Book(title="Computer Networking: A Top-Down Approach", author="James Kurose, Keith Ross", isbn="978-0133594140", total_copies=3, available_copies=3)
    ]
    for b in demo_books:
        db.session.add(b)

    demo_members = [
        Member(name="Aarav Sharma", email="aarav.sharma@example.com", phone="+91 98765 43210", joined_at=datetime.utcnow() - timedelta(days=90)),
        Member(name="Diya Patel", email="diya.patel@example.com", phone="+91 98123 45678", joined_at=datetime.utcnow() - timedelta(days=75)),
        Member(name="Rohan Verma", email="rohan.verma@example.com", phone="+91 97234 56789", joined_at=datetime.utcnow() - timedelta(days=60)),
        Member(name="Ananya Iyer", email="ananya.iyer@example.com", phone="+91 96345 67890", joined_at=datetime.utcnow() - timedelta(days=45)),
        Member(name="Vikram Malhotra", email="vikram.m@example.com", phone="+91 95456 78901", joined_at=datetime.utcnow() - timedelta(days=30)),
        Member(name="Sneha Kulkarni", email="sneha.k@example.com", phone="+91 94567 89012", joined_at=datetime.utcnow() - timedelta(days=15))
    ]
    for m in demo_members:
        db.session.add(m)

    db.session.flush()

    demo_transactions = [
        Transaction(book_id=demo_books[0].id, member_id=demo_members[0].id, issue_date=today - timedelta(days=28), due_date=today - timedelta(days=14), status="ISSUED", fine_amount=0.0),
        Transaction(book_id=demo_books[1].id, member_id=demo_members[1].id, issue_date=today - timedelta(days=24), due_date=today - timedelta(days=10), status="ISSUED", fine_amount=0.0),
        Transaction(book_id=demo_books[4].id, member_id=demo_members[2].id, issue_date=today - timedelta(days=20), due_date=today - timedelta(days=6), status="ISSUED", fine_amount=0.0),
        Transaction(book_id=demo_books[2].id, member_id=demo_members[3].id, issue_date=today - timedelta(days=35), due_date=today - timedelta(days=21), return_date=today - timedelta(days=15), status="RETURNED", fine_amount=30.0),
        Transaction(book_id=demo_books[3].id, member_id=demo_members[4].id, issue_date=today - timedelta(days=4), due_date=today + timedelta(days=10), status="ISSUED", fine_amount=0.0),
        Transaction(book_id=demo_books[8].id, member_id=demo_members[5].id, issue_date=today - timedelta(days=2), due_date=today + timedelta(days=12), status="ISSUED", fine_amount=0.0)
    ]
    for t in demo_transactions:
        db.session.add(t)

    initial_alerts = [
        AlertsLog(
            member_id=demo_members[0].id,
            message=f"Dear {demo_members[0].name}, you have overdue library book(s): '{demo_books[0].title}' (14 days overdue, fine: Rs 70). Total accrued fine is Rs 70 (calculated at Rs 5/day). Please return them immediately to City Central Library.",
            sent_at=datetime.utcnow() - timedelta(days=1),
            channel="SNS (simulated)"
        ),
        AlertsLog(
            member_id=demo_members[1].id,
            message=f"Dear {demo_members[1].name}, you have overdue library book(s): '{demo_books[1].title}' (10 days overdue, fine: Rs 50). Total accrued fine is Rs 50 (calculated at Rs 5/day). Please return them immediately to City Central Library.",
            sent_at=datetime.utcnow() - timedelta(days=1),
            channel="SNS (simulated)"
        )
    ]
    for a in initial_alerts:
        db.session.add(a)

    db.session.commit()

with app.app_context():
    db.create_all()
    seed_demo_data()

@app.context_processor
def inject_global_data():
    today = date.today()
    overdue_count = Transaction.query.filter(
        Transaction.status == 'ISSUED',
        Transaction.due_date < today
    ).count()
    db_type = 'mysql' if 'mysql' in app.config['SQLALCHEMY_DATABASE_URI'] else 'sqlite'
    sns_mode = 'real' if sns_service.is_configured() else 'simulated'
    return {
        'global_overdue_count': overdue_count,
        'global_db_type': db_type,
        'global_sns_mode': sns_mode,
        'current_year': datetime.utcnow().year,
        'today': today
    }

@app.route('/health', methods=['GET'])
def health():
    db_type = 'mysql' if 'mysql' in app.config['SQLALCHEMY_DATABASE_URI'] else 'sqlite'
    sns_type = 'real' if sns_service.is_configured() else 'simulated'
    return jsonify({
        'status': 'ok',
        'database': db_type,
        'sns': sns_type
    }), 200

@app.route('/')
def dashboard():
    today = date.today()
    total_books = Book.query.count()
    total_copies_sum = db.session.query(db.func.sum(Book.total_copies)).scalar() or 0
    total_members = Member.query.count()
    issued_count = Transaction.query.filter_by(status='ISSUED').count()
    overdue_count = Transaction.query.filter(
        Transaction.status == 'ISSUED',
        Transaction.due_date < today
    ).count()
    returned_count = Transaction.query.filter_by(status='RETURNED').count()

    returned_fines = db.session.query(db.func.sum(Transaction.fine_amount)).filter_by(status='RETURNED').scalar() or 0.0

    overdue_txs = Transaction.query.filter(
        Transaction.status == 'ISSUED',
        Transaction.due_date < today
    ).all()
    outstanding_fines = sum((today - tx.due_date).days * 5 for tx in overdue_txs)
    total_fines = returned_fines + outstanding_fines

    recent_transactions = Transaction.query.order_by(Transaction.id.desc()).limit(5).all()

    return render_template(
        'dashboard.html',
        total_books=total_books,
        total_copies=total_copies_sum,
        total_members=total_members,
        issued_count=issued_count,
        overdue_count=overdue_count,
        returned_count=returned_count,
        total_fines=total_fines,
        recent_transactions=recent_transactions
    )

@app.route('/books')
def books_list():
    query_str = request.args.get('q', '').strip()
    if query_str:
        search_filter = f"%{query_str}%"
        books = Book.query.filter(
            (Book.title.ilike(search_filter)) |
            (Book.author.ilike(search_filter)) |
            (Book.isbn.ilike(search_filter))
        ).order_by(Book.title.asc()).all()
    else:
        books = Book.query.order_by(Book.title.asc()).all()
    return render_template('books/index.html', books=books, search_query=query_str)

@app.route('/books/add', methods=['GET', 'POST'])
def book_add():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        author = request.form.get('author', '').strip()
        isbn = request.form.get('isbn', '').strip()
        copies_raw = request.form.get('total_copies', '').strip()

        errors = []
        if not title:
            errors.append('Book title is required.')
        if not author:
            errors.append('Author name is required.')
        if not isbn:
            errors.append('ISBN is required.')
        elif Book.query.filter_by(isbn=isbn).first():
            errors.append('A book with this ISBN already exists.')

        try:
            total_copies = int(copies_raw)
            if total_copies < 1:
                errors.append('Total copies must be at least 1.')
        except ValueError:
            errors.append('Total copies must be a valid number.')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('books/form.html', book=None, form_data=request.form)

        new_book = Book(
            title=title,
            author=author,
            isbn=isbn,
            total_copies=total_copies,
            available_copies=total_copies
        )
        db.session.add(new_book)
        db.session.commit()
        flash(f"Book '{title}' added successfully.", 'success')
        return redirect(url_for('books_list'))

    return render_template('books/form.html', book=None, form_data={})

@app.route('/books/edit/<int:book_id>', methods=['GET', 'POST'])
def book_edit(book_id):
    book = db.get_or_404(Book, book_id)
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        author = request.form.get('author', '').strip()
        isbn = request.form.get('isbn', '').strip()
        copies_raw = request.form.get('total_copies', '').strip()

        errors = []
        if not title:
            errors.append('Book title is required.')
        if not author:
            errors.append('Author name is required.')
        if not isbn:
            errors.append('ISBN is required.')
        else:
            existing_isbn = Book.query.filter(Book.isbn == isbn, Book.id != book.id).first()
            if existing_isbn:
                errors.append('Another book with this ISBN already exists.')

        try:
            new_total = int(copies_raw)
            active_issues = Transaction.query.filter_by(book_id=book.id, status='ISSUED').count()
            if new_total < active_issues:
                errors.append(f'Total copies cannot be less than currently issued copies ({active_issues}).')
        except ValueError:
            errors.append('Total copies must be a valid number.')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('books/form.html', book=book, form_data=request.form)

        active_issues = Transaction.query.filter_by(book_id=book.id, status='ISSUED').count()
        book.title = title
        book.author = author
        book.isbn = isbn
        book.total_copies = new_total
        book.available_copies = new_total - active_issues

        db.session.commit()
        flash(f"Book '{title}' updated successfully.", 'success')
        return redirect(url_for('books_list'))

    return render_template('books/form.html', book=book, form_data={})

@app.route('/books/delete/<int:book_id>', methods=['POST'])
def book_delete(book_id):
    book = db.get_or_404(Book, book_id)
    active_issues = Transaction.query.filter_by(book_id=book.id, status='ISSUED').count()
    if active_issues > 0:
        flash(f"Cannot delete book '{book.title}' because it has {active_issues} active issued copy/copies. Please return all copies first.", 'danger')
        return redirect(url_for('books_list'))

    Transaction.query.filter_by(book_id=book.id).delete()
    title = book.title
    db.session.delete(book)
    db.session.commit()
    flash(f"Book '{title}' was deleted successfully.", 'success')
    return redirect(url_for('books_list'))

@app.route('/members')
def members_list():
    query_str = request.args.get('q', '').strip()
    if query_str:
        search_filter = f"%{query_str}%"
        members = Member.query.filter(
            (Member.name.ilike(search_filter)) |
            (Member.email.ilike(search_filter)) |
            (Member.phone.ilike(search_filter))
        ).order_by(Member.name.asc()).all()
    else:
        members = Member.query.order_by(Member.name.asc()).all()
    return render_template('members/index.html', members=members, search_query=query_str)

@app.route('/members/add', methods=['GET', 'POST'])
def member_add():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()

        errors = []
        if not name:
            errors.append('Member name is required.')
        if not email or '@' not in email:
            errors.append('A valid email address is required.')
        if not phone:
            errors.append('Phone number is required.')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('members/form.html', member=None, form_data=request.form)

        new_member = Member(name=name, email=email, phone=phone)
        db.session.add(new_member)
        db.session.commit()
        flash(f"Member '{name}' registered successfully.", 'success')
        return redirect(url_for('members_list'))

    return render_template('members/form.html', member=None, form_data={})

@app.route('/members/edit/<int:member_id>', methods=['GET', 'POST'])
def member_edit(member_id):
    member = db.get_or_404(Member, member_id)
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()

        errors = []
        if not name:
            errors.append('Member name is required.')
        if not email or '@' not in email:
            errors.append('A valid email address is required.')
        if not phone:
            errors.append('Phone number is required.')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('members/form.html', member=member, form_data=request.form)

        member.name = name
        member.email = email
        member.phone = phone
        db.session.commit()
        flash(f"Member '{name}' details updated successfully.", 'success')
        return redirect(url_for('members_list'))

    return render_template('members/form.html', member=member, form_data={})

@app.route('/members/delete/<int:member_id>', methods=['POST'])
def member_delete(member_id):
    member = db.get_or_404(Member, member_id)
    active_issues = Transaction.query.filter_by(member_id=member.id, status='ISSUED').count()
    if active_issues > 0:
        flash(f"Cannot delete member '{member.name}' because they currently have {active_issues} unreturned book(s).", 'danger')
        return redirect(url_for('members_list'))

    AlertsLog.query.filter_by(member_id=member.id).delete()
    Transaction.query.filter_by(member_id=member.id).delete()
    name = member.name
    db.session.delete(member)
    db.session.commit()
    flash(f"Member '{name}' was deleted successfully.", 'success')
    return redirect(url_for('members_list'))

@app.route('/transactions')
def transactions_list():
    status_filter = request.args.get('status', '').strip().upper()
    query = Transaction.query
    if status_filter in ['ISSUED', 'RETURNED']:
        query = query.filter_by(status=status_filter)
    transactions = query.order_by(Transaction.id.desc()).all()
    return render_template('transactions/index.html', transactions=transactions, current_filter=status_filter)

@app.route('/transactions/issue', methods=['GET', 'POST'])
def transaction_issue():
    if request.method == 'POST':
        member_id = request.form.get('member_id')
        book_id = request.form.get('book_id')
        due_date_str = request.form.get('due_date', '').strip()

        errors = []
        member = db.session.get(Member, int(member_id)) if (member_id and str(member_id).isdigit()) else None
        book = db.session.get(Book, int(book_id)) if (book_id and str(book_id).isdigit()) else None

        if not member:
            errors.append('Please select a valid member.')
        if not book:
            errors.append('Please select a valid book.')
        elif book.available_copies <= 0:
            errors.append(f"No copies available for '{book.title}'.")

        due_date = None
        if not due_date_str:
            errors.append('Please provide a due date.')
        else:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                if due_date <= date.today():
                    errors.append('Due date must be in the future.')
            except ValueError:
                errors.append('Invalid due date format. Please use YYYY-MM-DD.')

        if errors:
            for error in errors:
                flash(error, 'danger')
            members = Member.query.order_by(Member.name.asc()).all()
            available_books = Book.query.filter(Book.available_copies > 0).order_by(Book.title.asc()).all()
            default_due = (date.today() + timedelta(days=14)).isoformat()
            return render_template(
                'transactions/issue.html',
                members=members,
                books=available_books,
                default_due=default_due,
                form_data=request.form
            )

        book.available_copies -= 1
        new_tx = Transaction(
            book_id=book.id,
            member_id=member.id,
            issue_date=date.today(),
            due_date=due_date,
            status='ISSUED',
            fine_amount=0.0
        )
        db.session.add(new_tx)
        db.session.commit()
        flash(f"Book '{book.title}' successfully issued to {member.name}. Due on {due_date.strftime('%b %d, %Y')}.", 'success')
        return redirect(url_for('transactions_list'))

    members = Member.query.order_by(Member.name.asc()).all()
    available_books = Book.query.filter(Book.available_copies > 0).order_by(Book.title.asc()).all()
    default_due = (date.today() + timedelta(days=14)).isoformat()
    return render_template('transactions/issue.html', members=members, books=available_books, default_due=default_due, form_data={})

@app.route('/transactions/return/<int:tx_id>', methods=['POST'])
def transaction_return(tx_id):
    tx = db.get_or_404(Transaction, tx_id)
    if tx.status == 'RETURNED':
        flash('This book has already been returned.', 'warning')
        return redirect(request.referrer or url_for('transactions_list'))

    today = date.today()
    tx.return_date = today
    tx.status = 'RETURNED'

    fine = 0.0
    if today > tx.due_date:
        overdue_days = (today - tx.due_date).days
        fine = float(overdue_days * 5)
    tx.fine_amount = fine

    tx.book.available_copies += 1
    db.session.commit()

    if fine > 0:
        flash(f"Book '{tx.book.title}' returned late by {overdue_days} day(s). Fine charged: Rs {int(fine)}.", 'warning')
    else:
        flash(f"Book '{tx.book.title}' returned on time successfully.", 'success')

    return redirect(request.referrer or url_for('transactions_list'))

@app.route('/transactions/overdue')
def transactions_overdue():
    today = date.today()
    overdue_txs = Transaction.query.filter(
        Transaction.status == 'ISSUED',
        Transaction.due_date < today
    ).order_by(Transaction.due_date.asc()).all()

    total_overdue_fines = sum(tx.calculated_fine for tx in overdue_txs)
    return render_template(
        'transactions/overdue.html',
        transactions=overdue_txs,
        total_overdue_fines=total_overdue_fines
    )

@app.route('/admin/send-reminders', methods=['POST'])
def admin_send_reminders():
    result = reminder_service.process_overdue_reminders()
    count = result.get('sent_count', 0)
    if count > 0:
        flash(f"Dispatched {count} overdue reminder notification(s) via {result['alerts'][0].channel}.", 'success')
    else:
        flash("No overdue members found to send reminders to.", 'info')
    return redirect(request.referrer or url_for('transactions_overdue'))

@app.route('/alerts')
def alerts_list():
    alerts = AlertsLog.query.order_by(AlertsLog.sent_at.desc()).all()
    return render_template('alerts/index.html', alerts=alerts)

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
