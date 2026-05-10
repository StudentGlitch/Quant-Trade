import boto3
from botocore.exceptions import NoCredentialsError
from loguru import logger
import os

class S3Manager:
    """
    Phase 9.1: S3 Data Lake Integration.
    Boto3 wrapper for migrating data to MinIO/AWS S3.
    """
    
    def __init__(self, endpoint_url="http://minio:9000", access_key="swarm_admin", secret_key="swarm_secret"):
        self.endpoint_url = os.getenv("S3_ENDPOINT_URL", endpoint_url)
        self.access_key = os.getenv("S3_ACCESS_KEY_ID", access_key)
        self.secret_key = os.getenv("S3_SECRET_ACCESS_KEY", secret_key)
        
        try:
            self.s3 = boto3.client('s3',
                                   endpoint_url=self.endpoint_url,
                                   aws_access_key_id=self.access_key,
                                   aws_secret_access_key=self.secret_key)
            logger.info(f"S3Manager initialized with endpoint: {self.endpoint_url}")
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            self.s3 = None

    def initialize_buckets(self):
        """Create necessary buckets if they don't exist."""
        buckets = ['quant-market-data', 'quant-osint-data', 'quant-reports']
        if not self.s3:
            return
            
        existing_buckets = [b['Name'] for b in self.s3.list_buckets().get('Buckets', [])]
        
        for bucket in buckets:
            if bucket not in existing_buckets:
                try:
                    self.s3.create_bucket(Bucket=bucket)
                    logger.success(f"Created bucket: {bucket}")
                except Exception as e:
                    logger.error(f"Failed to create bucket {bucket}: {e}")

    def upload_file(self, file_path: str, bucket: str, object_name: str = None):
        """Upload a file to an S3 bucket."""
        if not self.s3:
            return False
            
        if object_name is None:
            object_name = os.path.basename(file_path)

        try:
            self.s3.upload_file(file_path, bucket, object_name)
            logger.debug(f"Uploaded {file_path} to s3://{bucket}/{object_name}")
            return True
        except FileNotFoundError:
            logger.error(f"The file {file_path} was not found")
            return False
        except NoCredentialsError:
            logger.error("Credentials not available")
            return False
        except Exception as e:
            logger.error(f"S3 Upload Error: {e}")
            return False
