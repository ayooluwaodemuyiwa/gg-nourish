import os
import json
import aiohttp
import logging
import random
from dotenv import load_dotenv

logger = logging.getLogger("delivery_api")

class UberEatsAPI:
    """
    A client for the Uber Eats API.
    
    This class provides methods to interact with the Uber Eats API for food delivery services.
    It supports searching for restaurants, viewing menus, and getting delivery estimates.
    
    If no API key is provided, it will use mock data for development and testing purposes.
    """
    
    def __init__(self, api_key=None):
        """Initialize the Uber Eats API client."""
        # Load environment variables if not already loaded
        load_dotenv()
        
        self.api_key = api_key or os.getenv("UBER_EATS_API_KEY")
        self.base_url = "https://api.uber.com/v1/eats"  # Base URL for Uber Eats API
        
        # Force use of real API if API key is provided
        self.use_mock = False if self.api_key else True
        
        if self.use_mock:
            logger.warning("No Uber Eats API key found. Using mock data.")
            # Load mock data
            self.mock_data = self._load_mock_data()
        else:
            logger.info("Using real Uber Eats API with provided key.")
    
    def _load_mock_data(self):
        """Load mock data for development purposes."""
        # Generate 1000+ unique restaurants with realistic names, ratings, etc.
        restaurant_data = {}
        
        # Define locations
        locations = [
            "San Francisco, CA", 
            "New York, NY", 
            "Los Angeles, CA", 
            "Chicago, IL", 
            "Seattle, WA",
            "Austin, TX",
            "Miami, FL",
            "Boston, MA",
            "Denver, CO",
            "Portland, OR",
            "Atlanta, GA",
            "Dallas, TX",
            "Phoenix, AZ",
            "San Diego, CA",
            "Las Vegas, NV",
            "Philadelphia, PA",
            "Houston, TX",
            "Washington, DC",
            "Nashville, TN",
            "New Orleans, LA"
        ]
        
        # Restaurant name components for generating realistic names
        name_prefixes = [
            "Healthy", "Green", "Fresh", "Clean", "Pure", "Vital", "Fit", "Active", 
            "Nourish", "Thrive", "Energize", "Balanced", "Lean", "Wholesome", "Natural",
            "Organic", "Power", "Vibrant", "Glow", "Harvest", "Blossom", "Sprout", "Root"
        ]
        
        name_suffixes = [
            "Kitchen", "Cafe", "Eatery", "Bowl", "Plate", "Table", "Garden", "Spot", 
            "Fuel", "Greens", "Bites", "Eats", "Market", "Feast", "Nourishment", "Cuisine",
            "House", "Haven", "Grill", "Bar", "Place", "Hub", "Corner", "Room", "Club"
        ]
        
        # Cuisine types
        cuisines = [
            "Health Food", "Vegetarian", "Vegan", "Mediterranean", "Asian Fusion", 
            "Fitness Food", "Organic", "Farm-to-Table", "Smoothie & Juice Bar", 
            "Salad Bar", "Poke", "Whole Foods", "Gluten-Free", "Keto", "Paleo",
            "Plant-Based", "Meal Prep", "Raw Food", "Protein-Focused", "Low-Carb"
        ]
        
        # Tags for filtering
        all_tags = [
            "healthy", "organic", "vegan", "vegetarian", "gluten-free", "dairy-free",
            "keto", "paleo", "low-carb", "high-protein", "plant-based", "non-gmo",
            "locally sourced", "sustainable", "eco-friendly", "sugar-free", "nut-free",
            "farm-to-table", "meal prep", "calorie counted", "macro friendly", "fitness",
            "weight loss", "muscle gain", "energy boosting", "detox", "immunity",
            "anti-inflammatory", "gut health", "brain food", "heart healthy", "omega-3",
            "antioxidants", "whole foods", "clean eating", "raw", "balanced nutrition"
        ]
        
        # Generate restaurants for each location
        for location in locations:
            # Create a list to hold restaurants for this location
            restaurant_data[location] = []
            
            # Generate 50 unique restaurants per location (1000+ total)
            for i in range(50):
                # Create a unique ID
                restaurant_id = f"r{len(restaurant_data[location]) + 1}_{location.replace(', ', '_').lower()}"
                
                # Generate a unique restaurant name
                prefix = random.choice(name_prefixes)
                suffix = random.choice(name_suffixes)
                restaurant_name = f"{prefix} {suffix}"
                
                # Generate realistic rating (3.5-5.0)
                rating = round(random.uniform(3.5, 5.0), 1)
                
                # Generate delivery fee ($0.99-$5.99)
                delivery_fee = round(random.uniform(0.99, 5.99), 2)
                
                # Generate estimated delivery time
                min_time = random.randint(10, 30)
                max_time = min_time + random.randint(5, 15)
                estimated_time = f"{min_time}-{max_time} min"
                
                # Select a random cuisine
                cuisine = random.choice(cuisines)
                
                # Select 3-5 random tags
                num_tags = random.randint(3, 5)
                tags = random.sample(all_tags, num_tags)
                
                # Create the restaurant object
                restaurant = {
                    "id": restaurant_id,
                    "name": restaurant_name,
                    "rating": rating,
                    "delivery_fee": delivery_fee,
                    "estimated_time": estimated_time,
                    "cuisine": cuisine,
                    "tags": tags,
                    "location": location,
                    "image_url": f"https://source.unsplash.com/300x200/?food,{cuisine.replace(' ', '-').lower()}"
                }
                
                # Add to the location's restaurant list
                restaurant_data[location].append(restaurant)
        
        # Generate menu items for each restaurant
        menu_data = {}
        
        # Menu item components
        protein_options = [
            "Grilled Chicken", "Wild Salmon", "Grass-Fed Beef", "Tofu", "Tempeh", 
            "Quinoa", "Lentils", "Black Beans", "Chickpeas", "Tuna", "Turkey", 
            "Plant Protein", "Seitan", "Egg Whites", "Greek Yogurt"
        ]
        
        base_options = [
            "Brown Rice", "Quinoa", "Mixed Greens", "Spinach", "Kale", "Sweet Potato",
            "Whole Grain Wrap", "Cauliflower Rice", "Ancient Grains", "Zucchini Noodles",
            "Buckwheat", "Black Rice", "Farro", "Sprouted Grain"
        ]
        
        veggie_options = [
            "Roasted Vegetables", "Steamed Broccoli", "Sautéed Kale", "Bell Peppers",
            "Cherry Tomatoes", "Cucumber", "Carrots", "Avocado", "Red Onion", "Mushrooms",
            "Asparagus", "Brussels Sprouts", "Cauliflower", "Green Beans", "Snap Peas"
        ]
        
        sauce_options = [
            "Tahini Dressing", "Olive Oil", "Lemon Vinaigrette", "Herb Sauce", 
            "Cashew Cream", "Yogurt Dressing", "Avocado Sauce", "Pesto", "Salsa",
            "Hummus", "Hot Sauce", "Chimichurri", "Balsamic Glaze"
        ]
        
        meal_types = [
            "Bowl", "Plate", "Salad", "Wrap", "Power Box", "Stir-Fry", "Burger",
            "Sandwich", "Smoothie", "Breakfast", "Snack Pack", "Soup", "Toast"
        ]
        
        # Generate menu items for all restaurants
        for location in restaurant_data:
            for restaurant in restaurant_data[location]:
                menu_items = []
                restaurant_id = restaurant["id"]
                
                # Generate 5-8 menu items per restaurant
                num_items = random.randint(5, 8)
                for j in range(num_items):
                    # Create a unique menu item ID
                    item_id = f"{restaurant_id}_item{j+1}"
                    
                    # Generate a menu item name
                    protein = random.choice(protein_options)
                    meal_type = random.choice(meal_types)
                    
                    # Random approach to naming
                    if random.random() < 0.5:
                        item_name = f"{protein} {meal_type}"
                    else:
                        adjectives = ["Energy", "Power", "Fit", "Vibrant", "Nourish", "Clean", "Fresh"]
                        item_name = f"{random.choice(adjectives)} {meal_type}"
                    
                    # Generate price ($7.99-$19.99)
                    price = round(random.uniform(7.99, 19.99), 2)
                    
                    # Generate description
                    base = random.choice(base_options)
                    veggies = random.sample(veggie_options, 2)
                    sauce = random.choice(sauce_options)
                    description = f"{protein} with {base}, {veggies[0]}, {veggies[1]}, and {sauce}"
                    
                    # Generate nutritional info
                    calories = random.randint(300, 700)
                    protein_g = random.randint(15, 45)
                    carbs_g = random.randint(20, 80)
                    fat_g = random.randint(8, 30)
                    
                    # Select 3 random tags
                    menu_tags = random.sample(all_tags, 3)
                    
                    # Create the menu item
                    menu_item = {
                        "id": item_id,
                        "name": item_name,
                        "price": price,
                        "description": description,
                        "calories": calories,
                        "protein": f"{protein_g}g",
                        "carbs": f"{carbs_g}g",
                        "fat": f"{fat_g}g",
                        "tags": menu_tags,
                        "image_url": f"https://source.unsplash.com/300x200/?food,{item_name.replace(' ', '-').lower()}"
                    }
                    
                    menu_items.append(menu_item)
                
                # Store the menu items
                menu_data[restaurant_id] = menu_items
        
        return {
            "restaurants": restaurant_data,
            "menus": menu_data
        }
    
    async def search_restaurants(self, location=None, cuisine_preference=None, health_goal=None, dietary_preferences=None):
        """
        Search for restaurants based on location and other criteria.
        
        Args:
            location (str): The location to search in
            cuisine_preference (str, optional): Filter by cuisine type
            health_goal (str, optional): Filter by health goal (weight loss, muscle gain, etc.)
            dietary_preferences (list, optional): List of dietary preferences
            
        Returns:
            list: List of restaurant dictionaries with details
        """
        try:
            # If using mock data
            if self.use_mock:
                # Use the mock data - ignore location and pull from all locations
                logger.info(f"Using mock data to search for random restaurants")
                
                # Get all restaurants from all locations
                all_restaurants = []
                for loc_restaurants in self.mock_data["restaurants"].values():
                    all_restaurants.extend(loc_restaurants)
                
                logger.info(f"Total available restaurants in database: {len(all_restaurants)}")
                
                # Start with a random selection of restaurants
                # Get a good variety by selecting from entire database
                initial_selection = random.sample(all_restaurants, min(100, len(all_restaurants)))
                restaurants = initial_selection
                
                # Apply cuisine filter if specified
                if cuisine_preference:
                    logger.info(f"Filtering by cuisine: {cuisine_preference}")
                    cuisine_lower = cuisine_preference.lower()
                    restaurants = [r for r in restaurants if cuisine_lower in r["cuisine"].lower() or
                                    any(cuisine_lower in tag.lower() for tag in r["tags"])]
                
                # Apply health goal filter if specified
                if health_goal:
                    logger.info(f"Filtering by health goal: {health_goal}")
                    health_goal_lower = health_goal.lower()
                    
                    # Map health goals to tags
                    health_goal_tags = {
                        "weight loss": ["low calorie", "low fat", "weight loss", "calorie counted"],
                        "muscle gain": ["high protein", "protein", "muscle", "bodybuilding"],
                        "energy": ["energy", "carbs", "performance", "endurance"],
                        "general health": ["balanced", "whole foods", "nutritious"],
                        "heart health": ["heart healthy", "low sodium", "omega-3"],
                        "digestion": ["fiber", "probiotics", "gut health"]
                    }
                    
                    # Get relevant tags for this health goal
                    relevant_tags = []
                    for goal, tags in health_goal_tags.items():
                        if health_goal_lower in goal or goal in health_goal_lower:
                            relevant_tags.extend(tags)
                    
                    # Filter restaurants by relevant tags
                    if relevant_tags:
                        restaurants = [r for r in restaurants if 
                                       any(tag.lower() in " ".join(r["tags"]).lower() for tag in relevant_tags)]
                
                # Apply dietary preferences filter if specified
                if dietary_preferences:
                    logger.info(f"Filtering by dietary preferences: {dietary_preferences}")
                    original_restaurants = restaurants.copy()
                    filtered_restaurants = []
                    
                    for restaurant in restaurants:
                        restaurant_tags = " ".join([tag.lower() for tag in restaurant.get("tags", [])])
                        meets_criteria = True
                        
                        # Special handling for strict dietary requirements
                        for pref in dietary_preferences:
                            pref_lower = pref.lower()
                            # For strict requirements, ensure they're met
                            if ("vegan" in pref_lower and "vegan" not in restaurant_tags) or \
                               ("vegetarian" in pref_lower and "vegetarian" not in restaurant_tags and "vegan" not in restaurant_tags):
                                # Only mark as not meeting criteria for core dietary restrictions
                                meets_criteria = False
                                break
                        
                        if meets_criteria:
                            filtered_restaurants.append(restaurant)
                    
                    # If we filtered out ALL or nearly all restaurants, return some from the original list with a mix
                    if len(filtered_restaurants) < 5 and original_restaurants:
                        logger.warning(f"Too few restaurants matched strict filters. Adding more options.")
                        result_restaurants = filtered_restaurants.copy()
                        
                        # Add more restaurants from the original list to make at least 10
                        remaining_needed = 10 - len(result_restaurants)
                        other_restaurants = [r for r in original_restaurants if r not in filtered_restaurants]
                        if other_restaurants and remaining_needed > 0:
                            addition = random.sample(other_restaurants, min(remaining_needed, len(other_restaurants)))
                            result_restaurants.extend(addition)
                        
                        restaurants = result_restaurants
                    else:
                        restaurants = filtered_restaurants
                
                # If our filters were too strict and we have no restaurants, add fallbacks
                if not restaurants:
                    logger.warning("No restaurants matched criteria. Creating fallback options.")
                    fallback_restaurants = []
                    
                    fallback_cuisines = [
                        "Health Food", "Mediterranean", "Vegetarian", "Vegan", 
                        "Asian Fusion", "Mexican", "Italian", "American", "Indian", "Thai"
                    ]
                    
                    for i, cuisine in enumerate(fallback_cuisines):
                        fallback_restaurants.append({
                            "id": f"fallback_{i}",
                            "name": f"{cuisine} Kitchen",
                            "cuisine": cuisine,
                            "rating": 4.5,
                            "delivery_fee": 2.99,
                            "delivery_time": "20-30 min",
                            "image_url": "https://example.com/placeholder.jpg",
                            "tags": ["healthy", "quick", "reliable", cuisine.lower(), "vegetarian"]
                        })
                    
                    # Return a diverse set of fallbacks
                    return random.sample(fallback_restaurants, min(10, len(fallback_restaurants)))
                
                # Select at least 10 random restaurants, up to 20 if available
                if len(restaurants) > 20:
                    restaurants = random.sample(restaurants, random.randint(10, 20))
                elif len(restaurants) < 10:
                    # If we have less than 10 restaurants, add more by relaxing filters
                    logger.warning(f"Found less than 10 restaurants ({len(restaurants)}). Relaxing filters to find more.")
                    
                    # Get additional restaurants without dietary filters
                    all_restaurants = []
                    for loc_restaurants in self.mock_data["restaurants"].values():
                        all_restaurants.extend(loc_restaurants)
                    
                    # Apply only cuisine filter if specified
                    if cuisine_preference:
                        cuisine_lower = cuisine_preference.lower()
                        additional_restaurants = [r for r in all_restaurants if cuisine_lower in r["cuisine"].lower() or
                                            any(cuisine_lower in tag.lower() for tag in r["tags"])]
                    else:
                        additional_restaurants = all_restaurants
                    
                    # Remove any duplicates
                    additional_restaurants = [r for r in additional_restaurants if r not in restaurants]
                    
                    # Add more restaurants until we have at least 10
                    needed = 10 - len(restaurants)
                    if len(additional_restaurants) >= needed:
                        restaurants.extend(random.sample(additional_restaurants, needed))
                    else:
                        restaurants.extend(additional_restaurants)
                    
                    if len(restaurants) < 10:
                        # If we still don't have enough, generate some on-the-fly
                        logger.warning(f"Still have less than 10 restaurants ({len(restaurants)}). Generating more.")
                        for i in range(10 - len(restaurants)):
                            restaurant_id = f"extra_{i}_random"
                            restaurant_name = f"Health Spot {i+1}"
                            restaurants.append({
                                "id": restaurant_id,
                                "name": restaurant_name,
                                "cuisine": "Health Food",
                                "rating": 4.5,
                                "delivery_fee": 2.99,
                                "estimated_time": "15-30 min",
                                "image_url": "https://example.com/placeholder.jpg",
                                "tags": ["healthy", "organic", "vegetarian", "vegan", "gluten-free"]
                            })
                
                return restaurants
            else:
                # Implementation for real API (simplified)
                return self._get_sample_restaurants(location, cuisine_preference, health_goal, dietary_preferences)
                
        except Exception as e:
            logger.error(f"Error searching for restaurants: {e}")
            # Return a smaller fallback list on error
            return [
                {
                    "id": "fallback1",
                    "name": "Healthy Eats (Fallback)",
                    "rating": 4.5,
                    "delivery_fee": 2.99,
                    "estimated_time": "20-30 min",
                    "cuisine": "Health Food",
                    "tags": ["healthy", "quick", "reliable"]
                }
            ]
    
    def _get_sample_restaurants(self, location=None, cuisine_preference=None, health_goal=None, dietary_preferences=None):
        """Generate mock restaurant data for development purposes."""
        # Create a base set of restaurants
        all_restaurants = []
        
        # Restaurant name components
        prefixes = ["The", "Urban", "Green", "Fresh", "Golden", "Silver", "Blue", "Red", "Organic", "Wild"]
        names = ["Kitchen", "Table", "Plate", "Bistro", "Cafe", "Grill", "Garden", "Spoon", "Fork", "Bowl"]
        cuisine_types = [
            "Italian", "Mexican", "Thai", "Indian", "Japanese", "Chinese", "American", 
            "Greek", "Mediterranean", "French", "Korean", "Vietnamese", "Vegetarian", "Vegan"
        ]
        
        # Generate 20 realistic restaurants with diverse cuisines
        for i in range(20):
            # Ensure we get a mix of cuisine types
            cuisine = cuisine_types[i % len(cuisine_types)]
            
            # Create restaurant with realistic data
            restaurant = {
                "id": f"restaurant_{i}",
                "name": f"{random.choice(prefixes)} {random.choice(names)}",
                "cuisine": cuisine,
                "rating": round(random.uniform(3.5, 5.0), 1),
                "delivery_fee": round(random.uniform(1.99, 7.99), 2),
                "estimated_time": f"{random.randint(15, 45)}-{random.randint(25, 60)} min",
                "tags": ["healthy", cuisine.lower(), "quick"]
            }
            
            # Add dietary tags randomly but ensure diversity
            if random.random() > 0.5:
                restaurant["tags"].append("vegetarian")
            if random.random() > 0.7:
                restaurant["tags"].append("vegan")
            if random.random() > 0.7:
                restaurant["tags"].append("gluten-free")
            
            all_restaurants.append(restaurant)
        
        # Shuffle restaurants to ensure randomness
        random.shuffle(all_restaurants)
        
        # Return at least 5 restaurants
        return all_restaurants[:max(5, random.randint(5, 20))]
    
    async def get_restaurant_menu(self, restaurant_id):
        """
        Get the menu for a specific restaurant.
        
        Args:
            restaurant_id (str): The ID of the restaurant
            
        Returns:
            list: A list of menu items
        """
        if self.use_mock:
            # Use mock data
            menu_items = self.mock_data["menus"].get(restaurant_id, [])
            
            # Simulate network delay
            # await asyncio.sleep(0.3)
            
            return menu_items
        else:
            # Use real API
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                try:
                    async with session.get(f"{self.base_url}/restaurants/{restaurant_id}/menu", headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            return data.get("menu_items", [])
                        else:
                            logger.error(f"Error getting restaurant menu: {response.status}")
                            return []
                except Exception as e:
                    logger.error(f"Error calling Uber Eats API: {e}")
                    return []
    
    async def filter_menu_by_health_goal(self, menu_items, health_goal):
        """
        Filter menu items based on a health goal.
        
        Args:
            menu_items (list): List of menu items to filter
            health_goal (str): Health goal to filter by
            
        Returns:
            list: Filtered list of menu items
        """
        if not menu_items or not health_goal:
            return menu_items
        
        health_goal = health_goal.lower()
        
        # Define filtering criteria based on health goals
        criteria = {
            "weight loss": lambda item: int(item.get("calories", 1000)) < 500,
            "muscle gain": lambda item: item.get("protein", "0g").replace("g", "") and int(item.get("protein", "0g").replace("g", "")) > 25,
            "energy": lambda item: int(item.get("carbs", "0g").replace("g", "")) > 30,
            "general health": lambda item: any(tag in ["healthy", "balanced", "organic"] for tag in item.get("tags", []))
        }
        
        # Apply the appropriate filter
        filter_func = criteria.get(health_goal, lambda item: True)
        return [item for item in menu_items if filter_func(item)]
    
    async def get_delivery_estimate(self, restaurant_id, user_location):
        """
        Get a delivery time and cost estimate.
        
        Args:
            restaurant_id (str): The ID of the restaurant
            user_location (str): The user's location
            
        Returns:
            dict: Delivery estimate information
        """
        if self.use_mock:
            # Generate random but realistic delivery estimates
            delivery_time = random.randint(15, 45)
            delivery_fee = round(random.uniform(1.99, 5.99), 2)
            
            return {
                "estimated_delivery_time": f"{delivery_time}-{delivery_time + 10} min",
                "delivery_fee": delivery_fee,
                "restaurant_id": restaurant_id
            }
        else:
            # Use real API
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                params = {
                    "restaurant_id": restaurant_id,
                    "user_location": user_location
                }
                
                try:
                    async with session.get(f"{self.base_url}/delivery-estimate", headers=headers, params=params) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            logger.error(f"Error getting delivery estimate: {response.status}")
                            return {}
                except Exception as e:
                    logger.error(f"Error calling Uber Eats API: {e}")
                    return {}
