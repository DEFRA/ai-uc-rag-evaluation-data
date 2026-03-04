import fastapi
import pymongo.asynchronous.database

from app import config as app_config
from app.common import mongo
from app.upload import repository as upload_repository
from app.upload import service as upload_service


def get_upload_record_repository(
    db: pymongo.asynchronous.database.AsyncDatabase = fastapi.Depends(mongo.get_db),
) -> upload_repository.UploadRecordRepository:
    return upload_repository.UploadRecordRepository(db)


def get_upload_service(
    upload_repo: upload_repository.UploadRecordRepository = fastapi.Depends(
        get_upload_record_repository
    ),
) -> upload_service.UploadService:
    return upload_service.UploadService(
        cdp_uploader_url=app_config.config.uploader.cdp_uploader_url,
        s3_bucket=app_config.config.ingestion_data_bucket,
        callback_base_url=app_config.config.uploader.callback_base_url,
        upload_repo=upload_repo,
    )
