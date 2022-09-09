# -*- coding: utf-8 -*-
#¸¸.·´¯`·.¸¸.·´¯`·.¸¸
# ║╚╔═╗╝║  │┌┘─└┐│  ▄█▀‾
# =============================== #
# Import and Validate Topology v3 #
#       Nat Cagle 2022-08-17      #
# =============================== #

'''
╔═════════════════╗
║ Notes and To-Do ║
╚═════════════════╝

## 2 hashtags in the code - recent changes/updates
### 3 hashtags in the code - unique variable or identifier
#### 4 hashtags in the code - things to be updated

## Recent Changes
  - Something that has recently been updated. A dynamic list that is preserved/reset
	in each new version

#### Update Plans
  - Something that still needs to be updated

'''



'''
╔═════════╗
║ Imports ║
╚═════════╝
'''
# ArcPy aliasing
import arcpy as ap
from arcpy import (AddFieldDelimiters as field_delim,
	AddMessage as write,
	MakeFeatureLayer_management as make_lyr,
	MakeTableView_management as make_tbl,
	SelectLayerByAttribute_management as select_by_att,
	SelectLayerByLocation_management as select_by_loc,
	Delete_management as arcdel)
# STOP! Hammer time
from datetime import datetime as dt
import time
# Number bumbers
import re
# System Modules
import os
import sys



'''
╔═══════════════════╗
║ General Functions ║
╚═══════════════════╝
'''
#-----------------------------------
def get_count(fc): # Returns feature count
    results = int(ap.GetCount_management(fc).getOutput(0))
    return results

#-----------------------------------
def MGCP_check(MGCP):
	if not ap.Exists(MGCP):
		ap.AddError('                       ______\n                    .-"      "-.\n                   /            \\\n       _          |              |          _\n      ( \\         |,  .-.  .-.  ,|         / )\n       > "=._     | )(__/  \\__)( |     _.=" <\n      (_/"=._"=._ |/     /\\     \\| _.="_.="\\_)\n             "=._ (_     ^^     _)"_.="\n                 "=\\__|IIIIII|__/="\n                _.="| \\IIIIII/ |"=._\n      _     _.="_.="\\          /"=._"=._     _\n     ( \\_.="_.="     `--------`     "=._"=._/ )\n      > _.="                            "=._ <\n     (_/                                    \\_)\n')
		ap.AddError("Dataset {0} does not exist.\nPlease double check that the file path is correct.\nExitting tool...\n".format(MGCP))
		sys.exit(0)

#-----------------------------------
def disable_editor_tracking(featureclass): # Automatically disables editor tracking for each feature class that doesn't already have it disabled
	write("Disabling Editor Tracking")
	firstl = False
	for fc in featureclass:
		if ap.Describe(fc).editorTrackingEnabled:
			try:
				ap.DisableEditorTracking_management(fc)
				if not firstl:
					write("\n")
					firstl = True
				write("{0} - Disabled".format(fc))
			except:
				ap.AddWarning("Error disabling editor tracking for {0}. Please check the data manually and try again.".format(fc))
				pass
	if firstl:
		write("Editor Tracking has been disabled.")
	else:
		write("Editor Tracking has already been disabled.")

#-----------------------------------
def check_defense(in_out): # If any of the tools that require the Defense Mapping license are selected, check out the Defense license
	class LicenseError(Exception):
		pass
	try:
		if ap.CheckExtension('defense') == 'Available' and in_out == 'out':
			write("\n~~ Checking out Defense Mapping Extension ~~\n")
			ap.CheckOutExtension('defense')
		elif in_out == 'in':
			write("\n~~ Checking Defense Mapping Extension back in ~~\n")
			ap.CheckInExtension('defense')
		else:
			raise LicenseError
	except LicenseError:
		write("Defense Mapping license is unavailable")
	except ap.ExecuteError:
		writeresults('check_defense')


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#


