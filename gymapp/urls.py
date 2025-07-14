"""
URL configuration for gymapp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static, serve
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from plans.views import MembershipPlanViewSet, MembershipSubscriptionViewSet
from checkins.views import CheckInViewSet
from invoices.views import InvoiceViewSet
from reports.views import ReportViewSet
from .views import dashboard_statistics, health_check
from .api import admin_dashboard_stats, bulk_member_action, bulk_invoice_action, member_stats
from .admin import gym_admin
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication


# User profile view for /auth/me/ endpoint
class UserProfileView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response(
            {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': getattr(user, 'role', 'STAFF'),
                'is_active': user.is_active,
                'date_joined': user.date_joined,
            }
        )


# Import members URLs
from members import urls as members_urls

router = DefaultRouter()
router.register(r'plans', MembershipPlanViewSet)
router.register(r'subscriptions', MembershipSubscriptionViewSet)
router.register(r'checkins', CheckInViewSet)
router.register(r'invoices', InvoiceViewSet)
router.register(r'reports', ReportViewSet)

urlpatterns = [
    # Django Admin
    path('admin/', gym_admin.urls),
    # API Endpoints
    path('api/', include(router.urls)),
    path('api/members/', include(members_urls)),
    # JWT Authentication
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/auth/me/', UserProfileView.as_view(), name='user-profile'),
    # Django REST Framework auth (for browsable API)
    path('api-auth/', include('rest_framework.urls')),
    # Application endpoints
    path('api/dashboard/', dashboard_statistics, name='dashboard-stats'),
    # Admin API endpoints
    path('api/admin/stats/', admin_dashboard_stats, name='admin-dashboard-stats'),
    path('api/admin/bulk-member-action/', bulk_member_action, name='bulk-member-action'),
    path('api/admin/bulk-invoice-action/', bulk_invoice_action, name='bulk-invoice-action'),
    path('api/member-stats/', member_stats, name='member-stats'),
    # Notifications API
    path('api/notifications/', include('notifications.urls')),
    # Reports API
    path(
        'api/reports/generate/', ReportViewSet.as_view({'post': 'generate'}), name='report-generate'
    ),
    path(
        'api/reports/<int:pk>/download/',
        ReportViewSet.as_view({'get': 'download'}),
        name='report-download',
    ),
    # Health Check
    path('health/', health_check, name='health_check'),
]
# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += [
        path('media/<path:path>', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
