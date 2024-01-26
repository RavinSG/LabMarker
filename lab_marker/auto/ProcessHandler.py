import pexpect

from lab_marker.auto.StreamHandler import StreamHandler


class ProcessHandler:
    def __init__(self, process_name, out_stream: StreamHandler, cwd=None):
        if cwd is None:
            self.process = pexpect.spawn(process_name)
        else:
            self.process = pexpect.spawn(process_name, cwd=cwd)
        self.is_alive = self.process.isalive()
        self.out_stream = out_stream

    def write_to_out_stream(self, message):
        self.out_stream.write_message(message)

    def get_output(self, timeout=0.1):
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

    def send_command(self, command, get_output=True):
        if not self.is_alive:
            raise ChildProcessError("The called process has already been terminated")
        self.process.sendline(command)
        self.is_alive = self.process.isalive()
        if get_output:
            self.get_output()

    def kill_process(self):
        self.write_to_out_stream("Process terminated!")
        self.process.close()
