import json
from google.api_core.exceptions import GoogleAPICallError
from google.cloud import speech, translate_v2 as translate
from google.cloud.speech import RecognitionConfig, RecognitionAudio
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

@csrf_exempt
@require_http_methods(["POST"])
def record(request):
    """
    Handles start/stop recording requests.
    For now, this function will simply log the action.
    Actual audio recording will be handled on the client side.
    """

    try:
        data = json.loads(request.body)
        action = data.get("action")
        language_mode = data.get("language_mode")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if action not in ["start", "stop"]:
        return JsonResponse({"error": "Invalid action"}, status=400)

    return JsonResponse({"message": f"Recording {action}ed in {language_mode} mode"}, status=200)


@csrf_exempt
@require_http_methods(["POST"])
def process_and_translate(request):
    try:
        audio_file = request.FILES.get('audio')
        if not audio_file:
            return JsonResponse({"error": "No audio file provided"}, status=400)

        language_mode = request.POST.get('language_mode', 'Any')

        # Initialize Google Cloud Speech client
        speech_client = speech.SpeechClient()

        # Prepare the audio file
        audio_content = audio_file.read()
        audio = RecognitionAudio(content=audio_content)

        # Set language code for English and Taiwanese
        language_code = 'en-US' if language_mode == 'English' else 'zh-TW'
        target_language = 'zh-TW' if language_mode == 'English' else 'en'

        # Create a RecognitionConfig
        config = RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.FLAC,
            sample_rate_hertz=0,  # Auto-detect sample rate
            enable_automatic_punctuation=True,
            model='default',
            language_code=language_code,
        )

        # If language_mode is 'Any', try both English and Taiwanese
        if language_mode == 'Any':
            print("im in language any")
            # Try English
            config.language_code = 'en-US'
            response_en = speech_client.recognize(config=config, audio=audio)

            # Try Taiwanese
            config.language_code = 'zh-TW'
            response_tw = speech_client.recognize(config=config, audio=audio)

            # Choose the response with the highest confidence
            if response_en.results and response_tw.results:
                confidence_en = response_en.results[0].alternatives[0].confidence
                confidence_tw = response_tw.results[0].alternatives[0].confidence
                if confidence_en > confidence_tw:
                    response = response_en
                    language_code = 'en-US'
                    target_language = 'zh-TW'
                else:
                    response = response_tw
                    language_code = 'zh-TW'
                    target_language = 'en'
            elif response_en.results:
                response = response_en
                language_code = 'en-US'
                target_language = 'zh-TW'
            elif response_tw.results:
                response = response_tw
                language_code = 'zh-TW'
                target_language = 'en'
            else:
                return JsonResponse({"error": "Speech recognition failed"}, status=500)
        else:
            # Perform speech recognition
            response = speech_client.recognize(config=config, audio=audio)
            if not response.results:
                return JsonResponse({"error": "Speech recognition failed"}, status=500)

        recognized_text = response.results[0].alternatives[0].transcript

        # Initialize Google Cloud Translation client
        translate_client = translate.Client()

        # Translate the text
        translation = translate_client.translate(
            recognized_text, target_language=target_language)
        translated_text = translation['translatedText']

        # Return response
        return JsonResponse({
            "detected_language": language_code,
            "processed_text": recognized_text,
            "translated_text": translated_text
        }, status=200)

    except GoogleAPICallError as e:
        return JsonResponse({"error": "Google API call failed: " + str(e)}, status=500)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)