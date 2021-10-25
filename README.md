# flask-mssql-restapi
Implementing a REST API using Python Flask and Azure SQL


### Delete Stored Procedure
```
CREATE OR ALTER  PROCEDURE [dbo].[delete_temperature]
@json NVARCHAR(max)
AS
SET NOCOUNT ON;

DECLARE @TemperatureId INT = JSON_VALUE(@Json, '$.temperatureId');  --this refers to the key inside the json
	
DELETE FROM [temperatures] WHERE [temperatureId] = @TemperatureId;

SELECT * FROM (SELECT temperatureId = @TemperatureId) D FOR JSON AUTO;

GO
```
