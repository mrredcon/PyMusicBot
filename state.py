class MusicSettings:
    def __init__(self):
        self.loop = False
        self.current_filename = ""
        self.current_title = ""
        self.queue = list()
        self.is_downloading = False
