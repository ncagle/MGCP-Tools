# ======================= #
# Populate SDV and UID v5 #
# Nat Cagle 2022-02-15    #
# ======================= #
import arcpy
from arcpy import AddMessage as write
from datetime import datetime
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



''''''''' Parameters and Variables '''''''''
MGCP = arcpy.GetParameterAsText(0) # Get MGCP dataset
img_foot = arcpy.GetParameterAsText(1) # Get imagery footprint shapefile
run_fin_tool = arcpy.GetParameter(2) # Check you ran the MGCP Finishing Tool first.
actual_sdv = arcpy.GetParameter(3) # Option to still use the hard work I put into indentifying and updating spatially accurate feature source dates

if run_fin_tool == False:
	write("Please run the MGCP Finishing Tool before Populate SDV and UID.")
	write("This will prevent NULL geometries from interfering with the SDV calculation.")
	sys.exit(0)

arcpy.env.workspace = MGCP
workspace = arcpy.env.workspace
arcpy.env.overwriteOutput = True
featureclass = arcpy.ListFeatureClasses()
featureclass.sort()

fc_fields = ['sdv', 'SHAPE@', 'OID@'] #Source Date Value(SDV) field and the true centroid token of each feature to find which footprint it mostly overlaps
img_fields = ['Acquisitio', 'SHAPE@'] #Acquisition date for the imagery footprint polygons and the shape token for comparisons

populated = lambda x: x is not None and str(x).strip() != '' # Finds empty fields.

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

if actual_sdv:
	''''''''' Footprint Search and Update '''''''''
	for fc in featureclass:
		arcpy.MakeTableView_management(fc, "fc_table")
		feat_count = int(arcpy.GetCount_management("fc_table").getOutput(0))
		write('\n== Searching {0} {1} features for matching footprints. =='.format(feat_count, fc))

		with arcpy.da.UpdateCursor(fc, fc_fields) as fcu:
			# For each feature in the feature class, make a search cursor based on the imagery footprint shape and acquisition date
			count = 0
			for feat in fcu:
				# Checks shape for NULL geometries left over from Topology
				if str(type(feat[1])) == r"<type 'NoneType'>":
					write("*** WARNING ***")
					write('NULL geometry found in ' + str(fc) + '. Make sure you have run the MGCP Finishing Tool.\nIf the problem persists, try running Repair Geometry manually and trying again.')
					sys.exit(0)
				# Get the centroid of the current feature
				centroid = feat[1].trueCentroid
				with arcpy.da.SearchCursor(img_foot, img_fields) as img:
					# For each polygon in the imagery footprint, check if it contains the centroid of the current feature
					for cell in img:
						if cell[1].contains(centroid):
							# Convert the Aquisition field of the footprint polygon and the SDV field of the current feature to a datetime variable for comparison
							try:
								# The imagery footprint Acquisitio field seems to function as a typecast datetime variable
								try:
									feat_date = datetime.strptime(feat[0], "%Y-%m-%d")
									# If the feature centroid is within this footprint polygon AND the aquisition date is newer than the sdv of the feature,
									# convert the acquisition date to the sdv yyyy-mm-dd format and update the sdv
									if cell[0] > feat_date:
										cell_date = cell[0].strftime("%Y-%m-%d")
										feat[0] = cell_date
										count += 1
								except:
									# If SDV is NULL or incorrect format, skip logic and populate SDV with formatted acquisition date
									cell_date = cell[0].strftime("%Y-%m-%d")
									feat[0] = cell_date
									count += 1
							except:
								write('=== Error: HE_dl_f411 ===\nCheck that the imagery footprint was retrieved correctly and has the proper datetime Acquisition field values.')
				# Run this for an entire feature class and then update the values
				fcu.updateRow(feat)

		if count > 0:
			write('\nUpdated {0} SDV dates in {1}.'.format(count, fc))

 # Need to impliment sdv value sanitation
