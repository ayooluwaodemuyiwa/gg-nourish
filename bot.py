import os
import discord
import logging

from discord.ext import commands
from dotenv import load_dotenv
from agent import MistralAgent

PREFIX = "!"

# Setup logging
logger = logging.getLogger("discord")

# Load the environment variables
load_dotenv()

# Initialize the bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# Remove the default help command
bot.remove_command('help')

# Import the Mistral agent from the agent.py file
agent = MistralAgent()


# Get the token from the environment variables
token = os.getenv("DISCORD_TOKEN")


@bot.event
async def on_ready():
    """
    Called when the client is done preparing the data received from Discord.
    Prints message on terminal when bot successfully connects to discord.

    https://discordpy.readthedocs.io/en/latest/api.html#discord.on_ready
    """
    logger.info(f"{bot.user} has connected to Discord!")
    # Set the bot's activity to show it's a food delivery assistant
    await bot.change_presence(activity=discord.Game(name="GG Delivery | !help"))


@bot.event
async def on_message(message: discord.Message):
    """
    Called when a message is sent in any channel the bot can see.

    https://discordpy.readthedocs.io/en/latest/api.html#discord.on_message
    """
    # Don't delete this line! It's necessary for the bot to process commands.
    await bot.process_commands(message)

    # Ignore messages from self or other bots to prevent infinite loops.
    if message.author.bot or message.content.startswith(PREFIX):
        return

    # Process the message with the agent you wrote
    # Open up the agent.py file to customize the agent
    logger.info(f"Processing message from {message.author}: {message.content}")
    response = await agent.run(message)

    # Send the response back to the channel
    await message.reply(response)


# Commands

@bot.command(name="help", help="Shows this help message")
async def help_command(ctx):
    # Create the main embed for the help command
    embed = discord.Embed(
        title="GG Delivery Bot Commands",
        description="Here are all the available commands:",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name=f"{PREFIX}help", 
        value="Shows this help message", 
        inline=False
    )
    
    embed.add_field(
        name=f"{PREFIX}budget [amount]", 
        value="Sets your food budget or shows your current budget", 
        inline=False
    )
    
    embed.add_field(
        name=f"{PREFIX}address [delivery address]", 
        value="Sets your delivery address or shows your current address", 
        inline=False
    )
    
    embed.add_field(
        name=f"{PREFIX}location [city]", 
        value="Sets your default location for restaurant searches", 
        inline=False
    )
    
    embed.add_field(
        name=f"{PREFIX}preference [food preference]", 
        value="Adds a food preference or shows your current preferences", 
        inline=False
    )
    
    embed.add_field(
        name=f"{PREFIX}restaurants [location]", 
        value="Search for restaurants in a location", 
        inline=False
    )
    
    embed.add_field(
        name=f"{PREFIX}menu [restaurant name]", 
        value="View the menu for a restaurant", 
        inline=False
    )
    
    embed.add_field(
        name=f"{PREFIX}order [restaurant] [item1, item2, ...]", 
        value="Place an order directly from a restaurant", 
        inline=False
    )
    
    embed.add_field(
        name=f"{PREFIX}recommend [mood description]", 
        value="Get food recommendations based on your mood", 
        inline=False
    )
    
    embed.add_field(
        name=f"{PREFIX}profile", 
        value="View your saved delivery profile settings", 
        inline=False
    )
    
    embed.add_field(
        name=f"{PREFIX}cart", 
        value="View your current cart", 
        inline=False
    )
    
    embed.set_footer(text="Simply chat with me normally to discuss your order!")
    
    # Create interactive help view
    view = HelpView()
    
    await ctx.send(embed=embed, view=view)


@bot.command(name="budget", help="Set your budget for food orders")
async def budget_command(ctx, amount=None):
    if amount:
        response = await agent.set_budget(str(ctx.author.id), amount)
    else:
        user_data = agent._get_user_data(str(ctx.author.id))
        response = f"Your current budget is ${user_data['budget']:.2f}"
    
    await ctx.send(response)


@bot.command(name="address", help="Set your delivery address")
async def address_command(ctx, *, address=None):
    if address:
        response = await agent.set_address(str(ctx.author.id), address)
    else:
        user_data = agent._get_user_data(str(ctx.author.id))
        response = f"Your current delivery address is: {user_data['address'] or 'Not set'}"
    
    await ctx.send(response)


@bot.command(name="location", help="Set your default location for restaurant searches")
async def location_command(ctx, *, location=None):
    if location:
        response = await agent.set_location(str(ctx.author.id), location)
    else:
        user_data = agent._get_user_data(str(ctx.author.id))
        response = f"Your current location is: {user_data.get('default_location', 'Not set')}"
    
    await ctx.send(response)


@bot.command(name="preference", help="Add a food preference")
async def preference_command(ctx, *, preference=None):
    if preference:
        response = await agent.add_preference(str(ctx.author.id), preference)
    else:
        user_data = agent._get_user_data(str(ctx.author.id))
        prefs = user_data.get("preferences", [])
        if prefs:
            response = f"Your current food preferences: {', '.join(prefs)}"
        else:
            response = "You haven't set any food preferences yet."
    
    await ctx.send(response)


@bot.command(name="restaurants", help="Search for restaurants near a location")
async def restaurants_command(ctx, *, location=None):
    if not location:
        user_id = str(ctx.author.id)
        user_data = agent._get_user_data(user_id)
        location = user_data.get("default_location")
        
        if not location:
            await ctx.send("Please provide a location to search for restaurants or set a default location with `!location [city]`")
            return
    
    # First message to show we're processing
    processing_msg = await ctx.send(f"Searching for restaurants in {location}...")
    
    # Get restaurants from the agent
    restaurants = await agent.search_restaurants(location)
    
    # Create an embed for the restaurants
    embed = discord.Embed(
        title=f"Restaurants in {location}",
        description="Here are some restaurants near your location:",
        color=discord.Color.blue()
    )
    
    for restaurant in restaurants:
        embed.add_field(
            name=f"{restaurant['name']} - {restaurant['rating']}",
            value=f"Delivery fee: ${restaurant['delivery_fee']}\nEstimated time: {restaurant['estimated_time']}",
            inline=False
        )
    
    # Create UI for restaurant selection
    view = RestaurantSearchView(restaurants, agent, ctx.author.id)
    
    # Delete the processing message and send the restaurants
    await processing_msg.delete()
    await ctx.send(embed=embed, view=view)


