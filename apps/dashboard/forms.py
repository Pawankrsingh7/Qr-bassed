import secrets
import string

from django import forms
from django.contrib.auth.models import Group, User

from apps.menu.models import MenuCategory, MenuItem
from apps.restaurants.models import Restaurant

from .models import EmployeeProfile


def _generate_username(role: str, first_name: str, last_name: str) -> str:
    prefix = {
        'admin': 'ADM',
        'manager': 'MGR',
        'kitchen': 'KIT',
        'cashier': 'CSH',
        'waiter': 'WTR',
    }.get(role, 'USR')

    base = ''.join(ch for ch in f'{first_name}{last_name}'.upper() if ch.isalnum())[:4] or 'USER'
    while True:
        candidate = f'{prefix}{base}{secrets.randbelow(10000):04d}'
        if not User.objects.filter(username=candidate).exists():
            return candidate


def _generate_password(length: int = 10) -> str:
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


class StaffUserCreateForm(forms.Form):
    role = forms.ChoiceField(
        choices=[
            ('admin', 'Admin'),
            ('manager', 'Manager'),
            ('kitchen', 'Kitchen'),
            ('cashier', 'Cashier'),
            ('waiter', 'Staff/Waiter'),
        ]
    )
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    dob = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    gender = forms.ChoiceField(choices=EmployeeProfile.Gender.choices)
    phone_number = forms.CharField(max_length=20)
    email = forms.EmailField()
    aadhaar_number = forms.CharField(max_length=20)

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Email already exists.')
        return email

    def clean_aadhaar_number(self):
        aadhaar_number = ''.join(ch for ch in self.cleaned_data['aadhaar_number'] if ch.isdigit())
        if len(aadhaar_number) != 12:
            raise forms.ValidationError('Aadhaar must be 12 digits.')
        if EmployeeProfile.objects.filter(aadhaar_number=aadhaar_number).exists():
            raise forms.ValidationError('Aadhaar already exists.')
        return aadhaar_number

    def save(self):
        role = self.cleaned_data['role']
        username = _generate_username(role, self.cleaned_data['first_name'], self.cleaned_data['last_name'])
        temp_password = _generate_password()

        user = User.objects.create_user(
            username=username,
            password=temp_password,
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            email=self.cleaned_data['email'],
        )
        user.is_staff = True
        user.save(update_fields=['is_staff'])

        group, _ = Group.objects.get_or_create(name=role)
        user.groups.add(group)

        EmployeeProfile.objects.create(
            user=user,
            dob=self.cleaned_data['dob'],
            gender=self.cleaned_data['gender'],
            phone_number=self.cleaned_data['phone_number'],
            aadhaar_number=self.cleaned_data['aadhaar_number'],
        )

        return user, temp_password


class TableGenerateForm(forms.Form):
    restaurant = forms.ModelChoiceField(queryset=Restaurant.objects.filter(is_active=True))
    table_count = forms.IntegerField(min_value=1, max_value=500)


class MenuCategoryForm(forms.ModelForm):
    class Meta:
        model = MenuCategory
        fields = ('restaurant', 'name', 'display_order')


class MenuItemForm(forms.ModelForm):
    class Meta:
        model = MenuItem
        fields = ('restaurant', 'category', 'name', 'description', 'image_url', 'price', 'available')

    def clean(self):
        cleaned_data = super().clean()
        restaurant = cleaned_data.get('restaurant')
        category = cleaned_data.get('category')
        if restaurant and category and category.restaurant_id != restaurant.id:
            raise forms.ValidationError('Category must belong to selected restaurant.')
        return cleaned_data
