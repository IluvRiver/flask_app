#!/usr/bin/env python3
import requests
import time
import socket

# 올바른 프로토콜 사용
CLOUDFRONT_URL = "https://www.choiyunha.com"
ALB_URL = "http://project-web-alb-70773185.us-east-2.elb.amazonaws.com"  # HTTP 사용

def check_connectivity(url, name):
    """연결 가능성 먼저 확인"""
    print(f"\n{name} 연결성 확인:")
    try:
        if url.startswith('https://'):
            host = url.replace('https://', '').split('/')[0]
            port = 443
        else:
            host = url.replace('http://', '').split('/')[0]
            port = 80
        
        # DNS 조회
        ip = socket.gethostbyname(host)
        print(f"  DNS 조회: {host} → {ip}")
        
        # 포트 연결 테스트
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((ip, port))
        sock.close()
        
        if result == 0:
            print(f"  포트 {port} 연결: 성공")
            return True
        else:
            print(f"  포트 {port} 연결: 실패 (코드: {result})")
            return False
            
    except Exception as e:
        print(f"  연결 실패: {e}")
        return False

def test_url(url, name):
    """URL 응답시간 테스트"""
    print(f"\n{name} 성능 테스트:")
    times = []
    
    for i in range(1, 6):
        try:
            start = time.time()
            # SSL 검증 비활성화 및 리다이렉트 허용
            response = requests.get(
                url, 
                timeout=30, 
                allow_redirects=True,
                verify=False,  # SSL 검증 비활성화
                headers={'User-Agent': 'Performance-Test/1.0'}
            )
            end = time.time()
            
            elapsed_ms = (end - start) * 1000
            times.append(elapsed_ms)
            print(f"  Run {i}: {elapsed_ms:.2f} ms (HTTP {response.status_code})")
            
        except requests.exceptions.ConnectTimeout:
            print(f"  Run {i}: 연결 타임아웃")
        except requests.exceptions.ReadTimeout:
            print(f"  Run {i}: 읽기 타임아웃")
        except requests.exceptions.ConnectionError as e:
            print(f"  Run {i}: 연결 오류 - {str(e)[:100]}...")
        except Exception as e:
            print(f"  Run {i}: ERROR - {str(e)[:100]}...")
    
    if times:
        avg = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        print(f"  평균: {avg:.2f} ms")
        print(f"  최소/최대: {min_time:.2f} / {max_time:.2f} ms")
        print(f"  측정 성공: {len(times)}/5회")
        return avg
    return 0

def main():
    print("=== ALB vs CloudFront 성능 비교 ===")
    print(f"CloudFront (HTTPS): {CLOUDFRONT_URL}")
    print(f"ALB (HTTP): {ALB_URL}")
    
    # SSL 경고 무시
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # 연결성 먼저 확인
    cf_connected = check_connectivity(CLOUDFRONT_URL, "CloudFront")
    alb_connected = check_connectivity(ALB_URL, "ALB")
    
    if not alb_connected:
        print("\n⚠️ ALB 연결 불가 - 보안그룹이나 타겟 상태를 확인하세요")
        return
    
    # 성능 테스트
    cf_avg = test_url(CLOUDFRONT_URL, "CloudFront") if cf_connected else 0
    alb_avg = test_url(ALB_URL, "ALB Direct") if alb_connected else 0
    
    print("\n" + "="*50)
    print("=== 최종 결과 요약 ===")
    
    if cf_avg > 0:
        print(f"📊 CloudFront (HTTPS): {cf_avg:.2f} ms")
    if alb_avg > 0:
        print(f"📊 ALB Direct (HTTP): {alb_avg:.2f} ms")
    
    if cf_avg > 0 and alb_avg > 0:
        if cf_avg < alb_avg:
            improvement = ((alb_avg - cf_avg) / alb_avg) * 100
            print(f"✅ CloudFront가 {improvement:.1f}% 더 빠름")
            print(f"💡 CDN 캐싱 효과로 {alb_avg - cf_avg:.2f}ms 단축")
        else:
            slower = ((cf_avg - alb_avg) / alb_avg) * 100
            print(f"⚠️ CloudFront가 {slower:.1f}% 더 느림")
            print(f"💡 지역이나 캐시 미스로 인한 지연 가능성")
    
    print("\n📝 참고사항:")
    print("  - CloudFront: HTTPS + CDN 캐싱")
    print("  - ALB: HTTP 직접 연결")
    print("  - 실제 사용자는 CloudFront(HTTPS)만 사용")

if __name__ == "__main__":
    main()