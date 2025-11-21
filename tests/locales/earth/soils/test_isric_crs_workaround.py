"""Tests for ISRIC WMS CRS metadata workaround.

Verifies that fetch_layer() and fetch_isric_wrb() properly inject
Homolosine projection metadata when EPSG:152160 responses lack WKT.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = []

try:
    from osgeo import gdal
except ModuleNotFoundError:
    gdal = None  # type: ignore[assignment]
    pytestmark.append(pytest.mark.skip(reason="osgeo.gdal is required for CRS metadata tests"))
    fetch_isric_wrb = fetch_layer = soil_grid_proj4 = None  # type: ignore[assignment]
else:
    from wepppy.locales.earth.soils.isric import (
        fetch_isric_wrb,
        fetch_layer,
        soil_grid_proj4,
    )


@pytest.fixture
def temp_soils_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for soil data."""
    soils_dir = tmp_path / "soils"
    soils_dir.mkdir()
    return soils_dir


@pytest.fixture
def mock_wms_response_no_crs() -> bytes:
    """Create a minimal GeoTIFF without CRS metadata.
    
    Returns GeoTIFF bytes that have valid geotransform but empty WKT.
    """
    # Create a minimal 10x10 GeoTIFF in memory without projection
    mem_driver = gdal.GetDriverByName('MEM')
    ds = mem_driver.Create('', 10, 10, 1, gdal.GDT_Byte)
    ds.SetGeoTransform((-12774700.0, 100.0, 0.0, 5516600.0, 0.0, -100.0))
    # Explicitly do NOT set projection - this simulates the ISRIC bug
    band = ds.GetRasterBand(1)
    band.Fill(42)  # Fill with test data
    
    # Write to temp file and read bytes
    with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp:
        gtiff_driver = gdal.GetDriverByName('GTiff')
        gtiff_driver.CreateCopy(tmp.name, ds)
        ds = None  # Close memory dataset
        
        tmp_path = Path(tmp.name)
        tiff_bytes = tmp_path.read_bytes()
        tmp_path.unlink()  # Clean up
    
    return tiff_bytes


@pytest.fixture
def mock_wms_response_with_crs() -> bytes:
    """Create a minimal GeoTIFF with proper CRS metadata.
    
    Returns GeoTIFF bytes that already have Homolosine projection.
    """
    from osgeo import osr
    
    mem_driver = gdal.GetDriverByName('MEM')
    ds = mem_driver.Create('', 10, 10, 1, gdal.GDT_Byte)
    ds.SetGeoTransform((-12774700.0, 100.0, 0.0, 5516600.0, 0.0, -100.0))
    
    # Set the Homolosine projection
    sr = osr.SpatialReference()
    sr.ImportFromProj4(soil_grid_proj4)
    ds.SetProjection(sr.ExportToWkt())
    
    band = ds.GetRasterBand(1)
    band.Fill(42)
    
    with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp:
        gtiff_driver = gdal.GetDriverByName('GTiff')
        gtiff_driver.CreateCopy(tmp.name, ds)
        ds = None
        
        tmp_path = Path(tmp.name)
        tiff_bytes = tmp_path.read_bytes()
        tmp_path.unlink()
    
    return tiff_bytes


