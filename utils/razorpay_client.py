import razorpay
import os

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_live_SXwi1jtJbTmZIR")
RAZORPAY_KEY_SECRET = os.getenv(
    "RAZORPAY_KEY_SECRET", "boD5dyBKgjKHpHIXbb7EP7Q2"
)

client = razorpay.Client(
    auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
)
