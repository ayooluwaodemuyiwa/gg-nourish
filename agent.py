import os
import json
import aiohttp
import discord
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
from datetime import datetime

USER_DATA_FILE = 'user_data.json'
MISTRAL_MODEL = "mistral-small-latest"

class MistralAgent:
    def __init__(self):
        self.user_data = {}
        self.chat_history = {}
        self.load_user_data()
        self.active_gaming_sessions = {}
        
        # Initialize Mistral client if API key is available
        self.mistral_client = None
        try:
            mistral_api_key = os.getenv("MISTRAL_API_KEY")
            if mistral_api_key:
                self.mistral_client = MistralClient(api_key=mistral_api_key)
            else:
                print("Warning: MISTRAL_API_KEY not found in environment variables")
        except Exception as e:
            print(f"Error initializing Mistral client: {e}")
    
    def load_user_data(self):
        """Load user data from JSON file"""
        try:
            if os.path.exists(USER_DATA_FILE):
                with open(USER_DATA_FILE, 'r') as f:
                    self.user_data = json.load(f)
            else:
                self.user_data = {}
                self._save_user_data()
        except Exception as e:
            print(f"Error loading user data: {e}")
            self.user_data = {}
    
    def _save_user_data(self):
        """Save user data to JSON file"""
        try:
            with open(USER_DATA_FILE, 'w') as f:
                json.dump(self.user_data, f, indent=4)
        except Exception as e:
            print(f"Error saving user data: {e}")
    
    def _get_user_data(self, user_id):
        """Get or initialize user data"""
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                'health_goal': None,
                'fitness_level': None,
                'address': None,
                'dietary_preferences': [],
                'default_location': None,
                'payment_info': {},
                'order_history': [],
                'recipe_history': [],
                'fitness_plan': None,
                'last_activity_reminder': None,
                'gaming_sessions': []
            }
            self._save_user_data()
        return self.user_data[user_id]
    
    def _update_chat_history(self, user_id, role, content):
        """Update chat history for a user"""
        if user_id not in self.chat_history:
            self.chat_history[user_id] = []
        
        # Keep only the last 10 messages to maintain context without too much history
        if len(self.chat_history[user_id]) > 10:
            self.chat_history[user_id] = self.chat_history[user_id][-10:]
        
        self.chat_history[user_id].append(ChatMessage(role=role, content=content))
    
    async def start_conversation(self, user_id):
        """Start the initial conversation with the user"""
        welcome_message = """🌱 Welcome to **GG_Nourish**! 🎮✨  
Let's personalize your health journey. What's your goal?  
(Example: "I want to lose weight," "I need muscle gain," "I want more energy," "I'm preparing for a marathon.")"""
        
        self._update_chat_history(user_id, "assistant", welcome_message)
        return welcome_message
    
    async def analyze_health_goal(self, user_id, goal_description):
        """Analyze the user's health goal using Mistral AI"""
        if not self.mistral_client:
            return {
                "success": False, 
                "message": "Sorry, I'm having trouble connecting to my AI brain right now."
            }
        
        # Update chat history with user's goal
        self._update_chat_history(user_id, "user", goal_description)
        
        # Get dietary preferences if available
        user_data = self._get_user_data(user_id)
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
                
        # Log dietary restrictions for context
        if diet_restrictions:
            print(f"Including dietary restrictions in health goal analysis for user {user_id}: {diet_restrictions}")
        
        # Create system message for Mistral
        system_message = """You are GG_Nourish, a health and nutrition assistant for gamers.
Your task is to analyze the user's health goal and classify it into primary and secondary categories.

Primary categories:
- Weight Loss
- Muscle Gain
- Endurance
- Energy Boost
- General Health
- Mental Focus
- Recovery

Secondary categories:
- Dietary (related to food/nutrition)
- Exercise (related to physical activity)
- Lifestyle (related to habits/routines)
- Gaming Performance (related to gaming endurance/focus)

"""

        # Add dietary restrictions section
        system_message += "**DIETARY RESTRICTIONS - CRITICALLY IMPORTANT:**\n"
        
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
Respond in JSON format with:
{
  "primary_goal": "The main goal (one of the categories above)",
  "secondary_goals": ["Additional goals or aspects"],
  "dietary_needs": ["Key dietary needs for this goal"],
  "exercise_needs": ["Key exercise types for this goal"],
  "summary": "Brief summary of the goal in 1-2 sentences",
  "response": "Your conversational response to the user"
}"""

        try:
            # Prepare messages for Mistral
            messages = [
                ChatMessage(role="system", content=system_message),
                ChatMessage(role="user", content=f"My health goal is: {goal_description}")
            ]
            
            # Call Mistral API
            chat_response = self.mistral_client.chat(
                model=MISTRAL_MODEL,
                messages=messages,
                max_tokens=1024,
                temperature=0.7,
            )
            
            # Extract the response
            ai_message = chat_response.choices[0].message.content
            
            # Try to parse JSON from the response
            try:
                # Clean up the response to extract valid JSON
                ai_message = ai_message.replace("```json", "").replace("```", "").strip()
                goal_analysis = json.loads(ai_message)
                
                # Save the analyzed goal to user data
                user_data = self._get_user_data(user_id)
                user_data['health_goal'] = {
                    'primary': goal_analysis.get('primary_goal'),
                    'secondary': goal_analysis.get('secondary_goals', []),
                    'description': goal_description,
                    'dietary_needs': goal_analysis.get('dietary_needs', []),
                    'exercise_needs': goal_analysis.get('exercise_needs', []),
                    'summary': goal_analysis.get('summary', '')
                }
                self._save_user_data()
                
                # Update chat history with AI's response
                response_text = goal_analysis.get('response', '')
                self._update_chat_history(user_id, "assistant", response_text)
                
                # Format a message to show the user how their goal was understood
                goal_icons = {
                    "Weight Loss": "⚖️",
                    "Muscle Gain": "💪",
                    "Endurance": "🏃",
                    "Energy Boost": "⚡",
                    "General Health": "❤️",
                    "Mental Focus": "🧠",
                    "Recovery": "🔄"
                }
                
                primary_goal = goal_analysis.get('primary_goal')
                primary_icon = goal_icons.get(primary_goal, "🎯")
                
                formatted_response = f"""I understand your goal! 

