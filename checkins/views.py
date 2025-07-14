from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from authentication.permissions import IsStaffOrAdmin, IsTrainerOrHigher, IsOwnerOrStaff
from authentication.decorators import role_required
from django.utils import timezone
from django.db.models import Avg
from .models import CheckIn
from .serializers import CheckInSerializer
from rest_framework.views import APIView
from datetime import timedelta
from django.core.paginator import Paginator


class CheckInViewSet(viewsets.ModelViewSet):
    permission_classes = [IsTrainerOrHigher]  # Base permission

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsStaffOrAdmin]  # Only staff and admin can modify
        elif self.action in ['list', 'retrieve']:
            self.permission_classes = [IsTrainerOrHigher]  # Trainers can view
        elif self.action == 'my_checkins':
            self.permission_classes = [IsOwnerOrStaff]  # Members can view their own
        return super().get_permissions()

    def list(self, request, *args, **kwargs):
        # Members can only see their own check-ins
        if request.user.is_member_role():
            queryset = self.get_queryset().filter(member__user=request.user)
        else:
            queryset = self.get_queryset()

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Members can only retrieve their own check-ins
        if request.user.is_member_role() and instance.member.user != request.user:
            return Response(
                {"detail": "You do not have permission to view this check-in."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_checkins(self, request):
        """Endpoint for members to get their own check-ins"""
        checkins = self.get_queryset().filter(member__user=request.user)
        serializer = self.get_serializer(checkins, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    @role_required(['staff', 'admin'])
    def checkout(self, request, pk=None):
        """Check-out endpoint - only staff and admin can perform checkouts"""
        checkin = self.get_object()
        if checkin.check_out_time:
            return Response(
                {"detail": "Member is already checked out."}, status=status.HTTP_400_BAD_REQUEST
            )

        checkin.check_out_time = timezone.now()
        checkin.save()
        serializer = self.get_serializer(checkin)
        return Response(serializer.data)

    queryset = CheckIn.objects.all()
    serializer_class = CheckInSerializer
    permission_classes = []  # Temporarily disabled for testing

    def get_queryset(self):
        queryset = CheckIn.objects.all()
        member_id = self.request.query_params.get('member', None)
        date = self.request.query_params.get('date', None)

        if member_id:
            queryset = queryset.filter(member_id=member_id)
        if date:
            queryset = queryset.filter(check_in_time__date=date)

        return queryset

    @action(detail=True, methods=['post'])
    def checkout(self, request, pk=None):
        check_in = self.get_object()
        if check_in.check_out_time:
            return Response({'error': 'Already checked out'}, status=status.HTTP_400_BAD_REQUEST)

        check_in.check_out_time = timezone.now()
        check_in.save()
        serializer = self.get_serializer(check_in)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get paginated check-in history with filters"""
        # Get query parameters
        status = request.query_params.get('status', 'all')
        date_range = request.query_params.get('dateRange', 'all')
        page = int(request.query_params.get('page', 0))
        per_page = int(request.query_params.get('perPage', 10))

        # Build queryset
        queryset = CheckIn.objects.select_related('member').order_by('-check_in_time')

        # Filter by status
        if status == 'checked_in':
            queryset = queryset.filter(check_out_time__isnull=True)
        elif status == 'checked_out':
            queryset = queryset.filter(check_out_time__isnull=False)

        # Filter by date range
        if date_range == 'today':
            today = timezone.now().date()
            queryset = queryset.filter(check_in_time__date=today)
        elif date_range == 'week':
            week_ago = timezone.now() - timedelta(days=7)
            queryset = queryset.filter(check_in_time__gte=week_ago)
        elif date_range == 'month':
            month_ago = timezone.now() - timedelta(days=30)
            queryset = queryset.filter(check_in_time__gte=month_ago)

        # Paginate
        paginator = Paginator(queryset, per_page)
        page_obj = paginator.get_page(page + 1)  # Django pagination is 1-based

        serializer = CheckInSerializer(page_obj.object_list, many=True)

        return Response(
            {
                'results': serializer.data,
                'total': paginator.count,
                'page': page,
                'per_page': per_page,
                'total_pages': paginator.num_pages,
            }
        )

    @action(detail=False, methods=['get'])
    def stats(self, request):
        today = timezone.now().date()
        currently_in = CheckIn.objects.filter(check_out_time__isnull=True).count()
        today_total = CheckIn.objects.filter(check_in_time__date=today).count()

        # Calculate average stay duration for checked-out visits
        checked_out = CheckIn.objects.filter(check_out_time__isnull=False).exclude(
            check_in_time__date=today
        )
        avg_stay = 0
        if checked_out.exists():
            avg_stay = checked_out.annotate(
                duration=timezone.ExpressionWrapper(
                    timezone.F('check_out_time') - timezone.F('check_in_time'),
                    output_field=timezone.DurationField(),
                )
            ).aggregate(avg=Avg('duration'))['avg']
            avg_stay = int(avg_stay.total_seconds() / 60) if avg_stay else 0

        return Response(
            {'currentlyIn': currently_in, 'todayTotal': today_total, 'averageStayMinutes': avg_stay}
        )


class RecentCheckInsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        recent_checkins = (
            CheckIn.objects.filter(check_in_time__gte=timezone.now() - timedelta(hours=24))
            .select_related('member')
            .order_by('-check_in_time')[:20]
        )
        serializer = CheckInSerializer(recent_checkins, many=True)
        return Response(serializer.data)
