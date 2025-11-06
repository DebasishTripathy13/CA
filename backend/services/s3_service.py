import boto3
from botocore.exceptions import ClientError
from config import Config

class S3Service:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            region_name=Config.AWS_REGION,
            aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY
        )
        self.bucket_name = Config.S3_BUCKET_NAME
    
    def upload_certificate(self, cert_content, request_id, file_type='cert'):
        """Upload certificate or key to S3"""
        try:
            key = f"certificates/{request_id}/{file_type}.pem"
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=cert_content,
                ServerSideEncryption='AES256',
                ContentType='application/x-pem-file'
            )
            
            return key
        except ClientError as e:
            print(f"Error uploading to S3: {e}")
            return None
    
    def download_certificate(self, s3_key):
        """Download certificate from S3"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return response['Body'].read()
        except ClientError as e:
            print(f"Error downloading from S3: {e}")
            return None
    
    def generate_presigned_url(self, s3_key, expiration=3600):
        """Generate presigned URL for certificate download"""
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            print(f"Error generating presigned URL: {e}")
            return None
    
    def delete_certificate(self, s3_key):
        """Delete certificate from S3"""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True
        except ClientError as e:
            print(f"Error deleting from S3: {e}")
            return False
