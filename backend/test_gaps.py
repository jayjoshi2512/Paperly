import asyncio
import traceback
from app.database import AsyncSessionLocal
from app.eval.gap_detector import detect_knowledge_gaps
from app.models import Workspace

async def test():
    try:
        async with AsyncSessionLocal() as session:
            # We need a workspace
            workspace_id = 'test_id'
            print("Running detect_knowledge_gaps...")
            res = await detect_knowledge_gaps(session, workspace_id)
            print("Result:", res)
    except Exception as e:
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(test())
