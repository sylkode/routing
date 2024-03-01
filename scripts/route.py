import pandas as pd
import numpy as np
import requests 
from requests.exceptions import HTTPError 
import sys
import argparse
import json
from io import StringIO
import os.path
import datetime
import geopandas as gpd
import time as tm
from shapely.geometry import LineString
"""
    
    Usage:
    
    route.py --start 0.0 0.0 --end 0.0 0.0 --routing tomtom --out myfile.txt
    route.py --infile myfile.txt --routing tomtom --out myfile.txt
        reads start and end coordinates in a csv file with id,startlat,startlon,endlat,endlon
    
    Description: download a routing result from a REST routing API
    
    
"""

test = False
rest_default_url = {'ors':"https://api.openrouteservice.org/v2/directions",
                    'tomtom':"https://api.tomtom.com/routing/1/calculateRoute"}


class Router:
    def __init__(self):
        apikey = './tomtom-api-key.txt'
        parser = argparse.ArgumentParser(description='download a routing result from a REST routing API')
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--check', help='display default parameters', action="store_true")
        group.add_argument('--route', help='do the routing', action="store_true")

        parser.add_argument('--start', dest='start', help='lat lon start point', type=float, nargs=2, required=False,
                            default=[49.49331, 5.98375])  # default to esch gare
        parser.add_argument('--end', dest='end', help='lat lon  end point', type=float, nargs=2, required=False,
                            default=[49.60050, 6.13336])  # default to luxembourg gare
        parser.add_argument('--infile', help='start and end coordinates csv file', required=False)

        parser.add_argument('--summary', help='True: save csv points, False: save route line and summary',
                            action='store_true')
        parser.add_argument('--geometry', help='save line geometry, False: save attributes only', action='store_true')
        parser.add_argument('--outfile', dest='outfile', help='save routing results to csv|gpkg file', required=False,
                            default='../data/out/route.csv')
        parser.add_argument('--jsondir', dest='jsondir', help='set json directory to save the details of the routes', required=False, default='../data/out/json')
        parser.add_argument('--json', help='load json file if exists, request and save it otherwise',
                            action='store_true')
        parser.add_argument('--router', dest='router', help='REST routing API', required=False, default='tomtom',
                            choices=['tomtom', 'ors'])
        parser.add_argument('--route_weighting', help='routing weighting criteria', required=False, default='shortest',
                            choices=['shortest', 'fastest'])
        parser.add_argument('--resturl', help='REST routing custom url', required=False, default='')
        parser.add_argument('--api-key', dest='key', help='API-key-file', required=False, default=apikey)
        parser.add_argument('--travelMode', help='Mode of transport', required=False, default="car",
                            choices=['car', 'pedestrian'])
        parser.set_defaults(fonc=handler)
        self.parser = parser


