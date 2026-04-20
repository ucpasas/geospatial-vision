"""
tests/conftest.py
-----------------
Shared pytest fixtures — Phase 1.

One fixture only: a tiny synthetic GeoTIFF written to a temp directory.
Using a real file on disk (not an in-memory GDAL dataset) means the full
path → gdal.Open() round-trip is exercised, exactly as it will be in
production. Known pixel values let stats tests be exact in later phases.
"""

import numpy as np
import pytest
from osgeo import gdal, osr


@pytest.fixture(scope="session")
def sample_tif(tmp_path_factory):
    """
    Create a 10×10 single-band GeoTIFF with predictable properties:

      CRS         : EPSG:32755  (WGS 84 / UTM zone 55S)
      Pixel type  : Int16
      Pixel values: 0–99 row-major  →  min=0, max=99, mean=49.5  (exact)
      Resolution  : 10 m/pixel
      Nodata      : -9999

    scope="session" — created once, reused across all tests. Faster than
    recreating per test function, and safe because no test modifies this file.

    Returns
    -------
    pathlib.Path
        Absolute path to the written .tif file.
    """
    gdal.UseExceptions()

    out_path = tmp_path_factory.mktemp("data") / "sample.tif"

    driver = gdal.GetDriverByName("GTiff")
    ds = driver.Create(
        str(out_path),
        10,               # raster width  (pixels)
        10,               # raster height (pixels)
        1,                # number of bands
        gdal.GDT_Int16,   # pixel data type
    )

    # GeoTransform: (top_left_x, pixel_w, 0, top_left_y, 0, -pixel_h)
    # Anchored at a real UTM 55S easting/northing so reprojection is valid.
    ds.SetGeoTransform([500000.0, 10.0, 0.0, 6200000.0, 0.0, -10.0])

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(32755)
    ds.SetProjection(srs.ExportToWkt())

    data = np.arange(100, dtype=np.int16).reshape(10, 10)
    band = ds.GetRasterBand(1)
    band.SetNoDataValue(-9999)
    band.WriteArray(data)
    band.FlushCache()

    ds = None  # explicitly close — flushes to disk, releases file handle

    return out_path
