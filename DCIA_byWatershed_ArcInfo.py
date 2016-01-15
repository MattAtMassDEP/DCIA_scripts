#==============  PART 0 Set up Geoprocessor   ==========================================
# Import system modules
import sys, string, os, shutil, time
import arcpy
from arcpy import env
env.overwriteOutput = True

#adapting for batch land use clip and summary

print "Processing..."
# Check availability of appropriate ArcGIS license
# Set required ESRI code:
try:
    if arcpy.CheckProduct("arcview") == u"Available":
        arcpy.SetProduct("arcview")
        print "  " + "Esri Arcview product license set"
    #elif arcpy.CheckProduct("arceditor") == u"Available":
        #arcpy.SetProduct("arcinfo")
    else:
        msgLicenseDNE="No ESRI ArcView licenses available to run script"
        raise Exception, msgLicenseDNE
except Exception, ErrorDesc: print ErrorDesc
        

# get local variables to workspaces for tables from system arguments:

landuseFile  = sys.argv[1]   				#get path to landuse from user
Impervious   = sys.argv[2]				#get path to impervious cover from user
WorkSpacePath = sys.argv[3] 				#where the watersheds are
OutPathA = sys.argv[4]   				# where the land use clips go
OutPathB = sys.argv[5]	 				# where the summary tables go


#hard set the path to the landuse  
#LUPath = "G:\\local\\user projects\\mreardon\MEP\\Catchment DCIA estimate\\LANDUSE2005_POLY_HAMS_Clipped_to_Easthampton.shp" #where the Land use to be clipped is located- on other systems put path to your landuse
OutPathA = OutPathA + "\\"
OutPathB = OutPathB + "\\"

# This assumes that you subset the land use for the watershed.
#  This is the landuse clipped by Cape Cod by the Major Watersheds shapefile (outline away from coast)
#BasinLU = "LANDUSE2005_POLY_HAMS_Clipped_to_Easthampton.shp"

# set the location to the impervious cover shapefile
#Impervious =  "G:\\local\\user projects\\mreardon\\MEP\\template\\Catchment DCIA estimate\\Easthamption_impervious.shp"


env.workspace = WorkSpacePath

# Make a list of the watershed shape files-note they all start with "poly".
BasinList = []
BasinList = arcpy.ListFeatureClasses("poly*")

length = len(BasinList)
print" Basin list has  "+str(length)+" members"

# if no files are name poly exit script
if length == 0 or length is None:
    arcpy.AddMessage("You must name your watershed files with a name that begins with 'poly'. Script will now ext")
    sys.exit()
	

# Start to cycle through Basins  
for b in BasinList[0:]:
    arcpy.AddMessage("Clipping landuse and impervious by: " + str(b))  #tell user what is going on
    arcpy.arcpy.Clip_analysis(landuseFile, b, OutPathA + "LU"+str(b) )    #do the clip for landuse
    arcpy.arcpy.Clip_analysis(Impervious, b, OutPathA + "IMP"+str(b) )    #do the clip for landuse

	#add Area_A field to clipped landuse file
    arcpy.AddField_management(OutPathA +"LU"+str(b), "Area_A", "DOUBLE")    # add an Area_A field
    exp = "!SHAPE.AREA@ACRES!"			
    arcpy.CalculateField_management(OutPathA + "LU"+str(b), "Area_A", exp, "PYTHON_9.3") #calculate the area in acres for Area_A field
    print "Finished clip of "+b

    # extract the parts of the watershed shape file name then use it to build output file name for summary table
    NList = string.split(str(b), ".")
    OTName = "Sum_LU"+NList[0]+".dbf"
    arcpy.Statistics_analysis (OutPathA + "LU"+str(b),OutPathB +OTName,[["Area_A", "SUM"]], "LU05_DESC")
    
# change the workspace to landuse table summary info (to avoid having to type in the full path to the data every time)
env.workspace = OutPathA
arcpy.AddMessage("Changing workspace to : " + env.workspace )


