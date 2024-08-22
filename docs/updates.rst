Updates

Updating the ATNF Pulsar table is done automatically on 12am Sunday every week.

Alternatively, you can force it to happen manually by using the following docker command:

```
docker exec -it ywangvaster-web python3 manage.py refresh_pulsar_table
```

which will pull the update file from the ATNF database and add the new version. 
You will see all the logs to the console from the update script.