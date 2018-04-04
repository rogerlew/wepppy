
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
