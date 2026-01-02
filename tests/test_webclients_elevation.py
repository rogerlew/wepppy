import pytest
from unittest.mock import Mock, patch

from wepppy.all_your_base.geo.webclients.elevation import elevationquery


def test_elevationquery_returns_elevation_value():
    """Test that elevationquery returns the elevation value from USGS API."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"value": 1234.5}

    with patch("wepppy.all_your_base.geo.webclients.elevation.requests.get", return_value=mock_response) as mock_get:
        result = elevationquery(lng=-116.5, lat=45.2)

    assert result == 1234.5
    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args
    assert kwargs["params"]["x"] == -116.5
    assert kwargs["params"]["y"] == 45.2
    assert kwargs["params"]["wkid"] == 4326
    assert kwargs["params"]["units"] == "Meters"
    assert kwargs["params"]["includeDate"] == "false"


def test_elevationquery_raises_on_http_error():
    """Test that elevationquery raises RuntimeError on non-200 status code."""
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch("wepppy.all_your_base.geo.webclients.elevation.requests.get", return_value=mock_response):
        with pytest.raises(RuntimeError, match="Elevation service returned HTTP 500"):
            elevationquery(lng=-116.5, lat=45.2)


def test_elevationquery_raises_on_invalid_json():
    """Test that elevationquery raises RuntimeError on invalid JSON response."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("Invalid JSON")

    with patch("wepppy.all_your_base.geo.webclients.elevation.requests.get", return_value=mock_response):
        with pytest.raises(RuntimeError, match="Cannot parse JSON from elevation response"):
            elevationquery(lng=-116.5, lat=45.2)


def test_elevationquery_raises_on_missing_value():
    """Test that elevationquery raises RuntimeError when 'value' field is missing."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"error": "No data available"}

    with patch("wepppy.all_your_base.geo.webclients.elevation.requests.get", return_value=mock_response):
        with pytest.raises(RuntimeError, match="Elevation response missing value"):
            elevationquery(lng=-116.5, lat=45.2)


def test_elevationquery_handles_negative_elevation():
    """Test that elevationquery correctly handles negative elevation values."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"value": -86.5}  # Death Valley or below sea level

    with patch("wepppy.all_your_base.geo.webclients.elevation.requests.get", return_value=mock_response):
        result = elevationquery(lng=-116.5, lat=36.2)

    assert result == -86.5


@pytest.mark.integration
@pytest.mark.skip(reason="Integration test - requires network access")
def test_elevationquery_real_api_call():
    """Integration test that makes a real API call to USGS National Map."""
    # Moscow, Idaho coordinates
    elevation = elevationquery(lng=-116.9997, lat=46.7324)

    # Moscow, Idaho is approximately 790 meters elevation
    # Allow a reasonable range for the assertion
    assert 750 < elevation < 850
