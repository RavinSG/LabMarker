class StreamHandler:
    def __init__(self, file_name=None, open_mode='w', terminal_out=True):
        if file_name is not None:
            self.file = open(file_name, open_mode)
        else:
            self.file = None
        self.terminal_out = terminal_out

    def write_message(self, message):
        if self.terminal_out:
            print(message)

        if self.file is not None:
            self.file.write(message)

    def close(self):
        if self.file is not None:
            self.file.close()
