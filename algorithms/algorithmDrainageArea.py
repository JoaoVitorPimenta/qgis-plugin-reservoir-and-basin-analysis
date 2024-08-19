from qgis.core import (QgsRasterLayer,
                       QgsVectorLayer)
import processing

def extractUpslopeArea (dem,x,y):
    params4 = {
        'TARGET_PT_X':x,
        'TARGET_PT_Y':y,
        'ELEVATION':dem,
        'AREA':'TEMPORARY_OUTPUT',
        'METHOD':0
    }
    upslope = processing.run("sagang:upslopearea", params4)['AREA']
    upslopeRaster = QgsRasterLayer(upslope)
    return upslopeRaster
def polygonizeUpslopeArea (upslopeRaster):
    params5= {
            'INPUT':upslopeRaster,
            'OUTPUT':'TEMPORARY_OUTPUT'
    }
    vectorization = processing.run("gdal:polygonize", params5)['OUTPUT']
    upslopeVector = QgsVectorLayer(vectorization)
    return upslopeVector
    ##################################
def extractDrainageArea (upslopeVector):
    params10 = {
            'INPUT':upslopeVector,
            'FIELD':[],
            'SEPARATE_DISJOINT':False,
            'OUTPUT':'TEMPORARY_OUTPUT'
            }
    drainageArea = processing.run("native:dissolve",params10)['OUTPUT']
    return drainageArea
    #####################################
def executePlugin (dem,x,y):
    upslopeRaster = extractUpslopeArea(dem,x,y)
    upslopeVector = polygonizeUpslopeArea(upslopeRaster)
    drainageArea = extractDrainageArea(upslopeVector)
    return drainageArea
