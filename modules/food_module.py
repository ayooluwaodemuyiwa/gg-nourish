import json
import os
import logging
from datetime import datetime
from mistralai.client import MistralClient
from delivery_api import UberEatsAPI
import random

# Constants
MISTRAL_MODEL = "mistral-medium"  # Using medium model for faster responses

logger = logging.getLogger("food_module")

class FoodModule:
    def __init__(self, mistral_client, user_data_manager):
        """Initialize the food module with required dependencies"""
        self.mistral_client = mistral_client
        self.user_data_manager = user_data_manager
        
        # Get the Uber Eats API key from environment variables
        uber_eats_api_key = os.getenv("UBER_EATS_API_KEY")
        self.uber_eats_api = UberEatsAPI(api_key=uber_eats_api_key)  # Initialize Uber Eats API client with API key
        
        if uber_eats_api_key:
            logger.info("Uber Eats API initialized with provided API key")
        else:
            logger.warning("Uber Eats API initialized without API key - using mock data")
        
    async def determine_food_preference(self, user_id, message_content):
        """Determine if the user wants to order food or cook at home"""
        user_data = self.user_data_manager.get_user_data(user_id)
        health_goal = user_data.get('health_goal', {})
        dietary_preferences = user_data.get('dietary_restrictions', [])
        
        if not self.mistral_client:
            return {
                "success": False,
                "message": "Sorry, I'm having trouble connecting to my AI brain right now."
            }
            
        # Create system message for Mistral
        system_message = f"""You are GG_Nourish, a health and nutrition assistant for gamers.
Your task is to determine if the user wants to order food or cook at home based on their message.

User's health goal: {health_goal.get('primary', 'Not specified')}
User's dietary preferences: {', '.join(dietary_preferences) if dietary_preferences else 'Not specified'}

Analyze the user's message and determine their preference.
Respond in JSON format with:
{{
  "preference": "order" or "cook",
  "confidence": A number between 0 and 1 indicating your confidence in this determination,
  "reasoning": "Brief explanation of why you made this determination"
}}"""

        # Prepare messages for Mistral
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": message_content}
        ]
        
        try:
            # Call Mistral API
            chat_response = self.mistral_client.chat(
                model=MISTRAL_MODEL,
                messages=messages
            )
            
            # Extract the response
            ai_message = chat_response.choices[0].message.content
            
            # Try to parse JSON from the response
            try:
                # Clean up the response to extract valid JSON
                ai_message = ai_message.replace("```json", "").replace("```", "").strip()
                preference_data = json.loads(ai_message)
                
                preference = preference_data.get('preference', 'unknown')
                confidence = preference_data.get('confidence', 0)
                reasoning = preference_data.get('reasoning', '')
                
                # Save the preference to user data
                user_data['food_preference'] = {
                    "preference": preference,
                    "timestamp": datetime.now().isoformat()
                }
                self.user_data_manager.save_user_data()
                
                # Format the response based on preference
                if preference == 'order':
                    formatted_message = f"""
```
╔═══════════════════════════════════════════╗
║      🍽️ FOOD DELIVERY RECOMMENDATION      ║
╚═══════════════════════════════════════════╝
```

I understand you'd like to **order food**. Great choice!

To provide you with the best recommendations:

1️⃣ What's your location? (e.g., San Francisco, CA)
2️⃣ Any specific cuisine preferences? (e.g., Health Food, Vegetarian)
3️⃣ Any dietary restrictions I should know about?

I'll find healthy options that align with your **{health_goal.get('primary', '')}** goal!
"""
                elif preference == 'cook':
                    formatted_message = f"""
```
╔═══════════════════════════════════════════╗
║        🍳 RECIPE RECOMMENDATION         ║
╚═══════════════════════════════════════════╝
```

I understand you'd like to **cook at home**. Excellent choice!

To provide you with the best recipe recommendations:

1️⃣ What ingredients do you have on hand?
2️⃣ How much time do you have for cooking?
3️⃣ Any specific cuisine preferences?

I'll suggest healthy recipes that align with your **{health_goal.get('primary', '')}** goal!
"""
                else:
                    formatted_message = f"""
I'm not quite sure if you want to order food or cook at home. Could you clarify?

Would you prefer:
1️⃣ Food delivery recommendations
2️⃣ Recipes to cook at home
"""
                
                return {
                    "success": True,
                    "message": formatted_message,
                    "preference": preference,
                    "confidence": confidence
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing Mistral response: {e}")
                return {
                    "success": False,
                    "message": "I'm having trouble understanding your food preference. Could you clarify if you want to order food or cook at home?",
                    "error": str(e)
                }
                
        except Exception as e:
            logger.error(f"Error determining food preference: {e}")
            return {
                "success": False,
                "message": "Sorry, I'm having trouble determining your food preference right now. Please try again later.",
                "error": str(e)
            }
            
    async def get_food_recommendations(self, user_id, location=None, cuisine_preference=None):
        """Get food recommendations for a user"""
        try:
            # Get user data
            user_data = self.user_data_manager.get_user_data(user_id)
            if not user_data:
                return {
                    "success": False,
                    "message": "User data not found. Please set up your health profile first."
                }
            
            # Get primary health goal if available
            primary_goal = user_data.get('primary_goal', None)
            
            # Get dietary restrictions and favorite cuisines if available
            dietary_restrictions = user_data.get('dietary_restrictions', [])
            favorite_cuisines = user_data.get('favorite_cuisines', [])
            
            # Log dietary restrictions for debugging
            logger.info(f"Dietary restrictions for user {user_id}: {dietary_restrictions}")
            logger.info(f"Favorite cuisines for user {user_id}: {favorite_cuisines}")
            
            # Prioritize cuisine preference from parameter, then favorite cuisines
            if cuisine_preference:
                cuisine_filter = cuisine_preference
            elif favorite_cuisines and len(favorite_cuisines) > 0:
                # Select a random favorite cuisine
                cuisine_filter = random.choice(favorite_cuisines)
                logger.info(f"Selected cuisine from favorites: {cuisine_filter}")
            else:
                cuisine_filter = None
            
            # Use dietary restrictions as is - it's already a list
            diet_restrictions = dietary_restrictions
            
            # Log dietary restrictions for debugging
            logger.info(f"Using dietary restrictions: {diet_restrictions}")
            
            # If location is not provided, use a generic message
            location_message = f"in {location}" if location else "for you"
            
            # Search for restaurants using Uber Eats API (location is now optional)
            restaurants = await self.uber_eats_api.search_restaurants(
                location=location,
                cuisine_preference=cuisine_filter,
                health_goal=primary_goal,
                dietary_preferences=diet_restrictions if diet_restrictions else None
            )
            
            if not restaurants or len(restaurants) < 1:
                return {
                    "success": False,
                    "message": f"I couldn't find any restaurants {location_message} that match your criteria. Could you try a different location or cuisine?"
                }
            
            # Ensure we have diverse restaurants by including different cuisines
            logger.info(f"Found {len(restaurants)} restaurants before diversity filter")
            
            # Mix up the order to get better variety
            random.shuffle(restaurants)
            
            # Take up to 10 restaurants to show the user
            restaurants_to_show = restaurants[:10]
            
            # Log what we're showing
            logger.info(f"Showing {len(restaurants_to_show)} restaurants to the user")
            for r in restaurants_to_show:
                logger.info(f"- {r.get('name')} ({r.get('cuisine')})")
            
            # Store the restaurants in user data for later use
            user_data['last_restaurants'] = restaurants_to_show
            self.user_data_manager.save_user_data(user_id, user_data)
            
            # Format the restaurant recommendations with beautiful UI
            formatted_message = f"""
```
╔══════════════════════════════════════════════════════════════════════════╗
║                    🍽️  HEALTHY FOOD RECOMMENDATIONS                      ║
╚══════════════════════════════════════════════════════════════════════════╝
```

"""
            
            # Add dietary restrictions alert if present
            if diet_restrictions:
                diet_alert = f"Based on your **{primary_goal}** goal {location_message} and your dietary needs "
                diet_alert += f"(dietary restrictions: {', '.join(diet_restrictions)}), "
                diet_alert += "I've found these healthy options:"
                formatted_message += diet_alert
            else:
                formatted_message += f"Based on your **{primary_goal}** goal {location_message}, I've found these healthy options:"
            
            formatted_message += "\n\n"
            
            # Setup emoji indicators for features
            high_protein_emoji = "💪"
            low_cal_emoji = "🍃"
            quick_emoji = "⚡"
            eco_emoji = "🌱"
            popular_emoji = "🔥"
            
            # Add restaurant information with enhanced formatting
            for i, restaurant in enumerate(restaurants_to_show[:10], 1):
                name = restaurant.get('name', 'Unknown')
                rating = restaurant.get('rating', 0)
                delivery_fee = restaurant.get('delivery_fee', 0)
                estimated_time = restaurant.get('estimated_time', 'N/A')
                cuisine = restaurant.get('cuisine', 'Various')
                tags = restaurant.get('tags', [])
                
                # Generate star rating
                star_display = "⭐" * int(rating)
                if rating % 1 >= 0.5:  # Add half star
                    star_display += "✨"
                
                # Format delivery fee
                fee_display = f"${delivery_fee:.2f}" if isinstance(delivery_fee, (int, float)) else delivery_fee
                
                # Generate special indicators based on tags
                indicators = []
                if any(tag.lower() in ["high protein", "protein", "protein-focused"] for tag in tags):
                    indicators.append(high_protein_emoji)
                if any(tag.lower() in ["low calorie", "weight loss", "light"] for tag in tags):
                    indicators.append(low_cal_emoji)
                if "15-" in estimated_time:  # Quick delivery
                    indicators.append(quick_emoji)
                if any(tag.lower() in ["organic", "sustainable", "eco-friendly"] for tag in tags):
                    indicators.append(eco_emoji)
                if rating >= 4.7:  # Highly rated
                    indicators.append(popular_emoji)
                
                # Add diet compatibility indicators for dietary preferences
                is_compatible = True
                compatibility_note = ""
                
                if diet_restrictions:
                    diet_tags = [tag.lower() for tag in tags]
                    # Check for diet compatibility (vegetarian, vegan, etc.)
                    for diet in diet_restrictions:
                        diet_lower = diet.lower()
                        if diet_lower in ["vegetarian", "vegan", "keto", "paleo", "gluten-free"] and diet_lower not in diet_tags:
                            is_compatible = False
                            compatibility_note = f" (⚠️ May not offer {diet} options)"
                            break
                
                indicator_display = " ".join(indicators) if indicators else ""
                
                formatted_message += f"""
**{i}. {name}** {indicator_display}{compatibility_note}
• Rating: {star_display} ({rating})
• {cuisine} | ${delivery_fee:.2f} delivery | {estimated_time}
• Tags: {', '.join(tags[:3])}
"""
            
            # Add legend for indicators
            formatted_message += f"""
\n**Restaurant Features:**
{high_protein_emoji} High Protein | {low_cal_emoji} Low Calorie | {quick_emoji} Fast Delivery 
{eco_emoji} Eco-Friendly | {popular_emoji} Highly Rated

**How to proceed:**
• Type a number (1-10) to see the menu for that restaurant
• Type "more" to see different restaurant options
• Type "filter [cuisine]" to filter by a specific cuisine
• Type "save [number]" to save a restaurant to your favorites

**HEALTH TIP:** When ordering for your **{primary_goal}** goal, look for """
            
            # Provide specific health tips based on goal
            if "weight loss" in primary_goal:
                formatted_message += "meals with lean proteins, high fiber vegetables, and lighter sauces on the side."
            elif "muscle" in primary_goal:
                formatted_message += "meals high in protein, complex carbs, and healthy fats to fuel muscle growth."
            elif "energy" in primary_goal:
                formatted_message += "balanced meals with complex carbs, moderate protein, and nutrient-dense ingredients."
            else:
                formatted_message += "balanced meals with a good mix of vegetables, lean proteins, and whole grains."
            
            return {
                "success": True,
                "message": formatted_message,
                "restaurants": restaurants_to_show[:10],
                "has_more": len(restaurants_to_show) > 10,
                "requires_interaction": True
            }
            
        except Exception as e:
            logger.error(f"Error getting food recommendations: {e}")
            return {
                "success": False,
                "message": f"Sorry, I'm having trouble finding restaurants {location_message} right now. Please try again later.",
                "error": str(e)
            }
            
    async def get_restaurant_menu(self, user_id, restaurant_id):
        """Get the menu for a specific restaurant"""
        user_data = self.user_data_manager.get_user_data(user_id)
        health_goal = user_data.get('health_goal', {})
        primary_goal = health_goal.get('primary', '').lower()
        dietary_restrictions = user_data.get('dietary_restrictions', [])
        
        try:
            # Get the restaurant details from the last restaurants list
            last_restaurants = user_data.get('last_restaurants', [])
            restaurant = next((r for r in last_restaurants if r.get('id') == restaurant_id), None)
            
            if not restaurant:
                return {
                    "success": False,
                    "message": "I couldn't find that restaurant. Please try searching for restaurants again."
                }
                
            # Get the menu from the Uber Eats API
            menu_items = await self.uber_eats_api.get_restaurant_menu(restaurant_id)
            
            if not menu_items:
                return {
                    "success": False,
                    "message": f"I couldn't find the menu for {restaurant.get('name', 'this restaurant')}. Please try another restaurant."
                }
            
            # Use dietary restrictions as is - it's already a list
            diet_restrictions = dietary_restrictions
            
            # Log dietary restrictions for debugging
            logger.info(f"Using dietary restrictions for restaurant menu: {diet_restrictions}")
            
            # Filter menu items based on health goal if applicable
            if primary_goal:
                filtered_menu = await self.uber_eats_api.filter_menu_by_health_goal(menu_items, primary_goal)
                
                # If filtering removed all items, use the original menu
                if not filtered_menu:
                    filtered_menu = menu_items
                    health_message = f"None of the menu items perfectly match your {primary_goal} goal, but here are all options:"
                else:
                    health_message = f"These menu items are recommended for your {primary_goal} goal:"
            else:
                filtered_menu = menu_items
                health_message = "Here's the menu:"
            
            # Further filter by dietary restrictions if needed
            if diet_restrictions:
                menu_before_diet = len(filtered_menu)
                # Filter out items that contain allergens or don't comply with diet
                safe_menu = []
                maybe_safe_menu = []  # Items that might be compatible but need checking
                
                for item in filtered_menu:
                    item_tags = [tag.lower() for tag in item.get('tags', [])]
                    item_desc = item.get('description', '').lower()
                    
                    # Check if any restriction matches in tags or description
                    is_fully_safe = True
                    might_be_safe = True
                    allergen_warnings = []
                    
                    for restriction in diet_restrictions:
                        rest_lower = restriction.lower()
                        # If it's a diet (like "vegetarian"), the item should HAVE that tag
                        if rest_lower in ["vegetarian", "vegan", "keto", "paleo", "gluten-free"]:
                            if not any(rest_lower in tag for tag in item_tags):
                                is_fully_safe = False
                                # If it doesn't explicitly say non-vegetarian/non-vegan, it might be ok
                                if any(["meat" in item_desc, "chicken" in item_desc, "beef" in item_desc, 
                                       "pork" in item_desc, "fish" in item_desc, "seafood" in item_desc]):
                                    might_be_safe = False
                        # If it's an allergy, the item should NOT mention that allergen
                        else:
                            if rest_lower in item_desc:
                                is_fully_safe = False
                                might_be_safe = False
                                allergen_warnings.append(restriction)
                    
                    if is_fully_safe:
                        safe_menu.append(item)
                    elif might_be_safe:
                        # Add a warning note to the item
                        if 'description' not in item:
                            item['description'] = ''
                        
                        warning = "\n⚠️ *May not fully match your dietary needs - check with restaurant*"
                        if not item['description'].endswith(warning):
                            item['description'] += warning
                        
                        maybe_safe_menu.append(item)
                
                # Combine safe and maybe safe items
                if not safe_menu and not maybe_safe_menu and filtered_menu:
                    diet_warning = f"⚠️ None of the menu items fully match your dietary preferences ({', '.join(diet_restrictions)}). Here are all options, please check ingredients carefully."
                    filtered_menu = filtered_menu
                elif not safe_menu and maybe_safe_menu:
                    diet_warning = f"⚠️ No items fully match your dietary preferences ({', '.join(diet_restrictions)}), but these might be adaptable. Please check with the restaurant."
                    filtered_menu = maybe_safe_menu
                elif safe_menu and maybe_safe_menu:
                    diet_warning = f"✅ Some items match your dietary preferences ({', '.join(diet_restrictions)}). Items with ⚠️ symbols may need modifications."
                    filtered_menu = safe_menu + maybe_safe_menu
                else:
                    diet_warning = f"✅ These items match your dietary preferences ({', '.join(diet_restrictions)})."
                    filtered_menu = safe_menu
            else:
                diet_warning = ""
                
            # Format the menu with beautiful UI
            restaurant_name = restaurant.get('name', 'RESTAURANT MENU')
            stars = "⭐" * int(restaurant.get('rating', 0))
            cuisine = restaurant.get('cuisine', 'Various')
            delivery = restaurant.get('delivery_fee', 0)
            time = restaurant.get('estimated_time', 'N/A')
            
            formatted_message = f"""
```
╔══════════════════════════════════════════════════════════════════════════╗
║                          🍽️  {restaurant_name}                          ║
╚══════════════════════════════════════════════════════════════════════════╝
```

**{stars} | {cuisine} | ${delivery:.2f} delivery | {time}**

{health_message}
{diet_warning if diet_warning else ""}

"""
            
            # Set up emoji indicators for menu items
            protein_emoji = "💪"
            low_cal_emoji = "🍃"
            healthy_emoji = "💚"
            spicy_emoji = "🔥"
            veggie_emoji = "🥦"
            keto_emoji = "🥑"
            
            # Add menu items with enhanced formatting
            for i, item in enumerate(filtered_menu[:8], 1):
                name = item.get('name', 'Unknown')
                price = item.get('price', 0)
                description = item.get('description', 'No description available')
                calories = item.get('calories', 'N/A')
                protein = item.get('protein', 'N/A')
                carbs = item.get('carbs', 'N/A')
                fat = item.get('fat', 'N/A')
                tags = [tag.lower() for tag in item.get('tags', [])]
                
                # Generate indicators based on nutrition and tags
                indicators = []
                
                if isinstance(protein, str) and 'g' in protein:
                    protein_val = int(protein.replace('g', ''))
                    if protein_val >= 25:
                        indicators.append(protein_emoji)
                
                if isinstance(calories, (int, float)) and calories < 500:
                    indicators.append(low_cal_emoji)
                
                if "healthy" in tags or "nutritious" in tags:
                    indicators.append(healthy_emoji)
                
                if "spicy" in tags or "hot" in description.lower():
                    indicators.append(spicy_emoji)
                
                if "vegetarian" in tags or "vegan" in tags:
                    indicators.append(veggie_emoji)
                
                if "keto" in tags or "low-carb" in tags:
                    indicators.append(keto_emoji)
                
                indicator_display = " ".join(indicators) if indicators else ""
                
                formatted_message += f"""
**{i}. {name}** {indicator_display}
• ${price:.2f} | {calories} cal | P: {protein} | C: {carbs} | F: {fat}
• {description}
"""
            
            # Add legend and options
            formatted_message += f"""
\n**Dish Features:**
{protein_emoji} High Protein | {low_cal_emoji} Low Calorie | {healthy_emoji} Nutritious
{spicy_emoji} Spicy | {veggie_emoji} Plant-Based | {keto_emoji} Low-Carb

**How to proceed:**
• Type "back" to return to restaurant list
• Type "save menu [number]" to save a menu item to your favorites
• Type "order [number]" to get tips for ordering this dish

**HEALTH TIP:** For your **{primary_goal}** goal, """
            
            # Provide specific health tips based on goal
            if "weight loss" in primary_goal:
                formatted_message += "consider options with lower calories and higher protein to stay full longer."
            elif "muscle" in primary_goal:
                formatted_message += "prioritize dishes with at least 25g of protein to support muscle growth."
            elif "energy" in primary_goal:
                formatted_message += "look for balanced macros with complex carbs to sustain energy during gaming."
            else:
                formatted_message += "choose balanced meals with plenty of vegetables and lean proteins."
            
            # Save the menu items to user data for reference
            user_data['last_menu'] = {
                'restaurant_id': restaurant_id,
                'restaurant_name': restaurant_name,
                'menu_items': filtered_menu[:8]
            }
            self.user_data_manager.save_user_data(user_id, user_data)
            
            return {
                "success": True,
                "message": formatted_message,
                "menu_items": filtered_menu[:8],
                "restaurant": restaurant
            }
            
        except Exception as e:
            logger.error(f"Error getting restaurant menu: {e}")
            return {
                "success": False,
                "message": "Sorry, I'm having trouble retrieving the menu right now. Please try again later.",
                "error": str(e)
            }
            
    async def get_dietary_preferences(self, user_id):
        """Get the current dietary preferences for a user"""
        user_data = self.user_data_manager.get_user_data(user_id)
        dietary_restrictions = user_data.get('dietary_restrictions', [])
        
        if not dietary_restrictions:
            return {
                "success": True,
                "message": "You don't have any dietary restrictions set yet. Use the `!diet` command followed by your restrictions to set them. For example: `!diet vegetarian, no nuts, lactose intolerant`"
            }
            
        formatted_message = f"""
```
╔═══════════════════════════════════════════╗
║      🥗 YOUR DIETARY PREFERENCES           ║
╚═══════════════════════════════════════════╝
```

Your current dietary restrictions are:
• {" • ".join(dietary_restrictions)}

To update your preferences, use the `!diet` command followed by your restrictions.
Example: `!diet vegetarian, gluten-free, no shellfish`
"""
        
        return {
            "success": True,
            "message": formatted_message
        }
    
    async def update_dietary_preferences(self, user_id, args):
        """Update the dietary preferences for a user"""
        # Join args into a string and split by commas for individual preferences
        preferences_text = " ".join(args)
        new_preferences = [pref.strip() for pref in preferences_text.split(',')]
        
        # Filter out empty preferences
        new_preferences = [pref for pref in new_preferences if pref]
        
        if not new_preferences:
            return {
                "success": False,
                "message": "Please provide your dietary restrictions. For example: `!diet vegetarian, no nuts, lactose intolerant`"
            }
        
        # Update user data
        user_data = self.user_data_manager.get_user_data(user_id)
        user_data['dietary_restrictions'] = new_preferences
        self.user_data_manager.save_user_data()
        
        logger.info(f"Updated dietary preferences for user {user_id}: {new_preferences}")
        
        formatted_message = f"""
```
╔═══════════════════════════════════════════╗
║    🥗 DIETARY PREFERENCES UPDATED!         ║
╚═══════════════════════════════════════════╝
```

I've updated your dietary restrictions to:
• {" • ".join(new_preferences)}

I'll make sure all food recommendations comply with these restrictions. Your health and safety are my top priority!
"""
        
        return {
            "success": True,
            "message": formatted_message
        }
        
    async def generate_recipe(self, user_id, ingredients=None, cuisine=None, time_available=None):
        """Generate a recipe based on user's health goal and available ingredients"""
        user_data = self.user_data_manager.get_user_data(user_id)
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
            
        # Get user preferences if available
        dietary_restrictions = user_data.get('dietary_restrictions', [])
        favorite_cuisines = user_data.get('favorite_cuisines', [])
        
        # Use dietary restrictions as is - it's already a list
        diet_restrictions = dietary_restrictions
                
        # Log dietary restrictions for debugging
        logger.info(f"Using dietary restrictions for recipe: {diet_restrictions}")
        
        # Create system message for Mistral with STRONG emphasis on dietary restrictions
        system_message = f"""You are GG_Nourish, a health and nutrition assistant for gamers.
Your task is to generate a healthy recipe that aligns with the user's health goal.

**CRITICAL DIETARY INFORMATION:**
"""

        if diet_restrictions:
            system_message += f"""
- DIETARY PREFERENCES: {', '.join(diet_restrictions)}
  ***IMPORTANT: STRICTLY ADHERE TO THESE DIETARY PREFERENCES IN YOUR RECIPE***
"""
        else:
            system_message += "- No specific dietary preferences\n"

        system_message += f"""
User's health goal: {health_goal.get('primary', 'Not specified')}
Available ingredients: {ingredients or 'Not specified'}
Cuisine preference: {cuisine or (favorite_cuisines[0] if favorite_cuisines else 'Not specified')}
Time available: {time_available or 'Not specified'}

Create a recipe that:
1. Is 100% COMPLIANT with any dietary restrictions (NO EXCEPTIONS - this is the highest priority)
2. Uses the available ingredients when possible
3. Aligns with the user's health goal
4. Is easy to prepare
5. Is nutritionally balanced

DO NOT include any foods that conflict with the user's dietary restrictions under any circumstances.
TRIPLE CHECK that no restricted ingredients are included in your recipe - even as trace ingredients or garnishes.

Respond in JSON format with:
{{
  "recipe_name": "Name of the recipe",
  "preparation_time": "Estimated preparation time",
  "cooking_time": "Estimated cooking time",
  "difficulty": "Easy, Medium, or Hard",
  "ingredients": [
    {{
      "name": "Ingredient name",
      "quantity": "Quantity needed",
      "unit": "Unit of measurement"
    }}
  ],
  "instructions": [
    "Step 1 instruction",
    "Step 2 instruction"
  ],
  "nutrition": {{
    "calories": "Estimated calories per serving",
    "protein": "Protein content",
    "carbs": "Carbohydrate content",
    "fat": "Fat content"
  }},
  "health_benefits": [
    "Health benefit 1",
    "Health benefit 2"
  ],
  "tips": [
    "Cooking tip 1",
    "Cooking tip 2"
  ],
  "gaming_friendly": "Explain why this recipe is good for gamers (e.g., easy to eat while gaming, provides sustained energy)"
}}"""

        # Prepare messages for Mistral
        user_message = f"Generate a recipe for me using {ingredients or 'whatever ingredients you think are appropriate'}."
        
        if cuisine:
            user_message += f" I prefer {cuisine} cuisine."
        elif favorite_cuisines:
            user_message += f" I prefer {favorite_cuisines[0]} cuisine."
            
        user_message += f" I have {time_available or 'about 30 minutes'} to cook."
        
        if diet_restrictions:
            user_message += f" **IMPORTANT: Remember that I have these dietary restrictions: {', '.join(diet_restrictions)}. DO NOT include these in my recipe.**"
        
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        
        try:
            # Call Mistral API
            chat_response = self.mistral_client.chat(
                model=MISTRAL_MODEL,
                messages=messages
            )
            
            # Extract the response
            ai_message = chat_response.choices[0].message.content
            
            # Try to parse JSON from the response
            try:
                # Clean up the response to extract valid JSON
                ai_message = ai_message.replace("```json", "").replace("```", "").strip()
                recipe_data = json.loads(ai_message)
                
                # Save the recipe to user data
                user_data['last_recipe'] = {
                    "recipe_name": recipe_data.get('recipe_name'),
                    "ingredients": recipe_data.get('ingredients'),
                    "instructions": recipe_data.get('instructions'),
                    "timestamp": datetime.now().isoformat()
                }
                self.user_data_manager.save_user_data(user_id, user_data)
                
                # Format the recipe with improved UI
                formatted_message = f"""
```
╔═══════════════════════════════════════════╗
║         🍳 YOUR PERSONALIZED RECIPE        ║
╚═══════════════════════════════════════════╝
```

# **{recipe_data.get('recipe_name', 'Custom Recipe')}**

⏱️ **Prep Time:** {recipe_data.get('preparation_time', 'N/A')}
⏱️ **Cook Time:** {recipe_data.get('cooking_time', 'N/A')}
🔥 **Difficulty:** {recipe_data.get('difficulty', 'N/A')}
"""

                # Add dietary compliance notice if restrictions exist
                if diet_restrictions:
                    formatted_message += f"\n✅ **Dietary Compliance:** This recipe is compliant with your dietary needs ({', '.join(diet_restrictions)})\n"

                formatted_message += "\n## **Ingredients:**\n"
                
                for ingredient in recipe_data.get('ingredients', []):
                    name = ingredient.get('name', '')
                    quantity = ingredient.get('quantity', '')
                    unit = ingredient.get('unit', '')
                    
                    formatted_message += f"• {quantity} {unit} {name}\n"
                
                formatted_message += f"""
## **Instructions:**
"""
                
                for i, instruction in enumerate(recipe_data.get('instructions', []), 1):
                    formatted_message += f"{i}. {instruction}\n"
                
                formatted_message += f"""
## **Nutrition (per serving):**
• Calories: {recipe_data.get('nutrition', {}).get('calories', 'N/A')}
• Protein: {recipe_data.get('nutrition', {}).get('protein', 'N/A')}
• Carbs: {recipe_data.get('nutrition', {}).get('carbs', 'N/A')}
• Fat: {recipe_data.get('nutrition', {}).get('fat', 'N/A')}

## **Health Benefits:**
"""
                
                for benefit in recipe_data.get('health_benefits', []):
                    formatted_message += f"• {benefit}\n"
                
                formatted_message += f"""
## **Cooking Tips:**
"""
                
                for tip in recipe_data.get('tips', []):
                    formatted_message += f"• {tip}\n"
                
                formatted_message += f"""
This recipe is designed to support your **{health_goal.get('primary', '')}** goal!

**Would you like to:**
1️⃣ Save this recipe
2️⃣ Generate a different recipe
3️⃣ Get a shopping list for missing ingredients
"""
                
                return {
                    "success": True,
                    "message": formatted_message,
                    "recipe": recipe_data
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing Mistral response: {e}")
                return {
                    "success": False,
                    "message": "I'm having trouble generating a recipe for you. Let me try again.",
                    "error": str(e)
                }
                
        except Exception as e:
            logger.error(f"Error generating recipe: {e}")
            return {
                "success": False,
                "message": "Sorry, I'm having trouble generating a recipe right now. Please try again later.",
                "error": str(e)
            }
