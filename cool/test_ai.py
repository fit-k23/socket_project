import time
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn
from rich.console import Console
from io import StringIO

# Create a StringIO buffer to capture the output
output_buffer = StringIO()

# Create a console that writes to the StringIO buffer
custom_console = Console(file=output_buffer, force_terminal=True)

with Progress(
    TextColumn("[bold blue]{task.description}"),
    BarColumn(),
    "[progress.percentage]{task.percentage:>3.0f}%",
    "•",
    TimeElapsedColumn(),
    console=custom_console,  # Use the custom console
) as progress:

    # Add a task
    task_id = progress.add_task("Processing...", total=100)


    while not progress.finished:
        progress.update(task_id, advance=1)
        time.sleep(0.005)

# Get the final output string from the StringIO buffer
final_output = output_buffer.getvalue()

print("Meow")
# Print the captured output (or use it as needed)
print(final_output)

