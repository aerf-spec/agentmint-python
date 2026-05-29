import sys, time

def stream(path, delay=0.15):
    with open(path) as f:
        for line in f:
            sys.stdout.write(line)
            sys.stdout.flush()
            time.sleep(delay)

stream("/tmp/tamper_output.txt")
