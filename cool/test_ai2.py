from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
import time

def main():
	with Progress(
		SpinnerColumn(),
		TextColumn("[progress.description]{task.description}"),
		transient=True
	) as progress:
		task = progress.add_task("Processing...", total=100)

		with Live(Panel(Text("Temporary message here", style="bold yellow")), refresh_per_second=4) as live:
			for i in range(100):
				time.sleep(0.1)  # Simulating some work
				progress.update(task, advance=1)

				# Update the temporary message if needed
				if i == 50:
					live.update(Panel(Text("Halfway there!", style="bold green")))

			# Clear the temporary message
			live.update("")

	print("All tasks completed!")


if __name__ == "__main__":
	main()