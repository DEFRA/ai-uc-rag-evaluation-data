import datetime


class UploadRecord:
    def __init__(self, upload_status: str, location: str):
        self.upload_status = upload_status
        self.location = location
        self.created_at = datetime.datetime.now(datetime.UTC)
