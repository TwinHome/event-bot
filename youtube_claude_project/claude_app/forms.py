from django import forms

class YouTubeLinkForm(forms.Form):
    youtube_url = forms.URLField(
        label='YouTube URL',
        max_length=200,
        widget=forms.URLInput(attrs={
            'class': 'form-control mt-3',
            'placeholder': 'Enter YouTube URL'
        })
    )


class QueryForm(forms.Form):
    query = forms.CharField(label='Your Question', max_length=1000)



from .models import ChatHistory
class ChatHistoryForm(forms.ModelForm):
    class Meta:
        model = ChatHistory
        fields = ['user_message', 'bot_reply']
