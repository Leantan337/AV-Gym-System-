# Generated by Django 5.0.1 on 2025-06-02 00:28

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("members", "0001_initial"),
        ("plans", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="NotificationTemplate",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "name",
                    models.CharField(max_length=100, verbose_name="Template Name"),
                ),
                (
                    "notification_type",
                    models.CharField(
                        choices=[
                            ("MEMBERSHIP_EXPIRY", "Membership Expiry"),
                            ("PAYMENT_DUE", "Payment Due"),
                            ("GENERAL", "General Notification"),
                        ],
                        default="GENERAL",
                        max_length=50,
                        verbose_name="Notification Type",
                    ),
                ),
                (
                    "subject",
                    models.CharField(max_length=200, verbose_name="Email Subject"),
                ),
                ("body_text", models.TextField(verbose_name="Email Body (Text)")),
                (
                    "body_html",
                    models.TextField(blank=True, verbose_name="Email Body (HTML)"),
                ),
                ("is_active", models.BooleanField(default=True, verbose_name="Active")),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Updated At"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="NotificationLog",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "notification_type",
                    models.CharField(
                        choices=[
                            ("MEMBERSHIP_EXPIRY", "Membership Expiry"),
                            ("PAYMENT_DUE", "Payment Due"),
                            ("GENERAL", "General Notification"),
                        ],
                        max_length=50,
                        verbose_name="Notification Type",
                    ),
                ),
                (
                    "subject",
                    models.CharField(max_length=200, verbose_name="Email Subject"),
                ),
                ("message", models.TextField(verbose_name="Message Sent")),
                (
                    "is_email_sent",
                    models.BooleanField(default=False, verbose_name="Email Sent"),
                ),
                (
                    "sent_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Sent At"),
                ),
                (
                    "member",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="notification_logs",
                        to="members.member",
                        verbose_name="Member",
                    ),
                ),
                (
                    "subscription",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="notification_logs",
                        to="plans.membershipsubscription",
                        verbose_name="Related Subscription",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="NotificationSetting",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "notification_type",
                    models.CharField(
                        choices=[
                            ("MEMBERSHIP_EXPIRY", "Membership Expiry"),
                            ("PAYMENT_DUE", "Payment Due"),
                            ("GENERAL", "General Notification"),
                        ],
                        max_length=50,
                        unique=True,
                        verbose_name="Notification Type",
                    ),
                ),
                (
                    "is_email_enabled",
                    models.BooleanField(default=True, verbose_name="Send Email"),
                ),
                (
                    "is_dashboard_enabled",
                    models.BooleanField(default=True, verbose_name="Show on Dashboard"),
                ),
                (
                    "days_before_expiry",
                    models.JSONField(
                        default=list,
                        help_text="List of days before expiry to send notifications (e.g. [30, 15, 7, 3, 1])",
                        verbose_name="Days Before Expiry",
                    ),
                ),
                (
                    "template",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="settings",
                        to="notifications.notificationtemplate",
                        verbose_name="Default Template",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ExpiryNotificationQueue",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "days_before_expiry",
                    models.IntegerField(verbose_name="Days Before Expiry"),
                ),
                ("scheduled_date", models.DateField(verbose_name="Scheduled Date")),
                (
                    "is_processed",
                    models.BooleanField(default=False, verbose_name="Processed"),
                ),
                (
                    "processed_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="Processed At"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "subscription",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="expiry_notifications",
                        to="plans.membershipsubscription",
                        verbose_name="Subscription",
                    ),
                ),
            ],
            options={
                "ordering": ["scheduled_date", "days_before_expiry"],
                "unique_together": {("subscription", "days_before_expiry")},
            },
        ),
    ]
