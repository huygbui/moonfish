from app.worker.hatchet_client import hatchet
from app.worker.workflows import podcast_generation


def main() -> None:
    worker = hatchet.worker("podcast_generation_worker", workflows=[podcast_generation])
    worker.start()


if __name__ == "__main__":
    main()
