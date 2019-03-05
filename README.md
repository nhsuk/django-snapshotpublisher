Django - Snapshot Publisher
=============================

[[TO_DO_ADD_DESCRIPTION]]

Quick start
-----------

[[TO_DO]]


How to use
----------

[[TO_DO]]


How to contribute
-----------------

### Requirements
* Docker
* docker-compose
You'll get all this lot installed nicely with (https://docs.docker.com/docker-for-mac/install).


### Setup locally
Build the image
```
docker-compose build
```
Run the containers
```
docker-compose up
```
Create super user:
```
docker-compose run --rm web python manage.py createsuperuser
```