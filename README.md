# Routing from origin destination file with REST API services

This script automatize the requests to online services to calculate shortest or quickest routes form origin to destination.

The supported services are tomtom and openrouteservice.
They both require a registration to get an API key. Their plans can be free or 

It is also possible to install a local version of openrouteservice using a subset of the underlying OpenStreeMap dataset on your area of interest.

## how it works?

`route.py --start 0.0 0.0 --end 0.0 0.0 --routing tomtom --out myfile.txt`

`route.py --infile myfile.txt --routing tomtom --out myfile.txt`  
        reads start and end coordinates in a csv file with id,startlat,startlon,endlat,endlon