{primary_icon} **Primary Focus**: {primary_goal}

🔍 **Key Aspects**:
"""
                
                if goal_analysis.get('secondary_goals'):
                    formatted_response += "- " + "\n- ".join(goal_analysis.get('secondary_goals')) + "\n\n"
                
                formatted_response += f"""{goal_analysis.get('response', '')}

Would you like to:
1️⃣ Order in food that matches your goal?
2️⃣ Get a recipe to cook at home?"""
                
                return {
                    "success": True,
                    "message": formatted_response,
                    "analysis": goal_analysis
                }
                
            except json.JSONDecodeError as e:
                print(f"Error parsing Mistral response: {e}")
                return {
                    "success": False,
                    "message": "I couldn't properly analyze your goal. Can you try describing it a bit differently?",
                    "error": str(e)
                }
                
        except Exception as e:
            print(f"Error calling Mistral API: {e}")
            return {
                "success": False,
                "message": "Sorry, I'm having trouble understanding your goal right now. Please try again later.",
                "error": str(e)
            }
    
    async def track_gaming_session(self, user_id, start=True, channel_id=None):
        """Track when a user starts or ends a gaming session"""
        user_data = self._get_user_data(user_id)
        current_time = datetime.now()
        
        if start:
            # User started gaming
            self.active_gaming_sessions[user_id] = {
                "start_time": current_time,
                "channel_id": channel_id
            }
        else:
            # User ended gaming
            if user_id in self.active_gaming_sessions:
                start_time = self.active_gaming_sessions[user_id]["start_time"]
                duration = (current_time - start_time).total_seconds() / 60  # Duration in minutes
                
                # Save session data
                if 'gaming_sessions' not in user_data:
                    user_data['gaming_sessions'] = []
                
                user_data['gaming_sessions'].append({
                    "start": start_time.isoformat(),
                    "end": current_time.isoformat(),
                    "duration_minutes": duration
                })
                
                self._save_user_data()
                del self.active_gaming_sessions[user_id]
    
    async def check_activity_reminder(self, user_id):
        """Check if user has been gaming for too long and needs a reminder to move"""
        if user_id not in self.active_gaming_sessions:
            return None
        
        user_data = self._get_user_data(user_id)
        current_time = datetime.now()
        start_time = self.active_gaming_sessions[user_id]["start_time"]
        channel_id = self.active_gaming_sessions[user_id]["channel_id"]
        
        # Calculate how long they've been gaming (in minutes)
        duration = (current_time - start_time).total_seconds() / 60
        
        # Check if they've been gaming for over 2 hours (120 minutes)
        if duration >= 120:
            # Check if we've already sent a reminder in the last hour
            last_reminder = user_data.get('last_activity_reminder')
            if last_reminder:
                last_reminder_time = datetime.fromisoformat(last_reminder)
                time_since_reminder = (current_time - last_reminder_time).total_seconds() / 60
                
                # Only send a new reminder if it's been at least 60 minutes
                if time_since_reminder < 60:
                    return None
            
            # Update the last reminder time
            user_data['last_activity_reminder'] = current_time.isoformat()
            self._save_user_data()
            
            # Generate a reminder message
            reminder_message = f"""⚠️ You've been gaming for {int(duration)} minutes!  
