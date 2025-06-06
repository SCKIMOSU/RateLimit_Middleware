from django.http import HttpResponseForbidden
from .models import AllowedIP, BlockedIPLog

class IPFirewallMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        allowed_ips = [ip.ip_address for ip in AllowedIP.objects.all()]
        remote_ip = self.get_client_ip(request)

        print("📌 요청한 클라이언트 IP:", remote_ip)
        print("✅ 현재 허용된 IP 목록:", allowed_ips)

        if remote_ip not in allowed_ips:
            BlockedIPLog.objects.create(ip_address=remote_ip, accessed_path=request.path)
            return HttpResponseForbidden(f"Access denied for IP: {remote_ip}")

        return self.get_response(request)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # IP가 여러 개일 수 있으므로 첫 번째 값 사용
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR') # 일반적인 경우
        return ip


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

#
# import time
# from django.core.cache import cache
# from django.http import JsonResponse
#
# from django.conf import settings
#
# # window = getattr(settings, "RATE_LIMIT_WINDOW", 60)
# # limit = getattr(settings, "RATE_LIMIT_COUNT", 10)
#
#
# class RateLimitMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response  #
#
#
#     def __call__(self, request):
#         ip = self.get_client_ip(request)
#         now = time.time()
#         key = f"rate-limit:{ip}"
#         # window = 60  # 초
#         # limit = 10  # 허용 횟수
#         window = getattr(settings, 'RATE_LIMIT_WINDOW', 60)
#         limit = getattr(settings, 'RATE_LIMIT_COUNT', 10)
#
#         history = cache.get(key, [])
#         history = [timestamp for timestamp in history if now - timestamp < window]
#
#         if len(history) >= limit:
#             return JsonResponse({"error": "Rate limit exceeded. Try again later."}, status=429)
#
#         history.append(now)
#         cache.set(key, history, timeout=window)
#
#         return self.get_response(request)
#
#     def get_client_ip(self, request):
#         x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
#         if x_forwarded_for:
#             return x_forwarded_for.split(",")[0]
#         return request.META.get("REMOTE_ADDR")
