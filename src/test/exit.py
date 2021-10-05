import atexit


@atexit.register
def last_word():
    with open("last_word.txt", "w") as f:
        print("I'm dead...", file=f)


while True:
    pass
