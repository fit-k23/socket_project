from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.console import Console
import time

from rich.text import Text


def main():
	console = Console(color_system="truecolor")

	with Progress(
		SpinnerColumn(),
		TextColumn("[progress.description]{task.description}"),
		transient=True,
		console=console
	) as progress:
		task = progress.add_task("Processing...", total=100)

		# Print the initial temporary message
		console.print("Starting the process...", style="bold yellow")

		for i in range(100):
			time.sleep(0.1)  # Simulating some work
			progress.update(task, advance=1)

			# Update the temporary message if needed
			if i == 50:
				# Move cursor up one line and clear the line
				# console.print(Text.from_ansi("\033[A\033[K Meow").spans)
				console.print(Text.from_ansi("\033[FMy text overwriting the previous line.").spans)
				console.print("Halfway there!", style="bold green")

		# Clear the temporary message
		# console.control("\033[A\033[K")

		progress.print("[bold]All tasks completed!")


if __name__ == "__main__":
	main()