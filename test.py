import os

with open("input/test_123.txt", 'w') as f:
	for i in range(100000):
		f.write(f"{i % 10} ")
		if i % 10 == 0:
			f.write("\n")

with open("input/test_123.txt", 'r') as f:
	s = f.readline().splitlines()
