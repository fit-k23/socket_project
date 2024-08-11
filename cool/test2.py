import time

from rich.progress import Progress

with Progress() as progress:
	task = progress.add_task("twiddling thumbs", total=10)
	for job in range(10):
		progress.console.print(f"Working on job #{job}")
		time.sleep(1)
		progress.advance(task)

	progress.remove_task(task)