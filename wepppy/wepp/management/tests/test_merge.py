from wepppy.wepp.management import get_management, merge_managements

man42 = get_management(42, _map='disturbed')
man43 = get_management(52, _map='disturbed')

merged = merge_managements([man42, man43])
print(merged)
