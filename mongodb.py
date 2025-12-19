import pymongo

# Try the shorter +srv string instead
CONNECTION_STRING = "mongodb+srv://kazirafi98_db_user:hfqTB5GzCb0LECG8@cluster0.psonwzp.mongodb.net/?retryWrites=true&w=majority"

try:
    # Adding a timeout so you don't wait 30 seconds for a fail
    client = pymongo.MongoClient(CONNECTION_STRING, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print("✅ Success! Connection established.")
except Exception as e:
    print(f"❌ Still failing. Error: {e}")


    def check_user_limit(session_id):
        # Find the user's current count
        user_record = logs.find_one({"session_id": session_id})

        if not user_record:
            # First time user: Create record
            logs.insert_one({
                "session_id": session_id,
                "count": 1,
                "last_query": datetime.now()
            })
            return True

        if user_record["count"] >= 3:
            print(f"🚫 User {session_id} has reached the limit. Please Log In.")
            return False

        # Increment the count
        logs.update_one({"session_id": session_id}, {"$inc": {"count": 1}})
        return True


    # Test the logic
    user = "guest_user_99"
    for i in range(4):
        if check_user_limit(user):
            print(f"Query {i + 1} allowed.")
        else:
            break

except Exception as e:
    print(f"❌ Connection failed: {e}")