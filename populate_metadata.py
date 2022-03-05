# ========================= #
# Populate MGCP Metadata v6 #
# Nat Cagle 2022-02-15      #
# ========================= #
import decimal
import arcpy
import sys
import os
from datetime import datetime
from arcpy import AddMessage as write
import re
import uuid

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


''''''''' Dictionary Definitions '''''''''

# If changes are made to the default values for metadata, update them here
cell_default = {
'CCMNT' : 'This cell is UNCLASSIFIED but not approved for public release. Data and derived products may be used for government purposes. NGA name and seal protected by 10 U.S.C. 425.',
'CCRSID' : 'WGS 84 2D-Geographic East-North',
'CDCHAR' : 'utf8',
'CDESCR' : 'Multinational Geospatial Co-production Program (MGCP) dataset covering the 1x1 degree cell between <W> and <E> longitudes and <S> and <N> latitudes',
'CDLANG' : 'English',
'CFFMTN' : 'SHAPEFILE',
'CFFMTS' : 'ESRI Shapefile Technical Description - An ESRI White Paper',
'CFFMTV' : 'July 1998',
'CLSTAT' : '50k density feature extraction from monoscopic imagery using MGCP TRD v4.5.1. Ancillary source data used as needed to supplement the features not seen on imagery.',
'CMCHAR' : 'utf8',
'CMLANG' : 'English',
'CMPOCA' : 'NGA',
'CMPOCC' : 'USA',
'CMSEC' : 'unclassified',
'CMSHND' : 'Not for Public Release',
'CMSPLN' : 'Cell',
'CMSTDN' : 'ISO 19115',
'CMSTDV' : '2003',
'CORIGA' : 'NGA',
'CORIGC' : 'USA',
'CSECCL' : 'unclassified',
'CSERES' : 'MGCP',
'CSHNDI' : 'Not for Public Release',
'CURI' : 'http://www.mgcp.ws'
}

subregion_default = {
'SACEMT' : '15', # This is a Long int in the MD_Accuracy_Eval domain representing 'Product specification'
'SACEVL' : '25',
'SALEMT' : '998', # Long int for 'Not Applicable'. Could not clarify origin domain
'SALEVL' : '-32765',
'SDESCR' : 'Single subregion',
'SFCATR' : 'MGCP Feature Catalogue 4.5.1',
'SFCDTD' : 'TRD4.5.1 2019-07-05',
'SFCINC' : 'FALSE',
'SLSTAT' : 'Initial collection using imagery.',
'SMCHAR' : 'utf8',
'SMLANG' : 'English',
'SMSEC' : 'unclassified',
'SMSHND' : 'Not for Public Release',
'SMSPLN' : 'Subregion',
'SMSTDN' : 'ISO 19115',
'SMSTDV' : '2003',
'SORIGA' : 'NGA',
'SORIGC' : 'USA',
'SSCALE' : '50000',
'SSVCID' : 'noElevations',
'SSVCTY' : '3', # This is a long int in the MD_Vertical_Source domain representing "No Elevation"
'SSVRTI' : 'No Elevations',
'STIERN' : 'Not for Public Release',
'STYPEU' : '',
'SUBRID' : '01',
'SUFONT' : 'Arial Unicode MS',
'SVNAME' : 'GAIT',
'SVSPCD' : 'TRD4.5.1 2019-07-05T00:00:00Z',
'SVSPCN' : 'MGCP Technical Reference Documentation (TRD4v4.5.1)',
'SVSTMT' : 'geometry conformant to specification',
'SVVALD' : 'TRUE',
'SVVERS' : '26'
}

new_imagery = {
'SSRCID' : 'Newest Very High Resolution Commercial Monoscopic Imagery',
'SSRCSC' : '5000',
'SSRCTY' : '110', # More Long ints that masquerade as text and are difficult to find values for. This is the MD_Source domain for 'Very High Resolution Commercial Monoscopic Imagery'
'SUBRID' : '01'
}

old_imagery = {
'SSRCID' : 'Oldest Very High Resolution Commercial Monoscopic Imagery',
'SSRCSC' : '5000',
'SSRCTY' : '110', # Long int for the MD_Source domain. See line 73. 'Very High Resolution Commercial Monoscopic Imagery'
'SUBRID' : '01'
}

