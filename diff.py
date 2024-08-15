# import hashlib
# import time
#
# f = "test_123.txt"
#
# print(len("\x00\x01\x00\x00\x00budta\x00\x00\x00Zmeta\x00\x00\x00\x00\x00\x00\x00!hdlr\x00\x00\x00\x00\x00\x00\x00\x00mdirappl\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00-ilst\x00\x00\x00%\xa9too\x00\x00\x00\x1ddata\x00\x00\x00\x01\x00\x00\x00\x00Lavf58.76.100"))
#
# f1 = "input/" + f
# f2 = "output/" + f
#
# file1 = open(f1, "rb")
#
# file2 = open(f2, "rb")
#
# def get_hash(f_path, mode='md5'):
#     h = hashlib.new(mode)
#     with open(f_path, 'rb') as file:
#         data = file.read()
#     h.update(data)
#     digest = h.hexdigest()
#     return digest
#
# if get_hash(f1) != get_hash(f2):
# 	print("Wrong hash")
#
# while False:
# 	s1 = file1.read(4096)
# 	s2 = file1.read(4096)
# 	if s1 == s2: continue
# 	print(s1, "\n\n", s2, "\n===================\n")
# 	time.sleep(0.5)
from rich.progress import Progress, TextColumn

progress = Progress(
	TextColumn("[bold blue]{task.description}"),
	auto_refresh=True
)

task0 = progress.add_task("Meow0")
task1 = progress.add_task("Meow1")
task2 = progress.add_task("Meow2")
task3 = progress.add_task("Meow3")

print(progress.tasks)

progress.remove_task(task2)

print("\n\n")

print(progress.tasks)

