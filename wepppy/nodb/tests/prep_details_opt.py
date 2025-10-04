from wepppy.nodb.core import Ron


import sys
import traceback
import contextlib

@contextlib.contextmanager
def traced_print():
    global print

    # Store the old print function
    old_print = print

    def new_print(*args, **kwargs):
        # Get the current stack
        stack = traceback.extract_stack()

        # Call the old print function with the trace
        old_print(f"[STACK] {stack}")

        # Call the old print function with the original arguments
        old_print(*args, **kwargs)

    # Replace the built-in print function
    print = new_print
    yield
    # Restore the old print function
    print = old_print

def out2(msg):
    print(msg)

if __name__ == "__main__":
    # Test
    with traced_print():
        print("Hello, world!")
        out2("dog")

        wd = '/geodata/weppcloud_runs/kind-pinpoint/'
        ron = Ron.getInstance(wd)
        ron.subs_summary(abbreviated=True)