geonames_d = {
'SSRCID' : 'GeoNames',
'SSRCSC' : '50000',
'SSRCTY' : '25', # Long int for the MD_Source domain. See line 73. 'GeoNames'
'SUBRID' : '01'
}

dvof_d = {
'SSRCID' : 'DVOF',
'SSRCSC' : '50000',
'SSRCTY' : '21', # Long int for the MD_Source domain. See line 73. 'DVOF'
'SUBRID' : '01'
}


''''''''' User Parameters '''''''''

# MGCP_Metadata dataset
MGCP = arcpy.GetParameterAsText(0)
arcpy.env.workspace = MGCP
arcpy.env.overwriteOutput = True
# Check box to make a new cell polygon from given coordinates.
new_cell = arcpy.GetParameter(1)
# Imagery Footprint
img_foot = arcpy.GetParameterAsText(2)
# TPC name to get cell coordinates
TPC = arcpy.GetParameterAsText(3)
# Checkbox "Leave attribute field blank for Edition 1. Populate with 'Complete Update' for Edition 2, 3, etc."
update_edition = arcpy.GetParameter(4)
# Dates
local_date = arcpy.GetParameterAsText(5) # Date TPC was pulled local for finishing YYYY-MM-DD (for latest extraction date) (apply to DVOF source per Candi)
gait_date = arcpy.GetParameterAsText(6) # Delivery date (for date of final GAIT run)
# DVOF
dvof_check = arcpy.GetParameter(7) # Did you use DVOF checkbox
# Geonames date: Database most recent update on: https://geonames.nga.mil/gns/html
geo_check = arcpy.GetParameter(8) # Did you use geonames checkbox
shp_check = arcpy.GetParameter(9) # Do you only have access to a Geonames shapefile in stead of a FC for some incredibly inconvenient reason?
geo_file = arcpy.GetParameterAsText(10)


''''''''' Feature Class List '''''''''

# List and sort feature classes and give them their own variable for the later update cursors
featureclass = arcpy.ListFeatureClasses()
featureclass.sort()
fc_cell = featureclass[0]
fc_subregion = featureclass[2]
fc_source = featureclass[1]
# Sets path for the XML metadata export as the folder containing the GDB and sets the location of the cell feature class
export_path = os.path.dirname(os.path.dirname(MGCP))
cell_path = os.path.join(MGCP, fc_cell)


''''''''' User Error Handling '''''''''

if len(featureclass) != 3:
    write("There should be 3 feature classes in the MGCP_Metadata dataset: Cell, Subregion, and Source.\nPlease repair the dataset and try again.")
    sys.exit(0)
elif len(featureclass) == 3:
    write("Populating metadata feature classes " + str(fc_cell) + ", " + str(fc_subregion) + ", and " + str(fc_source) + " with default values.\nIf you wish to update the default values, edit the default dictionaries in the script.")
# Checks for proper format of user input dates
try:
	temp1 = datetime.strptime(local_date, '%Y-%m-%d')
	temp2 = datetime.strptime(gait_date, '%Y-%m-%d')
except ValueError:
        raise ValueError("Incorrect date format, should be YYYY-MM-DD")


''''''''' Dates '''''''''
ex_year = datetime.strptime(gait_date, '%Y-%m-%d')
curr_year = ex_year.strftime("%Y")
write('Year of data production: {0}'.format(curr_year))
img_dates = []
# Searches through Imagery Footprint dates and creates a list in the YYYY-MM-DD format
with arcpy.da.SearchCursor(img_foot, 'Acquisitio') as img:
	for row in img:
		date = row[0].strftime("%Y-%m-%d")
		img_dates.append(date)
# Get newest and oldest imagery footprint dates
img_date_new = max(img_dates)
img_date_old = min(img_dates)

