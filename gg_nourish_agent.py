import os
import json
import asyncio
import discord
from discord import app_commands
from discord.ui import Button, View, Select
import logging
from dotenv import load_dotenv
from mistralai.client import MistralClient
from datetime import datetime
from modules.workout_ui_server import WorkoutUIServer
from datetime import timedelta

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('gg_nourish')

# Import our modules
from modules.user_data_manager import UserDataManager
from modules.food_module import FoodModule
from modules.fitness_module import FitnessModule

# Load environment variables
load_dotenv()

# Constants
MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY')
MISTRAL_MODEL = "mistral-large-latest"
DATA_FILE_PATH = "user_data.json"
ACTIVITY_WARNING_THRESHOLD_MINUTES = 60  # 1 hour in minutes (for testing)

class GGNourishAgent(discord.Client):
    def __init__(self, *args, **kwargs):
        # We'll use the intents from kwargs if provided, otherwise create default intents
        if 'intents' not in kwargs:
            intents = discord.Intents.default()
            intents.message_content = True
            intents.members = True
            kwargs['intents'] = intents
        
        super().__init__(*args, **kwargs)
        
        # Initialize Mistral client
        self.mistral_client = MistralClient(api_key=MISTRAL_API_KEY) if MISTRAL_API_KEY else None
        if self.mistral_client:
            logger.info("Mistral client initialized successfully")
        else:
            logger.warning("Mistral client not initialized - API key not found")
        
        # Initialize user data manager
        self.user_data_manager = UserDataManager(DATA_FILE_PATH)
        
        # Initialize modules
        self.food_module = FoodModule(self.mistral_client, self.user_data_manager)
        self.fitness_module = FitnessModule(self.mistral_client, self.user_data_manager)
        
        # Initialize workout UI server
        self.workout_ui_server = WorkoutUIServer()
        
        # We'll start the activity reminder task in setup_hook
        self.activity_reminder_task = None
        
    async def setup_hook(self):
        """This is called when the client is done preparing data"""
        logger.info("Setting up activity reminder task")
        # Start the activity reminder task
        self.activity_reminder_task = self.loop.create_task(self.check_user_activity())
        
        logger.info("Starting workout UI server")
        # Start the workout UI server
        await self.workout_ui_server.start()
        
    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info(f'{self.user} has connected to Discord!')
        
        # Set the bot's status
        await self.change_presence(activity=discord.Game(name="!help for commands"))
        
        # Initialize the workout UI server
        if not hasattr(self, 'workout_ui_server') or not self.workout_ui_server:
            self.workout_ui_server = WorkoutUIServer()
        
        # Start the activity reminder task
        self.activity_reminder_task = self.loop.create_task(self.check_user_activity())
        
        # Send startup messages to all guilds
        startup_header = """
```
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║                           GG_NOURISH BOT                                   ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
```

# 🎮 Welcome to GG_Nourish! 🥗

## What is GG_Nourish?
GG_Nourish is a specialized Discord bot designed for gamers who want to maintain a healthy lifestyle while enjoying their gaming sessions. The bot monitors your activity, provides personalized nutrition advice, and offers quick exercise breaks to prevent health issues associated with long gaming sessions.
"""

        startup_features = """
## Main Features:
• **Activity Monitoring**: Automatically detects when you've been gaming too long and suggests breaks
• **Food Recommendations**: Get personalized food suggestions based on your preferences
• **Uber Eats Integration**: Find healthy restaurants near you with `!order [location]`
• **Recipe Generator**: Create recipes from ingredients you already have
• **Fitness Plans**: Receive customized workout routines that fit your gaming schedule
• **Workout Timer**: Follow guided 10-minute exercise breaks between gaming sessions
"""

        startup_getting_started = """
## How to Get Started:
1. Type `!start` to begin your health journey
2. Set your health goal with `!healthgoal [your goal]`
3. Explore food options with `!food [preference]` or `!order [location]`
4. Try a quick workout with `!workout`

## Why GG_Nourish?
Studies show that gamers often neglect their health during intense gaming sessions. GG_Nourish helps by:
- Reminding you to take breaks after extended gaming periods
- Providing quick, healthy food options that don't interrupt your gaming flow
- Offering short exercise routines designed specifically for gamers
- Tracking your health progress over time
"""

        startup_food_ordering = """
## How to Order Food with Uber Eats:
1. Set your health goal with `!healthgoal [your goal]`
2. Use `!order [your location]` (e.g., `!order San Francisco, CA`)
3. View restaurant recommendations based on your health goal
4. Open Uber Eats app/website and search for the recommended restaurant
5. Choose healthy menu items that align with your goals

## Need Help?
Type `!help` at any time to see all available commands.

Ready to level up your health while gaming? Type `!start` to begin!
"""
        
        # Send to the first channel in each guild
        for guild in self.guilds:
            sent = False
            for channel in guild.text_channels:
                # Check if we have permission to send messages in this channel
                if channel.permissions_for(guild.me).send_messages:
                    try:
                        await channel.send(startup_header)
                        await channel.send(startup_features)
                        await channel.send(startup_getting_started)
                        await channel.send(startup_food_ordering)
                        sent = True
                        break
                    except Exception as e:
                        logger.error(f"Failed to send startup message to {channel.name} in {guild.name}: {e}")
            
            if not sent:
                logger.warning(f"Could not send startup message to any channel in {guild.name}")
    
    async def on_message(self, message):
        """Called when a message is sent in a channel the bot can see"""
        # Ignore messages from the bot itself
        if message.author == self.user:
            return
            
        # Get user's name for personalized responses
        user_name = message.author.display_name
        user_id = str(message.author.id)
            
        # Update user activity timestamp
        self.user_data_manager.update_user_activity(user_id)
        
        # Process commands
        if message.content.startswith('!'):
            await self.process_command(message, user_name, user_id)
        else:
            # Process conversation with Mistral
            await self.process_conversation(message, user_name, user_id)
            
    async def process_command(self, message, user_name, user_id):
        """Process a command message"""
        content = message.content.strip()
        # Split by the first space
        parts = content.split(' ', 1)
        command = parts[0][1:].lower()  # Remove the ! and convert to lowercase
        args = parts[1] if len(parts) > 1 else ""
        
        # Process different commands
        if command == 'help':
            await self.send_help_message(message.channel, user_name)
        elif command == 'start':
            await self.send_start_message(message.channel, user_id, user_name)
        elif command == 'healthgoal':
            await self.process_health_goal_command(message, args, user_id, user_name)
        elif command == 'stats':
            await self.process_stats_command(message, user_id, user_name)
        elif command == 'food':
            await self.process_food_command(message, args, user_id, user_name)
        elif command == 'recipe':
            await self.process_recipe_command(message, args, user_id, user_name)
        elif command == 'fitnessplan':
            await self.process_fitness_plan_command(message, user_id, user_name)
        elif command == 'workout':
            await self.process_workout_command(message, user_id, user_name)
        elif command == 'order':
            await self.process_order_command(message, args, user_id, user_name)
        elif command == 'diet' or command == 'dietary':
            await self.process_dietary_command(message, args, user_id, user_name)
        elif command == 'addfavorite':
            await self.process_add_favorite_command(message, args, user_id, user_name)
        elif command == 'favorites':
            await self.process_favorites_command(message, user_id, user_name)
        elif command == 'test':
            await self.process_test_command(message, args, user_id, user_name)
        else:
            await message.channel.send(f"Sorry {user_name}, I don't recognize that command. Type `!help` for a list of commands.")
    
    async def process_conversation(self, message, user_name, user_id):
        """Process a conversation message using Mistral AI"""
        # Skip if Mistral client is not available
        if not self.mistral_client:
            return
            
        user_message = message.content
        
        # Get user data
        user_data = self.user_data_manager.get_user_data(user_id)
        health_goal_data = user_data.get('health_goal', {})
        
        # Extract health goal text, handling both dictionary and string formats
        if isinstance(health_goal_data, dict):
            health_goal = health_goal_data.get('primary', '')
        else:
            health_goal = str(health_goal_data) if health_goal_data else ''
        
        # Get dietary preferences
        dietary_preferences = user_data.get('dietary_preferences', {})
        diet_restrictions = []
        allergies = []
        diets = []
        
        if dietary_preferences:
            if 'allergies' in dietary_preferences:
                allergies = dietary_preferences['allergies']
                diet_restrictions.extend(allergies)
            if 'diets' in dietary_preferences:
                diets = dietary_preferences['diets']
                diet_restrictions.extend(diets)
                
        # Log dietary restrictions
        if diet_restrictions:
            logger.info(f"Including dietary restrictions in conversation for user {user_id}: {diet_restrictions}")
        
        # Create system message for Mistral
        system_message = f"""You are GG_Nourish, a friendly and supportive health assistant for gamers.

USER INFO:
- Name: {user_name}
- Health Goal: {health_goal if health_goal else "Not specified yet"}
"""

        # Add dietary restrictions section - ALWAYS include this section even if empty
        system_message += f"""
**DIETARY RESTRICTIONS - CRITICALLY IMPORTANT:**
"""

        if allergies:
            system_message += f"""
- FOOD ALLERGIES: {', '.join(allergies)}
  ***WARNING: Never recommend foods containing these allergens - this is a safety issue***
"""
        else:
            system_message += "- No known food allergies\n"

        if diets:
            system_message += f"""
- DIETARY PREFERENCES: {', '.join(diets)}
  ***Always respect these dietary preferences in ALL recommendations***
"""
        else:
            system_message += "- No specific dietary preferences\n"
            
        system_message += """
INSTRUCTIONS:
1. Be conversational and personable - address the user by name
2. Provide health, nutrition, and fitness advice tailored for gamers
3. Keep your responses concise but helpful
4. If the user asks about commands, remind them of the !help command
5. If they ask about food, suggest using !food or !recipe commands
6. If they ask about fitness, suggest using !fitnessplan or !workout commands
7. If they ask about ordering food, suggest using !order command
8. NEVER suggest foods that conflict with the user's dietary restrictions
9. ALWAYS be mindful of the user's dietary needs in ANY food-related discussion

Your personality: Friendly, supportive, understanding of gamer lifestyle, encouraging but not pushy
"""

        try:
            # Send a typing indicator while generating
            async with message.channel.typing():
                response = self.mistral_client.chat(
                    model=MISTRAL_MODEL,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": user_message}
                    ]
                )
                
                ai_response = response.choices[0].message.content
                
                # Split message if it's too long
                if len(ai_response) > 1900:
                    parts = self.split_message(ai_response)
                    for part in parts:
                        await message.channel.send(part)
                else:
                    await message.channel.send(ai_response)
                
        except Exception as e:
            logger.error(f"Error processing conversation: {e}")
            await message.channel.send(f"Sorry {user_name}, I'm having trouble understanding right now. Try using a command like !help to see what I can do.")
    
    async def process_health_goal_command(self, message, args, user_id, user_name):
        """Process the !healthgoal command"""
        if not args:
            await message.channel.send("Please specify your health goal. For example: `!healthgoal lose weight while gaming` or `!healthgoal build muscle`")
            return
            
        # Save the health goal in a consistent dictionary format
        user_data = self.user_data_manager.get_user_data(user_id)
        user_data['health_goal'] = {
            'primary': args,
            'set_at': datetime.now().isoformat()
        }
        self.user_data_manager.save_user_data(user_id, user_data)
        
        # Generate a response using Mistral AI
        try:
            response = self.mistral_client.chat(
                model="mistral-tiny",
                messages=[
                    {"role": "system", "content": "You are a health assistant for gamers. Be encouraging and positive."},
                    {"role": "user", "content": f"I'm a gamer and my health goal is: {args}. Give me a brief, encouraging response and 2-3 specific tips tailored to this goal that I can implement while maintaining my gaming hobby."}
                ]
            )
            
            health_response = response.choices[0].message.content
            await message.channel.send(f"Hey {user_name}, I've saved your health goal: **{args}**\n\n{health_response}")
            
        except Exception as e:
            logger.error(f"Error generating health goal response: {e}")
            await message.channel.send(f"Hey {user_name}, I've saved your health goal: **{args}**\n\nI'll help you achieve this goal with personalized recommendations!")
    
    async def process_stats_command(self, message, user_id, user_name):
        """Process the !stats command to show user health statistics and progress"""
        # Get user data
        user_data = self.user_data_manager.get_user_data(user_id)
        
        # Check if user has started their health journey
        if not user_data.get('started', False):
            await message.channel.send(f"Hey {user_name}, you haven't started your health journey yet! Use `!start` to begin.")
            return
            
        # Extract health goal
        health_goal_data = user_data.get('health_goal', {})
        if isinstance(health_goal_data, dict):
            health_goal = health_goal_data.get('primary', 'Not set')
        else:
            health_goal = str(health_goal_data) if health_goal_data else 'Not set'
            
        # Get start date
        start_date_str = user_data.get('start_date', None)
        days_active = 0
        if start_date_str:
            try:
                start_date = datetime.fromisoformat(start_date_str)
                days_active = (datetime.now() - start_date).days + 1
            except:
                days_active = 0
                
        # Get workout stats
        total_workouts = len(user_data.get('workout_history', []))
        last_workout_time = user_data.get('last_workout_time', None)
        last_workout_str = "Never"
        if last_workout_time:
            try:
                last_workout = datetime.fromisoformat(last_workout_time)
                # Format as "X days ago" or "Today" or "Yesterday"
                days_since = (datetime.now() - last_workout).days
                if days_since == 0:
                    last_workout_str = "Today"
                elif days_since == 1:
                    last_workout_str = "Yesterday"
                else:
                    last_workout_str = f"{days_since} days ago"
            except:
                last_workout_str = "Unknown"
                
        # Create stats embed
        embed = discord.Embed(
            title=f"📊 Health Stats for {user_name}",
            description=f"Here's your health journey progress!",
            color=0x00ff00
        )
        
        # Add fields to embed
        embed.add_field(name="🎯 Health Goal", value=health_goal, inline=False)
        embed.add_field(name="📅 Days Active", value=str(days_active), inline=True)
        embed.add_field(name="💪 Total Workouts", value=str(total_workouts), inline=True)
        embed.add_field(name="⏱️ Last Workout", value=last_workout_str, inline=True)
        
        # Add fitness plan if available
        if 'fitness_plan' in user_data:
            embed.add_field(name="🏋️ Fitness Plan", value="You have a personalized fitness plan! Use `!fitnessplan` to view it.", inline=False)
            
        # Add dietary preferences if available
        dietary_prefs = user_data.get('dietary_preferences', [])
        if dietary_prefs:
            embed.add_field(name="🥗 Dietary Preferences", value=", ".join(dietary_prefs), inline=False)
            
        # Add footer
        embed.set_footer(text="Keep up the great work! 💪")
        
        await message.channel.send(embed=embed)
        
    async def process_dietary_command(self, message, args, user_id, user_name):
        """Process the !dietary command to set dietary preferences"""
        user_data = self.user_data_manager.get_user_data(user_id)
        
        # If no args, show current dietary preferences
        if not args:
            dietary_prefs = user_data.get('dietary_preferences', [])
            
            if not dietary_prefs:
                await message.channel.send(f"""
Hey {user_name}! 🥗 You don't have any dietary preferences set yet.

**Why set dietary preferences?**
- Ensures all food recommendations are safe for you
- Helps find restaurants that accommodate your needs
- Makes recipe suggestions more relevant

To set your preferences, use: `!dietary vegetarian, gluten-free` (for example)

Common dietary preferences:
• vegetarian
• vegan
• gluten-free
• dairy-free
• nut-free
• keto
• paleo
• low-carb
• low-sodium
• halal
• kosher

You can set multiple preferences by separating them with commas.
""")
            else:
                prefs_list = ", ".join(dietary_prefs)
                await message.channel.send(f"""
Hey {user_name}! 🥗 Your current dietary preferences are: **{prefs_list}**

These preferences are used to:
1. Filter restaurant recommendations
2. Customize recipe suggestions
3. Ensure food recommendations are safe for you

To update your preferences, use: `!dietary [new preferences]`
To clear your preferences, use: `!dietary clear`
""")
            return
            
        # Clear preferences if requested
        if args.lower() == "clear":
            if 'dietary_preferences' in user_data:
                del user_data['dietary_preferences']
                self.user_data_manager.save_user_data(user_id, user_data)
                await message.channel.send(f"✅ I've cleared your dietary preferences, {user_name}.")
            else:
                await message.channel.send(f"You don't have any dietary preferences set, {user_name}.")
            return
            
        # Parse and set new preferences
        preferences = [pref.strip().lower() for pref in args.split(',')]
        
        # Validate preferences
        valid_preferences = []
        for pref in preferences:
            # Skip empty preferences
            if not pref:
                continue
                
            # Add the preference
            valid_preferences.append(pref)
            
        if not valid_preferences:
            await message.channel.send(f"Sorry {user_name}, I couldn't understand those dietary preferences. Please try again with preferences like 'vegetarian', 'gluten-free', etc.")
            return
            
        # Update user data
        user_data['dietary_preferences'] = valid_preferences
        self.user_data_manager.save_user_data(user_id, user_data)
        
        # Confirm to user with personalized response
        prefs_list = ", ".join(valid_preferences)
        
        # Create a more personalized confirmation based on the preferences
        safety_message = ""
        if any(pref in ["gluten-free", "nut-free", "dairy-free", "shellfish-free", "soy-free", "egg-free"] for pref in valid_preferences):
            safety_message = "\n\n**Safety Note:** I'll ensure all food recommendations strictly avoid these allergens for your safety."
        
        lifestyle_message = ""
        if any(pref in ["vegetarian", "vegan", "halal", "kosher"] for pref in valid_preferences):
            lifestyle_message = "\n\n**Lifestyle Note:** I'll respect your dietary choices in all recommendations."
        
        health_message = ""
        if any(pref in ["keto", "paleo", "low-carb", "low-sodium", "low-sugar", "low-fat"] for pref in valid_preferences):
            health_message = "\n\n**Health Note:** I'll optimize recommendations to support your health goals."
        
        await message.channel.send(f"""
✅ Got it, {user_name}! I've updated your dietary preferences to: **{prefs_list}**

All food recommendations, recipes, and restaurant suggestions will now respect these preferences.{safety_message}{lifestyle_message}{health_message}

You can update these anytime with `!dietary [preferences]` or clear them with `!dietary clear`.
""")
        
        # Save this conversation entry
        self.save_conversation_entry(user_id, f"!dietary {args}", f"Set dietary preferences to: {prefs_list}")
        
    async def process_favorites_command(self, message, user_id, user_name):
        """Process the !favorites command to show favorite restaurants and recipes"""
        # Get user data
        user_data = self.user_data_manager.get_user_data(user_id)
        
        # Get favorites
        favorites = user_data.get('favorites', {})
        favorite_restaurants = favorites.get('restaurants', [])
        favorite_recipes = favorites.get('recipes', [])
        
        if not favorite_restaurants and not favorite_recipes:
            await message.channel.send(f"Hey {user_name}, you don't have any favorites saved yet! Use `!addfavorite restaurant [name]` or `!addfavorite recipe [name]` to add some.")
            return
            
        # Create embed
        embed = discord.Embed(
            title=f"⭐ {user_name}'s Favorites",
            description="Here are your saved favorites:",
            color=0xffcc00
        )
        
        # Add restaurants
        if favorite_restaurants:
            restaurant_list = "\n• ".join(favorite_restaurants)
            embed.add_field(name="🍽️ Favorite Restaurants", value=f"• {restaurant_list}", inline=False)
        
        # Add recipes
        if favorite_recipes:
            recipe_list = "\n• ".join(favorite_recipes)
            embed.add_field(name="🍳 Favorite Recipes", value=f"• {recipe_list}", inline=False)
            
        await message.channel.send(embed=embed)
        
    async def process_add_favorite_command(self, message, args, user_id, user_name):
        """Process the !addfavorite command to add a favorite restaurant or recipe"""
        if not args:
            await message.channel.send(f"Hey {user_name}, please specify what you want to add to favorites. For example: `!addfavorite restaurant Healthy Harvest` or `!addfavorite recipe Protein Pancakes`")
            return
            
        # Parse arguments
        parts = args.split(' ', 1)
        if len(parts) < 2:
            await message.channel.send(f"Hey {user_name}, please specify both the type (restaurant or recipe) and the name. For example: `!addfavorite restaurant Healthy Harvest`")
            return
            
        fav_type = parts[0].lower()
        fav_name = parts[1].strip()
        
        if fav_type not in ['restaurant', 'recipe']:
            await message.channel.send(f"Hey {user_name}, the favorite type must be either 'restaurant' or 'recipe'.")
            return
            
        # Update user data
        user_data = self.user_data_manager.get_user_data(user_id)
        
        if 'favorites' not in user_data:
            user_data['favorites'] = {'restaurants': [], 'recipes': []}
            
        if fav_type == 'restaurant':
            if fav_name not in user_data['favorites']['restaurants']:
                user_data['favorites']['restaurants'].append(fav_name)
        else:  # recipe
            if fav_name not in user_data['favorites']['recipes']:
                user_data['favorites']['recipes'].append(fav_name)
                
        self.user_data_manager.save_user_data(user_id, user_data)
        
        # Confirm to user
        await message.channel.send(f"✅ Added **{fav_name}** to your favorite {fav_type}s, {user_name}!")
        
    async def process_test_command(self, message, args, user_id, user_name):
        """Process the !test command for testing features"""
        if not args:
            await message.channel.send(f"Hey {user_name}, please specify what you want to test. Available tests: `activity`")
            return
            
        test_type = args.lower()
        
        if test_type == 'activity':
            # Simulate an activity warning
            await message.channel.send(f"⚠️ **TESTING ACTIVITY WARNING** ⚠️")
            
            # Create a workout reminder embed
            embed = discord.Embed(
                title="🚨 Gaming Break Reminder",
                description=f"Hey {user_name}! You've been gaming for a while. Time for a quick health break!",
                color=0xff9900
            )
            
            embed.add_field(name="Why Take Breaks?", value="Regular breaks help prevent eye strain, reduce muscle stiffness, and improve focus.", inline=False)
            embed.add_field(name="What Now?", value="Try a quick 10-minute workout or stretch session to refresh your body and mind!", inline=False)
            
            # Create workout button
            workout_view = WorkoutView(self, user_id)
            
            await message.channel.send(embed=embed, view=workout_view)
        else:
            await message.channel.send(f"Hey {user_name}, I don't recognize that test type. Available tests: `activity`")
    
    async def process_workout_command(self, message, user_id, user_name):
        """Process the !workout command"""
        # Create workout view
        workout_view = WorkoutView(self, user_id)
        
        # Get user data
        user_data = self.user_data_manager.get_user_data(user_id)
        
        # Send workout message
        workout_message = f"""
```
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║                           🏋️ GAMING WORKOUT BREAK                          ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
```

**Hey {user_name}, ready for a quick health break?**

Taking short exercise breaks during gaming sessions helps:
• Reduce eye strain and headaches
• Prevent wrist and back pain
• Improve circulation and energy levels
• Boost your gaming performance

Choose an option below:
"""
        
        # Send the message with the view
        sent_message = await message.channel.send(workout_message, view=workout_view)
        
        # Store the message ID for later reference
        user_data['last_workout_message_id'] = sent_message.id
        
        # Update last workout time
        user_data['last_workout_time'] = datetime.now().isoformat()
        
        # Save user data
        self.user_data_manager.save_user_data(user_id, user_data)
    
    async def process_recipe_command(self, message, args, user_id, user_name):
        """Process the !recipe command"""
        if not args:
            await message.channel.send(f"Hey {user_name}, please list some ingredients you have on hand. For example: `!recipe chicken, rice, broccoli`")
            return
            
        # Get user data for health goal and dietary preferences
        user_data = self.user_data_manager.get_user_data(user_id)
        health_goal_data = user_data.get('health_goal', {})
        
        # Extract health goal text, handling both dictionary and string formats
        if isinstance(health_goal_data, dict):
            health_goal = health_goal_data.get('primary', '')
        else:
            health_goal = str(health_goal_data) if health_goal_data else ''
            
        # Get dietary preferences
        dietary_prefs = user_data.get('dietary_preferences', [])
        dietary_prefs_text = ", ".join(dietary_prefs) if dietary_prefs else "None specified"
            
        # Create prompt for Mistral
        prompt = f"""
You are GG_Nourish, a nutrition assistant for gamers. You have a friendly, conversational tone and understand gaming culture well.

USER CONTEXT:
- Name: {user_name}
- Health goal: {health_goal if health_goal else "Not specified"}
- Dietary preferences/restrictions: {dietary_prefs_text}
- Current query: "{args}"
- Platform: Discord (gaming community)

CONVERSATION HISTORY:
{self.get_recent_conversation_context(user_id)}

IMPORTANT SAFETY INSTRUCTION: You MUST strictly adhere to the user's dietary preferences and restrictions.
If they have allergies or dietary restrictions, NEVER recommend foods that violate these restrictions.

PERSONALITY INSTRUCTIONS:
- Be conversational and natural - respond as if you're chatting with a friend
- Use gaming references and terminology when appropriate
- Show understanding of gaming-specific challenges (time constraints, need for focus, etc.)
- Adapt your tone to match the user's energy level and style
- Acknowledge previous interactions if relevant
- Be helpful without being judgmental about food choices

Provide personalized food recommendations that:
1. Match their query
2. Support their health goal (if specified)
3. STRICTLY FOLLOW their dietary preferences/restrictions (this is critical for safety)
4. Are suitable for gamers (easy to eat, not messy for keyboards/controllers)
5. Include nutritional benefits specifically relevant to gaming performance (focus, energy, etc.)

Keep your response concise but helpful. Address them by name and reference their specific situation.
"""

        try:
            # Send a typing indicator while generating
            async with message.channel.typing():
                response = self.mistral_client.chat(
                    model=MISTRAL_MODEL,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": args}
                    ]
                )
                
                recipe_response = response.choices[0].message.content
                
                # Split the response into chunks if it's too long for Discord
                chunks = self.split_message(recipe_response)
                
                # Save this conversation entry
                self.save_conversation_entry(user_id, f"!recipe {args}", recipe_response)
                
                # Send each chunk as a separate message
                for i, chunk in enumerate(chunks):
                    if i == 0:
                        # Add a header to the first chunk
                        await message.channel.send(f"**🍳 Here's your recipe, {user_name}!** {f'(Part {i+1}/{len(chunks)})' if len(chunks) > 1 else ''}\n\n{chunk}")
                    else:
                        # Add continuation header to subsequent chunks
                        await message.channel.send(f"**Recipe continued** (Part {i+1}/{len(chunks)})\n\n{chunk}")
                
        except Exception as e:
            logger.error(f"Error generating recipe: {e}")
            await message.channel.send(f"Sorry {user_name}, I'm having trouble creating a recipe right now. Please try again later.")
    
    async def process_food_command(self, message, args, user_id, user_name):
        """Process the !food command"""
        if not args:
            await message.channel.send(f"Hey {user_name}, please tell me what kind of food you're looking for. For example: `!food healthy breakfast ideas` or `!food quick protein snacks`")
            return
            
        # Get user data for health goal and dietary preferences
        user_data = self.user_data_manager.get_user_data(user_id)
        health_goal_data = user_data.get('health_goal', {})
        
        # Extract health goal text, handling both dictionary and string formats
        if isinstance(health_goal_data, dict):
            health_goal = health_goal_data.get('primary', '')
        else:
            health_goal = str(health_goal_data) if health_goal_data else ''
            
        # Get dietary preferences
        dietary_prefs = user_data.get('dietary_preferences', [])
        dietary_prefs_text = ", ".join(dietary_prefs) if dietary_prefs else "None specified"
            
        # Create prompt for Mistral
        prompt = f"""
You are GG_Nourish, a nutrition assistant for gamers. You have a friendly, conversational tone and understand gaming culture well.

USER CONTEXT:
- Name: {user_name}
- Health goal: {health_goal if health_goal else "Not specified"}
- Dietary preferences/restrictions: {dietary_prefs_text}
- Current query: "{args}"
- Platform: Discord (gaming community)

CONVERSATION HISTORY:
{self.get_recent_conversation_context(user_id)}

IMPORTANT SAFETY INSTRUCTION: You MUST strictly adhere to the user's dietary preferences and restrictions.
If they have allergies or dietary restrictions, NEVER recommend foods that violate these restrictions.

PERSONALITY INSTRUCTIONS:
- Be conversational and natural - respond as if you're chatting with a friend
- Use gaming references and terminology when appropriate
- Show understanding of gaming-specific challenges (time constraints, need for focus, etc.)
- Adapt your tone to match the user's energy level and style
- Acknowledge previous interactions if relevant
- Be helpful without being judgmental about food choices

Provide personalized food recommendations that:
1. Match their query
2. Support their health goal (if specified)
3. STRICTLY FOLLOW their dietary preferences/restrictions (this is critical for safety)
4. Are suitable for gamers (easy to eat, not messy for keyboards/controllers)
5. Include nutritional benefits specifically relevant to gaming performance (focus, energy, etc.)

Keep your response concise but helpful. Address them by name and reference their specific situation.
"""

        try:
            # Send a typing indicator while generating
            async with message.channel.typing():
                response = self.mistral_client.chat(
                    model=MISTRAL_MODEL,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": args}
                    ]
                )
                
                food_response = response.choices[0].message.content
                
                # Split the response into chunks if it's too long for Discord
                chunks = self.split_message(food_response)
                
                # Save this conversation entry
                self.save_conversation_entry(user_id, f"!food {args}", food_response)
                
                # Send each chunk as a separate message
                for i, chunk in enumerate(chunks):
                    if i == 0:
                        # Add a header to the first chunk
                        await message.channel.send(f"**🍔 Food recommendations for {user_name}** {f'(Part {i+1}/{len(chunks)})' if len(chunks) > 1 else ''}\n\n{chunk}")
                    else:
                        # Add continuation header to subsequent chunks
                        await message.channel.send(f"**Recommendations continued** (Part {i+1}/{len(chunks)})\n\n{chunk}")
                
        except Exception as e:
            logger.error(f"Error generating food recommendations: {e}")
            await message.channel.send(f"Sorry {user_name}, I'm having trouble generating food recommendations right now. Please try again later.")
    
    async def process_fitness_plan_command(self, message, user_id, user_name):
        """Process the !fitnessplan command to create a personalized fitness plan"""
        # Get user data for health goal
        user_data = self.user_data_manager.get_user_data(user_id)
        health_goal_data = user_data.get('health_goal', {})
        
        # Extract health goal text, handling both dictionary and string formats
        if isinstance(health_goal_data, dict):
            health_goal = health_goal_data.get('primary', '')
        else:
            health_goal = str(health_goal_data) if health_goal_data else ''
        
        if not health_goal:
            await message.channel.send(f"Hey {user_name}, before I can create a fitness plan for you, I need to know your health goal. Please set it with `!healthgoal [your goal]`")
            return
        
        # Create prompt for Mistral
        prompt = f"""
You are GG_Nourish, a fitness and nutrition assistant for gamers. You have a friendly, conversational tone and understand gaming culture well.

USER CONTEXT:
- Name: {user_name}
- Health goal: {health_goal}
- Platform: Discord (gaming community)

CONVERSATION HISTORY:
{self.get_recent_conversation_context(user_id)}

IMPORTANT SAFETY INSTRUCTION: You MUST strictly adhere to the user's health goals and preferences.
If they have specific requirements or restrictions, NEVER recommend exercises that violate these restrictions.

PERSONALITY INSTRUCTIONS:
- Be conversational and natural - respond as if you're chatting with a friend
- Use gaming references and terminology when appropriate
- Show understanding of gaming-specific challenges (time constraints, need for focus, etc.)
- Adapt your tone to match the user's energy level and style
- Acknowledge previous interactions if relevant
- Be helpful without being judgmental about their fitness level

Create a personalized fitness plan that:
1. Aligns with their health goal
2. Is suitable for gamers who sit for long periods
3. Includes exercises that can be done at home with minimal equipment
4. Addresses common issues gamers face (wrist strain, back pain, eye fatigue)
5. Can be broken down into short sessions that fit between gaming sessions

Format your response conversationally, addressing them by name. Include:
- A catchy name for their fitness plan
- A brief introduction explaining the benefits of the plan
- A weekly schedule with specific exercises
- Tips for incorporating movement into gaming sessions
- Stretches or exercises that can be done during loading screens or between matches

Keep your response concise but helpful.
"""

        try:
            # Send a typing indicator while generating
            async with message.channel.typing():
                response = self.mistral_client.chat(
                    model=MISTRAL_MODEL,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": f"Create a fitness plan for me with my health goal: {health_goal}"}
                    ]
                )
                
                fitness_plan = response.choices[0].message.content
                
                # Split the response into chunks if it's too long for Discord
                chunks = self.split_message(fitness_plan)
                
                # Save this conversation entry
                self.save_conversation_entry(user_id, "!fitnessplan", fitness_plan)
                
                # Send each chunk as a separate message
                for i, chunk in enumerate(chunks):
                    if i == 0:
                        # Add a header to the first chunk
                        await message.channel.send(f"**🏋️ Your Personalized Fitness Plan, {user_name}!** {f'(Part {i+1}/{len(chunks)})' if len(chunks) > 1 else ''}\n\n{chunk}")
                    else:
                        # Add continuation header to subsequent chunks
                        await message.channel.send(f"**Fitness Plan continued** (Part {i+1}/{len(chunks)})\n\n{chunk}")
                
                # Add a reminder about the workout command
                await message.channel.send(f"**Want to start a quick workout now?** Use `!workout` to begin a guided exercise session!")
                
                # Save the fitness plan to user data
                user_data['fitness_plan'] = {
                    'plan': fitness_plan,
                    'created_at': datetime.now().isoformat(),
                    'health_goal': health_goal
                }
                self.user_data_manager.save_user_data(user_id, user_data)
                
        except Exception as e:
            logger.error(f"Error generating fitness plan: {e}")
            await message.channel.send(f"Sorry {user_name}, I'm having trouble creating a fitness plan right now. Please try again later.")
    
    async def process_order_command(self, message, args, user_id, user_name):
        """Process the !order command to find restaurants and order food"""
        if not args:
            await message.channel.send(f"""
Hey {user_name}! 🍽️ **Ready to order some healthy food?**

To get restaurant recommendations based on your health goals and dietary preferences, use the `!order` command followed by your location:

Example: `!order San Francisco` or `!order New York`

**The food ordering workflow:**
1. Set your health goal with `!healthgoal` (if you haven't already)
2. Set any dietary restrictions with `!dietary` (if applicable)
3. Use `!order [location]` to get restaurant recommendations that match your needs
4. View the recommended restaurants and their healthy menu options

**Note:** Your dietary preferences will be strictly respected in all recommendations for your safety.

Try it now with: `!order [your location]`
""")
            return
            
        location = args.strip()
        
        # Get user data for health goal and dietary preferences
        user_data = self.user_data_manager.get_user_data(user_id)
        health_goal_data = user_data.get('health_goal', {})
        
        # Extract health goal text, handling both dictionary and string formats
        if isinstance(health_goal_data, dict):
            health_goal = health_goal_data.get('primary', '')
        else:
            health_goal = str(health_goal_data) if health_goal_data else ''
        
        if not health_goal:
            await message.channel.send(f"Hey {user_name}, before I can recommend restaurants, I need to know your health goal. Please set it with `!healthgoal [your goal]`")
            return
            
        # Get dietary preferences
        dietary_prefs = user_data.get('dietary_preferences', [])
        
        # Get restaurant recommendations
        try:
            # Send a typing indicator while processing
            async with message.channel.typing():
                # Check if we're using the real API or mock data
                using_real_api = not self.food_module.uber_eats_api.use_mock
                
                # Debug info about API usage
                api_status = "real API" if using_real_api else "mock data"
                logger.info(f"Restaurant search for {location} using {api_status}")
                logger.info(f"Health goal: {health_goal}")
                logger.info(f"Dietary preferences: {dietary_prefs}")
                
                # For mock data, let's ensure we're using a supported location format
                if not using_real_api and location.lower() == "san francisco, ca":
                    # Try with just "San Francisco" for mock data
                    logger.info("Simplifying location for mock data")
                    location = "San Francisco"
                
                restaurants = await self.food_module.uber_eats_api.search_restaurants(
                    location=location,
                    health_goal=health_goal,
                    dietary_preferences=dietary_prefs
                )
                
                logger.info(f"Found {len(restaurants)} restaurants")
                
                if not restaurants:
                    # Different error messages based on whether we're using the real API or mock data
                    if using_real_api:
                        await message.channel.send(f"""
Hey {user_name}, I couldn't find any restaurants in "{location}" that match your health goal and dietary preferences.

This could be because:
• The location might not be supported by Uber Eats
• There might be an issue with the Uber Eats API connection
• The location format might be incorrect
• Your dietary preferences might be too restrictive for the available options

Please try a different location or check your spelling.
""")
                    else:
                        # Using mock data
                        await message.channel.send(f"""
Hey {user_name}, I couldn't find any restaurants in "{location}" that match your health goal and dietary preferences.

**Currently supported locations for testing with mock data:**
• San Francisco
• New York

Please try one of these locations or check your spelling.
""")
                    return
                
                # Format restaurant recommendations
                dietary_info = ""
                if dietary_prefs:
                    dietary_info = f" and dietary preferences ({', '.join(dietary_prefs)})"
                
                intro_message = f"""
Hey {user_name}! 🍽️ I found {len(restaurants)} restaurants in {location} that match your health goal: **{health_goal}**{dietary_info}

Here are some healthy options for you:
"""
                await message.channel.send(intro_message)
                
                # Send each restaurant as a separate message with embed for better formatting
                for restaurant in restaurants[:3]:  # Limit to 3 restaurants to avoid spam
                    # Create embed for restaurant
                    embed = discord.Embed(
                        title=f"🍽️ {restaurant['name']}",
                        description=f"**{restaurant['cuisine']}** • {restaurant['rating']}⭐ • ${restaurant['delivery_fee']} delivery • {restaurant['estimated_time']}",
                        color=0x00ff00
                    )
                    
                    # Add restaurant tags with emphasis on dietary compatibility
                    tags = ", ".join(restaurant['tags'])
                    if dietary_prefs:
                        # Highlight tags that match dietary preferences
                        highlighted_tags = []
                        for tag in restaurant['tags']:
                            tag_matches_pref = any(pref.lower() in tag.lower() for pref in dietary_prefs)
                            if tag_matches_pref:
                                highlighted_tags.append(f"**{tag}**")
                            else:
                                highlighted_tags.append(tag)
                        tags = ", ".join(highlighted_tags)
                    
                    embed.add_field(name="Tags", value=tags, inline=False)
                    
                    # Add menu items if available
                    if 'menu_items' in restaurant:
                        menu_items = restaurant['menu_items']
                        menu_text = ""
                        for item in menu_items:
                            # Add dietary compatibility indicator for each menu item
                            dietary_compatible = True
                            if dietary_prefs and 'tags' in item:
                                # Check if item tags align with dietary preferences
                                item_tags = [tag.lower() for tag in item.get('tags', [])]
                                for pref in dietary_prefs:
                                    if not any(pref.lower() in tag for tag in item_tags):
                                        dietary_compatible = False
                                        break
                            
                            # Add a checkmark for items that match dietary preferences
                            dietary_indicator = "✅ " if dietary_compatible else ""
                            menu_text += f"• {dietary_indicator}**{item['name']}** - ${item['price']}\n  {item['description']}\n"
                        
                        embed.add_field(name="🥗 Recommended Menu Items", value=menu_text, inline=False)
                    
                    # Add footer with health goal alignment and dietary safety
                    footer_text = f"These options align with your {health_goal} goal"
                    if dietary_prefs:
                        footer_text += f" and respect your dietary preferences ({', '.join(dietary_prefs)})"
                    embed.set_footer(text=footer_text)
                    
                    await message.channel.send(embed=embed)
                
                # Add a summary message
                if len(restaurants) > 3:
                    await message.channel.send(f"...and {len(restaurants) - 3} more restaurants that match your preferences.")
                
                # Save this interaction for context
                response_summary = f"Found {len(restaurants)} restaurants in {location} matching {health_goal} and dietary preferences: {dietary_prefs}"
                self.save_conversation_entry(user_id, f"!order {location}", response_summary)
                
                # Personalized closing message based on time of day
                current_hour = datetime.now().hour
                if 5 <= current_hour < 11:
                    meal_type = "breakfast"
                elif 11 <= current_hour < 15:
                    meal_type = "lunch"
                elif 15 <= current_hour < 22:
                    meal_type = "dinner"
                else:
                    meal_type = "late-night meal"
                
                await message.channel.send(f"Hope you find something delicious and healthy for your {meal_type}, {user_name}! 😋")
                
        except Exception as e:
            logger.error(f"Error processing order command: {e}")
            await message.channel.send(f"Sorry {user_name}, I encountered an error while searching for restaurants. Please try again later.")
    
    async def food_recommendations_button(self, interaction: discord.Interaction):
        """Button to get food recommendations"""
        await interaction.response.defer()
        
        # Get random food recommendations without requiring location
        response = await self.food_module.get_food_recommendations(
            self.user_id, 
            location=None  # No location needed for random recommendations
        )
        await interaction.followup.send(response.get('message'))
    
    async def send_start_message(self, channel, user_id, user_name):
        """Send a welcome message to start the user's health journey"""
        start_message = """
```
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║                 WELCOME TO YOUR HEALTH JOURNEY!                            ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
```

**Welcome to GG_Nourish, {user_name}!** 🎮 + 💪 = 🌟

I'm your personal health assistant designed specifically for gamers. Let's start your journey to a healthier gaming lifestyle!

**First Steps:**

1️⃣ Set your health goal with `!healthgoal [your goal]`
   Example: `!healthgoal I want to have more energy during gaming sessions`

2️⃣ Explore healthy food options with `!food [preference]`
   Example: `!food something quick and nutritious`

3️⃣ Take a quick workout break with `!workout`
   (These are designed to fit between gaming sessions!)

**What Makes GG_Nourish Special:**
• Activity monitoring that reminds you to take breaks
• Personalized food and recipe recommendations
• Quick workout routines designed for gamers
• Progress tracking with `!stats`

Ready to level up your health while gaming? Let's get started!
"""
        
        await channel.send(start_message)
        
        # Update user data to mark that they've started
        user_data = self.user_data_manager.get_user_data(user_id)
        user_data['started'] = True
        user_data['start_date'] = datetime.now().isoformat()
        self.user_data_manager.save_user_data(user_id, user_data)
        
    async def send_help_message(self, channel, user_name):
        """Send a help message with available commands"""
        help_embed = discord.Embed(
            title="🎮 GG_Nourish Commands 🥗",
            description="Here are the commands you can use:",
            color=discord.Color.green()
        )
        
        help_embed.add_field(
            name="Getting Started",
            value=(
                "`!start` - Begin your health journey\n"
                "`!help` - Show this help message\n"
                "`!stats` - View your progress and stats"
            ),
            inline=False
        )
        
        help_embed.add_field(
            name="Health Goals",
            value=(
                "`!healthgoal [goal]` - Set your health goal\n"
                "Example: `!healthgoal I want to build muscle while gaming`"
            ),
            inline=False
        )
        
        help_embed.add_field(
            name="Dietary Preferences",
            value=(
                "`!diet` - View your current dietary preferences\n"
                "`!diet [preferences]` - Set your dietary preferences\n"
                "Example: `!diet vegetarian, gluten-free, no dairy`"
            ),
            inline=False
        )
        
        help_embed.add_field(
            name="Food & Nutrition",
            value=(
                "`!food [preference]` - Get food recommendations\n"
                "`!recipe [ingredients]` - Generate a recipe\n"
                "`!order [location]` - Find healthy restaurants near you"
            ),
            inline=False
        )
        
        help_embed.add_field(
            name="Fitness & Exercise",
            value=(
                "`!fitnessplan` - Get a personalized fitness plan\n"
                "`!workout` - Start a quick workout break"
            ),
            inline=False
        )
        
        help_embed.add_field(
            name="Favorites",
            value=(
                "`!favorites` - View your favorites\n"
                "`!addfavorite restaurant [name]` - Add a restaurant to favorites\n"
                "`!addfavorite recipe [name]` - Add a recipe to favorites"
            ),
            inline=False
        )
        
        help_embed.add_field(
            name="Testing",
            value=(
                "`!test activity` - Simulate activity detection"
            ),
            inline=False
        )
        
        help_embed.set_footer(text=f"GG_Nourish is here to help you stay healthy while gaming, {user_name}!")
        
        await channel.send(embed=help_embed)
    
    async def process_dietary_command(self, message, args, user_id, user_name):
        """Process the diet command to set or view dietary preferences"""
        if not args:
            # If no arguments, get current dietary preferences
            response = await self.food_module.get_dietary_preferences(user_id)
        else:
            # With arguments, update dietary preferences
            response = await self.food_module.update_dietary_preferences(user_id, args)
            
        await message.channel.send(response.get('message'))
        
        # Create an interactive follow-up if they've set preferences
        if args and response.get('success'):
            view = DietaryPreferencesView(self, user_id)
            await message.channel.send("Would you like to add more details to your dietary preferences?", view=view)
        
    async def check_user_activity(self):
        """Check user activity and send reminders for breaks"""
        await self.wait_until_ready()
        logger.info("Starting activity monitoring task")
        
        while not self.is_closed():
            try:
                # Get all user data
                all_user_data = self.user_data_manager.get_all_user_data()
                
                for user_id, user_data in all_user_data.items():
                    # Skip if no activity data
                    if 'activity_data' not in user_data:
                        continue
                        
                    # Get the last activity time
                    last_activity = self.user_data_manager.get_last_activity_time(user_id)
                    
                    # Skip if no activity in the last hour (user is not active)
                    if not last_activity or (datetime.now() - last_activity).total_seconds() > 3600:
                        continue
                    
                    # Get activity data
                    activity_data = user_data['activity_data']
                    
                    # Skip if no session start
                    if 'session_start' not in activity_data:
                        continue
                        
                    # Calculate session duration
                    try:
                        session_start = datetime.fromisoformat(activity_data['session_start'])
                        session_duration = datetime.now() - session_start
                        session_minutes = session_duration.total_seconds() / 60
                    except (ValueError, TypeError):
                        continue
                    
                    # Check if we need to send a warning
                    today = datetime.now().strftime('%Y-%m-%d')
                    
                    # Only update activity counter every minute (not every loop iteration)
                    # Get the last activity update time
                    last_update_time = activity_data.get('last_update_time')
                    current_time = datetime.now().isoformat()
                    
                    # Only increment activity if it's been at least 60 seconds since the last update
                    if not last_update_time or (datetime.now() - datetime.fromisoformat(last_update_time)).total_seconds() >= 60:
                        daily_activity = activity_data.get('daily_activity', {}).get(today, 0)
                        
                        # Update daily activity (increment by 1 minute)
                        if 'daily_activity' not in activity_data:
                            activity_data['daily_activity'] = {}
                        activity_data['daily_activity'][today] = daily_activity + 1
                        
                        # Update the last update time
                        activity_data['last_update_time'] = current_time
                        
                        # Save the updated activity data
                        self.user_data_manager.save_user_data(user_id, user_data)
                        
                        # Log activity update
                        logger.debug(f"Updated activity for user {user_id}: {daily_activity + 1} minutes")
                    else:
                        # Get current daily activity without incrementing
                        daily_activity = activity_data.get('daily_activity', {}).get(today, 0)
                    
                    # Check if we need to send a warning
                    if daily_activity >= ACTIVITY_WARNING_THRESHOLD_MINUTES and not activity_data.get('warning_sent', False):
                        # Send warning to the user
                        try:
                            user = await self.fetch_user(int(user_id))
                            
                            # Create workout view
                            workout_view = WorkoutView(self, user_id)
                            
                            await user.send(
                                f"⚠️ **HEALTH ALERT** ⚠️\n\n"
                                f"You've been gaming for {daily_activity} minutes. Time for a quick health break!\n\n"
                                f"Taking short breaks helps prevent eye strain, muscle fatigue, and improves your gaming performance.",
                                view=workout_view
                            )
                            
                            # Mark warning as sent and store the time
                            activity_data['warning_sent'] = True
                            activity_data['last_warning_time'] = datetime.now().isoformat()
                            self.user_data_manager.save_user_data(user_id, user_data)
                            
                            logger.info(f"Sent activity warning to user {user_id}")
                        except Exception as e:
                            logger.error(f"Failed to send activity warning to user {user_id}: {e}")
                    
                    # Only reset warning flag after the warning threshold has been reached again
                    # AND it's been at least 60 minutes since the last warning
                    elif activity_data.get('warning_sent', False):
                        last_warning_time = activity_data.get('last_warning_time')
                        
                        # If we have a last warning time and it's been at least 60 minutes
                        if last_warning_time and (datetime.now() - datetime.fromisoformat(last_warning_time)).total_seconds() >= 3600:
                            logger.info(f"Resetting warning flag for user {user_id} after time threshold")
                            activity_data['warning_sent'] = False
                            self.user_data_manager.save_user_data(user_id, user_data)
            
            except Exception as e:
                logger.error(f"Error in activity monitoring task: {e}")
            
            # Check every 30 seconds (more reasonable interval)
            await asyncio.sleep(30)

    def get_recent_conversation_context(self, user_id):
        """Get recent conversation history for a user to provide context to the AI"""
        user_data = self.user_data_manager.get_user_data(user_id)
        
        # Initialize conversation history if it doesn't exist
        if 'conversation_history' not in user_data:
            user_data['conversation_history'] = []
            return "No previous conversation history."
        
        # Get the last 5 interactions (or fewer if there aren't that many)
        recent_history = user_data['conversation_history'][-5:] if len(user_data['conversation_history']) > 5 else user_data['conversation_history']
        
        if not recent_history:
            return "No previous conversation history."
            
        # Format the conversation history
        formatted_history = []
        for entry in recent_history:
            if 'command' in entry and 'response' in entry:
                formatted_history.append(f"User command: {entry['command']}")
                formatted_history.append(f"Your response: {entry['response'][:150]}..." if len(entry['response']) > 150 else f"Your response: {entry['response']}")
        
        return "\n".join(formatted_history) if formatted_history else "No previous conversation history."
        
    def save_conversation_entry(self, user_id, command, response):
        """Save a conversation entry to the user's history"""
        user_data = self.user_data_manager.get_user_data(user_id)
        
        # Initialize conversation history if it doesn't exist
        if 'conversation_history' not in user_data:
            user_data['conversation_history'] = []
        
        # Add the new entry
        user_data['conversation_history'].append({
            'timestamp': datetime.now().isoformat(),
            'command': command,
            'response': response
        })
        
        # Limit history to last 20 interactions to prevent excessive memory usage
        if len(user_data['conversation_history']) > 20:
            user_data['conversation_history'] = user_data['conversation_history'][-20:]
        
        # Save the updated user data
        self.user_data_manager.save_user_data(user_id, user_data)

    def split_message(self, message, max_length=1900):
        """Split a long message into smaller chunks that fit within Discord's character limit"""
        # If the message is already short enough, return it as a single chunk
        if len(message) <= max_length:
            return [message]
            
        # Split by paragraphs (double newlines)
        chunks = []
        current_chunk = ""
        paragraphs = message.split("\n\n")
        
        for paragraph in paragraphs:
            # If adding this paragraph would exceed the limit, start a new chunk
            if len(current_chunk) + len(paragraph) + 2 > max_length:
                if current_chunk:  # Only add non-empty chunks
                    chunks.append(current_chunk)
                current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
        
        # Add the last chunk if it's not empty
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks

