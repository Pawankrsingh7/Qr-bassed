from django.shortcuts import render


def kitchen_dashboard(request):
    return render(request, 'kitchen/dashboard.html')
