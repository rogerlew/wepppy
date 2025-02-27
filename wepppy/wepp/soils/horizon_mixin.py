from math import exp


from wepppy.all_your_base import isfloat


def estimate_bulk_density(sand_percent, silt_percent, clay_percent):
    """
    Estimate bulk density based on sand, silt, and clay percentages using general mid-point values.

    Parameters:
    - sand_percent: Percentage of sand in the soil.
    - silt_percent: Percentage of silt in the soil.
    - clay_percent: Percentage of clay in the soil.

    Returns:
    - Estimated bulk density (g/cm^3).
    """

    # Define mid-point values for each soil type
    sand_density = 1.6  # Midpoint of 1.5 - 1.7 g/cm^3
    silt_density = 1.4  # Midpoint of 1.3 - 1.5 g/cm^3
    clay_density = 1.2  # Midpoint of 1.1 - 1.3 g/cm^3
    remainder_density = 1.4  # Assuming remainder is loamy in nature

    # Calculate the remainder percentage
    remainder_percent = 100 - sand_percent - silt_percent - clay_percent

    # Calculate the estimated bulk density using a weighted average approach
    estimated_density = ((sand_percent * sand_density) +
                         (silt_percent * silt_density) +
                         (clay_percent * clay_density) +
                         (remainder_percent * remainder_density)) / 100

    return estimated_density


def compute_conductivity(clay: float, sand: float, cec: float):

    conductivity = 0

    # conductivity
    if sand == 0.0 or clay == 0.0 or cec == 0.0:
        return None

    if clay <= 40.0:
        if cec > 1.0:
            # apply equation 1 from usersum.pdf
            conductivity = -0.265 + 0.0086 * pow(sand, 1.8) + \
                           11.46 * pow(cec, -0.75)
        else:
            # this isn't documented in the usersum.pdf
            # this is what is being applied in the watershed
            # interface
            conductivity = 11.195 + 0.0086 * pow(sand, 1.8)
    else:
        # apply equation 2 from usersum.pdf
        conductivity = 0.0066 * exp(244.0 / clay)

    return conductivity


def compute_erodibilities(clay: float, sand: float, vfs: float, om: float):
    # interrill, rill, shear
    if sand == 0.0 or vfs == 0.0 or om == 0.0 or clay == 0.0:
        return dict(
            interrill=0.0,
            rill=0.0,
            shear=0.0
        )

    if sand >= 30.0:
        if vfs > 40.0:
            vfs = 40.0
        if om < 0.35:
            om = 1.36
        if clay > 42.0:
            clay = 42.0

        # apply equation 6 from usersum.pdf
        interrill = 2728000.0 + 192100.0 * vfs

        # apply equation 7 from usersum.pdf
        rill = 0.00197 + 0.00030 * vfs + 0.03863 * exp(-1.84 * om)

        # apply equation 8 from usersum.pdf
        shear = 2.67 + 0.065 * clay - 0.058 * vfs
    else:
        if clay < 10.0:
            clay = 10.0

        # apply equation 9 from usersum.pdf
        interrill = 6054000.0 - 55130.0 * clay

        # apply equation 10 from usersum.pdf
        rill = 0.0069 + 0.134 * exp(-0.20 * clay)

        # apply equation 11 from usersum.pdf
        shear = 3.5

    return dict(
        interrill=interrill,
        rill=rill,
        shear=shear
    )


class HorizonMixin(object):
    def _rosettaPredict(self):
        from rosetta import Rosetta2, Rosetta3, Rosetta5

        clay = self.clay
        sand = self.sand
        vfs = self.vfs
        bd = self.bd
        th33 = getattr(self, 'th33', None)
        th1500 = getattr(self, 'th1500', None)

        assert isfloat(clay), clay
        assert isfloat(sand), sand
        assert isfloat(vfs), vfs

        #if isfloat(bd) and isfloat(th33) and isfloat(th1500):
        #    r5 = Rosetta5()
        #    res_dict = r5.predict_kwargs(sand=sand, silt=vfs, clay=clay, bd=bd, th33=th33, th1500=th1500)

        if isfloat(bd):
            r3 = Rosetta3()
            res_dict = r3.predict_kwargs(sand=sand, silt=vfs, clay=clay, bd=bd)
            #{'theta_r': 0.07949616246974722, 'theta_s': 0.3758162328532708, 'alpha': 0.0195926196444751,
            # 'npar': 1.5931548676406013, 'ks': 40.19261619137084, 'wp': 0.08967567432339575, 'fc': 0.1877343793032436}

        else:
            r2 = Rosetta2()
            res_dict = r2.predict_kwargs(sand=sand, silt=vfs, clay=clay)

        self.ks = res_dict['ks']
        self.wilt_pt = res_dict['wp']
        self.field_cap = res_dict['fc']
        self.rosetta_d = res_dict

    def _computeConductivity(self):
        self.conductivity = compute_conductivity(clay=self.clay, sand=self.sand, cec=self.cec)

    @property
    def ksat(self):
        return self.conductivity

    def _computeErodibility(self):
        """
        Computes erodibility estimates according to:

        https://www.ars.usda.gov/ARSUserFiles/50201000/WEPP/usersum.pdf
        """

        res = compute_erodibilities(clay=self.clay, sand=self.sand, vfs=self.vfs, om=self.om)

        self.interrill = res['interrill']
        self.rill = res['rill']
        self.shear = res['shear']

    def _computeAnisotropy(self):
        hzdepb_r = self.depth

        anisotropy = None
        if isfloat(hzdepb_r):
            if hzdepb_r > 50:
                anisotropy = 1.0
            else:
                anisotropy = 10.0

        self.anisotropy = anisotropy

    @property
    def simple_texture(self):
        """
        Classifies horizon texture into silt loam, loam, sand loam, and clay loam
        Courtesy of Mary Ellen Miller
        :return:
        """
        from wepppy.wepp.soils.utils import simple_texture
        return simple_texture(self.clay, self.sand)

    def _computeAlbedo(self):
        albedo = 0.6 / exp(0.4 * self.om)
        if albedo < 0.01:
            albedo = 0.01

        self.albedo = albedo

    def to_dict(self):
        return dict(
            clay=self.clay,
            sand=self.sand,
            vfs=self.vfs,
            bd=self.bd,
            om=self.om,
            cec=self.cec,
            ki=self.interrill,
            kr=self.rill,
            shcrit=self.shear,
            anisotropy=self.anisotropy,
            ksat=self.conductivity,
            th33=self.th33,
            th1500=self.th1500,
            depth=self.depth,
            simple_texture=self.simple_texture,
        )
    
    def __str__(self):
        return f'{int(self.depth)} {self.bd:0.1f} {self.conductivity:0.2f} {self.anisotropy:0.1f} {self.field_cap:0.3f} {self.wilt_pt:0.3f} {self.sand:0.1f} {self.clay:0.1f} {self.om:0.1f} {self.cec:0.1f} {self.rfg:0.1f}'
