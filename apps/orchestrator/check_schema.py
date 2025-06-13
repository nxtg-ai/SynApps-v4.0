"""
Script to check the database schema for the workflow_runs table.
"""
import asyncio
from db import get_db_session

async def check_schema():
    """Check the schema of the workflow_runs table."""
    async with get_db_session() as session:
        result = await session.execute('PRAGMA table_info(workflow_runs)')
        rows = result.fetchall()
        print('Database schema for workflow_runs:')
        for row in rows:
            print(row)

if __name__ == "__main__":
    asyncio.run(check_schema())
