from qgis.PyQt.QtCore import QVariant
from qgis.core import (QgsProcessingException,
                       QgsRasterLayer,
                       QgsVectorLayer,
                       QgsField)
import processing
from numpy import loadtxt, append, column_stack
from scipy.integrate import cumulative_trapezoid
from scipy.interpolate import interp1d

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
def hypsometricCurves (dem,drainageArea):
    params6 = {
            'INPUT_DEM':dem,
            'BOUNDARY_LAYER':drainageArea,
            'STEP':1,
            'USE_PERCENTAGE':False,
            'OUTPUT_DIRECTORY':'TEMPORARY_OUTPUT'
    }
    hypsometriccurve = processing.run(
                                      "qgis:hypsometriccurves",
                                      params6
                                      )['OUTPUT_DIRECTORY']
    maskName = drainageArea.sourceName()
    pathHC = hypsometriccurve + '/histogram_' + maskName + '_1.csv'
    return pathHC
def calculateAHV (areaHeightCurve):
    data = loadtxt(areaHeightCurve, delimiter=',',skiprows=1)
    xd = data[:, 0].tolist()
    yd = data[:, 1].tolist()

    integration = cumulative_trapezoid(xd,yd)
    integrationComplet = append(integration,0)
    data_with_integration = column_stack((data,integrationComplet))
    dataWoLastRow = data_with_integration[:-1]
    return dataWoLastRow
def findParameter (dataAHV,parameter,parameterValue):
    volumes = dataAHV[:, 2]
    heights = dataAHV[:, 1]
    areas = dataAHV[:, 0]
    volInterpolation = interp1d(volumes, heights, kind='linear')
    areaInterpolation = interp1d(areas, heights, kind='linear')
    errorMessageBelow = (
        'This value is below the minimum value of the curve: '
        )
    errorMessageAbove = (
        'This value is above the maximum value of the curve: '
        )
    
    HEIGHT_PARAMETER = 'HEIGHT (m)'
    ELEVATION_PARAMETER = 'ELEVATION (m)'
    AREA_PARAMETER = 'AREA (m2)'
    VOLUME_PARAMETER = 'VOLUME (m3)'

    if parameter == HEIGHT_PARAMETER:
        if parameterValue < 0:
            raise QgsProcessingException(
                "The height can't be negative"
                )
        if parameterValue > (heights[-1]-heights[0] +1):
            raise QgsProcessingException(
                errorMessageAbove + str(heights[-1]-heights[0] +1)
                )
        water_elevation = float(parameterValue+heights[0]-1)
        water_height = float(parameterValue)
        return water_elevation, water_height

    if parameter == ELEVATION_PARAMETER:
        if parameterValue < heights[0]:
            raise QgsProcessingException(
                errorMessageBelow + str(heights[0])
                )
        if parameterValue > heights[-1]:
            raise QgsProcessingException(
                errorMessageAbove + str(heights[-1])
                )
        water_elevation = float(parameterValue)
        water_height = float(water_elevation - heights[0] +1)
        return water_elevation, water_height

    if parameter == AREA_PARAMETER:
        if parameterValue < areas[0]:
            raise QgsProcessingException(
                errorMessageBelow + str(areas[0])
                )
        if parameterValue > areas[-1]:
            raise QgsProcessingException(
                errorMessageAbove + str(areas[-1])
                )
        water_elevation = float(areaInterpolation(parameterValue))
        water_height = float(water_elevation - heights[0] +1)
        return water_elevation, water_height
    if parameter == VOLUME_PARAMETER:
        if parameterValue < volumes[0]:
            raise QgsProcessingException(
                errorMessageBelow + str(volumes[0])
                )
        if parameterValue > volumes[-1]:
            raise QgsProcessingException(
                errorMessageAbove + str(volumes[-1])
                )
        water_elevation = float(volInterpolation(parameterValue))
        water_height = float(water_elevation - heights[0] +1)
        return water_elevation, water_height
def extractFloodedArea (dem, mask, water_elev, water_height):
    params8 = {
            'INPUT':dem,
            'MASK':mask,
            'NODATA':-99999,
            'CROP_TO_CUTLINE':False,
            'OUTPUT':'TEMPORARY_OUTPUT'
            }
    clip = processing.run(
                        "gdal:cliprasterbymasklayer",
                        params8
    )['OUTPUT']
    demclipped = QgsRasterLayer(clip)
    params9 = {
            'INPUT_RASTER':demclipped,
            'RASTER_BAND':1,
            'TABLE':['0',water_elev,'1',water_elev,'4000','0'],
            'NO_DATA':-9999,
            'RANGE_BOUNDARIES':0,
            'NODATA_FOR_MISSING':False,
            'DATA_TYPE':6,
            'OUTPUT':'TEMPORARY_OUTPUT'}
    reclassifing = processing.run(
                                    "native:reclassifybytable",
                                    params9
    )['OUTPUT']
    demreclassified = QgsRasterLayer(reclassifing)

    params10 = {
            'INPUT':demreclassified,
            'OUTPUT':'TEMPORARY_OUTPUT'
            }
    vectorization = processing.run(
                                    "gdal:polygonize",
                                    params10
    )['OUTPUT']
    demvectorized = QgsVectorLayer(vectorization)

    pr = demvectorized.dataProvider()
    pr.setSubsetString("\"DN\" = 1")
    ########################################
    params11 = {
            'INPUT': demvectorized,
            'FIELD':['DN'],
            'SEPARATE_DISJOINT':False,
            'OUTPUT':'memory:floodedarea'
            }
    floodedArea = processing.run("native:dissolve",params11)['OUTPUT']
    elevField = QgsField('Elevation (m)', QVariant.Double,len=10, prec=2)
    heightField = QgsField('Height (m)', QVariant.Double, len=10, prec=2)
    floodedArea.dataProvider().addAttributes([elevField,heightField])
    floodedArea.updateFields()
    floodedArea.startEditing()
    elevationFieldID = floodedArea.fields().indexOf('Elevation (m)')
    heightFieldID = floodedArea.fields().indexOf('Height (m)')
    for features in floodedArea.getFeatures():
        features.setAttribute(elevationFieldID, water_elev)
        features.setAttribute(heightFieldID, water_height)
        floodedArea.updateFeature(features)
    floodedArea.deleteAttributes([0,1])
    floodedArea.commitChanges()

    return floodedArea
def executePluginForCoord (dem,selectedParameter,parameterValue,x,y):
    upslopeRaster = extractUpslopeArea(dem,x,y)
    upslopeVector = polygonizeUpslopeArea(upslopeRaster)
    drainageArea = extractDrainageArea(upslopeVector)
    hypsometricCurve = hypsometricCurves(dem,drainageArea)
    AHV = calculateAHV(hypsometricCurve)
    elevation, height = findParameter(AHV,selectedParameter,
                                        parameterValue)
    floodedArea = extractFloodedArea(dem,drainageArea,elevation,
                                        height)
    return floodedArea
def executePluginForArea (dem,area,selectedParameter,parameterValue):
    hypsometricCurve = hypsometricCurves(dem,area)
    AHV = calculateAHV(hypsometricCurve)
    elevation, height = findParameter(AHV,selectedParameter,
                                        parameterValue)
    floodedArea = extractFloodedArea(dem,area,elevation,
                                        height)
    return floodedArea