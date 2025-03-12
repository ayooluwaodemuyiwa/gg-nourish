import os
import json
import asyncio
import webbrowser
from aiohttp import web
from urllib.parse import quote

class WorkoutUIServer:
    def __init__(self, host='localhost', port=8080):
        """Initialize the workout UI server"""
        self.host = host
        self.port = port
        self.app = web.Application()
        self.setup_routes()
        self.runner = None
        self.site = None
        
    def setup_routes(self):
        """Set up the server routes"""
        # Static files
        static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
        self.app.router.add_static('/static', static_path)
        
        # UI files
        ui_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ui')
        self.app.router.add_static('/ui', ui_path)
        
        # API routes
        self.app.router.add_get('/api/workout', self.get_workout)
        self.app.router.add_post('/api/workout/complete', self.complete_workout)
        
        # Main route
        self.app.router.add_get('/', self.index_handler)
        
    async def index_handler(self, request):
        """Handle the index route"""
        # Redirect to the workout timer
        return web.HTTPFound('/ui/workout_timer.html')
        
    async def get_workout(self, request):
        """API endpoint to get workout data"""
        # Get workout data from query parameters
        workout_data = request.query.get('workout', '{}')
        
        try:
            # Parse workout data
            workout = json.loads(workout_data)
            return web.json_response(workout)
        except json.JSONDecodeError:
            return web.json_response({'error': 'Invalid workout data'}, status=400)
            
    async def complete_workout(self, request):
        """API endpoint to mark a workout as complete"""
        try:
            data = await request.json()
            # Here you would typically update the user's workout history
            # For now, we'll just return a success response
            return web.json_response({'success': True})
        except json.JSONDecodeError:
            return web.json_response({'error': 'Invalid request data'}, status=400)
            
    async def start(self):
        """Start the server"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()
        print(f"Workout UI server running at http://{self.host}:{self.port}")
        
    async def stop(self):
        """Stop the server"""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
            
    def open_workout_ui(self, workout_data=None):
        """Open the workout UI in a browser"""
        url = f"http://{self.host}:{self.port}/ui/workout_timer.html"
        
        if workout_data:
            # Encode workout data as URL parameter
            encoded_data = quote(json.dumps(workout_data))
            url = f"{url}?workout={encoded_data}"
            
        # Open the URL in a new browser window
        webbrowser.open(url, new=2)
        
        return url
