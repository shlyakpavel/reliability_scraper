from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    Integer,
    String,
    Float,
    ForeignKey
)
meta = MetaData()

link = Table(
    'link', meta, 
    Column('id', Integer, primary_key=True),
    Column('link', String),
    Column(
        'device_id',
        Integer,
        ForeignKey('device.id')
    )
)
device = Table(
    'device', meta,
    Column('id', Integer, primary_key=True),
    Column('query', String),
    Column('mttr', Float),
    Column('mtbf', Float),
    Column('failure_rate', Float),
    Column('failure_rate_in_storage_mode', Float),
    Column('storage_time', Float),
    Column('minimal_resource', Float),
    Column('gamma_percentage_resource', Float),
    Column('average_resource', Float),
    Column('average_lifetime', Float),
    Column('recovery_intensity', Float),
    Column('system_reliability', Float)
)

if __name__ == '__main__':
    engine = create_engine(
        'postgresql://postgres:docker@postgres:5432',
        echo = True
    )
    meta.create_all(engine)