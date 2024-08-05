import os

with open("input/test_123.txt", 'w') as f:
	for i in range(10000):
		f.write("L" + str(i).ljust(4) + " ")
		for j in range(10):
			f.write(f"{j} ")
		f.write("\n")