from django.http import HttpResponse

def index(request):
    return HttpResponse("Welcome! Your IP is allowed.")
