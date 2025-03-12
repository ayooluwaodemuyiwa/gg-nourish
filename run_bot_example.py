import os
import sys
from dotenv import load_dotenv

# Check if .env file exists
env_path = os.path.join(os.path.dirname(__file__), '.env')
if not os.path.exists(env_path):
    print("\033[91mError: .env file not found!\033[0m")
    print("Please create a .env file with your DISCORD_TOKEN and MISTRAL_API_KEY.")
    print("See env_setup_instructions.txt for details.")
    
    # For demo purposes only (without connecting to Discord)
    print("\n\033[93mDo you want to run a demo with sample tokens? (y/n)\033[0m")
    response = input().strip().lower()
    
    if response == 'y':
        # Set sample tokens for demo only
        os.environ['DISCORD_TOKEN'] = 'SAMPLE_TOKEN_FOR_DEMO'
        os.environ['MISTRAL_API_KEY'] = 'SAMPLE_KEY_FOR_DEMO'
        print("\033[93mRunning with sample tokens (bot won't actually connect to Discord)...\033[0m")
    else:
        sys.exit(1)
else:
    load_dotenv(env_path)

# This would normally start the bot
print("\033[92m=== GG Delivery Bot ===\033[0m")
print("Bot would be starting now with the following configuration:")
print(f"- Discord Token: {'*' * 10}{os.environ.get('DISCORD_TOKEN', '')[-5:] if len(os.environ.get('DISCORD_TOKEN', '')) > 5 else ''}")
print(f"- Mistral API Token: {'*' * 10}{os.environ.get('MISTRAL_API_KEY', '')[-5:] if len(os.environ.get('MISTRAL_API_KEY', '')) > 5 else ''}")
print("\nAvailable commands:")
print("- !help: Shows all available commands")
print("- !budget: Set your food budget")
print("- !address: Set your delivery address")
print("- !location: Set your default location")
print("- !restaurants: Search for restaurants")
print("- !menu: View a restaurant's menu")
print("- !recommend: Get food recommendations")
print("- !cart: View and manage your cart")
print("- !profile: View and edit your profile")
print("\nTo actually run the bot, create the .env file and run: python bot.py")
