from schemas import Job

from ..config import JobQueue


async def process_ocr_job(client: JobQueue, job: Job) -> Job:
    return job
