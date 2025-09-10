# pyright: reportMissingImports=false, reportMissingModuleSource=false
import asyncio
from sqlalchemy import select

from src.db.session import async_session_factory
from src.db.models.job import Job
from src.db.models.candidate import Candidate


async def main() -> None:
    async with async_session_factory() as session:
        # Backfill Job.created_by_user_id with owner (user_id) if null
        jobs = (await session.execute(select(Job))).scalars().all()
        j_updated = 0
        for j in jobs:
            try:
                if getattr(j, "created_by_user_id", None) is None and getattr(j, "user_id", None):
                    j.created_by_user_id = j.user_id
                    j_updated += 1
            except Exception:
                pass

        # Backfill Candidate.created_by_user_id with tenant owner (user_id) if null
        cands = (await session.execute(select(Candidate))).scalars().all()
        c_updated = 0
        for c in cands:
            try:
                if getattr(c, "created_by_user_id", None) is None and getattr(c, "user_id", None):
                    c.created_by_user_id = c.user_id
                    c_updated += 1
            except Exception:
                pass

        try:
            await session.commit()
        except Exception:
            await session.rollback()
            raise

        print(f"Backfill done. Jobs updated: {j_updated}, Candidates updated: {c_updated}")


if __name__ == "__main__":
    asyncio.run(main())


