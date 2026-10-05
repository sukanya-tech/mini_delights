from django import forms

from .models import Item


class AdminItemForm(forms.ModelForm):
	class Meta:
		model = Item
		fields = ('name', 'description', 'image', 'price', 'category', 'count')
		widgets = {
			'name': forms.TextInput(attrs={'placeholder': 'Item title', 'required': True}),
			'description': forms.Textarea(attrs={'placeholder': 'Describe the item', 'rows': 4}),
			'image': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
			'price': forms.NumberInput(attrs={'min': '0', 'step': '0.01', 'placeholder': '0.00', 'required': True}),
			'count': forms.NumberInput(attrs={'min': '0', 'step': '1', 'placeholder': '0', 'required': True}),
		}

	category = forms.ChoiceField(choices=(
		('home', 'Home'),
		('freshly-baked', 'Freshly Baked'),
		('desserts', 'Desserts'),
		('offers', 'Offers'),
	))

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['image'].required = not bool(self.instance.pk)
		self.fields['description'].required = False
