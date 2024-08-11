import random
import time

import colorama
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn, TaskID, DownloadColumn

#
# from pip._internal.cli.progress_bars import get_download_progress_renderer
#
# if __name__ == "__main__":
# 	chunks = []
# 	b = get_download_progress_renderer(bar_type="on", size=100)
# 	for i in range(100):
# 		chunks.append(range(i))
# 		for bb in b(chunks):
# 			time.sleep(.1)

# import time
# import sys
#
# toolbar_width = 40
#
# # setup toolbar
# sys.stdout.write("[%s]" % (" " * toolbar_width))
# sys.stdout.flush()
# sys.stdout.write("\b" * (toolbar_width+1)) # return to start of line, after '['
#
# for i in range(toolbar_width):
#     time.sleep(0.1) # do real work here
#     # update the bar
#     sys.stdout.write("█") # ■ ▒ █ █ █
#     sys.stdout.flush()
#
# sys.stdout.write("]\n") # this ends the progress bar

colorama.init()

taskIds = []

print("Meow111111111111111111")
# time.sleep(2)

progress = Progress(
    TextColumn("[blue] a {task.description}"),
    BarColumn(bar_width=20),
    "[progress.percentage]{task.percentage:>3.0f}%",
    "•",
    TimeElapsedColumn(),
    DownloadColumn(),
    # refresh_per_second = 60
)

print("Meow1111222222")

time.sleep(1)


progress.print("Hellow")
taskIds.append(progress.add_task(f"[green] Meow0...{int(time.time())}", total=1E6))
taskIds.append(progress.add_task(f"[green] Meow1...{int(time.time())}", total=1E6))
taskIds.append(progress.add_task(f"[green] Meow2...{int(time.time())}", total=1E6))

print(f"Rebder {progress.get_renderable()}")

with progress.console.capture() as capture:
    progress.print("Meow")
    progress.console.print("[bold red]Hello[/] World")

with progress:
    while True:
        if time.time_ns() % 13 == 0:
            taskIds.append(progress.add_task(f"[green] Added...{int(time.time())}", total=1E6))
            continue
        # print("Meow")
        for task in taskIds[:]:
            # progress.console.print("Meow")
            if time.time_ns() % 20 == 0:
                # o = "Deleted " +
                progress.print(TimeElapsedColumn().render(progress.tasks[task]))
                progress.remove_task(task)
                taskIds.remove(task)
                continue
            progress.update(task, advance=random.choice(range(100)) * 1000)
            time.sleep(0.05)

with progress.console.capture() as capture:
    progress.print("Meow")
    progress.console.print("[bold red]Hello[/] World")
# from rich.console import Console
#
# console = Console()
# tasks = [f"task {n}" for n in range(1, 11)]
#
# with console.status("[bold green]Working on tasks...") as status:
#     while tasks:
#         task = tasks.pop(0)
#         time.sleep(1)
#         console.log(f"{task} complete")