💡 Time to stretch, walk around, or grab some water! 🏃‍♂️💦  

Try one of these:
🏃 Quick 5-Min Walk
🧘 Stretching Routine
🚶 Stand Up & Hydrate

🌟 Keep that energy up! Your health is just as important as your gaming grind! 🎮💙"""
            
            return {
                "message": reminder_message,
                "channel_id": channel_id
            }
        
        return None
        
    async def determine_food_preference(self, user_id, message):
        """Determine if the user wants to order in or cook at home"""
        # Update chat history with user's message
        self._update_chat_history(user_id, "user", message)
        
        if not self.mistral_client:
            return {
                "success": False, 
                "message": "Sorry, I'm having trouble connecting to my AI brain right now."
            }
            
        # Get user data
        user_data = self._get_user_data(user_id)
        health_goal = user_data.get('health_goal', {})
        
        # Get dietary preferences if available
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
                
        # Log dietary restrictions for context
        if diet_restrictions:
            print(f"Including dietary restrictions in food preference analysis for user {user_id}: {diet_restrictions}")
        
        # Create system message for Mistral
        system_message = f"""You are GG_Nourish, a health and nutrition assistant for gamers.
Your task is to determine if the user wants to:
1. Order food from restaurants
2. Get a recipe to cook at home
3. None of the above (other request)

User's health goal: {health_goal.get('primary', 'Not specified')}

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
Respond in JSON format with:
{
  "preference": "restaurant" OR "recipe" OR "other",
  "confidence": 0-100 (how confident you are in this determination),
  "response": "Your conversational response to the user"
}"""
        
        try:
            # Prepare messages for Mistral
            messages = [
                ChatMessage(role="system", content=system_message),
                ChatMessage(role="user", content=message)
            ]
            
            # Call Mistral API
            chat_response = self.mistral_client.chat(
                model=MISTRAL_MODEL,
                messages=messages,
                max_tokens=512,
                temperature=0.3,
            )
            
            # Extract the response
            ai_message = chat_response.choices[0].message.content
            
            # Try to parse JSON from the response
            try:
                # Clean up the response to extract valid JSON
                ai_message = ai_message.replace("```json", "").replace("```", "").strip()
                preference_analysis = json.loads(ai_message)
                
                # Save the preference to user data
                user_data = self._get_user_data(user_id)
                user_data['food_preference'] = preference_analysis.get('preference')
                self._save_user_data()
                
                # Update chat history with AI's response
                response_text = preference_analysis.get('response', '')
                self._update_chat_history(user_id, "assistant", response_text)
                
                preference = preference_analysis.get('preference')
                
                if preference == "order_in":
                    next_step_message = """Great! I'll help you find the perfect delivery options that match your health goals. 

What type of cuisine are you in the mood for today? Or would you like me to recommend something based on your health goal?"""
                else:  # cook_at_home
                    next_step_message = """Excellent choice! Cooking at home is a great way to control exactly what goes into your food.

What ingredients do you have on hand? Or would you like me to suggest a recipe based on your health goal?"""
                
                return {
                    "success": True,
                    "message": preference_analysis.get('response', '') + "\n\n" + next_step_message,
                    "preference": preference
                }
                
            except json.JSONDecodeError as e:
                print(f"Error parsing Mistral response: {e}")
                return {
                    "success": False,
                    "message": "I'm not sure if you want to order in or cook at home. Could you clarify?",
                    "error": str(e)
                }
                
        except Exception as e:
            print(f"Error calling Mistral API: {e}")
            return {
                "success": False,
                "message": "Sorry, I'm having trouble understanding your preference right now. Please try again later.",
                "error": str(e)
            }

    async def generate_food_recommendations(self, user_id, cuisine_preference=None):
        """Generate AI-matched food recommendations using Uber Eats API"""
        from delivery_api import UberEatsAPI
        
        user_data = self._get_user_data(user_id)
        health_goal = user_data.get('health_goal', {})
        
        if not health_goal:
            return {
                "success": False,
                "message": "I need to understand your health goal first. Can you tell me what your health goal is?"
            }
        
        # Get dietary preferences if available
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
                
        # Log dietary restrictions for context
        if diet_restrictions:
            print(f"Including dietary restrictions in food recommendations for user {user_id}: {diet_restrictions}")
        
        # Create system message for Mistral
        system_message = f"""You are GG_Nourish, a health and nutrition assistant for gamers.
