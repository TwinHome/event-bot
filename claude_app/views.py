from django.shortcuts import render,redirect
from django.shortcuts import render,redirect,get_object_or_404
from django.http import JsonResponse
from django.http import HttpResponseBadRequest
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, login
import re
from django.shortcuts import render, redirect
from .forms import YouTubeLinkForm
from youtube_transcript_api import YouTubeTranscriptApi
import re
from googleapiclient.discovery import build
import isodate
import nltk
import re
from datetime import datetime, timedelta
import anthropic
import os
from nltk.tokenize import sent_tokenize
import logging
from .models import Transcript, ChatHistory
from django.conf import settings
from .models import Transcript
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from .forms import QueryForm
import anthropic
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth import logout as django_logout


def youtube_custom_login_view(request):
    # Redirect authenticated users
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return HttpResponseRedirect(reverse_lazy("youtube_dashboard"))
        else:
            return HttpResponseRedirect(reverse_lazy("unauthorised"))

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = authenticate(username=form.cleaned_data['username'], password=form.cleaned_data['password'])
            if user is not None:
                login(request, user)
                return redirect(get_success_url(request))
            else:
                # Handle the case where authentication fails
                return render(request, "adminlogin.html", {'form': form})
        else:
            # Form is invalid
            return render(request, "adminlogin.html", {'form': form})
    else:
        # GET request, show the empty form
        form = AuthenticationForm()
        return render(request, "adminlogin.html", {'form': form})



def get_success_url(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return reverse_lazy("youtube_dashboard")
    else:
        return reverse_lazy("unauthorised")


from .forms import QueryForm, ChatHistoryForm
def youtube_dashboard_view(request):
    if not request.user.is_superuser:
        return redirect("unauthorised")

    user_transcripts = Transcript.objects.filter(user=request.user)
    context = {
        'transcripts': user_transcripts
    }
    return render(request, 'youtube_dashboard.html', context)


def chat_list_view(request, transcript_id):
    transcript = get_object_or_404(Transcript, id=transcript_id, user=request.user)
    chats = ChatHistory.objects.filter(transcript=transcript)
    return render(request, 'chat_list.html', {'transcript': transcript, 'chats': chats})




def edit_chat_view(request, chat_id):
    chat = get_object_or_404(ChatHistory, id=chat_id)
    if request.method == 'POST':
        form = ChatHistoryForm(request.POST, instance=chat)
        if form.is_valid():
            form.save()
            return redirect('chat_list',transcript_id=chat.transcript.id)
    else:
        form = ChatHistoryForm(instance=chat)
    return render(request, 'edit_chat.html', {'form': form})

def delete_chat_view(request, chat_id):
    chat = get_object_or_404(ChatHistory, id=chat_id)
    if request.method == 'POST':
        chat.delete()
        return redirect('chat_list',transcript_id=chat.transcript.id)
    return render(request, 'delete_chat.html', {'chat': chat})


def format_transcript(transcript_with_timestamps):
    formatted_transcript = []
    for start, end, text in transcript_with_timestamps:
        start_minutes, start_seconds = divmod(int(start), 60)
        end_minutes, end_seconds = divmod(int(end), 60)
        formatted_transcript.append(f"[{start_minutes:02d}:{start_seconds:02d} >
    return "\n".join(formatted_transcript)



def extract_video_id(youtube_url):
    # Handles both regular and shortened YouTube URLs
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11})(?:\?|&|$)',  # Regular YouTube URLs
        r'youtu\.be\/([0-9A-Za-z_-]{11})'            # Shortened YouTube URLs
    ]
    for pattern in patterns:
        video_id_match = re.search(pattern, youtube_url)
        if video_id_match:
            return video_id_match.group(1)
    raise ValueError("Invalid YouTube URL")





def get_video_details(video_id, api_key):
    youtube = build('youtube', 'v3', developerKey=api_key)

    request = youtube.videos().list(
        part="snippet,contentDetails",
        id=video_id
    )
    response = request.execute()

    if not response['items']:
        raise ValueError("Invalid video ID or video not found")

    video = response['items'][0]
    title = video['snippet']['title']
    description = video['snippet']['description']
    duration = isodate.parse_duration(video['contentDetails']['duration'])
    duration_str = str(duration)

    thumbnail_url = video['snippet']['thumbnails']['high']['url']

    return title, duration_str, description, thumbnail_url



def generate_summary(transcript_text):
    client = anthropic.Anthropic(api_key="")  # Replace with your actual API key
    response = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=150,
        temperature=0.7,
        system="You are a helpful assistant. Summarize the given text.",
        messages=[
            {"role": "user", "content": transcript_text}
        ]
    )
    if isinstance(response.content, list):
        reply_text = '\n'.join(block.text for block in response.content if hasattr(block, 'text'))
    elif hasattr(response.content, 'text'):
        reply_text = response.content.text
    else:
        reply_text = "Sorry, I couldn't process your request."



    return reply_text