class TestFetchLayerCRSWorkaround:
    """Test CRS metadata injection in fetch_layer()."""
    
    def test_injects_crs_when_missing_epsg152160(
        self,
        temp_soils_dir: Path,
        mock_wms_response_no_crs: bytes,
    ) -> None:
        """Verify CRS is injected when EPSG:152160 response lacks metadata."""
        mock_response = MagicMock()
        mock_response.read.return_value = mock_wms_response_no_crs
        
        mock_wms = MagicMock()
        mock_wms.getmap.return_value = mock_response
        
        with patch('wepppy.locales.earth.soils.isric.WebMapService', return_value=mock_wms):
            fetch_layer(
                wms_url='https://test.example/map',
                layer='test_0-5cm_Q0.5',
                crs='EPSG:152160',
                adj_bbox=(-12774700, 5511400, -12767800, 5516600),
                size=(69, 52),
                format='image/tiff',
                soils_dir=str(temp_soils_dir),
                status_channel=None,
            )
        
        # Verify the file was created
        output_file = temp_soils_dir / 'test_0-5cm_Q0.5.tif'
        assert output_file.exists()
        
        # Check that CRS was injected
        ds = gdal.Open(str(output_file), gdal.GA_ReadOnly)
        wkt = ds.GetProjection()
        ds = None
        
        assert len(wkt) > 0, "WKT should be populated after injection"
        assert 'Interrupted_Goode_Homolosine' in wkt or 'igh' in wkt.lower()
    
    def test_preserves_existing_crs_epsg152160(
        self,
        temp_soils_dir: Path,
        mock_wms_response_with_crs: bytes,
    ) -> None:
        """Verify existing CRS is not overwritten for EPSG:152160."""
        mock_response = MagicMock()
        mock_response.read.return_value = mock_wms_response_with_crs
        
        mock_wms = MagicMock()
        mock_wms.getmap.return_value = mock_response
        
        with patch('wepppy.locales.earth.soils.isric.WebMapService', return_value=mock_wms):
            fetch_layer(
                wms_url='https://test.example/map',
                layer='test_0-5cm_Q0.5',
                crs='EPSG:152160',
                adj_bbox=(-12774700, 5511400, -12767800, 5516600),
                size=(69, 52),
                format='image/tiff',
                soils_dir=str(temp_soils_dir),
                status_channel=None,
            )
        
        output_file = temp_soils_dir / 'test_0-5cm_Q0.5.tif'
        
        # Verify CRS is still present and correct
        ds = gdal.Open(str(output_file), gdal.GA_ReadOnly)
        wkt = ds.GetProjection()
        ds = None
        
        assert len(wkt) > 0
        assert 'Interrupted_Goode_Homolosine' in wkt or 'igh' in wkt.lower()
    
    def test_skips_injection_for_other_crs(
        self,
        temp_soils_dir: Path,
        mock_wms_response_no_crs: bytes,
    ) -> None:
        """Verify CRS injection is skipped for non-152160 CRS codes."""
        mock_response = MagicMock()
        mock_response.read.return_value = mock_wms_response_no_crs
        
        mock_wms = MagicMock()
        mock_wms.getmap.return_value = mock_response
        
        with patch('wepppy.locales.earth.soils.isric.WebMapService', return_value=mock_wms):
            fetch_layer(
                wms_url='https://test.example/map',
                layer='test_0-5cm_Q0.5',
                crs='EPSG:4326',  # Different CRS
                adj_bbox=(-121.5, 49.7, -121.4, 49.8),
                size=(69, 52),
                format='image/tiff',
                soils_dir=str(temp_soils_dir),
                status_channel=None,
            )
        
        output_file = temp_soils_dir / 'test_0-5cm_Q0.5.tif'
        
        # Verify CRS was NOT injected (should remain empty)
        ds = gdal.Open(str(output_file), gdal.GA_ReadOnly)
        wkt = ds.GetProjection()
        ds = None
        
        assert len(wkt) == 0, "WKT should remain empty for non-152160 CRS"


