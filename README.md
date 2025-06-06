# [웹서버14주차]Rate Limiting 미들웨어 구현

- Rate Limiting (속도 제한)
    - 특정 시간 동안 **클라이언트가 보낼 수 있는 요청 수를 제한**하는 기술
    - 보안(DoS/DDoS 방어), 자원 보호, API 사용 통제 등에 사용
    - AWS **Lightsail(Ubuntu)** 환경에서 사용할 수 있는 **rate limiting 구현**

---

## ✅ 1. Rate Limiting 구현 방식

| 방식 | 위치 | 도구 | 설명 |
| --- | --- | --- | --- |
| **UFW** | 서버 방화벽 | `ufw` (Uncomplicated Firewall) | 기본적인 `connection limit` 적용 가능 (IP당 접속 횟수 제한) |
| **Nginx** | Reverse Proxy | `limit_conn`, `limit_req` | HTTP 요청 단위의 세밀한 속도 제한 설정 가능 |
| **Django 등 앱 레벨** | 웹 애플리케이션 | `django-ratelimit`, DRF throttling 등 | 사용자/토큰/IP 기준의 API 요청 제한 |
| **Cloudflare/Lightsail 방화벽** | CDN or 외부 | Cloudflare Rules, AWS 네트워크 ACL | 대규모 공격 방지, 전방위 보호용 |

---

## 🔐 2. UFW 기반 간단 Rate Limiting (TCP 연결 제한)

```bash
# 기본 예: 30초 내 6회 이상 접속 시 차단 (SSH brute-force 방지 등)
sudo ufw limit ssh/tcp comment 'Limit SSH rate'

```

- 위 명령은 `ufw`의 기본 Rate Limiting 기능으로,
    - **IP당 30초에 6번 이상 접속 시 차단**
    - 주로 **SSH brute-force 방지용**으로 사용

> ❗ HTTP 요청 단위의 제한에는 적합하지 않음 — Nginx 권장
> 

---

## 🚦 3. Nginx 기반 HTTP Rate Limiting 설정 예제

### 🔧 `/etc/nginx/nginx.conf` 또는 `site-available/*.conf`에 추가

```
http {
    limit_req_zone $binary_remote_addr zone=mylimit:10m rate=5r/s;

    server {
        listen 80;
        server_name yourdomain.com;

        location / {
            limit_req zone=mylimit burst=10 nodelay;
            proxy_pass http://127.0.0.1:8000;
        }
    }
}

```

### 설명:

- `limit_req_zone`: 클라이언트 IP 기반으로 요청 수 추적 (`5r/s` = 초당 5건)
- `burst=10`: 버스트 요청 허용 수 (짧은 시간 급증 허용)
- `nodelay`: 가능한 즉시 처리 (지연 없음, 초과 시 거절)

### 📦 설정 적용

```bash
sudo nginx -t
sudo systemctl reload nginx

```

---

## 🧩 4. Django/DRF 기반 Application-Level Rate Limiting

### ✅ 설치

```bash
pip install django-ratelimit

```

### ✅ 예제 (View 함수에 데코레이터 적용)

```python
from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='5/m', block=True)
def my_view(request):
    return HttpResponse("OK")

```

- `5/m`: 분당 5회 허용
- `key='ip'`: 클라이언트 IP 기준
- `block=True`: 초과 시 429 응답

### ✅ DRF (Django REST Framework) 설정

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '10/min',
    }
}

```

---

## ✨ 정리

| 범위 | 방법 | 적용 대상 | 장점 |
| --- | --- | --- | --- |
| 서버 방화벽 | `ufw limit` | TCP 포트 수준 | SSH brute-force 방지 |
| 웹 서버 | `nginx limit_req` | HTTP 요청 | 속도 제한 설정 정밀 |
| 웹 앱 | `django-ratelimit` | API / 사용자별 | 인증된 사용자 제한에 적합 |

---

## ✅  미들웨어 앱 디렉토리 구조

- Django 캐시활용

```

firewall_project/
├── firewall/
│   ├── models.py
│   ├── views.py
│   ├── middleware.py
│   └── ...
└── firewall_project/
    └── settings.py

```

- Django 프로젝트에 **Rate Limiting (요청 속도 제한)** 기능 추가로
    - 클라이언트의 요청 빈도를 제한해서 **DoS 방지**, **API 오용 방지**, **자원 보호** 등의 목적 달성
    - **IP 기반 요청 횟수 제한(Rate Limit)** 기능을 구현하는 방법

---

## ✅ 간단한 IP 기반 Rate Limiting 미들웨어 직접 구현

### 🔹 예: 1분당 10회 요청 제한

`firewall/middleware.py`:

```python
import time
from django.core.cache import cache
from django.http import JsonResponse

