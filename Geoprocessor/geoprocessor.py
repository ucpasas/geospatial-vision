"""
geoprocessor.py
---------------
GDAL Python bindings wrapper.
"""

from osgeo import gdal, osr
import os

gdal.UseExceptions()


class Geoprocessor:
    def __init__(self, path: str):
        self.path = path

    def _open(self) -> gdal.Dataset:
        try:
            ds = gdal.Open(self.path)
        except RuntimeError:
            raise RuntimeError(f"GDAL could not open file: {self.path!r}")

        if ds is None:
            raise RuntimeError(f"GDAL could not open file: {self.path!r}")

        return ds

    def _estimate_output_resolution(self, transform, cx, cy, x_res, y_res):
        """Estimate output resolution by transforming a single centre point.

        TODO: Replace single-point sampling with a 5x5 grid across the raster
        extent, taking the minimum resolution across all sample points. The
        current approach breaks down for:
          - Large rasters spanning wide latitude ranges
          - Highly oblique projections
          - Rasters near the poles
        See: https://gdal.org/programs/gdalwarp.html#cmdoption-gdalwarp-tr
        """
        x1, y1, _ = transform.TransformPoint(cx, cy)
        x2, y2, _ = transform.TransformPoint(cx + x_res, cy + y_res)
        return abs(x2 - x1), abs(y2 - y1)

    def reproject(self, output_path: str, epsg: int) -> gdal.Dataset:
        """Reproject the raster to a new CRS.

        Parameters
        ----------
        output_path : str
            Path to write the reprojected GeoTIFF.
        epsg : int
            Target CRS as an EPSG code, e.g. 4326 for WGS84.

        Returns
        -------
        gdal.Dataset
            The reprojected output dataset.
        """
        ds_src = self._open()

        gt = ds_src.GetGeoTransform()
        x_res = gt[1]
        y_res = abs(gt[5])

        src_srs = osr.SpatialReference()
        src_srs.ImportFromWkt(ds_src.GetProjection())

        dst_srs = osr.SpatialReference()
        dst_srs.ImportFromEPSG(epsg)

        transform = osr.CoordinateTransformation(src_srs, dst_srs)

        # Sample at raster centre — see _estimate_output_resolution TODO
        cx = gt[0] + (ds_src.RasterXSize / 2) * x_res
        cy = gt[3] + (ds_src.RasterYSize / 2) * -y_res

        out_x_res, out_y_res = self._estimate_output_resolution(
            transform, cx, cy, x_res, y_res
        )

        ds = gdal.Warp(
            output_path,
            self.path,
            dstSRS=f"EPSG:{epsg}",
            xRes=out_x_res,
            yRes=out_y_res,
            resampleAlg=gdal.GRA_Bilinear,
            targetAlignedPixels=True,
        )

        if ds is None:
            raise RuntimeError(f"gdal.Warp failed writing to {output_path!r}")

        return ds

    def clip_to_bbox(self, output_path: str, bbox: tuple) -> gdal.Dataset:
        """Clip the raster to a bounding box.

        Parameters
        ----------
        output_path : str
            Path to write the clipped GeoTIFF.
        bbox : tuple
            (min_x, min_y, max_x, max_y) in the source raster's CRS units.

        Returns
        -------
        gdal.Dataset
            The clipped output dataset.

        Raises
        ------
        ValueError
            If bbox is malformed or min >= max on either axis.
        RuntimeError
            If GDAL fails to clip.
        """
        min_x, min_y, max_x, max_y = bbox

        if min_x >= max_x or min_y >= max_y:
            raise ValueError(
                f"Invalid bbox {bbox!r}: min values must be less than max values."
            )

        self._open()  # validate source before starting

        try:
            ds = gdal.Warp(
                output_path,
                self.path,
                outputBounds=(min_x, min_y, max_x, max_y),
            )
        except RuntimeError as e:
            raise RuntimeError(f"gdal.Warp clip failed for {self.path!r}: {e}") from e

        if ds is None:
            raise RuntimeError(f"gdal.Warp clip failed for {self.path!r}")

        return ds

    def convert_to_cog(self, output_path: str) -> gdal.Dataset:
        """Convert the raster to a Cloud Optimised GeoTIFF (COG).

        Operation order is mandatory:
        1. Write intermediate GeoTIFF
        2. BuildOverviews() on intermediate
        3. Translate() with COPY_SRC_OVERVIEWS=YES

        TODO: Replace two-step Translate+BuildOverviews with the GDAL 3.1+ COG
        driver (format="COG") once minimum GDAL version can be guaranteed:
            gdal.Translate(output_path, self.path, format="COG",
                        creationOptions=["COMPRESS=DEFLATE",
                                            "OVERVIEWS=IGNORE_EXISTING"])

        TODO: Add validate_cog() helper after conversion to assert the output
        is a true COG — correct byte order, internal overviews, tiled layout.
        Use the cogdumper library (pip install cogdumper) or the official
        GDAL COG validator:
            python -m cogdumper.cog_validate output.tif
        Without validation, a misconfigured output silently passes as a GeoTIFF
        but fails to deliver range-request performance in production.

        Parameters
        ----------
        output_path : str
            Path to write the COG GeoTIFF.

        Returns
        -------
        gdal.Dataset
            The COG output dataset.

        Raises
        ------
        RuntimeError
            If any GDAL operation fails.
        """
    

        intermediate_path = output_path + ".tmp.tif"

        try:
            # Step 1 — write intermediate GeoTIFF
            try:
                ds_inter = gdal.Translate(intermediate_path, self.path)
            except RuntimeError as e:
                raise RuntimeError(f"Intermediate write failed: {e}") from e

            if ds_inter is None:
                raise RuntimeError("Intermediate write failed: gdal.Translate returned None")

            # Step 2 — build overviews on the intermediate file
            # Levels 2,4,8,16 — each is half the resolution of the previous
            try:
                ds_inter.BuildOverviews("NEAREST", [2, 4, 8, 16])
            except RuntimeError as e:
                raise RuntimeError(f"BuildOverviews failed: {e}") from e

            ds_inter = None  # flush and close before Translate reads it

            # Step 3 — translate to COG, copying the overviews built in step 2
            try:
                ds_cog = gdal.Translate(
                    output_path,
                    intermediate_path,
                    creationOptions=[
                        "COMPRESS=DEFLATE",
                        "TILED=YES",
                        "COPY_SRC_OVERVIEWS=YES",
                    ],
                )
            except RuntimeError as e:
                raise RuntimeError(f"COG Translate failed: {e}") from e

            if ds_cog is None:
                raise RuntimeError("COG Translate failed: gdal.Translate returned None")

            return ds_cog

        finally:
            # Always clean up the intermediate file even if an exception occurred
            if os.path.exists(intermediate_path):
                os.remove(intermediate_path)

    def get_stats(self, band: int = 1) -> dict:
        """Compute exact statistics for a raster band.

        Parameters
        ----------
        band : int
            Band number, 1-indexed. Defaults to 1.

        Returns
        -------
        dict
            Keys: min, max, mean, stddev
        """
        ds = self._open()

        try:
            b = ds.GetRasterBand(band)
        except RuntimeError:
            raise RuntimeError(f"Band {band} not found in {self.path!r}")

        min_, max_, mean_, stddev_ = b.ComputeStatistics(False)

        ds = None

        return {
            "min": min_,
            "max": max_,
            "mean": mean_,
            "stddev": stddev_,
        }
