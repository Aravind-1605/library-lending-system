import unittest
import uuid
from datetime import date, timedelta
from app import app, db
from models import Book, Member, Transaction, AlertsLog

class LibrarySystemTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

    def test_health_check(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data.get('status'), 'ok')
        self.assertIn(data.get('database'), ['sqlite', 'mysql'])
        self.assertEqual(data.get('sns'), 'simulated')

    def test_dashboard_route(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('Operational Dashboard', html)
        self.assertIn('statusChart', html)
        self.assertIn('Recent Transactions', html)

    def test_books_list_and_search(self):
        response = self.client.get('/books')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('Clean Code', html)

        search_res = self.client.get('/books?q=Pragmatic')
        self.assertEqual(search_res.status_code, 200)
        search_html = search_res.get_data(as_text=True)
        self.assertIn('The Pragmatic Programmer', search_html)
        self.assertNotIn('Continuous Delivery', search_html)

    def test_book_crud_lifecycle(self):
        unique_isbn = f"978-TDD-{uuid.uuid4().hex[:6]}"
        add_res = self.client.post('/books/add', data={
            'title': 'Test Driven Development',
            'author': 'Kent Beck',
            'isbn': unique_isbn,
            'total_copies': '3'
        }, follow_redirects=True)
        self.assertEqual(add_res.status_code, 200)
        html = add_res.get_data(as_text=True)
        self.assertIn('Test Driven Development', html)

        with app.app_context():
            created_book = Book.query.filter_by(isbn=unique_isbn).first()
            self.assertIsNotNone(created_book)
            self.assertEqual(created_book.available_copies, 3)
            book_id = created_book.id

        edit_res = self.client.post(f'/books/edit/{book_id}', data={
            'title': 'Test Driven Development by Example',
            'author': 'Kent Beck',
            'isbn': unique_isbn,
            'total_copies': '4'
        }, follow_redirects=True)
        self.assertEqual(edit_res.status_code, 200)
        self.assertIn('Test Driven Development by Example', edit_res.get_data(as_text=True))

        del_res = self.client.post(f'/books/delete/{book_id}', follow_redirects=True)
        self.assertEqual(del_res.status_code, 200)
        with app.app_context():
            deleted = db.session.get(Book, book_id)
            self.assertIsNone(deleted)

    def test_book_prevent_delete_with_active_issue(self):
        with app.app_context():
            active_tx = Transaction.query.filter_by(status='ISSUED').first()
            self.assertIsNotNone(active_tx)
            book_id = active_tx.book_id

        del_res = self.client.post(f'/books/delete/{book_id}', follow_redirects=True)
        self.assertEqual(del_res.status_code, 200)
        html = del_res.get_data(as_text=True)
        self.assertIn('Cannot delete book', html)

        with app.app_context():
            book = db.session.get(Book, book_id)
            self.assertIsNotNone(book)

    def test_member_crud_and_prevent_delete(self):
        unique_email = f"rahul.{uuid.uuid4().hex[:6]}@example.com"
        add_res = self.client.post('/members/add', data={
            'name': 'Rahul Dravid',
            'email': unique_email,
            'phone': '+91 99999 11111'
        }, follow_redirects=True)
        self.assertEqual(add_res.status_code, 200)
        html = add_res.get_data(as_text=True)
        self.assertIn('Rahul Dravid', html)

        with app.app_context():
            member = Member.query.filter_by(email=unique_email).first()
            self.assertIsNotNone(member)
            member_id = member.id

        edit_res = self.client.post(f'/members/edit/{member_id}', data={
            'name': 'Rahul S. Dravid',
            'email': unique_email,
            'phone': '+91 99999 22222'
        }, follow_redirects=True)
        self.assertEqual(edit_res.status_code, 200)
        self.assertIn('Rahul S. Dravid', edit_res.get_data(as_text=True))

        del_res = self.client.post(f'/members/delete/{member_id}', follow_redirects=True)
        self.assertEqual(del_res.status_code, 200)
        with app.app_context():
            self.assertIsNone(db.session.get(Member, member_id))

        with app.app_context():
            active_tx = Transaction.query.filter_by(status='ISSUED').first()
            active_member_id = active_tx.member_id

        del_active_res = self.client.post(f'/members/delete/{active_member_id}', follow_redirects=True)
        self.assertEqual(del_active_res.status_code, 200)
        self.assertIn('Cannot delete member', del_active_res.get_data(as_text=True))

    def test_issue_and_return_book_lifecycle(self):
        temp_tag = uuid.uuid4().hex[:6]
        with app.app_context():
            member = Member(name=f'Borrower {temp_tag}', email=f'borrower_{temp_tag}@test.com', phone='+91 91234 56780')
            book = Book(title=f'Temp Book {temp_tag}', author='Temp Author', isbn=f'978-TMP-{temp_tag}', total_copies=2, available_copies=2)
            db.session.add(member)
            db.session.add(book)
            db.session.commit()
            m_id = member.id
            b_id = book.id

        due_date_str = (date.today() + timedelta(days=14)).isoformat()
        issue_res = self.client.post('/transactions/issue', data={
            'member_id': str(m_id),
            'book_id': str(b_id),
            'due_date': due_date_str
        }, follow_redirects=True)
        self.assertEqual(issue_res.status_code, 200)

        with app.app_context():
            refreshed_book = db.session.get(Book, b_id)
            self.assertEqual(refreshed_book.available_copies, 1)
            issued_tx = Transaction.query.filter_by(book_id=b_id, member_id=m_id, status='ISSUED').first()
            self.assertIsNotNone(issued_tx)
            tx_id = issued_tx.id

        return_res = self.client.post(f'/transactions/return/{tx_id}', follow_redirects=True)
        self.assertEqual(return_res.status_code, 200)

        with app.app_context():
            refreshed_book = db.session.get(Book, b_id)
            self.assertEqual(refreshed_book.available_copies, 2)
            returned_tx = db.session.get(Transaction, tx_id)
            self.assertEqual(returned_tx.status, 'RETURNED')
            self.assertEqual(returned_tx.fine_amount, 0.0)

    def test_overdue_and_fine_calculation(self):
        late_tag = uuid.uuid4().hex[:6]
        with app.app_context():
            member = Member(name=f'Late Borrower {late_tag}', email=f'late_{late_tag}@test.com', phone='+91 98888 77777')
            book = Book(title=f'Late Book {late_tag}', author='Late Author', isbn=f'978-LATE-{late_tag}', total_copies=1, available_copies=0)
            db.session.add(member)
            db.session.add(book)
            db.session.flush()

            overdue_tx = Transaction(
                book_id=book.id,
                member_id=member.id,
                issue_date=date.today() - timedelta(days=20),
                due_date=date.today() - timedelta(days=5),
                status='ISSUED',
                fine_amount=0.0
            )
            db.session.add(overdue_tx)
            db.session.commit()
            tx_id = overdue_tx.id

        overdue_page = self.client.get('/transactions/overdue')
        self.assertEqual(overdue_page.status_code, 200)
        html = overdue_page.get_data(as_text=True)
        self.assertIn(f'Late Book {late_tag}', html)
        self.assertIn('5 days', html)
        self.assertIn('₹25', html)

        return_res = self.client.post(f'/transactions/return/{tx_id}', follow_redirects=True)
        self.assertEqual(return_res.status_code, 200)
        self.assertIn('Fine charged: Rs 25', return_res.get_data(as_text=True))

        with app.app_context():
            final_tx = db.session.get(Transaction, tx_id)
            self.assertEqual(final_tx.status, 'RETURNED')
            self.assertEqual(final_tx.fine_amount, 25.0)

    def test_admin_send_reminders(self):
        res = self.client.post('/admin/send-reminders', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('Dispatched', html)

        alerts_res = self.client.get('/alerts')
        self.assertEqual(alerts_res.status_code, 200)
        alerts_html = alerts_res.get_data(as_text=True)
        self.assertIn('SNS (simulated)', alerts_html)

    def test_transaction_history_filter(self):
        all_res = self.client.get('/transactions')
        self.assertEqual(all_res.status_code, 200)

        issued_res = self.client.get('/transactions?status=ISSUED')
        self.assertEqual(issued_res.status_code, 200)

        returned_res = self.client.get('/transactions?status=RETURNED')
        self.assertEqual(returned_res.status_code, 200)

    def test_custom_404_error_page(self):
        res = self.client.get('/a-page-that-definitely-does-not-exist-1234')
        self.assertEqual(res.status_code, 404)
        html = res.get_data(as_text=True)
        self.assertIn('Resource Not Found', html)
        self.assertNotIn('Traceback', html)

if __name__ == '__main__':
    unittest.main()
