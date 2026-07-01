import json
from pathlib import Path
from uuid import uuid4

from app.models import Run


def create_run(task: str, storage_dir: str = "runs") -> Run:
    storage_path = Path(storage_dir)
    storage_path.mkdir(parents=True, exist_ok=True)

    run = Run(id=f"run_{uuid4().hex}", task=task)
    run_file = storage_path / f"{run.id}.json"

    run_file.write_text(
        json.dumps(run.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return run