class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ip = self.get_client_ip(request)
        now = time.time()
        key = f"rate-limit:{ip}"
        window = 60  # 초
        limit = 10   # 허용 횟수

        history = cache.get(key, [])
        history = [timestamp for timestamp in history if now - timestamp < window]

        if len(history) >= limit:
            return JsonResponse({"error": "Rate limit exceeded. Try again later."}, status=429)

        history.append(now)
        cache.set(key, history, timeout=window)

        return self.get_response(request)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0]
        return request.META.get("REMOTE_ADDR")

```

---

### 🔹 설정에 추가

`settings.py`에 아래 설정 추가:

```python
MIDDLEWARE += ['firewall.middleware.RateLimitMiddleware']

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

```

> 배포 시 Redis 등의 외부 캐시 사용 추천
> 

---

## ✅ 코드 설명 (해석 및 구조 정리)

```python
class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

```

- Django 미들웨어 표준 구조. **요청 전후 처리 가능.**

```python
def __call__(self, request):
    ip = self.get_client_ip(request)  # 클라이언트 IP 추출
    now = time.time()                 # 현재 시간 (초 단위 float)
    key = f"rate-limit:{ip}"         # 캐시에 사용할 키
    window = 60                      # 시간 창 (초)
    limit = 10                       # 제한 횟수 (10회)

```

```python
    history = cache.get(key, [])  # 이전 요청 시간 리스트 가져오기
    history = [t for t in history if now - t < window]  # window 내 요청만 유지

```

- `window` 초 이내의 요청만 필터링 (슬라이딩 윈도우 방식)

```python
    if len(history) >= limit:
        return JsonResponse({"error": "Rate limit exceeded. Try again later."}, status=429)

```

- 요청이 허용 범위를 초과하면 `429 Too Many Requests` 반환

```python
    history.append(now)  # 이번 요청 시간 추가
    cache.set(key, history, timeout=window)

```

- 요청 기록을 다시 캐시에 저장 (만료 시간은 `window`와 동일)

```python
    return self.get_response(request)  # 정상 처리

```

```python
def get_client_ip(self, request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0]
    return request.META.get("REMOTE_ADDR")

```

- 프록시 서버 뒤에 있을 경우를 대비하여 `X-Forwarded-For` 헤더 우선

---

## 🛠️ 사용 방법

1. `firewall/middleware.py` 파일 저장
2. `settings.py` 에 등록:

```python
MIDDLEWARE = [
    # ...
    'firewall.middleware.RateLimitMiddleware',
]

```

1. `settings.py`에서 캐시 백엔드 설정 확인:

```python
# 간단한 테스트용 로컬 메모리 캐시
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'rate-limit-cache',
    }
}

```

> 🚀 운영환경에서는 Redis를 권장
> 

```python
# Redis 캐시 사용 예시 (django-redis 필요)
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

```

---

## ✅ 테스트 환경

- Django에서 **IP 기반 Rate Limiting**을 위한 **미들웨어 테스트 코드**
    - `RateLimitMiddleware`가 요청을 제한하는지 검증

---

### 📁 디렉토리 구조 예시

```
firewall_project/
├── firewall/
│   ├── middleware.py
│   ├── views.py
│   ├── tests/
│       └── test_rate_limit.py  ← 테스트 코드 위치

```

---

## ✅ `firewall/tests/test_rate_limit.py`

```python
import time
from django.test import TestCase, Client, override_settings

@override_settings(
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }
)
class RateLimitMiddlewareTest(TestCase):
    def setUp(self):
        self.client = Client(REMOTE_ADDR='127.0.0.1')

    def test_rate_limit_allows_under_limit(self):
        for i in range(5):
            response = self.client.get('/')
            self.assertNotEqual(response.status_code, 429, f"Request {i+1} failed early")

    def test_rate_limit_blocks_over_limit(self):
        for i in range(10):
            self.client.get('/')
        response = self.client.get('/')
        self.assertEqual(response.status_code, 429)
        self.assertIn("Rate limit exceeded", response.json()["error"])

    def test_rate_limit_resets_after_window(self):
        for i in range(10):
            self.client.get('/')
        time.sleep(61)  # 60초 후 재요청
        response = self.client.get('/')
        self.assertNotEqual(response.status_code, 429)

```

---

## ✅ 테스트 실행

```bash
python manage.py test firewall.tests.test_rate_limit

```

---

- 실행 결과

![md.png](md.png)

## ✅ 테스트 설명

| 테스트 이름 | 설명 |
| --- | --- |
| `test_rate_limit_allows_under_limit` | 5회 이하 요청은 허용되어야 함 |
| `test_rate_limit_blocks_over_limit` | 10회 넘는 요청은 `429` 반환해야 함 |
| `test_rate_limit_resets_after_window` | 60초 지나면 다시 요청 가능해야 함 |

---

## ✅ 목표 : 10초에 10회 허용

- **`RateLimitMiddleware` 테스트가 너무 오래 걸리는 이유는 `time.sleep(61)`** 때문
    - **`rate window`를 테스트용으로 축소**하고, **테스트 속도를 대폭 향상** 조정
    - 테스트 시간을 `60초 → 10초`로 단축
    - `rate limit window`를 설정값으로 분리

---

## ✅ 미들웨어 구현 예시

```python
import time
from django.core.cache import cache
from django.http import JsonResponse
from django.conf import settings

