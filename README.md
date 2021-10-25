# flask-mssql-restapi
Implementing a REST API using Python Flask and Azure SQL


### Delete Stored Procedure
```
CREATE   PROCEDURE [dbo].[delete_temperature]
@json NVARCHAR(max)
AS
SET NOCOUNT ON;
	
DELETE
FROM 
	[temperatures] 
WHERE [temperatureId] =
 (SELECT temperatureId FROM OPENJSON(@json) WITH (temperatureId INT '$.temperatureId')) --this refers to the key inside the json
GO
```
