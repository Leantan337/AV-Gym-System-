from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import models
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta
from members.models import Member
from plans.models import MembershipPlan, MembershipSubscription
from checkins.models import CheckIn
from invoices.models import Invoice
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import connection
import redis
import os


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_statistics(request):
    # Time ranges
    today = timezone.now().date()
    thirty_days_ago = timezone.now() - timedelta(days=30)

    # Member statistics
    total_members = Member.objects.count()
    active_members = Member.objects.filter(status='active').count()
    new_members_30d = Member.objects.filter(created_at__gte=thirty_days_ago).count()

    # Subscription statistics
    active_subscriptions = MembershipSubscription.objects.filter(
        status='active', end_date__gte=today
    ).count()
    subscription_revenue = (
        MembershipSubscription.objects.filter(status='active', end_date__gte=today).aggregate(
            total=Sum('plan__price')
        )['total']
        or 0
    )

    # Check-in statistics
    todays_checkins = CheckIn.objects.filter(check_in_time__date=today).count()
    checkins_30d = CheckIn.objects.filter(check_in_time__gte=thirty_days_ago).count()

    # Most popular plans
    popular_plans = MembershipPlan.objects.annotate(
        subscriber_count=Count(
            'membershipsubscription',
            filter=models.Q(
                membershipsubscription__status='active', membershipsubscription__end_date__gte=today
            ),
        )
    ).order_by('-subscriber_count')[:5]

    # Financial statistics
    total_revenue = (
        Invoice.objects.filter(status='paid').aggregate(total=Sum('amount'))['total'] or 0
    )
    revenue_30d = (
        Invoice.objects.filter(status='paid', created_at__gte=thirty_days_ago).aggregate(
            total=Sum('amount')
        )['total']
        or 0
    )
    pending_payments = (
        Invoice.objects.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0
    )

    return Response(
        {
            'members': {
                'total': total_members,
                'active': active_members,
                'new_last_30_days': new_members_30d,
            },
            'subscriptions': {
                'active': active_subscriptions,
                'revenue': subscription_revenue,
                'popular_plans': [
                    {'name': plan.name, 'subscribers': plan.subscriber_count}
                    for plan in popular_plans
                ],
            },
            'checkins': {'today': todays_checkins, 'last_30_days': checkins_30d},
            'finance': {
                'total_revenue': total_revenue,
                'revenue_last_30_days': revenue_30d,
                'pending_payments': pending_payments,
            },
        }
    )


def index(request):
    return render(request, 'admin/index.html')


@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """
    Health check endpoint for monitoring
    """
    health_status = {'status': 'healthy', 'timestamp': None, 'services': {}}

    try:
        health_status['timestamp'] = timezone.now().isoformat()

        # Check database connection
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                health_status['services']['database'] = 'healthy'
        except Exception as e:
            health_status['services']['database'] = f'unhealthy: {str(e)}'
            health_status['status'] = 'unhealthy'

        # Check Redis connection
        try:
            redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
            r = redis.from_url(redis_url)
            r.ping()
            health_status['services']['redis'] = 'healthy'
        except Exception as e:
            health_status['services']['redis'] = f'unhealthy: {str(e)}'
            health_status['status'] = 'unhealthy'

        # Check Celery connection
        try:
            from celery import current_app

            current_app.control.inspect().active()
            health_status['services']['celery'] = 'healthy'
        except Exception as e:
            health_status['services']['celery'] = f'unhealthy: {str(e)}'
            # Don't mark overall as unhealthy for Celery issues

        # Check file system
        try:
            media_dir = os.path.join(os.getcwd(), 'media')
            if os.access(media_dir, os.W_OK):
                health_status['services']['filesystem'] = 'healthy'
            else:
                health_status['services']['filesystem'] = 'unhealthy: no write access'
                health_status['status'] = 'unhealthy'
        except Exception as e:
            health_status['services']['filesystem'] = f'unhealthy: {str(e)}'
            health_status['status'] = 'unhealthy'

        # Add application info
        health_status['app_info'] = {
            'name': 'AV Gym Management System',
            'version': '1.0.0',
            'environment': os.environ.get('ENVIRONMENT', 'development'),
        }

        status_code = 200 if health_status['status'] == 'healthy' else 503

    except Exception as e:
        health_status = {
            'status': 'error',
            'error': str(e),
            'timestamp': timezone.now().isoformat() if 'timezone' in locals() else None,
        }
        status_code = 500

    return JsonResponse(health_status, status=status_code)
