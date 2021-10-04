import time

import pymongo

from data import read_source

# Assume docker container started with:
# docker run -d -p 27017:27017 --name finance-bot-mongo -v finance-bot-volume:/data/db mongo


class MongoConnector:
    
    def __init__(self, host="localhost", port=27017):
        # Get client
        self.client = pymongo.MongoClient(host=host, port=port)
    
        # Get main db, collection
        self.db = self.client["finance-bot-db"]
        self.source_col = self.db["finance-bot-source"]
        
        # Get backup db
        self.backup_db = self.client["finance-bot-db-backup"]

    # insert rows of df as documents to source collection
    def insert_df(self, df):
        df_dicts = (s.to_dict() for (i, s) in df.iterrows())
        self.source_col.insert_many(df_dicts)

    # return iterator of rows of source collection
    def load_source(self, filter_document={}):
        return self.source_col.find(filter_document)

    # create backup dbs based on time and event
    def backup_source(self, source, event="manual"):
        t = time.time_ns()
        backup_col = self.backup_db[f"finance-bot-source-{t}-{event}"]
        backup_col.insert_many(self.load_source())
