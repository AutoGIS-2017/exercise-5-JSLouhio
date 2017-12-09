# -*- coding: utf-8 -*-
"""

Visualize.py

"""
import matplotlib.pyplot as plt
import geopandas as gpd
from bokeh.plotting import figure, save
from bokeh.models import ColumnDataSource, HoverTool, LogColorMapper
from bokeh.palettes import Plasma256 as palette
import pysal as ps
from shapely.geometry import MultiLineString
from bokeh.models import Title

###############################################################################
#p1:  Static Maps
###############################################################################

# Filepaths
travel_fp = r"dataE5/TravelTimes_to_5975375_RailwayStation.shp"
roads_fp = r"dataE5/roads.shp"
metro_fp = r"dataE5/metro.shp"
pop_fp = r"dataE5/Vaestotietoruudukko_2015.shp"

# Read files
ttCentral = gpd.read_file(travel_fp)
roads = gpd.read_file(roads_fp)
metro = gpd.read_file(metro_fp)
pop = gpd.read_file(pop_fp)

#filter out na's
ttCentral = ttCentral[ttCentral['walk_d'] >= 0]

# Get the CRS of the grid
travelcrs = ttCentral.crs

# Reproject geometries using the crs of travel time grid
roads = roads.to_crs(crs=travelcrs)
metro = metro.to_crs(crs=travelcrs)
pop = pop.to_crs(crs=travelcrs)

# Next, goal is to visualize how much travel distances differ from shortest possible euclidean distances to Central railway station.
# travel time -Data's source, Accesibility recearch group, tells what are the relevant columns for this here:
#    <http://blogs.helsinki.fi/accessibility/helsinki-region-travel-time-matrix-2015/>
# -> pt_r_d: 	Distance in meters of the public transportation route in rush hour traffic
# -> car_r_d: 	Distance in meters of the private car route in rush hour traffic
# -> walk_d: 	Distance in meters of the walking route

#Row 12165 contains the ykr grid id that matches the to_id column,
# thus it probably contains the central railway station
# this calculates centroid for that square, giving us geometry for the station.
centralpoint = ttCentral.loc[12165]['geometry'].centroid

# new column for minimum distances, filled by calculating shortest distance from each row's geometry to previous central centroid.
ttCentral['minDist'] = ttCentral['geometry'].centroid.distance(centralpoint).astype(int)

#Calculate how much longer route car travels to central in rush hour compared to minimum possible.
ttCentral['carExtraD'] = ttCentral['car_r_d'] - ttCentral['minDist']

#same for public transportation
ttCentral['ptExtraD'] = ttCentral['pt_r_d'] - ttCentral['minDist']

#next the visualization

#Note-to-self: list of cmap ranges: http://matplotlib.org/examples/color/colormaps_reference.html
# '_r' reverts the scale! (ex. cmap=''terrain_r'')

#public transport
mapTitle, mapLayer = plt.subplots(1)
mapLayer = ttCentral.plot(column="ptExtraD", linewidth=0.03, label = 'Meters', cmap="YlGn_r", scheme="quantiles", k=9, alpha=0.9, ax=mapLayer,  legend = True)

#add main roads and metro lines
roads.plot(ax=mapLayer, color="grey", linewidth=1.5)
metro.plot(ax=mapLayer, color="orange", linewidth=2.5)

#background color
mapLayer.set_facecolor("lightskyblue")

#Title for map
mapTitle.suptitle('Extra travel distance of public transport to central Helsinki \n (difference to shortest euclidean distance)')

#North arrow to southeastern corner
mapLayer.text(x=402400,y=6669000, s='^ \nN ', ha='center', fontsize=20, family='Courier new', rotation = 0)

#move legend so it doesn't overlap the map
leg = mapLayer.get_legend()
leg.set_bbox_to_anchor((1.58, 0.9))

#resize mapwindow, so that legend can also fit there.
mapBox = mapLayer.get_position()
mapLayer.set_position([mapBox.x0, mapBox.y0, mapBox.width*0.7, mapBox.height*0.7])
mapLayer.legend()

#save to file
plt.savefig("ptExtraDistance.png")

