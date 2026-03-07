from schemas import Job

from ..config import JobQueue


async def process_grader_job(client: JobQueue, job: Job) -> Job:
    return job
