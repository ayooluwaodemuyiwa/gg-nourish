# GG_Nourish - Health Assistant for Gamers

![GG_Nourish Logo](https://i.imgur.com/placeholder.png)

## What is GG_Nourish?

GG_Nourish is a Discord bot designed to help gamers maintain a healthy lifestyle while enjoying their gaming sessions. It addresses common health issues faced by gamers:

- **Sedentary Behavior**: Long gaming sessions without breaks can lead to health problems
- **Poor Nutrition**: Gamers often neglect proper nutrition during intense gaming sessions
- **Eye Strain & Muscle Fatigue**: Extended screen time causes physical discomfort
- **Work-Life Balance**: Difficulty balancing gaming with healthy lifestyle choices

## Why GG_Nourish?

According to research, the average gamer spends 8.5 hours per week playing games, with hardcore gamers spending 20+ hours weekly. This sedentary behavior is associated with:

- 40% increased risk of cardiovascular issues
- Higher rates of obesity and metabolic disorders
- Increased eye strain and musculoskeletal problems
- Poor dietary habits and nutrition

GG_Nourish helps combat these issues by providing timely reminders, personalized nutrition advice, and quick exercise routines specifically designed for gamers.

## Features

### Activity Monitoring
- Tracks gaming session duration
- Sends break reminders after customizable intervals
- Interactive UI for responding to break suggestions

### Food Recommendations
- Personalized restaurant suggestions from Uber Eats
- Filters based on health goals and dietary preferences
- Interactive menu browsing with nutrition information

### Recipe Generation
- Custom recipes based on ingredients you have available
- Tailored to your health goals and dietary restrictions
- Save and track your favorite recipes

### Fitness Integration
- Quick 10-minute workout routines between gaming sessions
- Web-based workout timer with guided exercises
- Customized fitness plans that fit into your gaming schedule

### Health Statistics
- Track your progress over time
- See how many breaks you've taken
- Monitor improvements in your health habits

## Commands

| Command | Description | Example |
|---------|-------------|---------|
| `!start` | Begin your health journey | `!start` |
| `!help` | View all available commands | `!help` |
| `!healthgoal` | Set and analyze your health goal | `!healthgoal I want to lose weight while gaming` |
| `!food` | Get food recommendations | `!food I want something healthy and quick` |
| `!recipe` | Generate a recipe with your ingredients | `!recipe chicken, rice, vegetables` |
| `!dietary` | Set dietary preferences | `!dietary I'm vegetarian and allergic to nuts` |
| `!favorites` | View your favorite restaurants and recipes | `!favorites` |
| `!addfavorite` | Add to your favorites | `!addfavorite restaurant Healthy Harvest` |
| `!fitnessplan` | Create a personalized fitness plan | `!fitnessplan` |
| `!workout` | Take a quick exercise break | `!workout` |
| `!stats` | View your health statistics | `!stats` |
| `!test activity` | Test the activity warning feature | `!test activity` |

## Getting Started

### Prerequisites
- Python 3.8 or higher
- Discord Bot Token
- Mistral AI API Key
- (Optional) Uber Eats API Key

### Installation

1. **Clone the repository**
   ```
   git clone https://github.com/yourusername/gg-nourish.git
   cd gg-nourish
   ```

2. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   Create a `.env` file with the following content:
   ```
   DISCORD_TOKEN=your_discord_bot_token
   MISTRAL_API_KEY=your_mistral_api_key
   UBER_EATS_API_KEY=your_uber_eats_api_key (optional)
   ```

4. **Run the bot**
   ```
   python run_bot.py
   ```

   For testing with shorter activity warning thresholds:
   ```
   python run_bot.py --test
   ```

## UI Components

GG_Nourish features a modern Discord UI with:

- **Interactive Buttons**: One-click actions for workouts, viewing menus, and more
- **Dropdown Menus**: Select restaurants, menu items, and workout options
- **Formatted Messages**: Clear, visually appealing information presentation
- **Web-based Workout Timer**: Browser interface for guided workout sessions

## Usage Statistics

GG_Nourish tracks your usage to help you monitor your health progress:

- Total gaming time tracked
- Number of workout breaks taken
- Favorite restaurants and recipes saved
- Progress toward your health goals

View your statistics anytime with the `!stats` command.

## Testing Features

To test the activity warning feature without waiting for the default time threshold:

1. Run the bot in test mode: `python run_bot.py --test`
2. Use the command `!test activity` in Discord
3. You should receive an activity warning within about 1 minute

## Troubleshooting

- **Bot not responding**: Check your Discord token and ensure the bot has proper permissions
- **No food recommendations**: Verify your Mistral API key is correct
- **Workout timer not opening**: Make sure no other applications are using the same port

## Architecture

The GG_Nourish application has been modularized into separate components:

1. **Main Agent** (gg_nourish_agent.py): Integrates all modules and handles Discord interactions
2. **Food Module** (food_module.py): Handles food recommendations and recipe generation
3. **Fitness Module** (fitness_module.py): Manages fitness plans and exercise breaks
4. **User Data Manager** (user_data_manager.py): Handles user data storage and retrieval
5. **Workout UI Server** (workout_ui_server.py): Serves the workout timer UI

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Discord.py](https://discordpy.readthedocs.io/) for the Discord API wrapper
- [Mistral AI](https://mistral.ai/) for providing the large language model capabilities
- [Uber Eats API](https://developer.uber.com/) for food delivery integration
