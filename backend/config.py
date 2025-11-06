import os
from datetime import timedelta

class Config:
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        'postgresql://user:password@localhost:5432/cert_assistant'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # AWS Configuration
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'cert-assistant-storage')
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    
    # ADCS Configuration
    ADCS_HOST = os.getenv('ADCS_HOST')
    ADCS_CA_NAME = os.getenv('ADCS_CA_NAME')
    
    # Application Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    
    # Email Configuration
    SMTP_SERVER = os.getenv('SMTP_SERVER')
    SMTP_PORT = os.getenv('SMTP_PORT', 587)
    SMTP_USERNAME = os.getenv('SMTP_USERNAME')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
    
    # SSO Configuration
    SSO_ENABLED = os.getenv('SSO_ENABLED', 'false').lower() == 'true'
    SSO_PROVIDER_URL = os.getenv('SSO_PROVIDER_URL')
    SSO_CLIENT_ID = os.getenv('SSO_CLIENT_ID')
    SSO_CLIENT_SECRET = os.getenv('SSO_CLIENT_SECRET')
