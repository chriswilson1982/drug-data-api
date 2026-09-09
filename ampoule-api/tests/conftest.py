import os

# main.py refuses to import without MONGODB_URI set, and building the
# (lazy, connect=False) MongoClient doesn't require a reachable server,
# so a placeholder URI is enough for tests that stub out the collections.
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
