# -*- coding: utf-8 -*-
# ============================ #
# Populate Feature Metadata v8 #
# Nat Cagle 2022-07-21         #
# ============================ #
import arcpy as ap
from arcpy import AddMessage as write
from datetime import datetime as dt
import time
import uuid
import sys
import inspect

#            _________________________________
#           | Takes an MGCP dataset and       |
#           | imagery footprint and checks    |
#           | which features are within       |
#           | which newest footprint polygon  |
#           | and updates the feature SDV     |
#           | field with a properly formatted |
#           | Acquisition date from that      |
#           | footprint polygon.              |
#      _    /‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾
#   __(.)< ‾
#~~~\___)~~~



def get_count(fc): # Returns feature count
    results = int(ap.GetCount_management(fc).getOutput(0))
    return results

# Explicit is better than implicit
# Lambda function works better than "if not fieldname:", which can falsely catch 0.
populated = lambda x: x is not None and str(x).strip() != '' # Function that returns boolean of if input field is populated or empty

def debug_view(**kwargs): # Input variable to view info in script output
	# Set to boolean to only run once for the given variable
	#_debug = False debug_view(=,repeat=False)
	#var_debug = False
	#debug_view(var=var,repeat=T/F)
	arg_list = kwargs.keys() # Python 2: kwargs.keys()  # Python 3: list(kwargs.keys())
	arg_list.remove('repeat')
	while not globals()[arg_list[0] + "_debug"]:
		write("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
		write("Debug info for {0}:".format(arg_list[0]))
		write("   Variable Type: {0}".format(type(kwargs[arg_list[0]])))
		write("   Assigned Value: {0}".format(kwargs[arg_list[0]]))
		write("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
		if not kwargs['repeat']:
			globals()[arg_list[0] + "_debug"] = True
		else:
			return

#-----------------------------------
def update_uid():
	uid_total = 0
	for fc in featureclass:
		if not get_count(fc):
			continue
		write("Searching {0} UIDs in {1} for bad or missing values.".format(get_count(fc), fc))
		uid_count = 0
		with ap.da.SearchCursor(fc, 'uid') as scursor:
			values = [srow[0] for srow in scursor]
		with ap.da.UpdateCursor(fc, 'uid') as ucursor:
			for urow in ucursor:
				if not populated(urow[0]):
					urow[0] = str(uuid.uuid4())
					uid_count += 1
				elif len(urow[0]) != 36: # 36 character random alphanumeric string
					urow[0] = str(uuid.uuid4()) # GOTOHELL-FUCK-COCK-PISS-MOTHERFUCKER and LEONARDO-EATS-FROG-EGGS-DISGUSTINGLY are valid XD
					uid_count += 1
				elif values.count(urow[0]) > 1:
					urow[0] = str(uuid.uuid4())
					uid_count += 1
				ucursor.updateRow(urow)
			if uid_count:
				write("Updated {0} MGCP UIDs in {1}".format(uid_count, fc))
			uid_total += uid_count
	ap.AddWarning("{0} invalid or missing UID values updated.".format(uid_total))
	return uid_total


''''''''' Parameters and Variables '''''''''
MGCP = ap.GetParameterAsText(0) # Get MGCP dataset
img_foot = ap.GetParameterAsText(1) # Get imagery footprint shapefile
run_fin_tool = ap.GetParameter(2) # Check you ran the MGCP Finishing Tool first.
#actual_sdv = ap.GetParameter(3) # Option to still use the hard work I put into indentifying and updating spatially accurate feature source dates
sdv_check = ap.GetParameter(3) # Update SDV from Imagery Footprint
# Geonames date: Database most recent update on: https://geonames.nga.mil/gns/html
geo_shp_check = ap.GetParameter(4) # Do you only have access to a Geonames shapefile in stead of a FC for some incredibly inconvenient reason?
geo_file = ap.GetParameterAsText(5)

if run_fin_tool == False:
	write("\n\n\n**********************************************************")
	write("Please run the MGCP Finishing Tool before Populate SDV and UID.")
	write("This will prevent NULL geometries from interfering with the SDV calculation.")
	write("**********************************************************\n\n\n")
	sys.exit(0)


ap.env.workspace = MGCP
workspace = ap.env.workspace
ap.env.overwriteOutput = True
ap.RefreshCatalog(MGCP)
featureclass = ap.ListFeatureClasses()
featureclass.sort()
error_event = 0


write("\nImporting Geonames Source data...")
geo_dates = []
# Searches through the Geonames file modify dates and creates a list in the YYYY-MM-DD format
geo_field_names = [f.name for f in ap.ListFields(geo_file)]

if 'mod_dt_nm' in geo_field_names:
	geo_field = 'mod_dt_nm'
	with ap.da.SearchCursor(geo_file, geo_field) as scursor:
		write("\nSearching Geonames feature class for date field.\nName: 'mod_dt_nm'\nAlias: 'Last Edited Date (name)'")
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
		write('\nSearching Geonames feature class for \'MODIFY_DATE\' field.')
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
			write('\nSearching Geonames shapefile for \'MODIFY_DAT\' field.')
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

# Find newest Geonames modify dates
geo_date_new = max(geo_dates)
write("Latest NGA GEOnet Names Server (GNS) database update date: {0}".format(geo_date_new))
error_event += ap.GetMaxSeverity()



''''''''' Update Spatial SDV Values '''''''''
sdv_fields = ['sdv', 'OID@', 'SHAPE@'] #Source Date Value(SDV) field and the true centroid token of each feature to find which footprint it mostly overlaps
fc_fields = ['acc', 'ccn', 'sdp', 'srt', 'txt', 'sdv']
img_fields = ['Acquisitio', 'SHAPE@'] #Acquisition date for the imagery footprint polygons and the shape token for comparisons


if sdv_check:
	for fc in featureclass:
		if not get_count(fc):
			continue

		write('\n== Searching {0} features for matching footprints. =='.format(fc))
		with ap.da.UpdateCursor(fc, sdv_fields) as ucursor: # ['sdv', 'OID@', 'SHAPE@']
			# For each feature in the feature class, blanket update the SDV field with the oldest imagery date cz fuck accuracy, we want consistency.
			count = 0
			unknown_err_list = []
			null_geom_list = []
			for urow in ucursor: # Iterate thru each feature in the fc
				# Checks shape for NULL geometries left over from Topology or bad data
				if urow[-1] is None:
					ap.AddError("*** WARNING ***")
					ap.AddError("NULL geometry found in {0} feature OID: {1}\nMake sure you have run the MGCP Finishing Tool.\nIf the problem persists, try running Repair Geometry manually and trying again.".format(fc, oid))
					null_geom_list.append(oid)
					continue
				sdv = urow[0]
				oid = urow[1]
				centroid = urow[-1].trueCentroid

				try:
					with ap.da.SearchCursor(img_foot, img_fields) as scursor: # ['Acquisitio', 'SHAPE@']
						for srow in scursor: # Iterate thru each imagery footprint polygon
							acquisition = srow[0]
							shape = srow[-1]
							if shape.contains(centroid): # If the current feature centroid is within this imagery footprint polygon
								cell_date = acquisition.strftime("%Y-%m-%d") # Assumes properly downloaded imagery footprint shapefile will have the Acquisition field as a date object
								if 'N_A' in sdv or not populated(sdv): # If the feature SDV field contains 'N_A' cz of some stupid analyst or is not populated
									urow[0] = cell_date
									count += 1
								elif populated(sdv): # If instead, the SDV field is populated with (hopefully) a date
									try:
										feat_date = dt.strptime(sdv, "%Y-%m-%d") # Parse what should be a text field in this format
										if acquisition > feat_date:
											urow[0] = cell_date
											count += 1
									except: # The SDV fild has some oddball value or an incorrectly formatted date. Fuck it. Overwrite it.
										urow[0] = cell_date
										count += 1
										continue
				except:
					# If SDV is NULL or incorrect format, skip to next feature
					ap.AddError("Encountered a problem while applying the Imagery Footprint acquisition date to {0} feature OID: {1}. Possibly a NULL value in the imagery acquisition date or NULL geometry or attribute in the feature.\nPlease check the validity of the Imagery Footprint and try again.\n**If this problem persists, you may have to manually attribute the SDV of the {0} feature. Please attribute it with the oldest Acquisition field date in the Imagery Footprint that intersects it.".format(fc, oid))
					unknown_err_list.append(oid)
					continue

				ucursor.updateRow(urow)

		if count > 0:
			write('\nUpdated {0} SDV dates in {1}.'.format(count, fc))
		if len(unknown_err_list) > 0:
			ap.AddError("\n*** WARNING ***")
			ap.AddError("These {0} features failed to have their SDV updated. Further manual investigation may be required.\nCheck the Imagery Footprint Acquisition field and the individual feature attribute fields and geometry.".format(fc))
			ap.AddError(unknown_err_list)
		if len(null_geom_list) > 0:
			ap.AddError("\n*** WARNING ***")
			ap.AddError("These {0} features were flagged as having NULL geometry. If Repair Geometry has not fixed them, further manual investigation may be required.".format(fc))
			ap.AddError(null_geom_list)
		error_event += ap.GetMaxSeverity()


''''''''' Update UFI Values '''''''''
# Iterate through all features and update the uid field with uuid4 random values
# uidcount = 0
# for fc in featureclass:
# 	feat_count = int(ap.GetCount_management(fc).getOutput(0))
# 	if feat_count == 0:
# 		continue
# 	try:
# 		with ap.da.SearchCursor(fc, 'uid') as scursor:
# 			values = [row[0] for row in scursor]
# 		with ap.da.UpdateCursor(fc, 'uid') as ucursor:
# 			for row in ucursor:
# 				if not populated(row[0]):
# 					row[0] = str(uuid.uuid4())
# 					uidcount += 1
# 				elif values.count(row[0]) > 1:
# 					row[0] = str(uuid.uuid4())
# 					uidcount += 1
# 				ucursor.updateRow(row)
# 			write("Updated {0} MGCP UIDs in {1}".format(uidcount, fc))
# 	except ap.ExecuteError:
# 		# if the code failed for the current fc, check the error
# 		error_count += 1
# 		ap.AddError("\n***Failed to run {0}.***\n".format(tool_name))
# 		ap.AddError("Error Report:")
# 		ap.AddError("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
# 		ap.AddError(ap.GetMessages())
# 		ap.AddError("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
# 		ap.AddError("\nPlease rerun the tool, but uncheck the {0} tool option. Either the feature class is too big or something else has gone wrong. Large data handling for tools other than Integration will be coming in a future update.".format(tool_name))
# 		ap.AddError("Exiting tool.\n")
# 		continue
# 	error_event += ap.GetMaxSeverity()
uid_total = 0
uid_total = update_uid()


''''''''' Populate Feature Metadata '''''''''
acc = 1 # If not already
ccn = r"Copyright 2014 by the National Geospatial-Intelligence Agency, U.S. Government.  No domestic copyright claimed under Title 17 U.S.C. All rights reserved."
sdp = "Very High Resolution Commercial Monoscopic Imagery"
srt = 110
txt = 'N_A' # Unless populated
for fc in featureclass:
	#write("Assigning {0} metadata to {1} feature class.".format(sdp, fc))
	# fc_fields = ['acc', 'ccn', 'sdp', 'srt', 'txt', 'sdv']
	with ap.da.UpdateCursor(fc, fc_fields) as ucursor:
		for urow in ucursor:
			if not populated(urow[0]):
				urow[0] = acc
			urow[1] = ccn
			urow[2] = sdp
			urow[3] = srt
			if not populated(urow[4]):
				urow[4] = txt
			if 'TextP' in fc:
				urow[2] = "GeoNames"
				urow[3] = 25
				urow[5] = geo_date_new
			ucursor.updateRow(urow)



write("\n\nUpdated feature SDV fields based on their spatial relation with the oldest respective, adjacent Imagery Footprint acquisition dates.")
write("All feature UID values have been updated.")
write("Feature level metadata populated for {0}.\n\n".format(fc_fields))
if error_event >= 2:
	ap.AddError("\n*** Something has gone wrong in the tool. Please read through the outputs above to see what happened. ***\n")





### Trash Pile ###


# if actual_sdv: #Deprecated unfortunately. Needs refactoring.
# 	''''''''' Footprint Search and Update '''''''''
# 	for fc in featureclass:
# 		ap.MakeTableView_management(fc, "fc_table")
# 		feat_count = int(ap.GetCount_management("fc_table").getOutput(0))
# 		write('\n== Searching {0} {1} features for matching footprints. =='.format(feat_count, fc))
#
# 		with ap.da.UpdateCursor(fc, fc_fields) as fcu:
# 			# For each feature in the feature class, make a search cursor based on the imagery footprint shape and acquisition date
# 			count = 0
# 			for feat in fcu:
# 				# Checks shape for NULL geometries left over from Topology
# 				if str(type(feat[1])) == r"<type 'NoneType'>":
# 					write("*** WARNING ***")
# 					write('NULL geometry found in ' + str(fc) + '. Make sure you have run the MGCP Finishing Tool.\nIf the problem persists, try running Repair Geometry manually and trying again.')
# 					sys.exit(0)
# 				# Get the centroid of the current feature
# 				centroid = feat[1].trueCentroid
# 				with ap.da.SearchCursor(img_foot, img_fields) as img:
# 					# For each polygon in the imagery footprint, check if it contains the centroid of the current feature
# 					for cell in img:
# 						if cell[1].contains(centroid):
# 							# Convert the Aquisition field of the footprint polygon and the SDV field of the current feature to a datetime variable for comparison
# 							try:
# 								# The imagery footprint Acquisitio field seems to function as a typecast datetime variable
# 								try:
# 									feat_date = dt.strptime(feat[0], "%Y-%m-%d")
# 									# If the feature centroid is within this footprint polygon AND the aquisition date is newer than the sdv of the feature,
# 									# convert the acquisition date to the sdv yyyy-mm-dd format and update the sdv
# 									if cell[0] > feat_date:
# 										cell_date = cell[0].strftime("%Y-%m-%d")
# 										feat[0] = cell_date
# 										count += 1
# 								except:
# 									# If SDV is NULL or incorrect format, skip logic and populate SDV with formatted acquisition date
# 									cell_date = cell[0].strftime("%Y-%m-%d")
# 									feat[0] = cell_date
# 									count += 1
# 							except:
# 								write('=== Error: HE_dl_f411 ===\nCheck that the imagery footprint was retrieved correctly and has the proper datetime Acquisition field values.')
# 				# Run this for an entire feature class and then update the values
# 				fcu.updateRow(feat)
#
# 		if count > 0:
# 			write('\nUpdated {0} SDV dates in {1}.'.format(count, fc))
#
#  # Need to impliment sdv value sanitation
# else:
# 	''''''''' Blanket Feature Update Based on Absolutely Nothing '''''''''
# 	for fc in featureclass:
# 		feat_count = int(ap.GetCount_management(fc).getOutput(0))
# 		if feat_count == 0:
# 			continue
#
# 		write('\n== Searching {0} {1} features for matching footprints. =='.format(feat_count, fc))
# 		img_dates = []
# 		# Searches through Imagery Footprint dates and creates a list in the YYYY-MM-DD format
# 		with ap.da.SearchCursor(img_foot, 'Acquisitio') as img:
# 			for row in img:
# 				date = row[0].strftime("%Y-%m-%d") # The imagery footprint Acquisition field seems to function as a typecast datetime variable
# 				img_dates.append(date)
# 		# Get newest and oldest imagery footprint dates
# 		img_date_new = max(img_dates)
# 		img_date_old = min(img_dates) # Harris means oldest when they say "earliest". What a failing of a word in the english language.
# 		img_date_old_debug = False
#
# 		with ap.da.UpdateCursor(fc, sdv_fields) as fcu:
# 			# For each feature in the feature class, blanket update the SDV field with the oldest imagery date cz fuck accuracy, we want consistency.
# 			count = 0
# 			unknown_err_list = []
# 			null_geom_list = []
# 			for feat in fcu:
# 				# Checks shape for NULL geometries left over from Topology or bad data
# 				sdv = feat[0]
# 				shape = feat[1]
# 				oid = feat[2]
# 				try:
# 					if shape is None: #if str(type(feat[1])) == r"<type 'NoneType'>":
# 						write("*** WARNING ***")
# 						write("NULL geometry found in {0} feature OID: {1}\nMake sure you have run the MGCP Finishing Tool.\nIf the problem persists, try running Repair Geometry manually and trying again.".format(fc, oid))
# 						null_geom_list.append(oid)
# 						continue
# 					elif not populated(sdv):
# 						feat[0] = img_date_old
# 						count += 1
# 					elif sdv == 'N_A':
# 						feat[0] = img_date_old
# 						count += 1
# 					elif populated(sdv):
# 						if type(sdv) == str: #if str(type(feat[0])) == r"<type 'str'>":
# 							feat[0] = img_date_old
# 							count += 1
# 						if type(sdv) == unicode:
# 							feat[0] = img_date_old
# 							count += 1
# 				except:
# 					# If SDV is NULL or incorrect format, skip to next feature
# 					write("Encountered a problem while applying the Imagery Footprint acquisition date to {0} feature OID: {1}. Possibly a NULL value in the imagery acquisition date or NULL geometry or attribute in the feature.\nPlease check the validity of the Imagery Footprint and try again.\n**If this problem persists, you may have to manually attribute the SDV of the {0} feature. Please attribute it with the oldest Acquisition field date in the Imagery Footprint.".format(fc, oid))
# 					unknown_err_list.append(oid)
# 					continue
# 				fcu.updateRow(feat)
#
# 		if count > 0:
# 			write('\nUpdated {0} SDV dates in {1}.'.format(count, fc))
# 		if len(unknown_err_list) > 0:
# 			write("\n*** WARNING ***")
# 			write("These {0} features failed to have their SDV updated. Further manual investigation may be required.\nCheck the Imagery Footprint Acquisition field and the individual feature attribute fields and geometry.".format(fc))
# 			write(unknown_err_list)
# 		if len(null_geom_list) > 0:
# 			write("\n*** WARNING ***")
# 			write("These {0} features were flagged as having NULL geometry. If Repair Geometry has not fixed them, further manual investigation may be required.".format(fc))
# 			write(null_geom_list)

# if 'TextP' in fc:
# 	sdp = "GeoNames"
# 	srt = 25
# 	write("**Assigning {0} metadata to {1} feature class for Named Location Points.".format(sdp, fc))
# 	with ap.da.UpdateCursor(fc, fc_fields) as ucursor:
# 		for urow in ucursor:
# 			if urow[0] != 1:
# 				urow[0] = acc
# 			urow[1] = ccn
# 			urow[2] = sdp
# 			urow[3] = srt
# 			if not populated(urow[4]):
# 				urow[4] = txt
# 			if geo_check:
# 				urow[5] = geo_date_new
# 			ucursor.updateRow(urow)
# 	continue

# img_dates = []
# # Searches through Imagery Footprint dates and creates a list in the YYYY-MM-DD format
# with ap.da.SearchCursor(img_foot, 'Acquisitio') as scursor:
# 	for srow in scursor:
# 		date = srow[0].strftime("%Y-%m-%d") # The imagery footprint Acquisition field seems to function as a typecast datetime variable
# 		img_dates.append(date)
# # Get oldest imagery footprint dates
# img_date_old = min(img_dates) # Harris means oldest when they say "earliest". What a failing of a word in the english language.



# else:
# 	''''''''' Blanket Feature Update Based on Absolutely Nothing '''''''''
# 	# count_dot_debug = False
# 	# count_dot_out_debug = False
# 	# count_dot_raw_debug = False
# 	# count_under_debug = False
# 	# count_under_out_debug = False
# 	# count_under_raw_debug = False
# 	for fc in featureclass:
# 		# count_dot = int(ap.management.GetCount(fc).getOutput(0))
# 		# debug_view(count_dot=count_dot, repeat=False)
# 		# count_dot_out = ap.management.GetCount(fc).getOutput(0)
# 		# debug_view(count_dot_out=count_dot_out, repeat=False)
# 		# count_dot_raw = ap.management.GetCount(fc)
# 		# debug_view(count_dot_raw=count_dot_raw, repeat=False)
# 		# count_under = int(ap.GetCount_management(fc).getOutput(0)) # Method I use
# 		# debug_view(count_under=count_under, repeat=False)
# 		# count_under_out = ap.GetCount_management(fc).getOutput(0)
# 		# debug_view(count_under_out=count_under_out, repeat=False)
# 		# count_under_raw = ap.GetCount_management(fc) # John's method. does this only work with layers? Or can it print a number but can't be used as an int var
# 		# debug_view(count_under_raw=count_under_raw, repeat=False)
# 		feat_count = int(ap.GetCount_management(fc).getOutput(0))
# 		if feat_count == 0:
# 			continue
#
# 		write('\n== Searching {0} {1} features for matching footprints. =='.format(feat_count, fc))
# 		img_dates = []
# 		# Searches through Imagery Footprint dates and creates a list in the YYYY-MM-DD format
# 		with ap.da.SearchCursor(img_foot, 'Acquisitio') as img:
# 			#acq_date_debug = False
# 			for row in img:
# 				#acq_date = row[0]
# 				#debug_view(acq_date=acq_date,repeat=False)
# 				date = row[0].strftime("%Y-%m-%d") # The imagery footprint Acquisition field seems to function as a typecast datetime variable
# 				img_dates.append(date)
# 		# Get newest and oldest imagery footprint dates
# 		img_date_new = max(img_dates)
# 		img_date_old = min(img_dates) # Harris means oldest when they say "earliest". What a failing of a word in the english language.
# 		img_date_old_debug = False
# 		#debug_view(img_date_old=img_date_old,repeat=False)
#
# 		with ap.da.UpdateCursor(fc, fc_fields) as fcu:
# 			# For each feature in the feature class, blanket update the SDV field with the oldest imagery date cz fuck accuracy, we want consistency.
# 			count = 0
# 			unknown_err_list = []
# 			null_geom_list = []
# 			#feat_parse_debug = False
# 			#feat_date_debug = False
# 			#sdv_debug = False
# 			#shape_debug = False
# 			#oid_debug = False
# 			for feat in fcu:
# 				# Checks shape for NULL geometries left over from Topology or bad data
# 				sdv = feat[0]
# 				shape = feat[1]
# 				oid = feat[2]
# 				#debug_view(sdv=sdv,repeat=False)
# 				#debug_view(shape=shape,repeat=False)
# 				#debug_view(oid=oid,repeat=False)
# 				try:
# 					if shape is None: #if str(type(feat[1])) == r"<type 'NoneType'>":
# 						write("*** WARNING ***")
# 						write("NULL geometry found in {0} feature OID: {1}\nMake sure you have run the MGCP Finishing Tool.\nIf the problem persists, try running Repair Geometry manually and trying again.".format(fc, oid))
# 						null_geom_list.append(oid)
# 						continue
# 					elif not populated(sdv):
# 						#write("Current SDV not populated")
# 						feat[0] = img_date_old
# 						count += 1
# 					elif sdv == 'N_A':
# 						#write("Current SDV is N_A")
# 						feat[0] = img_date_old
# 						count += 1
# 					elif populated(sdv):
# 						if type(sdv) == str: #if str(type(feat[0])) == r"<type 'str'>":
# 							#write("Current SDV is string: {0}".format(sdv))
# 							feat[0] = img_date_old
# 							count += 1
# 						if type(sdv) == unicode:
# 							#write("Current SDV is unicode: {0}".format(sdv))
#
# 					# feat_parse = dt.strptime(feat[0], "%Y-%m-%d")
# 					# debug_view(feat_parse=feat_parse,repeat=False)
# 					# feat_date = feat_parse.strftime("%Y-%m-%d")
# 					# debug_view(feat_date=feat_date,repeat=False)
#
# 					# if type(test_string) == str:
# 					# 	write("set feat[0] string to img_date_old string")
# 					# else:
# 					# 	write(type(feat[0]))
#
# 					# elif img_date_old < feat_date:
# 					# 	#img_date_old = dt.strptime(img_date_old, '%Y-%m-%d')
# 					# 	#feat_date = dt.strptime(feat[0], "%Y-%m-%d")
# 					# 	#feat_date = feat[0].strftime("%Y-%m-%d")
# 					# 	feat[0] = img_date_old
# 					# 	count += 1
# 					# else:
# 					# 	continue
# 				except:
# 					# If SDV is NULL or incorrect format, skip to next feature
# 					write("Encountered a problem while applying the Imagery Footprint acquisition date to {0} feature OID: {1}. Possibly a NULL value in the imagery acquisition date or NULL geometry or attribute in the feature.\nPlease check the validity of the Imagery Footprint and try again.\n**If this problem persists, you may have to manually attribute the SDV of the {0} feature. Please attribute it with the oldest Acquisition field date in the Imagery Footprint.".format(fc, oid))
# 					unknown_err_list.append(oid)
# 					continue
# 				fcu.updateRow(feat)
#
# 		if count > 0:
# 			write('\nUpdated {0} SDV dates in {1}.'.format(count, fc))
# 		if len(unknown_err_list) > 0:
# 			write("\n*** WARNING ***")
# 			write("These {0} features failed to have their SDV updated. Further manual investigation may be required.\nCheck the Imagery Footprint Acquisition field and the individual feature attribute fields and geometry.".format(fc))
# 			write(unknown_err_list)
# 		if len(null_geom_list) > 0:
# 			write("\n*** WARNING ***")
# 			write("These {0} features were flagged as having NULL geometry. If Repair Geometry has not fixed them, further manual investigation may be required.".format(fc))
# 			write(null_geom_list)
#
#
# ''''''''' Populate UID '''''''''
# # Iterate through all features and update the uid field with uuid4 random values
# with ap.da.UpdateCursor(fc, 'uid') as ucursor:
# 	idcount = 0
# 	for row in ucursor:
# 		row[0] = str(uuid.uuid4())
# 		ucursor.updateRow(row)
# 		idcount += 1
# 	if idcount > 0:
# 		write('\nUpdated {0} MGCP UIDs in {1}.'.format(idcount, fc))



##fc = 'AerofacA'
##write('Searching footprint polygons matching ' + fc + ' features.')
##with ap.da.UpdateCursor(fc, fc_fields) as fcu:
##    # For each feature in the feature class, make a search cursor based on the imagery footprint shape and acquisition date
##    count = 0
##    for feat in fcu:
##        # While SHAPE@ is a geometry object, SHAPE@TRUECENTROID is just a tuple of x,y coordinates.
##        # So the great, almighty ArcMap can't figure out that x,y coordinates are a point unless explicitly told on the most basic level
##        # So we have to break every thing down just to go through the pain of making a variable of the tuple to make the coordinates
##        # to make the point to make the point geometry of the centroid to just see if it is in the damn square
##        centroid = feat[1].trueCentroid
##        with ap.da.SearchCursor(img_foot, img_fields) as img:
##            # For each polygon in the imagery footprint, check if it contains the centroid of the current feature
##            for cell in img:
##                if cell[1].contains(centroid):
##                    # Convert the Aquisition field of the footprint polygon and the SDV field of the current feature to a datetime variable for comparison
##                    try:
##                        write('cell[0]:')
##                        write(cell[0])
##                        try:
##                            write('== try branch ==')
##                            write('parsing feat[0]...')
##                            #write(str(feat[0]))
##                            feat_date = dt.strptime(feat[0], "%Y-%m-%d")
##                            #feat_date = feat_date.strftime("%Y-%m-%d")
##                            write('feat_date parsed:')
##                            write(feat_date)
##                            # If the feature centroid is within this footprint polygon AND the aquisition date is newer than the sdv of the feature,
##                            # convert the acquisition date to the sdv yyyy-mm-dd format and update the sdv
##                            if cell[0] > feat_date:
##                                write('\n')
##                                write('if')
##                                write(cell[0])
##                                write('>')
##                                write(feat_date)
##                                write('\n')
##                                cell_date = cell[0].strftime("%Y-%m-%d")
##                                write('cell_date formatted:')
##                                write(cell_date)
##                                feat[0] = cell_date
##                                write('feat[0] updated:')
##                                write(feat[0])
##                        except:
##                            # If SDV is NULL or incorrect format, skip logic and populate SDV with formatted acquisition date
##                            write('== except branch ==')
##                            cell_date = cell[0].strftime("%Y-%m-%d")
##                            write('cell_date formatted:')
##                            write(cell_date)
##                            feat[0] = cell_date
##                            write('feat[0] updated:')
##                            write(feat[0])
##                    except:
##                        write('===Unknown failure. Check imagery footprint, Acquisition field values, and local database SDV for NULLs or formatting errors.===')
##        # Run this for an entire feature class and then update the values
##        count += 1
##        write('Updating ' + str(count) + ' SDV values in ' + fc + '.')
##        fcu.updateRow(feat)
##        write('feat[0] updated:')
##        write(feat[0])
##        write('next feature -->\n\n\n')


# str() takes the mm/dd/yyyy format from the imagery footprint and converts it to
# a string formatted as 'yyyy-mm-dd hh:mm:ss(all 0)'
#cell_str = str(cell[0])
# The datetime string parser format argument must match the string converted format above
# Yet it create a datetime object with the format mm/dd/yyyy
#cell_date = dt.strptime(cell_str, "%Y-%m-%d %H:%M:%S")
#write('cell_str = str(cell[0]):')
#write(cell_str)
#write('cell_date = dt.strptime(cell_str, "%Y-%m-%d %H:%M:%S"):')
#write(cell_date)


### For each feature class, make an update cursor based on the sdv field and each feature's centroid
##fc = 'AerofacA'
##write('Searching footprint polygons matching ' + fc + ' features.')
##with ap.da.UpdateCursor(fc, fc_fields) as fcu:
##    # For each feature in the feature class, make a search cursor based on the imagery footprint shape and acquisition date
##    feat_count = 0
##    for feat in fcu:
##        feat_count += 1
##        write('====Beginning feature number ' + str(feat_count) + ' ====')
##        # While SHAPE@ is a geometry object, SHAPE@TRUECENTROID is just a tuple of x,y coordinates.
##        # So the great, almighty ArcMap can't figure out that x,y coordinates are a point unless explicitly told on the most basic level
##        # So we have to break every thing down just to go through the pain of making a variable of the tuple to make the coordinates
##        # to make the point to make the point geometry of the centroid to just see if it is in the damn square
##        write('FEAT')
##        write(feat)
##        write('SDV:')
##        write(feat[0])
##        write('SHAPE@ field:')
##        write(feat[1])
##        write('Centroid breakdown to point geometry')
##        #coord = feat[1]
##        #write(coord)
##        #x = coord[0]
##        #write("{0:.15f}".format(x))
##        #y = coord[1]
##        #write("{0:.15f}".format(y))
##        #centroid = ap.PointGeometry(ap.Point(x,y))
##        shape = feat[1].trueCentroid
##        write(str(shape))
##        with ap.da.SearchCursor(img_foot, img_fields) as img:
##            # For each polygon in the imagery footprint, check if it contains the centroid of the current feature
##            write(img)
##            for cell in img:
##                write('CELL')
##                write(cell)
##                write('Acquisition Date:')
##                write(cell[0])
##                write('SHAPE@ field:')
##                write(cell[1])
##                if cell[1].contains(centroid):
##                    write('cell contains centroid')
##                    # Convert the Aquisition field of the footprint polygon and the SDV field of the current feature to a datetime variable for comparison
##                    try:
##                        try:
##                            cell_date = dt.strptime(cell[0], "%m/%d/%Y")
##                        except:
##                            write('===Incorrect date format in Imagery Footprint. Please check it was downloaded correctly from the source package ID.===')
##                        try:
##                            feat_date = dt.strptime(feat[0], "%Y-%m-%d")
##                            # If the feature centroid is within this footprint polygon AND the aquisition date is newer than the sdv of the feature,
##                            # convert the acquisition date to the sdv yyyy-mm-dd format and update the sdv
##                            if cell_date > feat_date:
##                                write(cell_date)
##                                cell_date = cell_date.strftime("%Y-%m-%d")
##                                feat[0] = cell_date
##                        except:
##                            # If SDV is NULL or incorrect format, skip logic and populate SDV with formatted acquisition date
##                            cell_date = cell_date.strftime("%Y-%m-%d")
##                            write('skipped feat_date try:')
##                            write(cell_date)
##                            feat[0] = cell_date
##                    except:
##                        write('===Unknown failure. Check imagery footprint, Acquisition field values, and local database SDV for NULLs or formatting errors.===')
##        # Run this for an entire feature class and then update the values
##        #write('Updating ' + str(feat_count) + ' SDV values in ' + fc + '.')
##        write('====End of feature number ' + str(feat_count) + ' ====')
##        fcu.updateRow(feat)
##        time.sleep(0.25)


##cursor = ap.da.SearchCursor(input_fc, "SHAPE@XY")
##centroid_coords = []
##for feature in cursor:
##    centroid_coords.append(feature[0])
##
##point = ap.Point()
##pointGeometryList = []
##
##for pt in centroid_coords:
##    point.X = pt[0]
##    point.Y = pt[1]
##
##    pointGeometry = ap.PointGeometry(point)
##    pointGeometryList.append(pointGeometry)


### For each feature class, make an update cursor based on the sdv field and each feature's centroid
##for fc in featureclass:
##    write('Searching footprint polygons matching ' + fc + ' features.')
##    with ap.da.UpdateCursor(fc, fc_fields) as fcu:
##        # For each feature in the feature class, make a search cursor based on the imagery footprint shape and acquisition date
##        count = 0
##        for feat in fcu:
##            # While SHAPE@ is a geometry object, SHAPE@TRUECENTROID is just a tuple of x,y coordinates.
##            # So the great, almighty ArcMap can't figure out that x,y coordinates are a point unless explicitly told on the most basic level
##            # So we have to break every thing down just to go through the pain of making a variable of the tuple to make the coordinates
##            # to make the point to make the point geometry of the centroid to just see if it is in the damn square
##            coord = feat[1]
##            x = coord[0]
##            y = coord[1]
##            centroid = ap.PointGeometry(ap.Point(x,y))
##            with ap.da.SearchCursor(img_foot, img_fields) as img:
##                # For each polygon in the imagery footprint, check if it contains the centroid of the current feature
##                for cell in img:
##                    write(cell[0])
##                    write(cell[1])
##                    if cell[1].contains(centroid):
##                        write('cell contains centroid')
##                        # Convert the Aquisition field of the footprint polygon and the SDV field of the current feature to a datetime variable for comparison
##                        try:
##                            try:
##                                cell_date = dt.strptime(cell[0], "%m/%d/%Y")
##                            except:
##                                write('===Incorrect date format in Imagery Footprint. Please check it was downloaded correctly from the source package ID.===')
##                            try:
##                                feat_date = dt.strptime(feat[0], "%Y-%m-%d")
##                                # If the feature centroid is within this footprint polygon AND the aquisition date is newer than the sdv of the feature,
##                                # convert the acquisition date to the sdv yyyy-mm-dd format and update the sdv
##                                if cell_date > feat_date:
##                                    write(cell_date)
##                                    cell_date = cell_date.strftime("%Y-%m-%d")
##                                    feat[0] = cell_date
##                            except:
##                                # If SDV is NULL or incorrect format, skip logic and populate SDV with formatted acquisition date
##                                cell_date = cell_date.strftime("%Y-%m-%d")
##                                write('skipped feat_date try:')
##                                write(cell_date)
##                                feat[0] = cell_date
##                        except:
##                            write('===Unknown failure. Check imagery footprint, Acquisition field values, and local database SDV for NULLs or formatting errors.===')
##            # Run this for an entire feature class and then update the values
##            count += 1
##            write('Updating ' + str(count) + ' SDV values in ' + fc + '.')
##            fcu.updateRow(feat)



#point = ap.Point(25282, 43770)
#ptGeometry = ap.PointGeometry(point)

##lyr_dict = {}
##for x in range(1, int(getfeaturecount(img_footprint))):
##    lyr_dict["strip{0}".format(x)] = ""

##cell = "7/7/2021"
##feat = ""
##print('Original values:')
##print(cell)
##print(feat)
##print('\n')
##
##
##try:
##
##   try:
##      print('Parsing cell date')
##      cell_date = dt.strptime(cell, "%m/%d/%Y")
##   except:
##      print('Incorrect date format in Imagery Footprint. Please check it was downloaded correctly from the source package ID.')
##
##   try:
##      print('Parsing feature date')
##      feat_date = dt.strptime(feat, "%Y-%m-%d")
##      print('\n')
##
##      print('Parsed variables:')
##      print(cell_date)
##      print(feat_date)
##      print('\n')
##
##      print('Formatting cell date and feature date')
##      cell_date = cell_date.strftime("%Y-%m-%d")
##      feat_date = feat_date.strftime("%Y-%m-%d")
##      print('\n')
##
##      print('Formatted variables:')
##      print(cell_date)
##      print(feat_date)
##      print('\n')
##
##      if cell_date > feat_date:
##         feat = cell_date
##         print('Cell date greater, feature SDV replaced.')
##         print(cell)
##         print(feat)
##      else:
##         print('Feature up to date.')
##         print(cell)
##         print(feat)
##   except:
##      print('Feature SDV field is NULL value. Skipping to formatted replacement.')
##      cell_date = cell_date.strftime("%Y-%m-%d")
##      feat = cell_date
##      print('\n')
##
##      print('Updated NULL SDV variable:')
##      print(cell)
##      print(feat)
##
##except:
##   print('Unknown failure. Check imagery footprint Acquisition values and local database SDV for NULLs or errors')
##
##
