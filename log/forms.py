from django import forms
from django.utils.safestring import mark_safe
from django.utils import timezone
import datetime

class weblog_userForm(forms.Form):
    nickname = forms.CharField(label='', initial="Nickname", widget=forms.TextInput(attrs={
        'required' : False,
        'id' : False,
        'onfocus' : mark_safe("if(this.value=='Nickname'){this.value='';}"),
        'onblur' : mark_safe("if(!this.value){this.value='Nickname';}"),
    }))
    password = forms.CharField(label='', initial="Password", widget=forms.PasswordInput(render_value=True, attrs={
        'required' : False,
        'id' : False,
        'onfocus' : mark_safe("if(this.value=='Password'){this.value='';}"),
        'onblur' : mark_safe("if(!this.value){this.value='Password';}"),
    }))
    message = forms.CharField(label='', initial="Message...", widget=forms.TextInput(attrs={
        'required' : False,
        'id' : False,
        'onfocus' : mark_safe("if(this.value=='Message...'){this.value='';}"),
        'onblur' : mark_safe("if(!this.value){this.value='Message...';}"),
    }))

class weblog_dlForm(forms.Form):
    date = forms.DateField(widget=forms.SelectDateWidget(
        years=(list(reversed(range(2015,datetime.datetime.now().year+1)))),
        ),
        initial=datetime.date.today,
    )
    format_choices = (
        ('html', 'HTML'),
        ('json', 'JSON'),
        ('xml', 'XML'),
        ('yaml', 'YAML'),
    )
    log_format = forms.ChoiceField(choices=format_choices)
