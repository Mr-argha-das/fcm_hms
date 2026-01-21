from mongoengine import connect

def init_db():
    connect(
        db="hms_db",
        host="mongodb+srv://infozodex_db_user:absolutions@data.yycywiw.mongodb.net/hms_db"
        # host="mongodb+srv://avbigbuddy:nZ4ATPTwJjzYnm20@cluster0.wplpkxz.mongodb.net/hms_db"
    )
