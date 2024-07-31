# Known bugs:
### > If file has an odd size, it will break the design

Eg: the buffer size is 1024, the flag `[S0FTE`'s size is 8. If the file size is between the 1016 to 1024, it will split up the flag and break the format. This's also the case for any size that split up the flag.

I have no clue how to solve this but double buffering...

### > Sometime, the buffer (system one?) split up the buffer and break the program...