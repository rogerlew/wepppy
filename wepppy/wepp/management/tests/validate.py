# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew.gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

if __name__ == "__main__":
    from wepppy.wepp.management import (
        load_map,
        get_management_summary,
        get_management
    )

    d = load_map()

    for k in d.keys():
        print(k)
        man_sum = get_management_summary(k)
        print(man_sum.desc)

        m = get_management(k)
        m5 = m.build_multiple_year_man(5)
        m10 = m.build_multiple_year_man(10)
