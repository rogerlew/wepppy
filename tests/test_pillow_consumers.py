"""Real native codec, font and plotting outputs for the owned Pillow build."""
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms, ImageDraw, ImageFont, ImageSequence
import pytest

pytestmark = pytest.mark.integration
FIXTURES = Path(__file__).parent / 'data/dependency_security'


@pytest.mark.parametrize('format,options', [
    ('PNG', {}), ('TIFF', {'compression': 'tiff_lzw'}),
    ('WEBP', {'lossless': True}), ('JPEG2000', {'irreversible': False}),
    ('BMP', {}),
])
def test_lossless_rgb_codec_roundtrip(format, options):
    pixels = np.arange(24 * 32 * 3, dtype=np.uint8).reshape(24, 32, 3)
    original = Image.fromarray(pixels)
    encoded = BytesIO()
    original.save(encoded, format=format, **options)
    encoded.seek(0)
    with Image.open(encoded) as decoded:
        decoded.load()
        assert decoded.format == format
        assert decoded.mode == 'RGB'
        assert decoded.size == original.size
        np.testing.assert_array_equal(np.asarray(decoded), pixels)


@pytest.mark.parametrize('format', ['PNG', 'WEBP', 'TIFF'])
def test_alpha_channels_survive(format):
    image = Image.new('RGBA', (24, 16), (10, 80, 120, 128))
    encoded = BytesIO()
    image.save(encoded, format=format, lossless=True)
    encoded.seek(0)
    with Image.open(encoded) as decoded:
        assert decoded.convert('RGBA').tobytes() == image.tobytes()


@pytest.mark.parametrize('format', ['JPEG', 'AVIF'])
def test_lossy_codecs_keep_color_and_geometry(format):
    image = Image.new('RGB', (32, 24), (40, 100, 180))
    encoded = BytesIO()
    image.save(encoded, format=format, quality=100)
    encoded.seek(0)
    with Image.open(encoded) as decoded:
        assert decoded.size == image.size
        assert decoded.mode == 'RGB'
        error = np.abs(np.asarray(decoded).astype(int) - np.asarray(image).astype(int))
        assert error.max() <= 2


@pytest.mark.parametrize('format', ['GIF', 'PNG', 'TIFF'])
def test_multiframe_pixels_and_order(format):
    frames = [Image.new('RGB', (16, 12), color) for color in ['red', 'blue']]
    encoded = BytesIO()
    frames[0].save(encoded, format=format, save_all=True, append_images=frames[1:], duration=100, loop=0)
    encoded.seek(0)
    with Image.open(encoded) as decoded:
        actual = [frame.convert('RGB').tobytes() for frame in ImageSequence.Iterator(decoded)]
        assert actual == [frame.tobytes() for frame in frames]
        for index in (0, 1, 0):
            decoded.seek(index)
            assert decoded.convert('RGB').tobytes() == frames[index].tobytes()


def test_icc_profile_roundtrip():
    image = Image.new('RGB', (10, 8), (20, 40, 60))
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
    encoded = BytesIO()
    image.save(encoded, format='PNG', icc_profile=profile)
    encoded.seek(0)
    with Image.open(encoded) as decoded:
        assert decoded.info['icc_profile'] == profile
        converted = ImageCms.profileToProfile(decoded, BytesIO(profile), BytesIO(profile), outputMode='RGB')
        assert converted.tobytes() == image.tobytes()


def test_woff2_real_font_without_layout_fallback():
    font = ImageFont.truetype(str(FIXTURES / 'OpenSans.woff2'), 20, layout_engine=ImageFont.Layout.BASIC)
    assert font.layout_engine == ImageFont.Layout.BASIC
    image = Image.new('RGB', (180, 48), 'white')
    ImageDraw.Draw(image).text((2, 2), 'WEPP café 123', font=font, fill='black')
    assert font.getbbox('WEPP café 123') == (0, 7, 135, 22)
    assert np.count_nonzero(np.any(np.asarray(image) != 255, axis=2)) == 833
    # This counts BASIC rendering, never a silent fallback from RAQM.


def test_matplotlib_agg_png_contains_rendered_plot():
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    figure = Figure(figsize=(4, 3), dpi=100)
    FigureCanvasAgg(figure)
    axes = figure.subplots()
    axes.plot([0, 1, 2], [0, 3, 1])
    axes.set(xlabel='Distance (m)', ylabel='Elevation (m)', title='Profile')
    encoded = BytesIO()
    figure.savefig(encoded, format='png')
    encoded.seek(0)
    with Image.open(encoded) as decoded:
        assert decoded.size == (400, 300)
        assert decoded.mode == 'RGBA'
        pixels = np.asarray(decoded)
        assert np.count_nonzero(np.any(pixels[:, :, :3] < 200, axis=2)) > 1000


def test_malformed_woff2_is_rejected():
    prefix = (FIXTURES / 'OpenSans.woff2').read_bytes()[:32]
    with pytest.raises(OSError):
        ImageFont.truetype(BytesIO(prefix), 20, layout_engine=ImageFont.Layout.BASIC)
