# Library Book Lending System (LibLend Pro)

A complete, production-ready Library Book Lending and Management Web Application built with Python 3.11, Flask, SQLAlchemy, Amazon SNS (with automatic simulation fallback), and APScheduler.

LibLend Pro streamlines library operations including catalog inventory tracking, membership records, book issuing and returns with automated fine calculation (Rs 5/overdue day), an overdue management console, and automated overdue alert dispatching.

---

## Features

- **Executive Dashboard**: Live operational metrics with stat cards (total books and copies, active members, currently issued items, overdue count, and total fines), an interactive Chart.js doughnut chart, and a quick-action recent transactions stream.
- **Book Catalog Management**: Full CRUD support (Add, Edit, Delete, View) with real-time search across titles, authors, and ISBNs. Prevents accidental deletion of books with active borrowings.
- **Member Directory**: Full member CRUD with search by name, email, or phone. Blocks member deletion while unreturned books are linked.
- **Lending & Issue Workflows**: Intuitive book checkout system. Automatically tracks inventory decrement upon issuance and blocks checkout when available stock reaches zero. Default 14-day loan duration.
- **Return Processing & Fine Calculation**: Instant check-in workflow. Restores stock count and computes fine penalties at Rs 5 per day past the due date.
- **Overdue Management Console**: Dedicated dashboard listing all active overdue loans, accrued penalty fines, borrower contact information, and a single-click "Send Reminders Now" trigger.
- **Automated Alerts & Dual-Mode SNS**: Background cron job powered by APScheduler executing daily at 09:00 to alert overdue borrowers. Dispatches notifications to Amazon SNS if configured, or automatically falls back to simulated SNS mode locally without requiring AWS credentials.
- **Notification Audit Log**: Immutable record of all dispatched alerts, displaying recipient member, alert message, timestamp, and delivery channel (`SNS` or `SNS (simulated)`).
- **Health & Diagnostic Endpoint**: `GET /health` returns JSON reporting database driver and SNS operational state.
- **Responsive Modern UI**: Bootstrap 5 + Bootstrap Icons with responsive layout and distinct status badges (blue for issued, red for overdue, green for returned).

---

## Architecture Overview

```
                      +-----------------------------------+
                      |         Web Client Browser        |
                      +-----------------+-----------------+
                                        | HTTP (Port 80/5000)
                                        v
+---------------------------------------------------------------------------------+
| AWS EC2 / Local Host Server                                                     |
|                                                                                 |
|   +-----------------------+           +-------------------------------------+   |
|   |  Gunicorn WSGI / App  |<--------->|  APScheduler (Daily Cron at 09:00)  |   |
|   +-----------+-----------+           +------------------+------------------+   |
|               |                                          |                      |
|               v                                          v                      |
|   +-----------------------+           +-------------------------------------+   |
|   |  Flask Core Engine    |<--------->|  ReminderService & SNSService       |   |
|   +-----------+-----------+           +------------------+------------------+   |
+---------------|------------------------------------------|----------------------+
                |                                          |
                | SQLAlchemy ORM                           | boto3 SNS Publish
                v                                          v
+-------------------------------+         +---------------------------------------+
| Database Storage Layer        |         | Amazon SNS / Notification Service     |
| - Local: SQLite (library.db)  |         | - Real AWS: SNS Topic -> Email Sub    |
| - Prod: AWS RDS MySQL (8.0)   |         | - Local: In-Memory / Simulated Logger |
+-------------------------------+         +---------------------------------------+
```

---

## Entity-Relationship (ER) Diagram

```mermaid
erDiagram
    MEMBERS ||--o{ TRANSACTIONS : "borrows"
    MEMBERS ||--o{ ALERTS_LOG : "receives"
    BOOKS ||--o{ TRANSACTIONS : "issued in"

    MEMBERS {
        int id PK
        string name
        string email
        string phone
        datetime joined_at
    }

    BOOKS {
        int id PK
        string title
        string author
        string isbn UK
        int total_copies
        int available_copies
    }

    TRANSACTIONS {
        int id PK
        int book_id FK
        int member_id FK
        date issue_date
        date due_date
        date return_date
        string status
        float fine_amount
    }

    ALERTS_LOG {
        int id PK
        int member_id FK
        text message
        datetime sent_at
        string channel
    }
```

---

