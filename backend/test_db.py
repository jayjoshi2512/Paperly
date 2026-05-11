import asyncio
import traceback
from app.database import AsyncSessionLocal
from app.models import Workspace, User, RoleEnum
from app.auth.service import get_password_hash

async def test():
    try:
        async with AsyncSessionLocal() as session:
            # 1. Create Workspace
            workspace = Workspace(name='test_workspace_3')
            session.add(workspace)
            await session.flush() # This is where it failed previously
            
            # 2. Create User
            hashed = get_password_hash("password123")
            user = User(
                email="test_user_3@example.com",
                password_hash=hashed,
                workspace_id=workspace.id,
                role=RoleEnum.admin
            )
            session.add(user)
            await session.commit()
            print('SUCCESS')
    except Exception as e:
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(test())
