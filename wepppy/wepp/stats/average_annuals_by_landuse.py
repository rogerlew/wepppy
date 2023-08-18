

from wepppy.wepp.stats import ReportBase
from wepppy.wepp.stats.row_data import RowData

class AverageAnnualsByLanduse(ReportBase):
    def __init__(self, annual_averages):
        self.annual_averages = annual_averages
        # Define the header based on annual averages' columns
        self.header = annual_averages.columns.tolist()

    def __iter__(self):
        for _, data_row in self.annual_averages.iterrows():
            yield RowData(data_row.to_dict())
