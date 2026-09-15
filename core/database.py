import os

from mongoengine import connect


def init_db():
    connect(
        db="hms_db10",
        # Set MONGO_URI in the environment to override (handy for deploys)
        host=os.getenv(
            "MONGO_URI",
            "mongodb+srv://infozodex_db_user:absolutions@data.yycywiw.mongodb.net"
        )
        # host="mongodb+srv://avbigbuddy:nZ4ATPTwJjzYnm20@cluster0.wplpkxz.mongodb.net/hms_db1"
    )