if geo_check:
	geo_dates = []
	# Searches through the Geonames file modify dates and creates a list in the YYYY-MM-DD format
	geo_field = 'MODIFY_DATE'
	if shp_check:
		geo_field = 'MODIFY_DAT'
	with arcpy.da.SearchCursor(geo_file, geo_field) as geo:
		if shp_check:
			write('Searching Geonames shapefile for \'MODIFY_DAT\' field.')
			for row in geo: # The Geonames shapefile 'MODIFY_DAT' field is already a datetime object and cannot be parsed, only formatted.
				date = row[0].strftime("%Y-%m-%d")
				geo_dates.append(date)
		else:
			write('Searching Geonames feature class for \'MODIFY_DATE\' field.')
			for row in geo: # The Geonames FC 'MODIFY_DATE' field needs to be parsed as a datetime object and then formatted
				feat_date = datetime.strptime(row[0], "%m/%d/%Y")
				date = feat_date.strftime("%Y-%m-%d")
				geo_dates.append(date)
	# Find newest Geonames modify dates
	geo_date_new = max(geo_dates)


''''''''' New Cell Generation '''''''''

# Generates a new cell polygon if box is checked
if new_cell == True:
	# Creates list of letters and numbers from TPC variable. ex: E018S07 -> [E, 018, S, 07]
	start = re.findall('(\d+|[A-Za-z]+)', TPC)
	# Error handling for user input
	if len(start) != 4:
	    write("Incorrect format for TPC coordinates. Please ignore negative coordinates. Example: E018S07")
	    sys.exit(0)

	# Edits values for correct coordinate grid quadrant
	if start[0] == 'W' or start[0] == 'w': # Sanitizes inputs for capital or lowercase
		start[1] = abs(int(start[1])) * -1
	if start[2] == 'S' or start[2] == 's':
		start[3] = abs(int(start[3])) * -1

	if len(str(int(start[1]))) == 1:
		spacing = 1
	if len(str(int(start[1]))) == 2:
		spacing = 2
	if len(str(int(start[1]))) == 3:
		spacing = 3

	# Creates [x,y] point variables
	start[1] = str(start[1]) + '.000000000000'
	start[3] = str(start[3]) + '.000000000000'

	ws = [float(start[1]), float(start[3])]
	write('Parsing user input for Southwest corner.')
	write(TPC + ' ---> ' + str(ws))
	if ws[0] == float(start[1]):
		write('Coordinates for Cell generation acquired.')
	else:
		write('TPC name format invalid. Please try again.')
		pause()
	wn = [ws[0], ws[1]+1]
	en = [ws[0]+1, ws[1]+1]
	es = [ws[0]+1, ws[1]]
	coords = [ws, wn, en, es, ws]
	write('Constructing new cell polygons based on provided coordinates:\n')

	write(str(wn) + '_____' + str(en))
	if spacing == 1:
		write('    |              | \n    |              | \n    |              | \n    |              | \n    |              | \n    |              | ')
	if spacing == 2:
		write('     |               | \n     |               | \n     |               | \n     |               | \n     |               | \n     |               | ')
	if spacing == 3:
		write('      |                | \n      |                | \n      |                | \n      |                | \n      |                | \n      |                | ')
	write(str(ws) + '_____' + str(es))


	# Create a feature class with a spatial reference of GCS WGS 1984
	result = arcpy.management.CreateFeatureclass(MGCP, "bs_line_skware", "POLYLINE", spatial_reference=4326)
	feature_class = result[0]

	# Write feature to new feature class
	with arcpy.da.InsertCursor(feature_class, ['SHAPE@']) as icursor:
	    icursor.insertRow([coords])

	# Use the FeatureToPolygon function to form new areas
	arcpy.FeatureToPolygon_management('bs_line_skware', 'bs_skware')
	arcpy.Append_management('bs_skware', fc_cell, 'NO_TEST','First','')
	arcpy.Delete_management('bs_line_skware')
	arcpy.Delete_management('bs_skware')


	write('\nConfirmation of Cell vertices at 1 degree intervals:')
	with arcpy.da.SearchCursor(fc_cell, ["SHAPE@"]) as ucursor:
		for row in ucursor:
		    for part in row[0]:
				corner = 0
				for pnt in part:
				    if pnt:
				        # Print x,y coordinates of current point
				        write("{}, {}".format(pnt.X, pnt.Y))
				    else:
				        # If pnt is None, this represents an interior ring
				        write("Interior Ring:")


''''''''' Dictionary Updates '''''''''

