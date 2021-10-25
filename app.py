import sys
import os
import json
import pyodbc
import socket
from flask import Flask
from flask_restful import reqparse, abort, Api, Resource
from threading import Lock
from tenacity import *
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.ext.flask.flask_middleware import FlaskMiddleware
from opencensus.trace.samplers import ProbabilitySampler
import logging

# Initialize Flask
app = Flask(__name__)

# Setup Azure Monitor
if 'APPINSIGHTS_KEY' in os.environ:
    middleware = FlaskMiddleware(
        app,
        exporter=AzureExporter(connection_string="InstrumentationKey={0}".format(
            os.environ['APPINSIGHTS_KEY'])),
        sampler=ProbabilitySampler(rate=1.0),
    )

# Setup Flask Restful framework
api = Api(app)
parser = reqparse.RequestParser()
parser.add_argument('sensorNum')
parser.add_argument('temperature')
parser.add_argument('humidity')

# Implement singleton to avoid global objects


class ConnectionManager(object):
    __instance = None
    __connection = None
    __lock = Lock()

    def __new__(cls):
        if ConnectionManager.__instance is None:
            ConnectionManager.__instance = object.__new__(cls)
        return ConnectionManager.__instance

    def __getConnection(self):
        if (self.__connection == None):
            application_name = ";APP={0}".format(socket.gethostname())
            self.__connection = pyodbc.connect(
                os.environ['azuresqlconn'] + application_name)

        return self.__connection

    def __removeConnection(self):
        self.__connection = None

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(10), retry=retry_if_exception_type(pyodbc.OperationalError), after=after_log(app.logger, logging.DEBUG))
    def executeQueryJSON(self, procedure, payload=None):
        result = {}
        try:
            conn = self.__getConnection()

            cursor = conn.cursor()

            if payload:
                cursor.execute(f"EXEC {procedure} ?", json.dumps(payload))
            else:
                cursor.execute(f"EXEC {procedure}")

            result = cursor.fetchone()

            if result:
                result = json.loads(result[0])
            else:
                result = {}

            cursor.commit()
        except pyodbc.OperationalError as e:
            app.logger.error(f"{e.args[1]}")
            if e.args[0] == "08S01":
                # If there is a "Communication Link Failure" error,
                # then connection must be removed
                # as it will be in an invalid state
                self.__removeConnection()
                raise
        finally:
            cursor.close()

        return result


class Queryable(Resource):
    def executeQueryJson(self, verb, payload=None):
        result = {}
        entity = type(self).__name__.lower()
        procedure = f"dbo.{verb}_{entity}"
        result = ConnectionManager().executeQueryJSON(procedure, payload)
        return result


# Temperature Class
class Temperature(Queryable):
    def get(self, temperature_id):
        #temperatures = {}
        #temperatures["TemperatureID"] = temperatureId
        temperature = {"temperatureId" : temperature_id}
        result = self.executeQueryJson("get", temperature)
        return result, 200

    def post(self):
        args = parser.parse_args()
        result = self.executeQueryJson("post", args)
        return result, 201

    def put(self):
        args = parser.parse_args()
        temperatures = json.loads(args['temperatures'])
        result = self.executeQueryJson("put", temperatures)
        return result, 201

    def patch(self, temperatureId):
        args = parser.parse_args()
        temperatures = json.loads(args['temperatures'])
        temperatures["TemperatureID"] = temperatureId
        result = self.executeQueryJson("patch", temperatures)
        return result, 202

    def delete(self, temperatureId):
        temperatures = {}
        temperatures["TemperatureID"] = temperatureId
        result = self.executeQueryJson("delete", temperatures)
        return result, 202


# Temperatures Class
class Temperatures(Queryable):
    def get(self):
        result = self.executeQueryJson("get")
        return result, 200


# Create API routes
api.add_resource(Temperature, '/temperature', '/temperature/<temperature_id>')
api.add_resource(Temperatures, '/temperatures')
