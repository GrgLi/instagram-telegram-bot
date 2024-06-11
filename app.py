import asyncio
import instaloader
from telegram import Bot
import schedule
import time
import os
import logging
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(filename='bot.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize Instagram loader
loader = instaloader.Instaloader()

# Initialize Telegram Bot
telegram_bot = Bot(token='YOUR TELEGRAM BOT TOKEN')

# Variable to store the last posted shortcode
last_posted_shortcode = ''

async def download_latest_post(username, num_posts_to_check=10):
    try:
        logging.info(f"Attempting to download the latest post from {username}.")
        
        # Load the profile
        profile = instaloader.Profile.from_username(loader.context, username)
        logging.info(f"Profile loaded: {profile.username}")

        # Iterate over the posts and find the most recent non-pinned post
        latest_post = None
        latest_time = datetime.min
        checked_posts = 0

        for post in profile.get_posts():
            if post.date_utc > latest_time:
                latest_time = post.date_utc
                latest_post = post
            
            checked_posts += 1
            # Stop if we have checked enough recent posts to bypass pinned posts
            if checked_posts >= num_posts_to_check:
                break

        if not latest_post:
            logging.error("No recent non-pinned posts found.")
            return None, None

        logging.info(f"Latest non-pinned post found: {latest_post.shortcode} at {latest_post.date_utc}")

        target_dir = 'latest_post'
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        # Clear out the target directory to avoid confusion with old files
        for filename in os.listdir(target_dir):
            file_path = os.path.join(target_dir, filename)
            if os.path.isfile(file_path):
                os.unlink(file_path)

        loader.download_post(latest_post, target=target_dir)
        logging.info(f"Downloaded post with shortcode: {latest_post.shortcode}")

        # Determine file paths
        image_path = None
        caption_path = None

        # Check downloaded files to find the image and caption
        for file in os.listdir(target_dir):
            if file.endswith('.jpg') or file.endswith('.png'):
                image_path = os.path.join(target_dir, file)
            if file.endswith('.txt'):
                caption_path = os.path.join(target_dir, file)

        if not image_path:
            logging.error(f"No image found for the latest post: {latest_post.shortcode}")

        if not caption_path:
            logging.info("No caption file found, will use default 'No caption available.'")

        return image_path, caption_path

    except Exception as e:
        logging.error(f"Error downloading the latest post: {e}")
        return None, None

async def send_post_to_telegram(chat_id, image_path, caption_path):
    try:
        # Read the caption from the file
        if caption_path and os.path.exists(caption_path):
            with open(caption_path, 'r', encoding='utf-8') as caption_file:
                caption = caption_file.read()
        else:
            caption = "No caption available."

        if image_path and os.path.exists(image_path):
            logging.info(f"Sending image {image_path} with caption to Telegram.")
            with open(image_path, 'rb') as photo:
                await telegram_bot.send_photo(chat_id=chat_id, photo=photo, caption=caption)
            logging.info("Post sent to Telegram successfully!")
        else:
            logging.error(f"Image file not found: {image_path}")

    except Exception as e:
        logging.error(f"Error sending post to Telegram: {e}")

def job():
    try:
        global last_posted_shortcode
        image_path, caption_path = asyncio.run(download_latest_post('INSTAGRAM ACCOUNT'))
        
        if image_path and caption_path:
            # Extract the shortcode from the image file name (assuming it's part of the filename)
            shortcode = os.path.basename(image_path).split('_')[0]
            if shortcode != last_posted_shortcode:
                asyncio.run(send_post_to_telegram('YOUR TELEGRAM CHANNEL ID', image_path, caption_path))
                last_posted_shortcode = shortcode  # Update the last posted shortcode
            else:
                logging.info("No new posts to send.")
    except Exception as e:
        logging.error(f"Error during job execution: {e}")

# Schedule the job to run every 5 minutes
schedule.every(5).minutes.do(job)

# Keep the script running
logging.info("Bot started, running every 5 minutes.")
while True:
    schedule.run_pending()
    time.sleep(1)
