import base64
import io
import logging
import time

import requests

logger = logging.getLogger(__name__)

PROMPT = (
    "You are a navigation assistant for a visually impaired person inside their home. "
    "Analyze this image and in 2-3 short sentences:\n"
    "1) Name any obstacles and say if they are near (<1m), medium (1-3m), or far (>3m).\n"
    "2) State the safest direction to move: left, right, or straight.\n"
    "3) Flag any critical hazards: stairs going down, knives, open doors.\n"
    "Be calm and direct. Plain sentences only — no markdown, no preamble."
)


class VisionAgent:
    """
    Free AI Vision Agent — two providers, no local model required.

      1. Gemini 1.5 Flash   1,500 req/day free   https://aistudio.google.com/app/apikey
      2. Mistral Pixtral    unlimited, 2 RPM free https://console.mistral.ai

    Add keys to your .env file:
        GEMINI_API_KEY=your_key_here
        MISTRAL_API_KEY=your_key_here

    The agent runs every AGENT_INTERVAL_SECONDS (default 15s).
    YOLO handles all buzzer alerts every frame regardless of agent status.
    If both keys are missing or both calls fail, detection still works normally.
    """

    def __init__(self):
        from django.conf import settings
        self.gemini_key  = getattr(settings, 'GEMINI_API_KEY',  '')
        self.mistral_key = getattr(settings, 'MISTRAL_API_KEY', '')
        self.interval    = getattr(settings, 'AGENT_INTERVAL_SECONDS', 15)
        self._last       = 0

        # Log provider status at startup
        active = []
        if self.gemini_key:  active.append('Gemini')
        if self.mistral_key: active.append('Mistral')
        if active:
            logger.info('✅ Vision agent ready — providers: %s', ', '.join(active))
        else:
            logger.warning(
                '⚠️  No AI agent keys found in .env. '
                'Add GEMINI_API_KEY or MISTRAL_API_KEY. '
                'YOLO detection works fine without them.'
            )

    def ready(self):
        return (time.time() - self._last) >= self.interval

    def analyze(self, image_bytes):
        """
        Try Gemini first, fall back to Mistral.
        Returns (description: str | None, provider: str | None).
        """
        if not self.ready():
            return None, None

        if not self.gemini_key and not self.mistral_key:
            return None, None

        result, provider = (
            self._gemini(image_bytes)  or
            self._mistral(image_bytes) or
            (None, None)
        )

        if result:
            self._last = time.time()
            logger.info('Agent [%s]: %s', provider, result[:100])

        return result, provider

    # Provider 1: Gemini 1.5 Flash
    # Free tier: 1,500 requests/day, 15 RPM
    # Get key: https://aistudio.google.com/app/apikey
    def _gemini(self, img_bytes):
        if not self.gemini_key:
            return None
        try:
            import google.generativeai as genai
            from PIL import Image as PILImage
            genai.configure(api_key=self.gemini_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            img   = PILImage.open(io.BytesIO(img_bytes))
            resp  = model.generate_content(
                [PROMPT, img],
                generation_config={'max_output_tokens': 150}
            )
            t = resp.text.strip()
            return (t, 'Gemini') if t else None
        except Exception as e:
            logger.warning('Gemini failed: %s', e)
            return None

    # Provider 2: Mistral Pixtral
    # Free tier: unlimited requests, 2 requests per minute
    # Get key: https://console.mistral.ai
    def _mistral(self, img_bytes):
        if not self.mistral_key:
            return None
        try:
            b64  = base64.b64encode(img_bytes).decode()
            resp = requests.post(
                'https://api.mistral.ai/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {self.mistral_key}',
                    'Content-Type':  'application/json',
                },
                json={
                    'model': 'pixtral-12b-2409',
                    'messages': [{
                        'role': 'user',
                        'content': [
                            {'type': 'text',      'text': PROMPT},
                            {'type': 'image_url', 'image_url': f'data:image/jpeg;base64,{b64}'},
                        ]
                    }],
                    'max_tokens': 150,
                },
                timeout=12
            )
            resp.raise_for_status()
            t = resp.json()['choices'][0]['message']['content'].strip()
            return (t, 'Mistral') if t else None
        except Exception as e:
            logger.warning('Mistral failed: %s', e)
            return None