def get_data(url):
    """
        Get a http response to url request 
        
        Arguments
        ---------
            url: url to request with its parameters 
        Returns
        -------
            response: can be None
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
    except HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')
    except Exception as err:
        print(f'Other error occurred: {err}')
        raise
    return response

def post_data(url, headers, body):
    """
        Post a http response to url request 
        
        Arguments
        ---------
            url: url to request with its parameters 
            headers: dict with http headers 
            body: dict with post parameters
        Returns
        -------
            response: can be None
    """
    try:
        response = requests.post(url, json=body, headers=headers)
        response.raise_for_status()
    except HTTPError as http_err:
        print(f'HTTP POST error occurred: {http_err}')
    except Exception as err:
        print(f'Other POST error occurred: {err}')
        raise
    return response

def isochronesfromfile(args, key):
    """
        Download the routing results from REST router accordingly to the lat/lon coords from args.infile
        
        args.infile is a csv file and MUST contain a header with the following:
            id, lat,lon
        
        Arguments
        ---------
            args    : from argparse
            key     : api key value
        Returns
        -------
            DataFrame with route points if args.summary is True, GeoDataFrame with route line and summary otherwise
    """
    if args.summary:
        df = pd.DataFrame()
    else:
        df = gpd.GeoDataFrame()
    if args.infile:
        inreq = pd.read_csv(args.infile, dtype={'id':'str'})
        inreq.info()
        print(f'read {args.infile}: {len(inreq.index)} lines')
        for index, row in inreq.iterrows():
            print(f'row id {row["id"]} lat {row["lat"]}')
            dfisochrone = isochronefinder(args, [row['lat'],row['lon']], row['id'], key)
            if not dfisochrone.empty:
                df = pd.concat([df, dfisochrone],sort=False)
    return df


def isochronefinder(args, coords, ranges, id, key):
    """
        Downloads the isochrones results from REST router accordingly to the start, end arguments
            
        Arguments
        ---------
            args    : from argparse
            coords   : array with  lat lon
            ranges   : Maximum range value of the analysis in seconds for time and metres for distance.Alternatively a comma separated list of specific single range values if more than one location is set
            id      : str to identify the route
            key     : api key value
        Returns
        -------
            DataFrame: with isochrones geometry if args.summary is True, GeoDataFrame with isochrone area and summary otherwise
    """
    pyisochrone = []
    df= pd.DataFrame()
    #key = getApiKey(args)
    if args.router=='ors':
        # default free flow drive
        
        '''
            import requests
        
            body = {"locations":[[5.886453,49.532905]],"range":[800,1000],"range_type":"distance","area_units":"km","units":"m"}
        
            headers = {
                'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
                'Authorization': 'your-api-key',
                'Content-Type': 'application/json; charset=utf-8'
            }
            call = requests.post('https://api.openrouteservice.org/v2/isochrones/driving-car', json=body, headers=headers)

            print(call.status_code, call.reason)
            print(call.text)
        '''
        headers = {
            'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8','Authorization': key, 'Content-Type': 'application/json; charset=utf-8'
        }
        baseurl = rest_default_url["ors"]
        if len(args.resturl)>0:
            baseurl = args.resturl
            url = f'{baseurl}/driving-car/geojson'
            if args.travelMode=='pedestrian':
                url = f'{baseurl}/foot-walking/geojson'
            if "localhost" in args.resturl: # non V2 API support http://localhost:8080/ors/directions
                profile='driving-car'
                if args.travelMode=='pedestrian':
                    profile='foot-walking'
                url = f'{baseurl}?locations={coords[1]},{coords[0]}&range={",".join(map(str,ranges))}&format=geojson&preference=shortest'
        body = {"locations":[[coords[1],coords[0]]], "range":ranges,"id":id, "range_type":"distance","units":"m"}
        if args.json:
            #check if args.jsondir/{id}.json is present otherwise do request
            if os.path.isfile(f'{args.jsondir}/{id}.json'):
                print(f'\tread ors {args.jsondir}/{id}.json')
                with open(f'{args.jsondir}/{id}.json', 'r') as file:
                    data = file.read().replace('\n', '')
                    if data!="null":
                        pyisochrone = json.load(StringIO(data))
            else:
                response = post_data(url, headers, body)
                # if (len(args.resturl)>0) & ("localhost" in args.resturl):
                    # print(f'\tGET {url}')
                    # response = get_data(url)
                # else:
                    # response = post_data(url, headers, body)
                    #tm.sleep(2) # OpenRouteService does not support more than 40 requests in a minute, lets try with a 2s sleep
                print(response.status_code, response.reason)
                print(f'\tors request |save json')
                pyisochrone = getJSONResponse(response, id)
                # save json for later
                writeJSONResponse(args,pyisochrone,id)
        else:
            if test:
                with open('U:/Projets/2018_CURHA_GPS/data/walk/ors/example.geojson', 'r') as file:
                    data = file.read().replace('\n', '')
                    pyisochrone = json.load(StringIO(data))
            else:
                if (len(args.resturl)>0) & ("localhost" in args.resturl):
                    response = get_data(url)
                else:
                    response = post_data(url, headers, body)
                print(f'ors request')
                pyisochrone = getJSONResponse(response, id)
    
    else:
        print (f'router.py does not support the router {args.router}')
    df = getisochroneinfo(args, pyisochrone,id)
    # if args.summary:
        # #print(f'route info output  implemented  for {args.router}')
        # df = getisochroneinfo(args, pyisochrone,id)
    # else:
        # #print(f'route points output  implemented  for {args.router}')
        # df = getisochronegeometry(args, pyisochrone,id)
    return df

def routesfromfile(args, key):
    """
        Download the routing results from REST router accordingly to the start/end coords from args.infile
        
        args.infile is a csv file and MUST contain a header with the following:
            id, start_lat, start_lon, end_lat, end_lon
        
        Arguments
        ---------
            args    : from argparse
            key     : api key value
        Returns
        -------
            DataFrame with route points if args.summary is True, GeoDataFrame with route line and summary otherwise
    """
    if args.summary:
        df = pd.DataFrame()
    else:
        df = gpd.GeoDataFrame()
    if args.infile:
        inreq = pd.read_csv(args.infile, dtype={'id':'str'})
        inreq.info()
        print(f'read {args.infile}: {len(inreq.index)} lines')
        for index, row in inreq.iterrows():
            print(f'row id {row["id"]} start_lat {row["start_lat"]}')
            dfroute = routefinder(args, [row['start_lat'],row['start_lon']], [row['end_lat'],row['end_lon']], row['id'], key)
            if not dfroute.empty:
                df = pd.concat([df, dfroute],sort=False)
    return df

def routefinder(args, start, end, id, key):
    """
        Downloads the routing results from REST router accordingly to the start, end arguments
            
        Arguments
        ---------
            args    : from argparse
            start   : array with  lat lon
            end     : array with  lat lon
            id      : str to identify the route
            key     : api key value
        Returns
        -------
            DataFrame: with route points if args.summary is True, GeoDataFrame with route line and summary otherwise
    """
    pyroute = []
    df= pd.DataFrame()
    #key = getApiKey(args)
    if args.router == 'tomtom':
        time = tomorrow2am()
        baseurl = rest_default_url["tomtom"]
        if len(args.resturl)>0:
            baseurl = args.resturl
        url = f'{baseurl}/{start[0]},{start[1]}:{end[0]},{end[1]}/json?avoid=unpavedRoads&routeType={args.route_weighting}&traffic=true&travelMode=car&key={key}&departAt={time}&travelMode={args.travelMode}'
        
        if args.json:
            #check if args.jsondir/{id}.json is present otherwise do request
            if os.path.isfile(f'{args.jsondir}/{id}.json'):
                with open(f'{args.jsondir}/{id}.json', 'r') as file:
                    data = file.read().replace('\n', '')
                    if data!="null":
                        pyroute = json.load(StringIO(data))
            else:
                response = get_data(url)
                pyroute = getJSONResponse(response, id)
                # save json for later
                writeJSONResponse(args,pyroute,id)
        else:
            if test:
                with open('U:\\temp\\route.json', 'r') as file:
                    data = file.read().replace('\n', '')
                    pyroute = json.load(StringIO(data))
            else:
                response = get_data(url)
                pyroute = getJSONResponse(response, id)
    elif args.router == 'ors':
        # default free flow drive
        
        '''
            this gives a detailed geometry:
            
            import requests

            body = {"coordinates":[[8.681495,49.41461],[8.686507,49.41943],[8.687872,49.420318]],"elevation":"true","id":101,"instructions":"true","maneuvers":"true","preference":"fastest","units":"m"}

            headers = {
                'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
                'Authorization': '5b3ce3597851110001cf62489e097ebf8805476a839f24b83345cc4e',
                'Content-Type': 'application/json; charset=utf-8'
            }
            call = requests.post('https://api.openrouteservice.org/v2/directions/foot-walking/geojson', json=body, headers=headers)

            print(call.status_code, call.reason)
            print(call.text)
        '''
        headers = {
            'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
            'Authorization': key, 'Content-Type': 'application/json; charset=utf-8 '
        }
        baseurl = rest_default_url["ors"]
        body = {"coordinates": [[start[1], start[0]], [end[1], end[0]]], "elevation": "true",
                "id": id, "instructions": "false", "maneuvers": "false", "preference": args.route_weighting,
                "units": "m"}
        if len(args.resturl)>0:
            baseurl = args.resturl
            url = f'{baseurl}/driving-car/geojson'
            if args.travelMode=='pedestrian':
                url = f'{baseurl}/foot-walking/geojson'
            if "localhost" in args.resturl:
                profile='driving-car'
                if args.travelMode=='pedestrian':
                    profile='foot-walking'
                if "v2" in args.resturl:
                    url = f'{baseurl}/{profile}/geojson'
                    body = {"coordinates": [[start[1], start[0]], [end[1], end[0]]],
                            "elevation": "true", "id": id, "instructions": "false", "maneuvers": "false",
                            "preference": args.route_weighting, "units": "m"}
                else: # non V2 API support http://localhost:8080/ors/directions
                    url = f'{baseurl}?coordinates={start[1]},{start[0]}|{end[1]},{end[0]}&profile={profile}&format' \
                      f'=geojson&elevation=true&preference={args.route_weighting}'

        if args.json:
            #check if args.jsondir/{id}.json is present otherwise do request
            if os.path.isfile(f'{args.jsondir}/{id}.json'):
                print(f'\tread ors {args.jsondir}/{id}.json')
                with open(f'{args.jsondir}/{id}.json', 'r') as file:
                    data = file.read().replace('\n', '')
                    if data!="null":
                        pyroute = json.load(StringIO(data))
            else:
                if (len(args.resturl)>0) & ("localhost" in args.resturl) & ('v2' not in args.resturl):
                    print(f'\tGET {url}')
                    response = get_data(url)
                elif (len(args.resturl)>0) & ("localhost" in args.resturl) & ('v2' in args.resturl):
                    print(f'\tPOST {url} and {body}')
                    response = post_data(url, headers, body)
                else:
                    response = post_data(url, headers, body)
                    tm.sleep(2) # OpenRouteService does not support more than 40 requests in a minute, lets try with a 2s sleep
                print(response.status_code, response.reason)
                print(f'\tors request |save json')
                pyroute = getJSONResponse(response, id)
                # save json for later
                writeJSONResponse(args,pyroute,id)
        else:
            if test:
                with open('U:/Projets/2018_CURHA_GPS/data/walk/ors/example.geojson', 'r') as file:
                    data = file.read().replace('\n', '')
                    pyroute = json.load(StringIO(data))
            else:
                if (len(args.resturl) > 0) & ("localhost" in args.resturl) & ('v2' not in args.resturl):
                    print(f'\tGET {url}')
                    response = get_data(url)
                elif (len(args.resturl) > 0) & ("localhost" in args.resturl) & ('v2' in args.resturl):
                    print(f'\tPOST {url} and {body}')
                    response = post_data(url, headers, body)
                else:
                    response = post_data(url, headers, body)
                print(f'ors request')
                pyroute = getJSONResponse(response, id)

    else:
        print (f'router.py does not support the router {args.router}')
    
    if args.summary:
        #print(f'route info output  implemented  for {args.router}')
        df = getrouteinfo(args, pyroute,id)
    else:
        #print(f'route points output  implemented  for {args.router}')
        df = getroutepoints(args, pyroute,id)
    return df

def writeJSONResponse(args,pyroute,id):
    """
        write the JSON structure in args.jsondir/id.json 
        
        Arguments
        ---------
            args    : from argparse
            pyroute : python representation of the json structure
            id      : integer to identify the route
    """
    file = open(f'{args.jsondir}/{id}.json', 'w')
    file.write(json.dumps(pyroute))
    file.close()
    
def getJSONResponse(response,id):
    """
        Get the JSON response 
        
        Arguments
        ---------
            response: the response
            id      : str to identify the route
        Returns
        -------
            python object: corresponding to the json decoding
    """
    pyroute = None
    if response.status_code == requests.codes.ok:
        pyroute = json.load(StringIO(response.text))
    else:
        print(f'\t{id} : response code is {response.status_code}')
    return pyroute


def getisochroneinfo(args,pyisochrone,id):
    """
        Process the python structure to retrieve the route summary info such as duration, distance etc.
        
        Arguments
        ---------
            args    : from argparse
            pyroute  : python object: corresponding to the json decoding
            id      : integer to identify the route
        Returns
        -------
            GeoDataFrame: summary with a line geometry
    """
    results = gpd.GeoDataFrame()
    try:
        points = getisochronegeometry(args,pyisochrone,id)
        if not points.empty:
            d = {'id':id}
            results = pd.DataFrame(d, index=[0])
            if args.geometry:
                geometry = gpd.points_from_xy(points.longitude, points.latitude)
                points = gpd.GeoDataFrame(points, geometry=geometry) # points is now a GeoDataFrame
                s = points.groupby(['id'])['geometry'].apply(lambda x: LineString(x.tolist()))
                d = {'id':s.index, 'geometry':s.values}
                results = gpd.GeoDataFrame(d,geometry=d['geometry'])
                results.crs = {'init':'epsg:4326'}
            if pyisochrone:
                if type(pyisochrone) is dict: 
                    if args.router=='ors':
                        if "features" in pyisochrone:
                            if (len(args.resturl)>0) & ("localhost" in args.resturl):
                                summary = pyisochrone["features"][0]["properties"]["summary"][0]
                                results["lengthInMeters"] = summary["distance"]
                                results["travelTimeInSeconds"] = summary["duration"]
                                if "descent" in summary :
                                    results["descent"] = summary["descent"]
                                if "ascent" in summary:
                                    results["ascent"] = summary["ascent"]
                            else:
                                summary = pyisochrone["features"][0]["properties"]["summary"]
                                results["lengthInMeters"] = summary["distance"]
                                results["travelTimeInSeconds"] = summary["duration"]
                                results["descent"] = pyisochrone["features"][0]["properties"]["descent"]
                                results["ascent"] = pyisochrone["features"][0]["properties"]["ascent"]                        
                    else:
                        print(f'unknown router {args.router}')
    except Exception as err:
        print(f'Other error occurred in {id}: {err}')
        raise
    return results


def getisochronegeometry(args,pyisochrone,id):
    """
        Process the python structure to retrieve the isochrones
        
        Arguments
        ---------
            args    : from argparse
            pyisochrone : python object: corresponding to the json decoding
            id      : str to identify the isochrones
        Returns
        -------
            DataFrame:  a succession of coordinates of the route
                        id,geometry
    """
    df = pd.DataFrame()
    latitude = []
    longitude = []
    sequence = []
    seq = 0
    try:
        if pyisochrone:
            if(args.router=='ors'):
                print('todo: code it')
            elif(args.router=='ors'):
                if type(pyisochrone) is dict: 
                    if "features" in pyisochrone:
                        altitude = []
                        for point in pyisochrone["features"][0]["geometry"]["coordinates"]:
                            seq += 1
                            longitude.append(point[0])
                            latitude.append(point[1])
                            altitude.append(point[2])
                            sequence.append(seq)
                        df = pd.DataFrame({'id':id, 'latitude': latitude, 'longitude':longitude,'altitude':altitude,'seq':sequence})
                        print(f'\t{id}: points count: {len(df.index)}')
            else:
                print(f'unknown router {args.router}')
    except Exception as err:
        print(f'Other error occurred: {err}')
        raise
    return df

def getrouteinfo(args,pyroute,id):
    """
        Process the python structure to retrieve the route summary info such as duration, distance etc.
        
        Arguments
        ---------
            args    : from argparse
            pyroute  : python object: corresponding to the json decoding
            id      : integer to identify the route
        Returns
        -------
            GeoDataFrame: summary with a line geometry
    """
    results = gpd.GeoDataFrame()
    try:
        points = getroutepoints(args,pyroute,id)
        if not points.empty:
            d = {'id':id}
            results = pd.DataFrame(d, index=[0])
            if args.geometry:
                geometry = gpd.points_from_xy(points.longitude, points.latitude)
                points = gpd.GeoDataFrame(points, geometry=geometry) # points is now a GeoDataFrame
                if len(points) > 1:
                    s = points.groupby(['id'])['geometry'].apply(lambda x: LineString(x.tolist()))
                    d = {'id':s.index, 'geometry':s.values}
                else:
                    d = {'id':points['id'], 'geometry':None}
                results = gpd.GeoDataFrame(d,geometry=d['geometry'])
                results.crs = {'init':'epsg:4326'}
            if pyroute:
                if type(pyroute) is dict: 
                    if args.router=='tomtom':
                        if "routes" in pyroute:
                            summary = pyroute["routes"][0]["summary"]
                            results["lengthInMeters"] = summary["lengthInMeters"]
                            results["travelTimeInSeconds"] = summary["travelTimeInSeconds"]
                    elif args.router == 'ors':
                        if "features" in pyroute:
                            if (len(args.resturl)>0) & ("localhost" in args.resturl):
                                if "v2" in args.resturl:
                                    summary = pyroute["features"][0]["properties"]["summary"]
                                else:
                                    summary = pyroute["features"][0]["properties"]["summary"][0]
                                if 'distance' in summary:
                                    results["lengthInMeters"] = summary["distance"]
                                else:
                                    results["lengthInMeters"] = 0.0
                                if 'duration' in summary:
                                    results["travelTimeInSeconds"] = summary["duration"]
                                else:
                                    results["travelTimeInSeconds"] = 0.0
                                if "descent" in summary :
                                    results["descent"] = summary["descent"]
                                # else:
                                    # results["descent"] = None
                                if "ascent" in summary:
                                    results["ascent"] = summary["ascent"]
                                # else:
                                    # results["ascent"] = None
                            else:
                                summary = pyroute["features"][0]["properties"]["summary"]
                                results["lengthInMeters"] = summary["distance"]
                                results["travelTimeInSeconds"] = summary["duration"]
                                results["descent"] = pyroute["features"][0]["properties"]["descent"]
                                results["ascent"] = pyroute["features"][0]["properties"]["ascent"]                        
                    else:
                        print(f'unknown router {args.router}')
    except Exception as err:
        print(f'Other error occurred in {id}: {err}')
        raise
    return results

def getroutepoints(args,pyroute,id):
    """
        Process the python structure to retrieve the route coordinates
        
        Arguments
        ---------
            args    : from argparse
            pyroute : python object: corresponding to the json decoding
            id      : str to identify the route
        Returns
        -------
            DataFrame:  a succession of coordinates of the route
                        id,latitude,longitude,seq
    """
    df = pd.DataFrame()
    latitude = []
    longitude = []
    sequence = []
    seq = 0
    try:
        if pyroute:
            if(args.router=='tomtom'):
                if type(pyroute) is dict: 
                    if "routes" in pyroute:
                        for leg in pyroute["routes"][0]["legs"]: # TODO check for error
                            for point in leg["points"]:
                                seq += 1
                                latitude.append(point["latitude"])
                                longitude.append(point["longitude"])
                                sequence.append(seq)
                            df = pd.DataFrame({'id':id, 'latitude': latitude, 'longitude':longitude, 'seq':sequence})
                            print(f'\t{id}: points count: {len(df.index)}')
            elif(args.router=='ors'):
                if type(pyroute) is dict: 
                    if "features" in pyroute:
                        altitude = []
                        for point in pyroute["features"][0]["geometry"]["coordinates"]:
                            seq += 1
                            longitude.append(point[0])
                            latitude.append(point[1])
                            if len(point)==3:
                                altitude.append(point[2])
                            else:
                                altitude.append(np.nan)
                            sequence.append(seq)
                        df = pd.DataFrame({'id':id, 'latitude': latitude, 'longitude':longitude,'altitude':altitude,'seq':sequence})
                        print(f'\t{id}: points count: {len(df.index)}')
            else:
                print(f'unknown router {args.router}')
    except Exception as err:
        print(f'Other error occurred: {err}')
        raise
    return df

def getApiKey(args):
    """
        Read a text key file in args.key with the key for the API

        Arguments
        ---------
            args    : from argparse
        Returns
        -------
            string with the key
    """
    data=''
    try:
        with open(f'{args.key}', 'r') as file:
            data = file.read().replace('\n', '')
    except Exception as err:
        print(f'Error occurred: {err}')
    return data

def saveResults(args,df):
    """
        Save df results in csv|gpkg format accordingly with args.csv
        Write file in args.outfile
        
        Arguments
        ---------
            args    : from argparse
            df      : GeoDataFrame if args.summary, DataFrame otherwise
    """
    df.to_csv(args.outfile, index=False, header=True)
    if args.summary & args.geometry:
        basename=os.path.basename(args.outfile)
        basename=basename[:-4] # assuming '.csv'
        dirname =os.path.dirname(args.outfile)
        df.to_file(f'{dirname}/{basename}.gpkg',layer=basename,driver="GPKG")

def handler(args):
    """ 
        Main handler 
    """
    print('route.py starting\n')
    if args.check:
        check(args)
    if args.route:
        for key in vars(args).keys():
            print(f'\t{key} : {vars(args)[key]}')
        key = getApiKey(args)
        if args.infile:
            df = routesfromfile(args,key)
            saveResults(args,df)
        else:
            df = routefinder(args, args.start, args.end, os.path.basename(args.outfile[:-4]), key)
            saveResults(args,df)
    # if args.isochrone:
    #     for key in vars(args).keys():
    #         print(f'\t{key} : {vars(args)[key]}')
    #     key = getApiKey(args)
    #     if args.infile:
    #         df = isochronesfromfile(args,key)
    #         saveResults(args,df)
    print('\nroute.py closing')


def check(args):
    print('check arguments')
    for key in vars(args).keys():
        print(f'\t{key} : {vars(args)[key]}')

def tomorrow2am():
    now = datetime.datetime.today()
    tm = now + datetime.timedelta(days=1)
    t =datetime.time(hour=2)
    tm = datetime.datetime.combine(tm, t)
    return tm.strftime('%Y-%m-%dT%H:%M:%S') # 2015-04-02T15:01:17

def main():
    """
        python route.py --check --jsondir U:\Projets\2018_CURHA_GPS\data\pcc\json --json
    """
    myrouter = Router()
    args = myrouter.parser.parse_args()
    print(f'geometry: {args.geometry} json: {args.json} summary: {args.summary}')
    if args.fonc: 
        args.fonc(args)
    

if __name__ == "__main__":
    sys.exit(main())
