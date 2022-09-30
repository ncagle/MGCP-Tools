# -*- coding: utf-8 -*-
# ========================== #
# Populate MGCP Metadata v12 #
#    Nat Cagle 2022-09-29    #
# ========================== #
import sys
reload(sys)
sys.setdefaultencoding('utf8')
from arcpy import AddMessage as write
import arcpy as ap
from datetime import datetime as dt
import decimal
import os
import re
import uuid
import traceback
import xml.etree.ElementTree as et

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
'CCRSID' : 'WGS84E_2D', # 'WGS 84 2D-Geographic East-North'
'CDCHAR' : 'utf8',
'CDLANG' : 'eng',
'CFFMTN' : 'SHAPEFILE',
'CFFMTS' : 'ESRI Shapefile Technical Description - An ESRI White Paper',
'CFFMTV' : 'July 1998',
'CLSTAT' : '50k density feature extraction from monoscopic imagery using MGCP TRD v4.5.1. Ancillary source data used as needed to supplement the features not seen on imagery.',
'CMCHAR' : 'utf8',
'CMLANG' : 'eng',
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
'CURI' : 'https://www.mgcp.ws/'
}

subregion_default = {
'SACEMT' : '15', # This is a Long int in the MD_Accuracy_Eval domain representing 'Product specification'
'SACEVL' : '25',
'SALEMT' : '998', # Long int for 'Not Applicable'. Could not clarify origin domain
'SALEVL' : '-32765',
'SDESCR' : 'Single subregion',
'SFCATR' : 'MGCP_FeatureCatalogue_TRD4.5.1_20190705.xml', # 'MGCP Feature Catalogue 4.5.1'
'SFCDTD' : '2019-07-05', # 'TRD4.5.1 2019-07-05'
'SFCINC' : 'FALSE',
'SLSTAT' : 'Initial collection using imagery.',
'SMCHAR' : 'utf8',
'SMLANG' : 'eng',
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
'SVSPCD' : '2019-07-05T00:00:00Z', # 'TRD4.5.1 2019-07-05T00:00:00Z'
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



''''''''' Functions '''''''''
#-----------------------------------
# Write information for given variable
def write_info(name,var): # write_info('var_name',var)
	write("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
	write("Debug info for {0}:".format(name))
	write("   Variable Type: {0}".format(type(var)))
	write("   Assigned Value: {0}".format(var))
	write("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

#-----------------------------------
def namespace(element):
	prefix = re.findall(r'\{.*\}', element.tag)
	uri = re.findall(r'(?<=\}).*', element.tag)
	return prefix[0], uri[0]

#-----------------------------------
def add_namespace(root, prefix, uri):
		# In case of conflicting namespace definitions, first definition wins.
		if prefix not in root._namespaces.keys():
			root._namespaces[prefix] = uri
			et.register_namespace(prefix, uri)

#-----------------------------------
# Original function by Giova Lomba 2019-07-27
# https://stackoverflow.com/users/1375025/giova
# https://github.com/GiovaLomba
# Refactored for Python 2.7 and modified by Nat Cagle 2022-09-28
def xml_render(root, buffer='', namespaces=None, level=0, indent_size=2, encoding='utf-8'):
	if not level:
		buffer += '<?xml version="1.0" encoding="{0}"?>\n'.format(encoding)
	else:
		buffer += ''
	if isinstance(root, et.ElementTree):
		root = root.getroot()
	else:
		root = root
	if not level:
		_, namespaces = et._namespaces(root, 'utf-8') #[0] #et._namespaces(root)
	else:
		_, namespaces = (None, namespaces)
	print(root)
	for element in root.getiterator():
		indent = ' ' * indent_size * level
		tag = re.sub(r'({[^}]+}\s*)*', '', element.tag)
		buffer += '{0}<{1}'.format(indent, tag)
		for ns in re.findall(r'{[^}]+}', element.tag):
			ns_key = ns[1:-1]
			if ns_key not in namespaces: continue
			if namespaces[ns_key] != '':
				buffer += ' xmlns' + ':{0}'.format(namespaces[ns_key]) + '="{0}"'.format(ns_key)
			else:
				buffer += ' xmlns' + '="{0}"'.format(ns_key)
			del namespaces[ns_key]
		for k, v in element.attrib.items():
			buffer += ' {0}="{1}"'.format(k, v)
		if element.text:
			buffer += '>' + element.text.strip()
		else:
			buffer += '>'
		children = list(element)
		for child in children:
			if buffer[-1] != '\n':
				sep = '\n'
			else:
				sep = ''
			buffer += sep + xml_render(child, level=level+1, indent_size=indent_size, namespaces=namespaces)
		if 0 != len(children):
			buffer += '{0}</{1}>\n'.format(indent, tag)
		else:
			buffer += '</{0}>\n'.format(tag)
	return buffer



''''''''' User Parameters '''''''''
## [0] MGCP_Metadata Dataset - Feature Dataset
MGCP = ap.GetParameterAsText(0)
ap.env.workspace = MGCP
ap.env.overwriteOutput = True
## [1] Generate Cell Polygon? - Boolean # Default: True
new_cell = ap.GetParameter(1)
## [2] Imagery Footprint (Original) - Shapefile
img_foot = ap.GetParameterAsText(2)
## [3] TPC Coordinates (Cell ID - i.e. E018S07) - String
TPC = ap.GetParameterAsText(3)
## [4] Edition 1 Update? - Boolean # Default: True
# "Leave attribute field blank for Edition 1. Populate with 'Complete Update' for Edition 2, 3, etc."
update_edition = ap.GetParameter(4)
## [5] Date the database was pulled local (Format as YYYY-MM-DD) - String
local_date = ap.GetParameterAsText(5) # Date TPC was pulled local for finishing YYYY-MM-DD (for latest extraction date)
## [6] Delivery Date (Format as YYYY-MM-DD) - String
gait_date = ap.GetParameterAsText(6) # Delivery date (for date of final GAIT run)
### Ancillary Sources
# AAFIF
## [7] Was an AAFIF source used? - Boolean # Default: False
aafif_check = ap.GetParameter(7) # There is absolutely too much miscellaneous nonsense with this junk. Just find the date yourself and input it.
## [8] Newest AAFIF Date (Format as YYYY-MM-DD) (Optional) - String
aafif_date = ap.GetParameterAsText(8) # YYYY-MM-DD
# DVOF
## [9] Was a DVOF source used? - Boolean # Default: False
dvof_check = ap.GetParameter(9) # Did you use DVOF checkbox
## [10] Was the DVOF source a shapefile? (Optional) - Boolean # Default: False
dvof_shp_check = ap.GetParameter(10) # Why can nothing ever be consistent. This is for if you only have a DVOF source shapefile (point only)
## [11] DVOF Point Feature Class (or shapefile if necessary) (Optional) - Feature Class
dvof_file = ap.GetParameterAsText(11)
# Geonames
## [12] Was a Geonames source used? - Boolean # Default: False
geo_check = ap.GetParameter(12) # Did you use geonames checkbox
## [13] Was the Geonames source a shapefile? (Optional) - Boolean # Default: False
geo_shp_check = ap.GetParameter(13) # Do you only have access to a Geonames shapefile in stead of a FC for some incredibly inconvenient reason?
## [14] Geonames Point Feature Class (or shapefile if necessary) (Optional) - Feature Class
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
	ap.CreateFeatureclass_management(MGCP, "bs_skware", "POLYGON", spatial_reference=4326)

	with ap.da.InsertCursor("bs_skware", ["SHAPE@"]) as icursor:
		icursor.insertRow([ap.Polygon(ap.Array(coords), ap.SpatialReference(4326))])

	ap.Append_management('bs_skware', fc_cell, 'NO_TEST','First','')
	ap.Delete_management(os.path.join(MGCP, 'bs_skware'))

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
#-----------------------------------
# Creates list of dictionary keys
cell_fields = cell_default.keys()
# If a cell polygon already exists and just needs to be updated (from Create New Cell checkbox)
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

### Subregion ###
#-----------------------------------
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
#-----------------------------------
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
	write("\nExporting metadata to XML file...")
	# Runs Export MGCP XML Metadata tool from Defense Mapping using the cell path and the export path
	ap.ExportMetadata_defense(cell_path, export_path)

	write("Replacing misattributed 'MGCP_v4_r2' with 'MGCP_v4_r5.1' in the XML output.")
	xml_out = os.path.join(export_path, TPC + '.xml')
	xml_mod = os.path.join(export_path, TPC + '_mod.xml')
	if os.path.exists(xml_mod):
		write("Modified XML file already exists. Replacing modified XML with new version.")
		os.remove(xml_mod)
	old_trd = 'MGCP_v4_r2'
	current_trd = 'MGCP_v4_r5.1'

	with open(xml_out, 'r') as x_out, open(xml_mod, 'a') as x_mod:
		line_num = 0
		values_repaired = 0
		while True:
			line_num +=1
			line = x_out.readline()
			if line == '': break
			if old_trd in line:
				values_repaired +=1
				line = line.replace(old_trd, current_trd)
				write("~ Found '{0}' tag on line {1} ~".format(old_trd, line_num))
			x_mod.write(line)
	write("Replaced {0} '{1}' tags with '{2}'".format(values_repaired, old_trd, current_trd))

	# Remove original metadata output and rename the modified one to match what it should be.
	os.remove(xml_out)
	os.rename(xml_mod, xml_out)

	ap.AddWarning("\n\nXML file is located here:")
	ap.AddWarning(xml_out)
	ap.CheckInExtension("defense")
	ap.AddWarning("\n\n==== Metadata construction is complete! ====\n")
except:
	# Error handling. The Metadata dataset has to be in the GDB with a local copy of the data
	ap.AddError("MGCP dataset must be in the GDB along with the MGCP_Metadata dataset.")




# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
#                                  Trash Pile                                  #
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

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


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#


# xml_out = os.path.join(export_path, TPC + '.xml') #r'C:\Projects\njcagle\finishing\====== L3Harris_MGCP ======\_documentation_run\Final GAIT\E124N07.xml'
# xml_mod = os.path.join(export_path, TPC + '_mod.xml')
#
#
# #----------------------------------------------------------------------
#
#
# xml_out = os.path.join(export_path, TPC + '.xml')
# with open(xml_out) as xml:
# 	tree = et.parse(xml)
# 	root = tree.getroot()
# 	write("Replacing misattributed 'MGCP_v4_r2' with 'MGCP_v4_r5.1' in the XML output.")
# 	for element in root.getiterator():
# 		try:
# 			element.text = element.text.replace('MGCP_v4_r2', 'MGCP_v4_r5.1')
# 		except AttributeError:
# 			pass
# tree.write(xml_out)
#
#
# #----------------------------------------------------------------------
#
#
# metadata_ns = {
# 	'gmd': 'http://www.isotc211.org/2005/gmd',
# 	'gml': 'http://www.opengis.net/gml',
# 	'gco': 'http://www.isotc211.org/2005/gco',
# 	'gmx': 'http://www.isotc211.org/2005/gmx',
# 	'xlink': 'http://www.w3.org/1999/xlink',
# 	'mgcp': 'http://www.dgiwg.org/2005/mgcp'
# }
#
# with open(xml_out) as xml:
# 	tree = et.parse(xml)
# 	root = tree.getroot()
# 	tree.find('mgcp:MGCP_Cell/gmd:has/gmd:MD_Metadata/gmd:referenceSystemInfo/gmd:MD_ReferenceSystem/gmd:referenceSystemIdentifier/gmd:RS_Identifier/gmd:codeSpace/gco:CharacterString', metadata_ns).text = 'MGCP_v4_r5.1'
# 	tree.find('mgcp:MGCP_Cell/gmd:has/gmd:MD_Metadata/gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:identifier/gmd:RS_Identifier/gmd:codeSpace/gco:CharacterString', metadata_ns).text = 'MGCP_v4_r5.1'
# 	tree.find('mgcp:MGCP_Cell/mgcp:subregion/mgcp:MGCP_Subregion/mgcp:subregionMetadata/gmd:MD_Metadata/gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:identifier/gmd:RS_Identifier/gmd:codeSpace/gco:CharacterString', metadata_ns).text = 'MGCP_v4_r5.1'
# 	tree.find('mgcp:MGCP_Cell/mgcp:subregion/mgcp:MGCP_Subregion/mgcp:subregionMetadata/gmd:MD_Metadata/gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:report/gmd:DQ_AbsoluteExternalPositionalAccuracy/gmd:measureIdentification/gmd:RS_Identifier/gmd:codeSpace/gco:CharacterString', metadata_ns).text = 'MGCP_v4_r5.1'
# 	trd_code_space1 = tree.find('mgcp:MGCP_Cell/gmd:has/gmd:MD_Metadata/gmd:referenceSystemInfo/gmd:MD_ReferenceSystem/gmd:referenceSystemIdentifier/gmd:RS_Identifier/gmd:codeSpace/gco:CharacterString', metadata_ns)
# 	trd_code_space2 = tree.find('mgcp:MGCP_Cell/gmd:has/gmd:MD_Metadata/gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:identifier/gmd:RS_Identifier/gmd:codeSpace/gco:CharacterString', metadata_ns)
# 	trd_code_space3 = tree.find('mgcp:MGCP_Cell/mgcp:subregion/mgcp:MGCP_Subregion/mgcp:subregionMetadata/gmd:MD_Metadata/gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:identifier/gmd:RS_Identifier/gmd:codeSpace/gco:CharacterString', metadata_ns)
# 	trd_code_space4 = tree.find('mgcp:MGCP_Cell/mgcp:subregion/mgcp:MGCP_Subregion/mgcp:subregionMetadata/gmd:MD_Metadata/gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:report/gmd:DQ_AbsoluteExternalPositionalAccuracy/gmd:measureIdentification/gmd:RS_Identifier/gmd:codeSpace/gco:CharacterString', metadata_ns)
# 	print(trd_code_space1.text)
# 	print(trd_code_space2.text)
# 	print(trd_code_space3.text)
# 	print(trd_code_space4.text)
#
#
# #----------------------------------------------------------------------
#
#
# # Original function by Giova Lomba 2019-07-27
# # https://stackoverflow.com/users/1375025/giova
# # https://github.com/GiovaLomba
# # Refactored for Python 2.7 and modified by Nat Cagle 2022-09-28
# def xml_render(root, buffer='', namespaces=None, level=0, indent_size=2, encoding='utf-8'):
# 	if not level:
# 		buffer += '<?xml version="1.0" encoding="{0}"?>\n'.format(encoding)
# 	else:
# 		buffer += ''
# 	if isinstance(root, et.ElementTree):
# 		root = root.getroot()
# 	else:
# 		root = root
# 	if not level:
# 		_, namespaces = et._namespaces(root, 'utf-8') #[0] #et._namespaces(root)
# 	else:
# 		_, namespaces = (None, namespaces)
# 	print(root)
# 	for element in root.getiterator():
# 		indent = ' ' * indent_size * level
# 		tag = re.sub(r'({[^}]+}\s*)*', '', element.tag)
# 		buffer += '{0}<{1}'.format(indent, tag)
# 		for ns in re.findall(r'{[^}]+}', element.tag):
# 			ns_key = ns[1:-1]
# 			if ns_key not in namespaces: continue
# 			if namespaces[ns_key] != '':
# 				buffer += ' xmlns' + ':{0}'.format(namespaces[ns_key]) + '="{0}"'.format(ns_key)
# 			else:
# 				buffer += ' xmlns' + '="{0}"'.format(ns_key)
# 			del namespaces[ns_key]
# 		for k, v in element.attrib.items():
# 			buffer += ' {0}="{1}"'.format(k, v)
# 		if element.text:
# 			buffer += '>' + element.text.strip()
# 		else:
# 			buffer += '>'
# 		children = list(element)
# 		for child in children:
# 			if buffer[-1] != '\n':
# 				sep = '\n'
# 			else:
# 				sep = ''
# 			buffer += sep + xml_render(child, level=level+1, indent_size=indent_size, namespaces=namespaces)
# 		if 0 != len(children):
# 			buffer += '{0}</{1}>\n'.format(indent, tag)
# 		else:
# 			buffer += '</{0}>\n'.format(tag)
# 	return buffer
#
# tree = et.parse(xml_out)
# root = tree.getroot()
#
# trd_code_space1 = root.find('{http://www.isotc211.org/2005/gmd}has/{http://www.isotc211.org/2005/gmd}MD_Metadata/{http://www.isotc211.org/2005/gmd}referenceSystemInfo/{http://www.isotc211.org/2005/gmd}MD_ReferenceSystem/{http://www.isotc211.org/2005/gmd}referenceSystemIdentifier/{http://www.isotc211.org/2005/gmd}RS_Identifier/{http://www.isotc211.org/2005/gmd}codeSpace/{http://www.isotc211.org/2005/gco}CharacterString')
# trd_code_space2 = root.find('{http://www.isotc211.org/2005/gmd}has/{http://www.isotc211.org/2005/gmd}MD_Metadata/{http://www.isotc211.org/2005/gmd}identificationInfo/{http://www.isotc211.org/2005/gmd}MD_DataIdentification/{http://www.isotc211.org/2005/gmd}citation/{http://www.isotc211.org/2005/gmd}CI_Citation/{http://www.isotc211.org/2005/gmd}identifier/{http://www.isotc211.org/2005/gmd}RS_Identifier/{http://www.isotc211.org/2005/gmd}codeSpace/{http://www.isotc211.org/2005/gco}CharacterString')
# trd_code_space3 = root.find('{http://www.dgiwg.org/2005/mgcp}subregion/{http://www.dgiwg.org/2005/mgcp}MGCP_Subregion/{http://www.dgiwg.org/2005/mgcp}subregionMetadata/{http://www.isotc211.org/2005/gmd}MD_Metadata/{http://www.isotc211.org/2005/gmd}identificationInfo/{http://www.isotc211.org/2005/gmd}MD_DataIdentification/{http://www.isotc211.org/2005/gmd}citation/{http://www.isotc211.org/2005/gmd}CI_Citation/{http://www.isotc211.org/2005/gmd}identifier/{http://www.isotc211.org/2005/gmd}RS_Identifier/{http://www.isotc211.org/2005/gmd}codeSpace/{http://www.isotc211.org/2005/gco}CharacterString')
# trd_code_space4 = root.find('{http://www.dgiwg.org/2005/mgcp}subregion/{http://www.dgiwg.org/2005/mgcp}MGCP_Subregion/{http://www.dgiwg.org/2005/mgcp}subregionMetadata/{http://www.isotc211.org/2005/gmd}MD_Metadata/{http://www.isotc211.org/2005/gmd}dataQualityInfo/{http://www.isotc211.org/2005/gmd}DQ_DataQuality/{http://www.isotc211.org/2005/gmd}report/{http://www.isotc211.org/2005/gmd}DQ_AbsoluteExternalPositionalAccuracy/{http://www.isotc211.org/2005/gmd}measureIdentification/{http://www.isotc211.org/2005/gmd}RS_Identifier/{http://www.isotc211.org/2005/gmd}codeSpace/{http://www.isotc211.org/2005/gco}CharacterString')
#
# trd_code_space1.text = 'MGCP_v4_r5.1'
# trd_code_space2.text = 'MGCP_v4_r5.1'
# trd_code_space3.text = 'MGCP_v4_r5.1'
# trd_code_space4.text = 'MGCP_v4_r5.1'
#
# with open(xml_mod, "w") as xml:
# 	xml.write(xml_render(root))
#
#
# #----------------------------------------------------------------------
#
#
# import re
# def namespace(element):
# 	prefix = re.findall(r'\{.*\}', element.tag)
# 	uri = re.findall(r'(?<=\}).*', element.tag)
# 	return prefix[0], uri[0]
#
# def add_namespace(root, prefix, uri):
#         # In case of conflicting namespace definitions, first definition wins.
#         if prefix not in root._namespaces.keys():
#             root._namespaces[prefix] = uri
#             et.register_namespace(prefix, uri)
#
#
# #----------------------------------------------------------------------
# #################
# #### WORKING ####
# #################
# # !_!‾!_!‾!_!‾!_!‾!_!‾!_!‾!_!‾!_!‾!_!‾!_!‾!_!‾!_!‾!_!‾!_!‾!_!‾!_!‾!_!‾!_!‾!_!‾!
#
# # -*- coding: utf-8 -*-
# import sys
# reload(sys)
# sys.setdefaultencoding('utf8')
#
# xml_out = os.path.join(export_path, TPC + '.xml')
# xml_mod = os.path.join(export_path, TPC + '_mod.xml')
# old_trd = 'MGCP_v4_r2'
# current_trd = 'MGCP_v4_r5.1'
#
# with open(xml_out, 'r') as x_out, open(xml_mod, 'a') as x_mod:
#     while True:
#         line = x_out.readline()
#         if line == '': break
#         if old_trd in line:
#             line = line.replace(old_trd, current_trd)
#             print("\n\n** Found {0}! **\n** Replaced with {1}. **\n\n".format(old_trd, current_trd))
#         x_mod.write(line)
#
# # !_!‾!_!‾!_!‾!_!‾!_!‾!_!‾!_!‾!_!‾!_!‾!_!‾!_!‾!_!‾!_!‾!_!‾!_!‾!_!‾!_!‾!_!‾!_!‾!
# #----------------------------------------------------------------------
#
#
# et._namespaces(root, 'utf-8')
# (	{'{http://www.isotc211.org/2005/gmd}CI_ResponsibleParty': 'ns1:CI_ResponsibleParty',
# 	'{http://www.isotc211.org/2005/gmd}CI_Address': 'ns1:CI_Address',
# 	'{http://www.isotc211.org/2005/gmd}dataQualityInfo': 'ns1:dataQualityInfo',
# 	'{http://www.dgiwg.org/2005/mgcp}subregionCatalogue': 'ns0:subregionCatalogue',
# 	'{http://www.isotc211.org/2005/gmd}title': 'ns1:title',
# 	'{http://www.isotc211.org/2005/gmd}MD_SecurityConstraints': 'ns1:MD_SecurityConstraints',
# 	'{http://www.isotc211.org/2005/gmd}code': 'ns1:code',
# 	'{http://www.isotc211.org/2005/gmd}CI_Date': 'ns1:CI_Date',
# 	'{http://www.isotc211.org/2005/gmd}DQ_ConformanceResult': 'ns1:DQ_ConformanceResult',
# 	'{http://www.isotc211.org/2005/gmx}dataFile': 'ns3:dataFile',
# 	'{http://www.isotc211.org/2005/gmx}featureTypes': 'ns3:featureTypes',
# 	'{http://www.isotc211.org/2005/gmd}LI_Source': 'ns1:LI_Source',
# 	'{http://www.isotc211.org/2005/gmd}metadataStandardName': 'ns1:metadataStandardName',
# 	'{http://www.isotc211.org/2005/gmd}MD_RepresentativeFraction': 'ns1:MD_RepresentativeFraction',
# 	'{http://www.isotc211.org/2005/gmd}citation': 'ns1:citation',
# 	'{http://www.isotc211.org/2005/gmd}MD_GeometricObjects': 'ns1:MD_GeometricObjects',
# 	'{http://www.isotc211.org/2005/gmd}lineage': 'ns1:lineage',
# 	'{http://www.isotc211.org/2005/gco}Integer': 'ns2:Integer',
# 	'{http://www.isotc211.org/2005/gmd}spatialRepresentationInfo': 'ns1:spatialRepresentationInfo',
# 	'{http://www.isotc211.org/2005/gmd}geometricObjectCount': 'ns1:geometricObjectCount',
# 	'{http://www.isotc211.org/2005/gco}Record': 'ns2:Record',
# 	'{http://www.isotc211.org/2005/gmd}address': 'ns1:address',
# 	'{http://www.isotc211.org/2005/gmd}MD_Constraints': 'ns1:MD_Constraints',
# 	'{http://www.isotc211.org/2005/gmx}MimeFileType': 'ns3:MimeFileType',
# 	'{http://www.isotc211.org/2005/gmd}source': 'ns1:source',
# 	'{http://www.isotc211.org/2005/gmd}valueUnit': 'ns1:valueUnit',
# 	'{http://www.isotc211.org/2005/gco}Date': 'ns2:Date',
# 	'{http://www.isotc211.org/2005/gmx}Anchor': 'ns3:Anchor',
# 	'{http://www.isotc211.org/2005/gmd}scaleDenominator': 'ns1:scaleDenominator',
# 	'{http://www.isotc211.org/2005/gmd}CI_Contact': 'ns1:CI_Contact',
# 	'{http://www.isotc211.org/2005/gmd}featureTypes': 'ns1:featureTypes',
# 	'{http://www.isotc211.org/2005/gco}DateTime': 'ns2:DateTime',
# 	'{http://www.isotc211.org/2005/gmd}level': 'ns1:level',
# 	'{http://www.isotc211.org/2005/gmd}identifier': 'ns1:identifier',
# 	'{http://www.isotc211.org/2005/gmd}identificationInfo': 'ns1:identificationInfo',
# 	'{http://www.opengis.net/gml}LinearRing': 'ns5:LinearRing',
# 	'{http://www.opengis.net/gml}posList': 'ns5:posList',
# 	'{http://www.isotc211.org/2005/gmd}dataSetURI': 'ns1:dataSetURI',
# 	'{http://www.isotc211.org/2005/gmd}includedWithDataset': 'ns1:includedWithDataset',
# 	'{http://www.opengis.net/gml}id': 'ns5:id',
# 	'{http://www.isotc211.org/2005/gmd}MD_FeatureCatalogueDescription': 'ns1:MD_FeatureCatalogueDescription',
# 	'{http://www.isotc211.org/2005/gmd}report': 'ns1:report',
# 	'{http://www.isotc211.org/2005/gmd}date': 'ns1:date',
# 	'{http://www.dgiwg.org/2005/mgcp}MGCP_Cell': 'ns0:MGCP_Cell',
# 	'{http://www.dgiwg.org/2005/mgcp}subregionMetadata': 'ns0:subregionMetadata',
# 	'{http://www.isotc211.org/2005/gmd}metadataStandardVersion': 'ns1:metadataStandardVersion',
# 	'{http://www.isotc211.org/2005/gmx}FileName': 'ns3:FileName',
# 	'{http://www.isotc211.org/2005/gmd}hierarchyLevel': 'ns1:hierarchyLevel',
# 	'{http://www.isotc211.org/2005/gmd}southBoundLatitude': 'ns1:southBoundLatitude',
# 	'{http://www.isotc211.org/2005/gmd}measureDescription': 'ns1:measureDescription',
# 	None: None,
# 	'{http://www.isotc211.org/2005/gmd}MD_ClassificationCode': 'ns1:MD_ClassificationCode',
# 	'{http://www.isotc211.org/2005/gmd}pass': 'ns1:pass',
# 	'{http://www.isotc211.org/2005/gmd}organisationName': 'ns1:organisationName',
# 	'{http://www.isotc211.org/2005/gmx}fileFormat': 'ns3:fileFormat',
# 	'{http://www.dgiwg.org/2005/mgcp}subregion': 'ns0:subregion',
# 	'{http://www.dgiwg.org/2005/mgcp}MGCP_AccuracyEvaluationMethod': 'ns0:MGCP_AccuracyEvaluationMethod',
# 	'{http://www.isotc211.org/2005/gco}Boolean': 'ns2:Boolean',
# 	'{http://www.isotc211.org/2005/gmd}polygon': 'ns1:polygon',
# 	'{http://www.isotc211.org/2005/gmd}CI_DateTypeCode': 'ns1:CI_DateTypeCode',
# 	'{http://www.isotc211.org/2005/gmd}distributionFormat': 'ns1:distributionFormat',
# 	'{http://www.isotc211.org/2005/gmd}CI_Citation': 'ns1:CI_Citation',
# 	'{http://www.isotc211.org/2005/gmd}complianceCode': 'ns1:complianceCode',
# 	'{http://www.isotc211.org/2005/gmd}statement': 'ns1:statement',
# 	'{http://www.isotc211.org/2005/gmd}dateType': 'ns1:dateType',
# 	'src': 'src',
# 	'{http://www.isotc211.org/2005/gmd}DQ_AbsoluteExternalPositionalAccuracy': 'ns1:DQ_AbsoluteExternalPositionalAccuracy',
# 	'{http://www.isotc211.org/2005/gmd}geographicElement': 'ns1:geographicElement',
# 	'{http://www.isotc211.org/2005/gmd}contentInfo': 'ns1:contentInfo',
# 	'{http://www.isotc211.org/2005/gmd}equivalentScale': 'ns1:equivalentScale',
# 	'{http://www.isotc211.org/2005/gmd}referenceSystemIdentifier': 'ns1:referenceSystemIdentifier',
# 	'{http://www.isotc211.org/2005/gmd}DQ_QuantitativeResult': 'ns1:DQ_QuantitativeResult',
# 	'{http://www.isotc211.org/2005/gmd}country': 'ns1:country',
# 	'{http://www.isotc211.org/2005/gmx}fileType': 'ns3:fileType',
# 	'{http://www.isotc211.org/2005/gmx}MX_DataFile': 'ns3:MX_DataFile',
# 	'{http://www.isotc211.org/2005/gmd}MD_Metadata': 'ns1:MD_Metadata',
# 	'{http://www.isotc211.org/2005/gmd}CI_RoleCode': 'ns1:CI_RoleCode',
# 	'{http://www.isotc211.org/2005/gmd}result': 'ns1:result',
# 	'{http://www.isotc211.org/2005/gmd}scope': 'ns1:scope',
# 	'{http://www.isotc211.org/2005/gmd}MD_GeometricObjectTypeCode': 'ns1:MD_GeometricObjectTypeCode',
# 	'{http://www.isotc211.org/2005/gmd}has': 'ns1:has',
# 	'{http://www.isotc211.org/2005/gmd}hierarchyLevelName': 'ns1:hierarchyLevelName',
# 	'{http://www.dgiwg.org/2005/mgcp}MGCP_VerticalSourceTypeId': 'ns0:MGCP_VerticalSourceTypeId',
# 	'{http://www.isotc211.org/2005/gmd}metadataConstraints': 'ns1:metadataConstraints',
# 	'{http://www.isotc211.org/2005/gmd}MD_Format': 'ns1:MD_Format',
# 	'{http://www.isotc211.org/2005/gmd}resourceConstraints': 'ns1:resourceConstraints',
# 	'{http://www.isotc211.org/2005/gmd}RS_Identifier': 'ns1:RS_Identifier',
# 	'{http://www.isotc211.org/2005/gmd}supplementalInformation': 'ns1:supplementalInformation',
# 	'{http://www.isotc211.org/2005/gmd}westBoundLongitude': 'ns1:westBoundLongitude',
# 	'{http://www.isotc211.org/2005/gmd}CI_Series': 'ns1:CI_Series',
# 	'{http://www.isotc211.org/2005/gmd}MD_RestrictionCode': 'ns1:MD_RestrictionCode',
# 	'{http://www.isotc211.org/2005/gmd}language': 'ns1:language',
# 	'{http://www.isotc211.org/2005/gmd}MD_Distribution': 'ns1:MD_Distribution',
# 	'{http://www.isotc211.org/2005/gmd}characterSet': 'ns1:characterSet',
# 	'type': 'type',
# 	'{http://www.w3.org/1999/xlink}href': 'ns4:href',
# 	'{http://www.isotc211.org/2005/gmd}MD_SpatialRepresentationTypeCode': 'ns1:MD_SpatialRepresentationTypeCode',
# 	'{http://www.isotc211.org/2005/gco}CharacterString': 'ns2:CharacterString',
# 	'{http://www.isotc211.org/2005/gmd}topicCategory': 'ns1:topicCategory',
# 	'{http://www.isotc211.org/2005/gmd}extent': 'ns1:extent',
# 	'{http://www.isotc211.org/2005/gmd}DQ_DataQuality': 'ns1:DQ_DataQuality',
# 	'{http://www.isotc211.org/2005/gmd}specification': 'ns1:specification',
# 	'{http://www.isotc211.org/2005/gmd}referenceSystemInfo': 'ns1:referenceSystemInfo',
# 	'{http://www.isotc211.org/2005/gmd}EX_GeographicBoundingBox': 'ns1:EX_GeographicBoundingBox',
# 	'{http://www.isotc211.org/2005/gmd}dateStamp': 'ns1:dateStamp',
# 	'{http://www.dgiwg.org/2005/mgcp}MGCP_SourceTypeId': 'ns0:MGCP_SourceTypeId',
# 	'{http://www.isotc211.org/2005/gmd}role': 'ns1:role',
# 	'{http://www.isotc211.org/2005/gmd}denominator': 'ns1:denominator',
# 	'{http://www.isotc211.org/2005/gmd}northBoundLatitude': 'ns1:northBoundLatitude',
# 	'{http://www.isotc211.org/2005/gmd}measureIdentification': 'ns1:measureIdentification',
# 	'{http://www.isotc211.org/2005/gmd}useConstraints': 'ns1:useConstraints',
# 	'{http://www.isotc211.org/2005/gmd}geometricObjects': 'ns1:geometricObjects',
# 	'{http://www.dgiwg.org/2005/mgcp}MGCP_ParticipantNation': 'ns0:MGCP_ParticipantNation',
# 	'{http://www.isotc211.org/2005/gmd}EX_Extent': 'ns1:EX_Extent',
# 	'{http://www.isotc211.org/2005/gmd}name': 'ns1:name',
# 	'{http://www.isotc211.org/2005/gmd}geometricObjectType': 'ns1:geometricObjectType',
# 	'{http://www.isotc211.org/2005/gmd}contactInfo': 'ns1:contactInfo',
# 	'{http://www.isotc211.org/2005/gmd}spatialResolution': 'ns1:spatialResolution',
# 	'{http://www.dgiwg.org/2005/mgcp}MGCP_LanguageCode': 'ns0:MGCP_LanguageCode',
# 	'{http://www.isotc211.org/2005/gmd}series': 'ns1:series',
# 	'{http://www.isotc211.org/2005/gmd}abstract': 'ns1:abstract',
# 	'{http://www.isotc211.org/2005/gmd}evaluationMethodDescription': 'ns1:evaluationMethodDescription',
# 	'{http://www.isotc211.org/2005/gmx}fileName': 'ns3:fileName',
# 	'{http://www.dgiwg.org/2005/mgcp}MGCP_ParticipantAgency': 'ns0:MGCP_ParticipantAgency',
# 	'{http://www.isotc211.org/2005/gmd}MD_ScopeCode': 'ns1:MD_ScopeCode',
# 	'{http://www.isotc211.org/2005/gco}Decimal': 'ns2:Decimal',
# 	'{http://www.isotc211.org/2005/gmd}contact': 'ns1:contact',
# 	'{http://www.isotc211.org/2005/gmd}featureCatalogueCitation': 'ns1:featureCatalogueCitation',
# 	'codeListValue': 'codeListValue',
# 	'{http://www.isotc211.org/2005/gmd}pointOfContact': 'ns1:pointOfContact',
# 	'{http://www.isotc211.org/2005/gmd}accessConstraints': 'ns1:accessConstraints',
# 	'{http://www.isotc211.org/2005/gmd}MD_ReferenceSystem': 'ns1:MD_ReferenceSystem',
# 	'id': 'id',
# 	'{http://www.isotc211.org/2005/gmd}DQ_ConceptualConsistency': 'ns1:DQ_ConceptualConsistency',
# 	'{http://www.isotc211.org/2005/gmd}version': 'ns1:version',
# 	'{http://www.isotc211.org/2005/gmd}MD_CharacterSetCode': 'ns1:MD_CharacterSetCode',
# 	'{http://www.isotc211.org/2005/gco}LocalName': 'ns2:LocalName',
# 	'{http://www.isotc211.org/2005/gmd}distributionInfo': 'ns1:distributionInfo',
# 	'{http://www.isotc211.org/2005/gmd}MD_DataIdentification': 'ns1:MD_DataIdentification',
# 	'{http://www.opengis.net/gml}exterior': 'ns5:exterior',
# 	'{http://www.isotc211.org/2005/gmd}explanation': 'ns1:explanation',
# 	'{http://www.isotc211.org/2005/gmd}MD_Resolution': 'ns1:MD_Resolution',
# 	'codeList': 'codeList',
# 	'{http://www.isotc211.org/2005/gmd}useLimitation': 'ns1:useLimitation',
# 	'{http://www.isotc211.org/2005/gmd}LI_Lineage': 'ns1:LI_Lineage',
# 	'{http://www.isotc211.org/2005/gmx}fileDescription': 'ns3:fileDescription',
# 	'{http://www.isotc211.org/2005/gmd}eastBoundLongitude': 'ns1:eastBoundLongitude',
# 	'{http://www.isotc211.org/2005/gmd}handlingDescription': 'ns1:handlingDescription',
# 	'{http://www.isotc211.org/2005/gmd}sourceCitation': 'ns1:sourceCitation',
# 	'{http://www.isotc211.org/2005/gmd}DQ_Scope': 'ns1:DQ_Scope',
# 	'{http://www.isotc211.org/2005/gmd}classification': 'ns1:classification',
# 	'{http://www.isotc211.org/2005/gmd}value': 'ns1:value',
# 	'{http://www.isotc211.org/2005/gmd}MD_LegalConstraints': 'ns1:MD_LegalConstraints',
# 	'{http://www.isotc211.org/2005/gmd}MD_VectorSpatialRepresentation': 'ns1:MD_VectorSpatialRepresentation',
# 	'{http://www.isotc211.org/2005/gmd}nameOfMeasure': 'ns1:nameOfMeasure',
# 	'{http://www.opengis.net/gml}Polygon': 'ns5:Polygon',
# 	'{http://www.dgiwg.org/2005/mgcp}MGCP_Subregion': 'ns0:MGCP_Subregion',
# 	'{http://www.isotc211.org/2005/gmd}sourceExtent': 'ns1:sourceExtent',
# 	'{http://www.isotc211.org/2005/gmd}otherConstraints': 'ns1:otherConstraints',
# 	'{http://www.isotc211.org/2005/gmd}EX_BoundingPolygon': 'ns1:EX_BoundingPolygon',
# 	'{http://www.isotc211.org/2005/gmd}dateTime': 'ns1:dateTime',
# 	'{http://www.isotc211.org/2005/gmd}editionDate': 'ns1:editionDate',
# 	'{http://www.isotc211.org/2005/gmd}codeSpace': 'ns1:codeSpace',
# 	'{http://www.isotc211.org/2005/gmd}resourceFormat': 'ns1:resourceFormat',
# 	'{http://www.isotc211.org/2005/gmd}MD_TopicCategoryCode': 'ns1:MD_TopicCategoryCode',
# 	'{http://www.isotc211.org/2005/gmd}spatialRepresentationType': 'ns1:spatialRepresentationType'
# 	},
# 	{'http://www.isotc211.org/2005/gmx': 'ns3',
# 	'http://www.isotc211.org/2005/gmd': 'ns1',
# 	'http://www.opengis.net/gml': 'ns5',
# 	'http://www.isotc211.org/2005/gco': 'ns2',
# 	'http://www.dgiwg.org/2005/mgcp': 'ns0',
# 	'http://www.w3.org/1999/xlink': 'ns4'}
# )
#
# dir(et)
# ['Comment', 'Element', 'ElementPath', 'ElementTree', 'HTML_EMPTY', 'PI', 'ParseError', 'ProcessingInstruction', 'QName', 'SubElement', 'TreeBuilder', 'VERSION', 'XML', 'XMLID', 'XMLParser', 'XMLTreeBuilder', '_Element', '_ElementInterface', '_IterParseIterator', '_SimpleElementPath', '__all__', '__builtins__', '__doc__', '__file__', '__name__', '__package__', '_encode', '_escape_attrib', '_escape_attrib_html', '_escape_cdata', '_namespace_map', '_namespaces', '_raise_serialization_error', '_sentinel', '_serialize', '_serialize_html', '_serialize_text', '_serialize_xml', 'dump', 'fromstring', 'fromstringlist', 'iselement', 'iterparse', 'parse', 're', 'register_namespace', 'sys', 'tostring', 'tostringlist', 'warnings']
#
# dir(et._namespaces)
# ['__call__', '__class__', '__closure__', '__code__', '__defaults__', '__delattr__', '__dict__', '__doc__', '__format__', '__get__', '__getattribute__', '__globals__', '__hash__', '__init__', '__module__', '__name__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', 'func_closure', 'func_code', 'func_defaults', 'func_dict', 'func_doc', 'func_globals', 'func_name']


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#


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
