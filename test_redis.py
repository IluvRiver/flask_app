#!/usr/bin/env python3

import redis
import json
from google.cloud import secretmanager

def test_redis_connection():
    """Redis 연결 테스트"""
    try:
        # GCP Secret Manager에서 설정 로드
        client = secretmanager.SecretManagerServiceClient()
        name = client.secret_version_path("hifrodo-05", "project-secrets", "latest")
        response = client.access_secret_version(request={"name": name})
        config = json.loads(response.payload.data.decode("UTF-8"))
        
        print(f"Redis host: {config['redis_host']}")
        
        # GCP Redis 연결 시도 (SSL 없이)
        print("Testing GCP Redis connection (without SSL)...")
        r = redis.StrictRedis(
            host=config['redis_host'], 
            port=6379,
            socket_connect_timeout=10
        )
        
        # 연결 테스트
        result = r.ping()
        print(f"✅ Redis ping result: {result}")
        
        # 간단한 읽기/쓰기 테스트
        r.set('test_key', 'test_value')
        value = r.get('test_key')
        print(f"✅ Redis read/write test: {value}")
        
        return True
        
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        
        # SSL 연결도 시도해보기
        try:
            print("Testing Redis connection with SSL...")
            r_ssl = redis.StrictRedis(
                host=config['redis_host'], 
                port=6379,
                ssl=True,
                ssl_cert_reqs=None,
                socket_connect_timeout=10
            )
            result = r_ssl.ping()
            print(f"✅ Redis SSL ping result: {result}")
            return True
        except Exception as ssl_error:
            print(f"❌ Redis SSL connection also failed: {ssl_error}")
        
        return False

if __name__ == "__main__":
    test_redis_connection()