def get_transcript(youtube_url, filename, api_key):
    try:
        video_id = extract_video_id(youtube_url)
        title, duration, description, thumbnail_url = get_video_details(video_id, api_key)
        transcript = YouTubeTranscriptApi.get_transcript(video_id)

        transcript_with_timestamps = []
        for i in range(len(transcript) - 1):
            start_time = transcript[i]['start']
            end_time = transcript[i + 1]['start']
            text = transcript[i]['text']
            transcript_with_timestamps.append((start_time, end_time, text))

        last_entry = transcript[-1]
        last_start = last_entry['start']
        last_duration = last_entry['duration']
        last_end = last_start + last_duration
        last_text = last_entry['text']
        transcript_with_timestamps.append((last_start, last_end, last_text))

        formatted_transcript = format_transcript(transcript_with_timestamps)

        # Ensure the transcripts/original directory exists
        transcripts_dir = os.path.join(settings.MEDIA_ROOT)
        os.makedirs(transcripts_dir, exist_ok=True)

        file_path = os.path.join(transcripts_dir, filename)

        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(f"Title: {title}\n")
            file.write(f"Duration: {duration}\n")
            file.write(f"Description: {description}\n")
            file.write(f"Thumbnail URL: {thumbnail_url}\n\n")
            file.write(formatted_transcript)

        summary = generate_summary(formatted_transcript)

        return {
            'video_id': video_id,
            'title': title,
            'duration': duration,
            'description': description,
            'thumbnail_url': thumbnail_url,
            'formatted_transcript': formatted_transcript,
            'file_path': file_path,
            'summary': summary
        }
    except Exception as e:
        print(f"An error occurred: {e}")
        return None



def transcript_view(request):
    api_key = ''
    if request.method == 'POST':
        form = YouTubeLinkForm(request.POST)
        if form.is_valid():
            youtube_url = form.cleaned_data['youtube_url']
            video_id = extract_video_id(youtube_url)
            filename = f'transcripts/original/transcript_{video_id}.txt'
            file_path = os.path.join(settings.MEDIA_ROOT, filename)

            # Ensure the directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Save original transcript
            # get_transcript(youtube_url, file_path,api_key)
            transcript_data = get_transcript(youtube_url, filename, api_key)

            # Create or update the transcript entry in the database
            if transcript_data:
                # Save the transcript and video details to the database
                transcript = Transcript.objects.create(
                    # original_file=filename,
                    video_id=transcript_data['video_id'],
                    original_file=f'{filename}',
                    title=transcript_data['title'],
                    duration=transcript_data['duration'],
                    description=transcript_data['description'],
                    thumbnail_url=transcript_data['thumbnail_url'],
                    summary=transcript_data['summary'],
                    user=request.user
                )
                transcript.save()
                with open(transcript_data['file_path'], 'r') as file:
                    content = file.read()
                # transcript.save()
                # return HttpResponse(content, content_type='text/plain')
                return redirect('index', transcript_id=transcript.id)
            else:
                return HttpResponse("An error occurred while processing the transcript.", content_type='text/plain')
        else:
            form = QueryForm()

            # Process transcript
            # full_transcript = read_transcript(file_path)
            # corrected_transcript = process_transcript_in_chunks(file_path)
            # processed_file_path = f"{os.path.splitext(file_path)[0]}_GPT{os.path.splitext(file_path)[1]}"
            # write_corrected_transcript(corrected_transcript, processed_file_path)

            # Save the processed transcript
            # transcript.processed_file = processed_file_path.replace(settings.MEDIA_ROOT + '/', '')
            # transcript.save()

            # Redirect to another view that could handle further interactions
            return redirect('index', transcript_id=transcript.id)
    else:
        form = YouTubeLinkForm()

    return render(request, 'transcript.html', {'form': form})





def index(request, transcript_id):
    transcript = get_object_or_404(Transcript, id=transcript_id)
    summary_full = transcript.summary
    summary_truncated = summary_full[:200] if len(summary_full) > 200 else summary_full
    context = {
        'transcript_id': transcript.id,
        'transcript': transcript,
        'summary_full': summary_full,
        'summary_truncated': summary_truncated,
    }
    return render(request, 'chatbot.html', context)



def chatbot_response(request, transcript_id):
    client = anthropic.Anthropic(api_key="")
    user_message = request.GET.get('message', '').strip()

    # Check if user_message is empty
    greetings_responses = {
        "hello": "Hello! How can I assist you today?",
        "hi": "Hi there! What can I do for you?",
        "hey": "Hey! How can I help you?",
        "greetings": "Greetings! How may I assist you?",
        "good morning": "Good morning! How can I assist you today?",
        "good afternoon": "Good afternoon! What can I help you with?",
        "good evening": "Good evening! How may I assist you?",
        "how are you": "I'm just a bot, but I'm here to help! How can I assist you?",
        "how are you doing": "I'm just a bot, but I'm here to help! How can I assist you?",
        "how's it going": "I'm just a bot, but I'm here to help! How can I assist you?"
    }

    # Check if the user message is a greeting
    if user_message in greetings_responses:
        return JsonResponse({"reply": greetings_responses[user_message]})

    try:
        transcript = Transcript.objects.get(id=transcript_id)
        transcript_file_path = transcript.original_file.path

        with open(transcript_file_path, 'r') as file:
            transcript_data = file.read()
    except Transcript.DoesNotExist:
        return JsonResponse({"reply": "Transcript not found."})
    except FileNotFoundError:
        return JsonResponse({"reply": "Transcript file not found."})

    # Prepare the response from the chatbot
    response = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=300,
        temperature=0,
        system="You are a helpful assistant. Keep the answer as concise as possible. Use the content of the file only; don't give answers from the internet. If you don't know the answer, just say 'I don't know'. Don't try to make up an answer. Respond in common words so that usage of language is easily understood by all age groups.",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_message
                    },
                    {
                        "type": "text",
                        "text": transcript_data  # Incorporate some part of the transcript into the context if needed
                    }
                ]
            }
        ]
    )

    # Handling response
    if isinstance(response.content, list):
        reply_text = '\n'.join(block.text for block in response.content if hasattr(block, 'text'))
    elif hasattr(response.content, 'text'):
        reply_text = response.content.text
    else:
        reply_text = "Sorry, I couldn't process your request."

    ChatHistory.objects.create(
        transcript=transcript,
        user_message=user_message,
        bot_reply=reply_text
    )

    return JsonResponse({"reply": reply_text})


def youtube_logout(request):
    django_logout(request)
    return redirect('youtube_admin_login')


