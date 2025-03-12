import json
import os
import logging
from datetime import datetime
from mistralai.client import MistralClient

# Constants
MISTRAL_MODEL = "mistral-medium"  # Using medium model for faster responses
ACTIVITY_REMINDER_THRESHOLD = 60  # 1 minute in seconds (for testing)

logger = logging.getLogger("fitness_module")

class FitnessModule:
    def __init__(self, mistral_client, user_data_manager):
        """Initialize the fitness module with required dependencies"""
        self.mistral_client = mistral_client
        self.user_data_manager = user_data_manager
        
    async def create_fitness_plan(self, user_id):
        """Create a dynamic fitness plan aligned with the user's health goal"""
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
            logger.info(f"Including dietary restrictions in fitness plan for user {user_id}: {diet_restrictions}")
            
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
  "progress_tracking": "How to track progress"
}"""

        # Prepare messages for Mistral
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"Create a fitness plan for my {health_goal.get('primary', '')} goal that I can follow as a gamer."}
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
                fitness_plan = json.loads(ai_message)
                
                # Save the fitness plan to user data
                user_data['fitness_plan'] = {
                    "plan_name": fitness_plan.get('plan_name'),
                    "weekly_schedule": fitness_plan.get('weekly_schedule'),
                    "equipment_needed": fitness_plan.get('equipment_needed'),
                    "goal_alignment": fitness_plan.get('goal_alignment'),
                    "created_at": datetime.now().isoformat()
                }
                self.user_data_manager.save_user_data()
                
                # Format the fitness plan with improved UI
                formatted_message = f"""
```
╔═══════════════════════════════════════════╗
║     💪 YOUR PERSONALIZED FITNESS PLAN     ║
╚═══════════════════════════════════════════╝
```

**{fitness_plan.get('plan_name', 'Custom Fitness Plan')}**

This plan is designed specifically for your **{health_goal.get('primary', '')}** goal.

**WEEKLY SCHEDULE:**
"""
                
                for day in fitness_plan.get('weekly_schedule', []):
                    day_name = day.get('day', '')
                    day_focus = day.get('focus', '')
                    formatted_message += f"\n**{day_name} - {day_focus}**\n"
                    
                    if day_focus.lower() == 'rest':
                        formatted_message += "Rest day - Focus on recovery and light stretching.\n"
                    else:
                        formatted_message += f"⏱️ Total time: {day.get('total_time', 'N/A')}\n\n"
                        
                        for i, exercise in enumerate(day.get('exercises', []), 1):
                            exercise_name = exercise.get('name', '')
                            exercise_sets = exercise.get('sets', '')
                            exercise_reps = exercise.get('reps', '')
                            
                            formatted_message += f"{i}. **{exercise_name}**: {exercise_sets} sets × {exercise_reps}\n"
                            formatted_message += f"   _{exercise.get('description', '')}_\n"
                
                formatted_message += f"""
**EQUIPMENT NEEDED:**
"""
                for item in fitness_plan.get('equipment_needed', ['No special equipment needed']):
                    formatted_message += f"• {item}\n"
                
                formatted_message += f"""
**HOW THIS SUPPORTS YOUR GOAL:**
{fitness_plan.get('goal_alignment', 'N/A')}

**GAMING INTEGRATION:**
{fitness_plan.get('gaming_integration', 'N/A')}

**NUTRITION TIPS:**
{fitness_plan.get('nutrition_tips', 'N/A')}

**TRACKING PROGRESS:**
{fitness_plan.get('progress_tracking', 'N/A')}

**WHAT WOULD YOU LIKE TO DO NEXT?**
1️⃣ Start a quick workout break now
2️⃣ Adjust this plan (easier/harder)
3️⃣ Save this plan and continue gaming
"""
                
                return {
                    "success": True,
                    "message": formatted_message,
                    "fitness_plan": fitness_plan
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing Mistral response: {e}")
                return {
                    "success": False,
                    "message": "I'm having trouble creating a fitness plan for you. Let me try again.",
                    "error": str(e)
                }
                
        except Exception as e:
            logger.error(f"Error generating fitness plan: {e}")
            return {
                "success": False,
                "message": "Sorry, I'm having trouble creating a fitness plan right now. Please try again later.",
                "error": str(e)
            }
            
    async def generate_exercise_break(self, user_id):
        """Generate a quick exercise break for the user"""
        user_data = self.user_data_manager.get_user_data(user_id)
        fitness_plan = user_data.get('fitness_plan', {})
        health_goal = user_data.get('health_goal', {})
        
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
            
        # Create system message for Mistral
        system_message = f"""You are GG_Nourish, a health and nutrition assistant for gamers.