@bot.command(name="menu", help="View a restaurant's menu")
async def menu_command(ctx, *, restaurant_name=None):
    if not restaurant_name:
        await ctx.send("Please provide a restaurant name to view the menu. For example: `!menu Pizza Palace`")
        return
    
    # First message to show we're processing
    processing_msg = await ctx.send(f"Fetching the menu for {restaurant_name}...")
    
    # Get the menu from the agent
    menu = await agent.get_restaurant_menu(restaurant_name)
    
    # Create an embed for the menu
    embed = discord.Embed(
        title=f"{restaurant_name} Menu",
        description="Here's what they offer:",
        color=discord.Color.green()
    )
    
    # Add items to the embed
    for item in menu:
        embed.add_field(
            name=f"{item['name']} - ${item['price']:.2f}",
            value=item['description'],
            inline=False
        )
    
    # Create UI components for ordering
    view = RestaurantMenuView(restaurant_name, menu, agent, ctx.author.id)
    
    # Delete the processing message and send the menu
    await processing_msg.delete()
    await ctx.send(embed=embed, view=view)


@bot.command(name="order", help="Place an order directly")
async def order_command(ctx, restaurant=None, *, items_str=None):
    if not restaurant or not items_str:
        await ctx.send("Please provide a restaurant name and items to order. For example: `!order 'Pizza Palace' 2x Pepperoni, 1x Fries`")
        return
    
    user_id = str(ctx.author.id)
    user_data = agent._get_user_data(user_id)
    
    # Check if address is set
    if not user_data["address"]:
        await ctx.send("You need to set your delivery address first. Use `!address` to set it.")
        return
    
    # Parse the items string
    # Format: "2x Pepperoni, 1x Fries" or "Pepperoni, Fries"
    items = []
    for item_str in items_str.split(","):
        item_str = item_str.strip()
        
        # Check if quantity is specified (e.g. "2x Pepperoni")
        if "x " in item_str and item_str.split("x ")[0].strip().isdigit():
            qty_str, name = item_str.split("x ", 1)
            try:
                quantity = int(qty_str.strip())
                items.append({"name": name.strip(), "quantity": quantity})
            except ValueError:
                items.append({"name": item_str, "quantity": 1})
        else:
            items.append({"name": item_str, "quantity": 1})
    
    # Send a message to indicate the order is being processed
    await ctx.send(f"Processing your order from {restaurant}...")
    
    # Place the order
    response = await agent.place_order(user_id, restaurant, items)
    
    # Send the response
    await ctx.send(response)


@bot.command(name="recommend", help="Get food recommendations based on your mood")
async def recommend_command(ctx, *, mood_description=None):
    if not mood_description:
        # Create a modal for input if no mood description provided
        modal = MoodInputModal()
        await ctx.send("Let's find food based on your mood! Click the button below to describe how you're feeling.", view=MoodInputView(ctx.author.id))
        return
    
    # First message to show we're processing
    processing_msg = await ctx.send("Analyzing your mood and finding the perfect food recommendations...")
    
    try:
        # Analyze mood
        mood_analysis = await agent.analyze_mood(mood_description)
        
        # Create an embed for the recommendations
        embed = discord.Embed(
            title="Food Recommendations Based on Your Mood",
            description=f"Based on your current mood, here are some food suggestions:",
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="Your Mood",
            value=mood_analysis["mood"],
            inline=False
        )
        
        embed.add_field(
            name="Food Suggestions",
            value=", ".join(mood_analysis["food_suggestions"]),
            inline=False
        )
        
        embed.add_field(
            name="Why These Foods",
            value=mood_analysis["reasoning"],
            inline=False
        )
        
        # Get user's location
        user_id = str(ctx.author.id)
        user_data = agent._get_user_data(user_id)
        location = user_data.get("default_location", "San Francisco")
        
        # Try to find restaurants that match the food suggestions
        suggested_restaurants = []
        for food in mood_analysis["food_suggestions"]:
            restaurants = await agent.search_restaurants(location, food)
            for restaurant in restaurants:
                if restaurant not in suggested_restaurants:
                    suggested_restaurants.append(restaurant)
                if len(suggested_restaurants) >= 3:  # Limit to 3 suggestions
                    break
            if len(suggested_restaurants) >= 3:
                break
        
        # Add restaurant suggestions if found
        if suggested_restaurants:
            restaurant_text = ""
            for restaurant in suggested_restaurants:
                restaurant_text += f"• {restaurant['name']} - Delivery fee: ${restaurant['delivery_fee']}, ETA: {restaurant['estimated_time']}\n"
            
            embed.add_field(
                name=f"Restaurants near {location} that might have what you're looking for:",
                value=restaurant_text,
                inline=False
            )
            
            # Create a view with restaurant selection options
            view = RecommendedRestaurantsView(suggested_restaurants, agent, ctx.author.id)
            
            # Delete the processing message and send the recommendations
            await processing_msg.delete()
            await ctx.send(embed=embed, view=view)
        else:
            # No matching restaurants found
            embed.set_footer(text="Use !restaurants to explore food options in your area")
            
            # Delete the processing message and send the recommendations
            await processing_msg.delete()
            await ctx.send(embed=embed)
        
    except Exception as e:
        # If something goes wrong, just fall back to a simple message
        await processing_msg.delete()
        await ctx.send(f"I recommend trying some comfort food like pizza, burgers, or your favorite local restaurant. What sounds good to you?")


@bot.command(name="profile", help="View your saved delivery profile")
async def profile_command(ctx):
    user_id = str(ctx.author.id)
    user_data = agent._get_user_data(user_id)
    
    embed = discord.Embed(
        title="Your GG Delivery Profile",
        description="Here are your current settings:",
        color=discord.Color.teal()
    )
    
    # Budget
    embed.add_field(
        name="Budget",
        value=f"${user_data['budget']:.2f}" if user_data['budget'] else "Not set",
        inline=True
    )
    
    # Location
    embed.add_field(
        name="Location",
        value=user_data.get('default_location', 'Not set'),
        inline=True
    )
    
    # Address
    embed.add_field(
        name="Delivery Address",
        value=user_data['address'] or "Not set",
        inline=False
    )
    
    # Preferences
    preferences = user_data.get('preferences', [])
    embed.add_field(
        name="Food Preferences",
        value=", ".join(preferences) if preferences else "No preferences set",
        inline=False
    )
    
    # Order History - future enhancement
    embed.add_field(
        name="Order History",
        value="Coming soon!",
        inline=False
    )
    
    embed.set_footer(text=f"User ID: {user_id}")
    
    # Create UI view with buttons to edit profile settings
    view = ProfileView(agent, user_id)
    
    await ctx.send(embed=embed, view=view)


