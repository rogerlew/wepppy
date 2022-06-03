from math import exp


from wepppy.all_your_base import isfloat


class HorizonMixin(object):
    def _rosettaPredict(self):
        from rosetta import Rosetta3, Rosetta3

        clay = self.clay
        sand = self.sand
        vfs = self.vfs
        bd = self.bd

        assert isfloat(clay), clay
        assert isfloat(sand), sand
        assert isfloat(vfs), vfs
    
        if isfloat(bd):
            r3 = Rosetta3()
            res_dict = r3.predict_kwargs(sand=sand, silt=vfs, clay=clay, bd=bd)

        else:
            r2 = Rosetta2()
            res_dict = r2.predict_kwargs(sand=sand, silt=vfs, clay=clay)

        self.ks = res_dict['ks']
        self.wilt_pt = res_dict['wp']
        self.field_cap = res_dict['fc']
        self.rosetta_d = res_dict

    def _computeConductivity(self):
        clay = self.clay
        sand = self.sand
        cec = self.cec

        conductivity = 0 
        
        # conductivity
        if sand == 0.0 or clay == 0.0 or cec == 0.0:
            self.conductivity = None
            return
            
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
            
        self.conductivity = conductivity

  
    def _computeErodibility(self):
        """
        Computes erodibility estimates according to:
        
        https://www.ars.usda.gov/ARSUserFiles/50201000/WEPP/usersum.pdf
        """
        clay = self.clay
        sand = self.sand
        vfs = self.vfs
        om = self.om
        
        # interrill, rill, shear
        if sand == 0.0 or vfs == 0.0 or om == 0.0 or clay == 0.0:
            self.interrill = 0.0
            self.rill = 1.0
            self.shear = 0.0
            return 
        
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
      
        self.interrill = interrill
        self.rill = rill
        self.shear = shear

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
  