Your task is to create a quick exercise break that can be done during gaming sessions.

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
Create a 5-10 minute exercise break that:
1. Helps relieve tension from sitting
2. Can be done right at the desk
3. Focuses on problem areas for gamers (wrists, neck, back, eyes)
4. Is energizing but not too intense
5. NEVER suggests snacks or drinks that conflict with dietary restrictions

Respond in JSON format with:
{
  "break_name": "Name of the exercise break",
  "duration": "Total duration in minutes",
  "exercises": [
    {
      "name": "Name of exercise",
      "duration": "Duration in seconds",
      "description": "Brief description of how to do the exercise",
      "benefit": "Specific benefit for gamers"
    }
  ],
  "healthy_snack_suggestion": "A quick healthy snack idea that strictly complies with any dietary restrictions",
  "hydration_tip": "A tip for staying hydrated during gaming"
}"""

        # Prepare messages for Mistral
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": "Create a quick exercise break for me during my gaming session."}
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
                exercise_break = json.loads(ai_message)
                
                # Format the exercise break with improved UI
                formatted_message = f"""
```
╔═══════════════════════════════════════════╗
║      ⏱️ {exercise_break.get('break_name', 'QUICK EXERCISE BREAK').upper()}      ║
╚═══════════════════════════════════════════╝
```

**Duration: {exercise_break.get('duration', '5-10 minutes')}**

Take a short break from gaming to refresh your body and mind!

**EXERCISES:**
"""
                
                for i, exercise in enumerate(exercise_break.get('exercises', []), 1):
                    exercise_name = exercise.get('name', '')
                    exercise_duration = exercise.get('duration', '')
                    exercise_description = exercise.get('description', '')
                    exercise_benefit = exercise.get('benefit', '')
                    
                    formatted_message += f"{i}. **{exercise_name}** ({exercise_duration})\n"
                    formatted_message += f"   {exercise_description}\n"
                    formatted_message += f"   _Benefit: {exercise_benefit}_\n\n"
                
                formatted_message += f"""
**HEALTHY SNACK SUGGESTION:**
{exercise_break.get('healthy_snack_suggestion', 'N/A')}

**HYDRATION TIP:**
{exercise_break.get('hydration_tip', 'N/A')}

**BENEFITS:**
"""
                
                for benefit in exercise_break.get('benefits', []):
                    formatted_message += f"• {benefit}\n"
                
                formatted_message += """
