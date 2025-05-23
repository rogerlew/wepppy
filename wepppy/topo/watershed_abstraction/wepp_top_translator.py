# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.



def upland_hillslopes(chn_id, network, top_translator):
    """
    Given a channel id, return the upland hillslopes

    network is a dictionary of channel_ids with list of channels that drain into them
    """

    # need to recursively find the upland hillslopes by looking at the channels in
    # network[chn_id] and then checking for right, left, and top hillslopes by calling top_translator.channel_hillslopes(chn_id)
    
    assert top_translator.is_channel(top=chn_id), f"{chn_id} is not a channel"

    hillslopes = top_translator.channel_hillslopes(chn_id)
    
    for _chn_id in network.get(chn_id, []):
        if chn_id == _chn_id:
            continue
        hillslopes += upland_hillslopes(_chn_id, network, top_translator)

    return hillslopes


class WeppTopTranslator:
    """
    Utility class to translate between sub_ids, wepp_ids, 
    and topaz_ids, and chn_enums.
    
    Conventions
        sub_id
            string in the "hill_%i" % top format

        chn_id
            string in the "chn_%i" % top  format

        wepp (a.k.a. wepp_id)
            integer wepp id (consecutive)

        top (a.k.a. topaz_id)
            integer topaz
            right hillslopes end with 3
            left hillslopes end with 2
            center hillslopes end with 1
            channels end with 4

        chn_enum
            integer = wepp - hillslope_n
    """
    def __init__(self, top_sub_ids, top_chn_ids):
        # need the sub_ids as integers sorted in ascending order
        self._sub_ids = top_sub_ids = sorted(top_sub_ids)

        # need the chn_ids as integers sorted in descending order
        self._chn_ids = top_chn_ids = sorted(top_chn_ids, reverse=True)

        # now we are going to assign wepp ids and build
        # lookup dictionaries from translating between
        # wepp and topaz ids
        top2wepp = {0: 0}

        i = 1
        for _id in top_sub_ids:
            assert _id not in top2wepp
            top2wepp[_id] = i
            i += 1

        for _id in top_chn_ids:
            assert _id not in top2wepp
            top2wepp[_id] = i
            i += 1

        wepp2top = dict([(v, k) for k, v in top2wepp.items()])

        self.sub_ids = ["hill_%i" % _id for _id in top_sub_ids]
        self.chn_ids = ["chn_%i" % _id for _id in top_chn_ids]
        self._wepp2top = wepp2top
        self._top2wepp = top2wepp
        self.hillslope_n = len(top_sub_ids)
        self.channel_n = len(top_chn_ids)
        self.n = self.hillslope_n + self.channel_n

    @property
    def top2wepp(self):
        """
        dictionary of topazids (int) to weppids (int)
        """
        return self._top2wepp

    @property
    def wepp2top(self):
        return self._wepp2top

    def top(self, wepp=None, sub_id=None, chn_id=None, chn_enum=None):
        assert sum([v is not None for v in [wepp, sub_id, chn_id, chn_enum]]) == 1
        _wepp2top = self._wepp2top

        if sub_id is not None:
            if '_' in str(sub_id):
                return int(sub_id.split('_')[1])
            else:
                return sub_id

        if chn_id is not None:
            if '_' in str(chn_id):
                return int(chn_id.split('_')[1])
            else:
                return chn_id

        if chn_enum is not None:
            wepp = self.wepp(chn_enum=int(chn_enum))

        if wepp is not None:
            return _wepp2top[int(wepp)]

        return None

    def wepp(self, top=None, sub_id=None, chn_id=None, chn_enum=None):
        assert sum([v is not None for v in [top, sub_id, chn_id, chn_enum]]) == 1
        _top2wepp = self._top2wepp
        hillslope_n = self.hillslope_n

        if chn_enum is not None:
            return int(chn_enum) + hillslope_n

        if sub_id is not None:
            top = self.top(sub_id=sub_id)

        if chn_id is not None:
            top = self.top(chn_id=chn_id)

        if top is not None:
            return _top2wepp[int(top)]

        return None

    def chn_enum(self, wepp=None, chn_id=None, top=None):
        assert sum([v is not None for v in [wepp, chn_id, top]]) == 1
        hillslope_n = self.hillslope_n

        if chn_id is not None:
            wepp = self.wepp(chn_id=chn_id)

        if top is not None:
            wepp = self.wepp(top=int(top))

        if wepp == 0:
            return 0

        assert self.is_channel(wepp=wepp), (wepp, top)

        if wepp is not None:
            return wepp - hillslope_n

        return None

    def is_channel(self, top=None, wepp=None):
        assert sum([v is not None for v in [top, wepp]]) == 1

        if top is not None:
            return str(top).endswith('4')
        else:
            return str(self.top(wepp=int(wepp))).endswith('4')

    def has_top(self, top):
        return top in self._top2wepp

    def __iter__(self):
        for sub_id in self.sub_ids:
            yield int(sub_id.split('_')[1])

        for chn_id in self.chn_ids:
            yield int(chn_id.split('_')[1])

    def iter_chn_ids(self):
        for chn_id in self.chn_ids:
            yield chn_id

    def iter_sub_ids(self):
        for sub_id in self.sub_ids:
            yield sub_id

    def iter_wepp_chn_ids(self):
        for chn_id in self.chn_ids:
            yield self.wepp(chn_id=chn_id)
            
    def iter_wepp_sub_ids(self):
        wepp_ids = []
        for sub_id in self.sub_ids:
            wepp_ids.append(self.wepp(sub_id=sub_id))

        for wepp_id in sorted(wepp_ids):
            yield wepp_id


    def channel_hillslopes(self, chn_id):
        if isinstance(chn_id, str):
            chn_id = int(chn_id.split('_')[1])
            
        hillslopes = []

        # right subcatchments end in 2
        hright = int(chn_id) - 2
        if self.has_top(hright):
            hillslopes.append(hright)

        # left subcatchments end in 3
        hleft = int(chn_id) - 1
        if self.has_top(hleft):
            hillslopes.append(hleft)

        # center subcatchments end in 1
        hcenter = int(chn_id) - 3
        if self.has_top(hcenter):
            hillslopes.append(hcenter)

        return hillslopes

    def build_structure(self, network, pickle_fn=None):
        # now we are going to define the lines of the structure file
        # this doesn't handle impoundments

        structure = []
        for chn_id in self.iter_chn_ids():
            top = self.top(chn_id=chn_id)
            chn_enum = self.chn_enum(chn_id=chn_id)

            # right subcatchments end in 2
            hright = top - 2
            if not self.has_top(hright):
                hright = 0

            # left subcatchments end in 3
            hleft = top - 1
            if not self.has_top(hleft):
                hleft = 0

            # center subcatchments end in 1
            hcenter = top - 3
            if not self.has_top(hcenter):
                hcenter = 0

            # define structure for channel
            # the first item defines the channel
            _structure = [chn_enum]

            # network is defined from the NETW.TAB file that has
            # already been read into {network}
            # the 0s are appended to make sure it has a length of
            # at least 3
            chns = network.get(top, [])
            chns = [v for v in sorted(chns, reverse=True) if v != 24] + [0, 0, 0]

            # structure line with top ids
            _structure += [hright, hleft, hcenter] + chns[:3]

            # this is where we would handle impoundments
            # for now no impoundments are assumed
            _structure += [0, 0, 0]

            # and translate topaz to wepp
            structure.append([int(v) for v in _structure])

        if pickle_fn is not None:
            import pickle
            with open(pickle_fn, 'wb') as f:
                pickle.dump(structure, f)
            return None

        return structure

if __name__ == '__main__':
    wd = '/geodata/weppcloud_runs/insomniac-boatload/'

    from wepppy.nodb import Watershed

    watershed = Watershed.getInstance(wd)

    translator = watershed.translator_factory()

    from wepppy.topo.watershed_abstraction import upland_hillslopes

    network = watershed.network
    print(network)

    hills = upland_hillslopes(chn_id=194, network=network, top_translator=translator)
    print(hills)