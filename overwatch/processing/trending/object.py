class TrendingObject:
    def __init__(self, name, description, histogramNames, parameters):
        # type: (str, str, list, dict) -> None
        self.name = name
        self.desc = description
        self.histogramNames = histogramNames
        self.parameters = parameters

        self.values = []  # TODO change to numpy array
        self.currentEntry = 0