**WOULD YOU LIKE TO:**
1️⃣ Start the guided workout with timer (opens in browser)
2️⃣ See a different workout
3️⃣ Skip this workout
"""
                
                return {
                    "success": True,
                    "message": formatted_message,
                    "exercise_break": exercise_break
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing Mistral response: {e}")
                return {
                    "success": False,
                    "message": "I'm having trouble creating an exercise break for you. Let me try again.",
                    "error": str(e)
                }
                
        except Exception as e:
            logger.error(f"Error generating exercise break: {e}")
            return {
                "success": False,
                "message": "Sorry, I'm having trouble creating an exercise break right now. Please try again later.",
                "error": str(e)
            }
            
    async def get_exercise_tips(self, user_id, exercise_type=None):
        """Get exercise tips based on the user's health goal and exercise type"""
        user_data = self.user_data_manager.get_user_data(user_id)
        health_goal = user_data.get('health_goal', {})
        
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
            logger.info(f"Including dietary restrictions in exercise tips for user {user_id}: {diet_restrictions}")
            
        # Create system message for Mistral
        system_message = f"""You are GG_Nourish, a health and nutrition assistant for gamers.
Your task is to provide exercise tips based on the user's health goal and exercise type.

User's health goal: {health_goal.get('primary', 'Not specified')}
Exercise type: {exercise_type or 'Not specified'}

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
Provide exercise tips that:
1. Are specifically tailored to gamers
2. Address the exercise type if specified
3. Support the user's health goal
4. Can be integrated into a gamer's lifestyle
5. Include proper form guidance
6. NEVER recommend protein sources or supplements that conflict with dietary restrictions
7. ALWAYS be mindful of any dietary preferences when suggesting nutrition to support exercise

Respond in JSON format with:
{
  "title": "Title for the exercise tips",
  "primary_tips": [
    "Primary tip 1",
    "Primary tip 2"
  ],
  "form_guidance": "Guidance on proper form",
  "gamer_specific_advice": "Advice specific to gamers",
  "nutrition_tips": "Nutrition tips STRICTLY compliant with dietary restrictions",
  "benefits": "Benefits of this exercise for the user's health goal"
}"""

        # Prepare user message
        user_message = f"Give me tips for {exercise_type or 'exercises'} that align with my {health_goal.get('primary', '')} goal."

        # Prepare messages for Mistral
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
                exercise_tips = json.loads(ai_message)
                
                # Format the response with improved UI
                formatted_message = f"""
```
╔══════════════════════════════════════════════════════════════════════════╗
║                    💪 {exercise_tips.get('title', 'EXERCISE TIPS')}                    ║
╚══════════════════════════════════════════════════════════════════════════╝
```

## **Tips:**
"""
                
                for tip in exercise_tips.get('primary_tips', []):
                    formatted_message += f"• {tip}\n"
                
                formatted_message += f"""
## **Proper Form:**
{exercise_tips.get('form_guidance', 'N/A')}

## **Gamer-Specific Advice:**
{exercise_tips.get('gamer_specific_advice', 'N/A')}

## **Nutrition Tips:**
{exercise_tips.get('nutrition_tips', 'N/A')}

## **Benefits:**
{exercise_tips.get('benefits', 'N/A')}

Remember to start slowly and listen to your body. Taking short exercise breaks during gaming sessions can greatly improve your overall health!
"""
                
                return {
                    "success": True,
                    "message": formatted_message,
                    "exercise_tips": exercise_tips
                }
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing Mistral response: {e}")
                return {
                    "success": False,
                    "message": "I'm having trouble generating exercise tips for you. Let me try again.",
                    "error": str(e)
                }
                
        except Exception as e:
            logger.error(f"Error generating exercise tips: {e}")
            return {
                "success": False,
                "message": "Sorry, I'm having trouble generating exercise tips right now. Please try again later.",
                "error": str(e)
            }
            
    async def detect_gaming_session(self, user_id, message_content, channel_id=None):
        """Detect if a user is starting or ending a gaming session based on their message"""
        if not self.mistral_client:
            return None
            
        # Create system message for Mistral
        system_message = """You are GG_Nourish, a health and nutrition assistant for gamers.
Your task is to determine if the user is indicating they are starting or ending a gaming session.

Respond in JSON format with:
{
  "gaming_status": "starting OR ending OR none",
  "confidence": "A number between 0.0 and 1.0 indicating how confident you are",
  "game_name": "Name of the game they're playing (if mentioned)",
  "reasoning": "Brief explanation of why you made this determination"
}

Examples of starting a gaming session:
- "Going to play some Fortnite now"
- "Time for my League of Legends session"
- "Jumping into a game of Apex"
- "Starting my stream now"

Examples of ending a gaming session:
- "Just finished a 3-hour Valorant session"
- "Done gaming for today"
- "Taking a break from gaming"
- "That's enough Call of Duty for now"

If the message is unrelated to starting or ending a gaming session, set gaming_status to "none"."""

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
                gaming_analysis = json.loads(ai_message)
                
                gaming_status = gaming_analysis.get('gaming_status', 'none')
                confidence = float(gaming_analysis.get('confidence', 0))
                
                # Only consider if confidence is high enough
                if confidence >= 0.7:
                    if gaming_status == 'starting':
                        await self.user_data_manager.track_gaming_session(user_id, start=True, channel_id=channel_id)
                        return {
                            "status": "started",
                            "game": gaming_analysis.get('game_name', 'a game')
                        }
                    elif gaming_status == 'ending':
                        await self.user_data_manager.track_gaming_session(user_id, start=False)
                        return {
                            "status": "ended",
                            "game": gaming_analysis.get('game_name', 'a game')
                        }
                
                return None
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Error parsing Mistral response for gaming detection: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Error detecting gaming session: {e}")
            return None