else:
	''''''''' Blanket Feature Update Based on Absolutely Nothing '''''''''
	for fc in featureclass:
		feat_count = int(arcpy.GetCount_management(fc).getOutput(0))
		if feat_count == 0:
			continue

		write('\n== Searching {0} {1} features for matching footprints. =='.format(feat_count, fc))
		img_dates = []
		# Searches through Imagery Footprint dates and creates a list in the YYYY-MM-DD format
		with arcpy.da.SearchCursor(img_foot, 'Acquisitio') as img:
			for row in img:
				date = row[0].strftime("%Y-%m-%d") # The imagery footprint Acquisition field seems to function as a typecast datetime variable
				img_dates.append(date)
		# Get newest and oldest imagery footprint dates
		img_date_new = max(img_dates)
		img_date_old = min(img_dates) # Harris means oldest when they say "earliest". What a failing of a word in the english language.
		img_date_old_debug = False

		with arcpy.da.UpdateCursor(fc, fc_fields) as fcu:
			# For each feature in the feature class, blanket update the SDV field with the oldest imagery date cz fuck accuracy, we want consistency.
			count = 0
			unknown_err_list = []
			null_geom_list = []
			for feat in fcu:
				# Checks shape for NULL geometries left over from Topology or bad data
				sdv = feat[0]
				shape = feat[1]
				oid = feat[2]
				try:
					if shape is None: #if str(type(feat[1])) == r"<type 'NoneType'>":
						write("*** WARNING ***")
						write("NULL geometry found in {0} feature OID: {1}\nMake sure you have run the MGCP Finishing Tool.\nIf the problem persists, try running Repair Geometry manually and trying again.".format(fc, oid))
						null_geom_list.append(oid)
						continue
					elif not populated(sdv):
						feat[0] = img_date_old
						count += 1
					elif sdv == 'N_A':
						feat[0] = img_date_old
						count += 1
					elif populated(sdv):
						if type(sdv) == str: #if str(type(feat[0])) == r"<type 'str'>":
							feat[0] = img_date_old
							count += 1
						if type(sdv) == unicode:
							feat[0] = img_date_old
							count += 1
				except:
					# If SDV is NULL or incorrect format, skip to next feature
					write("Encountered a problem while applying the Imagery Footprint acquisition date to {0} feature OID: {1}. Possibly a NULL value in the imagery acquisition date or NULL geometry or attribute in the feature.\nPlease check the validity of the Imagery Footprint and try again.\n**If this problem persists, you may have to manually attribute the SDV of the {0} feature. Please attribute it with the oldest Acquisition field date in the Imagery Footprint.".format(fc, oid))
					unknown_err_list.append(oid)
					continue
				fcu.updateRow(feat)

		if count > 0:
			write('\nUpdated {0} SDV dates in {1}.'.format(count, fc))
		if len(unknown_err_list) > 0:
			write("\n*** WARNING ***")
			write("These {0} features failed to have their SDV updated. Further manual investigation may be required.\nCheck the Imagery Footprint Acquisition field and the individual feature attribute fields and geometry.".format(fc))
			write(unknown_err_list)
		if len(null_geom_list) > 0:
			write("\n*** WARNING ***")
			write("These {0} features were flagged as having NULL geometry. If Repair Geometry has not fixed them, further manual investigation may be required.".format(fc))
			write(null_geom_list)



''''''''' Update UFI Values '''''''''
# Iterate through all features and update the uid field with uuid4 random values
uidcount = 0
# Explicit is better than implicit
# Lambda function works better than "if not fieldname:", which can falsely catch 0.
populated = lambda x: x is not None and str(x).strip() != '' # Function that returns boolean of if input field is populated or empty