@bot.command(name="cart", help="View your current cart")
async def cart_command(ctx):
    user_id = str(ctx.author.id)
    user_data = agent._get_user_data(user_id)
    
    if not user_data.get('cart', []):
        await ctx.send("Your cart is empty! Use the `!menu` command to browse restaurant menus and add items to your cart.")
        return
    
    # Create cart view with cart items
    view = CartView(agent, user_id)
    
    await display_cart(ctx, user_id, view)


async def display_cart(ctx, user_id, view=None):
    """Display the user's cart with a nice embed and optional view for buttons"""
    user_data = agent._get_user_data(user_id)
    cart = user_data.get('cart', [])
    
    if not cart:
        await ctx.send("Your cart is empty! Use the `!menu` command to browse restaurant menus and add items to your cart.")
        return
    
    # Create a nice embed for the cart
    embed = discord.Embed(
        title="🛒 Your Cart",
        description=f"Here are the items in your cart from {cart[0]['restaurant']}:",
        color=discord.Color.gold()
    )
    
    total = 0
    for index, item in enumerate(cart, 1):
        item_price = float(item['price'].replace('$', ''))
        item_quantity = item.get('quantity', 1)
        item_total = item_price * item_quantity
        total += item_total
        
        embed.add_field(
            name=f"{index}. {item['name']} (x{item_quantity})",
            value=f"${item_total:.2f} (${item_price:.2f} each)",
            inline=False
        )
    
    # Add delivery fee and tax estimate
    delivery_fee = 3.99
    tax = total * 0.07  # Assume 7% tax
    grand_total = total + delivery_fee + tax
    
    embed.add_field(
        name="Subtotal",
        value=f"${total:.2f}",
        inline=True
    )
    
    embed.add_field(
        name="Delivery Fee",
        value=f"${delivery_fee:.2f}",
        inline=True
    )
    
    embed.add_field(
        name="Estimated Tax",
        value=f"${tax:.2f}",
        inline=True
    )
    
    embed.add_field(
        name="Total",
        value=f"**${grand_total:.2f}**",
        inline=False
    )
    
    # Check if the user has an address set
    if not user_data.get('address'):
        embed.add_field(
            name="⚠️ No Delivery Address",
            value="You haven't set a delivery address yet. Use the `!address` command to set one.",
            inline=False
        )
    
    # Check if the total exceeds the budget
    budget = user_data.get('budget')
    if budget and grand_total > budget:
        embed.add_field(
            name="⚠️ Budget Warning",
            value=f"This order exceeds your budget of ${budget:.2f} by ${grand_total - budget:.2f}.",
            inline=False
        )
    
    embed.set_footer(text="Use the buttons below to manage your cart")
    
    # If a view was provided, use it, otherwise create a new one
    view = view or CartView(agent, user_id)
    
    # Send the message with the embed and view
    return await ctx.send(embed=embed, view=view)


