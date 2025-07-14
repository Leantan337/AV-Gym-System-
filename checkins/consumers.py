import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import CheckIn
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser

User = get_user_model()


@database_sync_to_async
def get_user_by_id(user_id):
    """Helper function to get user by ID asynchronously."""
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        # Get the token from the query string
        query_string = scope.get('query_string', b'').decode()
        query_params = dict(q.split('=') for q in query_string.split('&') if q)
        token = query_params.get('token', None)

        if token:
            try:
                # Decode the JWT token
                access_token = AccessToken(token)
                user_id = access_token['user_id']
                user = await get_user_by_id(user_id)
                scope['user'] = user
                print(f"WebSocket: User authenticated via URL token: {user.username}")
            except Exception as e:
                print(f"JWT Auth error (URL token): {e}")
                scope['user'] = AnonymousUser()
        else:
            scope['user'] = AnonymousUser()

        return await super().__call__(scope, receive, send)


class CheckInConsumer(AsyncWebsocketConsumer):
    room_group_name = 'checkins'

    async def connect(self):
        print("WebSocket: connect called")
        # Accept the connection first to allow authentication message
        await self.accept()
        print("WebSocket: connection accepted")

    async def disconnect(self, close_code):
        print(f"WebSocket: disconnect called, code={close_code}")
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        print(f"WebSocket: received data: {text_data}")
        print(f"WebSocket: Processing message type: {json.loads(text_data).get('type')}")
        try:
            data = json.loads(text_data)
            event_type = data.get('type')

            # Handle heartbeat before authentication check
            if event_type == 'heartbeat':
                # Respond to heartbeat with a heartbeat_ack
                try:
                    await self.send(
                        json.dumps(
                            {'type': 'heartbeat_ack', 'timestamp': timezone.now().isoformat()}
                        )
                    )
                except Exception as e:
                    print(f"WebSocket: Error sending heartbeat response: {e}")
                    # Connection might be closed, don't try to send more
                    return
                return

            if event_type == 'authenticate':
                # Handle authentication message
                token = data.get('payload', {}).get('token')
                if token:
                    try:
                        access_token = AccessToken(token)
                        user_id = access_token['user_id']
                        user = await get_user_by_id(user_id)
                        if not isinstance(user, AnonymousUser):
                            self.scope['user'] = user
                            print(f"WebSocket: User authenticated via message: {user.username}")
                            # Add to group after successful authentication
                            await self.channel_layer.group_add(
                                self.room_group_name, self.channel_name
                            )
                            try:
                                await self.send(
                                    json.dumps(
                                        {
                                            'type': 'authentication_success',
                                            'message': 'Successfully authenticated',
                                        }
                                    )
                                )
                            except Exception as e:
                                print(f"WebSocket: Error sending auth success: {e}")
                                return

                            # Send initial stats after authentication
                            print("WebSocket: Fetching initial stats...")
                            try:
                                stats = await self.get_check_in_stats()
                                print("WebSocket: Initial stats fetched.")
                                await self.send(
                                    json.dumps({'type': 'initial_stats', 'payload': stats})
                                )
                                print("WebSocket: Initial stats sent.")
                            except Exception as e:
                                print(f"WebSocket: Error fetching or sending initial stats: {e}")
                                # Don't close connection for stats errors, just log them

                            return
                    except Exception as e:
                        print(f"Authentication error (message): {e}")
                        try:
                            await self.send(
                                json.dumps(
                                    {'type': 'authentication_error', 'message': 'Invalid token'}
                                )
                            )
                        except Exception as send_error:
                            print(f"WebSocket: Error sending auth error: {send_error}")
                        await self.close()
                        return
                else:
                    try:
                        await self.send(
                            json.dumps(
                                {'type': 'authentication_error', 'message': 'No token provided'}
                            )
                        )
                    except Exception as send_error:
                        print(f"WebSocket: Error sending auth error: {send_error}")
                    await self.close()
                    return

            # For non-authentication messages, check if user is authenticated
            if isinstance(self.scope["user"], AnonymousUser):
                try:
                    await self.send(
                        json.dumps({'type': 'error', 'message': 'Authentication required'})
                    )
                except Exception as send_error:
                    print(f"WebSocket: Error sending auth required: {send_error}")
                await self.close()
                return

            if event_type == 'check_in':
                await self.handle_check_in(data.get('payload', {}))
            elif event_type == 'check_out':
                await self.handle_check_out(data.get('payload', {}))
        except json.JSONDecodeError:
            print("WebSocket: Invalid JSON received")
            try:
                await self.send(json.dumps({'type': 'error', 'message': 'Invalid JSON format'}))
            except Exception as send_error:
                print(f"WebSocket: Error sending JSON error: {send_error}")

    @database_sync_to_async
    def get_check_in_stats(self):
        from members.models import Member

        currently_in = CheckIn.objects.filter(check_out_time__isnull=True).count()
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_total = CheckIn.objects.filter(check_in_time__gte=today_start).count()
        # Calculate average stay - this is a simplified example
        # A more accurate calculation would involve completed check-ins
        completed_checkins_today = CheckIn.objects.filter(
            check_in_time__gte=today_start, check_out_time__isnull=False
        )
        total_stay_minutes = sum(
            [
                (ci.check_out_time - ci.check_in_time).total_seconds() / 60
                for ci in completed_checkins_today
            ]
        )
        average_stay_minutes = (
            round(total_stay_minutes / completed_checkins_today.count())
            if completed_checkins_today.count() > 0
            else 0
        )

        return {
            'currentlyIn': currently_in,
            'todayTotal': today_total,
            'averageStayMinutes': average_stay_minutes,
        }

    @database_sync_to_async
    def process_check_in(self, member_id, location=None, notes=None):
        from members.models import Member

        try:
            member = Member.objects.get(id=member_id)
            check_in = CheckIn.objects.create(
                member=member, check_in_time=timezone.now(), location=location, notes=notes
            )
            return {
                'success': True,
                'check_in': {
                    'id': str(check_in.id),
                    'member': {
                        'id': str(member.id),
                        'full_name': member.full_name,
                        'membership_type': getattr(member, 'membership_type', ''),
                    },
                    'check_in_time': check_in.check_in_time.isoformat(),
                    'location': location,
                },
            }
        except Member.DoesNotExist:
            return {'success': False, 'error': 'Member not found'}

    async def handle_check_in(self, data):
        # Handle both 'memberId' and 'member_id' for backward compatibility
        member_id = data.get('memberId') or data.get('member_id')

        result = await self.process_check_in(member_id, data.get('location'), data.get('notes'))
        if result['success']:
            try:
                await self.send(
                    text_data=json.dumps(
                        {'type': 'check_in_success', 'payload': result['check_in']}
                    )
                )
            except Exception as e:
                print(f"WebSocket: Error sending check-in success: {e}")
                return

            try:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {'type': 'member_checked_in', 'payload': result['check_in']},
                )
            except Exception as e:
                print(f"WebSocket: Error broadcasting check-in: {e}")
        else:
            try:
                await self.send(
                    text_data=json.dumps(
                        {'type': 'check_in_error', 'payload': {'error': result['error']}}
                    )
                )
            except Exception as e:
                print(f"WebSocket: Error sending check-in error: {e}")

    async def handle_check_out(self, data):
        result = await self.process_check_out(data.get('checkInId'), data.get('notes'))
        if result['success']:
            try:
                await self.send(
                    text_data=json.dumps(
                        {'type': 'check_out_success', 'payload': result['check_out']}
                    )
                )
            except Exception as e:
                print(f"WebSocket: Error sending check-out success: {e}")
                return

            try:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {'type': 'member_checked_out', 'payload': result['check_out']},
                )
            except Exception as e:
                print(f"WebSocket: Error broadcasting check-out: {e}")
        else:
            try:
                await self.send(
                    text_data=json.dumps(
                        {'type': 'check_out_error', 'payload': {'error': result['error']}}
                    )
                )
            except Exception as e:
                print(f"WebSocket: Error sending check-out error: {e}")

    @database_sync_to_async
    def process_check_out(self, check_in_id, notes=None):
        try:
            check_in = CheckIn.objects.get(id=check_in_id, check_out_time__isnull=True)
            check_in.check_out_time = timezone.now()
            if notes:
                check_in.notes = notes
            check_in.save()
            return {
                'success': True,
                'check_out': {
                    'id': str(check_in.id),
                    'member': {
                        'id': str(check_in.member.id),
                        'full_name': check_in.member.full_name,
                        'membership_type': getattr(check_in.member, 'membership_type', ''),
                    },
                    'check_in_time': check_in.check_in_time.isoformat(),
                    'check_out_time': check_in.check_out_time.isoformat(),
                    'location': check_in.location,
                },
            }
        except CheckIn.DoesNotExist:
            return {'success': False, 'error': 'Check-in not found or already checked out'}

    async def member_checked_in(self, event):
        try:
            await self.send(
                text_data=json.dumps({'type': 'member_checked_in', 'payload': event['payload']})
            )
        except Exception as e:
            print(f"WebSocket: Error sending member_checked_in broadcast: {e}")

    async def member_checked_out(self, event):
        try:
            await self.send(
                text_data=json.dumps({'type': 'member_checked_out', 'payload': event['payload']})
            )
        except Exception as e:
            print(f"WebSocket: Error sending member_checked_out broadcast: {e}")
