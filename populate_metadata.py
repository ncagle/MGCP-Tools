# -*- coding: utf-8 -*-
# ========================== #
# Populate MGCP Metadata v10 #
#    Nat Cagle 2022-08-10    #
# ========================== #
import decimal
import arcpy as ap
import sys
import os
from datetime import datetime as dt
from arcpy import AddMessage as write
import re
import uuid
import traceback

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
# They failed to mention in the documentation that 1x1 needed to have the degree symbols
# Also, <W>, <E>, <S>, <N> need to be populated with values
cell_default = {
'CCMNT' : 'This cell is UNCLASSIFIED but not approved for public release. Data and derived products may be used for government purposes. NGA name and seal protected by 10 U.S.C. 425.',
'CCRSID' : 'WGS 84 2D-Geographic East-North',
'CDCHAR' : 'utf8',
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
'CURI' : 'https://www.mgcp.ws'
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
'SVVERS' : '27'
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
'SSRCTY' : '110', # Long int for the MD_Source domain. See MGCP TRD Domain Coded Values. 'Very High Resolution Commercial Monoscopic Imagery'
'SUBRID' : '01'
}

new_geonames_d = {
'SSRCID' : 'GeoNames',
'SSRCSC' : '50000',
'SSRCTY' : '25', # Long int for the MD_Source domain. See MGCP TRD Domain Coded Values. 'GeoNames'
'SUBRID' : '01'
}

# Not using this cz apparently having Oldest/Newest Geonames is "illegal" for GAIT validation. But not for DVOF...
old_geonames_d = {
'SSRCID' : 'Oldest GeoNames',
'SSRCSC' : '50000',
'SSRCTY' : '25', # Long int for the MD_Source domain. See MGCP TRD Domain Coded Values. 'GeoNames'
'SUBRID' : '01'
}

new_dvof_d = {
'SSRCID' : 'Newest DVOF',
'SSRCSC' : '50000',
'SSRCTY' : '21', # Long int for the MD_Source domain. See MGCP TRD Domain Coded Values. 'DVOF'
'SUBRID' : '01'
}

old_dvof_d = {
'SSRCID' : 'Oldest DVOF',
'SSRCSC' : '50000',
'SSRCTY' : '21', # Long int for the MD_Source domain. See MGCP TRD Domain Coded Values. 'DVOF'
'SUBRID' : '01'
}

aafif_d = {
'SSRCID' : 'AAFIF',
'SSRCSC' : '50000',
'SSRCTY' : '2', # Long int for the MD_Source domain. See MGCP TRD Domain Coded Values. 'AAFIF'
'SUBRID' : '01'
}



