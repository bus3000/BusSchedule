from ast import And
import datetime as dt
import asyncio as aio
from distutils.log import error
import json
import psycopg2
from functools import wraps

from flask import Flask, request, g, jsonify
from flask_restful import Api, Resource, abort, reqparse
from flasgger import Swagger, swag_from
#from flask_restplus import Namespace, Resource, fields, Api
import peewee as pw
from marshmallow import (
    Schema,
    fields,
    validate,
    pre_load,
    post_dump,
    post_load,
    ValidationError,
)



# namespace = Namespace('bus_schedule', 'bus schedule endpoints')

# bus_schedule_model = namespace.model('bus_schedule', {
#     'message': fields.String(
#         readonly=True,
#         description='Bus Schedule API'
#     )
# })


app = Flask(__name__)

api = Api(app)
app.config['SWAGGER'] = {
    'title': 'Bus Schedule API',
    'uiversion': 2
}
swag = Swagger(app)

db = pw.PostgresqlDatabase('BUS_SCHED', host='localhost', port=5432, user='postgres', password='temp123!')


###### MODELS #####
class BaseModel(pw.Model):
    """Base model class. All descendants share the same database."""

    class Meta:
        database = db


class Driver(BaseModel):
    #id = pw.IntegerField()
    first_name = pw.CharField()
    last_name = pw.CharField()
    ssn = pw.IntegerField()
    email = pw.CharField()

    class Meta: 
        table_name = "driver"

class Bus(BaseModel):
    capacity = pw.IntegerField()
    model = pw.IntegerField()
    make = pw.IntegerField()

    class Meta: 
        table_name = "bus"

class Schedule(BaseModel):
    id = pw.IntegerField()
    driver_id = pw.IntegerField()
    bus_id = pw.IntegerField()
    start_datetime = pw.BigIntegerField()
    end_datetime = pw.BigIntegerField()

    class Meta: 
        table_name = "schedule"


class User(BaseModel):
    id = pw.IntegerField()
    email = pw.CharField(max_length=80, unique=True)
    password = pw.CharField()
    joined_on = pw.BigIntegerField()
    admin = pw.BooleanField()

    class Meta:
        table_name = "bus_user"


def create_tables():
    db.connect()
    Driver.bind(db)
    Bus.bind(db)
    Schedule.bind(db)


##### SCHEMAS #####
class DriverSchema(Schema):
    id = fields.Int(dump_only=True)
    first_name = fields.Str(validate=validate.Length(min=0, max=64, error="First Name must be 0-64 chars long"))
    last_name = fields.Str(validate=validate.Length(min=0, max=64, error="Last Name must be 0-64 chars long"))
    ssn = fields.Int()
    email = fields.Str(validate=validate.Length(min=0, max=64, error="Email must be 0-64 chars long"))

    @post_dump(pass_many=True)
    def wrap(self, data, many, **kwargs):
        key = "drivers" if many else "driver"
        return {key: data}

    @post_load
    def make_object(self, data, **kwargs):
        if not data:
            return None
        return Driver(
            first_name=data["first_name"],
            last_name=data["last_name"],
            ssn=data["ssn"],
            email=data["email"]
        )

class BusSchema(Schema):
    id = fields.Int(dump_only=True)
    model = fields.Str(validate=validate.Length(min=0, max=64, error="Model must be 0-64 chars long"))
    make = fields.Str(validate=validate.Length(min=0, max=64, error="Make must be 0-64 chars long"))
    capacity = fields.Int()
    

    @post_dump(pass_many=True)
    def wrap(self, data, many, **kwargs):
        key = "buses" if many else "bus"
        return {key: data}

    @post_load
    def make_object(self, data, **kwargs):
        if not data:
            return None
        return Bus(
            #bus_id=data["bus_id"],
            model=data["model"],
            make=data["make"],
            capacity=data["capacity"]
        )

class ScheduleSchema(Schema):
    id = fields.Int(dump_only=True)
    bus_id = fields.Int()
    driver_id = fields.Int()
    start_datetime = fields.Int()
    end_datetime = fields.Int()
    

    @post_dump(pass_many=True)
    def wrap(self, data, many, **kwargs):
        key = "schedules" if many else "schedule"
        return {key: data}

    @post_load
    def make_object(self, data, **kwargs):
        if not data:
            return None
        return Schedule(
            # sched_id = data["sched_id"],
            bus_id=data["bus_id"],
            driver_id=data["driver_id"],
            start_datetime=data["start_datetime"],
            end_datetime=data["end_datetime"]
        )