Your task is to generate food recommendations that align with the user's health goal.

User's health goal: {health_goal.get('primary', 'Not specified')}
Health goal summary: {health_goal.get('summary', 'Not specified')}
Cuisine preference: {cuisine_preference or 'Not specified'}

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
Generate restaurant recommendations with the following details:
1. The best types of restaurants for their health goal
2. Specific dishes that would align with their goal
3. Ingredients to look for or avoid
4. ALWAYS consider their dietary restrictions and allergies

Respond in JSON format with:
{
  "restaurant_types": ["Type 1", "Type 2"],
  "recommended_dishes": ["Dish 1", "Dish 2"],
  "ingredients_to_look_for": ["Ingredient 1", "Ingredient 2"],
  "ingredients_to_avoid": ["Ingredient 1", "Ingredient 2"],
  "ordering_tips": "Tips for ordering to meet their health goal",
  "response": "Your conversational response to the user"
}"""

        try:
            # Prepare messages for Mistral
            messages = [
                ChatMessage(role="system", content=system_message),
                ChatMessage(role="user", content=f"Find me restaurants that match my {health_goal.get('primary', '')} goal{' with ' + cuisine_preference + ' cuisine' if cuisine_preference else ''}.")
            ]
            
            # Call Mistral API
            chat_response = self.mistral_client.chat(
                model=MISTRAL_MODEL,
                messages=messages,
                max_tokens=1024,
                temperature=0.7,
            )
            
            # Extract the response
            ai_message = chat_response.choices[0].message.content
            
            # Try to parse JSON from the response
            try:
                # Clean up the response to extract valid JSON
                ai_message = ai_message.replace("```json", "").replace("```", "").strip()
                recommendations = json.loads(ai_message)
                
                # Update chat history with AI's response
                response_text = recommendations.get('response', '')
                self._update_chat_history(user_id, "assistant", response_text)
                
                # Format the recommendations
                formatted_response = f"""🍽️ **Food Recommendations for Your {health_goal.get('primary', '')} Goal**

{recommendations.get('response', '')}

**Recommended Restaurants:**
"""
                
                for idx, restaurant in enumerate(recommendations.get('recommended_restaurants', []), 1):
                    formatted_response += f"{idx}. **{restaurant.get('name', '')}** - {restaurant.get('reasoning', '')}\n\n"
                
                formatted_response += """Would you like to:
1️⃣ See the menu for one of these restaurants?
2️⃣ Get different recommendations?
3️⃣ Place an order?"""
                
                return {
                    "success": True,
                    "message": formatted_response,
                    "recommendations": recommendations.get('recommended_restaurants', [])
                }
                
            except json.JSONDecodeError as e:
                print(f"Error parsing Mistral response: {e}")
                return {
                    "success": False,
                    "message": "I'm having trouble finding the best restaurants for your health goal. Let me try again.",
                    "error": str(e)
                }
                
        except Exception as e:
            print(f"Error generating food recommendations: {e}")
            return {
                "success": False,
                "message": "Sorry, I'm having trouble finding restaurants right now. Please try again later.",
                "error": str(e)
            }

    async def generate_personalized_recipe(self, user_id, ingredients=None):
        """Generate a personalized recipe for cooking at home based on health goal"""
        user_data = self._get_user_data(user_id)
        health_goal = user_data.get('health_goal', {})
        
        if not health_goal:
            return {
                "success": False,
                "message": "I need to understand your health goal first. Can you tell me what your health goal is?"
            }
            
        if not self.mistral_client:
            return {
                "success": False, 
                "message": "Sorry, I'm having trouble connecting to my AI brain right now."
            }
            
        # Get dietary preferences if available
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
                
        # Log dietary restrictions for context
        if diet_restrictions:
            print(f"Including dietary restrictions in recipe generation for user {user_id}: {diet_restrictions}")
        
        # Create system message for Mistral
        system_message = f"""You are GG_Nourish, a health and nutrition assistant for gamers.
Your task is to generate a personalized recipe that aligns with the user's health goal.

User's health goal: {health_goal.get('primary', 'Not specified')}
Health goal summary: {health_goal.get('summary', 'Not specified')}
Ingredients mentioned by user: {ingredients or 'None specified'}

**DIETARY RESTRICTIONS - CRITICALLY IMPORTANT:**
"""

        if allergies:
            system_message += f"""
- FOOD ALLERGIES: {', '.join(allergies)}
  ***WARNING: Never include these allergens in the recipe - this is a safety issue***
"""
        else:
            system_message += "- No known food allergies\n"

        if diets:
            system_message += f"""
- DIETARY PREFERENCES: {', '.join(diets)}
  ***The recipe MUST comply with these dietary preferences***
