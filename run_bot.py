import os
import logging
import time
import argparse
from dotenv import load_dotenv
from gg_nourish_agent import run_bot

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("gg_nourish.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('run_bot')

def print_welcome():
    """Print a welcome message with the bot's purpose"""
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║                           GG_NOURISH BOT                                   ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝

PURPOSE:
GG_Nourish is a Discord bot designed to help gamers maintain a healthy lifestyle
while enjoying their gaming sessions. The bot addresses the common health issues
faced by gamers, such as:

- Sedentary behavior and lack of physical activity
- Poor nutrition and unhealthy eating habits
- Eye strain and muscle fatigue from extended gaming sessions
- Difficulty balancing gaming with healthy lifestyle choices

FEATURES:
- Activity monitoring with break reminders
- Personalized food recommendations from Uber Eats
- Custom recipe generation based on available ingredients
- Quick workout routines that can be done between gaming sessions
- Health goal tracking and personalized advice
- Favorites tracking for restaurants and recipes

USAGE:
1. Invite the bot to your Discord server
2. Set your health goals with !healthgoal
3. Get food recommendations with !food
4. Take workout breaks with !workout
5. Track your progress with !stats

For testing the activity warning feature, use: !test activity
""")

# Check if environment variables are set
discord_token = os.getenv('DISCORD_TOKEN')
mistral_api_key = os.getenv('MISTRAL_API_KEY')
uber_eats_api_key = os.getenv('UBER_EATS_API_KEY')

print_welcome()
print("\nEnvironment Check:")
print("Discord token found:", bool(discord_token))
print("Mistral API key found:", bool(mistral_api_key))
print("Uber Eats API key found:", bool(uber_eats_api_key), "(Optional)")

if not discord_token:
    print("Warning: DISCORD_TOKEN not found in environment variables")
    
if not mistral_api_key:
    print("Warning: MISTRAL_API_KEY not found in environment variables")

def start_bot(test_mode=False):
    """Start the bot with auto-restart on failure"""
    max_retries = 5
    retry_count = 0
    retry_delay = 10  # seconds
    
    if test_mode:
        print("\n🧪 RUNNING IN TEST MODE 🧪")
        print("Activity warnings will be triggered after 60 minutes of activity")
        print("Use !test activity to simulate activity and trigger warnings")
        os.environ['ACTIVITY_WARNING_THRESHOLD_MINUTES'] = '60'
    
    while retry_count < max_retries:
        try:
            print(f"\nStarting bot (attempt {retry_count + 1}/{max_retries})...")
            run_bot()
            # If run_bot() completes without error, break the loop
            break
        except Exception as e:
            retry_count += 1
            logger.error(f"Bot crashed with error: {e}")
            print(f"Bot crashed with error: {e}")
            import traceback
            traceback.print_exc()
            
            if retry_count < max_retries:
                print(f"Restarting bot in {retry_delay} seconds...")
                time.sleep(retry_delay)
                # Increase delay for next retry
                retry_delay *= 2
            else:
                print("Maximum retry attempts reached. Bot will not restart automatically.")

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run the GG_Nourish Discord bot')
    parser.add_argument('--test', action='store_true', help='Run in test mode with shorter activity warning threshold')
    args = parser.parse_args()
    
    # Run the bot
    if discord_token:
        start_bot(test_mode=args.test)
    else:
        print("Error: Cannot start bot without DISCORD_TOKEN")
