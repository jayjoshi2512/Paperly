import asyncio
import aiomysql

async def fix():
    conn = await aiomysql.connect(host='localhost', port=3306, user='root', password='', db='paperly')
    cursor = await conn.cursor()

    fixes = [
        "ALTER TABLE unanswered_queries ADD COLUMN IF NOT EXISTS cluster_label VARCHAR(255)",
        "ALTER TABLE unanswered_queries ADD COLUMN IF NOT EXISTS created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE document_diffs ADD COLUMN IF NOT EXISTS created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
        "ALTER TABLE queries ADD COLUMN IF NOT EXISTS session_id VARCHAR(36)",
        "CREATE TABLE IF NOT EXISTS chat_sessions (id VARCHAR(36) PRIMARY KEY, workspace_id VARCHAR(36) NOT NULL, user_id VARCHAR(36) NOT NULL, title VARCHAR(255), summary_state TEXT, created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE, FOREIGN KEY (user_id) REFERENCES users(id))",
        "ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE queries ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE",
    ]

    for sql in fixes:
        try:
            await cursor.execute(sql)
            print(f"OK: {sql[:70]}")
        except Exception as e:
            print(f"SKIP: {e}")

    await conn.commit()
    await cursor.close()
    conn.close()
    print("All done!")

asyncio.run(fix())