class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    email = fields.Str(
        required=True, validate=validate.Email(error="Not a valid email address")
    )
    password = fields.Str(
        required=True, validate=[validate.Length(min=6, max=36)], load_only=True
    )
    joined_on = fields.DateTime(dump_only=True)
    admin = fields.Boolean()

    # Clean up data
    @pre_load
    def process_input(self, data, **kwargs):
        data["email"] = data["email"].lower().strip()
        return data

    # We add a post_dump hook to add an envelope to responses
    @post_dump(pass_many=True)
    def wrap(self, data, many, **kwargs):
        key = "users" if many else "user"
        return {key: data}




user_schema = UserSchema()
driver_schema = DriverSchema()
driver_schemas = DriverSchema(many=True)
bus_schema = BusSchema()
bus_schemas = BusSchema(many=True)
schedule_schema = ScheduleSchema()
schedule_schemas = ScheduleSchema(many=True)

###### HELPERS ######


def check_auth(email, password):
    """Check if a username/password combination is valid."""
    try:
        user = User.get(User.email == email)
    except User.DoesNotExist:
        return False
    return password == user.password

def check_admin_auth(email, password):
    """Check if a username/password combination is valid AND is admin."""
    try:
        user = User.get(User.email == email)
    except User.DoesNotExist:
        return False
    return password == user.password and user.admin


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            resp = jsonify({"message": "Please authenticate."})
            resp.status_code = 401
            resp.headers["WWW-Authenticate"] = 'Basic realm="Example"'
            return resp
        kwargs["user"] = User.get(User.email == auth.username)
        return f(*args, **kwargs)

    return decorated

def requires_admin_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_admin_auth(auth.username, auth.password):
            resp = jsonify({"message": "Please authenticate as admin."})
            resp.status_code = 401
            resp.headers["WWW-Authenticate"] = 'Basic realm="Example"'
            return resp
        kwargs["user"] = User.get(User.email == auth.username)
        return f(*args, **kwargs)

    return decorated


# Ensure a separate connection for each thread
@app.before_request
def before_request():
    g.db = db
    g.db.connect()


@app.after_request
def after_request(response):
    g.db.close()
    return response


#### API #####

class Drivers(Resource):
    @app.route("/drivers/", methods=["GET"])
    def get_drivers():
        """
        GET Drivers
        ---
        tags:
          - restful
        responses:
          200:
            description: Driver data
            schema:
              id: Driver_GET
              properties:
                id:
                    type: integer
                    default: 1
                first_name:
                  type: string
                  default: John
                last_name:
                  type: string
                  default: Doe
                sin:
                  type: integer
                  default: 123456789
                email:
                  type: string
                  default: jd@busbus.ca
        """
        drivers = Driver.select()
        return driver_schemas.dump(list(drivers))

    @app.route("/drivers/", methods=["POST"])
    @requires_admin_auth
    def new_driver(user):
        """
        POST Drivers
        ---
        tags:
          - restful
        parameters:
          - in: body
            name: body
            schema:
              $ref: 'Driver_POST'
        securityDefinitions:
            basicAuth:
                type: basic
                definition: admin account
        responses:
          201:
            description: The driver has been created
            schema:
              id: Driver_POST
              properties:
                first_name:
                  type: string
                  default: John
                last_name:
                  type: string
                  default: Doe
                ssn:
                  type: integer
                  default: 123456789
                email:
                  type: string
                  default: jd@busbus.ca
        """
        json_input = request.get_json()
        try:
            driver = driver_schema.load(json_input)
        except ValidationError as err:
            return {"errors": err.messages}, 422
        driver.save()
        return driver_schema.dump(driver)

class Buses(Resource):
    @app.route("/buses/", methods=["GET"])
    def get_buses():
        """
        GET Buses
        ---
        tags:
          - restful
        responses:
          200:
            description: Bus data
            schema:
              id: Bus_GET
              properties:
                id:
                    type: integer
                    default: 1
                model:
                    type: string
                    default: ModelU
                make:
                    type: string
                    default: MakeU
                capacity:
                    type: integer
                    default: 64
        """
        buses = Bus.select()
        return bus_schemas.dump(list(buses))

    @app.route("/buses/", methods=["POST"])
    @requires_admin_auth
    def new_bus(user):
        """
        POST Buses
        ---
        tags:
          - restful
        parameters:
          - in: body
            name: body
            schema:
                $ref: 'Bus_POST'
        securityDefinitions:
            basicAuth:
                type: basic
                definition: admin account
        responses:
          201:
            description: The bus has been created
            schema:
              id: Bus_POST
              properties:
                model:
                    type: string
                    default: ModelU
                make:
                    type: string
                    default: MakeU
                capacity:
                    type: integer
                    default: 64
        """
        json_input = request.get_json()
        try:
            bus = bus_schema.load(json_input)
        except ValidationError as err:
            return {"errors": err.messages}, 422
        bus.save()
        return bus_schema.dump(bus)


