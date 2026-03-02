from django import forms
from django.contrib.auth.models import Group, User

from apps.menu.models import MenuCategory, MenuItem
from apps.restaurants.models import Restaurant


class StaffUserCreateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput())
    role = forms.ChoiceField(
        choices=[
            ('staff', 'Staff'),
            ('kitchen', 'Kitchen'),
            ('manager', 'Manager'),
        ]
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password', 'role')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = True
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            group, _ = Group.objects.get_or_create(name=self.cleaned_data['role'])
            user.groups.add(group)
        return user


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
        fields = ('restaurant', 'category', 'name', 'description', 'price', 'available')

    def clean(self):
        cleaned_data = super().clean()
        restaurant = cleaned_data.get('restaurant')
        category = cleaned_data.get('category')
        if restaurant and category and category.restaurant_id != restaurant.id:
            raise forms.ValidationError('Category must belong to selected restaurant.')
        return cleaned_data
