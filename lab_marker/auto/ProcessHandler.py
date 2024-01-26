import pexpect

from lab_marker.auto.StreamHandler import StreamHandler


class ProcessHandler:
    """
    This class is used to create and handle processes run for evaluating labs. Processes are run using pexpect and the
    output of the processes are polled during runtime. Commands can also be sent to the process while it is running.
    Outputs of the processes are handled by a StreamHandler object.
    """

    def __init__(self, process_name: str, out_stream: StreamHandler, cwd=None):
        if cwd is None:
            self.process = pexpect.spawn(process_name)
        else:
            # If cwd is not None, runs the command to create the process from cwd
            self.process = pexpect.spawn(process_name, cwd=cwd)
        self.is_alive = self.process.isalive()
        self.out_stream = out_stream

    def write_to_out_stream(self, message: str) -> None:
        self.out_stream.write_message(message)

    def get_output(self, timeout=0.1) -> None:
        """
        Polls the process in 1000 byte chunks to get it's output. If timeout is set to None, the read may block
        indefinitely. When the timeout is exceeded before filling the read buffer, a timeout event is raised. The
        content of the read buffer is written out using the outstream.

        When trying to read from a terminated process, an error will be raised.

        :param timeout: How long to wait for the buffer to fill
        """

        if not self.is_alive:
            raise ChildProcessError("The called process has already been terminated")
        while True:
            try:
                output = self.process.read_nonblocking(1000, timeout=timeout).decode('utf-8')
                self.write_to_out_stream(output)

            except pexpect.exceptions.TIMEOUT:
                self.is_alive = self.process.isalive()
                return

            except pexpect.exceptions.EOF:
                self.is_alive = self.process.isalive()
                return

    def send_command(self, command: str, get_output=True) -> None:
        """
        Sends a command to the process to be executed. By default, the result of executing the command will be polled
        from the process.

        :param command: The command to be sent to the process
        :param get_output: If true, the process will be polled right after sending the command to get the output
        """

        if not self.is_alive:
            raise ChildProcessError("The called process has already been terminated")

        self.process.sendline(command)
        self.is_alive = self.process.isalive()
        if get_output:
            self.get_output()

    def kill_process(self) -> None:
        """
        Kill the process by force
        """
        self.write_to_out_stream("Process terminated!")
        self.process.close()