class TestFetchISRICWRBCRSWorkaround:
    """Test CRS metadata injection in fetch_isric_wrb()."""
    
    def test_injects_crs_when_missing(
        self,
        temp_soils_dir: Path,
        mock_wms_response_no_crs: bytes,
    ) -> None:
        """Verify CRS is injected when WRB response lacks metadata."""
        mock_response = MagicMock()
        mock_response.read.return_value = mock_wms_response_no_crs
        
        mock_wms = MagicMock()
        mock_wms.getmap.return_value = mock_response
        
        with patch('wepppy.locales.earth.soils.isric.WebMapService', return_value=mock_wms):
            with patch('wepppy.locales.earth.soils.isric.adjust_to_grid') as mock_adjust:
                mock_adjust.return_value = (
                    (-12774700, 5511400, -12767800, 5516600),
                    (69, 52)
                )
                
                fetch_isric_wrb(
                    wgs_bbox=(-121.5, 49.7, -121.4, 49.8),
                    soils_dir=str(temp_soils_dir),
                    status_channel=None,
                )
        
        # Verify the file was created
        output_file = temp_soils_dir / 'wrb_MostProbable.tif'
        assert output_file.exists()
        
        # Check that CRS was injected
        ds = gdal.Open(str(output_file), gdal.GA_ReadOnly)
        wkt = ds.GetProjection()
        ds = None
        
        assert len(wkt) > 0, "WKT should be populated after injection"
        assert 'Interrupted_Goode_Homolosine' in wkt or 'igh' in wkt.lower()
    
    def test_preserves_existing_crs(
        self,
        temp_soils_dir: Path,
        mock_wms_response_with_crs: bytes,
    ) -> None:
        """Verify existing CRS is not overwritten in WRB."""
        mock_response = MagicMock()
        mock_response.read.return_value = mock_wms_response_with_crs
        
        mock_wms = MagicMock()
        mock_wms.getmap.return_value = mock_response
        
        with patch('wepppy.locales.earth.soils.isric.WebMapService', return_value=mock_wms):
            with patch('wepppy.locales.earth.soils.isric.adjust_to_grid') as mock_adjust:
                mock_adjust.return_value = (
                    (-12774700, 5511400, -12767800, 5516600),
                    (69, 52)
                )
                
                fetch_isric_wrb(
                    wgs_bbox=(-121.5, 49.7, -121.4, 49.8),
                    soils_dir=str(temp_soils_dir),
                    status_channel=None,
                )
        
        output_file = temp_soils_dir / 'wrb_MostProbable.tif'
        
        # Verify CRS is still present and correct
        ds = gdal.Open(str(output_file), gdal.GA_ReadOnly)
        wkt = ds.GetProjection()
        ds = None
        
        assert len(wkt) > 0
        assert 'Interrupted_Goode_Homolosine' in wkt or 'igh' in wkt.lower()
    
    def test_wrb_file_has_rat_and_crs(
        self,
        temp_soils_dir: Path,
        mock_wms_response_no_crs: bytes,
    ) -> None:
        """Verify both RAT and CRS are properly set in WRB output."""
        mock_response = MagicMock()
        mock_response.read.return_value = mock_wms_response_no_crs
        
        mock_wms = MagicMock()
        mock_wms.getmap.return_value = mock_response
        
        with patch('wepppy.locales.earth.soils.isric.WebMapService', return_value=mock_wms):
            with patch('wepppy.locales.earth.soils.isric.adjust_to_grid') as mock_adjust:
                mock_adjust.return_value = (
                    (-12774700, 5511400, -12767800, 5516600),
                    (69, 52)
                )
                
                fetch_isric_wrb(
                    wgs_bbox=(-121.5, 49.7, -121.4, 49.8),
                    soils_dir=str(temp_soils_dir),
                    status_channel=None,
                )
        
        output_file = temp_soils_dir / 'wrb_MostProbable.tif'
        ds = gdal.Open(str(output_file), gdal.GA_ReadOnly)
        
        # Check CRS
        wkt = ds.GetProjection()
        assert len(wkt) > 0, "WKT should be populated"
        assert 'Interrupted_Goode_Homolosine' in wkt or 'igh' in wkt.lower()
        
        # Check RAT
        band = ds.GetRasterBand(1)
        rat = band.GetDefaultRAT()
        assert rat is not None, "RAT should be attached"
        assert rat.GetColumnCount() == 2, "RAT should have VALUE and RSG columns"
        assert rat.GetRowCount() == 30, "RAT should have 30 WRB classes"
        
        ds = None


@pytest.mark.integration
class TestCRSWorkaroundIntegration:
    """Integration tests verifying end-to-end CRS handling."""
    
    def test_raster_interpolator_works_with_injected_crs(
        self,
        temp_soils_dir: Path,
        mock_wms_response_no_crs: bytes,
    ) -> None:
        """Verify RasterDatasetInterpolator can read files with injected CRS."""
        from wepppy.all_your_base.geo import RasterDatasetInterpolator
        
        mock_response = MagicMock()
        mock_response.read.return_value = mock_wms_response_no_crs
        
        mock_wms = MagicMock()
        mock_wms.getmap.return_value = mock_response
        
        with patch('wepppy.locales.earth.soils.isric.WebMapService', return_value=mock_wms):
            fetch_layer(
                wms_url='https://test.example/map',
                layer='bdod_0-5cm_Q0.5',
                crs='EPSG:152160',
                adj_bbox=(-12774700, 5511400, -12767800, 5516600),
                size=(69, 52),
                format='image/tiff',
                soils_dir=str(temp_soils_dir),
                status_channel=None,
            )
        
        output_file = temp_soils_dir / 'bdod_0-5cm_Q0.5.tif'
        
        # This should not raise "OGR Error: Corrupt data"
        interpolator = RasterDatasetInterpolator(str(output_file))
        
        # Verify the interpolator initialized successfully
        assert interpolator.wkt_text is not None
        assert len(interpolator.wkt_text) > 0
        # RasterDatasetInterpolator successfully created without error
