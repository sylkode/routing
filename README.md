# Routing from origin destination file with REST API services

This script automatize the requests to online services to calculate shortest or quickest routes form origin to destination.

The supported services are tomtom and openrouteservice.
They both require a registration to get an API key. Their plans can be free or 

It is also possible to install a local version of openrouteservice using a subset of the underlying OpenStreeMap dataset on your area of interest.

## Quick start


`route.py --start 0.0 0.0 --end 0.0 0.0 --routing tomtom --out myfile.txt`

`route.py --infile myfile.txt --routing tomtom --out myfile.txt`  
        reads start and end coordinates in a csv file with id,startlat,startlon,endlat,endlon

## Quick documentation

1. Prerequisite
python 3 and above and the libraries used by the script
2. Get an API key from the REST routing service
and then save it in a text file under /any/path/to/api-key-textfile.txt
3. check that output folders exist
`python route.py --check`  
The `--check` parameter will display all parameters on the standard output.

You can check that everything works using the followinfg command line :   
`python route.py --api-key /any/path/to/api-key-textfile.txt --route`

