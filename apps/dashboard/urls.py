from django.urls import path

from .views import admin_dashboard, payment_detail, report_export_csv, report_export_pdf, session_bill_print, staff_user_detail

app_name = 'dashboard'

urlpatterns = [
    path('', admin_dashboard, name='overview'),
    path('users/<int:user_id>/', staff_user_detail, name='user-detail'),
    path('payments/<int:payment_id>/', payment_detail, name='payment-detail'),
    path('sessions/<int:session_id>/print-bill/', session_bill_print, name='print-bill'),
    path('reports/export/csv/', report_export_csv, name='report-export-csv'),
    path('reports/export/pdf/', report_export_pdf, name='report-export-pdf'),
]