## Route & API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Operational dashboard with live metrics, Chart.js breakdown, and recent transactions |
| `GET` | `/health` | Health check endpoint returning `{"status":"ok","database":"...","sns":"..."}` |
| `GET` | `/books` | Books catalog with real-time search query parameter `?q=` |
| `GET`, `POST` | `/books/add` | Add new book to library catalog |
| `GET`, `POST` | `/books/edit/<id>` | Update existing book details and total inventory |
| `POST` | `/books/delete/<id>` | Delete book (blocked if active borrowings exist) |
| `GET` | `/members` | Member directory with search query parameter `?q=` |
| `GET`, `POST` | `/members/add` | Register new library member |
| `GET`, `POST` | `/members/edit/<id>` | Update member contact information |
| `POST` | `/members/delete/<id>` | Delete member (blocked if unreturned books exist) |
| `GET` | `/transactions` | Transaction history with status filter `?status=ISSUED\|RETURNED` |
| `GET`, `POST` | `/transactions/issue` | Issue available book to member (defaults to 14 days) |
| `POST` | `/transactions/return/<id>` | Return issued book, restore inventory, and calculate overdue fine |
| `GET` | `/transactions/overdue` | Overdue loans list with days overdue and fine estimates |
| `POST` | `/admin/send-reminders` | Trigger overdue reminder notifications immediately |
| `GET` | `/alerts` | Notification audit log displaying channel and timestamps |

---

## Environment Variables (.env)

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | No | `sqlite:///library.db` | SQLAlchemy connection string (e.g. `mysql://user:pass@host:3306/db`) |
| `SNS_TOPIC_ARN` | No | *Empty* | Amazon SNS Topic ARN. When blank or invalid, system runs in simulated mode |
| `AWS_DEFAULT_REGION` | No | `us-east-1` | AWS region hosting SNS topic |
| `SECRET_KEY` | No | Built-in fallback | Flask session cryptographic signing secret |
| `PORT` | No | `5000` | Port for local execution |

---

## Local Setup & Execution

### Prerequisites
- Python 3.10+ or Python 3.11
- pip

### 1. Clone & Enter Project Directory
```bash
git clone <repository-url>
cd <project-folder>
```

### 2. Create Virtual Environment
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment (Optional)
```bash
cp .env.example .env
```
*(Leave values blank to run fully locally with SQLite and simulated SNS).*

### 5. Launch the Application
```bash
python app.py
```
Open your browser and navigate to:
**`http://localhost:5000`**

On initial launch, the system automatically creates the database schema and seeds demo data (12 books, 6 members, 6 transactions, and sample alerts).

---

## AWS Deployment Guide

### Option 1: Automated Infrastructure via CloudFormation
1. Open the **AWS CloudFormation Console**.
2. Create a new stack using `cloudformation.yaml`.
3. Fill in the parameters:
   - `OperatorEmail`: Email address to receive overdue library notifications.
   - `DBMasterUsername`: RDS MySQL master username.
   - `DBMasterPassword`: RDS MySQL master password.
   - `KeyName`: Your existing EC2 KeyPair name.
4. Deploy the stack. CloudFormation automatically provisions:
   - AWS RDS MySQL 8.0 instance (free tier `db.t3.micro`).
   - Amazon SNS Topic with Email Subscription.
   - IAM Role with `sns:Publish` privileges attached to an EC2 Instance Profile.
   - EC2 Instance with Security Groups for HTTP (Port 80) and SSH (Port 22).
5. Obtain the stack outputs:
   - `RDSEndpoint`
   - `SNSTopicARN`
   - `EC2PublicIP`

### Option 2: Server Provisioning via `deploy_ec2.sh`
1. SSH into the deployed EC2 instance:
   ```bash
   ssh -i <your-key.pem> ec2-user@<EC2PublicIP>
   ```
2. Clone this repository or copy the project files to `/opt/library-system`.
3. Create `/opt/library-system/.env` with your RDS and SNS credentials:
   ```env
   DATABASE_URL=mysql://libraryadmin:<DBMasterPassword>@<RDSEndpoint>:3306/librarydb
   SNS_TOPIC_ARN=<SNSTopicARN>
   AWS_DEFAULT_REGION=us-east-1
   SECRET_KEY=super-secure-production-secret-key
   ```
4. Run the automated deployment script with administrative permissions:
   ```bash
   sudo chmod +x deploy_ec2.sh
   sudo ./deploy_ec2.sh
   ```
   The script installs all required packages, creates a virtual environment, configures a systemd unit file (`/etc/systemd/system/library.service`), and starts Gunicorn binding to port 80.

---

## Testing & Verification

A comprehensive automated test run verifies every route, transaction state transition, inventory update, and notification path.

To execute tests:
```bash
python -m unittest -v
```
All tests execute locally with zero external network or AWS dependencies.
