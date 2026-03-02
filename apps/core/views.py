from django.shortcuts import redirect, render


def home(request):
    return render(request, 'core/home.html')


def order_scan_entry(request):
    return redirect('/')
