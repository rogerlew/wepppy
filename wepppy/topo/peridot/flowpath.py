from dataclasses import dataclass
from typing import List

from wepppy.topo.watershed_abstraction.support import slp_asp_color


@dataclass
class Centroid:
    lnglat: List[float]
    px: List[int]


@dataclass
class PeridotFlowpath:
    topaz_id: str
    fp_id: str
    area: float
    centroid: Centroid
    direction: float
    aspect: float
    elevation: float
    length: float
    slope_scalar: float
    width: int
    color: str

    @classmethod
    def from_dict(cls, d):
        slope = float(d['slope_scalar'])
        aspect = float(d['aspect'])
        color = slp_asp_color(slope, aspect)
        return cls(
            topaz_id=d['topaz_id'],
            fp_id=d['fp_id'],
            area=d['area'],
            centroid=Centroid(lnglat=[d['centroid_lon'], d['centroid_lat']],
                              px=[d['centroid_px'], d['centroid_py']]),
            aspect=aspect,
            direction=d['direction'],
            elevation=d['elevation'],
            length=d['length'],
            slope_scalar=slope,
            width=d['width'],
            color=color
        )

    def as_dict(self):
        d = dict(
            topaz_id=self.topaz_id,
            fp_id=self.fp_id,
            length=self.length,
            width=self.width,
            area=self.area,
            aspect=self.aspect,
            direction=self.direction,
            slope_scalar=self.slope_scalar,
            color=self.color,
            centroid=self.centroid.lnglat
        )

        return d

    @property
    def fname(self):
        return f'slope_files/flowpaths/{self.topaz_id}/fp_{self.topaz_id}_{self.fp_id}.slp'

@dataclass
class PeridotHillslope:
    topaz_id: str
    wepp_id: str
    area: float
    centroid: Centroid
    direction: float
    aspect: float
    elevation: float
    length: float
    slope_scalar: float
    width: int
    color: str

    @property
    def slp_rel_path(self):
        return f'slope_files/hillslopes/hill_{self.topaz_id}.slp'

    @classmethod
    def from_dict(cls, d):
        slope = float(d['slope_scalar'])
        aspect = float(d['aspect'])
        color = slp_asp_color(slope, aspect)
        return cls(
            topaz_id=d['topaz_id'],
            wepp_id=d.get('wepp_id', None),
            area=d['area'],
            centroid=Centroid(lnglat=[d['centroid_lon'], d['centroid_lat']],
                              px=[d['centroid_px'], d['centroid_py']]),
            aspect=aspect,
            direction=d['direction'],
            elevation=d['elevation'],
            length=d['length'],
            slope_scalar=slope,
            width=d['width'],
            color=color
        )

    def as_dict(self):
        d = dict(
            topaz_id=self.topaz_id,
            wepp_id=getattr(self, 'wepp_id', None),
            length=self.length,
            width=self.width,
            area=self.area,
            aspect=self.aspect,
            direction=self.direction,
            slope_scalar=self.slope_scalar,
            color=self.color,
            centroid=self.centroid.lnglat
        )

        if hasattr(self, 'fp_longest'):
            d['fp_longest'] = self.fp_longest
        if hasattr(self, 'fp_longest_length'):
            d['fp_longest_length'] = self.fp_longest_length
        if hasattr(self, 'fp_longest_slope'):
            d['fp_longest_slope'] = self.fp_longest_slope

        return d

    @property
    def fname(self):
        return f'slope_files/hillslopes/hill_{self.topaz_id}.slp'

@dataclass
class PeridotChannel:
    topaz_id: str
    wepp_id: str
    area: float
    centroid: Centroid
    direction: float
    order: int
    aspect: float
    elevation: float
    length: float
    slope_scalar: float
    width: int
    color: str

    @classmethod
    def from_dict(cls, d):
        slope = float(d['slope_scalar'])
        aspect = float(d['aspect'])
        color = slp_asp_color(slope, aspect)
        return cls(
            topaz_id=d['topaz_id'],
            wepp_id=d.get('wepp_id', None),
            area=d['area'],
            centroid=Centroid(lnglat=[d['centroid_lon'], d['centroid_lat']],
                              px=[d['centroid_px'], d['centroid_py']]),
            direction=d['direction'],
            order=d['order'],
            aspect=aspect,
            elevation=d['elevation'],
            length=d['length'],
            slope_scalar=slope,
            width=d['width'],
            color=color
        )

    @property
    def channel_type(self) -> str:
        return 'Default'

    def as_dict(self):
        d = dict(
            topaz_id=self.topaz_id,
            wepp_id=getattr(self, 'wepp_id', None),
            length=self.length,
            width=self.width,
            area=self.area,
            aspect=self.aspect,
            direction=self.direction,
            order=self.order,
            slope_scalar=self.slope_scalar,
            color=self.color,
            centroid=self.centroid.lnglat,
            channel_type=self.channel_type
        )

        if hasattr(self, 'order'):
            d['order'] = self.order

        return d