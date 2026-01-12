"""
Email HTML templates for FixionMail.
"""

import os
from typing import Optional


def render_story_email(
    title: str,
    narrative: str,
    cover_image_url: Optional[str] = None,
    audio_url: Optional[str] = None,
    genre: str = "fiction",
    word_count: int = 0
) -> str:
    """
    Generate HTML email content for a story delivery.

    Args:
        title: Story title
        narrative: Full story text
        cover_image_url: URL to cover image (optional)
        audio_url: URL to audio narration (optional)
        genre: Story genre
        word_count: Word count for display

    Returns:
        HTML string for email
    """
    base_url = os.getenv("APP_BASE_URL", "http://localhost:8000").rstrip('/')

    # Image section
    image_section = ""
    if cover_image_url:
        full_image_url = cover_image_url if cover_image_url.startswith('http') else f"{base_url}/{cover_image_url.lstrip('/')}"
        image_section = f'''
        <div style="margin: 30px 0; text-align: center;">
          <img src="{full_image_url}" alt="{title}"
               style="width: 100%; max-width: 600px; height: auto; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.15);">
        </div>
        '''

    # Audio section
    audio_section = ""
    if audio_url:
        full_audio_url = audio_url if audio_url.startswith('http') else f"{base_url}/{audio_url.lstrip('/')}"
        audio_section = f'''
        <div style="margin: 30px 0; padding: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 16px;">
          <div style="text-align: center; margin-bottom: 20px;">
            <h3 style="color: white; margin: 0 0 8px 0; font-size: 20px;">Listen to Your Story</h3>
            <p style="margin: 0; font-size: 14px; color: rgba(255,255,255,0.9);">Professional narration</p>
          </div>
          <div style="text-align: center; margin-bottom: 20px;">
            <a href="{full_audio_url}" target="_blank"
               style="display: inline-block; background: white; color: #667eea; padding: 16px 40px; border-radius: 50px; text-decoration: none; font-weight: 700; font-size: 16px;">
              Play Audio
            </a>
          </div>
          <div style="background: rgba(255,255,255,0.15); border-radius: 12px; padding: 20px;">
            <audio controls style="width: 100%; height: 40px;">
              <source src="{full_audio_url}" type="audio/mpeg">
            </audio>
          </div>
        </div>
        '''

    # Format story paragraphs
    paragraphs = narrative.split('\n\n')
    formatted_story = ''.join([
        f'<p style="margin: 0 0 24px 0; font-size: 18px; line-height: 1.8; color: #2d2d2d;">{p.strip()}</p>'
        for p in paragraphs if p.strip()
    ])

    reading_time = max(1, round(word_count / 200)) if word_count > 0 else 5

    return f'''
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; font-family: Georgia, serif; background: #f8f9fa;">
      <div style="max-width: 700px; margin: 0 auto; padding: 40px 20px;">
        <!-- Header -->
        <div style="text-align: center; margin-bottom: 40px;">
          <div style="display: inline-block; background: white; padding: 12px 24px; border-radius: 30px; margin-bottom: 20px;">
            <p style="margin: 0; font-size: 13px; color: #6c757d; text-transform: uppercase; letter-spacing: 2px; font-weight: 600;">
              {genre.upper()}
            </p>
          </div>
          <h1 style="color: #1a1a1a; margin: 0 0 12px 0; font-size: 42px; font-weight: 700;">
            {title}
          </h1>
          <p style="margin: 0; font-size: 15px; color: #6c757d;">
            {word_count:,} words - {reading_time} min read
          </p>
        </div>

        {image_section}
        {audio_section}

        <!-- Story Content -->
        <div style="background: white; border-radius: 16px; padding: 60px 50px; margin: 30px 0;">
          {formatted_story}
        </div>

        <!-- Footer -->
        <div style="text-align: center; margin-top: 50px; padding: 40px 30px; background: white; border-radius: 16px;">
          <p style="margin: 0 0 12px 0; font-size: 18px; color: #1a1a1a; font-weight: 600;">
            Enjoyed this story?
          </p>
          <p style="margin: 0 0 20px 0; font-size: 15px; color: #6c757d;">
            You'll receive a new story tomorrow.
          </p>
          <div style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 12px 32px; border-radius: 25px;">
            <p style="margin: 0; font-size: 13px; color: white; font-weight: 600;">FIXION MAIL</p>
          </div>
        </div>

        <p style="text-align: center; color: #adb5bd; font-size: 12px; margin-top: 30px;">
          FixionMail - Daily Stories Delivered to Your Inbox
        </p>
      </div>
    </body>
    </html>
    '''
