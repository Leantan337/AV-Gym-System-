from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Sum
from members.models import Member
from plans.models import MembershipSubscription
from invoices.models import Invoice
from checkins.models import CheckIn


@api_view(['GET'])
# Temporarily disabled for testing
# @permission_classes([IsAdminUser])
def admin_dashboard_stats(request):
    today = timezone.now().date()

    # Member statistics
    total_members = Member.objects.count()
    active_members = Member.objects.filter(status='active').count()
    new_members = Member.objects.filter(created_at__date=today).count()

    # Subscription statistics
    active_subscriptions = MembershipSubscription.objects.filter(
        status='active', end_date__gte=today
    ).count()
    expiring_soon = MembershipSubscription.objects.filter(
        status='active', end_date__range=[today, today + timezone.timedelta(days=7)]
    ).count()

    # Financial statistics
    today_revenue = (
        Invoice.objects.filter(created_at__date=today, status='paid').aggregate(total=Sum('total'))[
            'total'
        ]
        or 0
    )
    pending_payments = (
        Invoice.objects.filter(status='pending').aggregate(total=Sum('total'))['total'] or 0
    )

    # Check-in statistics
    today_checkins = CheckIn.objects.filter(check_in_time__date=today).count()
    current_in_gym = CheckIn.objects.filter(
        check_in_time__date=today, check_out_time__isnull=True
    ).count()

    return Response(
        {
            'members': {
                'total': total_members,
                'active': active_members,
                'new_today': new_members,
            },
            'subscriptions': {
                'active': active_subscriptions,
                'expiring_soon': expiring_soon,
            },
            'finance': {
                'today_revenue': float(today_revenue),
                'pending_payments': float(pending_payments),
            },
            'checkins': {
                'today': today_checkins,
                'current': current_in_gym,
            },
        }
    )


@api_view(['POST'])
@permission_classes([IsAdminUser])
def bulk_member_action(request):
    action = request.data.get('action')
    member_ids = request.data.get('member_ids', [])

    if not member_ids:
        return Response({'error': 'No members selected'}, status=400)

    if action == 'activate':
        Member.objects.filter(id__in=member_ids).update(status='active')
    elif action == 'deactivate':
        Member.objects.filter(id__in=member_ids).update(status='inactive')
    else:
        return Response({'error': 'Invalid action'}, status=400)

    return Response({'status': 'success'})


@api_view(['POST'])
@permission_classes([IsAdminUser])
def bulk_invoice_action(request):
    action = request.data.get('action')
    invoice_ids = request.data.get('invoice_ids', [])

    if not invoice_ids:
        return Response({'error': 'No invoices selected'}, status=400)

    if action == 'mark_paid':
        Invoice.objects.filter(id__in=invoice_ids).update(status='paid')
    elif action == 'mark_pending':
        Invoice.objects.filter(id__in=invoice_ids).update(status='pending')
    else:
        return Response({'error': 'Invalid action'}, status=400)

    return Response({'status': 'success'})


@api_view(['GET'])
@permission_classes([IsAdminUser])
def member_stats(request):
    member_id = request.query_params.get('member_id')
    if not member_id:
        return Response({'error': 'Member ID is required'}, status=400)

    try:
        member = Member.objects.get(id=member_id)
    except Member.DoesNotExist:
        return Response({'error': 'Member not found'}, status=404)

    # Get member's active subscription
    active_subscription = MembershipSubscription.objects.filter(
        member=member, status='active', end_date__gte=timezone.now().date()
    ).first()

    # Get recent check-ins
    recent_checkins = CheckIn.objects.filter(member=member).order_by('-check_in_time')[:5]

    # Get payment history
    payment_history = Invoice.objects.filter(member=member).order_by('-created_at')[:5]

    return Response(
        {
            'member': {
                'id': str(member.id),
                'name': member.full_name,
                'status': member.status,
            },
            'subscription': {
                'plan': active_subscription.plan.name if active_subscription else None,
                'end_date': active_subscription.end_date if active_subscription else None,
            },
            'recent_checkins': [
                {
                    'check_in_time': checkin.check_in_time,
                    'check_out_time': checkin.check_out_time,
                }
                for checkin in recent_checkins
            ],
            'payment_history': [
                {
                    'amount': float(invoice.amount),
                    'status': invoice.status,
                    'due_date': invoice.due_date,
                }
                for invoice in payment_history
            ],
        }
    )
