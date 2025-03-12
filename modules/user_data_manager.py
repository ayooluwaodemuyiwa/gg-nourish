import json
import os
from datetime import datetime, timedelta

class UserDataManager:
    def __init__(self, data_file_path):
        """Initialize the user data manager with the path to the data file"""
        self.data_file_path = data_file_path
        self.user_data = self._load_user_data()
        
    def _load_user_data(self):
        """Load user data from the data file"""
        if os.path.exists(self.data_file_path):
            try:
                with open(self.data_file_path, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"Error loading user data from {self.data_file_path}. Creating new data file.")
                return {}
        else:
            return {}
            
    def save_user_data(self, user_id=None, user_data=None):
        """Save user data to the data file
        
        If user_id and user_data are provided, update that specific user's data
        Otherwise, save all user data
        """
        if user_id and user_data:
            self.user_data[user_id] = user_data
            
        with open(self.data_file_path, 'w') as f:
            json.dump(self.user_data, f, indent=2)
            
    def get_user_data(self, user_id):
        """Get data for a specific user, creating a new entry if it doesn't exist"""
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                "chat_history": [],
                "health_goal": {},
                "gaming_sessions": [],
                "created_at": datetime.now().isoformat()
            }
            self.save_user_data()
        elif "chat_history" not in self.user_data[user_id]:
            # Ensure chat_history exists for existing users
            self.user_data[user_id]["chat_history"] = []
            
        return self.user_data[user_id]
        
    def update_chat_history(self, user_id, role, content):
        """Update the chat history for a user"""
        user_data = self.get_user_data(user_id)
        
        # Add the message to the chat history
        user_data["chat_history"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # Limit chat history to last 50 messages
        if len(user_data["chat_history"]) > 50:
            user_data["chat_history"] = user_data["chat_history"][-50:]
            
        self.save_user_data()
        
    def get_chat_history(self, user_id, limit=10):
        """Get the chat history for a user"""
        user_data = self.get_user_data(user_id)
        chat_history = user_data.get("chat_history", [])
        
        # Return the last 'limit' messages
        return chat_history[-limit:] if chat_history else []
        
    async def track_gaming_session(self, user_id, start=True, channel_id=None):
        """Track the start or end of a gaming session"""
        user_data = self.get_user_data(user_id)
        gaming_sessions = user_data.get("gaming_sessions", [])
        
        if start:
            # Start a new gaming session
            gaming_sessions.append({
                "start_time": datetime.now().isoformat(),
                "end_time": None,
                "channel_id": channel_id,
                "last_activity_reminder": None
            })
        else:
            # End the most recent gaming session if it's still active
            if gaming_sessions and gaming_sessions[-1].get("end_time") is None:
                gaming_sessions[-1]["end_time"] = datetime.now().isoformat()
                
        user_data["gaming_sessions"] = gaming_sessions
        self.save_user_data()
        
    def get_active_gaming_session(self, user_id):
        """Get the active gaming session for a user, if any"""
        user_data = self.get_user_data(user_id)
        gaming_sessions = user_data.get("gaming_sessions", [])
        
        # Check if there's an active gaming session
        if gaming_sessions and gaming_sessions[-1].get("end_time") is None:
            return gaming_sessions[-1]
            
        return None
        
    def should_send_activity_reminder(self, user_id, threshold_seconds=60):
        """Check if an activity reminder should be sent based on the active gaming session"""
        active_session = self.get_active_gaming_session(user_id)
        
        if not active_session:
            return False
            
        # Get the last activity reminder time
        last_reminder = active_session.get("last_activity_reminder")
        
        # If there's no last reminder, check against the start time
        if not last_reminder:
            start_time = datetime.fromisoformat(active_session["start_time"])
            time_elapsed = (datetime.now() - start_time).total_seconds()
            return time_elapsed >= threshold_seconds
            
        # Otherwise, check against the last reminder time
        last_reminder_time = datetime.fromisoformat(last_reminder)
        time_elapsed = (datetime.now() - last_reminder_time).total_seconds()
        return time_elapsed >= threshold_seconds
        
    def update_activity_reminder(self, user_id):
        """Update the last activity reminder time for the active gaming session"""
        active_session = self.get_active_gaming_session(user_id)
        
        if active_session:
            active_session["last_activity_reminder"] = datetime.now().isoformat()
            self.save_user_data()
            
    def get_channel_for_active_session(self, user_id):
        """Get the channel ID for the active gaming session"""
        active_session = self.get_active_gaming_session(user_id)
        
        if active_session:
            return active_session.get("channel_id")
            
        return None
        
    def get_all_user_data(self):
        """Get all user data"""
        return self.user_data
        
    def get_last_activity_time(self, user_id):
        """Get the last activity time for a user"""
        user_data = self.get_user_data(user_id)
        
        if 'activity_data' not in user_data:
            return None
            
        last_activity = user_data['activity_data'].get('last_activity')
        
        if not last_activity:
            return None
            
        return datetime.fromisoformat(last_activity)
        
    def update_user_activity(self, user_id):
        """Update the user's activity timestamp"""
        user_data = self.get_user_data(user_id)
        
        if 'activity_data' not in user_data:
            user_data['activity_data'] = {}
            
        # Update last activity time
        user_data['activity_data']['last_activity'] = datetime.now().isoformat()
        
        # Update daily activity tracking
        today = datetime.now().strftime('%Y-%m-%d')
        
        if 'daily_activity' not in user_data['activity_data']:
            user_data['activity_data']['daily_activity'] = {}
            
        if today not in user_data['activity_data']['daily_activity']:
            user_data['activity_data']['daily_activity'][today] = 0
            
        # Increment activity time (in minutes)
        user_data['activity_data']['daily_activity'][today] += 1
        
        self.save_user_data()
