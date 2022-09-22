# -*- coding: utf-8 -*-
# ===================== #
# Make MGCP Cell AOI v1 #
# Nat Cagle  2022-09-21 #
# ===================== #
import decimal
import arcpy as ap
from arcpy import AddMessage as write
import sys
import os
import re


#            _______________________________
#           | Populates the Metadata fields |
#           | for MGCP. Creates Subregion   |
#           | and Source polygons based on  |
#           | the original Cell polygon.    |
#           | Adds Source polygons only as  |
#           | needed.                       |
#      _    /‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾
#   __(.)< ‾
#~~~\___)~~~



# Write information for given variable
def write_info(name,var): # write_info('var_name',var)
	write("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
	write("Debug info for {0}:".format(name))
	write("   Variable Type: {0}".format(type(var)))
	write("   Assigned Value: {0}".format(var))
	write("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")


''''''''' User Parameters '''''''''
ap.env.overwriteOutput = True
# TPC name to get cell coordinates
MGCP_cell = ap.GetParameterAsText(0)
out_path = ap.GetParameterAsText(1)
shp_name = 'MGCP_' + MGCP_cell + '_AOI'
tmp_shp = "in_memory\\" + shp_name
out_shp = os.path.join(out_path, shp_name + '.shp')


''''''''' New Cell Generation '''''''''
# Creates list of letters and numbers from TPC variable. ex: E018S07 -> ['E', '018', 'S', '07']
start = re.findall('(\d+|[A-Za-z]+)', MGCP_cell)
# Error handling for user input
if len(start) != 4:
	ap.AddError("Incorrect format for TPC coordinates. Please ignore negative coordinates. Example: E018S07")
	sys.exit(0)
# Edits values for correct coordinate grid quadrant
# Sanitizes inputs for capital or lowercase
if start[0] == 'W' or start[0] == 'w':
	start[1] = abs(int(start[1])) * -1
	w_long = start[1]
	e_long = start[1] + 1
else:
	start[1] = abs(int(start[1]))
	w_long = start[1]
	e_long = start[1] + 1
if start[2] == 'S' or start[2] == 's':
	start[3] = abs(int(start[3])) * -1
	s_lat = start[3]
	n_lat = start[3] + 1
else:
	start[3] = abs(int(start[3]))
	s_lat = start[3]
	n_lat = start[3] + 1

if len(str(int(start[1]))) == 1:
	spacing = 1
if len(str(int(start[1]))) == 2:
	spacing = 2
if len(str(int(start[1]))) == 3:
	spacing = 3


# Creates [x,y] point variables
start_one = str(start[1]) + '.000000000000'
start_three = str(start[3]) + '.000000000000'

corner = [float(start_one), float(start_three)]
write('\n\nParsing user input for Southwest corner.')
write(MGCP_cell + ' ---> ' + str(corner))
if corner[0] == float(start_one):
	write('Coordinates for Cell generation acquired.')
else:
	write('TPC name format invalid. Please try again.')
	sys.exit(0)
# wn = [ws[0], ws[1]+1]
# en = [ws[0]+1, ws[1]+1]
# es = [ws[0]+1, ws[1]]
# coords = [ws, wn, en, es, ws]
# corner = [19.000000000000, -8.000000000000]
ws = ap.Point(corner[0], corner[1])
wn = ap.Point(corner[0], corner[1]+1)
en = ap.Point(corner[0]+1, corner[1]+1)
es = ap.Point(corner[0]+1, corner[1])
coords = [ws, wn, en, es, ws]


write('Constructing new cell polygons based on provided coordinates:\n')
write(str([corner[0], corner[1]+1]) + '_____' + str([corner[0]+1, corner[1]+1]))
if spacing == 1:
	write('    |              | \n    |              | \n    |              | \n    |              | \n    |              | \n    |              | ')
if spacing == 2:
	write('     |               | \n     |               | \n     |               | \n     |               | \n     |               | \n     |               | ')
if spacing == 3:
	write('      |                | \n      |                | \n      |                | \n      |                | \n      |                | \n      |                | ')
write(str(corner) + '_____' + str([corner[0]+1, corner[1]]))


# Create a feature class with a spatial reference of GCS WGS 1984
ap.CreateFeatureclass_management('in_memory', shp_name, 'POLYGON', spatial_reference=4326)

with ap.da.InsertCursor(tmp_shp, ['SHAPE@']) as icursor:
	icursor.insertRow([ap.Polygon(ap.Array(coords), ap.SpatialReference(4326))])

arcpy.FeatureClassToShapefile_conversion(tmp_shp, out_path)


write('\nConfirmation of Cell vertices at 1 degree intervals:')
with ap.da.SearchCursor(out_shp, ['SHAPE@']) as icursor:
	for row in icursor:
		for part in row[0]:
			corner = 0
			for pnt in part:
				if pnt:
					# Print x,y coordinates of current point
					write("{}, {}".format(pnt.X, pnt.Y))
				else:
					# If pnt is None, this represents an interior ring
					write("Interior Ring:")

write("\n")
