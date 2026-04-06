"""
Batch processor - Efficient batch LLM processing.

Queue management, rate limiting, cost tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Callable
from enum import Enum
import time


class Status(Enum):
    """Job status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Job:
    """Batch job."""
    id: str
    input: str
    status: Status = Status.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        """Get job duration in seconds."""
        if not self.started_at or not self.completed_at:
            return None
        return (self.completed_at - self.started_at).total_seconds()

    def to_dict(self) -> Dict:
        """Convert to dict."""
        return {
            "id": self.id,
            "input": self.input[:100],  # First 100 chars
            "status": self.status.value,
            "result": self.result[:100] if self.result else None,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost": self.cost,
            "duration_seconds": self.duration_seconds,
        }


class BatchProcessor:
    """Process items in batches with rate limiting."""

    def __init__(self, batch_size: int = 10, rate_limit: float = 0.1):
        """
        Initialize processor.

        Args:
            batch_size: Items per batch
            rate_limit: Delay between requests (seconds)
        """
        self.batch_size = batch_size
        self.rate_limit = rate_limit
        self.jobs: Dict[str, Job] = {}
        self.queue: List[str] = []
        self.total_cost = 0.0
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def add_job(self, job_id: str, input_text: str) -> Job:
        """Add job to queue."""
        job = Job(id=job_id, input=input_text)
        self.jobs[job_id] = job
        self.queue.append(job_id)
        return job

    def add_batch(self, inputs: List[str]) -> List[Job]:
        """Add multiple jobs."""
        jobs = []
        for i, input_text in enumerate(inputs):
            job = self.add_job(f"job_{len(self.jobs)}_{i}", input_text)
            jobs.append(job)
        return jobs

    def process_queue(self, callback: Callable) -> Dict:
        """Process all queued jobs."""
        results = {
            "total_jobs": len(self.queue),
            "successful": 0,
            "failed": 0,
            "total_cost": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
        }

        for i, job_id in enumerate(self.queue):
            job = self.jobs[job_id]

            # Rate limiting
            if i > 0:
                time.sleep(self.rate_limit)

            try:
                job.status = Status.PROCESSING
                job.started_at = datetime.now()

                # Process job
                result, input_tokens, output_tokens, cost = callback(job.input)

                job.result = result
                job.input_tokens = input_tokens
                job.output_tokens = output_tokens
                job.cost = cost
                job.status = Status.COMPLETED
                job.completed_at = datetime.now()

                results["successful"] += 1
                results["total_cost"] += cost
                results["total_input_tokens"] += input_tokens
                results["total_output_tokens"] += output_tokens

            except Exception as e:
                job.status = Status.FAILED
                job.error = str(e)
                job.completed_at = datetime.now()
                results["failed"] += 1

        self.total_cost = results["total_cost"]
        self.total_input_tokens = results["total_input_tokens"]
        self.total_output_tokens = results["total_output_tokens"]

        return results

    def get_stats(self) -> Dict:
        """Get batch statistics."""
        completed = sum(1 for j in self.jobs.values() if j.status == Status.COMPLETED)
        failed = sum(1 for j in self.jobs.values() if j.status == Status.FAILED)

        return {
            "total_jobs": len(self.jobs),
            "completed": completed,
            "failed": failed,
            "pending": len(self.queue) - completed - failed,
            "total_cost": self.total_cost,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "avg_cost_per_job": self.total_cost / completed if completed > 0 else 0,
        }

    def get_results(self) -> List[Dict]:
        """Get all job results."""
        return [job.to_dict() for job in self.jobs.values()]


def create_batch(inputs: List[str]) -> BatchProcessor:
    """Create processor and add inputs."""
    processor = BatchProcessor()
    processor.add_batch(inputs)
    return processor


def process(data: str, **kwargs) -> str:
    """Process function."""
    return "Batch processor ready"


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Batch process items with rate limiting")
    parser.add_argument("-b", "--batch-size", type=int, default=10)
    parser.add_argument("-r", "--rate-limit", type=float, default=0.1)
    parser.add_argument("--stats", action="store_true", help="Show stats only")

    args = parser.parse_args()

    processor = BatchProcessor(batch_size=args.batch_size, rate_limit=args.rate_limit)
    print(f"Batch processor ready")
    print(f"  Batch size: {args.batch_size}")
    print(f"  Rate limit: {args.rate_limit}s")


if __name__ == "__main__":
    main()
