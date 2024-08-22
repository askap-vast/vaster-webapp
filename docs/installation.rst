# Installation

## Development

To install the webapp locally in development mode, start the docker containers and network with

```
docker compose up -d
```

Once successfully started you can access it at http://localhost:80 

## Production

To start the production version of the webapp, you need to be sure to change all of the USERNAME and PASSWORDS to appropriately complex versions.

You will also need to add your specific host URL to the list in ALLOWED_HOSTS, separated by a space. 

Once the containers are started and they report back healthy, you should be able to access the webapp at your set URL on port 80. 

SSL certificates have not been implemented just yet - Github issue (Link to issue)