# Dynamic dictionary values updated per run with user values
cell_default['CCDATE'] = local_date
cell_default['CEDDAT'] = local_date
cell_default['CMDATE'] = local_date
cell_default['CNEWSD'] = img_date_new
cell_default['COLDSD'] = img_date_old
cell_default['CELLID'] = TPC
cell_default['CCPYRT'] = 'Copyright {0} by the National Geospatial-Intelligence Agency, U.S. Government. No domestic copyright claimed under Title 17 U.S.C. All rights reserved.'.format(curr_year)
subregion_default['SCDATE'] = local_date
subregion_default['SEDDAT'] = local_date
subregion_default['SMDATE'] = local_date
subregion_default['SSVCDT'] = local_date
subregion_default['SVDATE'] = gait_date
subregion_default['SCPYRT'] ='Copyright {0} by the National Geospatial-Intelligence Agency, U.S. Government. No domestic copyright claimed under Title 17 U.S.C. All rights reserved.'.format(curr_year)
# Checkbox for update edition
if not update_edition:
	subregion_default['STYPEU'] = 'Complete Update'
new_imagery['SSRCDT'] = img_date_new
old_imagery['SSRCDT'] = img_date_old
# If geonames or DVOF were used in data collection
if geo_check:
	geonames_d['SSRCDT'] = geo_date_new
	subregion_default['SLSTAT'] = 'Initial collection using imagery and Geonames.'
if dvof_check:
	dvof_d['SSRCDT'] = gait_date
	subregion_default['SLSTAT'] = 'Initial collection using imagery and DVOF.'
if geo_check and dvof_check:
	subregion_default['SLSTAT'] = 'Initial collection using imagery, DVOF, and Geonames.'



''''''''' Populate Secondary Metadata Tiles '''''''''

### Cell ###
#for loop to append dictionary keys and values to blank lists if they don't match with current logic
# Creates list of dictionary keys
cell_fields = cell_default.keys()
# If a cell polygon already exists and just needs to be updated (from Create New Cell checkbox)
if new_cell == False:
	# Update cursor for cell feature class with the dictionary keys as the fields
	with arcpy.da.UpdateCursor(fc_cell, cell_fields) as ucursor:
	    for row in ucursor:
			count = 0
			# For each field set the value equal to the value in the dictionary for the field key
			for field in cell_fields:
				row[count] = cell_default[field]
	        	count += 1
			ucursor.updateRow(row)
	# Populates the gfid field using the uuid python function
	with arcpy.da.UpdateCursor(fc_cell, 'gfid') as ucursor:
		for row in ucursor:
			row[0] =str(uuid.uuid4())

# With the way arcpy handles inserts and updates, it is unable to just assign the values
# to the fields while also creating the cell shape. There for the generated cell acts as a temporary Polygon
# This inserts a new feature with the correct field values
with arcpy.da.InsertCursor(fc_cell, cell_fields) as icursor:
	values = [cell_default[x] for x in cell_fields]
	icursor.insertRow(values)
# Next it applies the @SHAPE token from the temporary polygon
with arcpy.da.UpdateCursor(fc_cell, ['OID@', 'SHAPE@', 'gfid']) as ucursor:
	first = 0
	# Determines which feature is the temp and which has the fields populated
	for row in ucursor:
		# Sets a variable with the @SHAPE token from the temp polygon
		if first == 0:
			temp_poly = row[1]
		# Sets the shape of any other features to the @SHAPE of the temp polygon
		if first != 0:
			row[1] = temp_poly
		first = 1
		# Populates the gfid field using the uuid python function
		row[2] = str(uuid.uuid4())
		ucursor.updateRow(row)
# Deletes the temp polygon after it's shape has been used
with arcpy.da.UpdateCursor(fc_cell, 'OID@') as ucursor:
	top_row = 0
	for row in ucursor:
		if top_row == 0:
			ucursor.deleteRow()
		top_row = 1

### Subregion ###
# Creates list of dictionary keys
sub_fields = subregion_default.keys()
# Inserts a new feature with the values in the dictionary for the field keys
with arcpy.da.InsertCursor(fc_subregion, sub_fields) as icursor:
	# Creates a list of all the values in the dictionary based on their associated field keys from the list of dictionary keys
	values = [subregion_default[x] for x in sub_fields]
	icursor.insertRow(values)
