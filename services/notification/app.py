import json
import os
from datetime import datetime, timezone
from uuid import uuid4

from azure.identity import DefaultAzureCredential
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from flask import Flask, jsonify, request

app = Flask(__name__)
SERVICE_NAME = os.getenv("SERVICE_NAME", "notification")
STARTED_AT = datetime.now(timezone.utc)
NOTIFICATIONS = []


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def publish_notification(notification):
    namespace = os.getenv("SERVICE_BUS_NAMESPACE")
    if not namespace:
        return
    with ServiceBusClient(namespace, DefaultAzureCredential()) as service_bus_client:
        sender = service_bus_client.get_queue_sender(os.getenv("SERVICE_BUS_QUEUE", "notifications"))
        with sender:
            sender.send_messages(ServiceBusMessage(json.dumps(notification)))


def emit_notification(payload):
    notification = {
        "id": f"ntf_{uuid4().hex[:10]}",
        "channel": payload.get("channel", "email"),
        "to": payload.get("to", "customer@example.com"),
        "subject": payload.get("subject", "Your order update"),
        "body": payload.get("body", "Thanks for shopping with us."),
        "status": payload.get("status", "sent"),
        "sentAt": now_iso(),
        "metadata": payload.get("metadata", {}),
    }
    NOTIFICATIONS.append(notification)
    publish_notification(notification)
    return notification


@app.get("/healthz")
def healthz():
    return jsonify(service=SERVICE_NAME, status="ok", persistence="service-bus", startedAt=STARTED_AT.isoformat())


@app.get("/")
def index():
    return jsonify(service=SERVICE_NAME, message="notification service ready")


@app.get("/api/templates")
def templates():
    return jsonify(
        service=SERVICE_NAME,
        templates=[
            {"name": "order_confirmation", "channel": "email"},
            {"name": "shipping_update", "channel": "email"},
            {"name": "payment_receipt", "channel": "email"},
            {"name": "cart_reminder", "channel": "sms"},
        ],
    )


@app.post("/api/notifications/send")
def send_notification():
    payload = request.get_json(silent=True) or {}
    notification = emit_notification(payload)
    return jsonify(service=SERVICE_NAME, notification=notification), 201


@app.post("/api/notifications/bulk")
def bulk_send():
    payload = request.get_json(silent=True) or {}
    sent = [emit_notification(item) for item in payload.get("notifications", [])]
    return jsonify(service=SERVICE_NAME, sent=sent, count=len(sent)), 201


@app.get("/api/notifications")
def list_notifications():
    return jsonify(service=SERVICE_NAME, count=len(NOTIFICATIONS), notifications=NOTIFICATIONS)


@app.get("/api/notifications/<notification_id>")
def get_notification(notification_id):
    for notification in NOTIFICATIONS:
        if notification["id"] == notification_id:
            return jsonify(service=SERVICE_NAME, notification=notification)
    return jsonify(error="notification not found", notificationId=notification_id), 404


@app.post("/api/notifications/<notification_id>/resend")
def resend(notification_id):
    for notification in NOTIFICATIONS:
        if notification["id"] == notification_id:
            resent = emit_notification(
                {
                    "channel": notification["channel"],
                    "to": notification["to"],
                    "subject": notification["subject"],
                    "body": notification["body"],
                    "metadata": notification.get("metadata", {}),
                    "status": "resent",
                }
            )
            return jsonify(service=SERVICE_NAME, notification=resent)
    return jsonify(error="notification not found", notificationId=notification_id), 404


@app.get("/api/digest")
def digest():
    channels = {}
    for notification in NOTIFICATIONS:
        channels[notification["channel"]] = channels.get(notification["channel"], 0) + 1
    return jsonify(service=SERVICE_NAME, channels=channels, total=len(NOTIFICATIONS), lastSent=NOTIFICATIONS[-1]["sentAt"] if NOTIFICATIONS else None)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
