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




# import time
# from django.test import TestCase, Client, override_settings
#
#
# @override_settings(
#     RATE_LIMIT_WINDOW=2,  # 테스트용 작은 시간창
#     RATE_LIMIT_COUNT=3,
#     CACHES={
#         'default': {
#             'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
#         }
#     }
# )
# class RateLimitMiddlewareTest(TestCase):
#     def setUp(self):
#         self.client = Client(REMOTE_ADDR='127.0.0.1')
#
#     def test_rate_limit_allows_under_limit(self):
#         for i in range(3):
#             response = self.client.get('/')
#             self.assertNotEqual(response.status_code, 429, f"Request {i + 1} failed early")
#
#     def test_rate_limit_blocks_over_limit(self):
#         for i in range(2):
#             response = self.client.get('/')
#             self.assertNotEqual(response.status_code, 429)
#         response = self.client.get('/')
#         self.assertEqual(response.status_code, 429)
#         #self.assertIn("Rate limit exceeded", response.json()["error"])
#
#     # def test_rate_limit_resets_after_window(self):
#     #     for i in range(10):
#     #         self.client.get('/')
#     #     time.sleep(61)  # 60초 후 재요청
#     #     response = self.client.get('/')
#     #     self.assertNotEqual(response.status_code, 429)


