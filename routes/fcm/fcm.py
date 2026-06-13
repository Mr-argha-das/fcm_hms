import firebase_admin
from firebase_admin import credentials, messaging
import logging


# 🔥 logger setup
logger = logging.getLogger("fcm")
logger.setLevel(logging.INFO)


# init once
if not firebase_admin._apps:
    cred = credentials.Certificate("utils/healthcare-hms-1fdc42c427ae.json")
    firebase_admin.initialize_app(cred)

def send_bulk_push(tokens, title, body, data=None):
    try:
        if not tokens:
            logger.warning("⚠️ No tokens provided")
            return

        logger.info(f"🚀 Sending push to {len(tokens)} users")

        message = messaging.MulticastMessage(
            tokens=tokens,
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            data=data or {}
        )

        # ✅ correct method for firebase-admin v7+
        response = messaging.send_each_for_multicast(message)

        logger.info(f"✅ Success count: {response.success_count}")
        logger.warning(f"❌ Failure count: {response.failure_count}")

        # per token logs
        for idx, resp in enumerate(response.responses):
            token = tokens[idx]

            if resp.success:
                logger.info(f"✔ Sent → {token}")
            else:
                logger.error(f"❌ Failed → {token} | {resp.exception}")

        return response

    except Exception:
        logger.exception("🔥 FCM bulk push crashed")
        return None