# Custom UI Components
class WorkoutView(discord.ui.View):
    """View for workout options"""
    def __init__(self, agent, user_id):
        super().__init__(timeout=300)  # 5 minute timeout
        self.agent = agent
        self.user_id = user_id
        self.current_exercise_index = 0
        self.timer_task = None
        self.remaining_seconds = 0
        self.is_paused = False
        self.workout_message = None
        
        # Define the workout exercises
        self.exercises = [
            {
                "name": "Neck Stretches",
                "duration": 60,  # seconds
                "description": "Gently tilt your head side to side and front to back",
                "benefit": "Relieves neck tension from looking at the screen"
            },
            {
                "name": "Shoulder Rolls",
                "duration": 60,
                "description": "Roll your shoulders backward and forward",
                "benefit": "Reduces shoulder stiffness from keyboard use"
            },
            {
                "name": "Wrist Stretches",
                "duration": 60,
                "description": "Extend your arms and gently bend your wrists in all directions",
                "benefit": "Prevents carpal tunnel and wrist strain"
            },
            {
                "name": "Eye Relief",
                "duration": 60,
                "description": "Look away from the screen and focus on objects at different distances",
                "benefit": "Reduces eye strain and prevents dry eyes"
            },
            {
                "name": "Standing Side Bends",
                "duration": 60,
                "description": "Stand up and bend side to side with arms overhead",
                "benefit": "Stretches your sides and improves posture"
            },
            {
                "name": "Seated Leg Extensions",
                "duration": 60,
                "description": "While seated, extend each leg straight out and hold",
                "benefit": "Improves circulation in your legs"
            },
            {
                "name": "Desk Push-ups",
                "duration": 60,
                "description": "Do push-ups against your desk at an angle",
                "benefit": "Activates chest and arm muscles"
            },
            {
                "name": "Chair Squats",
                "duration": 60,
                "description": "Stand up and sit down repeatedly without fully sitting",
                "benefit": "Strengthens leg muscles and improves circulation"
            },
            {
                "name": "Deep Breathing",
                "duration": 60,
                "description": "Take deep breaths, filling your lungs completely and exhaling slowly",
                "benefit": "Increases oxygen flow and reduces stress"
            },
            {
                "name": "Final Stretch",
                "duration": 60,
                "description": "Reach up high, then touch your toes, and finally twist side to side",
                "benefit": "Full-body stretch to finish your workout"
            }
        ]
    
    @discord.ui.button(label="Start 10-Min Workout", style=discord.ButtonStyle.primary, emoji="🏋️")
    async def start_workout_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Start a workout session directly in Discord"""
        try:
            # Disable all buttons except pause and stop
            self.start_workout_button.disabled = True
            self.show_snack_ideas_button.disabled = True
            self.remind_later_button.disabled = True
            
            # Enable pause and stop buttons
            self.pause_button.disabled = False
            self.stop_button.disabled = False
            
            # Update the view
            await interaction.response.edit_message(view=self)
            
            # Create the initial workout embed
            embed = await self.create_workout_embed()
            
            # Send the workout message
            self.workout_message = await interaction.followup.send(embed=embed)
            
            # Start the timer
            self.remaining_seconds = self.exercises[0]["duration"]
            self.timer_task = asyncio.create_task(self.run_timer())
            
            # Log the workout start
            logger.info(f"Started Discord workout for user {self.user_id}")
            
            # Increment workout count
            user_data = self.agent.user_data_manager.get_user_data(self.user_id)
            user_data['workout_count'] = user_data.get('workout_count', 0) + 1
            self.agent.user_data_manager.save_user_data(self.user_id, user_data)
            
        except Exception as e:
            logger.error(f"Error starting Discord workout: {e}")
            await interaction.response.send_message(
                "Sorry, I encountered an error starting the workout. Please try again later.",
                ephemeral=True
            )
    
    @discord.ui.button(label="Pause", style=discord.ButtonStyle.secondary, emoji="⏸️", disabled=True)
    async def pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Pause the workout timer"""
        if not self.is_paused:
            self.is_paused = True
            button.label = "Resume"
            button.emoji = "▶️"
        else:
            self.is_paused = False
            button.label = "Pause"
            button.emoji = "⏸️"
        
        await interaction.response.edit_message(view=self)
    
    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger, emoji="⏹️", disabled=True)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Stop the workout timer"""
        if self.timer_task and not self.timer_task.done():
            self.timer_task.cancel()
        
        # Update the workout message
        embed = discord.Embed(
            title="Workout Ended",
            description="You've ended your workout session. Great effort!",
            color=discord.Color.blue()
        )
        
        await self.workout_message.edit(embed=embed)
        
        # Disable all buttons
        self.pause_button.disabled = True
        self.stop_button.disabled = True
        
        await interaction.response.edit_message(view=self)
    
    @discord.ui.button(label="Show Snack Ideas", style=discord.ButtonStyle.success, emoji="🍎")
    async def show_snack_ideas_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show healthy snack ideas"""
        # Get user data for health goal
        user_data = self.agent.user_data_manager.get_user_data(self.user_id)
        health_goal = user_data.get('health_goal', 'general health')
        
        # Generate snack ideas based on health goal
        snack_ideas = await self.agent.food_module.get_snack_ideas(health_goal)
        
        # Create embed for snack ideas
        embed = discord.Embed(
            title="🍎 Healthy Gaming Snacks",
            description=f"Here are some quick and healthy snack ideas that align with your health goal: **{health_goal}**",
            color=discord.Color.green()
        )
        
        for i, snack in enumerate(snack_ideas[:5], 1):
            embed.add_field(
                name=f"{i}. {snack['name']}",
                value=f"{snack['description']}\n**Benefit:** {snack['benefit']}",
                inline=False
            )
        
        embed.set_footer(text="Snacks that fuel your gaming without slowing you down!")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Remind Me Later", style=discord.ButtonStyle.secondary, emoji="⏰")
    async def remind_later_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Schedule a workout reminder for later"""
        await interaction.response.send_message(
            "I'll remind you to take a workout break in 30 minutes. Keep gaming!",
            ephemeral=True
        )
        
        # Schedule a reminder
        user_data = self.agent.user_data_manager.get_user_data(self.user_id)
        user_data['next_workout_reminder'] = (datetime.now() + timedelta(minutes=30)).isoformat()
        self.agent.user_data_manager.save_user_data(self.user_id, user_data)
    
    async def create_workout_embed(self):
        """Create the workout embed with current exercise information"""
        exercise = self.exercises[self.current_exercise_index]
        total_exercises = len(self.exercises)
        progress = int((self.current_exercise_index / total_exercises) * 100)
        
        # Create progress bar
        progress_bar = ""
        bar_length = 20
        filled_length = int(bar_length * progress / 100)
        progress_bar = "▓" * filled_length + "░" * (bar_length - filled_length)
        
        embed = discord.Embed(
            title=f"🏋️ GG_Nourish Workout - Exercise {self.current_exercise_index + 1}/{total_exercises}",
            description=f"Take a quick break from gaming to refresh your mind and body!",
            color=discord.Color.blue()
        )
        
        # Format time remaining
        minutes = self.remaining_seconds // 60
        seconds = self.remaining_seconds % 60
        time_str = f"{minutes:01d}:{seconds:02d}"
        
        embed.add_field(
            name=exercise["name"],
            value=exercise["description"],
            inline=False
        )
        
        embed.add_field(
            name="Benefit",
            value=exercise["benefit"],
            inline=False
        )
        
        embed.add_field(
            name="Time Remaining",
            value=f"⏱️ {time_str}",
            inline=True
        )
        
        embed.add_field(
            name="Progress",
            value=f"{progress}% [{progress_bar}]",
            inline=True
        )
        
        embed.set_footer(text="Follow along with these exercises to reduce gaming fatigue!")
        
        return embed
    
    async def run_timer(self):
        """Run the workout timer"""
        try:
            while self.current_exercise_index < len(self.exercises):
                if not self.is_paused:
                    # Update the timer
                    if self.remaining_seconds > 0:
                        self.remaining_seconds -= 1
                    else:
                        # Move to the next exercise
                        self.current_exercise_index += 1
                        
                        # Check if workout is complete
                        if self.current_exercise_index >= len(self.exercises):
                            # Workout complete
                            embed = discord.Embed(
                                title="🎉 Workout Complete!",
                                description="Great job! You've completed your 10-minute workout break.",
                                color=discord.Color.green()
                            )
                            
                            embed.add_field(
                                name="Benefits",
                                value="• Reduced eye strain and muscle tension\n• Improved circulation and energy\n• Enhanced focus for your next gaming session",
                                inline=False
                            )
                            
                            embed.set_footer(text="Remember to take regular breaks during long gaming sessions!")
                            
                            await self.workout_message.edit(embed=embed)
                            
                            # Disable all buttons
                            self.pause_button.disabled = True
                            self.stop_button.disabled = True
                            
                            # Update the original message view
                            for interaction in self._view_children:
                                if hasattr(interaction, "message") and interaction.message:
                                    await interaction.message.edit(view=self)
                            
                            break
                        
                        # Set timer for the next exercise
                        self.remaining_seconds = self.exercises[self.current_exercise_index]["duration"]
                    
                    # Update the embed
                    embed = await self.create_workout_embed()
                    await self.workout_message.edit(embed=embed)
                
                # Wait for 1 second
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            logger.info(f"Workout timer cancelled for user {self.user_id}")
        except Exception as e:
            logger.error(f"Error in workout timer: {e}")
    
# Custom UI Components
class DietaryPreferencesView(View):
    """View for dietary preferences options"""
    def __init__(self, agent, user_id):
        super().__init__(timeout=300)  # 5 minute timeout
        self.agent = agent
        self.user_id = user_id
        
        # Add buttons for different dietary actions
        allergy_button = Button(
            style=discord.ButtonStyle.danger,
            label="Add Allergies",
            emoji="🚫",
            custom_id="allergies"
        )
        allergy_button.callback = self.allergy_button
        self.add_item(allergy_button)
        
        spice_level_button = Button(
            style=discord.ButtonStyle.primary,
            label="Set Spice Preference",
            emoji="🌶️",
            custom_id="spice_level"
        )
        spice_level_button.callback = self.spice_level_button
        self.add_item(spice_level_button)
        
    async def allergy_button(self, interaction: discord.Interaction):
        """Button to add allergies"""
        await interaction.response.send_modal(AllergiesModal(self.agent, self.user_id))
        
    async def spice_level_button(self, interaction: discord.Interaction):
        """Button to set spice preference"""
        # Create the select menu for spice level
        spice_options = [
            discord.SelectOption(label="Mild", description="Little to no spice", emoji="🥛"),
            discord.SelectOption(label="Medium", description="Some heat", emoji="🌱"),
            discord.SelectOption(label="Hot", description="Significant heat", emoji="🌶️"),
            discord.SelectOption(label="Extra Hot", description="Very spicy", emoji="🔥")
        ]
        
        # Create a select menu view
        view = View(timeout=300)
        select = SpiceLevelSelect(options=spice_options, agent=self.agent, user_id=self.user_id)
        view.add_item(select)
        
        await interaction.response.send_message("Please select your spice preference:", view=view)
        
# Custom UI Components
class SpiceLevelSelect(discord.ui.Select):
    """Select menu for spice level preference"""
    def __init__(self, options, agent, user_id):
        super().__init__(placeholder="Choose your spice preference", options=options, min_values=1, max_values=1)
        self.agent = agent
        self.user_id = user_id
        
    async def callback(self, interaction: discord.Interaction):
        """Process the selected spice level"""
        user_data = self.agent.user_data_manager.get_user_data(self.user_id)
        
        # Add spice preference to user data
        user_data['spice_preference'] = self.values[0]
        self.agent.user_data_manager.save_user_data()
        
        await interaction.response.send_message(
            f"Great! I've set your spice preference to **{self.values[0]}**. I'll consider this when recommending food."
        )

# Custom UI Components
class FavoriteCuisinesModal(discord.ui.Modal):
    """Modal for entering favorite cuisines"""
    def __init__(self, agent, user_id):
        super().__init__(title="Your Favorite Cuisines")
        self.agent = agent
        self.user_id = user_id
        
        self.cuisines = discord.ui.TextInput(
            label="Enter your favorite cuisines (comma separated)",
            placeholder="Italian, Mexican, Thai, Indian, etc.",
            required=True,
            style=discord.TextStyle.short
        )
        self.add_item(self.cuisines)
        
    async def on_submit(self, interaction: discord.Interaction):
        user_data = self.agent.user_data_manager.get_user_data(self.user_id)
        
        # Parse cuisines
        cuisine_list = [c.strip() for c in self.cuisines.value.split(',')]
        
        # Add cuisines to user data
        user_data['favorite_cuisines'] = cuisine_list
        self.agent.user_data_manager.save_user_data()
        
        await interaction.response.send_message(
            f"Thanks! I've saved your favorite cuisines: **{', '.join(cuisine_list)}**. I'll consider these in my recommendations."
        )

# Custom UI Components
class AllergiesModal(discord.ui.Modal):
    """Modal for entering food allergies"""
    def __init__(self, agent, user_id):
        super().__init__(title="Your Food Allergies")
        self.agent = agent
        self.user_id = user_id
        
        self.allergies = discord.ui.TextInput(
            label="Enter your allergies (comma separated)",
            placeholder="Peanuts, shellfish, eggs, etc.",
            required=True,
            style=discord.TextStyle.short
        )
        self.add_item(self.allergies)
        
    async def on_submit(self, interaction: discord.Interaction):
        user_data = self.agent.user_data_manager.get_user_data(self.user_id)
        
        # Parse allergies
        allergy_list = [a.strip() for a in self.allergies.value.split(',')]
        
        # Add allergies to user data
        user_data['allergies'] = allergy_list
        
        # Also add to dietary_restrictions for recipe generation
        if 'dietary_restrictions' not in user_data:
            user_data['dietary_restrictions'] = []
            
        # Add allergies with "no" prefix if not already there
        for allergy in allergy_list:
            formatted_allergy = f"no {allergy}"
            if formatted_allergy not in user_data['dietary_restrictions']:
                user_data['dietary_restrictions'].append(formatted_allergy)
        
        self.agent.user_data_manager.save_user_data()
        
        await interaction.response.send_message(
            f"Thanks for letting me know about your allergies: **{', '.join(allergy_list)}**. I'll make sure to avoid these in food recommendations and recipes."
        )

# Run the bot
def run_bot():
    """Run the Discord bot"""
    # Get the Discord token
    token = os.getenv('DISCORD_TOKEN')
    
    if not token:
        print("Error: DISCORD_TOKEN not found in environment variables")
        return
        
    # Create and run the bot
    client = GGNourishAgent()
    client.run(token)
    
if __name__ == "__main__":
    run_bot()
