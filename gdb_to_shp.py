# -*- coding: utf-8 -*-
#¸¸.·´¯`·.¸¸.·´¯`·.¸¸
# ║╚╔═╗╝║  │┌┘─└┐│  ▄█▀‾
# ============================= #
# Convert MGCP to Shapefiles v3 #
#      Nat Cagle 2022-08-18     #
# ============================= #

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


mgcp_list = ["AerofacA",
			"AerofacP",
			"AgristrA",
			"AgristrP",
			"AquedctA",
			"AquedctL",
			"AquedctP",
			"BarrierL",
			"BluffL",
			"BridgeA",
			"BridgeL",
			"BuildA",
			"BuildP",
			"BuiltupA",
			"BuiltupP",
			"CisternP",
			"CoastA",
			"CoastL",
			"CoastP",
			"CommA",
			"CommP",
			"CropA",
			"DamA",
			"DamL",
			"DamP",
			"DangerA",
			"DangerL",
			"DangerP",
			"DisposeA",
			"EmbankA",
			"EmbankL",
			"ExtractA",
			"ExtractP",
			"FerryL",
			"FerryP",
			"FirebrkA",
			"FordL",
			"FordP",
			"FortA",
			"FortP",
			"GrassA",
			"GroundA",
			"HarborA",
			"HarborP",
			"IndL",
			"InundA",
			"LakeresA",
			"Landfrm1A",
			"Landfrm2A",
			"LandfrmA",
			"LandfrmL",
			"LandfrmP",
			"LandIceA",
			"LandmrkA",
			"LandmrkL",
			"LandmrkP",
			"LockA",
			"LockL",
			"LockP",
			"MarkersP",
			"MilA",
			"MilL",
			"MilP",
			"MiscaeroP",
			"MiscL",
			"MiscP",
			"MiscpopA",
			"MiscpopP",
			"MtnP",
			"NuclearA",
			"OasisA",
			"ObstrP",
			"PhysA",
			"PierA",
			"PierL",
			"PipeL",
			"PlazaA",
			"PowerA",
			"PowerL",
			"PowerP",
			"ProcessA",
			"ProcessP",
			"PumpingA",
			"PumpingP",
			"RailrdL",
			"RampA",
			"RapidsA",
			"RapidsL",
			"RapidsP",
			"RigwellP",
			"RoadL",
			"RrturnP",
			"RryardA",
			"RuinsA",
			"RunwayA",
			"RunwayL",
			"RunwayP",
			"SeastrtA",
			"SeastrtL",
			"ShedL",
			"ShedP",
			"SportA",
			"StorageA",
			"StorageP",
			"SubstatA",
			"SubstatP",
			"SwampA",
			"TeleL",
			"TestA",
			"TextP",
			"ThermalA",
			"ThermalP",
			"TowerP",
			"TrackL",
			"TrailL",
			"TransA",
			"TransL",
			"TransP",
			"TreatA",
			"TreatP",
			"TreesA",
			"TreesL",
			"TreesP",
			"TundraA",
			"TunnelA",
			"TunnelL",
			"UtilP",
			"VoidA",
			"WatrcrsA",
			"WatrcrsL",
			"WellsprP"
			]

delta_list = ["AnnoL",
			"AnnoP",
			"ContourL",
			"ElevP",
			"PolbndA",
			"PolbndL"
			]

metadata_list = ["Cell",
				"Subregion",
				"Source"
				]


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
	### [1] Output Folder for Shapefiles - Folder
	out_path = argv[1]
	#delta = MGCP + "_Delta"
	#metadata = MGCP + "_Metadata"

	write("\n\n~ Convert MGCP to Shapefiles ~\n")

	check_defense('out')

	# Convert MGCP feature classes to shapefiles
	write("Building feature class list for MGCP.")
	mgcp_list = ap.ListFeatureClasses()
	mgcp_list.sort()
	mgcp_list = ["'" + MGCP + '\\' + fc + "'" for fc in mgcp_list]
	mgcp_string = ';'.join(mgcp_list)
	write("Converting MGCP dataset to shapefiles...\nThis will take a few minutes...")
	mgcp_result = ap.GeodatabaseToShape_defense(mgcp_string, out_path, "VALUES", "MGCP", "NO_CREATE_EMPTIES") #, "CREATE_EMPTIES")
	write(mgcp_result.getMessages())

	# if ap.Exists(delta):
	# 	# Convert MGCP_Delta feature classes to shapefiles
	# 	ap.env.workspace = delta
	# 	write("\nMGCP_Delta dataset identified in GDB.")
	# 	write("Building feature class list for MGCP_Delta.")
	# 	delta_list = ap.ListFeatureClasses()
	# 	delta_list.sort()
	# 	delta_list = ["'" + delta + '\\' + fc + "'" for fc in delta_list]
	# 	delta_string = ';'.join(delta_list)
	# 	write("Converting MGCP_Delta dataset to shapefiles.")
	# 	delta_result = ap.GeodatabaseToShape_defense(delta_string, out_path, "VALUES", "MGCP", "CREATE_EMPTIES")
	# 	write(delta_result.getMessages())

	# if ap.Exists(metadata):
	# 	# Convert MGCP_Metadata feature classes to shapefiles
	# 	ap.env.workspace = metadata
	# 	write("\nMGCP_Metadata dataset identified in GDB.")
	# 	write("Building feature class list for MGCP_Metadata.")
	# 	metadata_list = ap.ListFeatureClasses()
	# 	metadata_list.sort()
	# 	metadata_list = ["'" + metadata + '\\' + fc + "'" for fc in metadata_list]
	# 	metadata_string = ';'.join(metadata_list)
	# 	write("Converting MGCP_Metadata dataset to shapefiles.")
	# 	metadata_result = ap.GeodatabaseToShape_defense(metadata_string, out_path, "VALUES", "MGCP", "CREATE_EMPTIES")
	# 	write(metadata_result.getMessages())

	# The only files allowed in the MGCP database shapefiles zip are:
	# 	- Shapefiles (of the form [PAL][FCODE]{_n}.[dbf, shp, shx])
	# 	  i.e. AAA010.dbf, AAA010.shp, AAA010.shx, etc.
	# 	- X###Y##.xml
	# 	- An 'FC' folder containing one '.xml' file and one optional '.xls' file
	# 	- These are not case-sensitive
	too_much_shape = ('.cpg', '.prj', '.sbn', '.sbx', '.shp.xml')
	shapefiles_list = os.listdir(out_path)
	write("\nThere is too much shape in these shapefiles for MGCP.\nRemoving extraneous files with the following extensions:")
	write("    *.cpg, *.prj, *.sbn, *.sbx, *.shp.xml")

	for shp_ext in shapefiles_list:
	    if shp_ext.endswith(too_much_shape):
	        os.remove(os.path.join(out_path, shp_ext))

	check_defense('in')


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~#


if __name__=='__main__':
	ap.env.overwriteOutput = True
	argv = tuple(ap.GetParameterAsText(i) for i in range(ap.GetArgumentCount()))
	main(*argv)
