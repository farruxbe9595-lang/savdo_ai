from __future__ import annotations
from datetime import datetime
from app.db.models import SessionLocal, Job


def create_job(admin_id: int, file_id: str) -> Job:
    with SessionLocal() as s:
        job = Job(admin_id=admin_id, file_id=file_id, status="QUEUED")
        s.add(job)
        s.commit(); s.refresh(job)
        return job


def get_job(job_id: int) -> Job | None:
    with SessionLocal() as s:
        return s.get(Job, job_id)


def update_job(job_id: int, **kwargs) -> Job | None:
    with SessionLocal() as s:
        job = s.get(Job, job_id)
        if not job: return None
        for k, v in kwargs.items(): setattr(job, k, v)
        job.updated_at = datetime.utcnow()
        s.commit(); s.refresh(job)
        return job


def list_recent(admin_id: int, limit: int = 20) -> list[Job]:
    with SessionLocal() as s:
        return s.query(Job).filter(Job.admin_id == admin_id).order_by(Job.id.desc()).limit(limit).all()
