# GG_Nourish Bot User Guide

## 📱 Visual Guide to Using GG_Nourish

### Step 1: Start the Bot
Run the bot with:
```
python run_bot.py
```

### Step 2: Interact in Discord
Once the bot is running, you'll see it come online in your Discord server. The bot will send a welcome message:

![Welcome Message](https://i.imgur.com/placeholder.png)
```
🎮 GG_Nourish Bot is now online! 🎮

I'm here to help you stay healthy while gaming. Here's what I can do:

🍔 Food Recommendations - Healthy meals & snacks
🏋️ Fitness Plans - Personalized workout routines
⏱️ Activity Reminders - Break reminders during gaming

Try these commands:
• !healthgoal [your goal] - Set your health goal
• !food [preference] - Get food recommendations
• !recipe [ingredients] - Generate a recipe
• !fitnessplan - Create a fitness plan
• !workout - Take a quick break
• !help - See all commands

Just say hi or type a command to get started!
```

### Step 3: Set Your Health Goal
Type `!healthgoal` followed by your goal:
```
!healthgoal I want to build muscle while gaming
```

The bot will analyze your goal and respond with a confirmation.

### Step 4: Get Food Recommendations
Type `!food` followed by your preference:
```
!food I want to order something healthy
```

The bot will determine if you want to order in or cook at home, then provide recommendations:

For ordering:
```
🍽️ Based on your muscle-building goal, here are some restaurant options:

🥩 Protein Power Bowl from HealthyEats
• 45g protein, 520 calories
• $12.99, delivery in 25-35 min

🍗 Grilled Chicken Plate from FitFoods
• 38g protein, 450 calories
• $10.99, delivery in 15-25 min

Would you like to:
1️⃣ See menu details
2️⃣ See more options
3️⃣ Get cooking suggestions instead
```

### Step 5: Generate a Recipe
Type `!recipe` followed by ingredients you have:
```
!recipe chicken, rice, broccoli
```

The bot will generate a recipe:
```
🍳 Here's a muscle-building recipe with your ingredients:

🔹 Protein-Packed Chicken & Rice Bowl 🔹

Ingredients:
• 6 oz chicken breast
• 1 cup brown rice
• 2 cups broccoli
• 1 tbsp olive oil
• Seasonings: garlic, salt, pepper

Instructions:
1. Cook rice according to package
2. Season chicken and grill until cooked through
3. Steam broccoli until tender-crisp
4. Combine in bowl and drizzle with olive oil

Nutrition:
• Calories: 520
• Protein: 42g
• Carbs: 45g
• Fat: 15g

Perfect for your muscle-building goal!
```

### Step 6: Get a Fitness Plan
Type `!fitnessplan`:
```
!fitnessplan
```

The bot will create a personalized plan:
```
🏋️ Here's your personalized fitness plan for muscle building:

🔹 3-Day Split Routine 🔹

Day 1: Upper Body Push
• Pushups: 3 sets of 12
• Shoulder Press: 3 sets of 10
• Tricep Dips: 3 sets of 12

Day 2: Upper Body Pull
• Rows: 3 sets of 12
• Bicep Curls: 3 sets of 10
• Back Extensions: 3 sets of 15

Day 3: Lower Body
• Squats: 3 sets of 15
• Lunges: 3 sets of 10 per leg
• Calf Raises: 3 sets of 20

Rest 1-2 minutes between sets
Complete this routine 2x per week with rest days in between

Would you like me to:
1️⃣ Provide exercise descriptions
2️⃣ Adjust the difficulty
3️⃣ Create a different type of plan
```

### Step 7: Take a Workout Break
Type `!workout`:
```
!workout
```

The bot will offer a workout break:
```
⏱️ Time for a quick workout break!

I've prepared a 10-minute stretch routine to help you stay limber and prevent gaming fatigue.

Choose an option:
1️⃣ Start the guided workout with timer (opens in browser)
2️⃣ See the exercises without the timer
3️⃣ Skip this workout
```

If you select option 1, a browser window will open with a timer and exercise instructions.

## 🔄 Activity Reminders

The bot will automatically detect when you've been gaming for a while (currently set to 1 minute for testing) and will suggest taking a break:

```
⚠️ You've been gaming for over an hour!

Taking short breaks helps prevent eye strain and muscle stiffness.

Would you like to:
1️⃣ Take a quick 5-minute stretch break
2️⃣ Get a healthy snack suggestion
3️⃣ Remind me again in 30 minutes
```

## 💬 Natural Conversation

You can also just chat normally with the bot about health and nutrition topics:

```
User: What are some good snacks for late night gaming?

Bot: 🌙 For late night gaming, you want snacks that won't disrupt your sleep or energy levels:

• Greek yogurt with berries (protein + antioxidants)
• Small handful of nuts (healthy fats + protein)
• Apple slices with peanut butter (fiber + protein)
• Hummus with veggie sticks (protein + fiber)

These options provide sustained energy without sugar crashes and won't interfere with your sleep quality. They're also easy to eat while gaming!
```

## 🛠️ Troubleshooting

If the bot doesn't respond:
1. Check that it's still running in your terminal
2. Look for error messages in the terminal or in `gg_nourish.log`
3. Restart the bot with `python run_bot.py`

If you encounter specific errors, please check the log file for details.