class Schedules(Resource):
    @app.route("/schedules/", methods=["GET"])
    def get_schedules():
        """
        GET Schedules
        ---
        tags:
          - restful
        responses:
          200:
            description: Schedule data
            schema:
              id: Schedule_GET
              properties:
                buses:
                    bus_id:
                        type: integer
                        default: 1
                    default: [{"bus_id": 1}]
                drivers:
                    driver_id:
                        type: integer
                        default: 1
                    default: [{"driver_id": 2}]
                week_num:
                    type: integer
                    default: 31
        """
        try:
            json_input = request.get_json()
            busArr = []
            if not (json_input.get("buses") is None):
                busArr = list([item.get('bus_id')for item in json_input["buses"]])
            driverArr = []
            if not (json_input.get("drivers") is None):
                driverArr = list([item.get('driver_id') for item in json_input["drivers"]])
            week_num = -1
            if not (json_input.get("week_num") is None):
                week_num = json_input['week_num']
        except Exception as err:
            return {"Message":"Invalid json content. Expected:\r\n week_num,\r\nbuses:[bus_id],\r\ndrivers:[driver_id]"}, 500

        schedules = Schedule.select()

        if(len(busArr) > 0):
            schedules = schedules.where(Schedule.bus_id << busArr)
        if(len(driverArr) > 0):
            schedules = schedules.where(Schedule.driver_id << driverArr)

        if(week_num >= 0 and week_num <= 52):
            w1 = str(dt.datetime.now().year) + "-W" + str(week_num)
            w2 = str(dt.datetime.now().year) + "-W" + str(week_num + 1)
            if week_num == 51:
                w2 = str(dt.datetime.now().year+1) + "-W0"

            startDate = dt.datetime.strptime(w1 + '-0-00:00', "%Y-W%W-%w-%H:%M").timestamp()
            endDate = dt.datetime.strptime(w2 + '-6-23:59:59', "%Y-W%W-%w-%H:%M:%S").timestamp()
            print(str(startDate) + " " + str(endDate))
            schedules = schedules.where(Schedule.start_datetime >= startDate)
            schedules = schedules.where(Schedule.end_datetime <= endDate)

        schedules = schedules.order_by(Schedule.start_datetime.asc())
        return schedule_schemas.dump(list(schedules))


    @app.route("/schedules/", methods=["POST"])
    @requires_admin_auth
    def new_schedule(user):
        """
        POST Schedules
        ---
        tags:
          - restful
        parameters:
          - in: body
            name: body
            schema:
              $ref: 'Schedule_POST'
        securityDefinitions:
            basicAuth:
                type: basic
                definition: admin account
        responses:
          201:
            description: The schedule has been created
            schema:
              id: Schedule_POST
              properties:
                bus_id:
                    type: integer
                    default: 1
                driver_id:
                    type: integer
                    default: 1
                start_datetime:
                    type: integer
                    default: 1660493590
                end_datetime:
                    type: integer
                    default: 1660479190
                    
        """
        json_input = request.get_json()
        try:

            sched = schedule_schema.load(json_input)    
            sched.save()
            
        except ValidationError as err:
            return {"Message":err.messages}, 422
      
        return schedule_schema.dump(sched)

    @app.route("/schedules/", methods=["DELETE"])
    @requires_admin_auth
    def delete_schedule(user):
        """
        DELETE Schedules
        ---
        tags:
          - restful
        parameters:
          - in: body
            name: body
            schema:
              $ref: Schedule_DEL
        responses:
          200:
            description: The schedules has been deleted
            schema:
                id: Schedule_DEL
                properties:
                    schedules:
                        id:
                            type: integer
                            default: 1
                        default: [{"id":1}]
        """
        json_input = request.get_json()
        try:
            schedArr = list([item.get('id') for item in json_input["schedules"]])
        except Exception as err:
            return {"Message":"Invalid json content. Expected:\r\schedules:[id]"}, 500
        
        scheds = Schedule.delete().where(Schedule.id << schedArr)
        scheds.execute()
        return {"Message":"Successfully deleted Schedules"}, 200
    

api.add_resource(Drivers, '/drivers')
api.add_resource(Buses, '/nbuses')
api.add_resource(Schedules, '/schedules')

if __name__ == "__main__":
    create_tables()
    app.run(port=5000, debug=True)