from fastmcp import FastMCP
import os
import aiosqlite
import sqlite3
import tempfile
from datetime import datetime
import json

# --------------------------------------------------
# Configuration
# --------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TEMP_DIR = tempfile.gettempdir()

DB_PATH = os.path.join(TEMP_DIR, "expenses.db")

CATEGORIES_PATH = os.path.join(BASE_DIR, "categories.json")

print(f"Database path: {DB_PATH}")


# ============================================================
# FastMCP Server
# ============================================================

mcp = FastMCP("ExpenseTracker")


# ============================================================
# Database Initialization
# ============================================================

def init_db():
    """Create the SQLite database and expenses table if needed."""

    try:
        with sqlite3.connect(DB_PATH) as conn:

            # Enable WAL mode
            conn.execute("PRAGMA journal_mode=WAL")

            # Create expenses table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT DEFAULT '',
                    note TEXT DEFAULT ''
                )
                """
            )

            # Test write access
            conn.execute(
                """
                INSERT OR IGNORE INTO expenses
                (date, amount, category)
                VALUES ('2000-01-01', 0, 'test')
                """
            )

            conn.execute(
                "DELETE FROM expenses WHERE category = 'test'"
            )

            conn.commit()

            print("Database initialized successfully with write access")

    except Exception as e:
        print(f"Database initialization error: {e}")
        raise


# Initialize database when the server starts
init_db()


# ============================================================
# Helper Functions
# ============================================================

def validate_date(date_string: str) -> bool:
    """
    Validate that the date is in YYYY-MM-DD format.
    Example: 2026-09-23
    """

    try:
        datetime.strptime(date_string, "%Y-%m-%d")
        return True
    except ValueError:
        return False


# ============================================================
# Tool 1: Add Expense
# ============================================================

@mcp.tool()
async def add_expense(
    date: str,
    amount: float,
    category: str,
    subcategory: str = "",
    note: str = ""
):
    """
    Add a new expense entry to the database.

    Date must be in YYYY-MM-DD format.
    Example: 2026-09-23
    """

    # Validate date
    if not validate_date(date):
        return {
            "status": "error",
            "message": (
                "Invalid date format. "
                "Please use YYYY-MM-DD, for example 2026-09-23."
            )
        }

    # Validate amount
    if amount <= 0:
        return {
            "status": "error",
            "message": "Amount must be greater than 0."
        }

    try:
        async with aiosqlite.connect(DB_PATH) as conn:

            cursor = await conn.execute(
                """
                INSERT INTO expenses
                (date, amount, category, subcategory, note)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    date,
                    amount,
                    category,
                    subcategory,
                    note
                )
            )

            expense_id = cursor.lastrowid

            await conn.commit()

            return {
                "status": "success",
                "id": expense_id,
                "message": "Expense added successfully",
                "expense": {
                    "date": date,
                    "amount": amount,
                    "category": category,
                    "subcategory": subcategory,
                    "note": note
                }
            }

    except Exception as e:

        if "readonly" in str(e).lower():
            return {
                "status": "error",
                "message": (
                    "Database is in read-only mode. "
                    "Check file permissions."
                )
            }

        return {
            "status": "error",
            "message": f"Database error: {str(e)}"
        }


# ============================================================
# Tool 2: List Expenses
# ============================================================

@mcp.tool()
async def list_expenses(
    start_date: str,
    end_date: str
):
    """
    List expense entries within an inclusive date range.

    Dates must be in YYYY-MM-DD format.
    """

    # Validate dates
    if not validate_date(start_date):
        return {
            "status": "error",
            "message": (
                "Invalid start_date format. "
                "Please use YYYY-MM-DD."
            )
        }

    if not validate_date(end_date):
        return {
            "status": "error",
            "message": (
                "Invalid end_date format. "
                "Please use YYYY-MM-DD."
            )
        }

    if start_date > end_date:
        return {
            "status": "error",
            "message": "start_date cannot be after end_date."
        }

    try:
        async with aiosqlite.connect(DB_PATH) as conn:

            cursor = await conn.execute(
                """
                SELECT
                    id,
                    date,
                    amount,
                    category,
                    subcategory,
                    note
                FROM expenses
                WHERE date BETWEEN ? AND ?
                ORDER BY date DESC, id DESC
                """,
                (
                    start_date,
                    end_date
                )
            )

            rows = await cursor.fetchall()

            columns = [
                description[0]
                for description in cursor.description
            ]

            expenses = [
                dict(zip(columns, row))
                for row in rows
            ]

            return expenses

    except Exception as e:

        return {
            "status": "error",
            "message": f"Error listing expenses: {str(e)}"
        }


# ============================================================
# Tool 3: Summarize Expenses
# ============================================================

@mcp.tool()
async def summarize(
    start_date: str,
    end_date: str,
    category: str | None = None
):
    """
    Summarize expenses by category within an inclusive date range.

    Dates must be in YYYY-MM-DD format.
    """

    # Validate dates
    if not validate_date(start_date):
        return {
            "status": "error",
            "message": (
                "Invalid start_date format. "
                "Please use YYYY-MM-DD."
            )
        }

    if not validate_date(end_date):
        return {
            "status": "error",
            "message": (
                "Invalid end_date format. "
                "Please use YYYY-MM-DD."
            )
        }

    if start_date > end_date:
        return {
            "status": "error",
            "message": "start_date cannot be after end_date."
        }

    try:
        async with aiosqlite.connect(DB_PATH) as conn:

            query = """
                SELECT
                    category,
                    SUM(amount) AS total_amount,
                    COUNT(*) AS count
                FROM expenses
                WHERE date BETWEEN ? AND ?
            """

            params = [
                start_date,
                end_date
            ]

            # Optional category filter
            if category:
                query += " AND category = ?"
                params.append(category)

            query += """
                GROUP BY category
                ORDER BY total_amount DESC
            """

            cursor = await conn.execute(
                query,
                params
            )

            rows = await cursor.fetchall()

            columns = [
                description[0]
                for description in cursor.description
            ]

            summary = [
                dict(zip(columns, row))
                for row in rows
            ]

            return summary

    except Exception as e:

        return {
            "status": "error",
            "message": (
                f"Error summarizing expenses: {str(e)}"
            )
        }


# ============================================================
# Resource: Categories
# ============================================================

@mcp.resource(
    "expense:///categories",
    mime_type="application/json"
)
def categories():
    """Return available expense categories."""

    default_categories = {
        "categories": [
            "Food & Dining",
            "Transportation",
            "Shopping",
            "Entertainment",
            "Bills & Utilities",
            "Healthcare",
            "Travel",
            "Education",
            "Business",
            "Other"
        ]
    }

    try:

        if os.path.exists(CATEGORIES_PATH):

            with open(
                CATEGORIES_PATH,
                "r",
                encoding="utf-8"
            ) as file:

                return file.read()

        return json.dumps(
            default_categories,
            indent=2
        )

    except Exception as e:

        return json.dumps({
            "error": (
                f"Could not load categories: {str(e)}"
            )
        })


# ============================================================
# Start MCP Server
# ============================================================

if __name__ == "__main__":

    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8000
    )