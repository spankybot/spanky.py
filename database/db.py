from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.schema import MetaData
from sqlalchemy.pool import StaticPool

import database

class db_data():
    def __init__(self, db_path):
        self.db_engine = create_engine(db_path, connect_args={'check_same_thread':False}, poolclass=StaticPool)
        self.db_factory = sessionmaker(bind=self.db_engine)
        self.db_session = scoped_session(self.db_factory)
        self.db_metadata = MetaData()
        self.db_base = declarative_base(metadata=self.db_metadata, bind=self.db_engine)

        # Set the global objects so that they're used by the plugins
        database.metadata = self.db_metadata
        database.base = self.db_base