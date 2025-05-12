# Data management for De Casa Al Cole

This repository contains three different applications that gather and prepare the data for "De Casa al Cole":

* [`schools`](schools) is the app that scrapes the official website to get schools information in the Comunitat Valenciana
* [`postcodes`](postcodes) downloads the public addresses dataset for the three provinces and derives a single point per postal code
* [`traveltimes`](traveltimes) downloads an OSM extract and sets up a routing engine to then compute the travel distances and times for all the postal codes in the region

Check each app `README.md` file for details. In general they all function similarly, relying on `docker` and `docker compose` to build one or more containers that produce the final results into a `data` folder.