for fc in featureclass:
	feat_count = int(arcpy.GetCount_management(fc).getOutput(0))
	if feat_count == 0:
		continue
	try:
		with arcpy.da.SearchCursor(fc, 'uid') as scursor:
			values = [row[0] for row in scursor]
		with arcpy.da.UpdateCursor(fc, 'uid') as ucursor:
			for row in ucursor:
				if not populated(row[0]):
					row[0] = str(uuid.uuid4())
					uidcount += 1
				elif values.count(row[0]) > 1:
					row[0] = str(uuid.uuid4())
					uidcount += 1
				ucursor.updateRow(row)
			write("Updated {0} MGCP UIDs in {1}".format(uidcount, fc))
	except arcpy.ExecuteError:
		# if the code failed for the current fc, check the error
		error_count += 1
		write("\n***Failed to run {0}.***\n".format(tool_name))
		write("Error Report:")
		write("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
		write(arcpy.GetMessages())
		write("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
		write("\nPlease rerun the tool, but uncheck the {0} tool option. Either the feature class is too big or something else has gone wrong. Large data handling for tools other than Integration will be coming in a future update.".format(tool_name))
		write("Exiting tool.\n")
		sys.exit(0)


if actual_sdv:
	write("\n\nUpdated all feature SDV fields based on their spatial relation with the provided Imagery Footprint acquisition dates.")
write("\n\nUpdated feature SDV fields based on the oldest Imagery Footprint acquisition date.")
write("All feature UID values have been updated.\n\n")


### Trash Pile ###


# else:
# 	''''''''' Blanket Feature Update Based on Absolutely Nothing '''''''''
# 	# count_dot_debug = False
# 	# count_dot_out_debug = False
# 	# count_dot_raw_debug = False
# 	# count_under_debug = False
# 	# count_under_out_debug = False
# 	# count_under_raw_debug = False
# 	for fc in featureclass:
# 		# count_dot = int(arcpy.management.GetCount(fc).getOutput(0))
# 		# debug_view(count_dot=count_dot, repeat=False)
# 		# count_dot_out = arcpy.management.GetCount(fc).getOutput(0)
# 		# debug_view(count_dot_out=count_dot_out, repeat=False)
# 		# count_dot_raw = arcpy.management.GetCount(fc)
# 		# debug_view(count_dot_raw=count_dot_raw, repeat=False)
# 		# count_under = int(arcpy.GetCount_management(fc).getOutput(0)) # Method I use
# 		# debug_view(count_under=count_under, repeat=False)
# 		# count_under_out = arcpy.GetCount_management(fc).getOutput(0)
# 		# debug_view(count_under_out=count_under_out, repeat=False)
# 		# count_under_raw = arcpy.GetCount_management(fc) # John's method. does this only work with layers? Or can it print a number but can't be used as an int var
# 		# debug_view(count_under_raw=count_under_raw, repeat=False)
# 		feat_count = int(arcpy.GetCount_management(fc).getOutput(0))
# 		if feat_count == 0:
# 			continue
#
# 		write('\n== Searching {0} {1} features for matching footprints. =='.format(feat_count, fc))
# 		img_dates = []
# 		# Searches through Imagery Footprint dates and creates a list in the YYYY-MM-DD format
# 		with arcpy.da.SearchCursor(img_foot, 'Acquisitio') as img:
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
# 		with arcpy.da.UpdateCursor(fc, fc_fields) as fcu:
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
# 					# feat_parse = datetime.strptime(feat[0], "%Y-%m-%d")
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
# 					# 	#img_date_old = datetime.strptime(img_date_old, '%Y-%m-%d')
# 					# 	#feat_date = datetime.strptime(feat[0], "%Y-%m-%d")
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
# with arcpy.da.UpdateCursor(fc, 'uid') as ucursor:
# 	idcount = 0
# 	for row in ucursor:
# 		row[0] = str(uuid.uuid4())
# 		ucursor.updateRow(row)
# 		idcount += 1
# 	if idcount > 0:
# 		write('\nUpdated {0} MGCP UIDs in {1}.'.format(idcount, fc))



##fc = 'AerofacA'
##write('Searching footprint polygons matching ' + fc + ' features.')
##with arcpy.da.UpdateCursor(fc, fc_fields) as fcu:
##    # For each feature in the feature class, make a search cursor based on the imagery footprint shape and acquisition date
##    count = 0
##    for feat in fcu:
##        # While SHAPE@ is a geometry object, SHAPE@TRUECENTROID is just a tuple of x,y coordinates.
##        # So the great, almighty ArcMap can't figure out that x,y coordinates are a point unless explicitly told on the most basic level
##        # So we have to break every thing down just to go through the pain of making a variable of the tuple to make the coordinates
##        # to make the point to make the point geometry of the centroid to just see if it is in the damn square
##        centroid = feat[1].trueCentroid
##        with arcpy.da.SearchCursor(img_foot, img_fields) as img:
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
##                            feat_date = datetime.strptime(feat[0], "%Y-%m-%d")
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
#cell_date = datetime.strptime(cell_str, "%Y-%m-%d %H:%M:%S")
#write('cell_str = str(cell[0]):')
#write(cell_str)
#write('cell_date = datetime.strptime(cell_str, "%Y-%m-%d %H:%M:%S"):')
#write(cell_date)


### For each feature class, make an update cursor based on the sdv field and each feature's centroid
##fc = 'AerofacA'
##write('Searching footprint polygons matching ' + fc + ' features.')
##with arcpy.da.UpdateCursor(fc, fc_fields) as fcu:
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
##        #centroid = arcpy.PointGeometry(arcpy.Point(x,y))
##        shape = feat[1].trueCentroid
##        write(str(shape))
##        with arcpy.da.SearchCursor(img_foot, img_fields) as img:
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
##                            cell_date = datetime.strptime(cell[0], "%m/%d/%Y")
##                        except:
##                            write('===Incorrect date format in Imagery Footprint. Please check it was downloaded correctly from the source package ID.===')
##                        try:
##                            feat_date = datetime.strptime(feat[0], "%Y-%m-%d")
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


##cursor = arcpy.da.SearchCursor(input_fc, "SHAPE@XY")
##centroid_coords = []
##for feature in cursor:
##    centroid_coords.append(feature[0])
##
##point = arcpy.Point()
##pointGeometryList = []
##
##for pt in centroid_coords:
##    point.X = pt[0]
##    point.Y = pt[1]
##
##    pointGeometry = arcpy.PointGeometry(point)
##    pointGeometryList.append(pointGeometry)


### For each feature class, make an update cursor based on the sdv field and each feature's centroid
##for fc in featureclass:
##    write('Searching footprint polygons matching ' + fc + ' features.')
##    with arcpy.da.UpdateCursor(fc, fc_fields) as fcu:
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
##            centroid = arcpy.PointGeometry(arcpy.Point(x,y))
##            with arcpy.da.SearchCursor(img_foot, img_fields) as img:
##                # For each polygon in the imagery footprint, check if it contains the centroid of the current feature
##                for cell in img:
##                    write(cell[0])
##                    write(cell[1])
##                    if cell[1].contains(centroid):
##                        write('cell contains centroid')
##                        # Convert the Aquisition field of the footprint polygon and the SDV field of the current feature to a datetime variable for comparison
##                        try:
##                            try:
##                                cell_date = datetime.strptime(cell[0], "%m/%d/%Y")
##                            except:
##                                write('===Incorrect date format in Imagery Footprint. Please check it was downloaded correctly from the source package ID.===')
##                            try:
##                                feat_date = datetime.strptime(feat[0], "%Y-%m-%d")
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



#point = arcpy.Point(25282, 43770)
#ptGeometry = arcpy.PointGeometry(point)

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
##      cell_date = datetime.strptime(cell, "%m/%d/%Y")
##   except:
##      print('Incorrect date format in Imagery Footprint. Please check it was downloaded correctly from the source package ID.')
##
##   try:
##      print('Parsing feature date')
##      feat_date = datetime.strptime(feat, "%Y-%m-%d")
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