class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

        # 설정 또는 기본값
        self.window = getattr(settings, "RATE_LIMIT_WINDOW", 10)  # 10초
        self.limit = getattr(settings, "RATE_LIMIT_COUNT", 10)    # 10회

    def __call__(self, request):
        ip = self.get_client_ip(request)
        now = time.time()
        key = f"rate-limit:{ip}"

        # 요청 기록 가져오기
        history = cache.get(key, [])
        # 윈도우 내 요청만 유지
        history = [t for t in history if now - t < self.window]

        if len(history) >= self.limit:
            return JsonResponse(
                {"error": "Rate limit exceeded. Try again later."},
                status=429
            )

        # 요청 기록 추가 및 저장
        history.append(now)
        cache.set(key, history, timeout=self.window)

        return self.get_response(request)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

```

---

## ✅ `settings.py` 설정 (선택)

```python
# settings.py

RATE_LIMIT_WINDOW = 10  # 10초
RATE_LIMIT_COUNT = 10   # 10회

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

```

> 또는 Redis 사용 시:
> 

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

```

---

## ✅ 테스트 등록 예시

```python
MIDDLEWARE = [
    # ...
    'yourapp.middleware.RateLimitMiddleware',
]

```

---

## 🧪 테스트 확인

- 10초 이내에 10번 요청하면 모두 정상 (`200 OK`)
- 11번째 요청은 `429 Too Many Requests` 반환
- 10초가 지나면 다시 초기화

---

## ✅ 요약

| 설정 값 | 의미 |
| --- | --- |
| `window = 10` | 10초 동안의 시간 창 |
| `limit = 10` | 최대 허용 횟수 |
| `timeout = window` | 캐시 TTL = 윈도우 길이 (자동 만료) |

---

## 🔍 **단위 테스트 함수** 코드

✅ time.sleep(61) —> time.sleep(11)  # 10초 후로 수정 

```jsx
    def test_rate_limit_resets_after_window(self):
        for i in range(10):
            self.client.get('/')
        time.sleep(11)  # 10초 후 재요청
        response = self.client.get('/')
        self.assertNotEqual(response.status_code, 429)
```

## ✅ 결과

| 테스트 이름 | 기존 소요 시간 | 개선 후 |
| --- | --- | --- |
| rate limit 테스트 | 60초 이상 | 10초 이내 |

---

## 🧠 설명

```jsx
    def test_rate_limit_blocks_over_limit(self):
        for i in range(10):
            self.client.get('/')
        response = self.client.get('/')
        self.assertEqual(response.status_code, 429)
```

| 코드 | 설명 |
| --- | --- |
| `for _ in range(10):` | 10번 반복하여 GET 요청을 보냄. 이 횟수는 허용된 요청 한도 (`RATE_LIMIT_COUNT =` 10)에 해당. |
| `self.client.get('/')` | Django 테스트 클라이언트로 `/` 경로에 요청을 보냄. |
| `response = self.client.get('/')` | 11번째 요청. 앞서 10회 요청했으므로, 이 요청은 **Rate Limit을 초과한 요청** |
| `self.assertEqual(response.status_code, 429)` | 따라서 이 응답은 **429 상태코드**를 반환해야 테스트를 통과함 |

---

---

## 📌 테스트 결과

> 정상 요청 10회는 허용하고,
> 
> 
> **11번째 요청은 차단(429)** 되어야 한다는 것을 검증하는 테스트
> 

---

![md.png](md%201.png)

- postman에서 10초이내에 11번 send 버튼을 누른다.
    - 그러면 429 Too Many Requests 메시지가 나옴

![post.png](post.png)

- 브라우저에서 10초이내에 11번 send 버튼을 누른다.
    - 그러면 Rate limit exceeded. Try again later 메시지가 나옴

![db.png](db.png)

```jsx

    def __call__(self, request):
        ip = self.get_client_ip(request)
        now = time.time()
        key = f"rate-limit:{ip}"
        # window = 60  # 초
        # limit = 10   # 허용 횟수

        history = cache.get(key, [])
        history = [timestamp for timestamp in history if now - timestamp < self.window]

        if len(history) >= self.limit:
            return JsonResponse({"error": "Rate limit exceeded. Try again later."}, status=429)

        history.append(now)
        cache.set(key, history, timeout=self.window)

        return self.get_response(request)
```
