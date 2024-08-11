from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.text import Text
import time


def main():
	# Note: We're using only one live display (Progress) for both progress and messages
	with Progress(
		SpinnerColumn(),
		TextColumn("[progress.description]{task.description}"),
		TextColumn("{task.fields[message]}"),
		transient=True
	) as progress:
		task = progress.add_task("Processing...", total=100, message="Starting...")

		for i in range(100):
			time.sleep(0.1)  # Simulating some work
			progress.update(task, advance=1)

			# Update the temporary message if needed
			if i == 50:
				progress.update(task, message="Halfway there!")

		# Clear the temporary message
		# progress.update(task, message="")

	print("All tasks completed!")


if __name__ == "__main__":
	main()