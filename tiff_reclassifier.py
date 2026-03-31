import processing
from qgis.core import QgsRasterLayer, QgsProject

# 1. Define Paths and Parameters
input_raster = input("TIFF file:")
output_gpkg = input("Output(gkpg)")
# Table format: [min, max, new_value, min, max, new_value,...]
# Example: 0-10 -> 1, 10-20 -> 2
reclass_table = [0, 10, 1, 10, 20, 2] 

# Load the raster to ensure it's valid
layer = QgsRasterLayer(input_raster, 'input_raster')
if not layer.isValid():
    print("Layer failed to load!")
else:
    # 2. Run QGIS "Reclassify by table" algorithm
    # Algorithm ID: native:reclassifybytable [1]
    params = {
        'INPUT_RASTER': input_raster,
        'RASTER_BAND': 1,
        'TABLE': reclass_table,
        'NO_DATA': -9999,
        'RANGE_BOUNDARIES': 0, # min < value <= max
        'NODATA_FOR_MISSING': False,
        'DATA_TYPE': 5, # Float32
        'OUTPUT': output_gpkg # 3. Output directly to GeoPackage
    }
    
    print("Running reclassification...")
    result = processing.run("native:reclassifybytable", params)
    
    # Load result into map
    QgsProject.instance().addMapLayer(QgsRasterLayer(result['OUTPUT'], 'Reclassified'))
    print(f"Finished. Saved to: {output_gpkg}")