"""
        else:
            system_message += "- No specific dietary preferences\n"

        system_message += """
Generate a recipe with the following details:
1. Quick to prepare (under 30 minutes if possible)
2. Uses common ingredients
3. Rich in nutrients that support the user's health goal
4. Tasty and satisfying
5. NEVER includes ingredients that conflict with allergies or dietary preferences

Respond in JSON format with:
{
  "recipe_name": "Name of the recipe",
  "prep_time": "Preparation time in minutes",
  "cook_time": "Cooking time in minutes",
  "difficulty": "Easy, Medium, or Hard",
  "ingredients": ["Ingredient 1", "Ingredient 2"],
  "instructions": ["Step 1", "Step 2"],
  "nutritional_highlights": ["Highlight 1", "Highlight 2"],
  "goal_alignment": "How this recipe supports their health goal",
  "tips": "Additional cooking or preparation tips",
  "response": "Your conversational response to the user"
}"""

        try:
            # Prepare messages for Mistral
            user_prompt = f"Generate a recipe that supports my {health_goal.get('primary', '')} goal"
            if ingredients:
                user_prompt += f" using these ingredients: {ingredients}"
                
            messages = [
                ChatMessage(role="system", content=system_message),
                ChatMessage(role="user", content=user_prompt)
            ]
            
            # Call Mistral API
            chat_response = self.mistral_client.chat(
                model=MISTRAL_MODEL,
                messages=messages,
                max_tokens=1500,
                temperature=0.7,
            )
            
            # Extract the response
            ai_message = chat_response.choices[0].message.content
            
            # Try to parse JSON from the response
            try:
                # Clean up the response to extract valid JSON
                ai_message = ai_message.replace("```json", "").replace("```", "").strip()
                recipe = json.loads(ai_message)
                
                # Save the recipe to user data
                if 'recipe_history' not in user_data:
                    user_data['recipe_history'] = []
                
                user_data['recipe_history'].append({
                    "recipe_name": recipe.get('recipe_name'),
                    "calories": recipe.get('calories'),
                    "health_goal": health_goal.get('primary'),
                    "timestamp": datetime.now().isoformat()
                })
                self._save_user_data()
                
                # Update chat history with AI's response
                response_text = recipe.get('response', '')
                self._update_chat_history(user_id, "assistant", response_text)
                
                # Format the recipe
                formatted_response = f"""🍳 **Personalized Recipe: {recipe.get('recipe_name', '')}**

{recipe.get('response', '')}

**Nutritional Information:**
- Calories: {recipe.get('calories', 'N/A')}
- Protein: {recipe.get('protein', 'N/A')}
- Carbs: {recipe.get('carbs', 'N/A')}
- Fat: {recipe.get('fat', 'N/A')}
- Servings: {recipe.get('servings', 'N/A')}

**Ingredients:**
"""
                
                for ingredient in recipe.get('ingredients', []):
                    formatted_response += f"- {ingredient}\n"
                
                formatted_response += "\n**Instructions:**\n"
                
                for idx, step in enumerate(recipe.get('instructions', []), 1):
                    formatted_response += f"{idx}. {step}\n"
                
                formatted_response += f"""
**Preparation Time:** {recipe.get('preparation_time', 'N/A')}
**Cooking Time:** {recipe.get('cooking_time', 'N/A')}

**Health Benefits:**
{recipe.get('health_benefits', 'N/A')}

**Where to Find Ingredients:**
{', '.join(recipe.get('grocery_stores', ['Your local grocery store']))}

