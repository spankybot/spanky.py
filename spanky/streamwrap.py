import logging
import textwrap
import threading

from spanky.hook2.storage import dsdict

LOG_PREFIX = "logger/"

def get_loggers():
    """
    Returns list of loggers configured in logging
    """
    return [LOG_PREFIX + key for key in logging.Logger.manager.loggerDict.keys()]

def set_sw_for_logger(name, server_id, chan_id):
    """
    Sets stream wrapper for a logger
    """
    actual_name = name.replace(LOG_PREFIX, "")

    if actual_name in logging.Logger.manager.loggerDict:
        new_stream = StreamWrap(None, name)
        logging.Logger.manager.loggerDict[actual_name].addHandler(
            logging.StreamHandler(stream=new_stream))

        new_stream.set_channel(server_id, chan_id)
    else:
        print(f"No such logger {actual_name}")

def init_loggers():
    """
    Initialize the logging loggers.
    """
    settings = dsdict("debug", "settings")

    if "chans" not in settings:
        return

    for log_type in settings["chans"].keys():
        if log_type.startswith(LOG_PREFIX):
            data = settings["chans"][log_type]
            set_sw_for_logger(log_type, data["server_id"], data["chan_id"])

class StreamWrap():
    """
    Wrapper for a stream (i.e. stdout).
    """
    MAX_BUFFSIZE = 20 * 1024 # 20k of max buffer space
    MAX_MSG_SZ = 1990 # max discord message size

    wraps = {}

    def __init__(self, stream, name):
        self.stream = stream
        self.name = name

        self.settings = dsdict("debug", "settings")
        self._buf = ""
        self._lock = threading.Lock()

        self.enabled = False
        if "chans" in self.settings and self.name in self.settings["chans"]:
            self.enabled = True

        StreamWrap.wraps[self.name] = self

    @property
    def storage(self):
        return self.settings

    def _to_stream(self, s):
        """Write s to the stream"""
        if not self.stream:
            return

        self.stream.write(str(s))
        self.stream.flush()

    def _to_buffer(self, s):
        """Write s to the buffer"""
        to_write = str(s)

        try:
            self._lock.acquire()

            self._buf += to_write
            # Cap the buffer size to MAX_BUFFSIZE
            if len(self._buf) > StreamWrap.MAX_BUFFSIZE:
                self._buf = self._buf[-StreamWrap.MAX_BUFFSIZE:]
        except:
            pass
        finally:
            self._lock.release()

        return len(to_write)

    def flush_to_discord(self, bot, send_func):
        """
        Try flushing the buffer to discord.
        """
        if not bot.is_ready or not self.enabled:
            return

        old_buf = None
        try:
            self._lock.acquire()
            old_buf = self._buf
            self._buf = ""
        except:
            pass
        finally:
            self._lock.release()

        # Handle long lines
        lines = []
        for line in old_buf.splitlines():
            if len(line) >= StreamWrap.MAX_MSG_SZ:
                split_line = textwrap.wrap(line, width=200)
                lines.extend(split_line)
            else:
                lines.append(line)


        EMPTY_MSG = "-\n"
        # Split in chunks of maximum 2k chars
        chunks = []
        crt_line = EMPTY_MSG
        for line in lines:
            if len(line) + len(crt_line) >= StreamWrap.MAX_MSG_SZ:
                chunks.append(crt_line)
                crt_line = EMPTY_MSG

            crt_line += line + "\n"

        if crt_line != EMPTY_MSG:
            chunks.append(crt_line)

        if len(chunks) == 0:
            return

        server_id = self.storage["chans"][self.name]["server_id"]
        chan_id = self.storage["chans"][self.name]["chan_id"]
        for server in bot.get_servers():
            if server_id == server.id:
                for chunk in chunks:
                    send_func(server=server, target=chan_id, text=chunk, check_old=False)

    def get_channel(self):
        """
        Get the list of channels where debugging is enabled.
        """
        if "chans" not in self.storage or self.name not in self.storage["chans"]:
            return "Not set"

        return f"<#{self.storage['chans'][self.name]['chan_id']}>"

    def set_channel(self, server_id, chan_id):
        """
        Add a channel to the debug list
        """
        if "chans" not in self.storage:
            self.storage["chans"] = {}

        new_elem = {}
        new_elem["server_id"] = server_id
        new_elem["chan_id"] = chan_id

        self.storage["chans"][self.name] = new_elem
        self.storage.sync()
        self.enabled = True

    def rem_channel(self):
        if "chans" not in self.storage:
            return

        if self.name not in self.storage["chans"].keys():
            return

        del self.storage["chans"][self.name]
        self.storage.sync()
        self.enabled = False

    def write(self, data):
        """
        Stream write.
        """
        if self.enabled:
            self._to_buffer(data)

        self._to_stream(data)

    def flush(self):
        """
        TODO: Don't do anything?
        """
        pass