# Updates the shape of the subregion polygon with the shape of the previous cell polygon
with arcpy.da.UpdateCursor(fc_subregion, ['SHAPE@', 'gfid']) as ucursor:
	for row in ucursor:
		# Populates the gfid field using the uuid python function
		row[1] = str(uuid.uuid4())
		with arcpy.da.SearchCursor(fc_cell, 'SHAPE@') as scursor:
			for fc in scursor:
				row[0] = fc[0]
		ucursor.updateRow(row)

### Source ###
# Creates list of dictionary keys
src_fields = new_imagery.keys()
# Inserts new features for all specified sources with the values in the dictionary for the field keys
with arcpy.da.InsertCursor(fc_source, src_fields) as icursor:
	# Creates lists of all the values in the dictionaries based on their associated field keys from the list of dictionary keys (the source feature class has the same keys regardless of source type)
	img_new_vals = [new_imagery[x] for x in src_fields]
	img_old_vals = [old_imagery[x] for x in src_fields]
	# Only generates features if they are specified as sources from user input
	if geo_check == True:
		geo_vals = [geonames_d[x] for x in src_fields]
	if dvof_check == True:
		dvof_vals = [dvof_d[x] for x in src_fields]
	# Inserts the features based on the source values defined above
	icursor.insertRow(img_new_vals)
	icursor.insertRow(img_old_vals)
	# Only generates features if they are specified as sources from user input
	if geo_check == True:
		icursor.insertRow(geo_vals)
	if dvof_check == True:
		icursor.insertRow(dvof_vals)
# Updates the shape of the subregion polygon with the shape of the previous cell polygon
with arcpy.da.UpdateCursor(fc_source, ['SHAPE@', 'gfid']) as ucursor:
	for row in ucursor:
		# Populates the gfid field using the uuid python function
		row[1] = str(uuid.uuid4())
		with arcpy.da.SearchCursor(fc_cell, 'SHAPE@') as scursor:
			for fc in scursor:
				row[0] = fc[0]
		ucursor.updateRow(row)


''''''''' Export XML Metadata '''''''''

try:
	# Checks out Defense Mapping extension
	arcpy.CheckOutExtension("defense")
	write("Exporting Cell metadata to xml file. Path is located here:")
	write(export_path)
	# Runs Export MGCP XML Metadata tool from Defense Mapping using the cell path and the export path
	arcpy.ExportMetadata_defense(cell_path, export_path)
	arcpy.CheckInExtension("defense")
	write("==== Metadata construction is complete! ====")
except:
	# Error handling. The Metadata dataset has to be in the GDB with a local copy of the data
    write("MGCP dataset must be in the GDB along with the MGCP_Metadata dataset.")


###### Making a skware in ArcMap trash heap ######

	# # Create arcpy array of point geometries and convert that to polygon object
	# array = arcpy.Array([arcpy.Point(ws[0],ws[1]), arcpy.Point(wn[0],wn[1]), arcpy.Point(en[0],en[1]), arcpy.Point(es[0],es[1])])
	# poly = arcpy.Polygon(array)
	# write(poly.WKT)
	#
	#
	# ws_p = arcpy.Point(ws[0],ws[1])
	# wn_p = arcpy.Point(wn[0],wn[1])
	# en_p = arcpy.Point(en[0],en[1])
	# es_p = arcpy.Point(es[0],es[1])
	#
	# arrlist = [ws_p, wn_p, en_p, es_p]
	# #write(arrlist[0].X)
	# corner_array = arcpy.Array(arrlist)
	# #write(corner_array)
	# xxx = arcpy.Geometry('polyline', corner_array)
	# write(xxx.WKT)
	# with arcpy.InsertCursor(fc_cell, 'SHAPE@') as icursor:
	# 	icursor.insertRow(arcpy.Polygon(xxx.getPart()))
	# write(yyy.WKT)

	# write(type(start[1]))
	# write(start[1] + "," + start[3])
	# x = decimal.Decimal(start[1])
	# y = decimal.Decimal(start[3])
	# write(type(x))
	# write(x)
	# write(y)