# UI Components
class RestaurantSearchView(discord.ui.View):
    def __init__(self, restaurants, agent, user_id):
        super().__init__(timeout=300)  # 5 minute timeout
        self.restaurants = restaurants
        self.agent = agent
        self.user_id = str(user_id)
        
        # Add dropdown menu for restaurant selection
        select_options = [
            discord.SelectOption(
                label=restaurant['name'][:99],  # Discord limits option labels to 100 chars
                description=f"Rating: {restaurant['rating']}, Delivery: ${restaurant['delivery_fee']}",
                value=str(i)
            )
            for i, restaurant in enumerate(restaurants)
        ]
        
        restaurant_select = Select(
            placeholder="Select a restaurant to view menu",
            options=select_options,
            custom_id="restaurant_select"
        )
        
        restaurant_select.callback = self.restaurant_select_callback
        self.add_item(restaurant_select)
    
    async def restaurant_select_callback(self, interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        selected_idx = int(interaction.data['values'][0])
        restaurant = self.restaurants[selected_idx]
        
        # Get the menu for the selected restaurant
        menu = await self.agent.get_restaurant_menu(restaurant['name'])
        
        # Create an embed for the menu
        embed = discord.Embed(
            title=f"{restaurant['name']} Menu",
            description="Here's what they offer:",
            color=discord.Color.green()
        )
        
        # Add items to the embed
        for item in menu:
            embed.add_field(
                name=f"{item['name']} - ${item['price']:.2f}",
                value=item['description'],
                inline=False
            )
        
        # Create UI components for ordering
        view = RestaurantMenuView(restaurant['name'], menu, self.agent, self.user_id)
        
        # Send the menu
        await interaction.response.send_message(embed=embed, view=view)

class RestaurantMenuView(discord.ui.View):
    def __init__(self, restaurant_name, menu, agent, user_id):
        super().__init__(timeout=300)  # 5 minute timeout
        self.restaurant_name = restaurant_name
        self.menu = menu
        self.agent = agent
        self.user_id = str(user_id)
        self.cart = []
        
        # Add dropdown menu for item selection
        select_options = [
            discord.SelectOption(
                label=f"{item['name']} - ${item['price']:.2f}",
                description=item['description'][:100] if len(item['description']) <= 100 else item['description'][:97] + "...",
                value=str(i)
            )
            for i, item in enumerate(menu)
        ]
        
        item_select = Select(
            placeholder="Add items to your order",
            options=select_options,
            custom_id="menu_item_select"
        )
        
        item_select.callback = self.item_select_callback
        self.add_item(item_select)
        
        # Add view cart button
        view_cart_button = Button(
            label="View Cart", 
            style=discord.ButtonStyle.primary,
            custom_id="view_cart"
        )
        view_cart_button.callback = self.view_cart_callback
        self.add_item(view_cart_button)
        
        # Add checkout button
        checkout_button = Button(
            label="Checkout", 
            style=discord.ButtonStyle.success,
            custom_id="checkout"
        )
        checkout_button.callback = self.checkout_callback
        self.add_item(checkout_button)
    
    async def item_select_callback(self, interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This menu is not for you!", ephemeral=True)
            return
            
        selected_idx = int(interaction.data['values'][0])
        selected_item = self.menu[selected_idx]
        
        # Add item to cart
        item_with_qty = {
            "name": selected_item['name'],
            "price": selected_item['price'],
            "quantity": 1
        }
        
        # Check if item is already in cart
        for item in self.cart:
            if item["name"] == selected_item['name']:
                item["quantity"] += 1
                await interaction.response.send_message(f"Added another {selected_item['name']} to your cart!", ephemeral=True)
                return
        
        self.cart.append(item_with_qty)
        await interaction.response.send_message(f"Added {selected_item['name']} to your cart!", ephemeral=True)
    
    async def view_cart_callback(self, interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This cart is not yours!", ephemeral=True)
            return
        
        if not self.cart:
            await interaction.response.send_message("Your cart is empty!", ephemeral=True)
            return
        
        # Create an embed for the cart
        embed = discord.Embed(
            title="Your Cart",
            description=f"Items in your cart from {self.restaurant_name}:",
            color=discord.Color.gold()
        )
        
        total = 0
        for item in self.cart:
            item_total = item["price"].replace('$', '') * item["quantity"]
            total += item_total
            embed.add_field(
                name=f"{item['quantity']}x {item['name']}",
                value=f"${item_total:.2f} (${item['price']} each)",
                inline=False
            )
        
        embed.add_field(
            name="Total",
            value=f"${total:.2f}",
            inline=False
        )
        
        # Create a view for cart actions
        view = CartActionView(self.restaurant_name, self.cart, self.agent, self.user_id)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def checkout_callback(self, interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This cart is not yours!", ephemeral=True)
            return
        
        if not self.cart:
            await interaction.response.send_message("Your cart is empty! Add some items first.", ephemeral=True)
            return
        
        # Get user data to check address
        user_data = self.agent._get_user_data(self.user_id)
        
        if not user_data["address"]:
            # Prompt user to enter address
            modal = AddressModal(self.restaurant_name, self.cart, self.agent, self.user_id)
            await interaction.response.send_modal(modal)
        else:
            # Show confirmation view
            total = sum(item["price"].replace('$', '') * item["quantity"] for item in self.cart)
            
            embed = discord.Embed(
                title="Order Confirmation",
                description=f"Ready to place your order from {self.restaurant_name}?",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="Delivery Address",
                value=user_data["address"],
                inline=False
            )
            
            embed.add_field(
                name="Total",
                value=f"${total:.2f}",
                inline=False
            )
            
            view = OrderConfirmationView(self.restaurant_name, self.cart, self.agent, self.user_id)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class CartActionView(discord.ui.View):
    def __init__(self, restaurant_name, cart, agent, user_id):
        super().__init__(timeout=300)
        self.restaurant_name = restaurant_name
        self.cart = cart
        self.agent = agent
        self.user_id = str(user_id)
        
        # Add clear cart button
        clear_button = Button(
            label="Clear Cart", 
            style=discord.ButtonStyle.danger,
            custom_id="clear_cart"
        )
        clear_button.callback = self.clear_cart_callback
        self.add_item(clear_button)
        
        # Add checkout button
        checkout_button = Button(
            label="Checkout", 
            style=discord.ButtonStyle.success,
            custom_id="cart_checkout"
        )
        checkout_button.callback = self.checkout_callback
        self.add_item(checkout_button)
    
    async def clear_cart_callback(self, interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This cart is not yours!", ephemeral=True)
            return
        
        self.cart.clear()
        await interaction.response.send_message("Your cart has been cleared!", ephemeral=True)
    
    async def checkout_callback(self, interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This cart is not yours!", ephemeral=True)
            return
        
        # Get user data to check address
        user_data = self.agent._get_user_data(self.user_id)
        
        if not user_data["address"]:
            # Prompt user to enter address
            modal = AddressModal(self.restaurant_name, self.cart, self.agent, self.user_id)
            await interaction.response.send_modal(modal)
        else:
            # Show confirmation view
            total = sum(item["price"].replace('$', '') * item["quantity"] for item in self.cart)
            
            embed = discord.Embed(
                title="Order Confirmation",
                description=f"Ready to place your order from {self.restaurant_name}?",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="Delivery Address",
                value=user_data["address"],
                inline=False
            )
            
            embed.add_field(
                name="Total",
                value=f"${total:.2f}",
                inline=False
            )
            
            view = OrderConfirmationView(self.restaurant_name, self.cart, self.agent, self.user_id)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class AddressModal(discord.ui.Modal, title="Enter Delivery Address"):
    def __init__(self, restaurant_name, cart, agent, user_id):
        super().__init__()
        self.restaurant_name = restaurant_name
        self.cart = cart
        self.agent = agent
        self.user_id = user_id
        
        self.address = TextInput(
            label="Delivery Address",
            placeholder="Enter your full delivery address",
            style=discord.TextStyle.paragraph,
            required=True
        )
        
        self.add_item(self.address)
    
    async def on_submit(self, interaction):
        # Save the address to user data
        user_data = self.agent._get_user_data(self.user_id)
        user_data["address"] = self.address.value
        self.agent._save_user_data()
        
        # Show confirmation view
        total = sum(item["price"].replace('$', '') * item["quantity"] for item in self.cart)
        
        embed = discord.Embed(
            title="Order Confirmation",
            description=f"Ready to place your order from {self.restaurant_name}?",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="Delivery Address",
            value=self.address.value,
            inline=False
        )
        
        embed.add_field(
            name="Total",
            value=f"${total:.2f}",
            inline=False
        )
        
        view = OrderConfirmationView(self.restaurant_name, self.cart, self.agent, self.user_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class OrderConfirmationView(discord.ui.View):
    def __init__(self, restaurant_name, cart, agent, user_id):
        super().__init__(timeout=300)
        self.restaurant_name = restaurant_name
        self.cart = cart
        self.agent = agent
        self.user_id = user_id
        
        # Add cancel button
        cancel_button = Button(
            label="Cancel", 
            style=discord.ButtonStyle.secondary,
            custom_id="cancel_order"
        )
        cancel_button.callback = self.cancel_callback
        self.add_item(cancel_button)
        
        # Add confirm button
        confirm_button = Button(
            label="Confirm Order", 
            style=discord.ButtonStyle.success,
            custom_id="confirm_order"
        )
        confirm_button.callback = self.confirm_callback
        self.add_item(confirm_button)
    
    async def cancel_callback(self, interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This order is not yours!", ephemeral=True)
            return
        
        await interaction.response.send_message("Order cancelled.", ephemeral=True)
    
    async def confirm_callback(self, interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This order is not yours!", ephemeral=True)
            return
        
        # Format items for the agent
        items = [{"name": item["name"], "quantity": item["quantity"]} for item in self.cart]
        
        # Place the order
        response = await self.agent.place_order(self.user_id, self.restaurant_name, items)
        
        # Send confirmation
        embed = discord.Embed(
            title="Order Placed!",
            description=response,
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed)

class ProfileView(discord.ui.View):
    def __init__(self, agent, user_id):
        super().__init__(timeout=300)  # 5 minute timeout
        self.agent = agent
        self.user_id = str(user_id)
        
        # Add buttons for each setting
        edit_budget_button = Button(
            label="Edit Budget", 
            style=discord.ButtonStyle.primary,
            custom_id="edit_budget"
        )
        edit_budget_button.callback = self.edit_budget_callback
        self.add_item(edit_budget_button)
        
        edit_location_button = Button(
            label="Edit Location", 
            style=discord.ButtonStyle.primary,
            custom_id="edit_location"
        )
        edit_location_button.callback = self.edit_location_callback
        self.add_item(edit_location_button)
        
        edit_address_button = Button(
            label="Edit Address", 
            style=discord.ButtonStyle.primary,
            custom_id="edit_address"
        )
        edit_address_button.callback = self.edit_address_callback
        self.add_item(edit_address_button)
        
        edit_preferences_button = Button(
            label="Edit Preferences", 
            style=discord.ButtonStyle.primary,
            custom_id="edit_preferences"
        )
        edit_preferences_button.callback = self.edit_preferences_callback
        self.add_item(edit_preferences_button)
    
    async def edit_budget_callback(self, interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This profile is not yours!", ephemeral=True)
            return
        
        # Show budget modal
        modal = BudgetModal(self.agent, self.user_id)
        await interaction.response.send_modal(modal)
    
    async def edit_location_callback(self, interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This profile is not yours!", ephemeral=True)
            return
        
        # Show location modal
        modal = LocationModal(self.agent, self.user_id)
        await interaction.response.send_modal(modal)
    
    async def edit_address_callback(self, interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This profile is not yours!", ephemeral=True)
            return
        
        # Show address modal
        modal = AddressEditModal(self.agent, self.user_id)
        await interaction.response.send_modal(modal)
    
    async def edit_preferences_callback(self, interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This profile is not yours!", ephemeral=True)
            return
        
        # Show preferences modal
        modal = PreferencesModal(self.agent, self.user_id)
        await interaction.response.send_modal(modal)

class BudgetModal(discord.ui.Modal, title="Set Your Budget"):
    def __init__(self, agent, user_id):
        super().__init__()
        self.agent = agent
        self.user_id = user_id
        
        # Get current budget
        user_data = agent._get_user_data(user_id)
        current_budget = user_data['budget'] or 0
        
        self.budget = TextInput(
            label="Budget Amount ($)",
            placeholder="Enter your budget (e.g. 25.00)",
            default=str(current_budget) if current_budget else "",
            required=True
        )
        
        self.add_item(self.budget)
    
    async def on_submit(self, interaction):
        try:
            # Update budget
            budget_value = float(self.budget.value)
            user_data = self.agent._get_user_data(self.user_id)
            user_data['budget'] = budget_value
            self.agent._save_user_data()
            
            await interaction.response.send_message(f"Your budget has been updated to ${budget_value:.2f}!", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("Please enter a valid number for your budget.", ephemeral=True)

class LocationModal(discord.ui.Modal, title="Set Your Location"):
    def __init__(self, agent, user_id):
        super().__init__()
        self.agent = agent
        self.user_id = user_id
        
        # Get current location
        user_data = agent._get_user_data(user_id)
        current_location = user_data.get('default_location', '')
        
        self.location = TextInput(
            label="Your Location",
            placeholder="Enter your city (e.g. San Francisco)",
            default=current_location,
            required=True
        )
        
        self.add_item(self.location)
    
    async def on_submit(self, interaction):
        # Update location
        location_value = self.location.value
        user_data = self.agent._get_user_data(self.user_id)
        user_data['default_location'] = location_value
        self.agent._save_user_data()
        
        await interaction.response.send_message(f"Your default location has been updated to {location_value}!", ephemeral=True)

class AddressEditModal(discord.ui.Modal, title="Set Your Delivery Address"):
    def __init__(self, agent, user_id):
        super().__init__()
        self.agent = agent
        self.user_id = user_id
        
        # Get current address
        user_data = agent._get_user_data(user_id)
        current_address = user_data['address'] or ''
        
        self.address = TextInput(
            label="Delivery Address",
            placeholder="Enter your full delivery address",
            default=current_address,
            style=discord.TextStyle.paragraph,
            required=True
        )
        
        self.add_item(self.address)
    
    async def on_submit(self, interaction):
        # Update address
        address_value = self.address.value
        user_data = self.agent._get_user_data(self.user_id)
        user_data['address'] = address_value
        self.agent._save_user_data()
        
        await interaction.response.send_message(f"Your delivery address has been updated!", ephemeral=True)

class PreferencesModal(discord.ui.Modal, title="Set Your Food Preferences"):
    def __init__(self, agent, user_id):
        super().__init__()
        self.agent = agent
        self.user_id = user_id
        
        # Get current preferences
        user_data = agent._get_user_data(user_id)
        current_preferences = ', '.join(user_data.get('preferences', []))
        
        self.preferences = TextInput(
            label="Food Preferences",
            placeholder="Enter preferences, separated by commas (e.g. Italian, Vegan, Spicy)",
            default=current_preferences,
            style=discord.TextStyle.paragraph,
            required=False
        )
        
        self.add_item(self.preferences)
    
    async def on_submit(self, interaction):
        # Update preferences
        preferences_value = self.preferences.value
        user_data = self.agent._get_user_data(self.user_id)
        
        # Parse preferences
        if preferences_value.strip():
            preferences_list = [p.strip() for p in preferences_value.split(',') if p.strip()]
            user_data['preferences'] = preferences_list
        else:
            user_data['preferences'] = []
            
        self.agent._save_user_data()
        
        if user_data['preferences']:
            await interaction.response.send_message(f"Your food preferences have been updated to: {', '.join(user_data['preferences'])}", ephemeral=True)
        else:
            await interaction.response.send_message("Your food preferences have been cleared.", ephemeral=True)

class MoodInputView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=300)  # 5 minute timeout
        self.user_id = str(user_id)
        
        # Add button to open modal
        describe_mood_button = Button(
            label="Describe Your Mood", 
            style=discord.ButtonStyle.primary,
            custom_id="describe_mood"
        )
        describe_mood_button.callback = self.describe_mood_callback
        self.add_item(describe_mood_button)
    
    async def describe_mood_callback(self, interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This button is not for you!", ephemeral=True)
            return
        
        # Create and show the modal
        modal = MoodInputModal()
        await interaction.response.send_modal(modal)

class MoodInputModal(discord.ui.Modal, title="Describe Your Mood"):
    def __init__(self):
        super().__init__()
        
        self.mood_description = TextInput(
            label="How are you feeling?",
            placeholder="I'm feeling...",
            style=discord.TextStyle.paragraph,
            required=True
        )
        
        self.add_item(self.mood_description)
    
    async def on_submit(self, interaction):
        await interaction.response.defer()
        
        # Send a message that we're processing
        processing_msg = await interaction.followup.send("Analyzing your mood and finding the perfect food recommendations...")
        
        try:
            # Analyze mood
            mood_analysis = await agent.analyze_mood(self.mood_description.value)
            
            # Create an embed for the recommendations
            embed = discord.Embed(
                title="Food Recommendations Based on Your Mood",
                description=f"Based on your current mood, here are some food suggestions:",
                color=discord.Color.purple()
            )
            
            embed.add_field(
                name="Your Mood",
                value=mood_analysis["mood"],
                inline=False
            )
            
            embed.add_field(
                name="Food Suggestions",
                value=", ".join(mood_analysis["food_suggestions"]),
                inline=False
            )
            
            embed.add_field(
                name="Why These Foods",
                value=mood_analysis["reasoning"],
                inline=False
            )
            
            # Get user's location
            user_id = str(interaction.user.id)
            user_data = agent._get_user_data(user_id)
            location = user_data.get("default_location", "San Francisco")
            
            # Try to find restaurants that match the food suggestions
            suggested_restaurants = []
            for food in mood_analysis["food_suggestions"]:
                restaurants = await agent.search_restaurants(location, food)
                for restaurant in restaurants:
                    if restaurant not in suggested_restaurants:
                        suggested_restaurants.append(restaurant)
                    if len(suggested_restaurants) >= 3:  # Limit to 3 suggestions
                        break
                if len(suggested_restaurants) >= 3:
                    break
            
            # Add restaurant suggestions if found
            if suggested_restaurants:
                restaurant_text = ""
                for restaurant in suggested_restaurants:
                    restaurant_text += f"• {restaurant['name']} - Delivery fee: ${restaurant['delivery_fee']}, ETA: {restaurant['estimated_time']}\n"
                
                embed.add_field(
                    name=f"Restaurants near {location} that might have what you're looking for:",
                    value=restaurant_text,
                    inline=False
                )
                
                # Create a view with restaurant selection options
                view = RecommendedRestaurantsView(suggested_restaurants, agent, user_id)
                
                # Delete the processing message and send the recommendations
                await processing_msg.delete()
                await interaction.followup.send(embed=embed, view=view)
            else:
                # No matching restaurants found
                embed.set_footer(text="Use !restaurants to explore food options in your area")
                
                # Delete the processing message and send the recommendations
                await processing_msg.delete()
                await interaction.followup.send(embed=embed)
            
        except Exception as e:
            # If something goes wrong, just fall back to a simple message
            await processing_msg.delete()
            await interaction.followup.send(f"I recommend trying some comfort food like pizza, burgers, or your favorite local restaurant. What sounds good to you?")

class RecommendedRestaurantsView(discord.ui.View):
    def __init__(self, restaurants, agent, user_id):
        super().__init__(timeout=300)  # 5 minute timeout
        self.restaurants = restaurants
        self.agent = agent
        self.user_id = str(user_id)
        
        # Add buttons for each restaurant
        for i, restaurant in enumerate(restaurants[:3]):  # Limit to 3 restaurants
            button = Button(
                label=restaurant['name'][:80], 
                style=discord.ButtonStyle.primary,
                custom_id=f"restaurant_{i}"
            )
            button.callback = self.make_restaurant_callback(i)
            self.add_item(button)
    
    def make_restaurant_callback(self, idx):
        async def restaurant_callback(interaction):
            if str(interaction.user.id) != self.user_id:
                await interaction.response.send_message("This button is not for you!", ephemeral=True)
                return
                
            restaurant = self.restaurants[idx]
            
            # Get the menu for the selected restaurant
            menu = await self.agent.get_restaurant_menu(restaurant['name'])
            
            # Create an embed for the menu
            embed = discord.Embed(
                title=f"{restaurant['name']} Menu",
                description="Here's what they offer:",
                color=discord.Color.green()
            )
            
            # Add items to the embed
            for item in menu:
                embed.add_field(
                    name=f"{item['name']} - ${item['price']:.2f}",
                    value=item['description'],
                    inline=False
                )
            
            # Create UI components for ordering
            view = RestaurantMenuView(restaurant['name'], menu, self.agent, self.user_id)
            
            # Send the menu
            await interaction.response.send_message(embed=embed, view=view)
        
        return restaurant_callback

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)  # 5 minute timeout
        
        # Add example buttons to demonstrate UI capabilities
        get_started_button = Button(
            label="🚀 Get Started", 
            style=discord.ButtonStyle.success,
            custom_id="get_started"
        )
        get_started_button.callback = self.get_started_callback
        self.add_item(get_started_button)
        
        features_button = Button(
            label="✨ Features", 
            style=discord.ButtonStyle.primary,
            custom_id="features"
        )
        features_button.callback = self.features_callback
        self.add_item(features_button)
        
        examples_button = Button(
            label="📝 Examples", 
            style=discord.ButtonStyle.secondary,
            custom_id="examples"
        )
        examples_button.callback = self.examples_callback
        self.add_item(examples_button)
    
    async def get_started_callback(self, interaction):
        embed = discord.Embed(
            title="Getting Started with GG Delivery",
            description="Follow these steps to start ordering food:",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="1. Set Your Location",
            value="Use `!location [city]` to set your default location for restaurant searches",
            inline=False
        )
        
        embed.add_field(
            name="2. Set Your Address",
            value="Use `!address [full address]` to set your delivery address",
            inline=False
        )
        
        embed.add_field(
            name="3. Set Your Budget",
            value="Use `!budget [amount]` to set your food budget",
            inline=False
        )
        
        embed.add_field(
            name="4. Find Restaurants",
            value="Use `!restaurants` to see restaurants in your area",
            inline=False
        )
        
        embed.add_field(
            name="5. View Menus & Order",
            value="Click on a restaurant to view its menu and add items to your cart",
            inline=False
        )
        
        embed.set_footer(text="Or just tell me what you're craving, and I'll help you find it!")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def features_callback(self, interaction):
        embed = discord.Embed(
            title="GG Delivery Features",
            description="Here's what you can do with GG Delivery:",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🍔 Restaurant Search",
            value="Find restaurants in your area with interactive menus",
            inline=True
        )
        
        embed.add_field(
            name="🛒 Easy Ordering",
            value="Add items to your cart with just a click",
            inline=True
        )
        
        embed.add_field(
            name="😊 Mood-Based Recommendations",
            value="Get food suggestions based on how you're feeling",
            inline=True
        )
        
        embed.add_field(
            name="👤 User Profiles",
            value="Save your preferences, budget, and delivery address",
            inline=True
        )
        
        embed.add_field(
            name="💬 Natural Conversation",
            value="Just chat normally to discuss your food options",
            inline=True
        )
        
        embed.add_field(
            name="📱 Modern UI",
            value="Interactive buttons, dropdowns, and forms",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def examples_callback(self, interaction):
        embed = discord.Embed(
            title="Example Commands",
            description="Here are some examples of how to use GG Delivery:",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="Setting Up",
            value="```\n!location New York\n!address 123 Main St, Apt 4B, New York, NY\n!budget 30\n```",
            inline=False
        )
        
        embed.add_field(
            name="Finding Food",
            value="```\n!restaurants\n!menu Pizza Palace\n!recommend I'm feeling tired and need comfort food\n```",
            inline=False
        )
        
        embed.add_field(
            name="Placing Orders",
            value="```\n!order \"Pizza Palace\" 1x Pepperoni, 2x Cheese Sticks\n```",
            inline=False
        )
        
        embed.add_field(
            name="Natural Language",
            value="You can also just chat normally:\n```\nI'm craving pizza tonight\nWhat's good for a rainy day?\nI want something under $20\n```",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class CartView(discord.ui.View):
    def __init__(self, agent, user_id):
        super().__init__(timeout=300)  # 5 minute timeout
        self.agent = agent
        self.user_id = user_id
        
        # Add buttons for cart management
        clear_cart_button = Button(
            label="🗑️ Clear Cart", 
            style=discord.ButtonStyle.danger,
            custom_id="clear_cart"
        )
        clear_cart_button.callback = self.clear_cart_callback
        self.add_item(clear_cart_button)
        
        update_quantities_button = Button(
            label="✏️ Update Quantities", 
            style=discord.ButtonStyle.secondary,
            custom_id="update_quantities"
        )
        update_quantities_button.callback = self.update_quantities_callback
        self.add_item(update_quantities_button)
        
        checkout_button = Button(
            label="✅ Checkout", 
            style=discord.ButtonStyle.success,
            custom_id="checkout"
        )
        checkout_button.callback = self.checkout_callback
        self.add_item(checkout_button)
    
    async def clear_cart_callback(self, interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This is not your cart!", ephemeral=True)
            return
        
        # Ask for confirmation
        view = ClearCartConfirmView(self.agent, self.user_id)
        await interaction.response.send_message("Are you sure you want to clear your cart?", view=view, ephemeral=True)
    
    async def update_quantities_callback(self, interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This is not your cart!", ephemeral=True)
            return
        
        # Show a modal to update quantities
        modal = UpdateCartQuantitiesModal(self.agent, self.user_id)
        await interaction.response.send_modal(modal)
    
    async def checkout_callback(self, interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This is not your cart!", ephemeral=True)
            return
        
        user_data = self.agent._get_user_data(self.user_id)
        
        # Check if address is set
        if not user_data.get('address'):
            # Show address modal
            modal = AddressModal(self.agent, self.user_id, is_checkout=True)
            return await interaction.response.send_modal(modal)
        
        # Show checkout modal
        modal = CheckoutModal(self.agent, self.user_id)
        await interaction.response.send_modal(modal)

class ClearCartConfirmView(discord.ui.View):
    def __init__(self, agent, user_id):
        super().__init__(timeout=60)  # 1 minute timeout
        self.agent = agent
        self.user_id = user_id
        
        # Add confirmation buttons
        yes_button = Button(
            label="Yes, Clear Cart", 
            style=discord.ButtonStyle.danger,
            custom_id="confirm_clear"
        )
        yes_button.callback = self.confirm_callback
        self.add_item(yes_button)
        
        no_button = Button(
            label="No, Keep Items", 
            style=discord.ButtonStyle.secondary,
            custom_id="cancel_clear"
        )
        no_button.callback = self.cancel_callback
        self.add_item(no_button)
    
    async def confirm_callback(self, interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This is not your cart!", ephemeral=True)
            return
        
        # Clear the cart
        user_data = self.agent._get_user_data(self.user_id)
        user_data['cart'] = []
        self.agent._save_user_data()
        
        await interaction.response.edit_message(content="Your cart has been cleared!", view=None)
        
        # Update the original cart message
        ctx = await bot.get_context(interaction.message)
        await ctx.send("Your cart has been cleared! Use `!menu` to browse restaurant menus and add items.")
    
    async def cancel_callback(self, interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("This is not your cart!", ephemeral=True)
            return
        
        # Just close the confirmation message
        await interaction.response.edit_message(content="Cart clearing canceled.", view=None)

class UpdateCartQuantitiesModal(discord.ui.Modal, title="Update Cart Quantities"):
    def __init__(self, agent, user_id):
        super().__init__()
        self.agent = agent
        self.user_id = user_id
        
        # Get current cart
        user_data = agent._get_user_data(user_id)
        cart = user_data.get('cart', [])
        
        # Create a text input for each item (up to 5, which is the max for modals)
        self.item_inputs = []
        for i, item in enumerate(cart[:5]):  # Discord modals can only have 5 inputs max
            item_input = TextInput(
                label=f"{item['name']} (${float(item['price'].replace('$', '')):.2f})",
                placeholder="Enter quantity (0 to remove)",
                default=str(item.get('quantity', 1)),
                required=True,
                max_length=2
            )
            self.add_item(item_input)
            self.item_inputs.append(item_input)
    
    async def on_submit(self, interaction):
        try:
            # Update quantities
            user_data = self.agent._get_user_data(self.user_id)
            cart = user_data.get('cart', [])
            
            # Only process as many items as we have inputs for
            updated_cart = []
            for i, item_input in enumerate(self.item_inputs):
                if i < len(cart):
                    quantity = int(item_input.value)
                    if quantity > 0:
                        cart[i]['quantity'] = quantity
                        updated_cart.append(cart[i])
            
            # Keep any items beyond the first 5 (if any)
            if len(cart) > 5:
                updated_cart.extend(cart[5:])
            
            user_data['cart'] = updated_cart
            self.agent._save_user_data()
            
            await interaction.response.send_message("Your cart has been updated!", ephemeral=True)
            
            # Refresh the cart display
            ctx = await bot.get_context(interaction.message)
            if ctx.channel:
                await display_cart(ctx, self.user_id)
        
        except ValueError:
            await interaction.response.send_message("Please enter valid numbers for quantities.", ephemeral=True)

class AddressModal(discord.ui.Modal, title="Delivery Address"):
    def __init__(self, agent, user_id, is_checkout=False):
        super().__init__()
        self.agent = agent
        self.user_id = user_id
        self.is_checkout = is_checkout
        
        # Get current address
        user_data = agent._get_user_data(user_id)
        current_address = user_data.get('address', '')
        
        self.address = TextInput(
            label="Delivery Address",
            placeholder="Enter your full delivery address",
            default=current_address,
            style=discord.TextStyle.paragraph,
            required=True
        )
        
        self.add_item(self.address)
    
    async def on_submit(self, interaction):
        # Update address
        address_value = self.address.value
        user_data = self.agent._get_user_data(self.user_id)
        user_data['address'] = address_value
        self.agent._save_user_data()
        
        if self.is_checkout:
            # Continue to checkout
            modal = CheckoutModal(self.agent, self.user_id)
            await interaction.response.send_modal(modal)
        else:
            await interaction.response.send_message(f"Your delivery address has been set to: {address_value}", ephemeral=True)

class CheckoutModal(discord.ui.Modal, title="Complete Your Order"):
    def __init__(self, agent, user_id):
        super().__init__()
        self.agent = agent
        self.user_id = user_id
        
        # Get user data and cart info
        user_data = agent._get_user_data(user_id)
        cart = user_data.get('cart', [])
        
        if not cart:
            return
        
        # Calculate total
        total = sum(float(item['price'].replace('$', '')) * item.get('quantity', 1) for item in cart)
        delivery_fee = 3.99
        tax = total * 0.07
        grand_total = total + delivery_fee + tax
        
        # Create inputs for payment and special instructions
        self.payment_method = Select(
            placeholder="Select payment method",
            options=[
                discord.SelectOption(label="Credit Card", value="credit_card"),
                discord.SelectOption(label="PayPal", value="paypal"),
                discord.SelectOption(label="Cash on Delivery", value="cash")
            ],
            min_values=1,
            max_values=1
        )
        
        self.special_instructions = TextInput(
            label="Special Instructions (Optional)",
            placeholder="Enter any special delivery instructions",
            required=False,
            style=discord.TextStyle.paragraph
        )
        
        self.add_item(self.payment_method)
        self.add_item(self.special_instructions)
    
    async def on_submit(self, interaction):
        # Process the order
        user_data = self.agent._get_user_data(self.user_id)
        cart = user_data.get('cart', [])
        
        # Create a nice embed for the order confirmation
        embed = discord.Embed(
            title="🎉 Order Confirmed!",
            description=f"Your order from {cart[0]['restaurant']} has been placed.",
            color=discord.Color.green()
        )
        
        # Calculate the total
        total = sum(float(item['price'].replace('$', '')) * item.get('quantity', 1) for item in cart)
        delivery_fee = 3.99
        tax = total * 0.07
        grand_total = total + delivery_fee + tax
        
        # Add order details
        items_text = "\n".join([f"• {item.get('quantity', 1)}x {item['name']} - ${float(item['price'].replace('$', '')) * item.get('quantity', 1):.2f}" for item in cart])
        
        embed.add_field(
            name="Order Items",
            value=items_text,
            inline=False
        )
        
        embed.add_field(
            name="Delivery Address",
            value=user_data.get('address', 'No address specified'),
            inline=False
        )
        
        if self.special_instructions.value:
            embed.add_field(
                name="Special Instructions",
                value=self.special_instructions.value,
                inline=False
            )
        
        embed.add_field(
            name="Payment Method",
            value=self.payment_method.values[0].replace('_', ' ').title(),
            inline=True
        )
        
        embed.add_field(
            name="Total Amount",
            value=f"${grand_total:.2f}",
            inline=True
        )
        
        # Generate a random order number and estimated delivery time
        import random
        from datetime import datetime, timedelta
        
        order_number = f"GG-{random.randint(10000, 99999)}"
        delivery_time = datetime.now() + timedelta(minutes=random.randint(30, 60))
        delivery_time_str = delivery_time.strftime("%I:%M %p")
        
        embed.add_field(
            name="Order Number",
            value=order_number,
            inline=True
        )
        
        embed.add_field(
            name="Estimated Delivery",
            value=delivery_time_str,
            inline=True
        )
        
        # Add a tracking button
        track_order_button = Button(
            label="📍 Track Order", 
            style=discord.ButtonStyle.primary,
            custom_id=f"track_order_{order_number}"
        )
        
        view = discord.ui.View(timeout=None)
        view.add_item(track_order_button)
        
        # Clear the cart
        user_data['cart'] = []
        
        # Store the order in order history (if we had one)
        if 'order_history' not in user_data:
            user_data['order_history'] = []
        
        user_data['order_history'].append({
            'order_number': order_number,
            'restaurant': cart[0]['restaurant'],
            'items': [{'name': item['name'], 'quantity': item.get('quantity', 1), 'price': item['price']} for item in cart],
            'total': grand_total,
            'address': user_data.get('address', ''),
            'payment_method': self.payment_method.values[0],
            'special_instructions': self.special_instructions.value,
            'timestamp': datetime.now().isoformat(),
            'status': 'confirmed',
            'estimated_delivery': delivery_time_str
        })
        
        self.agent._save_user_data()
        
        await interaction.response.send_message(embed=embed, view=view)

# Start the bot, connecting it to the gateway
bot.run(token)
