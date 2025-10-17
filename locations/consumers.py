"""
WebSocket consumers for real-time location tracking
"""
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from authentication.models import DriverProfile
from bookings.models import Ride, RideLocation

logger = logging.getLogger(__name__)
User = get_user_model()


class LocationTrackingConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time location tracking during rides
    """
    
    async def connect(self):
        self.ride_id = self.scope['url_route']['kwargs']['ride_id']
        self.room_group_name = f'ride_tracking_{self.ride_id}'
        self.user = self.scope["user"]
        
        # Verify user authentication and permissions
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Verify ride exists and user has permission
        ride_exists = await self.verify_ride_permission()
        if not ride_exists:
            await self.close()
            return
        
        # Join ride tracking group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        logger.info(f"User {self.user.email} connected to ride tracking {self.ride_id}")
    
    async def disconnect(self, close_code):
        # Leave ride tracking group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        logger.info(f"User {self.user.email} disconnected from ride tracking {self.ride_id}")
    
    async def receive(self, text_data):
        """
        Handle incoming WebSocket messages
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'location_update' and self.user.role == 'driver':
                await self.handle_location_update(data)
            elif message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }))
            
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received from {self.user.email}")
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {str(e)}")
    
    async def handle_location_update(self, data):
        """
        Handle location update from driver
        """
        try:
            location_data = {
                'latitude': data.get('latitude'),
                'longitude': data.get('longitude'),
                'accuracy': data.get('accuracy'),
                'speed': data.get('speed'),
                'heading': data.get('heading')
            }
            
            # Validate required fields
            if not location_data['latitude'] or not location_data['longitude']:
                return
            
            # Save location to database
            await self.save_location_update(location_data)
            
            # Broadcast to all clients in the room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'location_broadcast',
                    'location': location_data,
                    'timestamp': data.get('timestamp')
                }
            )
            
        except Exception as e:
            logger.error(f"Error handling location update: {str(e)}")
    
    async def location_broadcast(self, event):
        """
        Send location update to WebSocket
        """
        await self.send(text_data=json.dumps({
            'type': 'location_update',
            'location': event['location'],
            'timestamp': event['timestamp']
        }))
    
    async def status_update(self, event):
        """
        Send ride status update to WebSocket
        """
        await self.send(text_data=json.dumps({
            'type': 'status_update',
            'status': event['status'],
            'message': event.get('message', ''),
            'timestamp': event['timestamp']
        }))
    
    @database_sync_to_async
    def verify_ride_permission(self):
        """
        Verify user has permission to track this ride
        """
        try:
            ride = Ride.objects.get(pk=self.ride_id)
            
            # Check if user is customer, driver, or admin
            if (self.user == ride.customer or 
                self.user == ride.driver or 
                self.user.role == 'admin'):
                return True
            
            return False
            
        except Ride.DoesNotExist:
            return False
    
    @database_sync_to_async
    def save_location_update(self, location_data):
        """
        Save location update to database
        """
        try:
            ride = Ride.objects.get(pk=self.ride_id)
            
            # Create location record
            RideLocation.objects.create(
                ride=ride,
                **location_data
            )
            
            # Update driver's current location
            if hasattr(self.user, 'driver_profile'):
                driver_profile = self.user.driver_profile
                driver_profile.current_latitude = location_data['latitude']
                driver_profile.current_longitude = location_data['longitude']
                driver_profile.save(update_fields=[
                    'current_latitude', 'current_longitude', 'last_location_update'
                ])
            
        except Ride.DoesNotExist:
            logger.error(f"Ride {self.ride_id} not found for location update")
        except Exception as e:
            logger.error(f"Error saving location update: {str(e)}")


class DriverLocationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for driver location updates when not on ride
    """
    
    async def connect(self):
        self.user = self.scope["user"]
        
        if not self.user.is_authenticated or self.user.role != 'driver':
            await self.close()
            return
        
        self.driver_group_name = f'driver_location_{self.user.id}'
        
        # Join driver location group
        await self.channel_layer.group_add(
            self.driver_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        logger.info(f"Driver {self.user.email} connected for location updates")
    
    async def disconnect(self, close_code):
        # Leave driver location group
        await self.channel_layer.group_discard(
            self.driver_group_name,
            self.channel_name
        )
        
        # Mark driver as offline
        await self.set_driver_offline()
        
        logger.info(f"Driver {self.user.email} disconnected from location updates")
    
    async def receive(self, text_data):
        """
        Handle incoming location updates from driver
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'location_update':
                await self.handle_driver_location_update(data)
            elif message_type == 'status_change':
                await self.handle_status_change(data)
            
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received from driver {self.user.email}")
        except Exception as e:
            logger.error(f"Error handling driver WebSocket message: {str(e)}")
    
    async def handle_driver_location_update(self, data):
        """
        Handle location update from driver
        """
        try:
            location_data = {
                'latitude': data.get('latitude'),
                'longitude': data.get('longitude'),
                'accuracy': data.get('accuracy'),
                'speed': data.get('speed'),
                'heading': data.get('heading')
            }
            
            # Save location and update driver status
            await self.save_driver_location(location_data, data.get('is_online', True))
            
            # Acknowledge receipt
            await self.send(text_data=json.dumps({
                'type': 'location_ack',
                'timestamp': data.get('timestamp')
            }))
            
        except Exception as e:
            logger.error(f"Error handling driver location update: {str(e)}")
    
    async def handle_status_change(self, data):
        """
        Handle driver online/offline status change
        """
        try:
            is_online = data.get('is_online', False)
            await self.update_driver_status(is_online)
            
            await self.send(text_data=json.dumps({
                'type': 'status_ack',
                'is_online': is_online,
                'timestamp': data.get('timestamp')
            }))
            
        except Exception as e:
            logger.error(f"Error handling driver status change: {str(e)}")
    
    @database_sync_to_async
    def save_driver_location(self, location_data, is_online):
        """
        Save driver location to database
        """
        try:
            driver_profile = self.user.driver_profile
            driver_profile.current_latitude = location_data['latitude']
            driver_profile.current_longitude = location_data['longitude']
            driver_profile.is_online = is_online
            driver_profile.save(update_fields=[
                'current_latitude', 'current_longitude', 'is_online', 'last_location_update'
            ])
            
        except Exception as e:
            logger.error(f"Error saving driver location: {str(e)}")
    
    @database_sync_to_async
    def update_driver_status(self, is_online):
        """
        Update driver online status
        """
        try:
            driver_profile = self.user.driver_profile
            driver_profile.is_online = is_online
            driver_profile.save(update_fields=['is_online'])
            
        except Exception as e:
            logger.error(f"Error updating driver status: {str(e)}")
    
    @database_sync_to_async
    def set_driver_offline(self):
        """
        Set driver as offline when disconnecting
        """
        try:
            driver_profile = self.user.driver_profile
            driver_profile.is_online = False
            driver_profile.save(update_fields=['is_online'])
            
        except Exception as e:
            logger.error(f"Error setting driver offline: {str(e)}")