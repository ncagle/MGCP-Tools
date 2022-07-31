# MGCP Tools
 A set of tools for MGCP data to clean features and populate metadata

MGCP Finishing Tool
 - Repairs Geometry
 - Fixes F_Code/FCSubtype mismatch error
 - Explodes multipart features in all feature classes
 - Calculates Default Values
 - Integrates all Utility feature classes

Populate Feature Metadata
 - Spatially compares each feature against an imagery footprint and Geonames source
 - Applies the latest imagery and Geonames dates to each feature
 - Finds invalid, missing, or duplicate UID values and populates them
 - Populates standardized metadata fields with source, content, and copyright information

Populate Cell Metadata
 - Constructs tile polygons for the cell being worked
 - Accepts AAFIF, Imagery, and Geonames sources
 - Populates all domain defined attributes according to latest TRDv4.5.1 metadata standards
 - Exports the metadata as an XML for further validation