#same for car
mapTitle, mapLayer = plt.subplots(1)
mapLayer = ttCentral.plot(column="carExtraD", linewidth=0.03, label = 'Meters', cmap="YlGn_r", scheme="quantiles", k=9, alpha=0.9, ax=mapLayer,  legend = True)
roads.plot(ax=mapLayer, color="grey", linewidth=1.5)
metro.plot(ax=mapLayer, color="orange", linewidth=2.5)
mapLayer.set_facecolor("lightskyblue")
mapTitle.suptitle('Extra travel distance of car to central Helsinki \n (difference to shortest euclidean distance)')
mapLayer.text(x=402400,y=6669000, s='^ \nN ', ha='center', fontsize=20, family='Courier new', rotation = 0)
leg = mapLayer.get_legend()
leg.set_bbox_to_anchor((1.58, 0.9))
chartBox = mapLayer.get_position()
mapLayer.set_position([chartBox.x0, chartBox.y0, chartBox.width*0.7, chartBox.height*0.7])
mapLayer.legend()
plt.savefig("carExtraDistance.png")


############################################################################################
# p2: Bokeh plots
########################################################################################


#function that gets coordinates from row containing geometry
def getPolyCoords(row, geom, coord_type):

    exterior = row[geom].exterior

    if coord_type == 'x':
        return list(exterior.coords.xy[0])
    elif coord_type == 'y':
        return list(exterior.coords.xy[1])

#Function that gets coordinates from a linestring.
#Also works on multilinestrings    
def getLineCoords(row, geom, coord_type):
    """Returns a list of coordinates ('x' or 'y') of a LineString geometry"""
    
    if(type(row[geom]) is MultiLineString):
        listofcoords = []
    
        for i in row[geom]:
            
            if coord_type == 'x':
                listofcoords = listofcoords + list(i.coords.xy[0])
            elif coord_type == 'y':
                listofcoords = listofcoords + list(i.coords.xy[1])
        return listofcoords
    
    else:
        if coord_type == 'x':
            return list(row[geom].coords.xy[0])
        elif coord_type == 'y':
            return list(row[geom].coords.xy[1])

# Classification of traveldistances
# List of values, minumum value is 0, maximum value is 16000 (16km) and step is 1000(1 kilometer).
breaks = [x for x in range(0, 16000, 1000)]

# Initialize the classifier and apply it
classifier = ps.User_Defined.make(bins=breaks)

#apply classifier to publictransport's extra distance
ptClassified = ttCentral[['ptExtraD']].apply(classifier)
ptClassified.columns = ['ptExtraDClass']

#same for car
carClassified = ttCentral[['carExtraD']].apply(classifier)
carClassified.columns = ['carExtraDClass']

#join classified series into main geoframe.
ttCentral = ttCentral.join(ptClassified)
ttCentral = ttCentral.join(carClassified)

#legend
#define the upper limit, step, and create a list ranging from bottom to top, incrementing by step
upperLimit = 16000
step = 1000
names = ["%s-%s " % (x-1000, x) for x in range(step, upperLimit, step)]
names.append("%s <" % upperLimit)

#add alphabets corresponding to classes (first class: "a 0-1000", second class: "b 1000-2000")
# this is done so that classes can be ordered ascendingly and thus appear  in correct order on legend
abc = 'abcdefghijklmnop'

for i in range(16):
    names[i] = abc[i]+" "+names[i]

#empty lists for labels
ttCentral['labelpt'] = None
ttCentral['labelCar'] = None

#add labels to their classes
for i in range(len(names)):
        ttCentral.loc[ttCentral['carExtraDClass'] == i, 'labelCar'] = names[i]
        ttCentral.loc[ttCentral['ptExtraDClass'] == i, 'labelpt'] = names[i]
        
#add "p 16000 <" to none -values 
ttCentral['labelpt'] = ttCentral['labelpt'].fillna("p %s <" % upperLimit)
ttCentral['labelCar'] = ttCentral['labelCar'].fillna("p %s <" % upperLimit)


#get x and y coords from traveldistance -frame's geometries
ttCentral['x'] = ttCentral.apply(getPolyCoords, geom='geometry', coord_type = 'x', axis=1)
ttCentral['y'] = ttCentral.apply(getPolyCoords, geom='geometry', coord_type = 'y', axis=1)

# Calculate x and y coordinates of the metro line
metro['x'] = metro.apply(getLineCoords, geom='geometry', coord_type='x', axis=1)
metro['y'] = metro.apply(getLineCoords, geom='geometry', coord_type='y', axis=1)

# Make a copy, drop the geometry column and create ColumnDataSource
metroWithoutGeom = metro.drop('geometry', axis=1).copy()
metroDatasource = ColumnDataSource(metroWithoutGeom)