'''
╔═══════════════╗
║ Main Function ║
╚═══════════════╝
'''
def main(*argv):
	### [0] MGCP - Feature Dataset
	MGCP = argv[0]
	MGCP_check(MGCP) # Check that the provided MGCP exists
	# Set the workspace to the MGCP feature dataset
	ap.env.workspace = MGCP
	ap.env.extent = MGCP
	### [1] Topology XML File - File
	topo_xml = argv[1]
	### [2] Disable Editor Tracking - Boolean
	disable = ap.GetParameter(2)
	featureclass = ap.ListFeatureClasses()
	featureclass.sort()
	topo_path = os.path.join(MGCP, 'MGCP_Topology')
	out_path = os.path.join(os.path.dirname(os.path.dirname(MGCP)), 'topology_errors')
	write("\n\n~ Import and Validate Topology ~\n")

	if disable: disable_editor_tracking(featureclass)
	check_defense('out')

	write("\nImporting Defense Mapping TRDv4.5 Topology file...")
	imp_result = ap.ImportTopology_defense(MGCP, topo_xml)
	write(imp_result.getMessages())
	write("Topology imported.")

	write("\nValidating Topology...")
	ap.ValidateTopology_management(topo_path)
	write("Topology has been validated.")

	write("\nIdentifying Topology errors...")
	ap.ExportTopologyErrors_management(topo_path, 'in_memory', 'MGCP_Topology')#, "in_memory")

	pnt_count = get_count("in_memory\\MGCP_Topology_point")
	crv_count = get_count("in_memory\\MGCP_Topology_line")
	srf_count = get_count("in_memory\\MGCP_Topology_poly")

	# if pnt_count or crv_count or srf_count:
	# 	try:
	# 		for i in xrange(0, 5):
	# 			enum = 0
	# 			if os.path.exists(out_path):
	# 				enum += 1
	# 				out_path = out_path + '_' + enum
	# 			if not os.path.exists(out_path):
	# 				os.mkdir(out_path)
	# 	except:
	# 		ap.AddError("\n\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
	# 		ap.AddError("The import and validation DID complete successfully.")
	# 		ap.AddError("Unable to create directory: {0}".format(out_path))
	# 		ap.AddError("Topology errors could not be exported.")
	# 		ap.AddError("The Topology will be left in the database for manual use.")
	# 		ap.AddError("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n")
	# 		check_defense('in')

	if pnt_count or crv_count or srf_count:
		if not os.path.exists(out_path):
			os.mkdir(out_path)

	if pnt_count:
		write("{0} point topology errors.\nExporting to the folder containing the validated GDB...".format(pnt_count))
		ap.FeatureClassToShapefile_conversion("in_memory\\MGCP_Topology_point", out_path)
		ap.AddWarning("Topology point errors located here:\n{0}".format(os.path.join(out_path, "MGCP_Topology_point")))
	if crv_count:
		write("{0} curve topology errors.\nExporting to the folder containing the validated GDB...".format(crv_count))
		ap.FeatureClassToShapefile_conversion("in_memory\\MGCP_Topology_line", out_path)
		ap.AddWarning("Topology point errors located here:\n{0}".format(os.path.join(out_path, "MGCP_Topology_line")))
	if srf_count:
		write("{0} surface topology errors.\nExporting to the folder containing the validated GDB...".format(srf_count))
		ap.FeatureClassToShapefile_conversion("in_memory\\MGCP_Topology_poly", out_path)
		ap.AddWarning("Topology point errors located here:\n{0}".format(os.path.join(out_path, "MGCP_Topology_poly")))

	write("\nDeleting Topology from dataset...")
	arcdel(topo_path)
	write("Topology deleted.")

	check_defense('in')


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#


if __name__=='__main__':
	ap.env.overwriteOutput = True
	argv = tuple(ap.GetParameterAsText(i) for i in range(ap.GetArgumentCount()))
	main(*argv)
