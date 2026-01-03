Why you used Mongodb instead of sql dbs?

🔹 Interview-style Answer

> “Actually, I’ve worked with both SQL and NoSQL, and the choice of MongoDB in that project was purely based on the use case – not a generic preference.”



Then continue:

> “In Option ARO, we were dealing with a lot of semi-structured and fast-changing data – things like strategy logs, live option chain snapshots, and analytics outputs. The schema was evolving quickly, and we needed:

Flexible schema for different strategies

High write throughput for live data

Easy horizontal scaling


MongoDB fit that really well. I could store JSON-like documents directly, add new fields per strategy without schema migrations, and write data very quickly as the WebSocket streams were coming in.

At the same time, I’m very comfortable with SQL – in fact, for more structured, transactional data like portfolios and mock trades in Market Masters or bookings in other projects, we used relational DBs like MySQL. So for me, it’s not ‘Mongo vs SQL’, it’s ‘which tool fits the data model and access pattern better’.”



You can end with:

> “If I need strong transactions, reporting, and strict relationships → I’ll pick SQL.
If I need flexible schema, high-volume logging, or analytics-style documents → MongoDB is often a better fit.”




---

🔹 Tiny Code Contrast (If They Dig Deeper)

MongoDB (PyMongo, storing a strategy snapshot):

from pymongo import MongoClient
client = MongoClient("mongodb://localhost:27017")
db = client["option_aro"]

db.strategy_snapshots.insert_one({
    "user_id": 123,
    "strategy_name": "BankNifty_PCR",
    "atm_price": 49520,
    "pcr": 1.23,
    "iv": 14.8,
    "timestamp": "2025-12-04T10:15:00Z",
    "extra_metrics": { "max_pain": 49500, "oi_change": 12000 }
})

No schema migration needed if tomorrow you add a new metric.

Same in SQL (conceptually):

CREATE TABLE strategy_snapshots (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    strategy_name VARCHAR(100),
    atm_price DECIMAL(10,2),
    pcr DECIMAL(5,2),
    iv DECIMAL(5,2),
    timestamp DATETIME
    -- adding new columns later needs ALTER TABLE
);

You don’t need to show the code unless they’re very technical, but having this mental model helps you sound very clear and confident.


---

If you want, next I can give you a one-line follow-up you can use when they ask:

> “So in which cases would you not use MongoDB?”

Here’s the exact interview-ready answer you should give — concise and technical, based on real backend practice:


---

✅ Interview Answer

> “Yes, I’ve implemented logging in Python. We usually store logs in files, and for production systems we forward them to centralized log systems for monitoring and debugging.”



Common storage options I’ve used / worked with:

1. Log files (for local & server debugging)


2. Databases (for audit logs)


3. Centralized logging tools (ELK, Cloud logging)




---

✅ Basic File-Based Logging (Most Common)

import logging

logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logging.info("User logged in successfully")
logging.error("Payment failed")

👉 Logs are stored in: app.log


---

✅ How We Use It in Real Projects (Like Your Fintech Apps)

> INFO → normal flow (API hits, user actions)

WARNING → unexpected but non-breaking issues

ERROR → API failures, DB issues

CRITICAL → system crashes




> Logs were later shipped to centralized systems for debugging production issues.




---

✅ If They Ask “Do You Store Logs in DB?”

> “Only for audit trails (like login history, trades, payments). Normal application logs are stored in files or centralized log systems, not inside transactional DBs.”




---

✅ Strong One-Line Finish

> “In short, I store logs in files using Python’s logging module and push them to centralized logging systems in production.”




---

If you want, I can also give you:

Rotating log files

Logging in Flask/Django

Difference between logging & print() (interview trap)

Yes — and here’s the correct, clear interview reply you should give:


---

✅ Interview Answer

> “Initially, logs are written to files on the server using Python’s logging module. From there, in production, those log files are automatically shipped to a cloud-based centralized logging system for monitoring and analysis.”



You can add:

> “So technically, the application writes logs locally first, and a log forwarder or cloud agent pushes them to the cloud.”




---

✅ Typical Cloud Flow (Real Systems)

Python App → app.log (server)
           → Log Agent / Forwarder
           → Cloud Logging / ELK / Monitoring Tool


---

✅ If they ask for examples of cloud tools

> AWS CloudWatch

ELK Stack (Elasticsearch, Logstash, Kibana)

GCP Logging, Azure Monitor





---

✅ Strong One-Line Summary

> “We don’t directly write logs to the cloud from Python; we write to files, and the cloud logging agent ships them for centralized monitoring.”




---

If you want, I can also prepare a Flask/Django production logging setup answer in 5–6 lines for deep technical rounds.

Got it — here’s the exact, clean technical answer you should give:


---

✅ Interview Answer

> “Yes, for logging in Python APIs and services, I use Python’s built-in logging module. It allows me to capture request flow, exceptions, warnings, and system errors at every step in a structured way.”



> “I configure log levels like INFO, WARNING, ERROR, and CRITICAL, and use handlers to write logs to files or console. In production, these files are picked up by centralized logging systems.”




---

✅ Basic Mechanism (What you actually use in code)

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = logging.FileHandler("app.log")
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

logger.info("API started")
logger.error("Database connection failed")


---

✅ How You Use It in APIs (Flask/Django style)

try:
    user = get_user(user_id)
    logger.info("User fetched successfully")
except Exception as e:
    logger.exception("Error while fetching user")

logger.exception() automatically logs the full stack trace.


---

✅ Strong One-Line Finish (Very Important)

> “So the main mechanism I use for logging in Python services is the built-in logging module with proper log levels, handlers, and formatters.”




---

If you want, I can also give you:

Logging in Flask vs Django

Why print() is not used in production

How log rotation works (RotatingFileHandler)

