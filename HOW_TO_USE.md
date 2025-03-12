# GG_Nourish Bot User Guide

## Getting Started

1. **Set up your environment variables**
   - Make sure your `.env` file contains your Discord token and Mistral API key
   - Example:
     ```
     DISCORD_TOKEN=your_discord_token_here
     MISTRAL_API_KEY=your_mistral_api_key_here
     ```

2. **Run the bot**
   - Execute `python run_bot.py` to start the bot
   - You should see log messages indicating the bot has connected to Discord

## Using the Bot

The GG_Nourish bot supports the following commands:

### Basic Commands

- `!help` - Display a list of available commands
- `!healthgoal [your goal]` - Set and analyze your health goal
  - Example: `!healthgoal I want to lose weight and build muscle`

### Food Commands

- `!food [preference]` - Get food recommendations based on your preference
  - Example: `!food I want to order in tonight`
- `!recipe [ingredients]` - Generate a recipe with your available ingredients
  - Example: `!recipe chicken, rice, broccoli`

### Fitness Commands

- `!fitnessplan` - Create a personalized fitness plan
- `!workout` - Start a quick workout break

## Workout Timer

When you use the `!workout` command or when the bot detects you've been gaming for a while, it will offer you a workout break with three options:

1. **Start the guided 10-minute workout with timer** - Opens a browser window with an interactive timer
2. **See the exercises without the timer** - Shows the exercises in Discord
3. **Skip this workout** - Postpones the workout

## Troubleshooting

If you encounter any issues:

1. Check the `gg_nourish.log` file for detailed error messages
2. Make sure your Discord token and Mistral API key are correct
3. Ensure you have all the required dependencies installed (`pip install -r requirements.txt`)

## Bot Structure

The GG_Nourish bot is modularized into several components:

1. **Main agent** (`gg_nourish_agent.py`) - Integrates all modules and handles Discord interactions
2. **Food module** (`modules/food_module.py`) - Handles food recommendations and recipe generation
3. **Fitness module** (`modules/fitness_module.py`) - Manages fitness plans and exercise breaks
4. **User data manager** (`modules/user_data_manager.py`) - Handles user data storage and retrieval
5. **Workout UI server** (`modules/workout_ui_server.py`) - Serves the workout timer UI

The bot automatically detects when you've been gaming for a while (currently set to 1 minute for testing) and will suggest taking a break with some exercises to keep you healthy while gaming.
