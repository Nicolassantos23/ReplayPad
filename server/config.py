from shared.config import settings

SERVER_CONFIG = {
    "host": settings.server_host,
    "port": settings.server_port,
    "database_url": settings.database_url,
    "storage_path": settings.storage_path,
    "upload_max_size": settings.upload_max_size,
    "log_level": settings.log_level,
}