# Write information for given variable
def write_info(name,var): # write_info('var_name',var)
	write("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
	write("Debug info for {0}:".format(name))
	write("   Variable Type: {0}".format(type(var)))
	write("   Assigned Value: {0}".format(var))
	write("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")



''''''''' User Parameters '''''''''

# MGCP_Metadata dataset
MGCP = ap.GetParameterAsText(0)
ap.env.workspace = MGCP
ap.env.overwriteOutput = True
# Check box to make a new cell polygon from given coordinates.
new_cell = ap.GetParameter(1)
# Imagery Footprint
img_foot = ap.GetParameterAsText(2)
# TPC name to get cell coordinates
TPC = ap.GetParameterAsText(3)
# Checkbox "Leave attribute field blank for Edition 1. Populate with 'Complete Update' for Edition 2, 3, etc."
update_edition = ap.GetParameter(4)
# Dates
local_date = ap.GetParameterAsText(5) # Date TPC was pulled local for finishing YYYY-MM-DD (for latest extraction date)
gait_date = ap.GetParameterAsText(6) # Delivery date (for date of final GAIT run)
# AAFIF
aafif_check = ap.GetParameter(7) # There is absolutely too much miscellaneous nonsense with this junk. Just find the date yourself and input it.
aafif_date = ap.GetParameterAsText(8) # YYYY-MM-DD
# DVOF
dvof_check = ap.GetParameter(9) # Did you use DVOF checkbox
dvof_shp_check = ap.GetParameter(10) # Why can nothing ever be consistent. This is for if you only have a DVOF source shapefile (point only)
dvof_file = ap.GetParameterAsText(11)
# Geonames date: Database most recent update on: https://geonames.nga.mil/gns/html
geo_check = ap.GetParameter(12) # Did you use geonames checkbox
geo_shp_check = ap.GetParameter(13) # Do you only have access to a Geonames shapefile in stead of a FC for some incredibly inconvenient reason?
geo_file = ap.GetParameterAsText(14)



''''''''' Feature Class List '''''''''

# List and sort feature classes and give them their own variable for the later update cursors
featureclass = ap.ListFeatureClasses()
featureclass.sort()
fc_cell = featureclass[0]
fc_subregion = featureclass[2]
fc_source = featureclass[1]
# Sets path for the XML metadata export as the folder containing the GDB and sets the location of the cell feature class
export_path = os.path.dirname(os.path.dirname(MGCP))
cell_path = os.path.join(MGCP, fc_cell)



''''''''' User Error Handling '''''''''

if len(featureclass) != 3:
	ap.AddError("There should be 3 feature classes in the MGCP_Metadata dataset: Cell, Subregion, and Source.\nPlease repair the dataset and try again.")
	sys.exit(0)
elif len(featureclass) == 3:
	write("\nPopulating metadata feature classes " + str(fc_cell) + ", " + str(fc_subregion) + ", and " + str(fc_source) + " with default values.\nIf you wish to update the default values, edit the default dictionaries in the script.\n")
# Checks for proper format of user input dates
try:
	write("Validating input date fields...")
	temp1 = dt.strptime(local_date, '%Y-%m-%d')
	temp2 = dt.strptime(gait_date, '%Y-%m-%d')
	if aafif_check:
		temp3 = dt.strptime(aafif_date, '%Y-%m-%d')
except ValueError:
		raise ValueError("Incorrect date format, should be YYYY-MM-DD")



''''''''' Dates ''''''''' # SANITIZE ALL THEIR STUPID INCONSISTENT INPUTS
ex_year = dt.strptime(gait_date, '%Y-%m-%d')
curr_year = ex_year.strftime("%Y")
write('Year of data production: {0}'.format(curr_year))
img_dates = []
# Searches through Imagery Footprint dates and creates a list in the YYYY-MM-DD format
with ap.da.SearchCursor(img_foot, 'Acquisitio') as img:
	for row in img:
		date = row[0].strftime("%Y-%m-%d")
		img_dates.append(date)
# Get newest and oldest imagery footprint dates
img_date_new = max(img_dates)
img_date_old = min(img_dates)
write("\nNewest acquisition date from imagery footprint: {0}".format(img_date_new))
write("Oldest acquisition date from imagery footprint: {0}".format(img_date_old))

if dvof_check:
	dvof_dates = []
	# Searches through the DVOF file modify dates and creates a list in the YYYY-MM-DD format
	dvof_field = 'SOURCEDT'
	with ap.da.SearchCursor(dvof_file, dvof_field) as dvof:
		if dvof_shp_check:
			write('\nSearching DVOF shapefile for \'SOURCEDT\' field.')
			for row in dvof: # The DVOF shapefile 'SOURCEDT' field is an unformatted disgrace. ex: 20220310 (I'm just assuming it's YYYY-MM-DD)
				date_field = str(row[0])
				feat_date = dt.strptime(date_field, "%Y%m%d")
				date = feat_date.strftime("%Y-%m-%d")
				dvof_dates.append(date)
		else:
			write('\nSearching DVOF feature class for \'SOURCEDT\' field.')
			for row in dvof: # The DVOF feature class 'SOURCEDT' field is an unformatted disgrace. ex: 20220310 (I'm just assuming it's YYYY-MM-DD)
				date_field = str(row[0])
				feat_date = dt.strptime(date_field, "%Y%m%d")
				date = feat_date.strftime("%Y-%m-%d")
				dvof_dates.append(date)
	# Find newest and oldest DVOF modify dates
	dvof_date_new = max(dvof_dates)
	dvof_date_old = min(dvof_dates)
	write("Latest DVOF source date: {0}".format(dvof_date_new))
	write("Earliest DVOF source date: {0}".format(dvof_date_old))

if geo_check:
	write("\nImporting Geonames Source data...")
	geo_dates = []
	# Searches through the Geonames file modify dates and creates a list in the YYYY-MM-DD format
	geo_field_names = [f.name for f in ap.ListFields(geo_file)]

	if 'mod_dt_nm' in geo_field_names:
		geo_field = 'mod_dt_nm'
		with ap.da.SearchCursor(geo_file, geo_field) as scursor:
			write("Searching Geonames feature class for date field.\nName: 'mod_dt_nm'\nAlias: 'Last Edited Date (name)'")
			for srow in scursor:
				date_field = srow[0]
				if type(date_field) == dt:
					date = date_field.strftime("%Y-%m-%d")
					geo_dates.append(date)
				else:
					feat_date = dt.strptime(date_field, "%m/%d/%Y")
					date = feat_date.strftime("%Y-%m-%d")
					geo_dates.append(date)

	elif 'MODIFY_DATE' in geo_field_names:
		geo_field = 'MODIFY_DATE'
		with ap.da.SearchCursor(geo_file, geo_field) as geo:
			write('Searching Geonames feature class for \'MODIFY_DATE\' field.')
			for row in geo:
				date_field = str(row[0])
				feat_date = dt.strptime(date_field, "%m/%d/%Y")
				date = feat_date.strftime("%Y-%m-%d")
				geo_dates.append(date)

	elif 'MODIFY_DAT' in geo_field_names:
		if not geo_shp_check:
			ap.AddError("**********************************************************")
			ap.AddError("There was an issue with the Geonames Source feature class. Attempting to correct for broken field names...\n")
			ap.AddError("It seems someone tried to just load a Geonames shapefile into a GDB instead of properly downloading the data from the NGA GEOnet Name Service. :]\nInconsistency in database standards is the leading cause of early heart failure in developers.\nExcel is not a database, and a shapefile is not a feature class. Do better.")
			ap.AddError("**********************************************************")
		geo_field = 'MODIFY_DAT'
		with ap.da.SearchCursor(geo_file, geo_field) as geo:
				write('Searching Geonames shapefile for \'MODIFY_DAT\' field.')
				write("")
				for row in geo:
					date_field = row[0]
					if type(date_field) == dt:
						date = date_field.strftime("%Y-%m-%d")
						geo_dates.append(date)
						continue
					else:
						try:
							feat_date = dt.strptime(date_field, "%m/%d/%Y")
							date = feat_date.strftime("%Y-%m-%d")
							geo_dates.append(date)
						except:
							geo_dates.append(date_field)

	geo_date_new = max(geo_dates)
	#geo_date_old = min(geo_dates)
	write("Latest NGA GEOnet Names Server (GNS) database update date in Geonames source: {0}".format(geo_date_new))
	#write("Earliest NGA GEOnet Names Server (GNS) database update date in Geonames source: {0}".format(geo_date_old))



''''''''' New Cell Generation '''''''''

# Creates list of letters and numbers from TPC variable. ex: E018S07 -> ['E', '018', 'S', '07']
start = re.findall('(\d+|[A-Za-z]+)', TPC)
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

# Generates a new cell polygon if box is checked
if new_cell:
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
	write(TPC + ' ---> ' + str(corner))
	if corner[0] == float(start_one):
		write('Coordinates for Cell generation acquired.')
	else:
		write('TPC name format invalid. Please try again.')
		pause()
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
	ap.CreateFeatureclass_management(MGCP, "bs_skware", "POLYGON", spatial_reference=4326)

	with ap.da.InsertCursor("bs_skware", ["SHAPE@"]) as icursor:
		icursor.insertRow([ap.Polygon(ap.Array(coords), ap.SpatialReference(4326))])

	ap.Append_management('bs_skware', fc_cell, 'NO_TEST','First','')
	ap.Delete_management(os.path.join(MGCP, 'bs_skware'))

	# Create a feature class with a spatial reference of GCS WGS 1984
	#result = ap.management.CreateFeatureclass(MGCP, "bs_line_skware", "POLYLINE", spatial_reference=4326)
	#feature_class = result[0]

	# Write feature to new feature class
	#with ap.da.InsertCursor(feature_class, ['SHAPE@']) as icursor:
	#    icursor.insertRow([coords])

	# Use the FeatureToPolygon function to form new areas
	#ap.FeatureToPolygon_management('bs_line_skware', 'bs_skware')
	#ap.Append_management('bs_skware', fc_cell, 'NO_TEST','First','')
	#ap.Delete_management('bs_line_skware')
	#ap.Delete_management('bs_skware')

	write('\nConfirmation of Cell vertices at 1 degree intervals:')
	with ap.da.SearchCursor(fc_cell, ["SHAPE@"]) as ucursor:
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
write("\nUpdating metadata dictionaries based on inputs and sources...\n")
cell_default['CCDATE'] = local_date
cell_default['CEDDAT'] = local_date
cell_default['CMDATE'] = local_date
cell_default['CNEWSD'] = img_date_new
cell_default['COLDSD'] = img_date_old
cell_default['CELLID'] = TPC
cell_default['CCPYRT'] = u"Copyright {0} by the National Geospatial-Intelligence Agency, U.S. Government. No domestic copyright claimed under Title 17 U.S.C. All rights reserved.".format(curr_year)

#Multinational Geospatial Co-production Program (MGCP) dataset covering the 1x1 degree cell between <W> and <E> longitudes and <S> and <N> latitudes
#cell_default['CDESCR'] = b"Multinational Geospatial Co-production Program (MGCP) dataset covering the 1\xC2\xB0x1\xC2\xB0 degree cell between {0} and {1} longitudes and {2} and {3} latitudes.".format(w_long, e_long, s_lat, n_lat)
degree_sign = u'\N{DEGREE SIGN}'
cell_default['CDESCR'] = u"Multinational Geospatial Co-production Program (MGCP) dataset covering the 1{4}x1{4} degree cell between {0} and {1} longitudes and {2} and {3} latitudes.".format(w_long, e_long, s_lat, n_lat, degree_sign) # 18 and 19 longitudes and -8 and -7 latitudes # 1°x1° # b"1\xC2\xB0x1\xC2\xB0"

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

# If geonames, DVOF, or AAFIF were used in data collection
if aafif_check:
	write("AAFIF Source used. Applying dates and Subregion cell updates.")
	aafif_d['SSRCDT'] = aafif_date
if dvof_check:
	write("DVOF Source used. Applying dates and Subregion cell updates.")
	new_dvof_d['SSRCDT'] = dvof_date_new
	old_dvof_d['SSRCDT'] = dvof_date_old
if geo_check:
	write("Geonames Source used. Applying dates and Subregion cell updates.")
	new_geonames_d['SSRCDT'] = geo_date_new
	#old_geonames_d['SSRCDT'] = geo_date_old

if aafif_check or dvof_check or geo_check:
	str_aafif = ' AAFIF'
	str_dvof = ' DVOF'
	str_geo = ' Geonames'
	comma = ','
	str_and = ' and'

	# XTHOR = ((1-a)*(1-b)*(c))+((1-a)*(b)*(1-c))+((a)*(1-b)*(1-c))
	XTHOR = ((1-aafif_check)*(1-dvof_check)*(geo_check))+((1-aafif_check)*(dvof_check)*(1-geo_check))+((aafif_check)*(1-dvof_check)*(1-geo_check))
	# DXTHOR = ((1-a)*(b)*(c))+((a)*(1-b)*(c))+((a)*(b)*(1-c))
	DXTHOR = ((1-aafif_check)*(dvof_check)*(geo_check))+((aafif_check)*(1-dvof_check)*(geo_check))+((aafif_check)*(dvof_check)*(1-geo_check))
	# THRAND = (a*b*c)
	THRAND = (aafif_check*dvof_check*geo_check)

	ze_formula = ((DXTHOR+THRAND)*comma) + (XTHOR*str_and) + (aafif_check*str_aafif) + (((aafif_check*DXTHOR)+THRAND)*comma) + ((aafif_check*DXTHOR)*str_and) + (dvof_check*str_dvof) + ((dvof_check*geo_check)*comma) + ((dvof_check*geo_check)*str_and) + (geo_check*str_geo)

	subregion_default['SLSTAT'] = "Initial collection using imagery{0}.".format(ze_formula)



''''''''' Populate Secondary Metadata Tiles '''''''''

### Cell ###
#for loop to append dictionary keys and values to blank lists if they don't match with current logic
# Creates list of dictionary keys
cell_fields = cell_default.keys()
# If a cell polygon already exists and just needs to be updated (from Create New Cell checkbox)
#if not new_cell:
# Update cursor for cell feature class with the dictionary keys as the fields
with ap.da.UpdateCursor(fc_cell, cell_fields) as ucursor:
	write("\nPopulating Metadata Cell feature class geometry and attributes.")
	for row in ucursor:
		count = 0
		# For each field set the value equal to the value in the dictionary for the field key
		for field in cell_fields:
			row[count] = cell_default[field]
			count += 1
		ucursor.updateRow(row)
# Populates the gfid field using the uuid python function
with ap.da.UpdateCursor(fc_cell, ['gfid']) as ucursor:
	for row in ucursor:
		row[0] = str(uuid.uuid4())
		ucursor.updateRow(row)

# With the way arcpy handles inserts and updates, it is unable to just assign the values
# to the fields while also creating the cell shape. There for the generated cell acts as a temporary Polygon
# This inserts a new feature with the correct field values
#else:
	# with ap.da.InsertCursor(fc_cell, cell_fields) as icursor:
	# 	write("\nPopulating Metadata Cell feature class geometry and attributes.")
	# 	# Creates a list of all the values in the dictionary based on their associated field keys from the list of dictionary keys
	# 	values = [cell_default[x] for x in cell_fields]
	# 	icursor.insertRow(values)
	# # Next it applies the @SHAPE token from the temporary polygon
	# with ap.da.UpdateCursor(fc_cell, ['OID@', 'SHAPE@', 'gfid']) as ucursor:
	# 	first = 0
	# 	# Determines which feature is the temp and which has the fields populated
	# 	for row in ucursor:
	# 		# Sets a variable with the @SHAPE token from the temp polygon
	# 		if first == 0:
	# 			temp_poly = row[1]
	# 		# Sets the shape of any other features to the @SHAPE of the temp polygon
	# 		if first != 0:
	# 			row[1] = temp_poly
	# 		first = 1
	# 		# Populates the gfid field using the uuid python function
	# 		row[2] = str(uuid.uuid4())
	# 		ucursor.updateRow(row)
	# # Deletes the temp polygon after it's shape has been used
	# with ap.da.UpdateCursor(fc_cell, 'OID@') as ucursor:
	# 	top_row = 0
	# 	for row in ucursor:
	# 		if top_row == 0:
	# 			ucursor.deleteRow()
	# 		top_row = 1

### Subregion ###
# Creates list of dictionary keys
sub_fields = subregion_default.keys()
# Inserts a new feature with the values in the dictionary for the field keys
with ap.da.InsertCursor(fc_subregion, sub_fields) as icursor:
	write("Populating Metadata Subregion feature class geometry and attributes.")
	# Creates a list of all the values in the dictionary based on their associated field keys from the list of dictionary keys
	values = [subregion_default[x] for x in sub_fields]
	icursor.insertRow(values)
# Updates the shape of the subregion polygon with the shape of the previous cell polygon
with ap.da.UpdateCursor(fc_subregion, ['SHAPE@', 'gfid']) as ucursor:
	for row in ucursor:
		# Populates the gfid field using the uuid python function
		row[1] = str(uuid.uuid4())
		with ap.da.SearchCursor(fc_cell, 'SHAPE@') as scursor:
			for fc in scursor:
				row[0] = fc[0]
		ucursor.updateRow(row)

### Source ###
# Creates list of dictionary keys
src_fields = new_imagery.keys()
# Inserts new features for all specified sources with the values in the dictionary for the field keys
with ap.da.InsertCursor(fc_source, src_fields) as icursor:
	write("Populating Metadata Source feature class geometry and attributes.\n")
	# Creates lists of all the values in the dictionaries based on their associated field keys from the list of dictionary keys (the source feature class has the same keys regardless of source type)
	img_new_vals = [new_imagery[x] for x in src_fields]
	img_old_vals = [old_imagery[x] for x in src_fields]
	# Only generates features if they are specified as sources from user input
	if aafif_check:
		aafif_vals = [aafif_d[x] for x in src_fields]
	if dvof_check:
		new_dvof_vals = [new_dvof_d[x] for x in src_fields]
		old_dvof_vals = [old_dvof_d[x] for x in src_fields]
	if geo_check:
		new_geo_vals = [new_geonames_d[x] for x in src_fields]
		#old_geo_vals = [old_geonames_d[x] for x in src_fields]
	# Inserts the features based on the source values defined above
	icursor.insertRow(img_new_vals)
	write("Created Newest Imagery Source feature")
	icursor.insertRow(img_old_vals)
	write("Created Oldest Imagery Source feature")
	# Only generates features if they are specified as sources from user input
	if aafif_check:
		icursor.insertRow(aafif_vals)
		write("Created AAFIF Source feature")
	if dvof_check:
		icursor.insertRow(new_dvof_vals)
		write("Created Newest DVOF Source feature")
		icursor.insertRow(old_dvof_vals)
		write("Created Oldest DVOF Source feature")
	if geo_check:
		icursor.insertRow(new_geo_vals)
		write("Created Newest Geonames Source feature")
		#icursor.insertRow(old_geo_vals)
		#write("Created Oldest Geonames Source feature")
# Updates the shapes of the source polygons with the shape of the previous cell polygon
with ap.da.UpdateCursor(fc_source, ['SHAPE@', 'gfid']) as ucursor:
	for row in ucursor:
		# Populates the gfid field using the uuid python function
		row[1] = str(uuid.uuid4())
		with ap.da.SearchCursor(fc_cell, 'SHAPE@') as scursor:
			for fc in scursor:
				row[0] = fc[0]
		ucursor.updateRow(row)



''''''''' Export XML Metadata '''''''''

try:
	# Checks out Defense Mapping extension
	ap.CheckOutExtension("defense")
	ap.AddWarning("\nExporting metadata to xml file. Path is located here:")
	ap.AddWarning(export_path)
	# Runs Export MGCP XML Metadata tool from Defense Mapping using the cell path and the export path
	ap.ExportMetadata_defense(cell_path, export_path)
	ap.CheckInExtension("defense")
	ap.AddWarning("\n==== Metadata construction is complete! ====\n")
except:
	# Error handling. The Metadata dataset has to be in the GDB with a local copy of the data
	ap.AddError("MGCP dataset must be in the GDB along with the MGCP_Metadata dataset.")





# THNOR = (1-a)*(1-b)*(1-c) (No source option checked)
#     # 0 0 0 = 1
#     # 1 0 0 = 0
#     # 0 1 0 = 0
#     # 0 0 1 = 0
#     # 1 1 0 = 0
#     # 0 1 1 = 0
#     # 1 0 1 = 0
#     # 1 1 1 = 0
# XTHOR = ((1-a)*(1-b)*(c))+((1-a)*(b)*(1-c))+((a)*(1-b)*(1-c)) (Only 1 source option checked) # Originally (1-(a+b+c-1))+(a*b*c)
#     # 0 0 0 = 0
#     # 1 0 0 = 1
#     # 0 1 0 = 1
#     # 0 0 1 = 1
#     # 1 1 0 = 0
#     # 0 1 1 = 0
#     # 1 0 1 = 0
#     # 1 1 1 = 0
# DXTHOR = ((1-a)*(b)*(c))+((a)*(1-b)*(c))+((a)*(b)*(1-c)) (Only 2 source options checked) # Originally (a+b+c-1)-2(a*b*c)
#     # 0 0 0 = 0
#     # 1 0 0 = 0
#     # 0 1 0 = 0
#     # 0 0 1 = 0
#     # 1 1 0 = 1
#     # 0 1 1 = 1
#     # 1 0 1 = 1
#     # 1 1 1 = 0
# THRAND = (a*b*c) (All 3 source options checked) # Originally (0+a)*(0+b)*(0+c)
#     # 0 0 0 = 0
#     # 1 0 0 = 0
#     # 0 1 0 = 0
#     # 0 0 1 = 0
#     # 1 1 0 = 0
#     # 0 1 1 = 0
#     # 1 0 1 = 0
#     # 1 1 1 = 1
# THNAND = (1-(a*b*c))
#     # 0 0 0 = 1
#     # 1 0 0 = 1
#     # 0 1 0 = 1
#     # 0 0 1 = 1
#     # 1 1 0 = 1
#     # 0 1 1 = 1
#     # 1 0 1 = 1
#     # 1 1 1 = 0
# |a|d|g|
#  0 0 0  'Initial collection using imagery.'
#  1 0 0  'Initial collection using imagery and AAFIF.'
#  0 1 0  'Initial collection using imagery and DVOF.'
#  0 0 1  'Initial collection using imagery and Geonames.'
#  1 1 0  'Initial collection using imagery, AAFIF, and DVOF.'
#  0 1 1  'Initial collection using imagery, DVOF, and Geonames.'
#  1 0 1  'Initial collection using imagery, AAFIF, and Geonames.'
#  1 1 1  'Initial collection using imagery, AAFIF, DVOF, and Geonames.'



###### Making a skware in ArcMap trash heap ######

	# # Create arcpy array of point geometries and convert that to polygon object
	# array = ap.Array([ap.Point(ws[0],ws[1]), ap.Point(wn[0],wn[1]), ap.Point(en[0],en[1]), ap.Point(es[0],es[1])])
	# poly = ap.Polygon(array)
	# write(poly.WKT)
	#
	#
	# ws_p = ap.Point(ws[0],ws[1])
	# wn_p = ap.Point(wn[0],wn[1])
	# en_p = ap.Point(en[0],en[1])
	# es_p = ap.Point(es[0],es[1])
	#
	# arrlist = [ws_p, wn_p, en_p, es_p]
	# #write(arrlist[0].X)
	# corner_array = ap.Array(arrlist)
	# #write(corner_array)
	# xxx = ap.Geometry('polyline', corner_array)
	# write(xxx.WKT)
	# with ap.InsertCursor(fc_cell, 'SHAPE@') as icursor:
	# 	icursor.insertRow(ap.Polygon(xxx.getPart()))
	# write(yyy.WKT)

	# write(type(start[1]))
	# write(start[1] + "," + start[3])
	# x = decimal.Decimal(start[1])
	# y = decimal.Decimal(start[3])
	# write(type(x))
	# write(x)
	# write(y)

# >>> import arcpy
# >>> pl = ap.FromWKT('LINESTRING(0 0, 10 0, 10 10, 0 10, 0 0)', ap.SpatialReference(3857))
# >>> pl
# <Polyline object at 0x19159987dd8[0x19159c5a210]>
# >>>
# >>> pg = ap.Polygon(pl.getPart(), pl.spatialReference)
# >>> pg<Polygon object at 0x19162933908[0x19159ef0aa8]
# >>>>

	# ws = [float(start[1]), float(start[3])]
	# ws2 = [x,y]
	# write(ws)
	# write(ws2)
	# p = ap.Point(115.0000000000000001, 06.0000000000000001)
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
	# with ap.da.InsertCursor(fc_cell, 'SHAPE@') as icursor:
	# 	icursor.insertRow([poly])
	#
	# workspace = os.path.dirname(MGCP)
	# edit = ap.da.Editor(workspace)
	# # Edit session is started without an undo/redo stack for versioned data
	# # (for second argument, use False for unversioned data)
	# edit.startEditing(False, True)
	# ap.GetMessages()
	# edit.startOperation()
	# write('update cursor')
	# tcursor = ap.da.UpdateCursor(fc_cell, ["SHAPE@"])
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
	# ap.GetMessages()

	# with ap.da.UpdateCursor(fc_cell, ["SHAPE@"]) as ucursor:
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
