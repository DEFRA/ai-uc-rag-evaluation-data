from app import config as app_config
from app.upload import service as upload_service


def get_upload_service() -> upload_service.UploadService:
    return upload_service.UploadService(
        cdp_uploader_url=app_config.config.uploader.cdp_uploader_url,
        s3_bucket=app_config.config.ingestion_data_bucket,
    )