class StreamHandler:
    """
    Handles writing to output streams such as files and the terminal. Can handle writing to multiple streams at once
    and have control over which streams to exclude as well.
    """

    def __init__(self, file_name: str = None, open_mode='w', terminal_out=False):
        if file_name is not None:
            self.file = open(file_name, open_mode)
        else:
            self.file = None
        self.terminal_out = terminal_out

    def write_message(self, message: str, no_print=False) -> None:
        """
        Write the content inside message to the available streams.

        :param message: A string that should be written to an output stream
        :param no_print: Disables printing the output to the terminal
        """
        if self.terminal_out and not no_print:
            print(message)

        if self.file is not None:
            self.file.write(message)

    def close(self) -> None:
        """
        Closes all opened output streams
        """
        if self.file is not None:
            self.file.close()
