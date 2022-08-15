# BusSchedule


## install apt packages

```
sudo apt-get install python-is-python3 python3-pip postgresql -y
```

## install pip packages

```
pip install asyncio psycopg2-binary flask flask-restful flasgger peewee marshmallow 
```

## populate postgres db

```
sudo -u postgres psql < create_db.sql
```