# >>> import arcpy
# >>> pl = arcpy.FromWKT('LINESTRING(0 0, 10 0, 10 10, 0 10, 0 0)', arcpy.SpatialReference(3857))
# >>> pl
# <Polyline object at 0x19159987dd8[0x19159c5a210]>
# >>>
# >>> pg = arcpy.Polygon(pl.getPart(), pl.spatialReference)
# >>> pg<Polygon object at 0x19162933908[0x19159ef0aa8]
# >>>>

	# ws = [float(start[1]), float(start[3])]
	# ws2 = [x,y]
	# write(ws)
	# write(ws2)
	# p = arcpy.Point(115.0000000000000001, 06.0000000000000001)
	# write(p.X)
	# write(p.Y)
	# write("p.X = integer 115.0001")
	# p.X = 115.0001
	# write(p.X)
	# write("p.X = string '115.0001'")
	# p.X = '115.0001'
	# write(p.X)
	# write("p.X = integer 115.000000000001")
	# p.X = 115.000000000001
	# write(p.X)
	# write("p.X = string '115.000000000001'")
	# p.X = '115.000000000001'
	# write(p.X)
	# write("p.X = int 4.00000000000001")
	# p.X = 4.00000000000001
	# write(p.X)
	# pause()\

	# write('inserting row')
	# # Inserts generated polygon into cell feature as blank @SHAPE template
	# with arcpy.da.InsertCursor(fc_cell, 'SHAPE@') as icursor:
	# 	icursor.insertRow([poly])
	#
	# workspace = os.path.dirname(MGCP)
	# edit = arcpy.da.Editor(workspace)
	# # Edit session is started without an undo/redo stack for versioned data
	# # (for second argument, use False for unversioned data)
	# edit.startEditing(False, True)
	# arcpy.GetMessages()
	# edit.startOperation()
	# write('update cursor')
	# tcursor = arcpy.da.UpdateCursor(fc_cell, ["SHAPE@"])
	# for row in tcursor:
	# 	for part in row[0]:
	# 		corner = 0
	# 		for pnt in part:
	# 			if pnt:
	# 				# Print x,y coordinates of current point
	# 				#
	# 				write('broken coords:')
	# 				write("{}, {}".format(pnt.X, pnt.Y))
	# 				write('^^^^')
	# 				if corner == 0:
	# 					write('original ws[0]')
	# 					write(ws[0])
	# 					pnt.X = ws[0]
	# 					pnt.Y = ws[1]
	# 				if corner == 1:
	# 					pnt.X = wn[0]
	# 					pnt.Y = wn[1]
	# 				if corner == 2:
	# 					pnt.X = en[0]
	# 					pnt.Y = en[1]
	# 				if corner == 3:
	# 					pnt.X = es[0]
	# 					pnt.Y = es[1]
	# 				if corner == 4:
	# 					pnt.X = ws[0]
	# 					pnt.Y = ws[1]
	# 				corner += 1
	# 				write('new coords:')
	# 				write("{}, {}".format(pnt.X, pnt.Y))
	# 				write('^^^^')
	# tcursor.updateRow()
	# edit.stopOperation()
	# edit.stopEditing(True)
	# arcpy.GetMessages()

	# with arcpy.da.UpdateCursor(fc_cell, ["SHAPE@"]) as ucursor:
	# 	for row in ucursor:
	# 		for part in row[0]:
	# 			corner = 0
	# 			for pnt in part:
	# 				if pnt:
	# 					# Print x,y coordinates of current point
	# 					#
	# 					write('broken coords:')
	# 					write("{}, {}".format(pnt.X, pnt.Y))
	# 					write('^^^^')
	# 					if corner == 0:
	# 						write('original ws[0]')
	# 						write(ws[0])
	# 						pnt.X = ws[0]
	# 						pnt.Y = ws[1]
	# 					if corner == 1:
	# 						pnt.X = wn[0]
	# 						pnt.Y = wn[1]
	# 					if corner == 2:
	# 						pnt.X = en[0]
	# 						pnt.Y = en[1]
	# 					if corner == 3:
	# 						pnt.X = es[0]
	# 						pnt.Y = es[1]
	# 					if corner == 4:
	# 						pnt.X = ws[0]
	# 						pnt.Y = ws[1]
	# 					corner += 1
	# 					write('new coords:')
	# 					write("{}, {}".format(pnt.X, pnt.Y))
	# 					write('^^^^')
	# 	ucursor.updateRow(row)
