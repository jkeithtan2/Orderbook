class EventException(Exception):
    def __init__(self, msg, event):
        super().__init__(msg)
        self.event = event


class SnapshotException(Exception):
    def __init__(self, msg):
        super().__init__(msg)


class SnapshotHttpException(Exception):
    pass


class SocketException(Exception):
    def __init__(self, msg):
        super().__init__(msg)


class InitException(Exception):
    pass
