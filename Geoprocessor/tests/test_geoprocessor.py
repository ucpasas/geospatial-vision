import pytest
from osgeo import gdal, osr
from geoprocessor import Geoprocessor


class TestOpen:
    def test_open_valid_file_returns_dataset(self, sample_tif):
        gp = Geoprocessor(str(sample_tif))
        ds = gp._open()

        assert ds is not None
        assert ds.RasterXSize == 10
        assert ds.RasterYSize == 10
        assert ds.RasterCount == 1

        ds = None

    def test_open_missing_file_raises_runtime_error(self):
        gp = Geoprocessor("/nonexistent/path/file.tif")

        with pytest.raises(RuntimeError):
            gp._open()


class TestReproject:
    def test_reproject_changes_crs(self, sample_tif, tmp_path):
        gp = Geoprocessor(str(sample_tif))
        out = str(tmp_path / "reprojected.tif")

        ds = gp.reproject(out, epsg=4326)

        actual = osr.SpatialReference()
        actual.ImportFromWkt(ds.GetProjection())

        expected = osr.SpatialReference()
        expected.ImportFromEPSG(4326)

        assert actual.IsSame(expected) == 1

        ds = None

class TestGetStats:
    def test_stats_match_known_pixel_values(self, sample_tif):
        gp = Geoprocessor(str(sample_tif))
        stats = gp.get_stats()

        # Fixture pixel values are 0-99 row-major — all exact
        assert stats["min"] == 0.0
        assert stats["max"] == 99.0
        assert stats["mean"] == 49.5
        assert stats["stddev"] > 0.0

    def test_stats_invalid_band_raises(self, sample_tif):
        gp = Geoprocessor(str(sample_tif))

        with pytest.raises(RuntimeError, match="Band 99 not found"):
            gp.get_stats(band=99)

class TestClipToBbox:
    def test_clip_reduces_extent(self, sample_tif, tmp_path):
        gp = Geoprocessor(str(sample_tif))
        out = str(tmp_path / "clipped.tif")

        # Fixture origin is (500000, 6200000), 10m pixels, 10x10 = 100x100m extent
        # Clip to the inner 50x50m — bottom-left quarter
        bbox = (500000.0, 6199950.0, 500050.0, 6200000.0)
        ds = gp.clip_to_bbox(out, bbox)

        assert ds.RasterXSize == 5
        assert ds.RasterYSize == 5

        ds = None

    def test_clip_invalid_bbox_raises(self, sample_tif, tmp_path):
        gp = Geoprocessor(str(sample_tif))
        out = str(tmp_path / "clipped.tif")

        with pytest.raises(ValueError, match="Invalid bbox"):
            gp.clip_to_bbox(out, bbox=(500050.0, 6200000.0, 500000.0, 6199950.0))

class TestConvertToCog:
    def test_cog_is_tiled(self, sample_tif, tmp_path):
        gp = Geoprocessor(str(sample_tif))
        out = str(tmp_path / "output.cog.tif")

        ds = gp.convert_to_cog(out)

        # Tiled layout is the core COG requirement
        md = ds.GetRasterBand(1).GetMetadata("IMAGE_STRUCTURE")
        assert md.get("BLOCK_TYPE") == "TILED" or ds.GetRasterBand(1).GetBlockSize() != [ds.RasterXSize, 1]

        ds = None

    def test_cog_has_overviews(self, sample_tif, tmp_path):
        gp = Geoprocessor(str(sample_tif))
        out = str(tmp_path / "output.cog.tif")

        ds = gp.convert_to_cog(out)

        assert ds.GetRasterBand(1).GetOverviewCount() > 0

        ds = None

    def test_cog_intermediate_file_cleaned_up(self, sample_tif, tmp_path):
        gp = Geoprocessor(str(sample_tif))
        out = str(tmp_path / "output.cog.tif")

        gp.convert_to_cog(out)

        assert not (tmp_path / "output.cog.tif.tmp.tif").exists()