#same for roads
roads['x'] = roads.apply(getLineCoords, geom='geometry', coord_type='x', axis=1)
roads['y'] = roads.apply(getLineCoords, geom='geometry', coord_type='y', axis=1)
roadsWithoutGeom = roads.drop('geometry',axis=1).copy()
roadsDatasource = ColumnDataSource(roadsWithoutGeom)

#load colormapper from imported palette (plasma256)
color_mapper = LogColorMapper(palette=palette)


#define tools to be included in the plot
TOOLS = "pan,wheel_zoom,box_zoom,reset,save"

##Plot for Car

#sort frame by car's classification label ('alphabetical order')
ttCentral = ttCentral.sort_values(by='labelCar')

#loop rows to remove alphabets
newtitles = []
for i,r in ttCentral.iterrows():
    newtitles.append(r['labelCar'][2:])

ttCentral['labelCar'] = newtitles

#reset index
ttCentral = ttCentral.reset_index(drop=True)

#define the frame as a datasource
ttWithoutGeom = ttCentral.drop('geometry', axis=1).copy()
ttSource = ColumnDataSource(ttWithoutGeom)

#make a figure 
p = figure(title="Car's travel distance difference to shortest possible to Helsinki central railway station", 
           tools=TOOLS,plot_width=650, plot_height=500, active_scroll = "wheel_zoom" )

#no grid lines
p.grid.grid_line_color = None

#load data from frame containing travel distance
traveldist = p.patches('x', 'y', source=ttSource, name='traveldist',
                            fill_color={'field': 'carExtraDClass', 'transform': color_mapper},
                            fill_alpha=1.0, line_color="black", line_width=0.05, legend="labelCar")

# Add roads on top of the same figure
roadfigure = p.multi_line('x', 'y', source=roadsDatasource, color="black", line_width=2)

# Insert a circle on top of the Central Railway Station
station_x = 385752.214
station_y =  6672143.803
circle = p.circle(x=[station_x], y=[station_y], name="point", size=10, color="Black")

# Add two separate hover tools for the data
phover = HoverTool(renderers=[circle])
phover.tooltips=[("Destination", "Railway Station")]

#Hovertools for travel distances
ghover = HoverTool(renderers=[traveldist])
ghover.tooltips=[("Minimum distance", "@minDist"),
                ("Public Transport's distance", "@pt_r_d"),
                ("Car's distance", "@car_r_d"),]

#add hovertools to plot
p.add_tools(ghover)
p.add_tools(phover)

#add clarification to bottom, telling that units are in meters
p.add_layout(Title(text="Units in meters", align="center"), "below")

# Save the figure
outfp = "carDistances.html"
save(p, outfp)


##Same for public transport

##Car

ttCentral = ttCentral.sort_values(by='labelpt')

newtitles = []
for i,r in ttCentral.iterrows():
    newtitles.append(r['labelpt'][2:])

ttCentral['labelpt'] = newtitles

ttCentral = ttCentral.reset_index(drop=True)

ttWithoutGeom = ttCentral.drop('geometry', axis=1).copy()
ttSource = ColumnDataSource(ttWithoutGeom)

p = figure(title="Public transports's travel distance's difference to shortest possible to Helsinki central railway", 
           tools=TOOLS,plot_width=650, plot_height=500, active_scroll = "wheel_zoom" )

p.grid.grid_line_color = None

traveldist = p.patches('x', 'y', source=ttSource, name='traveldist',
                            fill_color={'field': 'ptExtraDClass', 'transform': color_mapper},
                            fill_alpha=1.0, line_color="black", line_width=0.05, legend="labelpt")

# Metroline instead of roads this time
metrofigure = p.multi_line('x', 'y', source=metroDatasource, color="orange", line_width=2)

station_x = 385752.214
station_y =  6672143.803
circle = p.circle(x=[station_x], y=[station_y], name="point", size=10, color="Black")

phover = HoverTool(renderers=[circle])
phover.tooltips=[("Destination", "Railway Station")]

ghover = HoverTool(renderers=[traveldist])
ghover.tooltips=[("Minimum distance", "@minDist"),
                ("Public Transport's distance", "@pt_r_d"),
                ("Car's distance", "@car_r_d"),]

p.add_tools(ghover)
p.add_tools(phover)

p.add_layout(Title(text="Units in meters", align="center"), "below")

outfp = "ptDistances.html"
save(p, outfp)