# Build list of clipped landuse shapefiles
BasinLU_List = []
BasinLU_List = arcpy.ListFeatureClasses("LU*")

arcpy.AddMessage(BasinLU_List[0:])

# Build list of clipped impervious shapefiles
ImperviousList = []
ImperviousList = arcpy.ListFeatureClasses("IMPpoly*")

arcpy.AddMessage(ImperviousList[0:])



for x,y in zip(BasinLU_List,ImperviousList):

    arcpy.AddMessage(x) 			#just checking what shapefile we are actually getting
    arcpy.AddMessage(y)				#just checking what shapefile we are actually getting
    NList = string.split(str(x), ".") 		# line 91
    #arcpy.AddMessage(NList)
    
    NList1=NList[0]
    NList1= NList1[2:]
    arcpy.AddMessage(NList1)
	
     
    OutName= "TabulatedLUandIMP"+ NList1 +".dbf"
    arcpy.AddMessage(OutName)

    #arcpy.AddMessage(y)
    # Tabulate 
    # tabualte paramters-landuse shapefile,LUCODE, LU05_DESC, impervious shapefile, outputTable, class field, sumfield=Shape_Area, xy_tolerance, out_units=Acres
    arcpy.TabulateIntersection_analysis(x,"LUCODE;LU05_DESC", y, OutPathB + OutName,"IMPERVIOUS","Shape_Area","#","ACRES")


# change the workspace to summary tables folder (to avoid having to type in the full path to the data every time)
env.workspace = OutPathB
arcpy.AddMessage("Changing workspace to : " + env.workspace )

#build the list of Land Use by Wateshed summary tables
LU_shed = []
LU_shed = arcpy.ListTables("Sum_LU*")

# build the list of Tabulated files to add to
TabLUandIMP = []
TabLUandIMP = arcpy.ListTables("TabulatedLU*")

# go through the landuse and impervious cover table and the land use by watershed summary tables
for x,y in zip(TabLUandIMP,LU_shed):
    arcpy.AddMessage(x)
    arcpy.AddMessage(y)
    arcpy.JoinField_management(x,"LU05_DESC",y,"LU05_DESC","#")

#arcpy.AddMessage(TabLUandIMP)

# next add the DCIA field and then calculate DCIA with the code below.
for x in TabLUandIMP:
    arcpy.AddMessage(x)
    arcpy.AddField_management(x, "DCIA_perc", "DOUBLE")
    inTable=OutPathB+"\\"+str(x)
    arcpy.AddMessage(x + " should be running for DCIA")
    arcpy.CalculateField_management(inTable,"DCIA_perc","CalculateDCIA(!LUCODE!, !PERCENTAGE!)","PYTHON_9.3","def CalculateDCIA(LU_Code, PercentIA):\n  if (LU_Code == 15  or LU_Code == 16 or  LU_Code == 18 or  LU_Code == 19 or  LU_Code == 29 or  LU_Code == 39 or  LU_Code == 12 or LU_Code == 7 or  LU_Code == 8 or  LU_Code == 31 or  LU_Code == 5 or  LU_Code == 6 or  LU_Code == 9 or  LU_Code == 17 or  LU_Code == 24 or  LU_Code == 26 or  LU_Code == 34)  and PercentIA > 1.0:\n    return 0.1* (PercentIA)**1.5\n  elif (LU_Code == 1 or  LU_Code == 2 or  LU_Code == 3 or  LU_Code == 35 or  LU_Code == 36 or  LU_Code == 40) and  PercentIA > 1.0:\n    return 0.01 * (PercentIA)**2\n  elif  (LU_Code == 13 or  LU_Code == 38)  and PercentIA > 1.0:\n    return 0.04*(PercentIA)**1.7 \n  elif  (LU_Code == 10 or  LU_Code == 11)  and PercentIA > 1.0:\n    return 0.4*(PercentIA)**1.2 \n  else:\n    return 0\n\n\n\n\n")



	    
