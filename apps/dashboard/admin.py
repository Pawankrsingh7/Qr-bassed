from django.contrib import admin

from .models import EmployeeProfile


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'aadhaar_number', 'gender', 'dob')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'phone_number', 'aadhaar_number')
