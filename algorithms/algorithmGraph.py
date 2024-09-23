from qgis.core import (QgsRasterLayer,
                       QgsVectorLayer)
import processing
from scipy.integrate import cumulative_trapezoid
from numpy import loadtxt, append, column_stack
from plotly.graph_objects import Scatter
from plotly.subplots import make_subplots

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
def hypsometricCurves (dem,drainageArea,step):
    params6 = {
            'INPUT_DEM':dem,
            'BOUNDARY_LAYER':drainageArea,
            'STEP':step,
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
def graphAHV(npAHVData):
    area = npAHVData[:,0]/(10**6)
    height = npAHVData[:,1]
    volume = npAHVData[:,2]/(10**9)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(Scatter(
                            x=volume,
                            y=height,
                            mode='lines',
                            name='Volume - Height'
                            ),
                            secondary_y=False
                            )
    fig.add_trace(Scatter(x=area,
                            y=height,
                            mode='lines',
                            name='Area - Height'
                            ),
                            secondary_y=True
                            )

    fig.data[1].update(xaxis='x2')
    fig.update_layout(
        title='Area x Height x Volume',
        xaxis=dict(title='Volume (km3)'),
        yaxis=dict(title='Height (m)'),
        xaxis2=dict(title='Area (km2)',
                    overlaying='x',
                    side='top',
                    autorange='reversed'),
        yaxis2=dict(
                    title='Height (m)',
                    overlaying='y',
                    side='right',
                    position=1
                    )
                        )

    return fig
def executePluginForCoord (dem,x,y,step):
    upslopeRaster = extractUpslopeArea(dem,x,y)
    upslopeVector = polygonizeUpslopeArea(upslopeRaster)
    drainageArea = extractDrainageArea(upslopeVector)
    hypsometricCurve = hypsometricCurves(dem,drainageArea,step)
    AHV = calculateAHV(hypsometricCurve)
    graph = graphAHV(AHV)
    return AHV, graph
def executePluginForArea (dem,area,step):
    hypsometricCurve = hypsometricCurves(dem,area,step)
    AHV = calculateAHV(hypsometricCurve)
    graph = graphAHV(AHV)
    return AHV, graph