Would you like me to:
1️⃣ Create a fitness plan to complement this meal?
2️⃣ Suggest a different recipe?
3️⃣ Save this recipe to your favorites?"""
                
                return {
                    "success": True,
                    "message": formatted_response,
                    "recipe": recipe
                }
                
            except json.JSONDecodeError as e:
                print(f"Error parsing Mistral response: {e}")
                return {
                    "success": False,
                    "message": "I'm having trouble creating a recipe for you. Let me try again.",
                    "error": str(e)
                }
                
        except Exception as e:
            print(f"Error generating recipe: {e}")
            return {
                "success": False,
                "message": "Sorry, I'm having trouble creating a recipe right now. Please try again later.",
                "error": str(e)
            }

    async def create_fitness_plan(self, user_id):
        """Create a dynamic fitness plan aligned with the user's health goal"""
        user_data = self._get_user_data(user_id)
        health_goal = user_data.get('health_goal', {})
        
        if not health_goal:
            return {
                "success": False,
                "message": "I need to understand your health goal first. Can you tell me what your health goal is?"
            }
            
        if not self.mistral_client:
            return {
                "success": False, 
                "message": "Sorry, I'm having trouble connecting to my AI brain right now."
            }
            
        # Get dietary preferences if available
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
                
        # Log dietary restrictions for context
        if diet_restrictions:
            print(f"Including dietary restrictions in fitness plan for user {user_id}: {diet_restrictions}")
        
        # Create system message for Mistral
        system_message = f"""You are GG_Nourish, a health and nutrition assistant for gamers.
Your task is to create a personalized fitness plan that aligns with the user's health goal.

User's primary health goal: {health_goal.get('primary', 'Not specified')}
Secondary goals: {', '.join(health_goal.get('secondary', ['Not specified']))}

**DIETARY RESTRICTIONS - CRITICALLY IMPORTANT:**
"""

        if allergies:
            system_message += f"""
- FOOD ALLERGIES: {', '.join(allergies)}
  ***WARNING: Never recommend foods or supplements containing these allergens - this is a safety issue***
"""
        else:
            system_message += "- No known food allergies\n"

        if diets:
            system_message += f"""
- DIETARY PREFERENCES: {', '.join(diets)}
  ***Always respect these dietary preferences in ALL nutrition recommendations***
"""
        else:
            system_message += "- No specific dietary preferences\n"

        system_message += """
Create a fitness plan that:
1. Is realistic for gamers who may have limited time
2. Includes exercises that can be done at home with minimal equipment
3. Balances cardio, strength, and flexibility
4. Includes rest days
5. Takes into account the user's gaming schedule
6. ALWAYS considers dietary restrictions for any nutrition recommendations
7. NEVER suggests supplements or foods that conflict with the user's allergies or diet

Respond in JSON format with:
{
  "plan_name": "Name of the fitness plan",
  "weekly_schedule": [
    {
      "day": "Day of the week",
      "focus": "Main focus for this day (e.g., cardio, strength, rest)",
      "exercises": [
        {
          "name": "Name of exercise",
          "sets": "Number of sets",
          "reps": "Number of reps",
          "description": "Brief description of how to do the exercise"
        }
      ],
      "total_time": "Estimated time to complete the workout"
    }
  ],
  "equipment_needed": ["List of equipment needed, if any"],
  "goal_alignment": "How this plan supports the user's health goal",
  "gaming_integration": "How to integrate this plan with gaming sessions",
  "nutrition_tips": "Nutrition tips that STRICTLY comply with dietary restrictions",
  "progress_tracking": "How to track progress",
  "response": "Your conversational response to the user"
}"""

        try:
            # Prepare messages for Mistral
            messages = [
                ChatMessage(role="system", content=system_message),
                ChatMessage(role="user", content=f"Create a fitness plan for my {health_goal.get('primary', '')} goal that I can follow as a gamer.")
            ]
            
            # Call Mistral API
            chat_response = self.mistral_client.chat(
                model=MISTRAL_MODEL,
                messages=messages,
                max_tokens=2000,
                temperature=0.7,
            )
            
            # Extract the response
            ai_message = chat_response.choices[0].message.content
            
            # Try to parse JSON from the response
            try:
                # Clean up the response to extract valid JSON
                ai_message = ai_message.replace("```json", "").replace("```", "").strip()
                fitness_plan = json.loads(ai_message)
                
                # Save the fitness plan to user data
                user_data['fitness_plan'] = {
                    "plan_name": fitness_plan.get('plan_name'),
                    "weekly_schedule": fitness_plan.get('weekly_schedule'),
                    "equipment_needed": fitness_plan.get('equipment_needed'),
                    "goal_alignment": fitness_plan.get('goal_alignment'),
                    "created_at": datetime.now().isoformat()
                }
                self._save_user_data()
                
                # Update chat history with AI's response
                response_text = fitness_plan.get('response', '')
                self._update_chat_history(user_id, "assistant", response_text)
                
                # Format the fitness plan
                formatted_response = f"""💪 **Your Personalized Fitness Plan: {fitness_plan.get('plan_name', '')}**

{fitness_plan.get('response', '')}

**Weekly Schedule:**
"""
                
                for day in fitness_plan.get('weekly_schedule', []):
                    day_name = day.get('day', '')
                    day_focus = day.get('focus', '')
                    formatted_response += f"\n**{day_name} - {day_focus}**\n"
                    
                    if day_focus.lower() == 'rest':
                        formatted_response += "Rest day - Focus on recovery and light stretching.\n"
                    else:
                        formatted_response += f"Total time: {day.get('total_time', 'N/A')}\n\n"
                        
                        for exercise in day.get('exercises', []):
                            exercise_name = exercise.get('name', '')
                            exercise_sets = exercise.get('sets', '')
                            exercise_reps = exercise.get('reps', '')
                            exercise_description = exercise.get('description', '')
                            
                            formatted_response += f"- **{exercise_name}**: "
                            
                            if exercise_sets and exercise_reps:
                                formatted_response += f"{exercise_sets} sets x {exercise_reps} reps"
                            elif exercise_duration:
                                formatted_response += f"{exercise_duration}"
                                
                            if exercise_rest:
                                formatted_response += f", {exercise_rest} rest"
                                
                            formatted_response += f"\n  {exercise_description}\n"
                
                formatted_response += f"""
**Equipment Needed:**
{', '.join(fitness_plan.get('equipment_needed', ['No special equipment needed']))}

**How This Supports Your Goal:**
{fitness_plan.get('goal_alignment', 'N/A')}

**Gaming Integration:**
{fitness_plan.get('gaming_integration', 'N/A')}

**Tracking Progress:**
{fitness_plan.get('progress_tracking', 'N/A')}

I'll remind you to move after long gaming sessions to help you stay on track with this plan! 🎮💪"""
                
                return {
                    "success": True,
                    "message": formatted_response,
                    "fitness_plan": fitness_plan
                }
                
            except json.JSONDecodeError as e:
                print(f"Error parsing Mistral response: {e}")
                return {
                    "success": False,
                    "message": "I'm having trouble creating a fitness plan for you. Let me try again.",
                    "error": str(e)
                }
                
        except Exception as e:
            print(f"Error generating fitness plan: {e}")
            return {
                "success": False,
                "message": "Sorry, I'm having trouble creating a fitness plan right now. Please try again later.",
                "error": str(e)
            }

    async def enhance_activity_reminder(self, user_id):
        """Enhance the activity reminder with personalized exercises based on the user's fitness plan"""
        user_data = self._get_user_data(user_id)
        health_goal = user_data.get('health_goal', {})
        fitness_plan = user_data.get('fitness_plan', {})
        
        if not self.mistral_client:
            return {
                "success": False, 
                "message": "Sorry, I'm having trouble connecting to my AI brain right now."
            }
            
        # Get dietary preferences if available
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
                
        # Log dietary restrictions for context
        if diet_restrictions:
            print(f"Including dietary restrictions in activity reminder for user {user_id}: {diet_restrictions}")
        
        # Create system message for Mistral
        system_message = f"""You are GG_Nourish, a health and nutrition assistant for gamers.
Your task is to create a personalized activity reminder for a gamer who has been gaming for a while.

User's health goal: {health_goal.get('primary', 'Not specified')}
User has a fitness plan: {'Yes' if fitness_plan else 'No'}

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
Create a 5-minute activity break that:
1. Can be done right at the gaming desk
2. Helps with common gaming issues (eye strain, wrist pain, back pain)
3. Is energizing but not exhausting
4. NEVER suggests snacks or drinks that conflict with dietary restrictions

Respond in JSON format with:
{
  "reminder_title": "Catchy title for the activity break",
  "exercises": [
    {
      "name": "Name of exercise",
      "duration": "Duration in seconds",
      "description": "Brief description of how to do the exercise",
      "benefit": "Specific benefit for gamers"
    }
  ],
  "hydration_tip": "A tip for staying hydrated during gaming",
  "healthy_snack_suggestion": "A quick healthy snack idea that strictly complies with any dietary restrictions",
  "motivation": "A motivational message to encourage the user to take the break",
  "response": "Your conversational response to the user"
}"""

        try:
            # Prepare messages for Mistral
            messages = [
                ChatMessage(role="system", content=system_message),
                ChatMessage(role="user", content="I've been gaming for over 2 hours. Give me a quick exercise break.")
            ]
            
            # Call Mistral API
            chat_response = self.mistral_client.chat(
                model=MISTRAL_MODEL,
                messages=messages,
                max_tokens=1024,
                temperature=0.7,
            )
            
            # Extract the response
            ai_message = chat_response.choices[0].message.content
            
            # Try to parse JSON from the response
            try:
                # Clean up the response to extract valid JSON
                ai_message = ai_message.replace("```json", "").replace("```", "").strip()
                exercise_break = json.loads(ai_message)
                
                # Format the exercise break
                formatted_response = f"""⚠️ **Gaming Break Alert!** ⏰

You've been gaming for a while! Time for a quick **{exercise_break.get('break_name', '5-Minute Break')}**!

{exercise_break.get('response', '')}

**Quick Exercises (Total: {exercise_break.get('total_time', '5 minutes')}):**
"""
                
                for exercise in exercise_break.get('exercises', []):
                    exercise_name = exercise.get('name', '')
                    exercise_duration = exercise.get('duration', '')
                    exercise_description = exercise.get('description', '')
                    exercise_benefit = exercise.get('benefit', '')
                    
                    formatted_response += f"""
🔹 **{exercise_name}** ({exercise_duration})
   {exercise_description}
   *Benefit: {exercise_benefit}*
"""
                
                formatted_response += """
\n💡 Taking short breaks improves your gaming performance and keeps you healthy!
🎮 Ready to get back to your game? Let me know when you're done with your break!"""
                
                return {
                    "success": True,
                    "message": formatted_response,
                    "exercise_break": exercise_break
                }
                
            except json.JSONDecodeError as e:
                print(f"Error parsing Mistral response: {e}")
                # Fallback to a simple reminder if JSON parsing fails
                return {
                    "success": True,
                    "message": """⚠️ **Gaming Break Alert!** ⏰

You've been gaming for a while! Time for a quick break!

Try these quick exercises:
🔹 **Neck Stretches** (30 seconds) - Gently tilt your head side to side and front to back
🔹 **Wrist Rotations** (30 seconds) - Rotate your wrists in circles in both directions
🔹 **Shoulder Rolls** (30 seconds) - Roll your shoulders forward and backward
🔹 **Stand and Stretch** (1 minute) - Stand up, reach for the ceiling, then touch your toes
🔹 **Quick Walk** (2 minutes) - Walk around your room or to the kitchen and back

💡 Taking short breaks improves your gaming performance and keeps you healthy!
🎮 Ready to get back to your game? Let me know when you're done with your break!"""
                }
                
        except Exception as e:
            print(f"Error generating exercise break: {e}")
            # Fallback to a simple reminder if API call fails
            return {
                "success": True,
                "message": """⚠️ **Gaming Break Alert!** ⏰

You've been gaming for a while! Time for a quick break!

Try these quick exercises:
🔹 Stand up and stretch
🔹 Walk around for 2 minutes
🔹 Drink some water
🔹 Rest your eyes by looking at something 20 feet away for 20 seconds

💡 Taking short breaks improves your gaming performance and keeps you healthy!"""
            }
    
    async def detect_gaming_session(self, user_id, message_content, channel_id=None):
        """Detect if a user is starting or ending a gaming session based on their message"""
        if not self.mistral_client:
            return None
        
        # Get user data
        user_data = self._get_user_data(user_id)
        
        # Get dietary preferences if available
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
        
        # Create system message for Mistral
        system_message = """You are GG_Nourish, a health and nutrition assistant for gamers.
Your task is to determine if the user's message indicates they are:
1. Starting a gaming session
2. Ending a gaming session
3. Neither (talking about something else)

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
Look for keywords or phrases that indicate:
- Starting: "getting on", "launching", "starting", "about to play", "loading up", game titles, etc.
- Ending: "just finished", "getting off", "shutting down", "done playing", etc.

Respond in JSON format with:
{
  "status": "starting" OR "ending" OR "neither",
  "confidence": 0-100 (how confident you are in this determination),
  "game_mentioned": "Name of game if mentioned, or null",
  "explanation": "Brief explanation of why you made this determination"
}"""

        try:
            # Prepare messages for Mistral
            messages = [
                ChatMessage(role="system", content=system_message),
                ChatMessage(role="user", content=message_content)
            ]
            
            # Call Mistral API
            chat_response = self.mistral_client.chat(
                model=MISTRAL_MODEL,
                messages=messages,
                max_tokens=512,
                temperature=0.3,
            )
            
            # Extract the response
            ai_message = chat_response.choices[0].message.content
            
            # Try to parse JSON from the response
            try:
                # Clean up the response to extract valid JSON
                ai_message = ai_message.replace("```json", "").replace("```", "").strip()
                gaming_analysis = json.loads(ai_message)
                
                gaming_status = gaming_analysis.get('status', 'neither')
                confidence = float(gaming_analysis.get('confidence', 0))
                
                # Only consider if confidence is high enough
                if confidence >= 0.7:
                    if gaming_status == 'starting':
                        await self.track_gaming_session(user_id, start=True, channel_id=channel_id)
                        return {
                            "status": "started",
                            "game": gaming_analysis.get('game_mentioned', 'a game')
                        }
                    elif gaming_status == 'ending':
                        await self.track_gaming_session(user_id, start=False)
                        return {
                            "status": "ended",
                            "game": gaming_analysis.get('game_mentioned', 'a game')
                        }
                
                return None
                
            except (json.JSONDecodeError, ValueError) as e:
                print(f"Error parsing Mistral response for gaming detection: {e}")
                return None
                
        except Exception as e:
            print(f"Error detecting gaming session: {e}")
            return None
